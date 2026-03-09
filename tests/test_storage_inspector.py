"""
Tests for Task 056 — Storage Inspector
Browser: yinyang_server.py routes /api/v1/storage/*
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


def test_storage_summary_empty():
    import yinyang_server as ys
    ys._STORAGE_EVENTS.clear()
    h = _make_handler()
    h._handle_storage_summary()
    status, data = h._responses[0]
    assert status == 200
    summary = data["summary"]
    for t in ys.STORAGE_TYPES:
        assert t in summary
        assert summary[t]["event_count"] == 0


def test_storage_record_event():
    import yinyang_server as ys
    ys._STORAGE_EVENTS.clear()
    h = _make_handler({
        "storage_type": "localStorage",
        "domain": "example.com",
        "key": "user_pref",
        "size_bytes": 512,
    })
    h._handle_storage_record()
    status, data = h._responses[0]
    assert status == 200
    assert data["status"] == "recorded"
    assert data["event_id"].startswith("sto_")


def test_storage_domain_hashed():
    import yinyang_server as ys
    ys._STORAGE_EVENTS.clear()
    h = _make_handler({
        "storage_type": "cookies",
        "domain": "secret-domain.com",
        "key": "session",
        "size_bytes": 256,
    })
    h._handle_storage_record()
    event_id = h._responses[0][1]["event_id"]

    with ys._STORAGE_LOCK:
        ev = next(e for e in ys._STORAGE_EVENTS if e["event_id"] == event_id)
    assert "domain_hash" in ev
    assert "domain" not in ev
    assert "secret-domain.com" not in str(ev)


def test_storage_key_hashed():
    import yinyang_server as ys
    ys._STORAGE_EVENTS.clear()
    h = _make_handler({
        "storage_type": "sessionStorage",
        "domain": "example.com",
        "key": "secret_key_value",
        "size_bytes": 128,
    })
    h._handle_storage_record()
    event_id = h._responses[0][1]["event_id"]

    with ys._STORAGE_LOCK:
        ev = next(e for e in ys._STORAGE_EVENTS if e["event_id"] == event_id)
    assert "key_hash" in ev
    assert "key" not in ev or ev.get("key") != "secret_key_value"


def test_storage_invalid_type():
    import yinyang_server as ys
    ys._STORAGE_EVENTS.clear()
    h = _make_handler({
        "storage_type": "superStorage",
        "domain": "example.com",
        "key": "k",
        "size_bytes": 0,
    })
    h._handle_storage_record()
    status, data = h._responses[0]
    assert status == 400
    assert "storage_type" in data["error"]


def test_storage_by_domain():
    import yinyang_server as ys
    ys._STORAGE_EVENTS.clear()
    h1 = _make_handler({
        "storage_type": "localStorage",
        "domain": "example.com",
        "key": "key1",
        "size_bytes": 100,
    })
    h1._handle_storage_record()

    h2 = _make_handler()
    h2._handle_storage_by_domain()
    status, data = h2._responses[0]
    assert status == 200
    assert "groups" in data
    assert data["total_domains"] >= 1


def test_storage_clear():
    import yinyang_server as ys
    ys._STORAGE_EVENTS.clear()
    h1 = _make_handler({
        "storage_type": "indexedDB",
        "domain": "app.com",
        "key": "cache",
        "size_bytes": 4096,
    })
    h1._handle_storage_record()
    assert len(ys._STORAGE_EVENTS) == 1

    h2 = _make_handler()
    h2._handle_storage_clear()
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "cleared"
    assert len(ys._STORAGE_EVENTS) == 0


def test_storage_types_list():
    import yinyang_server as ys
    h = _make_handler()
    h._handle_storage_types()
    status, data = h._responses[0]
    assert status == 200
    assert "types" in data
    assert len(data["types"]) == 5
    assert "localStorage" in data["types"]
    assert "cookies" in data["types"]


def test_storage_html_no_cdn():
    html = open("/home/phuc/projects/solace-browser/web/storage-inspector.html").read()
    assert "cdn.jsdelivr" not in html
    assert "unpkg.com" not in html
    assert "cloudflare.com" not in html


def test_no_port_9222_in_storage():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    import re
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
