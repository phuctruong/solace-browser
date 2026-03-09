"""
Tests for Task 154 — Browser Shortcuts Manager
Browser: yinyang_server.py routes /api/v1/shortcuts/*
"""
import sys
import json
import re

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


def _valid_body(**overrides):
    base = {
        "action_type": "navigate_url",
        "key_combo": "ctrl+shift+g",
        "description": "Navigate to bookmarks",
        "is_enabled": True,
    }
    base.update(overrides)
    return base


def test_shortcut_create():
    import yinyang_server as ys
    ys._SHORTCUTS.clear()
    h = _make_handler(_valid_body())
    h._handle_shc_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["shortcut_id"].startswith("shc_")


def test_shortcut_invalid_action():
    import yinyang_server as ys
    ys._SHORTCUTS.clear()
    h = _make_handler(_valid_body(action_type="unknown_action"))
    h._handle_shc_create()
    status, data = h._responses[0]
    assert status == 400


def test_shortcut_invalid_key_combo():
    import yinyang_server as ys
    ys._SHORTCUTS.clear()
    h = _make_handler(_valid_body(key_combo="ctrlshiftg"))  # no "+"
    h._handle_shc_create()
    status, data = h._responses[0]
    assert status == 400


def test_shortcut_description_too_long():
    import yinyang_server as ys
    ys._SHORTCUTS.clear()
    long_desc = "x" * 201
    h = _make_handler(_valid_body(description=long_desc))
    h._handle_shc_create()
    status, data = h._responses[0]
    assert status == 400


def test_shortcut_list():
    import yinyang_server as ys
    ys._SHORTCUTS.clear()
    h1 = _make_handler(_valid_body(key_combo="ctrl+k", description="Open search"))
    h1._handle_shc_create()
    h2 = _make_handler()
    h2._handle_shc_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["shortcuts"], list)


def test_shortcut_delete():
    import yinyang_server as ys
    ys._SHORTCUTS.clear()
    h1 = _make_handler(_valid_body(key_combo="ctrl+d", description="Bookmark page"))
    h1._handle_shc_create()
    shc_id = h1._responses[0][1]["shortcut_id"]
    h2 = _make_handler()
    h2._handle_shc_delete(shc_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    with ys._SHORTCUTS_LOCK:
        assert not any(s["shortcut_id"] == shc_id for s in ys._SHORTCUTS)


def test_shortcut_not_found():
    import yinyang_server as ys
    ys._SHORTCUTS.clear()
    h = _make_handler()
    h._handle_shc_delete("shc_notexist")
    status, data = h._responses[0]
    assert status == 404


def test_shortcut_stats():
    import yinyang_server as ys
    ys._SHORTCUTS.clear()
    for i, at in enumerate(["navigate_url", "open_tab", "search"]):
        h = _make_handler(_valid_body(action_type=at, key_combo=f"ctrl+{i+1}"))
        h._handle_shc_create()
    h_stats = _make_handler()
    h_stats._handle_shc_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert "enabled_count" in data
    assert "by_action_type" in data
    assert data["total_shortcuts"] == 3
    assert data["enabled_count"] == 3


def test_action_types_list():
    import yinyang_server as ys
    h = _make_handler()
    h._handle_shc_action_types()
    status, data = h._responses[0]
    assert status == 200
    assert "action_types" in data
    assert len(data["action_types"]) == 12


def test_no_port_9222_in_shortcuts():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
