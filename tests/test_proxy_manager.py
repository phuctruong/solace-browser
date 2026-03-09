"""Tests for Task 089 — Proxy Manager."""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "e" * 64


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
    with ys._PROXY_LOCK:
        ys._PROXY_PROFILES.clear()
        ys._ACTIVE_PROXY = None


def test_proxy_add():
    h = make_handler({"protocol": "socks5", "host_hash": "host1", "port": 1080})
    h._handle_proxy_add()
    code, data = h._responses[0]
    assert code == 201
    assert data["profile_id"].startswith("prx_")
    assert data["status"] == "created"


def test_proxy_add_invalid_protocol():
    h = make_handler({"protocol": "ftp", "host_hash": "host1", "port": 21})
    h._handle_proxy_add()
    code, data = h._responses[0]
    assert code == 400
    assert "protocol" in data["error"]


def test_proxy_add_invalid_port():
    h = make_handler({"protocol": "http", "host_hash": "host1", "port": 99999})
    h._handle_proxy_add()
    code, data = h._responses[0]
    assert code == 400
    assert "port" in data["error"]


def test_proxy_add_port_zero():
    h = make_handler({"protocol": "http", "host_hash": "host1", "port": 0})
    h._handle_proxy_add()
    code, data = h._responses[0]
    assert code == 400


def test_proxy_list():
    h = make_handler({"protocol": "https", "host_hash": "h2", "port": 8080})
    h._handle_proxy_add()
    h2 = FakeHandler()
    h2._handle_proxy_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["profiles"], list)
    assert data["total"] >= 1


def test_proxy_delete():
    h = make_handler({"protocol": "socks4", "host_hash": "h3", "port": 9050})
    h._handle_proxy_add()
    profile_id = h._responses[0][1]["profile_id"]
    h2 = FakeHandler()
    h2._handle_proxy_delete(profile_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["profile_id"] == profile_id
    with ys._PROXY_LOCK:
        ids = [p["profile_id"] for p in ys._PROXY_PROFILES]
    assert profile_id not in ids


def test_proxy_delete_not_found():
    h = FakeHandler()
    h._handle_proxy_delete("prx_ghost")
    code, data = h._responses[0]
    assert code == 404


def test_proxy_activate():
    h = make_handler({"protocol": "socks5", "host_hash": "h4", "port": 1081})
    h._handle_proxy_add()
    profile_id = h._responses[0][1]["profile_id"]
    h2 = FakeHandler()
    h2._handle_proxy_activate(profile_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["status"] == "activated"


def test_proxy_active():
    h = make_handler({"protocol": "http", "host_hash": "h5", "port": 3128})
    h._handle_proxy_add()
    profile_id = h._responses[0][1]["profile_id"]
    h2 = FakeHandler()
    h2._handle_proxy_activate(profile_id)
    h3 = FakeHandler()
    h3._handle_proxy_active()
    code, data = h3._responses[0]
    assert code == 200
    assert data["active"] is not None
    assert data["active"]["profile_id"] == profile_id


def test_proxy_active_none():
    h = FakeHandler()
    h._handle_proxy_active()
    code, data = h._responses[0]
    assert code == 200
    assert data["active"] is None


def test_proxy_protocols():
    h = FakeHandler()
    h._handle_proxy_protocols()
    code, data = h._responses[0]
    assert code == 200
    assert "socks5" in data["protocols"]
    assert "http" in data["protocols"]
