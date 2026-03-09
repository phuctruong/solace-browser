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
    with ys._CSP_LOCK:
        ys._CSP_VIOLATIONS.clear()


def _payload(**overrides):
    payload = {
        "directive": "script-src",
        "page_url": "https://example.com/page",
        "blocked_url": "https://evil.com/script.js",
        "is_report_only": False,
    }
    payload.update(overrides)
    return payload


def test_csp_create():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload())
    assert h._response_code == 201
    assert h._response_body["violation_id"].startswith("csp_")


def test_csp_page_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload())
    assert "page_url_hash" in h._response_body
    assert "page_url" not in h._response_body


def test_csp_blocked_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload())
    assert "blocked_url_hash" in h._response_body
    assert "blocked_url" not in h._response_body


def test_csp_invalid_directive():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload(directive="unknown-src"))
    assert h._response_code == 400


def test_csp_missing_page_url():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload(page_url=""))
    assert h._response_code == 400


def test_csp_missing_blocked_url():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload(blocked_url=""))
    assert h._response_code == 400


def test_csp_list():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload())
    h._handle_csp_list()
    assert h._response_code == 200
    assert len(h._response_body["reports"]) == 1


def test_csp_delete():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload())
    violation_id = h._response_body["violation_id"]
    h._handle_csp_delete(violation_id)
    assert h._response_code == 200
    with ys._CSP_LOCK:
        assert ys._CSP_VIOLATIONS == []


def test_csp_stats():
    h = FakeHandler()
    _reset()
    h._handle_csp_create(_payload(is_report_only=True))
    h._handle_csp_create(_payload(directive="style-src", is_report_only=False))
    h._handle_csp_stats()
    assert h._response_code == 200
    assert h._response_body["total"] == 2
    assert h._response_body["report_only_count"] == 1
    assert isinstance(Decimal(h._response_body["report_only_rate"]), Decimal)


def test_no_port_9222_in_csp():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
