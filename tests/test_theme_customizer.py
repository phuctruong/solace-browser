# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 057 — Theme Customizer
Browser: yinyang_server.py routes /api/v1/theme/customizer/*
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


def test_theme_get_default():
    import yinyang_server as ys
    # Reset to default
    with ys._THEME_CUSTOMIZER_LOCK:
        ys._CURRENT_THEME_CUSTOMIZER.clear()
        ys._CURRENT_THEME_CUSTOMIZER.update(ys.DEFAULT_THEME_CUSTOMIZER)

    h = _make_handler()
    h._handle_theme_customizer_get()
    status, data = h._responses[0]
    assert status == 200
    assert "accent_color" in data
    assert "font_size" in data


def test_theme_update():
    import yinyang_server as ys
    with ys._THEME_CUSTOMIZER_LOCK:
        ys._CURRENT_THEME_CUSTOMIZER.clear()
        ys._CURRENT_THEME_CUSTOMIZER.update(ys.DEFAULT_THEME_CUSTOMIZER)

    h = _make_handler({"accent_color": "#FF0000", "font_size": "lg"})
    h._handle_theme_customizer_set()
    status, data = h._responses[0]
    assert status == 200
    assert data["status"] == "updated"
    assert data["theme"]["accent_color"] == "#FF0000"
    assert data["theme"]["font_size"] == "lg"


def test_theme_invalid_font_size():
    import yinyang_server as ys
    h = _make_handler({"font_size": "huge"})
    h._handle_theme_customizer_set()
    status, data = h._responses[0]
    assert status == 400
    assert "font_size" in data["error"]


def test_theme_reset():
    import yinyang_server as ys
    # First update it
    with ys._THEME_CUSTOMIZER_LOCK:
        ys._CURRENT_THEME_CUSTOMIZER["accent_color"] = "#DEADBE"

    h = _make_handler()
    h._handle_theme_customizer_reset()
    status, data = h._responses[0]
    assert status == 200
    assert data["status"] == "reset"
    assert data["theme"]["accent_color"] == ys.DEFAULT_THEME_CUSTOMIZER["accent_color"]


def test_theme_presets_list():
    import yinyang_server as ys
    h = _make_handler()
    h._handle_theme_customizer_presets()
    status, data = h._responses[0]
    assert status == 200
    assert "presets" in data
    assert data["total"] == 3
    preset_ids = [p["preset_id"] for p in data["presets"]]
    assert "solace-light" in preset_ids
    assert "solace-dark" in preset_ids


def test_theme_apply_preset():
    import yinyang_server as ys
    with ys._THEME_CUSTOMIZER_LOCK:
        ys._CURRENT_THEME_CUSTOMIZER.clear()
        ys._CURRENT_THEME_CUSTOMIZER.update(ys.DEFAULT_THEME_CUSTOMIZER)

    h = _make_handler()
    h._handle_theme_customizer_apply_preset("solace-dark")
    status, data = h._responses[0]
    assert status == 200
    assert data["status"] == "applied"
    assert data["theme"]["preset_id"] == "solace-dark"
    assert data["theme"]["accent_color"] == "#7B61FF"


def test_theme_apply_invalid_preset():
    import yinyang_server as ys
    h = _make_handler()
    h._handle_theme_customizer_apply_preset("nonexistent-preset")
    status, data = h._responses[0]
    assert status == 404
    assert "preset not found" in data["error"]


def test_theme_html_no_cdn():
    html = open("/home/phuc/projects/solace-browser/web/theme-customizer.html").read()
    assert "cdn.jsdelivr" not in html
    assert "unpkg.com" not in html
    assert "cloudflare.com" not in html


def test_theme_js_no_eval():
    js = open("/home/phuc/projects/solace-browser/web/js/theme-customizer.js").read()
    import re
    # eval() must not appear as a function call
    assert not re.search(r'\beval\s*\(', js)


def test_no_port_9222_in_theme():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    import re
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
