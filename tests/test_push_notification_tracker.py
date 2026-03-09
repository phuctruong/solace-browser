import os
import sys
from decimal import Decimal
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
    with ys._PUSH_TRACKER_LOCK:
        ys._PUSH_EVENTS.clear()


def _payload(**overrides):
    payload = {
        "event_type": "permission_granted",
        "origin": "https://example.com",
        "endpoint": "https://push.example.com/sub/123",
        "is_https": True,
    }
    payload.update(overrides)
    return payload


def test_event_create():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_create(_payload())
    assert h._response_code == 201
    assert h._response_body["event_id"].startswith("pnt_")


def test_event_origin_hashed():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_create(_payload())
    assert "origin_hash" in h._response_body
    assert "origin" not in h._response_body


def test_event_invalid_type():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_create(_payload(event_type="unknown"))
    assert h._response_code == 400


def test_event_https_flag():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_create(_payload(is_https=False))
    assert h._response_code == 201
    assert h._response_body["is_https"] is False


def test_event_list():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_create(_payload())
    h._handle_push_notification_tracker_list()
    assert h._response_code == 200
    assert len(h._response_body["events"]) == 1


def test_event_delete():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_create(_payload())
    event_id = h._response_body["event_id"]
    h._handle_push_notification_tracker_delete(event_id)
    assert h._response_code == 200
    with ys._PUSH_TRACKER_LOCK:
        assert ys._PUSH_EVENTS == []


def test_event_not_found():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_delete("pnt_notexist")
    assert h._response_code == 404


def test_push_stats():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_create(_payload(event_type="permission_granted"))
    h._handle_push_notification_tracker_create(_payload(event_type="permission_denied", endpoint=None))
    h._handle_push_notification_tracker_stats()
    assert h._response_code == 200
    assert isinstance(Decimal(h._response_body["permission_grant_rate"]), Decimal)


def test_push_event_types():
    h = FakeHandler()
    _reset()
    h._handle_push_notification_tracker_event_types()
    assert h._response_code == 200
    assert len(h._response_body["event_types"]) == 9


def test_no_port_9222_in_push():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content

