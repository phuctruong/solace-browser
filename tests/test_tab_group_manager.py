# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 058 — Tab Group Manager
Browser: yinyang_server.py routes /api/v1/tab-groups
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


def test_tab_groups_list_empty():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler()
    h._handle_tab_groups_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["groups"] == []
    assert data["total"] == 0


def test_tab_group_create_ok():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler({"name": "Work", "color": "blue"})
    h._handle_tab_group_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["status"] == "created"
    assert data["group"]["group_id"].startswith("tg_")
    assert data["group"]["name"] == "Work"
    assert data["group"]["color"] == "blue"
    assert data["group"]["tab_count"] == 0


def test_tab_group_create_invalid_color():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler({"name": "Work", "color": "pink"})
    h._handle_tab_group_create()
    status, data = h._responses[0]
    assert status == 400
    assert "color" in data["error"]


def test_tab_group_create_requires_auth():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler({"name": "Work", "color": "blue"}, auth=False)
    h._handle_tab_group_create()
    status, data = h._responses[0]
    assert status == 401


def test_tab_group_get_ok():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler({"name": "Research", "color": "green"})
    h._handle_tab_group_create()
    group_id = h._responses[0][1]["group"]["group_id"]

    h2 = _make_handler()
    h2._handle_tab_group_get(group_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["group_id"] == group_id


def test_tab_group_get_not_found():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler()
    h._handle_tab_group_get("tg_doesnotexist")
    status, data = h._responses[0]
    assert status == 404


def test_tab_group_add_tab_ok():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler({"name": "Dev", "color": "purple"})
    h._handle_tab_group_create()
    group_id = h._responses[0][1]["group"]["group_id"]

    tab_hash = "a" * 64
    h2 = _make_handler({"tab_hash": tab_hash, "title_hash": "b" * 64})
    h2._handle_tab_group_add_tab(group_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "added"
    assert data["tab_hash"] == tab_hash


def test_tab_group_add_tab_duplicate():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler({"name": "Dev", "color": "red"})
    h._handle_tab_group_create()
    group_id = h._responses[0][1]["group"]["group_id"]

    tab_hash = "c" * 64
    h2 = _make_handler({"tab_hash": tab_hash, "title_hash": "d" * 64})
    h2._handle_tab_group_add_tab(group_id)
    h3 = _make_handler({"tab_hash": tab_hash, "title_hash": "d" * 64})
    h3._handle_tab_group_add_tab(group_id)
    status, data = h3._responses[0]
    assert status == 409


def test_tab_group_remove_tab_ok():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler({"name": "Finance", "color": "orange"})
    h._handle_tab_group_create()
    group_id = h._responses[0][1]["group"]["group_id"]

    tab_hash = "e" * 64
    h2 = _make_handler({"tab_hash": tab_hash, "title_hash": "f" * 64})
    h2._handle_tab_group_add_tab(group_id)

    h3 = _make_handler()
    h3._handle_tab_group_remove_tab(group_id, tab_hash)
    status, data = h3._responses[0]
    assert status == 200
    assert data["status"] == "removed"


def test_tab_group_delete_ok():
    import yinyang_server as ys
    ys._TAB_GROUPS.clear()
    h = _make_handler({"name": "Temp", "color": "gray"})
    h._handle_tab_group_create()
    group_id = h._responses[0][1]["group"]["group_id"]

    h2 = _make_handler()
    h2._handle_tab_group_delete(group_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"

    with ys._TAB_GROUPS_LOCK:
        found = any(g["group_id"] == group_id for g in ys._TAB_GROUPS)
    assert not found
