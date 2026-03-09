"""
Tests for Task 062 — Cookie Manager
Browser: yinyang_server.py routes /api/v1/cookies/*
"""
import json
import sys

sys.path.insert(0, "/home/phuc/projects/solace-browser")

TOKEN = "test-token-sha256"


def _make_handler(body=None, auth=True):
    import yinyang_server as ys

    class FakeHandler(ys.YinyangHandler):
        def __init__(self):
            self._token = TOKEN
            self._responses = []
            self._body = json.dumps(body).encode() if body else b"{}"

        def _read_json_body(self):
            return json.loads(self._body)

        def _send_json(self, data, status=200):
            self._responses.append((status, data))

        def _check_auth(self):
            if not auth:
                self._send_json({"error": "unauthorized"}, 401)
                return False
            return True

    return FakeHandler()


def test_cookies_summary_empty():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    h = _make_handler()
    h._handle_cookies_summary()
    status, data = h._responses[0]
    assert status == 200
    assert data["total"] == 0
    for cat in ys.COOKIE_CATEGORIES:
        assert cat in data["by_category"]
        assert data["by_category"][cat] == 0


def test_cookie_record_ok():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    dh = "a" * 64
    nh = "b" * 64
    h = _make_handler({
        "domain_hash": dh, "name_hash": nh,
        "category": "analytics", "same_site": "Lax",
        "is_secure": True, "is_httponly": False,
    })
    h._handle_cookie_record()
    status, data = h._responses[0]
    assert status == 201
    assert data["record"]["record_id"].startswith("ck_")
    assert data["record"]["category"] == "analytics"
    assert data["record"]["same_site"] == "Lax"


def test_cookie_record_invalid_category():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    h = _make_handler({
        "domain_hash": "c" * 64, "name_hash": "d" * 64,
        "category": "tracking", "same_site": "Strict",
    })
    h._handle_cookie_record()
    status, data = h._responses[0]
    assert status == 400
    assert "category" in data["error"]


def test_cookie_record_invalid_same_site():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    h = _make_handler({
        "domain_hash": "e" * 64, "name_hash": "f" * 64,
        "category": "essential", "same_site": "Bogus",
    })
    h._handle_cookie_record()
    status, data = h._responses[0]
    assert status == 400
    assert "same_site" in data["error"]


def test_cookie_record_requires_auth():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    h = _make_handler({
        "domain_hash": "0" * 64, "name_hash": "1" * 64,
        "category": "essential", "same_site": "None",
    }, auth=False)
    h._handle_cookie_record()
    status, _ = h._responses[0]
    assert status == 401


def test_cookies_by_domain():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    dh = "9" * 64
    h = _make_handler({
        "domain_hash": dh, "name_hash": "8" * 64,
        "category": "marketing", "same_site": "None",
    })
    h._handle_cookie_record()

    h2 = _make_handler()
    h2._handle_cookies_by_domain()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total_domains"] >= 1
    assert any(d["domain_hash"] == dh for d in data["domains"])


def test_cookie_categories_list():
    import yinyang_server as ys
    h = _make_handler()
    h._handle_cookie_categories()
    status, data = h._responses[0]
    assert status == 200
    assert "categories" in data
    assert "analytics" in data["categories"]
    assert "essential" in data["categories"]


def test_cookies_clear_ok():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    h = _make_handler({
        "domain_hash": "7" * 64, "name_hash": "6" * 64,
        "category": "social", "same_site": "Strict",
    })
    h._handle_cookie_record()

    h2 = _make_handler()
    h2._handle_cookies_clear()
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "cleared"
    assert data["count"] >= 1
    assert len(ys._COOKIE_RECORDS) == 0


def test_cookie_domain_hash_must_be_64():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    h = _make_handler({
        "domain_hash": "short", "name_hash": "5" * 64,
        "category": "preferences", "same_site": "Lax",
    })
    h._handle_cookie_record()
    status, data = h._responses[0]
    assert status == 400
    assert "domain_hash" in data["error"]


def test_cookie_name_hash_must_be_64():
    import yinyang_server as ys
    ys._COOKIE_RECORDS.clear()
    h = _make_handler({
        "domain_hash": "4" * 64, "name_hash": "x",
        "category": "preferences", "same_site": "Lax",
    })
    h._handle_cookie_record()
    status, data = h._responses[0]
    assert status == 400
    assert "name_hash" in data["error"]
