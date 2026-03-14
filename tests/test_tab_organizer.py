# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 099 — Tab Organizer
Browser: yinyang_server.py routes /api/v1/tab-organizer
"""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


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
        self.rfile = BytesIO(self._body)
        self.wfile = BytesIO()

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


def setup_function():
    ys._WORKSPACES.clear()


def _make_workspace(name_hash="a" * 64):
    h = FakeHandler("POST", "/api/v1/tab-organizer/workspaces", {
        "name_hash": name_hash,
    })
    h._handle_workspace_create()
    return h


def test_workspace_create():
    h = _make_workspace()
    assert h._status == 201
    assert h._response["workspace"]["workspace_id"].startswith("wsp_")
    assert h._response["status"] == "created"
    assert h._response["workspace"]["tab_count"] == 0
    assert h._response["workspace"]["tabs"] == []


def test_workspace_list():
    _make_workspace(name_hash="b" * 64)
    h = FakeHandler("GET", "/api/v1/tab-organizer/workspaces")
    h._handle_workspace_list()
    assert h._status == 200
    assert isinstance(h._response["workspaces"], list)
    assert h._response["total"] >= 1


def test_workspace_delete():
    h1 = _make_workspace(name_hash="c" * 64)
    workspace_id = h1._response["workspace"]["workspace_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/tab-organizer/workspaces/{workspace_id}")
    h2._handle_workspace_delete(workspace_id)
    assert h2._status == 200
    assert h2._response["status"] == "deleted"
    assert h2._response["workspace_id"] == workspace_id


def test_workspace_not_found():
    h = FakeHandler("DELETE", "/api/v1/tab-organizer/workspaces/wsp_nonexistent")
    h._handle_workspace_delete("wsp_nonexistent")
    assert h._status == 404


def test_tab_add():
    h1 = _make_workspace(name_hash="d" * 64)
    workspace_id = h1._response["workspace"]["workspace_id"]

    h2 = FakeHandler("POST", f"/api/v1/tab-organizer/workspaces/{workspace_id}/tabs", {
        "url_hash": "e" * 64,
        "title_hash": "f" * 64,
        "status": "active",
    })
    h2._handle_workspace_tab_add(workspace_id)
    assert h2._status == 201
    assert h2._response["tab"]["tab_id"].startswith("tab_")
    assert h2._response["status"] == "added"


def test_tab_url_hashed():
    h1 = _make_workspace(name_hash="g" * 64)
    workspace_id = h1._response["workspace"]["workspace_id"]

    url_hash = "h" * 64
    h2 = FakeHandler("POST", f"/api/v1/tab-organizer/workspaces/{workspace_id}/tabs", {
        "url_hash": url_hash,
        "title_hash": "i" * 64,
        "status": "pinned",
    })
    h2._handle_workspace_tab_add(workspace_id)
    assert h2._status == 201
    assert h2._response["tab"]["url_hash"] == url_hash


def test_tab_invalid_status():
    h1 = _make_workspace(name_hash="j" * 64)
    workspace_id = h1._response["workspace"]["workspace_id"]

    h2 = FakeHandler("POST", f"/api/v1/tab-organizer/workspaces/{workspace_id}/tabs", {
        "url_hash": "k" * 64,
        "title_hash": "l" * 64,
        "status": "invalid_status",
    })
    h2._handle_workspace_tab_add(workspace_id)
    assert h2._status == 400
    assert "status" in h2._response["error"]


def test_tab_remove():
    h1 = _make_workspace(name_hash="m" * 64)
    workspace_id = h1._response["workspace"]["workspace_id"]

    h2 = FakeHandler("POST", f"/api/v1/tab-organizer/workspaces/{workspace_id}/tabs", {
        "url_hash": "n" * 64,
        "title_hash": "o" * 64,
        "status": "sleeping",
    })
    h2._handle_workspace_tab_add(workspace_id)
    tab_id = h2._response["tab"]["tab_id"]

    h3 = FakeHandler("DELETE", f"/api/v1/tab-organizer/workspaces/{workspace_id}/tabs/{tab_id}")
    h3._handle_workspace_tab_remove(workspace_id, tab_id)
    assert h3._status == 200
    assert h3._response["status"] == "removed"
    assert h3._response["tab_id"] == tab_id


def test_tab_statuses_list():
    h = FakeHandler("GET", "/api/v1/tab-organizer/tab-statuses")
    h._handle_tab_statuses_list()
    assert h._status == 200
    assert "statuses" in h._response
    assert len(h._response["statuses"]) == 6
    assert "active" in h._response["statuses"]
    assert "closed" in h._response["statuses"]


def test_no_port_9222_in_tabs():
    src = (REPO_ROOT / "yinyang_server.py").read_text()
    tab_section_start = src.find("Task 099")
    # Find the next task or server factory
    tab_section_end = src.find("Server factory", tab_section_start) if tab_section_start != -1 else -1
    tab_section = src[tab_section_start:tab_section_end] if tab_section_start != -1 and tab_section_end != -1 else ""
    assert "9222" not in tab_section
