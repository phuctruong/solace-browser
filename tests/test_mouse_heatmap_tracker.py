"""Tests for Task 179 — Mouse Heatmap Tracker."""
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
    with ys._MHE_LOCK:
        ys._MHE_RECORDS.clear()


def _payload(**overrides):
    p = {
        "interaction_type": "click",
        "url": "https://example.com/page",
        "x_pct": "45.50",
        "y_pct": "60.00",
        "session_id": "sess-abc-123",
    }
    p.update(overrides)
    return p


def test_mhe_create():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload())
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("mhe_")


def test_mhe_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload())
    assert "url_hash" in h._response_body
    assert "url" not in h._response_body


def test_mhe_session_hashed():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload())
    assert "session_hash" in h._response_body
    assert "session_id" not in h._response_body


def test_mhe_invalid_type():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload(interaction_type="swipe"))
    assert h._response_code == 400


def test_mhe_x_out_of_range():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload(x_pct="150.00"))
    assert h._response_code == 400


def test_mhe_y_out_of_range():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload(y_pct="-1"))
    assert h._response_code == 400


def test_mhe_list():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload())
    h._handle_mhe_list()
    assert h._response_code == 200
    assert len(h._response_body["records"]) == 1


def test_mhe_delete():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload())
    rid = h._response_body["record_id"]
    h._handle_mhe_delete(rid)
    assert h._response_code == 200
    with ys._MHE_LOCK:
        assert ys._MHE_RECORDS == []


def test_mhe_stats():
    h = FakeHandler()
    _reset()
    h._handle_mhe_create(_payload(x_pct="20.00", y_pct="30.00", session_id="s1"))
    h._handle_mhe_create(_payload(interaction_type="hover", x_pct="80.00", y_pct="70.00", session_id="s2"))
    h._handle_mhe_stats()
    assert h._response_code == 200
    assert h._response_body["total"] == 2
    assert h._response_body["unique_sessions"] == 2
    assert isinstance(Decimal(h._response_body["avg_x"]), Decimal)
    assert isinstance(Decimal(h._response_body["avg_y"]), Decimal)


def test_no_port_9222():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
