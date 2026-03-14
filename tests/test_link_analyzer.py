# Diagram: 05-solace-runtime-architecture
"""tests/test_link_analyzer.py — Task 069: Link Analyzer (10 tests)"""
import sys
import json
import hashlib
import os

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass


def make_handler(body=None):
    h = FakeHandler()
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {"content-length": str(len(h._body))}
    return h


def setup_function():
    """Clear link results before each test."""
    with ys._LINKS_LOCK:
        ys._LINK_RESULTS.clear()


def _make_page_hash():
    return hashlib.sha256(b"https://example.com").hexdigest()


def _make_url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()


def test_links_results_empty():
    """GET /api/v1/links/results → empty initially."""
    h = make_handler()
    h._handle_links_results_list()
    code, data = h._responses[-1]
    assert code == 200
    assert data["results"] == []
    assert data["total"] == 0


def test_links_analyze():
    """POST /api/v1/links/analyze → result stored."""
    page_hash = _make_page_hash()
    links = [
        {"url_hash": _make_url_hash("/about"), "link_type": "internal", "status": "ok"},
        {"url_hash": _make_url_hash("https://external.com"), "link_type": "external", "status": "redirect"},
    ]
    h = make_handler({"page_hash": page_hash, "links": links})
    h._handle_links_analyze()
    code, data = h._responses[-1]
    assert code == 201
    assert data["status"] == "analyzed"
    result = data["result"]
    assert result["page_hash"] == page_hash
    assert result["total_links"] == 2
    assert result["result_id"].startswith("lnk_")


def test_links_no_raw_urls():
    """Result stores url_hash, NOT raw URLs."""
    page_hash = _make_page_hash()
    url_hash = _make_url_hash("https://secret.com/page")
    h = make_handler({"page_hash": page_hash, "links": [
        {"url_hash": url_hash, "link_type": "external", "status": "ok"},
    ]})
    h._handle_links_analyze()
    code, data = h._responses[-1]
    assert code == 201
    result_json = json.dumps(data)
    assert "secret.com" not in result_json
    assert url_hash in result_json


def test_links_invalid_type():
    """Invalid link_type → 400."""
    page_hash = _make_page_hash()
    h = make_handler({"page_hash": page_hash, "links": [
        {"url_hash": _make_url_hash("/x"), "link_type": "INVALID_TYPE", "status": "ok"},
    ]})
    h._handle_links_analyze()
    code, data = h._responses[-1]
    assert code == 400
    assert "error" in data


def test_links_invalid_status():
    """Invalid status → 400."""
    page_hash = _make_page_hash()
    h = make_handler({"page_hash": page_hash, "links": [
        {"url_hash": _make_url_hash("/x"), "link_type": "internal", "status": "INVALID_STATUS"},
    ]})
    h._handle_links_analyze()
    code, data = h._responses[-1]
    assert code == 400
    assert "error" in data


def test_links_stats():
    """GET /api/v1/links/stats → counts correct."""
    page_hash = _make_page_hash()
    h = make_handler({"page_hash": page_hash, "links": [
        {"url_hash": _make_url_hash("/a"), "link_type": "internal", "status": "ok"},
        {"url_hash": _make_url_hash("/b"), "link_type": "external", "status": "broken"},
    ]})
    h._handle_links_analyze()

    hs = make_handler()
    hs._handle_links_stats()
    code, data = hs._responses[-1]
    assert code == 200
    assert data["total_analyses"] == 1
    assert data["total_links"] == 2
    assert data["broken_links"] == 1
    assert isinstance(data["broken_rate"], str)


def test_links_clear():
    """DELETE /api/v1/links/results → results cleared."""
    page_hash = _make_page_hash()
    h = make_handler({"page_hash": page_hash, "links": [
        {"url_hash": _make_url_hash("/x"), "link_type": "internal", "status": "ok"},
    ]})
    h._handle_links_analyze()

    hd = make_handler()
    hd._handle_links_results_clear()
    code, data = hd._responses[-1]
    assert code == 200
    assert data["status"] == "cleared"

    h2 = make_handler()
    h2._handle_links_results_list()
    _, d2 = h2._responses[-1]
    assert d2["total"] == 0


def test_links_types_list():
    """GET /api/v1/links/types → lists link_types and link_statuses."""
    h = make_handler()
    h._handle_links_types()
    code, data = h._responses[-1]
    assert code == 200
    assert "link_types" in data
    assert "link_statuses" in data
    assert "external" in data["link_types"]
    assert "broken" in data["link_statuses"]


def test_link_html_no_cdn():
    """link-analyzer.html must not reference external CDN URLs."""
    html_path = os.path.join(
        os.path.dirname(__file__), "..", "web", "link-analyzer.html"
    )
    with open(html_path) as f:
        content = f.read()
    assert "cdn.jsdelivr.net" not in content
    assert "cdnjs.cloudflare.com" not in content
    assert "unpkg.com" not in content
    assert "googleapis.com" not in content


def test_no_port_9222_in_links():
    """Port 9222 must not appear in link analyzer handlers."""
    import inspect
    src = inspect.getsource(ys.YinyangHandler._handle_links_analyze)
    src += inspect.getsource(ys.YinyangHandler._handle_links_results_list)
    src += inspect.getsource(ys.YinyangHandler._handle_links_results_clear)
    src += inspect.getsource(ys.YinyangHandler._handle_links_stats)
    src += inspect.getsource(ys.YinyangHandler._handle_links_types)
    assert "9222" not in src
    assert "Companion App" not in src
