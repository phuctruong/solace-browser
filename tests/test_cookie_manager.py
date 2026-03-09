"""Tests for Task 148 — Cookie Manager. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-148").hexdigest()


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
    with ys._COOKIE_MGR_LOCK:
        ys._COOKIE_MGR_RECORDS.clear()


def _make_cookie(**kwargs):
    base = {
        "domain": "example.com",
        "name": "_ga",
        "category": "analytics",
        "is_secure": True,
        "is_httponly": False,
        "is_session": False,
        "expires_days": 365,
    }
    base.update(kwargs)
    return base


def test_cookie_create():
    """POST creates cookie record with ckm_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie())
    h._handle_ckm_create()
    assert h._status == 201
    c = h._response["cookie"]
    assert c["cookie_id"].startswith("ckm_")


def test_cookie_domain_hashed():
    """POST stores domain_hash, raw domain never stored."""
    _reset()
    domain = "secret-site.com"
    h = FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie(domain=domain))
    h._handle_ckm_create()
    assert h._status == 201
    c = h._response["cookie"]
    assert "domain_hash" in c
    assert c["domain_hash"] == hashlib.sha256(domain.encode()).hexdigest()
    assert "domain" not in c


def test_cookie_name_hashed():
    """POST stores name_hash, raw name never stored."""
    _reset()
    name = "secret_cookie_name"
    h = FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie(name=name))
    h._handle_ckm_create()
    assert h._status == 201
    c = h._response["cookie"]
    assert "name_hash" in c
    assert c["name_hash"] == hashlib.sha256(name.encode()).hexdigest()
    assert "name" not in c


def test_cookie_invalid_category():
    """POST with unknown category returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie(category="tracking"))
    h._handle_ckm_create()
    assert h._status == 400


def test_cookie_negative_expires():
    """POST with expires_days=-1 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie(expires_days=-1))
    h._handle_ckm_create()
    assert h._status == 400


def test_cookie_privacy_score():
    """POST with advertising category sets privacy_score=2."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie(category="advertising"))
    h._handle_ckm_create()
    assert h._status == 201
    assert h._response["cookie"]["privacy_score"] == 2


def test_cookie_list():
    """GET returns list of cookies."""
    _reset()
    FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie())._handle_ckm_create()
    h = FakeHandler("GET", "/api/v1/cookie-manager/cookies")
    h._handle_ckm_list()
    assert h._status == 200
    assert isinstance(h._response["cookies"], list)
    assert h._response["total"] >= 1


def test_cookie_delete():
    """DELETE removes cookie record."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie())
    h_create._handle_ckm_create()
    cookie_id = h_create._response["cookie"]["cookie_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/cookie-manager/cookies/{cookie_id}")
    h_del._handle_ckm_delete(cookie_id)
    assert h_del._status == 200
    with ys._COOKIE_MGR_LOCK:
        ids = [c["cookie_id"] for c in ys._COOKIE_MGR_RECORDS]
    assert cookie_id not in ids


def test_cookie_stats():
    """GET /stats returns avg_privacy_score as Decimal string."""
    _reset()
    FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie(category="essential"))._handle_ckm_create()
    FakeHandler("POST", "/api/v1/cookie-manager/cookies", _make_cookie(category="advertising"))._handle_ckm_create()
    h = FakeHandler("GET", "/api/v1/cookie-manager/stats")
    h._handle_ckm_stats()
    assert h._status == 200
    r = h._response
    assert "avg_privacy_score" in r
    assert "." in r["avg_privacy_score"]  # Decimal format
    assert r["total_cookies"] == 2
    assert r["tracking_cookie_count"] == 1  # advertising counts as tracking


def test_no_port_9222_in_cookie_manager():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
