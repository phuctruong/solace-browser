# Diagram: 05-solace-runtime-architecture
"""Tests for Task 147 — Link Health Checker. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-147").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method, path, body=None, auth=True):
        self.command = method
        self.path = path
        self._body = json.dumps(body).encode() if body else b""
        self._auth = auth
        self._status = None
        self._response = None
        self.headers = {
            "Content-Length": str(len(self._body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.server = type("S", (), {
            "session_token_sha256": VALID_TOKEN,
            "repo_root": str(REPO_ROOT),
        })()

    def send_response(self, code):
        self._status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, code=200):
        self._status = code
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def _reset():
    with ys._LINK_HEALTH_LOCK:
        ys._LINK_HEALTH_CHECKS.clear()


def _make_check(**kwargs):
    base = {
        "url": "https://example.com/page",
        "page_url": "https://referrer.com/page",
        "status_code": 200,
        "response_ms": 123,
    }
    base.update(kwargs)
    return base


def test_check_create():
    """POST creates check with lhc_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-health/checks", _make_check())
    h._handle_lhc_create()
    assert h._status == 201
    c = h._response["check"]
    assert c["check_id"].startswith("lhc_")


def test_check_url_hashed():
    """POST stores url_hash, raw URL never stored."""
    _reset()
    url = "https://secret-link.com/target"
    h = FakeHandler("POST", "/api/v1/link-health/checks", _make_check(url=url))
    h._handle_lhc_create()
    assert h._status == 201
    c = h._response["check"]
    assert "url_hash" in c
    assert c["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    assert "url" not in c


def test_check_invalid_status():
    """POST with status_code not in LINK_STATUS_CODES returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-health/checks", _make_check(status_code=418))
    h._handle_lhc_create()
    assert h._status == 400


def test_check_negative_response():
    """POST with response_ms=-1 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-health/checks", _make_check(response_ms=-1))
    h._handle_lhc_create()
    assert h._status == 400


def test_check_broken_flag():
    """POST with status_code=404 sets is_broken=True."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-health/checks", _make_check(status_code=404))
    h._handle_lhc_create()
    assert h._status == 201
    assert h._response["check"]["is_broken"] is True


def test_check_healthy_flag():
    """POST with status_code=200 sets is_broken=False."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-health/checks", _make_check(status_code=200))
    h._handle_lhc_create()
    assert h._status == 201
    assert h._response["check"]["is_broken"] is False


def test_check_list():
    """GET returns list of checks."""
    _reset()
    FakeHandler("POST", "/api/v1/link-health/checks", _make_check())._handle_lhc_create()
    h = FakeHandler("GET", "/api/v1/link-health/checks")
    h._handle_lhc_list()
    assert h._status == 200
    assert isinstance(h._response["checks"], list)
    assert h._response["total"] >= 1


def test_check_delete():
    """DELETE removes check."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/link-health/checks", _make_check())
    h_create._handle_lhc_create()
    check_id = h_create._response["check"]["check_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/link-health/checks/{check_id}")
    h_del._handle_lhc_delete(check_id)
    assert h_del._status == 200
    with ys._LINK_HEALTH_LOCK:
        ids = [c["check_id"] for c in ys._LINK_HEALTH_CHECKS]
    assert check_id not in ids


def test_link_stats():
    """GET /stats returns broken_rate as Decimal string."""
    _reset()
    FakeHandler("POST", "/api/v1/link-health/checks", _make_check(status_code=200))._handle_lhc_create()
    FakeHandler("POST", "/api/v1/link-health/checks", _make_check(status_code=404))._handle_lhc_create()
    h = FakeHandler("GET", "/api/v1/link-health/stats")
    h._handle_lhc_stats()
    assert h._status == 200
    r = h._response
    assert "broken_rate" in r
    assert "." in r["broken_rate"]  # Decimal format
    assert r["broken_count"] == 1
    assert r["healthy_count"] == 1
    assert r["total_checks"] == 2


def test_no_port_9222_in_link_health():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
