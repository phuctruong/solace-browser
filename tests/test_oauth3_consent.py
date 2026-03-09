"""tests/test_oauth3_consent.py — OAuth3 Consent UI acceptance gate.
Task 024 | Rung 641 | 10 tests minimum

Tests:
  1. test_oauth3_pending_empty_initially
  2. test_oauth3_consented_empty_initially
  3. test_oauth3_approve_creates_grant
  4. test_oauth3_reject_removes_from_pending
  5. test_oauth3_revoke_deactivates_grant
  6. test_oauth3_scope_restriction_honored
  7. test_oauth3_invalid_scope_rejected
  8. test_oauth3_consent_html_no_cdn
  9. test_oauth3_consent_js_no_eval
  10. test_no_port_9222_in_oauth3_consent
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VALID_TOKEN = "c" * 64  # distinct from other test files


def _req(base, path, method="GET", payload=None, token=VALID_TOKEN):
    url = base + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


@pytest.fixture(scope="module")
def consent_server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("consent")
    import yinyang_server as ys
    # Reset module-level state for isolation
    with ys._OAUTH3_CONSENT_LOCK:
        ys._OAUTH3_PENDING.clear()
        ys._OAUTH3_GRANTS.clear()
    httpd = ys.build_server(0, str(tmp_path), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://localhost:{httpd.server_port}"
    for _ in range(30):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)
    yield base
    httpd.shutdown()


def _clear_state():
    """Reset in-memory state between tests."""
    import yinyang_server as ys
    with ys._OAUTH3_CONSENT_LOCK:
        ys._OAUTH3_PENDING.clear()
        ys._OAUTH3_GRANTS.clear()


# ---------------------------------------------------------------------------
# 1. GET /api/v1/oauth3/pending → [] initially
# ---------------------------------------------------------------------------
def test_oauth3_pending_empty_initially(consent_server):
    _clear_state()
    status, data = _req(consent_server, "/api/v1/oauth3/pending")
    assert status == 200
    assert data["pending"] == []
    assert data["count"] == 0


# ---------------------------------------------------------------------------
# 2. GET /api/v1/oauth3/consented → [] initially
# ---------------------------------------------------------------------------
def test_oauth3_consented_empty_initially(consent_server):
    _clear_state()
    status, data = _req(consent_server, "/api/v1/oauth3/consented")
    assert status == 200
    assert data["grants"] == []
    assert data["count"] == 0


# ---------------------------------------------------------------------------
# 3. POST /approve → grant appears in /consented
# ---------------------------------------------------------------------------
def test_oauth3_approve_creates_grant(consent_server):
    _clear_state()
    # Create a pending request
    status, pending = _req(
        consent_server,
        "/api/v1/oauth3/pending",
        method="POST",
        payload={
            "app_name": "TestApp",
            "requested_scopes": ["gmail:read", "calendar:read"],
        },
    )
    assert status == 201
    request_id = pending["request_id"]

    # Approve it
    status, grant = _req(
        consent_server,
        f"/api/v1/oauth3/consent/{request_id}/approve",
        method="POST",
        payload={"approved_scopes": ["gmail:read", "calendar:read"]},
    )
    assert status == 201
    assert grant["is_active"] is True
    assert grant["app_name"] == "TestApp"

    # Verify it appears in /consented
    status, data = _req(consent_server, "/api/v1/oauth3/consented")
    assert status == 200
    assert any(g["grant_id"] == grant["grant_id"] for g in data["grants"])


# ---------------------------------------------------------------------------
# 4. POST /reject → request removed from /pending
# ---------------------------------------------------------------------------
def test_oauth3_reject_removes_from_pending(consent_server):
    _clear_state()
    # Create a pending request
    status, pending = _req(
        consent_server,
        "/api/v1/oauth3/pending",
        method="POST",
        payload={
            "app_name": "RejectApp",
            "requested_scopes": ["browser:navigate"],
        },
    )
    assert status == 201
    request_id = pending["request_id"]

    # Reject it
    status, data = _req(
        consent_server,
        f"/api/v1/oauth3/consent/{request_id}/reject",
        method="POST",
        payload={"reason": "not needed"},
    )
    assert status == 200
    assert data["rejected"] is True

    # Verify it is gone from /pending
    status, pending_data = _req(consent_server, "/api/v1/oauth3/pending")
    assert status == 200
    ids = [r["request_id"] for r in pending_data["pending"]]
    assert request_id not in ids


# ---------------------------------------------------------------------------
# 5. DELETE /consented/{grant_id} → is_active becomes False
# ---------------------------------------------------------------------------
def test_oauth3_revoke_deactivates_grant(consent_server):
    _clear_state()
    # Create and approve
    status, pending = _req(
        consent_server,
        "/api/v1/oauth3/pending",
        method="POST",
        payload={
            "app_name": "RevokeApp",
            "requested_scopes": ["recipes:read"],
        },
    )
    assert status == 201
    request_id = pending["request_id"]

    status, grant = _req(
        consent_server,
        f"/api/v1/oauth3/consent/{request_id}/approve",
        method="POST",
        payload={},
    )
    assert status == 201
    grant_id = grant["grant_id"]

    # Revoke
    status, data = _req(
        consent_server,
        f"/api/v1/oauth3/consented/{grant_id}",
        method="DELETE",
    )
    assert status == 200
    assert data["revoked"] is True

    # Verify not in active grants
    status, grants_data = _req(consent_server, "/api/v1/oauth3/consented")
    assert status == 200
    active_ids = [g["grant_id"] for g in grants_data["grants"]]
    assert grant_id not in active_ids


# ---------------------------------------------------------------------------
# 6. scope restriction honored — approve with subset only
# ---------------------------------------------------------------------------
def test_oauth3_scope_restriction_honored(consent_server):
    _clear_state()
    # Request 2 scopes
    status, pending = _req(
        consent_server,
        "/api/v1/oauth3/pending",
        method="POST",
        payload={
            "app_name": "ScopeApp",
            "requested_scopes": ["gmail:read", "gmail:write"],
        },
    )
    assert status == 201
    request_id = pending["request_id"]

    # Approve only the read scope
    status, grant = _req(
        consent_server,
        f"/api/v1/oauth3/consent/{request_id}/approve",
        method="POST",
        payload={"approved_scopes": ["gmail:read"]},
    )
    assert status == 201
    assert grant["approved_scopes"] == ["gmail:read"]
    assert "gmail:write" not in grant["approved_scopes"]


# ---------------------------------------------------------------------------
# 7. invalid scope → 400
# ---------------------------------------------------------------------------
def test_oauth3_invalid_scope_rejected(consent_server):
    _clear_state()
    status, data = _req(
        consent_server,
        "/api/v1/oauth3/pending",
        method="POST",
        payload={
            "app_name": "BadScopeApp",
            "requested_scopes": ["gmail:read", "admin:delete_everything"],
        },
    )
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 8. web/oauth3-consent.html — no CDN references
# ---------------------------------------------------------------------------
def test_oauth3_consent_html_no_cdn(consent_server):
    html_path = PROJECT_ROOT / "web" / "oauth3-consent.html"
    assert html_path.exists(), "oauth3-consent.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "unpkg.com",
        "ajax.googleapis.com",
        "stackpath.bootstrapcdn.com",
        "maxcdn.bootstrapcdn.com",
    ]
    for pattern in cdn_patterns:
        assert pattern not in content, f"CDN reference found: {pattern}"


# ---------------------------------------------------------------------------
# 9. web/js/oauth3-consent.js — no eval()
# ---------------------------------------------------------------------------
def test_oauth3_consent_js_no_eval(consent_server):
    js_path = PROJECT_ROOT / "web" / "js" / "oauth3-consent.js"
    assert js_path.exists(), "oauth3-consent.js must exist"
    content = js_path.read_text()
    # Check for eval() calls — allow the word in comments explaining why it's banned
    import re
    # Find actual eval( calls, not in comments
    lines = content.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        assert "eval(" not in line, f"eval() found in JS: {line!r}"


# ---------------------------------------------------------------------------
# 10. no port 9222 anywhere in the consent files
# ---------------------------------------------------------------------------
def test_no_port_9222_in_oauth3_consent(consent_server):
    files_to_check = [
        PROJECT_ROOT / "web" / "oauth3-consent.html",
        PROJECT_ROOT / "web" / "js" / "oauth3-consent.js",
        PROJECT_ROOT / "web" / "css" / "oauth3-consent.css",
    ]
    for fpath in files_to_check:
        assert fpath.exists(), f"{fpath.name} must exist"
        content = fpath.read_text()
        assert "9222" not in content, f"Port 9222 found in {fpath.name}"
