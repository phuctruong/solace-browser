# Diagram: 05-solace-runtime-architecture
"""Tests for Task 090 — Automation Recorder."""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "f" * 64
TOKEN2 = "g" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self, token=VALID_TOKEN):
        self._responses = []
        self._body = b""
        self._token = token
        self.headers = {"content-length": "0", "Authorization": f"Bearer {token}"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass

    def send_response(self, code):
        self._responses.append((code, {}))

    def end_headers(self):
        pass


def make_handler(body=None, token=VALID_TOKEN):
    h = FakeHandler(token=token)
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {token}",
        }
    return h


def setup_function():
    with ys._AUTOMATION_LOCK:
        ys._AUTOMATIONS.clear()
        ys._ACTIVE_AUTOMATION_RECORDING.clear()


def test_automation_start():
    h = FakeHandler()
    h._handle_automation_start()
    code, data = h._responses[0]
    assert code == 200
    assert data["automation_id"].startswith("aut_")
    assert data["status"] == "started"


def test_automation_start_conflict():
    h = FakeHandler()
    h._handle_automation_start()
    h2 = FakeHandler()
    h2._handle_automation_start()
    code, data = h2._responses[0]
    assert code == 409


def test_automation_action():
    h = FakeHandler()
    h._handle_automation_start()
    h2 = make_handler({"action_type": "click", "element_hash": "el1", "page_hash": "pg1"})
    h2._handle_automation_action()
    code, data = h2._responses[0]
    assert code == 201
    assert data["action_id"].startswith("aact_")


def test_automation_action_invalid_type():
    h = FakeHandler()
    h._handle_automation_start()
    h2 = make_handler({"action_type": "hover_invalid", "element_hash": "el1", "page_hash": "pg1"})
    h2._handle_automation_action()
    code, data = h2._responses[0]
    assert code == 400
    assert "action_type" in data["error"]


def test_automation_action_no_active():
    h = make_handler({"action_type": "click", "element_hash": "el1", "page_hash": "pg1"})
    h._handle_automation_action()
    code, data = h._responses[0]
    assert code == 404


def test_automation_stop():
    h = FakeHandler(token=TOKEN2)
    h._handle_automation_start()
    aut_id = h._responses[0][1]["automation_id"]
    h2 = make_handler({"name": "My Automation"}, token=TOKEN2)
    h2._handle_automation_stop()
    code, data = h2._responses[0]
    assert code == 200
    assert data["automation_id"] == aut_id
    assert data["status"] == "stopped"


def test_automation_stop_saves_to_list():
    h = FakeHandler()
    h._handle_automation_start()
    h2 = make_handler({"action_type": "navigate", "element_hash": "", "page_hash": "pg1"})
    h2._handle_automation_action()
    h3 = FakeHandler()
    h3._handle_automation_stop()
    with ys._AUTOMATION_LOCK:
        count = len(ys._AUTOMATIONS)
    assert count >= 1


def test_automation_stop_not_active():
    h = FakeHandler()
    h._handle_automation_stop()
    code, data = h._responses[0]
    assert code == 404


def test_automation_list():
    h = FakeHandler()
    h._handle_automation_start()
    h2 = FakeHandler()
    h2._handle_automation_stop()
    h3 = FakeHandler()
    h3._handle_automation_list()
    code, data = h3._responses[0]
    assert code == 200
    assert isinstance(data["automations"], list)
    for item in data["automations"]:
        assert "actions" not in item


def test_automation_delete():
    h = FakeHandler()
    h._handle_automation_start()
    h2 = FakeHandler()
    h2._handle_automation_stop()
    with ys._AUTOMATION_LOCK:
        aut_id = ys._AUTOMATIONS[-1]["automation_id"]
    h3 = FakeHandler()
    h3._handle_automation_delete(aut_id)
    code, data = h3._responses[0]
    assert code == 200
    assert data["automation_id"] == aut_id
    with ys._AUTOMATION_LOCK:
        ids = [a["automation_id"] for a in ys._AUTOMATIONS]
    assert aut_id not in ids


def test_automation_delete_not_found():
    h = FakeHandler()
    h._handle_automation_delete("aut_ghost")
    code, data = h._responses[0]
    assert code == 404


def test_automation_action_types():
    h = FakeHandler()
    h._handle_automation_action_types()
    code, data = h._responses[0]
    assert code == 200
    assert "click" in data["action_types"]
    assert "navigate" in data["action_types"]
    assert "submit" in data["action_types"]
