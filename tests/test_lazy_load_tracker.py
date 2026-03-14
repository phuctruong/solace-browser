# Diagram: 05-solace-runtime-architecture
"""Tests for Task 178 — Lazy Load Tracker."""
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
    with ys._LZL_LOCK:
        ys._LZL_RECORDS.clear()


def _payload(**overrides):
    p = {
        "element_type": "image",
        "url": "https://example.com/page",
        "element_url": "https://cdn.example.com/img.jpg",
        "load_trigger": "intersection",
        "load_time_ms": "120.50",
        "was_visible_on_load": True,
    }
    p.update(overrides)
    return p


def test_lzl_create():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload())
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("lzl_")


def test_lzl_urls_hashed():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload())
    assert "url_hash" in h._response_body
    assert "element_url_hash" in h._response_body
    assert "url" not in h._response_body
    assert "element_url" not in h._response_body


def test_lzl_invalid_type():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload(element_type="audio"))
    assert h._response_code == 400


def test_lzl_invalid_trigger():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload(load_trigger="magic"))
    assert h._response_code == 400


def test_lzl_negative_load_time():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload(load_time_ms="-5"))
    assert h._response_code == 400


def test_lzl_was_visible_false():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload(was_visible_on_load=False))
    assert h._response_body["was_visible_on_load"] is False


def test_lzl_list():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload())
    h._handle_lzl_list()
    assert h._response_code == 200
    assert len(h._response_body["records"]) == 1


def test_lzl_delete():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload())
    rid = h._response_body["record_id"]
    h._handle_lzl_delete(rid)
    assert h._response_code == 200
    with ys._LZL_LOCK:
        assert ys._LZL_RECORDS == []


def test_lzl_stats():
    h = FakeHandler()
    _reset()
    h._handle_lzl_create(_payload(was_visible_on_load=True, load_time_ms="100.00"))
    h._handle_lzl_create(_payload(element_type="video", was_visible_on_load=False, load_time_ms="200.00"))
    h._handle_lzl_stats()
    assert h._response_code == 200
    assert h._response_body["total"] == 2
    assert h._response_body["visible_on_load_count"] == 1
    assert isinstance(Decimal(h._response_body["visible_rate"]), Decimal)
    assert isinstance(Decimal(h._response_body["avg_load_ms"]), Decimal)


def test_no_port_9222():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
