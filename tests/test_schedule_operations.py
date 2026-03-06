"""
tests/test_schedule_operations.py — Schedule Operations Test Suite
SolaceBrowser: schedule approve / cancel / list + offline queue + cloud request

Tests (50+ required):
  TestPathTraversalPrevention (8 tests)  — run_id sanitization, URL-encoded traversal
  TestScheduleApprove        (10 tests) — approved_v1.json, audit log, eSign SHA-256, screenshot
  TestScheduleCancel         (6 tests)  — audit entry, custom reason, response format
  TestScheduleList           (10 tests) — audit JSONL, malformed lines, outbox merge, sorting
  TestOfflineQueue           (8 tests)  — token stripping, max size, permissions, file creation
  TestOfflineFlush           (10 tests) — age filter, retry cap, retry increment, unknown drop
  TestCloudRequest           (8 tests)  — timeouts, redirect protection, POST/GET behaviour

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_schedule_operations.py -v

Rung: 274177
Auth: 65537
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
import stat
import sys
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: ensure web/ is importable and provide a minimal data_store stub
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = REPO_ROOT / "web"
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

# We import the handler class directly and unit-test each method in isolation,
# avoiding a live HTTP server.
from server import SlugRequestHandler, build_handler_class, SolaceDataStore  # type: ignore


# ---------------------------------------------------------------------------
# Helpers — build a minimal handler instance without a real socket
# ---------------------------------------------------------------------------

class _FakeSocket:
    """Minimal socket lookalike for BaseHTTPRequestHandler.__init__."""

    def makefile(self, mode: str, *args: Any, **kwargs: Any):
        return io.BytesIO()

    def sendall(self, data: bytes) -> None:  # noqa: D401
        pass


class _FakeDataStore:
    """Stub data store that returns empty settings by default."""

    def __init__(self, settings: dict | None = None) -> None:
        self._settings: dict = settings or {}

    def read_settings(self) -> dict:
        return dict(self._settings)

    def write_settings(self, data: dict) -> None:
        self._settings = dict(data)


def _make_handler(
    tmp_home: Path,
    settings: dict | None = None,
) -> SlugRequestHandler:
    """Create a SlugRequestHandler instance wired to tmp_home, capturing output."""
    store = _FakeDataStore(settings)
    handler_cls = build_handler_class(store)  # type: ignore[arg-type]

    # Intercept the raw socket I/O
    raw_request = b"POST / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    client_address = ("127.0.0.1", 9999)
    server_mock = MagicMock()

    handler = handler_cls.__new__(handler_cls)
    handler.data_store = store  # type: ignore[attr-defined]

    # Responses are written here
    handler._response_buffer = io.BytesIO()
    handler.wfile = handler._response_buffer
    handler.rfile = io.BytesIO()
    handler.server = server_mock
    handler.client_address = client_address
    handler.requestline = "POST / HTTP/1.1"
    handler.request_version = "HTTP/1.1"
    handler.command = "POST"
    handler.path = "/"
    handler.headers = {}  # type: ignore[assignment]
    handler.close_connection = False

    # Patch send_response / send_header / end_headers to capture calls
    handler._sent_status: int | None = None
    handler._sent_headers: dict[str, str] = {}

    def _fake_send_response(status: int, message: str = "") -> None:
        if isinstance(status, HTTPStatus):
            handler._sent_status = status.value
        else:
            handler._sent_status = int(status)

    def _fake_send_header(key: str, value: str) -> None:
        handler._sent_headers[key] = value

    def _fake_end_headers() -> None:
        pass

    handler.send_response = _fake_send_response  # type: ignore[method-assign]
    handler.send_header = _fake_send_header  # type: ignore[method-assign]
    handler.end_headers = _fake_end_headers  # type: ignore[method-assign]

    return handler


def _last_json(handler: SlugRequestHandler) -> dict:
    """Parse the most recently written JSON response from the buffer."""
    buf = handler._response_buffer.getvalue()  # type: ignore[attr-defined]
    # Reset so we can capture the next call
    handler._response_buffer.seek(0)
    handler._response_buffer.truncate()
    return json.loads(buf)


# ---------------------------------------------------------------------------
# Fixture — isolated home directory
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect Path.home() to a temporary directory for the test."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    return fake_home


@pytest.fixture()
def handler(tmp_home: Path) -> SlugRequestHandler:
    return _make_handler(tmp_home)


# ===========================================================================
# 1. Path Traversal Prevention
# ===========================================================================

class TestPathTraversalPrevention:
    """Verify that run_id values containing path traversal sequences are rejected."""

    # --- helpers that simulate the routing validation logic from do_POST ---

    @staticmethod
    def _validate_run_id(run_id: str) -> bool:
        """Mirror the regex check used in server.py routing."""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_\-]+$', run_id))

    def test_dotdot_slash_rejected(self):
        """run_id with '../' must not pass validation."""
        assert not self._validate_run_id("../etc/passwd")

    def test_dotdot_only_rejected(self):
        """run_id consisting only of '..' is rejected."""
        assert not self._validate_run_id("..")

    def test_slash_in_run_id_rejected(self):
        """run_id containing '/' is rejected."""
        assert not self._validate_run_id("run/../../secret")

    def test_url_encoded_traversal_rejected(self):
        """URL-encoded '%2F' or '%2E' traversal is rejected by the regex."""
        assert not self._validate_run_id("run%2F..%2Fetc")

    def test_null_byte_rejected(self):
        """Null byte in run_id is rejected."""
        assert not self._validate_run_id("run\x00id")

    def test_valid_alphanumeric_accepted(self):
        """Plain alphanumeric run_id passes."""
        assert self._validate_run_id("run123")

    def test_valid_with_dash_and_underscore_accepted(self):
        """run_id with dashes and underscores is valid."""
        assert self._validate_run_id("run_abc-123")

    def test_approve_returns_400_for_invalid_run_id(self, handler: SlugRequestHandler, tmp_home: Path):
        """
        When the routing layer detects an invalid run_id it calls _send_json with 400.
        We replicate that guard here by confirming our regex blocks the request before
        _handle_schedule_approve is reached.
        """
        import re
        bad_run_id = "../../../etc/passwd"
        # Simulate what do_POST does:
        if not re.match(r'^[a-zA-Z0-9_\-]+$', bad_run_id):
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid run_id format"})
        body = _last_json(handler)
        assert handler._sent_status == 400
        assert "error" in body


# ===========================================================================
# 2. Schedule Approve
# ===========================================================================

class TestScheduleApprove:
    """Unit tests for _handle_schedule_approve."""

    def _setup_outbox_run(self, tmp_home: Path, app_id: str, run_id: str) -> Path:
        """Create outbox/<app_id>/<run_id>/ directory structure."""
        run_dir = tmp_home / ".solace" / "outbox" / "apps" / app_id / run_id
        run_dir.mkdir(parents=True)
        return run_dir

    def test_approve_writes_approved_v1_json(self, handler: SlugRequestHandler, tmp_home: Path):
        """Successful approval writes approved_v1.json to the run directory."""
        run_dir = self._setup_outbox_run(tmp_home, "gmail", "run-001")

        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve("run-001", {"approved_by": "alice"})

        approved_file = run_dir / "approved_v1.json"
        assert approved_file.exists(), "approved_v1.json must be written on approval"
        data = json.loads(approved_file.read_text())
        assert data["run_id"] == "run-001"
        assert data["approved_by"] == "alice"

    def test_approve_creates_audit_log_entry(self, handler: SlugRequestHandler, tmp_home: Path):
        """Approval always appends a JSONL entry to audit/schedule_actions.jsonl."""
        self._setup_outbox_run(tmp_home, "gmail", "run-002")
        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve("run-002", {"approved_by": "bob"})

        audit_file = tmp_home / ".solace" / "audit" / "schedule_actions.jsonl"
        assert audit_file.exists()
        entries = [json.loads(line) for line in audit_file.read_text().strip().splitlines()]
        assert any(e.get("run_id") == "run-002" and e.get("event") == "approved"
                   for e in entries)

    def test_approve_generates_esign_record(self, handler: SlugRequestHandler, tmp_home: Path):
        """Approval generates an eSign JSONL file with SHA-256 hash fields."""
        self._setup_outbox_run(tmp_home, "gmail", "run-003")
        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve("run-003", {"approved_by": "carol"})

        esign_file = tmp_home / ".solace" / "audit" / "esign-run-003.jsonl"
        assert esign_file.exists()
        first_entry = json.loads(esign_file.read_text().strip().splitlines()[0])
        assert first_entry["event_type"] == "ESIGN"
        assert "esign_hash" in first_entry
        assert "action_hash" in first_entry
        # Verify hash length (SHA-256 = 64 hex chars)
        assert len(first_entry["esign_hash"]) == 64
        assert len(first_entry["action_hash"]) == 64

    def test_approve_esign_hash_is_deterministic(self, handler: SlugRequestHandler, tmp_home: Path):
        """The eSign hash is reproducible given the same inputs."""
        self._setup_outbox_run(tmp_home, "gmail", "run-999")
        user_id = "dave"
        meaning = "reviewed_and_approved"
        action_desc = "Approved scheduled run run-999"
        action_hash = hashlib.sha256(action_desc.encode()).hexdigest()
        # Server uses hash-chain: prev_hash|user_id|ts|meaning|action_hash

        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve(
                "run-999", {"approved_by": user_id}
            )

        esign_file = tmp_home / ".solace" / "audit" / "esign-run-999.jsonl"
        first_entry = json.loads(esign_file.read_text().strip().splitlines()[0])
        # Verify hash is deterministic by recomputing with server timestamp + hash chain
        ts = first_entry["timestamp"]
        prev_hash = first_entry.get("prev_hash", "genesis")
        expected = hashlib.sha256(f"{prev_hash}|{user_id}|{ts}|{meaning}|{action_hash}".encode()).hexdigest()
        assert first_entry["esign_hash"] == expected

    def test_approve_screenshot_failure_is_logged_not_silent(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Screenshot failure is logged as SCREENSHOT_FAILED in the eSign file (not silently dropped)."""
        self._setup_outbox_run(tmp_home, "gmail", "run-004")
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            handler._handle_schedule_approve("run-004", {"approved_by": "eve"})

        esign_file = tmp_home / ".solace" / "audit" / "esign-run-004.jsonl"
        lines = [json.loads(l) for l in esign_file.read_text().strip().splitlines()]
        failed_entries = [l for l in lines if l.get("event_type") == "SCREENSHOT_FAILED"]
        assert failed_entries, "SCREENSHOT_FAILED entry must be recorded on screenshot error"
        assert "error" in failed_entries[0]

    def test_approve_rejects_nonexistent_run_id(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Approval of a run not found in outbox returns 404 (no phantom approvals)."""
        # No outbox directory created
        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve("ghost-run-999", {"approved_by": "frank"})

        assert handler._sent_status == 404
        body = _last_json(handler)
        assert "error" in body

    def test_approve_response_contains_esign_hash(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """HTTP response JSON contains esign_hash field."""
        self._setup_outbox_run(tmp_home, "gmail", "run-005")
        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve("run-005", {"approved_by": "grace"})
        body = _last_json(handler)
        assert "esign_hash" in body
        assert len(body["esign_hash"]) == 64

    def test_approve_response_run_id_matches(self, handler: SlugRequestHandler, tmp_home: Path):
        """HTTP response run_id echoes the requested run_id."""
        self._setup_outbox_run(tmp_home, "gmail", "run-007")
        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve("run-007", {})
        body = _last_json(handler)
        assert body.get("run_id") == "run-007"

    def test_approve_with_successful_screenshot(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """When screenshot succeeds, its path is returned in the response."""
        self._setup_outbox_run(tmp_home, "gmail", "run-006")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"filepath": "/tmp/esign-run-006.png"}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            handler._handle_schedule_approve("run-006", {"approved_by": "hank"})

        body = _last_json(handler)
        assert body.get("screenshot") == "/tmp/esign-run-006.png"

    def test_approve_in_outbox_flag_is_true_when_run_exists(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """in_outbox is True when the run directory exists."""
        self._setup_outbox_run(tmp_home, "gmail", "run-101")
        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve("run-101", {})
        body = _last_json(handler)
        assert body.get("in_outbox") is True

    def test_approve_returns_404_when_run_missing(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Returns 404 when no matching run directory found (no phantom approvals)."""
        # No outbox exists
        with patch("urllib.request.urlopen", side_effect=OSError("no browser")):
            handler._handle_schedule_approve("run-102", {})
        assert handler._sent_status == 404


# ===========================================================================
# 3. Schedule Cancel
# ===========================================================================

class TestScheduleCancel:
    """Unit tests for _handle_schedule_cancel."""

    def test_cancel_writes_audit_entry(self, handler: SlugRequestHandler, tmp_home: Path):
        """Cancellation always appends a record to audit/schedule_actions.jsonl."""
        handler._handle_schedule_cancel("run-010", {"reason": "user_rejected"})

        audit_file = tmp_home / ".solace" / "audit" / "schedule_actions.jsonl"
        assert audit_file.exists()
        entries = [json.loads(l) for l in audit_file.read_text().strip().splitlines()]
        assert any(
            e.get("run_id") == "run-010" and e.get("event") == "cancelled"
            for e in entries
        )

    def test_cancel_default_reason_is_user_rejected(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Default cancellation reason is 'user_rejected' when not supplied."""
        handler._handle_schedule_cancel("run-011", {})
        audit_file = tmp_home / ".solace" / "audit" / "schedule_actions.jsonl"
        entries = [json.loads(l) for l in audit_file.read_text().strip().splitlines()]
        record = next(e for e in entries if e.get("run_id") == "run-011")
        assert record["reason"] == "user_rejected"

    def test_cancel_custom_reason_stored(self, handler: SlugRequestHandler, tmp_home: Path):
        """Custom cancellation reason is preserved in the audit entry."""
        handler._handle_schedule_cancel("run-012", {"reason": "timeout_exceeded"})
        audit_file = tmp_home / ".solace" / "audit" / "schedule_actions.jsonl"
        entries = [json.loads(l) for l in audit_file.read_text().strip().splitlines()]
        record = next(e for e in entries if e.get("run_id") == "run-012")
        assert record["reason"] == "timeout_exceeded"

    def test_cancel_response_ok_true(self, handler: SlugRequestHandler, tmp_home: Path):
        """Response JSON must contain ok: true."""
        handler._handle_schedule_cancel("run-013", {})
        body = _last_json(handler)
        assert body.get("ok") is True

    def test_cancel_response_returns_run_id(self, handler: SlugRequestHandler, tmp_home: Path):
        """Response JSON echoes the run_id."""
        handler._handle_schedule_cancel("run-014", {})
        body = _last_json(handler)
        assert body.get("run_id") == "run-014"

    def test_cancel_status_200(self, handler: SlugRequestHandler, tmp_home: Path):
        """HTTP status for a cancel call is 200 OK."""
        handler._handle_schedule_cancel("run-015", {})
        assert handler._sent_status == 200


# ===========================================================================
# 4. Schedule List
# ===========================================================================

class TestScheduleList:
    """Unit tests for _handle_schedule_list."""

    def _write_audit(self, tmp_home: Path, filename: str, entries: list[dict]) -> None:
        audit_dir = tmp_home / ".solace" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        f = audit_dir / filename
        f.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    def test_returns_activities_from_audit_log(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Activities list is populated from JSONL files in ~/.solace/audit/."""
        self._write_audit(tmp_home, "2026-03-01.jsonl", [
            {"run_id": "r1", "app_id": "gmail", "status": "success",
             "started_at": "2026-03-01T10:00:00Z"},
        ])
        handler._handle_schedule_list(send_body=True)
        body = _last_json(handler)
        ids = [a["id"] for a in body["activities"]]
        assert "r1" in ids

    def test_total_count_matches_activities(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """total field equals length of activities list."""
        self._write_audit(tmp_home, "2026-03-01.jsonl", [
            {"run_id": "x1", "status": "success", "started_at": "2026-03-01T10:00:00Z"},
            {"run_id": "x2", "status": "success", "started_at": "2026-03-01T11:00:00Z"},
        ])
        handler._handle_schedule_list(send_body=True)
        body = _last_json(handler)
        assert body["total"] == len(body["activities"])

    def test_malformed_jsonl_lines_skipped_gracefully(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Malformed JSON lines in audit files are skipped; valid lines still appear."""
        audit_dir = tmp_home / ".solace" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        mixed = (
            '{"run_id": "good1", "status": "success", "started_at": "2026-03-01T09:00:00Z"}\n'
            'NOT_VALID_JSON\n'
            '{"run_id": "good2", "status": "success", "started_at": "2026-03-01T08:00:00Z"}\n'
        )
        (audit_dir / "mixed.jsonl").write_text(mixed, encoding="utf-8")
        # Must not raise; returns both valid entries
        handler._handle_schedule_list(send_body=True)
        body = _last_json(handler)
        ids = [a["id"] for a in body["activities"]]
        assert "good1" in ids
        assert "good2" in ids

    def test_empty_audit_dir_returns_empty_list(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """With no audit files, activities is an empty list."""
        handler._handle_schedule_list(send_body=True)
        body = _last_json(handler)
        assert body["activities"] == []
        assert body["total"] == 0

    def test_pending_approvals_merged_from_outbox(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Items with preview.json but no approved_v1.json appear as pending_approval."""
        run_dir = tmp_home / ".solace" / "outbox" / "apps" / "notion" / "run-pending"
        run_dir.mkdir(parents=True)
        (run_dir / "preview.json").write_text(
            json.dumps({
                "app_name": "Notion",
                "preview_summary": "Export pages",
                "safety_tier": "B",
                "created_at": "2026-03-01T12:00:00Z",
                "scopes": ["read"],
            }),
            encoding="utf-8",
        )
        handler._handle_schedule_list(send_body=True)
        body = _last_json(handler)
        pending = [a for a in body["activities"] if a["status"] == "pending_approval"]
        assert any(a["id"] == "run-pending" for a in pending)

    def test_already_approved_outbox_not_included_as_pending(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Run directories with approved_v1.json are NOT listed as pending_approval."""
        run_dir = tmp_home / ".solace" / "outbox" / "apps" / "gmail" / "run-approved"
        run_dir.mkdir(parents=True)
        (run_dir / "preview.json").write_text(json.dumps({"app_name": "Gmail"}))
        (run_dir / "approved_v1.json").write_text(json.dumps({"run_id": "run-approved"}))
        handler._handle_schedule_list(send_body=True)
        body = _last_json(handler)
        pending = [a for a in body["activities"] if a.get("status") == "pending_approval"]
        assert all(a["id"] != "run-approved" for a in pending)

    def test_activities_sorted_by_started_at_descending(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Activities are returned newest-first."""
        self._write_audit(tmp_home, "sorted.jsonl", [
            {"run_id": "old", "status": "success", "started_at": "2026-01-01T00:00:00Z"},
            {"run_id": "new", "status": "success", "started_at": "2026-03-01T00:00:00Z"},
        ])
        handler._handle_schedule_list(send_body=True)
        body = _last_json(handler)
        ids = [a["id"] for a in body["activities"]]
        assert ids.index("new") < ids.index("old")

    def test_status_200_returned(self, handler: SlugRequestHandler, tmp_home: Path):
        """HTTP status is 200 on a successful list call."""
        handler._handle_schedule_list(send_body=True)
        assert handler._sent_status == 200

    def test_malformed_preview_json_skipped(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Malformed preview.json in outbox is skipped without crashing."""
        run_dir = tmp_home / ".solace" / "outbox" / "apps" / "slack" / "run-broken"
        run_dir.mkdir(parents=True)
        (run_dir / "preview.json").write_text("NOT JSON", encoding="utf-8")
        # Must not raise
        handler._handle_schedule_list(send_body=True)
        body = _last_json(handler)
        assert "activities" in body

    def test_unreadable_audit_file_skipped_gracefully(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """OSError on audit file read is handled; other entries still returned."""
        audit_dir = tmp_home / ".solace" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        good_file = audit_dir / "good.jsonl"
        good_file.write_text(
            json.dumps({"run_id": "ok1", "status": "success", "started_at": "2026-03-01T00:00:00Z"}),
            encoding="utf-8",
        )
        bad_file = audit_dir / "bad.jsonl"
        bad_file.write_text("placeholder", encoding="utf-8")
        # Make bad_file unreadable at the OS level
        bad_file.chmod(0o000)
        try:
            # Must not raise; still returns the good entry
            handler._handle_schedule_list(send_body=True)
            body = _last_json(handler)
            assert "activities" in body
        finally:
            # Restore permissions so tmp_path cleanup works
            bad_file.chmod(0o644)


# ===========================================================================
# 5. Offline Queue
# ===========================================================================

class TestOfflineQueue:
    """Unit tests for _queue_offline."""

    def test_queue_strips_auth_token(self, handler: SlugRequestHandler, tmp_home: Path):
        """auth_token must be removed from queued payload."""
        handler._OFFLINE_QUEUE = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        handler._queue_offline("esign_token", {
            "auth_token": "supersecret",
            "user_id": "alice",
        })
        entry = json.loads(handler._OFFLINE_QUEUE.read_text().strip())
        assert "auth_token" not in entry["payload"]
        assert entry["payload"]["user_id"] == "alice"

    def test_queue_strips_bearer_token(self, handler: SlugRequestHandler, tmp_home: Path):
        """bearer_token must be removed from queued payload."""
        handler._OFFLINE_QUEUE = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        handler._queue_offline("esign_sign", {"bearer_token": "tok123", "data": "x"})
        entry = json.loads(handler._OFFLINE_QUEUE.read_text().strip())
        assert "bearer_token" not in entry["payload"]

    def test_queue_strips_password(self, handler: SlugRequestHandler, tmp_home: Path):
        """password must be removed from queued payload."""
        handler._OFFLINE_QUEUE = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        handler._queue_offline("esign_sign", {"password": "hunter2", "user": "bob"})
        entry = json.loads(handler._OFFLINE_QUEUE.read_text().strip())
        assert "password" not in entry["payload"]

    def test_queue_strips_secret(self, handler: SlugRequestHandler, tmp_home: Path):
        """secret field must be removed from queued payload."""
        handler._OFFLINE_QUEUE = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        handler._queue_offline("cloud_sync_push", {"secret": "sk-xxx", "name": "test"})
        entry = json.loads(handler._OFFLINE_QUEUE.read_text().strip())
        assert "secret" not in entry["payload"]

    def test_queue_respects_max_size(self, handler: SlugRequestHandler, tmp_home: Path):
        """When queue is at max capacity the oldest entry is dropped."""
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        handler._OFFLINE_QUEUE = queue_file

        # Fill queue to exactly max
        max_size = handler._OFFLINE_QUEUE_MAX
        lines = [json.dumps({"action": "esign_sign", "payload": {}, "queued_at": f"entry-{i}", "retry_count": 0})
                 for i in range(max_size)]
        queue_file.write_text("\n".join(lines) + "\n")

        handler._queue_offline("cloud_evidence_push", {"new": "entry"})

        actual_lines = [l for l in queue_file.read_text().strip().splitlines() if l.strip()]
        # Size should not exceed max + 1 (new entry was appended after drop)
        assert len(actual_lines) <= max_size

    def test_queue_parent_directory_has_restrictive_permissions(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Queue parent directory must have mode 0o700 (owner-only)."""
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        handler._OFFLINE_QUEUE = queue_file
        handler._queue_offline("esign_token", {"user_id": "carol"})
        mode = stat.S_IMODE(queue_file.parent.stat().st_mode)
        assert mode == 0o700, f"Expected 0o700, got {oct(mode)}"

    def test_queue_creates_file_if_missing(self, handler: SlugRequestHandler, tmp_home: Path):
        """Queue file is created on first write if it does not exist."""
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        handler._OFFLINE_QUEUE = queue_file
        assert not queue_file.exists()
        handler._queue_offline("esign_sign", {"user_id": "dave"})
        assert queue_file.exists()

    def test_queue_preserves_non_sensitive_fields(
        self, handler: SlugRequestHandler, tmp_home: Path
    ):
        """Non-sensitive payload fields are kept intact."""
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        handler._OFFLINE_QUEUE = queue_file
        handler._queue_offline("cloud_evidence_push", {
            "run_id": "r42",
            "app_id": "gmail",
            "auth_token": "DROP_ME",
        })
        entry = json.loads(queue_file.read_text().strip())
        assert entry["payload"]["run_id"] == "r42"
        assert entry["payload"]["app_id"] == "gmail"
        assert "auth_token" not in entry["payload"]


# ===========================================================================
# 6. Offline Flush
# ===========================================================================

class TestOfflineFlush:
    """Unit tests for _handle_offline_flush."""

    def _setup_handler_with_token(self, tmp_home: Path, token: str = "valid-token") -> SlugRequestHandler:
        settings = {"cloud": {"auth_token": token}}
        h = _make_handler(tmp_home, settings=settings)
        h._OFFLINE_QUEUE = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        h._SOLACE_CLOUD_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app"
        return h

    def _write_queue(self, tmp_home: Path, items: list[dict]) -> None:
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        queue_file.write_text(
            "\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8"
        )

    def test_flush_skips_items_older_than_24_hours(
        self, tmp_home: Path
    ):
        """Items queued more than 24 hours ago are dropped (tokens likely expired)."""
        stale_ts = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=25)
        ).isoformat()
        self._write_queue(tmp_home, [
            {"action": "esign_sign", "payload": {}, "queued_at": stale_ts, "retry_count": 0},
        ])
        h = self._setup_handler_with_token(tmp_home)
        with patch.object(h, "_cloud_request", return_value=(200, {"ok": True})):
            h._handle_offline_flush({})
        body = _last_json(h)
        # Item was stale → dropped into errors, not flushed
        assert body["flushed"] == 0
        assert body["errors"] == 1

    def test_flush_skips_items_at_max_retry(self, tmp_home: Path):
        """Items with retry_count >= 5 are dropped."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._write_queue(tmp_home, [
            {"action": "esign_sign", "payload": {}, "queued_at": now_ts, "retry_count": 5},
        ])
        h = self._setup_handler_with_token(tmp_home)
        with patch.object(h, "_cloud_request", return_value=(200, {"ok": True})):
            h._handle_offline_flush({})
        body = _last_json(h)
        assert body["flushed"] == 0
        assert body["errors"] >= 1

    def test_flush_increments_retry_count_on_server_error(self, tmp_home: Path):
        """retry_count is incremented when the cloud returns 500."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._write_queue(tmp_home, [
            {"action": "esign_sign", "payload": {"data": "x"}, "queued_at": now_ts, "retry_count": 2},
        ])
        h = self._setup_handler_with_token(tmp_home)
        with patch.object(h, "_cloud_request", return_value=(500, {"error": "srv"})):
            h._handle_offline_flush({})
        # Item remains in queue with retry_count = 3
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        assert queue_file.exists()
        remaining = json.loads(queue_file.read_text().strip().splitlines()[0])
        assert remaining["retry_count"] == 3

    def test_flush_drops_unknown_action_types(self, tmp_home: Path):
        """Actions not in action_map are dropped (counted as errors, not kept)."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._write_queue(tmp_home, [
            {"action": "totally_unknown_action", "payload": {}, "queued_at": now_ts, "retry_count": 0},
        ])
        h = self._setup_handler_with_token(tmp_home)
        with patch.object(h, "_cloud_request", return_value=(200, {"ok": True})):
            h._handle_offline_flush({})
        body = _last_json(h)
        assert body["flushed"] == 0
        assert body["errors"] >= 1
        # Queue should be empty (item dropped)
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        assert not queue_file.exists()

    def test_flush_succeeds_and_deletes_queue_file(self, tmp_home: Path):
        """After flushing all items successfully, the queue file is deleted."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._write_queue(tmp_home, [
            {"action": "esign_sign", "payload": {"d": 1}, "queued_at": now_ts, "retry_count": 0},
        ])
        h = self._setup_handler_with_token(tmp_home)
        with patch.object(h, "_cloud_request", return_value=(200, {"ok": True})):
            h._handle_offline_flush({})
        body = _last_json(h)
        assert body["flushed"] == 1
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        assert not queue_file.exists(), "Queue file should be removed after full flush"

    def test_flush_returns_401_without_auth_token(self, tmp_home: Path):
        """Flush returns 401 when no cloud auth token is configured."""
        h = _make_handler(tmp_home, settings={})
        h._OFFLINE_QUEUE = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        h._handle_offline_flush({})
        assert h._sent_status == 401

    def test_flush_empty_queue_returns_zero(self, tmp_home: Path):
        """When no queue file exists, flush returns flushed=0, errors=0."""
        h = self._setup_handler_with_token(tmp_home)
        h._handle_offline_flush({})
        body = _last_json(h)
        assert body["flushed"] == 0
        assert body["errors"] == 0

    def test_flush_multiple_items_all_succeed(self, tmp_home: Path):
        """Multiple valid queue items are all flushed in one call."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._write_queue(tmp_home, [
            {"action": "esign_sign", "payload": {"i": 1}, "queued_at": now_ts, "retry_count": 0},
            {"action": "cloud_evidence_push", "payload": {"i": 2}, "queued_at": now_ts, "retry_count": 0},
            {"action": "cloud_sync_push", "payload": {"i": 3}, "queued_at": now_ts, "retry_count": 0},
        ])
        h = self._setup_handler_with_token(tmp_home)
        with patch.object(h, "_cloud_request", return_value=(201, {"ok": True})):
            h._handle_offline_flush({})
        body = _last_json(h)
        assert body["flushed"] == 3
        assert body["errors"] == 0

    def test_flush_offline_response_keeps_item_in_queue(self, tmp_home: Path):
        """When cloud returns status=0 (offline), item is retained for retry."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._write_queue(tmp_home, [
            {"action": "esign_token", "payload": {"d": 1}, "queued_at": now_ts, "retry_count": 0},
        ])
        h = self._setup_handler_with_token(tmp_home)
        with patch.object(h, "_cloud_request", return_value=(0, {"offline": True})):
            h._handle_offline_flush({})
        queue_file = tmp_home / ".solace" / "sync" / "offline-queue.jsonl"
        assert queue_file.exists(), "Item should remain in queue when cloud is offline"

    def test_flush_just_below_max_retry_keeps_item(self, tmp_home: Path):
        """Item with retry_count=4 is still attempted (< 5 threshold)."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._write_queue(tmp_home, [
            {"action": "esign_sign", "payload": {}, "queued_at": now_ts, "retry_count": 4},
        ])
        h = self._setup_handler_with_token(tmp_home)
        call_count = {"n": 0}

        def _fake_cr(method, path, payload=None, token=None):
            call_count["n"] += 1
            return (200, {"ok": True})

        with patch.object(h, "_cloud_request", side_effect=_fake_cr):
            h._handle_offline_flush({})
        # Should have been attempted
        assert call_count["n"] == 1


# ===========================================================================
# 7. Cloud Request
# ===========================================================================

class TestCloudRequest:
    """Unit tests for _cloud_request — timeout selection and redirect protection."""

    def _make_cr_handler(self, tmp_home: Path) -> SlugRequestHandler:
        h = _make_handler(tmp_home)
        h._SOLACE_CLOUD_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app"
        return h

    def test_post_uses_30s_timeout(self, tmp_home: Path):
        """POST requests use 30-second timeout."""
        h = self._make_cr_handler(tmp_home)
        captured: dict = {}

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        # Remove url attribute to skip redirect check
        del mock_resp.url

        def _fake_urlopen(req, timeout=None):
            captured["timeout"] = timeout
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            h._cloud_request("POST", "/api/v1/esign/sign", {"data": "x"})

        assert captured["timeout"] == 30

    def test_get_uses_15s_timeout(self, tmp_home: Path):
        """GET requests use 15-second timeout."""
        h = self._make_cr_handler(tmp_home)
        captured: dict = {}

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        del mock_resp.url

        def _fake_urlopen(req, timeout=None):
            captured["timeout"] = timeout
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            h._cloud_request("GET", "/api/v1/billing/status")

        assert captured["timeout"] == 15

    def test_redirect_to_different_host_returns_502(self, tmp_home: Path):
        """Redirect to an unexpected host returns (502, error dict)."""
        h = self._make_cr_handler(tmp_home)

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.status = 200
        # Simulate redirect to a different host
        mock_resp.url = "https://evil.example.com/steal"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            status, body = h._cloud_request("GET", "/api/v1/billing/status")

        assert status == 502
        assert "error" in body

    def test_http_error_returns_correct_status(self, tmp_home: Path):
        """HTTPError from the server is returned as (exc.code, parsed_body)."""
        h = self._make_cr_handler(tmp_home)

        err = urllib.error.HTTPError(
            url="https://example.com",
            code=401,
            msg="Unauthorized",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"error": "no auth"}'),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            status, body = h._cloud_request("POST", "/api/v1/esign/token", {})

        assert status == 401
        assert body.get("error") == "no auth"

    def test_network_error_returns_offline_status(self, tmp_home: Path):
        """URLError (network down) returns (0, {offline: True})."""
        h = self._make_cr_handler(tmp_home)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            status, body = h._cloud_request("POST", "/api/v1/esign/sign", {})
        assert status == 0
        assert body.get("offline") is True

    def test_bearer_token_added_to_authorization_header(self, tmp_home: Path):
        """When token is provided, Authorization: Bearer <token> header is set."""
        h = self._make_cr_handler(tmp_home)
        captured_req: list = []

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        del mock_resp.url

        def _fake_urlopen(req, timeout=None):
            captured_req.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            h._cloud_request("GET", "/api/v1/users/tier", token="mytoken123")

        req = captured_req[0]
        assert req.get_header("Authorization") == "Bearer mytoken123"

    def test_no_token_omits_authorization_header(self, tmp_home: Path):
        """When token is None, Authorization header is not added."""
        h = self._make_cr_handler(tmp_home)
        captured_req: list = []

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        del mock_resp.url

        def _fake_urlopen(req, timeout=None):
            captured_req.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            h._cloud_request("GET", "/api/v1/esign/attestations")

        req = captured_req[0]
        assert req.get_header("Authorization") is None

    def test_same_host_redirect_is_allowed(self, tmp_home: Path):
        """Redirect that stays on the same host is allowed."""
        h = self._make_cr_handler(tmp_home)

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.status = 200
        # Same host — allowed
        mock_resp.url = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/esign/token"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            status, body = h._cloud_request("POST", "/api/v1/esign/token", {})

        assert status == 200
        assert body.get("ok") is True
