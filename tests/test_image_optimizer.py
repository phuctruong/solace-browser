# Diagram: 05-solace-runtime-architecture
"""Tests for Image Optimizer (Task 120). 10 tests."""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from decimal import Decimal
from io import BytesIO


VALID_TOKEN = hashlib.sha256(b"test-image-optimizer-token").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method, path, body=None, auth=True):
        self.command = method
        self.path = path
        self._body = json.dumps(body).encode() if body else b""
        self._auth = auth
        self._status = None
        self._response = None
        self.headers = {
            "Content-Length": str(len(self._body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.server = type("S", (), {
            "session_token_sha256": VALID_TOKEN,
            "repo_root": str(REPO_ROOT),
        })()
        self.rfile = BytesIO(self._body)
        self.wfile = BytesIO()

    def send_response(self, code):
        self._status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, code=200):
        self._status = code
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def _reset():
    ys._IMAGE_REPORTS.clear()


def test_report_create():
    """POST creates report with img_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/image-optimizer/reports", {
        "page_url": "https://example.com/page",
        "image_url": "https://example.com/img.png",
        "format": "png",
        "issues": ["oversized"],
        "original_size_bytes": 100000,
        "optimized_size_bytes": 50000,
    })
    h._handle_image_report_create()
    assert h._status == 201
    report = h._response["report"]
    assert report["report_id"].startswith("img_")


def test_report_url_hashed():
    """image_hash present, no raw URL stored."""
    _reset()
    image_url = "https://example.com/private-image.jpg"
    h = FakeHandler("POST", "/api/v1/image-optimizer/reports", {
        "page_url": "https://example.com/page",
        "image_url": image_url,
        "format": "jpeg",
        "issues": [],
        "original_size_bytes": 200000,
        "optimized_size_bytes": 100000,
    })
    h._handle_image_report_create()
    assert h._status == 201
    report = h._response["report"]
    assert "image_hash" in report
    assert image_url not in str(report)
    expected = hashlib.sha256(image_url.encode()).hexdigest()
    assert report["image_hash"] == expected


def test_report_invalid_format():
    """Unknown format returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/image-optimizer/reports", {
        "page_url": "https://example.com",
        "image_url": "https://example.com/img.xyz",
        "format": "INVALID_FORMAT",
        "issues": [],
        "original_size_bytes": 1000,
        "optimized_size_bytes": 500,
    })
    h._handle_image_report_create()
    assert h._status == 400


def test_report_invalid_issue():
    """Unknown issue returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/image-optimizer/reports", {
        "page_url": "https://example.com",
        "image_url": "https://example.com/img.webp",
        "format": "webp",
        "issues": ["INVALID_ISSUE"],
        "original_size_bytes": 1000,
        "optimized_size_bytes": 500,
    })
    h._handle_image_report_create()
    assert h._status == 400


def test_report_zero_original():
    """original_size_bytes=0 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/image-optimizer/reports", {
        "page_url": "https://example.com",
        "image_url": "https://example.com/img.png",
        "format": "png",
        "issues": [],
        "original_size_bytes": 0,
        "optimized_size_bytes": 0,
    })
    h._handle_image_report_create()
    assert h._status == 400


def test_report_savings_pct():
    """savings_pct is a valid Decimal string."""
    _reset()
    h = FakeHandler("POST", "/api/v1/image-optimizer/reports", {
        "page_url": "https://example.com",
        "image_url": "https://example.com/img.gif",
        "format": "gif",
        "issues": ["large_filesize"],
        "original_size_bytes": 400000,
        "optimized_size_bytes": 100000,
    })
    h._handle_image_report_create()
    assert h._status == 201
    savings_pct = h._response["report"]["savings_pct"]
    # Must be parseable as Decimal
    val = Decimal(savings_pct)
    assert val == Decimal("75.00")


def test_report_list():
    """GET returns list of reports."""
    _reset()
    h = FakeHandler("POST", "/api/v1/image-optimizer/reports", {
        "page_url": "https://example.com",
        "image_url": "https://example.com/img.avif",
        "format": "avif",
        "issues": ["no_alt"],
        "original_size_bytes": 50000,
        "optimized_size_bytes": 25000,
    })
    h._handle_image_report_create()
    lh = FakeHandler("GET", "/api/v1/image-optimizer/reports")
    lh._handle_image_reports_list()
    assert lh._status == 200
    assert "reports" in lh._response
    assert lh._response["total"] == 1


def test_report_delete():
    """DELETE removes the report."""
    _reset()
    h = FakeHandler("POST", "/api/v1/image-optimizer/reports", {
        "page_url": "https://example.com",
        "image_url": "https://example.com/to-delete.png",
        "format": "png",
        "issues": [],
        "original_size_bytes": 10000,
        "optimized_size_bytes": 5000,
    })
    h._handle_image_report_create()
    report_id = h._response["report"]["report_id"]

    dh = FakeHandler("DELETE", f"/api/v1/image-optimizer/reports/{report_id}")
    dh._handle_image_report_delete(report_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"

    lh = FakeHandler("GET", "/api/v1/image-optimizer/reports")
    lh._handle_image_reports_list()
    assert lh._response["total"] == 0


def test_formats_list():
    """GET /formats returns 8 image formats."""
    h = FakeHandler("GET", "/api/v1/image-optimizer/formats")
    h._handle_image_formats()
    assert h._status == 200
    assert len(h._response["formats"]) == 8
    assert "jpeg" in h._response["formats"]
    assert "webp" in h._response["formats"]
    assert "avif" in h._response["formats"]


def test_no_legacy_debug_port_in_image():
    """Grep check: legacy debug port must not appear in this file."""
    banned_port = "92" + "22"  # split to avoid self-matching
    source = pathlib.Path(__file__).read_text()
    assert banned_port not in source
