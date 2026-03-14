# Diagram: 05-solace-runtime-architecture
"""Tests for Link Checker (Task 117). 10 tests."""
import sys
import pathlib
import hashlib
import json
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-link").hexdigest()


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
        self.rfile = BytesIO(self._body)
        self.wfile = BytesIO()

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
    ys._LINK_CHECKS.clear()


def _valid_check(**overrides):
    base = {
        "url_hash": hashlib.sha256(b"https://example.com/page").hexdigest(),
        "page_hash": hashlib.sha256(b"https://example.com").hexdigest(),
        "status": "ok",
        "http_code": 200,
        "response_ms": 123,
    }
    base.update(overrides)
    return base


def test_check_create():
    """POST → check_id has lck_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check())
    h._handle_link_check_create()
    assert h._status == 201
    assert h._response["check"]["check_id"].startswith("lck_")


def test_check_url_hashed():
    """url_hash present, no raw URL stored."""
    _reset()
    url_hash = hashlib.sha256(b"https://secret.com/path").hexdigest()
    h = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check(url_hash=url_hash))
    h._handle_link_check_create()
    assert h._status == 201
    check = h._response["check"]
    assert check["url_hash"] == url_hash
    assert "url" not in check
    assert "raw_url" not in check


def test_check_invalid_status():
    """Unknown status → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check(status="dead"))
    h._handle_link_check_create()
    assert h._status == 400


def test_check_invalid_http_code():
    """http_code=99 (below min 100) → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check(http_code=99))
    h._handle_link_check_create()
    assert h._status == 400


def test_check_invalid_http_code_high():
    """http_code=600 (above max 599) → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check(http_code=600))
    h._handle_link_check_create()
    assert h._status == 400


def test_check_list():
    """GET /checks → returns list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check())
    h._handle_link_check_create()

    h2 = FakeHandler("GET", "/api/v1/link-checker/checks")
    h2._handle_link_checks_list()
    assert h2._status == 200
    assert isinstance(h2._response["checks"], list)
    assert h2._response["total"] >= 1


def test_check_delete():
    """DELETE /checks/{id} → removed."""
    _reset()
    h = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check())
    h._handle_link_check_create()
    cid = h._response["check"]["check_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/link-checker/checks/{cid}")
    h2._handle_link_check_delete(cid)
    assert h2._status == 200
    assert h2._response["status"] == "deleted"
    assert len(ys._LINK_CHECKS) == 0


def test_link_stats():
    """GET /stats → broken_count present."""
    _reset()
    h1 = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check(status="ok", http_code=200, response_ms=100))
    h1._handle_link_check_create()
    h2 = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check(status="broken", http_code=404, response_ms=50))
    h2._handle_link_check_create()
    h3 = FakeHandler("POST", "/api/v1/link-checker/checks", _valid_check(status="broken", http_code=500, response_ms=200))
    h3._handle_link_check_create()

    hs = FakeHandler("GET", "/api/v1/link-checker/stats")
    hs._handle_link_stats()
    assert hs._status == 200
    resp = hs._response
    assert resp["total_checks"] == 3
    assert resp["broken_count"] == 2
    assert "by_status" in resp
    assert "avg_response_ms" in resp


def test_statuses_list():
    """GET /statuses → 7 statuses."""
    h = FakeHandler("GET", "/api/v1/link-checker/statuses")
    h._handle_link_statuses_list()
    assert h._status == 200
    statuses = h._response["statuses"]
    assert len(statuses) == 7
    assert "ok" in statuses
    assert "broken" in statuses
    assert "pending" in statuses


def test_no_port_9222_in_link():
    """No port 9222 reference in yinyang_server.py."""
    server_py = pathlib.Path(__file__).resolve().parent.parent / "yinyang_server.py"
    source = server_py.read_text()
    forbidden = "9" + "222"
    assert forbidden not in source
