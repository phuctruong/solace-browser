"""Tests for Task 137 — Social Share Tracker. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-137").hexdigest()


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
    with ys._SOCIAL_LOCK:
        ys._SOCIAL_SHARES.clear()


def _make_share(**kwargs):
    base = {
        "url": "https://example.com/article",
        "title": "Great Article",
        "platform": "twitter",
        "message": "Check this out!",
    }
    base.update(kwargs)
    return base


def test_share_create():
    """POST creates share with shr_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/social-share/shares", _make_share())
    h._handle_sst_create()
    assert h._status == 201
    s = h._response["share"]
    assert s["share_id"].startswith("shr_")


def test_share_url_hashed():
    """POST stores url_hash, no raw URL."""
    _reset()
    url = "https://secret.com/article"
    h = FakeHandler("POST", "/api/v1/social-share/shares", _make_share(url=url))
    h._handle_sst_create()
    assert h._status == 201
    s = h._response["share"]
    assert "url_hash" in s
    assert s["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    assert "url" not in s


def test_share_invalid_platform():
    """POST with unknown platform returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/social-share/shares", _make_share(platform="myspace"))
    h._handle_sst_create()
    assert h._status == 400


def test_share_list():
    """GET returns list of shares."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/social-share/shares", _make_share())
    h_create._handle_sst_create()
    h = FakeHandler("GET", "/api/v1/social-share/shares")
    h._handle_sst_list()
    assert h._status == 200
    assert isinstance(h._response["shares"], list)
    assert h._response["total"] >= 1


def test_share_delete():
    """DELETE removes share."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/social-share/shares", _make_share())
    h_create._handle_sst_create()
    share_id = h_create._response["share"]["share_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/social-share/shares/{share_id}")
    h_del._handle_sst_delete(share_id)
    assert h_del._status == 200
    with ys._SOCIAL_LOCK:
        ids = [s["share_id"] for s in ys._SOCIAL_SHARES]
    assert share_id not in ids


def test_share_not_found():
    """DELETE non-existent share returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/social-share/shares/shr_notexist")
    h._handle_sst_delete("shr_notexist")
    assert h._status == 404


def test_share_stats():
    """GET /stats returns top_platform."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/social-share/shares", _make_share(platform="linkedin"))
    h_create._handle_sst_create()
    h = FakeHandler("GET", "/api/v1/social-share/stats")
    h._handle_sst_stats()
    assert h._status == 200
    assert "top_platform" in h._response
    assert h._response["top_platform"] == "linkedin"


def test_share_stats_by_platform():
    """GET /stats returns by_platform with count."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/social-share/shares", _make_share(platform="reddit"))
    h_create._handle_sst_create()
    h_create2 = FakeHandler("POST", "/api/v1/social-share/shares", _make_share(platform="reddit"))
    h_create2._handle_sst_create()
    h = FakeHandler("GET", "/api/v1/social-share/stats")
    h._handle_sst_stats()
    assert h._status == 200
    assert h._response["by_platform"].get("reddit", 0) == 2


def test_platforms_list():
    """GET /platforms returns 10 platforms."""
    _reset()
    h = FakeHandler("GET", "/api/v1/social-share/platforms")
    h._handle_sst_platforms()
    assert h._status == 200
    assert len(h._response["platforms"]) == 10


def test_no_port_9222_in_social():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
