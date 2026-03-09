"""
Tests for Task 050 — Form Autofill
Browser: yinyang_server.py routes /api/v1/autofill/*
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


def test_autofill_profiles_empty():
    import yinyang_server as ys
    ys._AUTOFILL_PROFILES.clear()
    h = _make_handler()
    h._handle_autofill_profiles_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["total"] == 0


def test_autofill_add_profile():
    import yinyang_server as ys
    ys._AUTOFILL_PROFILES.clear()
    h = _make_handler({"name": "Work", "fields": {"first_name": "Alice"}})
    h._handle_autofill_profile_add()
    status, data = h._responses[0]
    assert status == 200
    assert data["profile_id"].startswith("af_")


def test_autofill_invalid_field_key():
    import yinyang_server as ys
    ys._AUTOFILL_PROFILES.clear()
    h = _make_handler({"name": "Bad", "fields": {"bad_key": "x"}})
    h._handle_autofill_profile_add()
    status, data = h._responses[0]
    assert status == 400


def test_autofill_no_name():
    import yinyang_server as ys
    ys._AUTOFILL_PROFILES.clear()
    h = _make_handler({"name": "", "fields": {}})
    h._handle_autofill_profile_add()
    status, data = h._responses[0]
    assert status == 400


def test_autofill_no_auth_post():
    import yinyang_server as ys
    h = _make_handler({"name": "X", "fields": {}}, auth=False)
    h._handle_autofill_profile_add()
    status, data = h._responses[0]
    assert status == 401


def test_autofill_delete_profile():
    import yinyang_server as ys
    ys._AUTOFILL_PROFILES.clear()
    h1 = _make_handler({"name": "Del", "fields": {"first_name": "Bob"}})
    h1._handle_autofill_profile_add()
    pid = h1._responses[0][1]["profile_id"]
    h2 = _make_handler()
    h2._handle_autofill_profile_delete(pid)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"


def test_autofill_delete_not_found():
    h = _make_handler()
    h._handle_autofill_profile_delete("af_nonexistent_xyz")
    status, data = h._responses[0]
    assert status == 404


def test_autofill_apply_profile():
    import yinyang_server as ys
    ys._AUTOFILL_PROFILES.clear()
    ys._AUTOFILL_HISTORY.clear()
    h1 = _make_handler({"name": "Apply", "fields": {"email": "x@x.com"}})
    h1._handle_autofill_profile_add()
    pid = h1._responses[0][1]["profile_id"]
    h2 = _make_handler({"domain": "testdomain.com"})
    h2._handle_autofill_apply(pid)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "applied"


def test_autofill_history_no_raw_domain():
    import yinyang_server as ys
    ys._AUTOFILL_PROFILES.clear()
    ys._AUTOFILL_HISTORY.clear()
    h1 = _make_handler({"name": "P", "fields": {"first_name": "C"}})
    h1._handle_autofill_profile_add()
    pid = h1._responses[0][1]["profile_id"]
    h2 = _make_handler({"domain": "rawdomain.com"})
    h2._handle_autofill_apply(pid)
    h3 = _make_handler()
    h3._handle_autofill_history()
    status, data = h3._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert "rawdomain.com" not in str(data["history"])


def test_autofill_html_no_cdn():
    html = open("/home/phuc/projects/solace-browser/web/form-autofill.html").read()
    assert "cdn.jsdelivr" not in html and "unpkg.com" not in html


def test_no_port_9222_in_autofill():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    import re
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0, f"Found port 9222 at offsets: {matches}"
