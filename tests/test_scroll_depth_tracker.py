"""Tests for Task 177 — Scroll Depth Tracker."""
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
    with ys._SDS_LOCK:
        ys._SDS_SESSIONS.clear()


def _payload(**overrides):
    p = {
        "content_type": "article",
        "url": "https://example.com/article",
        "max_depth_pct": "50.00",
        "time_on_page_seconds": "120.00",
    }
    p.update(overrides)
    return p


def test_sds_create():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload())
    assert h._response_code == 201
    assert h._response_body["session_id"].startswith("sds_")


def test_sds_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload())
    assert "url_hash" in h._response_body
    assert "url" not in h._response_body


def test_sds_invalid_type():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload(content_type="newsletter"))
    assert h._response_code == 400


def test_sds_depth_out_of_range():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload(max_depth_pct="110.00"))
    assert h._response_code == 400


def test_sds_negative_depth():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload(max_depth_pct="-5"))
    assert h._response_code == 400


def test_sds_negative_time():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload(time_on_page_seconds="-1"))
    assert h._response_code == 400


def test_sds_reached_bottom_true():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload(max_depth_pct="95.00"))
    assert h._response_body["reached_bottom"] is True


def test_sds_reached_bottom_false():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload(max_depth_pct="50.00"))
    assert h._response_body["reached_bottom"] is False


def test_sds_list():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload())
    h._handle_sds_list()
    assert h._response_code == 200
    assert len(h._response_body["sessions"]) == 1


def test_sds_delete():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload())
    sid = h._response_body["session_id"]
    h._handle_sds_delete(sid)
    assert h._response_code == 200
    with ys._SDS_LOCK:
        assert ys._SDS_SESSIONS == []


def test_sds_stats():
    h = FakeHandler()
    _reset()
    h._handle_sds_create(_payload(max_depth_pct="100.00"))
    h._handle_sds_create(_payload(content_type="blog", max_depth_pct="40.00"))
    h._handle_sds_stats()
    assert h._response_code == 200
    assert h._response_body["total"] == 2
    assert h._response_body["bottom_reach_count"] == 1
    assert isinstance(Decimal(h._response_body["bottom_rate"]), Decimal)
    assert isinstance(Decimal(h._response_body["avg_depth"]), Decimal)


def test_no_port_9222():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
