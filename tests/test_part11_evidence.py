import hashlib
import io
import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from evidence_bundle import ALCOABundle, ComplianceStatus, RUNG_ACHIEVED


VALID_TOKEN = "a" * 64


def _bundle_sha256(bundle: dict) -> str:
    payload = dict(bundle)
    payload.pop("sha256_chain_link", None)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _make_handler(path: str, method: str = "GET", body: dict | None = None):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    headers: dict[str, str] = {"Authorization": f"Bearer {VALID_TOKEN}"}
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        headers["Content-Length"] = str(len(raw))
        handler.rfile = io.BytesIO(raw)
    handler.headers = headers
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18888)
    handler.server = type("DummyServer", (), {"session_token_sha256": VALID_TOKEN})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    return handler, captured


@pytest.fixture()
def part11_env(tmp_path, monkeypatch):
    evidence_dir = tmp_path / ".solace" / "evidence"
    monkeypatch.setattr(ys, "PART11_EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(ys, "PART11_EVIDENCE_PATH", evidence_dir / "evidence.jsonl")
    monkeypatch.setattr(ys, "PART11_CHAIN_LOCK_PATH", evidence_dir / "chain.lock")
    return evidence_dir


def test_bundle_has_all_alcoa_fields():
    bundle = ALCOABundle.create_bundle("gmail.archive", {"id": 1}, {"id": 2}, "token-1", "user-1")
    assert set(bundle["alcoa_fields"].keys()) == {
        "attributable",
        "legible",
        "contemporaneous",
        "original",
        "accurate",
        "complete",
        "consistent",
        "enduring",
        "available",
    }


def test_chain_link_is_sha256_of_prev_plus_current():
    first_bundle = ALCOABundle.create_bundle("gmail.archive", {"id": 1}, {"id": 2}, "token-1", "user-1")
    first_sha256 = _bundle_sha256(first_bundle)
    second_bundle = ALCOABundle.create_bundle(
        "linkedin.send",
        {"message": "draft"},
        {"message": "sent"},
        "token-2",
        "user-2",
        previous_bundle_sha256=first_sha256,
    )
    second_sha256 = _bundle_sha256(second_bundle)
    expected_chain_link = hashlib.sha256(f"{first_sha256}{second_sha256}".encode("utf-8")).hexdigest()
    assert second_bundle["sha256_chain_link"] == expected_chain_link


def test_verify_chain_detects_tampered_bundle():
    first_bundle = ALCOABundle.create_bundle("gmail.archive", {"id": 1}, {"id": 2}, "token-1", "user-1")
    second_bundle = ALCOABundle.create_bundle(
        "linkedin.send",
        {"message": "draft"},
        {"message": "sent"},
        "token-2",
        "user-2",
        previous_bundle_sha256=_bundle_sha256(first_bundle),
    )
    second_bundle["action_type"] = "linkedin.tampered"
    assert ALCOABundle.verify_chain([first_bundle, second_bundle]) is False


def test_compliance_non_compliant_if_missing_field():
    bundle = ALCOABundle.create_bundle("gmail.archive", {"id": 1}, {"id": 2}, "token-1", "user-1")
    del bundle["alcoa_fields"]["available"]
    assert ALCOABundle.check_compliance(bundle) == ComplianceStatus.NON_COMPLIANT


def test_evidence_stored_append_only(part11_env):
    first_handler, first_capture = _make_handler(
        "/api/v1/evidence/bundle",
        "POST",
        {
            "action_type": "gmail.archive",
            "before_state_hash": "before-one",
            "after_state_hash": "after-one",
            "oauth3_token_id": "token-1",
            "user_id": "user-1",
        },
    )
    first_handler._handle_part11_evidence_bundle_create()
    assert first_capture["status"] == 201
    first_lines = ys.PART11_EVIDENCE_PATH.read_text().splitlines()
    first_chain_lines = ys.PART11_CHAIN_LOCK_PATH.read_text().splitlines()

    second_handler, second_capture = _make_handler(
        "/api/v1/evidence/bundle",
        "POST",
        {
            "action_type": "linkedin.send",
            "before_state_hash": "before-two",
            "after_state_hash": "after-two",
            "oauth3_token_id": "token-2",
            "user_id": "user-2",
        },
    )
    second_handler._handle_part11_evidence_bundle_create()
    assert second_capture["status"] == 201

    second_lines = ys.PART11_EVIDENCE_PATH.read_text().splitlines()
    second_chain_lines = ys.PART11_CHAIN_LOCK_PATH.read_text().splitlines()
    assert len(second_lines) == len(first_lines) + 1
    assert second_lines[0] == first_lines[0]
    assert len(second_chain_lines) == len(first_chain_lines) + 1
    assert second_chain_lines[0] == first_chain_lines[0]


def test_compliance_report_counts_correctly(part11_env):
    ys.create_and_store_evidence_bundle("gmail.archive", {"id": 1}, {"id": 2}, "token-1", "user-1")
    ys.create_and_store_evidence_bundle("linkedin.send", {"id": 3}, {"id": 4}, "token-2", "")
    ys.create_and_store_evidence_bundle("slack.send", {"id": 5}, {"id": 6}, "", "user-3")

    handler, captured = _make_handler("/api/v1/evidence/compliance-report")
    handler._handle_part11_evidence_compliance_report()

    assert captured["status"] == 200
    assert captured["data"] == {
        "compliant_count": 1,
        "partial_count": 1,
        "non_compliant": 1,
        "total": 3,
        "rung": RUNG_ACHIEVED,
    }


def test_bundle_timestamp_within_1s_of_action():
    before = datetime.now(timezone.utc)
    bundle = ALCOABundle.create_bundle("gmail.archive", {"id": 1}, {"id": 2}, "token-1", "user-1")
    after = datetime.now(timezone.utc)
    bundle_timestamp = datetime.fromisoformat(bundle["timestamp_iso8601"].replace("Z", "+00:00"))
    assert abs((bundle_timestamp - before).total_seconds()) <= 1
    assert abs((after - bundle_timestamp).total_seconds()) <= 1


def test_rung_274177_in_every_bundle(part11_env):
    ys.create_and_store_evidence_bundle("gmail.archive", {"id": 1}, {"id": 2}, "token-1", "user-1")
    ys.create_and_store_evidence_bundle("linkedin.send", {"id": 3}, {"id": 4}, "token-2", "user-2")
    stored_bundles = ys._load_part11_evidence_bundles()
    assert stored_bundles
    assert all(bundle["rung_achieved"] == RUNG_ACHIEVED for bundle in stored_bundles)


def test_record_evidence_uses_active_evidence_root_for_part11_storage(tmp_path, monkeypatch):
    evidence_path = tmp_path / "evidence.jsonl"
    monkeypatch.setattr(ys, "EVIDENCE_PATH", evidence_path)
    monkeypatch.setattr(ys, "PART11_EVIDENCE_DIR", ys.DEFAULT_PART11_EVIDENCE_DIR)
    monkeypatch.setattr(ys, "PART11_EVIDENCE_PATH", ys.DEFAULT_PART11_EVIDENCE_PATH)
    monkeypatch.setattr(ys, "PART11_CHAIN_LOCK_PATH", ys.DEFAULT_PART11_CHAIN_LOCK_PATH)

    ys.record_evidence(
        "session_check",
        {
            "app": "gmail",
            "status": "unknown",
            "oauth3_token_id": "token-1",
            "user_id": "user-1",
        },
    )

    part11_dir = evidence_path.parent / "evidence"
    assert evidence_path.exists() is True
    assert (part11_dir / "evidence.jsonl").exists() is True
    assert (part11_dir / "chain.lock").exists() is True
