"""Tests for Task 176 — Battery Status Tracker."""
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
    with ys._BST_LOCK:
        ys._BST_RECORDS.clear()


def _payload(**overrides):
    p = {
        "charging_state": "charging",
        "url": "https://example.com/page",
        "level_pct": "75.00",
        "charging_time_seconds": 3600,
        "discharging_time_seconds": None,
    }
    p.update(overrides)
    return p


def test_bst_create():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload())
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("bst_")


def test_bst_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload())
    assert "url_hash" in h._response_body
    assert "url" not in h._response_body


def test_bst_invalid_state():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload(charging_state="exploding"))
    assert h._response_code == 400


def test_bst_level_out_of_range():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload(level_pct="150.00"))
    assert h._response_code == 400


def test_bst_negative_level():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload(level_pct="-1"))
    assert h._response_code == 400


def test_bst_negative_charging_time():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload(charging_time_seconds=-1))
    assert h._response_code == 400


def test_bst_negative_discharging_time():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload(discharging_time_seconds=-5))
    assert h._response_code == 400


def test_bst_low_battery_flag():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload(charging_state="discharging", level_pct="15.00"))
    h._handle_bst_stats()
    assert h._response_code == 200
    assert h._response_body["low_battery_count"] == 1


def test_bst_list():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload())
    h._handle_bst_list()
    assert h._response_code == 200
    assert len(h._response_body["records"]) == 1


def test_bst_delete():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload())
    rid = h._response_body["record_id"]
    h._handle_bst_delete(rid)
    assert h._response_code == 200
    with ys._BST_LOCK:
        assert ys._BST_RECORDS == []


def test_bst_stats():
    h = FakeHandler()
    _reset()
    h._handle_bst_create(_payload(charging_state="charging", level_pct="80.00"))
    h._handle_bst_create(_payload(charging_state="discharging", level_pct="20.00"))
    h._handle_bst_stats()
    assert h._response_code == 200
    assert h._response_body["total"] == 2
    assert h._response_body["charging_count"] == 1
    assert isinstance(Decimal(h._response_body["avg_level"]), Decimal)


def test_no_port_9222():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
