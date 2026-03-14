# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 066 — Shortcut Manager
Browser: yinyang_server.py routes /api/v1/shortcuts/*
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


def test_shortcuts_includes_defaults():
    import yinyang_server as ys
    ys._CUSTOM_SHORTCUTS.clear()
    h = _make_handler()
    h._handle_shortcuts_list()
    status, data = h._responses[0]
    assert status == 200
    ids = [s["shortcut_id"] for s in data["shortcuts"]]
    assert "sys-001" in ids
    assert "sys-002" in ids
    assert "sys-003" in ids
    assert data["total"] >= 3


def test_shortcut_create():
    import yinyang_server as ys
    ys._CUSTOM_SHORTCUTS.clear()
    h = _make_handler({
        "keys": "Ctrl+Alt+R",
        "action": "open-recipe",
        "description": "Open recipes fast",
    })
    h._handle_shortcut_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["status"] == "created"
    assert data["shortcut"]["shortcut_id"].startswith("sc_")
    assert data["shortcut"]["keys"] == "Ctrl+Alt+R"
    assert data["shortcut"]["is_default"] is False


def test_shortcut_invalid_action():
    import yinyang_server as ys
    ys._CUSTOM_SHORTCUTS.clear()
    h = _make_handler({
        "keys": "Ctrl+X",
        "action": "not-a-valid-action",
        "description": "Bad",
    })
    h._handle_shortcut_create()
    status, data = h._responses[0]
    assert status == 400
    assert "action" in data["error"]


def test_shortcut_no_modifier_key():
    """Keys without modifier key should return 400."""
    import yinyang_server as ys
    ys._CUSTOM_SHORTCUTS.clear()
    h = _make_handler({
        "keys": "R",  # no modifier
        "action": "open-recipe",
        "description": "No modifier",
    })
    h._handle_shortcut_create()
    status, data = h._responses[0]
    assert status == 400
    assert "modifier" in data["error"].lower() or "keys" in data["error"].lower()


def test_shortcut_delete():
    import yinyang_server as ys
    ys._CUSTOM_SHORTCUTS.clear()
    h = _make_handler({
        "keys": "Shift+D",
        "action": "open-downloads",
        "description": "Downloads",
    })
    h._handle_shortcut_create()
    shortcut_id = h._responses[0][1]["shortcut"]["shortcut_id"]

    h2 = _make_handler()
    h2._handle_shortcut_delete(shortcut_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    assert len(ys._CUSTOM_SHORTCUTS) == 0


def test_shortcut_trigger():
    import yinyang_server as ys
    ys._CUSTOM_SHORTCUTS.clear()
    h = _make_handler({
        "keys": "Alt+N",
        "action": "open-notes",
        "description": "Notes",
    })
    h._handle_shortcut_create()
    shortcut_id = h._responses[0][1]["shortcut"]["shortcut_id"]

    h2 = _make_handler()
    h2._handle_shortcut_trigger(shortcut_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "triggered"
    assert data["trigger_count"] == 1


def test_shortcut_trigger_default():
    """Can trigger default shortcuts (sys-001)."""
    import yinyang_server as ys
    # Reset default trigger counts
    for s in ys.SC_DEFAULT_SHORTCUTS:
        s["trigger_count"] = 0

    h = _make_handler()
    h._handle_shortcut_trigger("sys-001")
    status, data = h._responses[0]
    assert status == 200
    assert data["status"] == "triggered"
    assert data["trigger_count"] >= 1


def test_shortcut_stats():
    import yinyang_server as ys
    ys._CUSTOM_SHORTCUTS.clear()
    h = _make_handler()
    h._handle_shortcuts_stats()
    status, data = h._responses[0]
    assert status == 200
    assert "total_shortcuts" in data
    assert "total_triggers" in data
    assert data["total_shortcuts"] >= 3  # at least the 3 defaults


def test_shortcut_html_no_cdn():
    """HTML must not reference external CDN URLs."""
    with open("/home/phuc/projects/solace-browser/web/shortcut-manager.html") as f:
        content = f.read()
    import re
    cdn_refs = re.findall(r'(?:src|href)\s*=\s*["\']https?://', content)
    assert cdn_refs == [], f"CDN references found: {cdn_refs}"


def test_no_port_9222_in_shortcuts():
    """No port 9222 references in shortcut manager files."""
    files = [
        "/home/phuc/projects/solace-browser/web/shortcut-manager.html",
        "/home/phuc/projects/solace-browser/web/js/shortcut-manager.js",
        "/home/phuc/projects/solace-browser/web/css/shortcut-manager.css",
    ]
    for path in files:
        with open(path) as f:
            content = f.read()
        assert "9222" not in content, f"Port 9222 found in {path}"
