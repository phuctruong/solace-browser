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
    with ys._WEBRTC_LOCK:
        ys._WEBRTC_RECORDS.clear()


def _payload(**overrides):
    payload = {
        "connection_type": "peer",
        "page_url": "https://example.com/call",
        "remote_ip": "203.0.113.42",
        "duration_ms": "1500.00",
        "bytes_sent": 1024,
        "bytes_received": 2048,
        "is_ice_connected": True,
    }
    payload.update(overrides)
    return payload


def test_webrtc_create():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload())
    assert h._response_code == 201
    assert h._response_body["conn_id"].startswith("wrc_")


def test_webrtc_ip_hashed():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload())
    assert "remote_ip_hash" in h._response_body
    assert "remote_ip" not in h._response_body


def test_webrtc_page_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload())
    assert "page_url_hash" in h._response_body
    assert "page_url" not in h._response_body


def test_webrtc_invalid_type():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload(connection_type="invalid_type"))
    assert h._response_code == 400


def test_webrtc_negative_duration():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload(duration_ms="-1"))
    assert h._response_code == 400


def test_webrtc_negative_bytes_sent():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload(bytes_sent=-1))
    assert h._response_code == 400


def test_webrtc_negative_bytes_received():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload(bytes_received=-5))
    assert h._response_code == 400


def test_webrtc_list():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload())
    h._handle_webrtc_list()
    assert h._response_code == 200
    assert len(h._response_body["connections"]) == 1


def test_webrtc_delete():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload())
    conn_id = h._response_body["conn_id"]
    h._handle_webrtc_delete(conn_id)
    assert h._response_code == 200
    with ys._WEBRTC_LOCK:
        assert ys._WEBRTC_RECORDS == []


def test_webrtc_stats():
    h = FakeHandler()
    _reset()
    h._handle_webrtc_create(_payload(is_ice_connected=True, duration_ms="1000.00"))
    h._handle_webrtc_create(_payload(connection_type="media", is_ice_connected=False, duration_ms="2000.00"))
    h._handle_webrtc_stats()
    assert h._response_code == 200
    assert h._response_body["total"] == 2
    assert h._response_body["ice_connected_count"] == 1
    assert isinstance(Decimal(h._response_body["avg_duration_ms"]), Decimal)
    assert isinstance(h._response_body["total_bytes"], int)


def test_no_port_9222_in_webrtc():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
