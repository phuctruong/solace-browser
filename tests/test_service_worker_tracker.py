import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yinyang_server as ys


REPO_ROOT = Path(__file__).resolve().parent.parent


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._response_code = None
        self._response_body = None

    def _send_json(self, code, body):
        self._response_code = code
        self._response_body = body

    def _require_auth(self):
        pass


def _reset():
    with ys._SW_TRACKER_LOCK:
        ys._SW_REGISTRATIONS.clear()


def _payload(**overrides):
    payload = {
        "event_type": "install",
        "state": "installed",
        "scope_url": "https://example.com/app/",
        "script_url": "https://example.com/sw.js",
        "is_https": True,
    }
    payload.update(overrides)
    return payload


def test_reg_create():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_create(_payload())
    assert h._response_code == 201
    assert h._response_body["reg_id"].startswith("swr_")


def test_reg_scope_hashed():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_create(_payload())
    assert "scope_hash" in h._response_body
    assert "scope_url" not in h._response_body


def test_reg_script_hashed():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_create(_payload())
    assert "script_hash" in h._response_body
    assert "script_url" not in h._response_body


def test_reg_invalid_event():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_create(_payload(event_type="invalid"))
    assert h._response_code == 400


def test_reg_invalid_state():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_create(_payload(state="unknown"))
    assert h._response_code == 400


def test_reg_list():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_create(_payload())
    h._handle_service_worker_tracker_list()
    assert h._response_code == 200
    assert len(h._response_body["registrations"]) == 1


def test_reg_delete():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_create(_payload())
    reg_id = h._response_body["reg_id"]
    h._handle_service_worker_tracker_delete(reg_id)
    assert h._response_code == 200
    with ys._SW_TRACKER_LOCK:
        assert ys._SW_REGISTRATIONS == []


def test_reg_not_found():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_delete("swr_notexist")
    assert h._response_code == 404


def test_sw_stats():
    h = FakeHandler()
    _reset()
    h._handle_service_worker_tracker_create(_payload(event_type="activate", state="activated"))
    h._handle_service_worker_tracker_stats()
    assert h._response_code == 200
    assert "by_state" in h._response_body
    assert h._response_body["by_state"]["activated"] == 1


def test_no_port_9222_in_sw_tracker():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content

