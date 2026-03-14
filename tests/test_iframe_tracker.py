# Diagram: 05-solace-runtime-architecture
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
    with ys._IFRAME_LOCK:
        ys._IFRAME_RECORDS.clear()


def _payload(**overrides):
    payload = {
        "frame_type": "embed",
        "page_url": "https://example.com/page",
        "src_url": "https://embed.example.com/widget",
        "is_cross_origin": True,
        "sandbox_attrs": ["allow-scripts"],
        "load_time_ms": 150,
    }
    payload.update(overrides)
    return payload


def test_frame_create():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload())
    assert h._response_code == 201
    assert h._response_body["frame_id"].startswith("ifr_")


def test_frame_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload())
    assert "page_url_hash" in h._response_body
    assert "page_url" not in h._response_body


def test_frame_src_hashed():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload())
    assert "src_url_hash" in h._response_body
    assert "src_url" not in h._response_body


def test_frame_invalid_type():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload(frame_type="unknown"))
    assert h._response_code == 400


def test_frame_invalid_sandbox():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload(sandbox_attrs=["allow-magic"]))
    assert h._response_code == 400


def test_frame_negative_load_time():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload(load_time_ms=-1))
    assert h._response_code == 400


def test_frame_list():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload())
    h._handle_iframe_tracker_list()
    assert h._response_code == 200
    assert len(h._response_body["frames"]) == 1


def test_frame_delete():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload())
    frame_id = h._response_body["frame_id"]
    h._handle_iframe_tracker_delete(frame_id)
    assert h._response_code == 200
    with ys._IFRAME_LOCK:
        assert ys._IFRAME_RECORDS == []


def test_iframe_stats():
    h = FakeHandler()
    _reset()
    h._handle_iframe_tracker_create(_payload(is_cross_origin=True, load_time_ms=100))
    h._handle_iframe_tracker_create(_payload(frame_type="video", is_cross_origin=False, load_time_ms=200))
    h._handle_iframe_tracker_stats()
    assert h._response_code == 200
    assert isinstance(Decimal(h._response_body["cross_origin_rate"]), Decimal)
    assert isinstance(Decimal(h._response_body["avg_load_ms"]), Decimal)


def test_no_port_9222_in_iframe():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content

