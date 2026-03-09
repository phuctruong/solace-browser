"""Tests for Task 113 — Storage Quota Monitor."""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0", "Authorization": "Bearer valid"}

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
    return h


def setup_function():
    with ys._QUOTA_LOCK:
        ys._QUOTA_MEASUREMENTS.clear()


def test_measurement_create():
    h = make_handler({"storage_type": "localstorage", "used_bytes": 1024,
                      "quota_bytes": 10240, "site_url": "https://example.com"})
    h._handle_quota_create()
    code, data = h._responses[0]
    assert code == 201
    assert data["measurement"]["measurement_id"].startswith("sqm_")


def test_measurement_pct_used():
    h = make_handler({"storage_type": "indexeddb", "used_bytes": 5000,
                      "quota_bytes": 10000, "site_url": "https://example.com"})
    h._handle_quota_create()
    code, data = h._responses[0]
    assert code == 201
    pct = data["measurement"]["pct_used"]
    # 5000/10000 * 100 = 50.00
    assert pct == "50.00"
    # Must be a string (Decimal string)
    assert isinstance(pct, str)


def test_measurement_invalid_type():
    h = make_handler({"storage_type": "unknowntype", "used_bytes": 100,
                      "quota_bytes": 1000, "site_url": "https://x.com"})
    h._handle_quota_create()
    code, data = h._responses[0]
    assert code == 400
    assert "storage_type" in data["error"]


def test_measurement_negative_used():
    h = make_handler({"storage_type": "cache", "used_bytes": -1,
                      "quota_bytes": 1000, "site_url": "https://x.com"})
    h._handle_quota_create()
    code, data = h._responses[0]
    assert code == 400
    assert "used_bytes" in data["error"]


def test_measurement_zero_quota():
    h = make_handler({"storage_type": "cookies", "used_bytes": 0,
                      "quota_bytes": 0, "site_url": "https://x.com"})
    h._handle_quota_create()
    code, data = h._responses[0]
    assert code == 400
    assert "quota_bytes" in data["error"]


def test_measurement_list():
    h = make_handler({"storage_type": "sessionstorage", "used_bytes": 200,
                      "quota_bytes": 2000, "site_url": "https://list.com"})
    h._handle_quota_create()
    h2 = FakeHandler()
    h2._handle_quota_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["measurements"], list)
    assert data["total"] >= 1


def test_measurement_latest():
    # Create two measurements of different types
    h1 = make_handler({"storage_type": "localstorage", "used_bytes": 100,
                       "quota_bytes": 1000, "site_url": "https://a.com"})
    h1._handle_quota_create()
    h2 = make_handler({"storage_type": "indexeddb", "used_bytes": 500,
                       "quota_bytes": 5000, "site_url": "https://b.com"})
    h2._handle_quota_create()
    h3 = FakeHandler()
    h3._handle_quota_latest()
    code, data = h3._responses[0]
    assert code == 200
    assert "latest" in data
    assert "localstorage" in data["latest"]
    assert "indexeddb" in data["latest"]


def test_measurement_delete():
    h = make_handler({"storage_type": "serviceworker", "used_bytes": 300,
                      "quota_bytes": 3000, "site_url": "https://del.com"})
    h._handle_quota_create()
    mid = h._responses[0][1]["measurement"]["measurement_id"]
    h2 = FakeHandler()
    h2._handle_quota_delete(mid)
    code, data = h2._responses[0]
    assert code == 200
    assert data["measurement_id"] == mid
    with ys._QUOTA_LOCK:
        ids = [m["measurement_id"] for m in ys._QUOTA_MEASUREMENTS]
    assert mid not in ids


def test_storage_types_list():
    h = FakeHandler()
    h._handle_quota_storage_types()
    code, data = h._responses[0]
    assert code == 200
    types = data["storage_types"]
    assert len(types) == 6
    assert "localstorage" in types
    assert "indexeddb" in types
    assert "serviceworker" in types


def test_no_port_9222_in_quota():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "922" + "2" not in content, "Port 9222 found in yinyang_server.py — BANNED"
