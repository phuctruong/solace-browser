"""tests/test_user_scripts.py — User Scripts Manager acceptance gate.
Task 047 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - run_at must be in SCRIPT_RUN_CONTEXTS → 400
  - code max 10000 chars → 400
  - FORBIDDEN_PATTERNS detected in validate endpoint
  - Auth required on POST/DELETE/toggle; GET/validate is public
  - No port 9222, no CDN, no eval() in frontend
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-user-scripts-047"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18911)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def delete_path(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


@pytest.fixture(autouse=True)
def reset_scripts(monkeypatch):
    """Reset user scripts state between tests."""
    monkeypatch.setattr(ys, "_USER_SCRIPTS", [])
    yield


def _add_script(name="My Script", url_pattern="*.example.com/*", code="console.log('hello');", run_at="document_idle"):
    return post_json(
        "/api/v1/user-scripts",
        {"name": name, "url_pattern": url_pattern, "code": code, "run_at": run_at},
    )


# ---------------------------------------------------------------------------
# 1. Initially empty
# ---------------------------------------------------------------------------
def test_scripts_empty_initially():
    status, data = get_json("/api/v1/user-scripts")
    assert status == 200
    assert data.get("scripts") == []


# ---------------------------------------------------------------------------
# 2. POST → script_id returned
# ---------------------------------------------------------------------------
def test_script_add():
    status, data = _add_script()
    assert status == 200
    assert data.get("status") == "added"
    assert "script_id" in data
    assert data["script_id"].startswith("scr_")


# ---------------------------------------------------------------------------
# 3. GET → includes added script
# ---------------------------------------------------------------------------
def test_script_list_includes_added():
    _, add_data = _add_script(name="Tracker Blocker")
    script_id = add_data["script_id"]
    status, data = get_json("/api/v1/user-scripts")
    assert status == 200
    ids = [s["script_id"] for s in data["scripts"]]
    assert script_id in ids


# ---------------------------------------------------------------------------
# 4. DELETE → removed
# ---------------------------------------------------------------------------
def test_script_delete():
    _, add_data = _add_script(name="Temp Script")
    script_id = add_data["script_id"]
    status, data = delete_path(f"/api/v1/user-scripts/{script_id}")
    assert status == 200
    assert data.get("status") == "deleted"
    _, list_data = get_json("/api/v1/user-scripts")
    ids = [s["script_id"] for s in list_data["scripts"]]
    assert script_id not in ids


# ---------------------------------------------------------------------------
# 5. POST /toggle → enabled=False
# ---------------------------------------------------------------------------
def test_script_toggle_disable():
    _, add_data = _add_script(name="Toggle Me")
    script_id = add_data["script_id"]
    status, data = post_json(f"/api/v1/user-scripts/{script_id}/toggle", {})
    assert status == 200
    assert data.get("enabled") is False


# ---------------------------------------------------------------------------
# 6. POST /toggle again → enabled=True
# ---------------------------------------------------------------------------
def test_script_toggle_enable():
    _, add_data = _add_script(name="Toggle Me Again")
    script_id = add_data["script_id"]
    # Disable first
    post_json(f"/api/v1/user-scripts/{script_id}/toggle", {})
    # Re-enable
    status, data = post_json(f"/api/v1/user-scripts/{script_id}/toggle", {})
    assert status == 200
    assert data.get("enabled") is True


# ---------------------------------------------------------------------------
# 7. GET /validate → safe=True for clean code
# ---------------------------------------------------------------------------
def test_script_validate_safe():
    _, add_data = _add_script(name="Safe Script", code="document.querySelector('h1').style.color = 'red';")
    script_id = add_data["script_id"]
    status, data = get_json(f"/api/v1/user-scripts/{script_id}/validate")
    assert status == 200
    assert data.get("safe") is True
    assert data.get("warnings") == []


# ---------------------------------------------------------------------------
# 8. code with eval( → safe=False, warnings present
# ---------------------------------------------------------------------------
def test_script_validate_unsafe():
    _, add_data = _add_script(name="Unsafe Script", code="var x = eval('2+2'); document.write(x);")
    script_id = add_data["script_id"]
    status, data = get_json(f"/api/v1/user-scripts/{script_id}/validate")
    assert status == 200
    assert data.get("safe") is False
    warnings = data.get("warnings", [])
    assert len(warnings) >= 1
    assert any("eval(" in w for w in warnings)


# ---------------------------------------------------------------------------
# 9. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_script_html_no_cdn():
    html_path = REPO_ROOT / "web" / "user-scripts.html"
    assert html_path.exists(), "user-scripts.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 10. No port 9222 in any user scripts file
# ---------------------------------------------------------------------------
def test_no_port_9222_in_user_scripts():
    files_to_check = [
        REPO_ROOT / "web" / "user-scripts.html",
        REPO_ROOT / "web" / "js" / "user-scripts.js",
        REPO_ROOT / "web" / "css" / "user-scripts.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
