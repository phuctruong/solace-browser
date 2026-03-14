# Diagram: 05-solace-runtime-architecture
"""Tests for Task 073 — Network Traffic Logger."""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0", "Authorization": f"Bearer {VALID_TOKEN}"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass

    def send_response(self, code):
        self._responses.append((code, {}))

    def end_headers(self):
        pass


def make_handler(body=None):
    h = FakeHandler()
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._NETWORK_LOG_LOCK:
        ys._NETWORK_LOG.clear()


def test_network_record():
    h = make_handler({
        "url": "https://example.com/api",
        "method": "GET",
        "status_code": 200,
        "duration_ms": 120,
    })
    h._handle_network_log_record()
    code, data = h._responses[0]
    assert code == 201
    assert data["log_id"].startswith("nrl_")


def test_network_url_hashed():
    url = "https://secret.com/path"
    h = make_handler({"url": url, "method": "POST", "status_code": 201, "duration_ms": 50})
    h._handle_network_log_record()
    code, data = h._responses[0]
    assert code == 201
    with ys._NETWORK_LOG_LOCK:
        entry = ys._NETWORK_LOG[-1]
    assert entry["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    assert "url" not in entry


def test_network_domain_hashed():
    h = make_handler({"url": "https://domain.com/page", "method": "GET", "status_code": 200})
    h._handle_network_log_record()
    with ys._NETWORK_LOG_LOCK:
        entry = ys._NETWORK_LOG[-1]
    assert "domain_hash" in entry
    assert len(entry["domain_hash"]) == 64


def test_network_invalid_method():
    h = make_handler({"url": "https://x.com", "method": "INVALID", "status_code": 200})
    h._handle_network_log_record()
    code, data = h._responses[0]
    assert code == 400


def test_network_invalid_status():
    h = make_handler({"url": "https://x.com", "method": "GET", "status_code": 99})
    h._handle_network_log_record()
    code, data = h._responses[0]
    assert code == 400
    assert "100" in data["error"] or "599" in data["error"]


def test_network_list():
    h = make_handler({"url": "https://list.com", "method": "GET", "status_code": 200})
    h._handle_network_log_record()
    h2 = FakeHandler()
    h2._handle_network_log_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["requests"], list)
    assert data["total"] >= 1


def test_network_clear():
    h = make_handler({"url": "https://clear.com", "method": "DELETE", "status_code": 200})
    h._handle_network_log_record()
    h2 = FakeHandler()
    h2._handle_network_log_clear()
    code, data = h2._responses[0]
    assert code == 200
    with ys._NETWORK_LOG_LOCK:
        assert len(ys._NETWORK_LOG) == 0


def test_network_summary():
    h = make_handler({"url": "https://sum.com", "method": "GET", "status_code": 200})
    h._handle_network_log_record()
    h2 = FakeHandler()
    h2._handle_network_log_summary()
    code, data = h2._responses[0]
    assert code == 200
    assert "by_method" in data
    assert "total" in data


def test_network_methods_list():
    h = FakeHandler()
    h._handle_network_log_methods()
    code, data = h._responses[0]
    assert code == 200
    assert len(data["methods"]) == 7
    assert "GET" in data["methods"]
    assert "POST" in data["methods"]


def test_no_port_9222_in_network_log():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
