"""Tests for Task 088 — Session Recorder."""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "c" * 64
TOKEN2 = "d" * 64


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
    with ys._REC_LOCK:
        ys._RECORDINGS.clear()
        ys._ACTIVE_RECORDING.clear()


def test_recorder_start():
    h = FakeHandler()
    h._handle_recorder_start()
    code, data = h._responses[0]
    assert code == 200
    assert data["recording_id"].startswith("rec_")
    assert data["status"] == "started"


def test_recorder_start_conflict():
    h = FakeHandler()
    h._handle_recorder_start()
    h2 = FakeHandler()
    h2._handle_recorder_start()
    code, data = h2._responses[0]
    assert code == 409


def test_recorder_stop():
    h = FakeHandler(token=TOKEN2)
    h._handle_recorder_start()
    rec_id = h._responses[0][1]["recording_id"]
    h2 = FakeHandler(token=TOKEN2)
    h2._handle_recorder_stop()
    code, data = h2._responses[0]
    assert code == 200
    assert data["recording_id"] == rec_id
    assert data["status"] == "stopped"


def test_recorder_stop_not_active():
    h = FakeHandler()
    h._handle_recorder_stop()
    code, data = h._responses[0]
    assert code == 404


def test_recorder_event():
    h = FakeHandler()
    h._handle_recorder_start()
    h2 = make_handler({"event_type": "click", "element_hash": "el1", "url_hash": "url1", "payload_hash": "p1"})
    h2._handle_recorder_event()
    code, data = h2._responses[0]
    assert code == 201
    assert data["event_id"].startswith("rev_")


def test_recorder_event_invalid_type():
    h = FakeHandler()
    h._handle_recorder_start()
    h2 = make_handler({"event_type": "hover", "element_hash": "el1", "url_hash": "url1", "payload_hash": "p1"})
    h2._handle_recorder_event()
    code, data = h2._responses[0]
    assert code == 400
    assert "event_type" in data["error"]


def test_recorder_event_no_active():
    h = make_handler({"event_type": "click", "element_hash": "el1", "url_hash": "url1", "payload_hash": "p1"})
    h._handle_recorder_event()
    code, data = h._responses[0]
    assert code == 404


def test_recorder_list():
    h = FakeHandler()
    h._handle_recorder_start()
    h2 = FakeHandler()
    h2._handle_recorder_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["recordings"], list)
    assert data["total"] >= 1
    for rec in data["recordings"]:
        assert "events" not in rec


def test_recorder_delete():
    h = FakeHandler()
    h._handle_recorder_start()
    rec_id = h._responses[0][1]["recording_id"]
    h2 = FakeHandler()
    h2._handle_recorder_delete(rec_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["recording_id"] == rec_id
    with ys._REC_LOCK:
        ids = [r["recording_id"] for r in ys._RECORDINGS]
    assert rec_id not in ids


def test_recorder_delete_not_found():
    h = FakeHandler()
    h._handle_recorder_delete("rec_ghost")
    code, data = h._responses[0]
    assert code == 404
