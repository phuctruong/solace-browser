"""Tests for Task 180 — Keyboard Shortcut Analytics."""
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
    with ys._KBD_LOCK:
        ys._KBD_EVENTS.clear()


def _payload(**overrides):
    p = {
        "event_type": "shortcut_triggered",
        "url": "https://example.com/app",
        "key_combo": "Ctrl+S",
        "ui_context": "editor",
        "was_successful": True,
    }
    p.update(overrides)
    return p


def test_kbd_create():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload())
    assert h._response_code == 201
    assert h._response_body["event_id"].startswith("kbd_")


def test_kbd_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload())
    assert "url_hash" in h._response_body
    assert "url" not in h._response_body


def test_kbd_key_combo_hashed():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload())
    assert "key_combo_hash" in h._response_body
    assert "key_combo" not in h._response_body


def test_kbd_context_hashed():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload())
    assert "context_hash" in h._response_body
    assert "ui_context" not in h._response_body


def test_kbd_invalid_type():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload(event_type="double_tap"))
    assert h._response_code == 400


def test_kbd_list():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload())
    h._handle_kbd_list()
    assert h._response_code == 200
    assert len(h._response_body["events"]) == 1


def test_kbd_delete():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload())
    eid = h._response_body["event_id"]
    h._handle_kbd_delete(eid)
    assert h._response_code == 200
    with ys._KBD_LOCK:
        assert ys._KBD_EVENTS == []


def test_kbd_stats():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload(key_combo="Ctrl+S", was_successful=True))
    h._handle_kbd_create(_payload(event_type="shortcut_missed", key_combo="Ctrl+Z", was_successful=False))
    h._handle_kbd_stats()
    assert h._response_code == 200
    assert h._response_body["total"] == 2
    assert h._response_body["success_count"] == 1
    assert h._response_body["unique_combos"] == 2
    assert isinstance(Decimal(h._response_body["success_rate"]), Decimal)


def test_kbd_unique_combos_dedup():
    h = FakeHandler()
    _reset()
    h._handle_kbd_create(_payload(key_combo="Ctrl+S"))
    h._handle_kbd_create(_payload(key_combo="Ctrl+S"))
    h._handle_kbd_stats()
    assert h._response_body["unique_combos"] == 1


def test_no_port_9222():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
