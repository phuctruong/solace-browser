# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 103 — Geo Location Tracker
Browser: yinyang_server.py routes /api/v1/geo-tracker/*
"""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


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

    def _send_json(self, data, status=200):
        self._status = status
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def setup_function():
    ys._GEO_PERMISSIONS.clear()


def test_record_permission_ok():
    h = FakeHandler("POST", "/api/v1/geo-tracker/permissions", {
        "site_hash": "a" * 64,
        "decision": "granted",
        "accuracy_level": "exact",
    })
    h._handle_geo_permission_record()
    assert h._status == 201
    assert h._response["record"]["perm_id"].startswith("gpr_")
    assert h._response["record"]["decision"] == "granted"


def test_record_invalid_decision():
    h = FakeHandler("POST", "/api/v1/geo-tracker/permissions", {
        "site_hash": "b" * 64,
        "decision": "BADDECISION",
        "accuracy_level": "exact",
    })
    h._handle_geo_permission_record()
    assert h._status == 400
    assert "decision" in h._response["error"]


def test_record_invalid_accuracy():
    h = FakeHandler("POST", "/api/v1/geo-tracker/permissions", {
        "site_hash": "c" * 64,
        "decision": "denied",
        "accuracy_level": "BADLEVEL",
    })
    h._handle_geo_permission_record()
    assert h._status == 400
    assert "accuracy_level" in h._response["error"]


def test_record_requires_auth():
    h = FakeHandler("POST", "/api/v1/geo-tracker/permissions", {
        "site_hash": "d" * 64,
        "decision": "granted",
        "accuracy_level": "city_level",
    }, auth=False)
    h._handle_geo_permission_record()
    assert h._status == 401


def test_list_permissions():
    h = FakeHandler("POST", "/api/v1/geo-tracker/permissions", {
        "site_hash": "e" * 64,
        "decision": "denied",
        "accuracy_level": "approximate",
    })
    h._handle_geo_permission_record()

    h2 = FakeHandler("GET", "/api/v1/geo-tracker/permissions")
    h2._handle_geo_permission_list()
    assert h2._status == 200
    assert h2._response["total"] >= 1


def test_delete_permission():
    h = FakeHandler("POST", "/api/v1/geo-tracker/permissions", {
        "site_hash": "f" * 64,
        "decision": "revoked",
        "accuracy_level": "country_level",
    })
    h._handle_geo_permission_record()
    perm_id = h._response["record"]["perm_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/geo-tracker/permissions/{perm_id}")
    h2._handle_geo_permission_delete(perm_id)
    assert h2._status == 200
    assert h2._response["status"] == "deleted"


def test_delete_permission_not_found():
    h = FakeHandler("DELETE", "/api/v1/geo-tracker/permissions/gpr_nonexistent")
    h._handle_geo_permission_delete("gpr_nonexistent")
    assert h._status == 404


def test_stats():
    h = FakeHandler("POST", "/api/v1/geo-tracker/permissions", {
        "site_hash": "g" * 64,
        "decision": "granted",
        "accuracy_level": "exact",
    })
    h._handle_geo_permission_record()

    h2 = FakeHandler("GET", "/api/v1/geo-tracker/stats")
    h2._handle_geo_stats()
    assert h2._status == 200
    assert "total_events" in h2._response
    assert "by_decision" in h2._response
    assert "by_accuracy" in h2._response
    assert "grant_rate" in h2._response
    assert float(h2._response["grant_rate"]) > 0


def test_stats_empty_grant_rate():
    # No records → grant_rate should still work
    h = FakeHandler("GET", "/api/v1/geo-tracker/stats")
    h._handle_geo_stats()
    assert h._status == 200
    assert h._response["grant_rate"] == "0.00"


def test_decisions_public():
    h = FakeHandler("GET", "/api/v1/geo-tracker/decisions", auth=False)
    h._handle_geo_decisions()
    assert h._status == 200
    assert "decisions" in h._response
    assert "granted" in h._response["decisions"]
