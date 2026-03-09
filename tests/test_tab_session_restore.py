"""tests/test_tab_session_restore.py — Task 127: Tab Session Restore | 10 tests"""
import sys
import json
import hashlib
import subprocess

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass


def make_handler():
    h = FakeHandler()
    ys._TAB_SESSIONS.clear()
    ys._RESTORE_LOG.clear()
    return h


def create_session(h, session_name="My Session", tab_count=3, tag="work"):
    h._body = json.dumps({
        "session_name": session_name,
        "tab_count": tab_count,
        "tag": tag,
        "tab_urls": ["https://a.com", "https://b.com", "https://c.com"],
    }).encode()
    h._handle_tab_session_create()
    return h._responses[-1]


def test_session_create():
    h = make_handler()
    code, data = create_session(h)
    assert code == 201
    assert data["session"]["session_id"].startswith("tbs_")


def test_session_name_hashed():
    h = make_handler()
    name = "My Private Session"
    code, data = create_session(h, session_name=name)
    assert code == 201
    sess = data["session"]
    expected = hashlib.sha256(name.encode()).hexdigest()
    assert sess["session_name_hash"] == expected
    assert name not in str(sess)


def test_session_invalid_tag():
    h = make_handler()
    h._body = json.dumps({"session_name": "x", "tab_count": 2, "tag": "invalid_tag"}).encode()
    h._handle_tab_session_create()
    code, data = h._responses[-1]
    assert code == 400


def test_session_zero_tabs():
    h = make_handler()
    h._body = json.dumps({"session_name": "x", "tab_count": 0, "tag": "work"}).encode()
    h._handle_tab_session_create()
    code, data = h._responses[-1]
    assert code == 400


def test_session_list():
    h = make_handler()
    create_session(h, session_name="S1")
    create_session(h, session_name="S2")
    h2 = FakeHandler()
    h2._handle_tab_sessions_list()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] == 2


def test_session_delete():
    h = make_handler()
    code, created = create_session(h)
    session_id = created["session"]["session_id"]
    h2 = FakeHandler()
    h2._handle_tab_session_delete(session_id)
    code2, data2 = h2._responses[-1]
    assert code2 == 200
    assert data2["session_id"] == session_id
    assert len(ys._TAB_SESSIONS) == 0


def test_session_restore():
    h = make_handler()
    _, created = create_session(h)
    session_id = created["session"]["session_id"]
    h2 = FakeHandler()
    h2._handle_tab_session_restore(session_id)
    code, data = h2._responses[-1]
    assert code == 201
    assert data["restore"]["restore_id"].startswith("tbr_")
    sess = next(s for s in ys._TAB_SESSIONS if s["session_id"] == session_id)
    assert sess["restore_count"] == 1


def test_session_restore_not_found():
    h = make_handler()
    h._handle_tab_session_restore("tbs_notexist")
    code, data = h._responses[-1]
    assert code == 404


def test_session_stats():
    h = make_handler()
    create_session(h, tab_count=4, tag="work")
    create_session(h, tab_count=6, tag="research")
    h2 = FakeHandler()
    h2._handle_tab_sessions_stats()
    code, data = h2._responses[-1]
    assert code == 200
    # avg_tab_count should be a Decimal string
    avg = data["avg_tab_count"]
    assert "." in avg, f"expected decimal string, got {avg!r}"
    assert float(avg) == 5.0
    assert "work" in data["by_tag"]
    assert "research" in data["by_tag"]


def test_no_port_9222_in_tab():
    result = subprocess.run(
        ["grep", "-c", "9222", "/home/phuc/projects/solace-browser/yinyang_server.py"],
        capture_output=True, text=True
    )
    count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
    assert count == 0, f"Found {count} occurrences of 9222 in yinyang_server.py"
