"""
Tests for Task 144 — Password Strength Checker
Browser: yinyang_server.py routes /api/v1/password-checker/*
"""
import sys
import json

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


def test_analyze_very_weak():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    h = _make_handler({"password": "abc", "url": "https://example.com/login"})
    h._handle_pwd144_analyze()
    status, data = h._responses[0]
    assert status == 201
    assert data["check"]["strength"] == "very_weak"
    assert data["check"]["check_id"].startswith("psc_")


def test_analyze_strong():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    # 16+ chars with upper, lower, digit, special -> very_strong
    h = _make_handler({"password": "Abcdefgh1234!@#$", "url": "https://example.com/login"})
    h._handle_pwd144_analyze()
    status, data = h._responses[0]
    assert status == 201
    assert data["check"]["strength"] == "very_strong"


def test_analyze_no_raw_password():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    h = _make_handler({"password": "MySecret123!", "url": "https://example.com"})
    h._handle_pwd144_analyze()
    _, data = h._responses[0]
    check = data["check"]
    assert "password_hash" in check
    assert "password" not in check
    assert len(check["password_hash"]) == 64


def test_analyze_empty_password():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    h = _make_handler({"password": "", "url": "https://example.com"})
    h._handle_pwd144_analyze()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_analyze_url_hashed():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    h = _make_handler({"password": "TestPass1!", "url": "https://login.example.com"})
    h._handle_pwd144_analyze()
    _, data = h._responses[0]
    check = data["check"]
    assert "url_hash" in check
    assert "url" not in check
    assert len(check["url_hash"]) == 64


def test_history_list():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    h1 = _make_handler({"password": "Pass123!", "url": "https://example.com"})
    h1._handle_pwd144_analyze()
    h2 = _make_handler()
    h2._handle_pwd144_history_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["history"], list)


def test_history_delete():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    h1 = _make_handler({"password": "DeleteMe1!", "url": "https://example.com"})
    h1._handle_pwd144_analyze()
    check_id = h1._responses[0][1]["check"]["check_id"]
    h2 = _make_handler()
    h2._handle_pwd144_history_delete(check_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    h3 = _make_handler()
    h3._handle_pwd144_history_list()
    _, list_data = h3._responses[0]
    assert list_data["total"] == 0


def test_history_not_found():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    h = _make_handler()
    h._handle_pwd144_history_delete("psc_notexist")
    status, data = h._responses[0]
    assert status == 404


def test_checker_stats():
    import yinyang_server as ys
    ys._PWD144_HISTORY.clear()
    h1 = _make_handler({"password": "abc", "url": "https://example.com"})
    h1._handle_pwd144_analyze()
    h2 = _make_handler({"password": "Abcdefgh1234!@#$", "url": "https://example.com"})
    h2._handle_pwd144_analyze()
    h_stats = _make_handler()
    h_stats._handle_pwd144_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert data["total_checks"] == 2
    assert "by_strength" in data
    avg = data["avg_score"]
    assert isinstance(avg, str)
    float(avg)


def test_no_port_9222_in_checker():
    import re
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0, f"Found port 9222 at positions: {matches}"
