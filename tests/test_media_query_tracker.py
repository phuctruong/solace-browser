# Diagram: 05-solace-runtime-architecture
"""Tests for Task 175 — Media Query Tracker."""
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

    def _send_json(self, data, status=200):
        self._response_code = status
        self._response_body = data

    def _check_auth(self):
        return True


def _reset():
    with ys._MQT_LOCK:
        ys._MQT_RECORDS.clear()


def _payload(**overrides):
    p = {
        "breakpoint": "md",
        "url": "https://example.com/page",
        "orientation": "portrait",
        "width_px": 768,
        "height_px": 1024,
        "device_pixel_ratio": "2.0",
    }
    p.update(overrides)
    return p


def test_mqt_create():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload())
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("mqt_")


def test_mqt_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload())
    assert "url_hash" in h._response_body
    assert "url" not in h._response_body


def test_mqt_invalid_breakpoint():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload(breakpoint="mega"))
    assert h._response_code == 400


def test_mqt_invalid_orientation():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload(orientation="sideways"))
    assert h._response_code == 400


def test_mqt_negative_width():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload(width_px=-1))
    assert h._response_code == 400


def test_mqt_negative_height():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload(height_px=-5))
    assert h._response_code == 400


def test_mqt_negative_dpr():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload(device_pixel_ratio="-1"))
    assert h._response_code == 400


def test_mqt_list():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload())
    h._handle_mqt_list()
    assert h._response_code == 200
    assert len(h._response_body["records"]) == 1


def test_mqt_delete():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload())
    rid = h._response_body["record_id"]
    h._handle_mqt_delete(rid)
    assert h._response_code == 200
    with ys._MQT_LOCK:
        assert ys._MQT_RECORDS == []


def test_mqt_stats():
    h = FakeHandler()
    _reset()
    h._handle_mqt_create(_payload(orientation="landscape", width_px=1920))
    h._handle_mqt_create(_payload(orientation="portrait", width_px=768))
    h._handle_mqt_stats()
    assert h._response_code == 200
    assert h._response_body["total"] == 2
    assert h._response_body["landscape_count"] == 1
    assert isinstance(Decimal(h._response_body["landscape_rate"]), Decimal)
    assert isinstance(Decimal(h._response_body["avg_width"]), Decimal)


def test_no_port_9222():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
