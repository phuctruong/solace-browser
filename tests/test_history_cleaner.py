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
    with ys._HISTORY_CLEAN_LOCK:
        ys._HISTORY_CLEAN_RECORDS.clear()


def _payload(**overrides):
    payload = {
        "reason": "user_request",
        "url_pattern": "https://example.com/*",
        "entries_removed": 42,
        "time_range_hours": 24,
    }
    payload.update(overrides)
    return payload


def test_history_cleaner_create():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload())
    assert h._response_code == 201
    assert h._response_body["clean_id"].startswith("hcl_")


def test_history_cleaner_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload())
    assert "url_hash" in h._response_body
    assert "url_pattern" not in h._response_body


def test_history_cleaner_invalid_reason():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload(reason="unknown_reason"))
    assert h._response_code == 400


def test_history_cleaner_negative_entries():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload(entries_removed=-1))
    assert h._response_code == 400


def test_history_cleaner_negative_time_range():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload(time_range_hours=-5))
    assert h._response_code == 400


def test_history_cleaner_zero_time_range_allowed():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload(time_range_hours=0))
    assert h._response_code == 201


def test_history_cleaner_list():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload())
    h._handle_history_cleaner_list()
    assert h._response_code == 200
    assert len(h._response_body["records"]) == 1


def test_history_cleaner_delete():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload())
    clean_id = h._response_body["clean_id"]
    h._handle_history_cleaner_delete(clean_id)
    assert h._response_code == 200
    with ys._HISTORY_CLEAN_LOCK:
        assert ys._HISTORY_CLEAN_RECORDS == []


def test_history_cleaner_stats():
    h = FakeHandler()
    _reset()
    h._handle_history_cleaner_create(_payload(entries_removed=10))
    h._handle_history_cleaner_create(_payload(reason="privacy", entries_removed=20))
    h._handle_history_cleaner_stats()
    assert h._response_code == 200
    assert h._response_body["total_cleanups"] == 2
    assert h._response_body["total_entries_removed"] == 30
    assert isinstance(Decimal(h._response_body["avg_entries"]), Decimal)


def test_no_port_9222_in_history_cleaner():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
