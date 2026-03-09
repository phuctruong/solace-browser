"""Tests for Resource Saver (Task 108). 10 tests."""
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
    ys._SAVED_RESOURCES.clear()


def test_resource_save():
    """POST saves resource with rsc_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/resource-saver/resources", {
        "resource_type": "script",
        "source": "page_load",
        "url_hash": "url_h",
        "content_hash": "content_h",
        "page_hash": "pg_h",
        "size_bytes": 1024,
    })
    h._handle_resource_save()
    assert h._status == 201
    resource = h._response["resource"]
    assert resource["resource_id"].startswith("rsc_")
    assert resource["resource_type"] == "script"


def test_resource_invalid_type():
    """POST with invalid resource_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/resource-saver/resources", {
        "resource_type": "INVALID",
        "source": "page_load",
        "url_hash": "u",
        "content_hash": "c",
        "page_hash": "p",
        "size_bytes": 0,
    })
    h._handle_resource_save()
    assert h._status == 400


def test_resource_invalid_source():
    """POST with invalid source returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/resource-saver/resources", {
        "resource_type": "image",
        "source": "INVALID_SOURCE",
        "url_hash": "u",
        "content_hash": "c",
        "page_hash": "p",
        "size_bytes": 0,
    })
    h._handle_resource_save()
    assert h._status == 400


def test_resource_list():
    """GET returns resources list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/resource-saver/resources", {
        "resource_type": "stylesheet",
        "source": "fetch",
        "url_hash": "u",
        "content_hash": "c",
        "page_hash": "p",
        "size_bytes": 500,
    })
    h._handle_resource_save()
    h2 = FakeHandler("GET", "/api/v1/resource-saver/resources")
    h2._handle_resource_list()
    assert h2._status == 200
    assert "resources" in h2._response
    assert h2._response["total"] == 1


def test_resource_delete():
    """DELETE resource returns 200."""
    _reset()
    h = FakeHandler("POST", "/api/v1/resource-saver/resources", {
        "resource_type": "font",
        "source": "xhr",
        "url_hash": "u",
        "content_hash": "c",
        "page_hash": "p",
        "size_bytes": 200,
    })
    h._handle_resource_save()
    resource_id = h._response["resource"]["resource_id"]

    dh = FakeHandler("DELETE", f"/api/v1/resource-saver/resources/{resource_id}")
    dh._handle_resource_delete(resource_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"


def test_resource_delete_not_found():
    """DELETE nonexistent resource returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/resource-saver/resources/rsc_nonexistent")
    h._handle_resource_delete("rsc_nonexistent")
    assert h._status == 404


def test_resource_by_type():
    """GET /by-type filters by resource_type."""
    _reset()
    # Save script and image
    for rt in ["script", "image"]:
        h = FakeHandler("POST", "/api/v1/resource-saver/resources", {
            "resource_type": rt,
            "source": "manual",
            "url_hash": f"u_{rt}",
            "content_hash": "c",
            "page_hash": "p",
            "size_bytes": 100,
        })
        h._handle_resource_save()
    # Filter by script
    h2 = FakeHandler("GET", "/api/v1/resource-saver/by-type?resource_type=script")
    h2._handle_resource_by_type("")
    assert h2._status == 200
    assert h2._response["total"] == 1
    assert h2._response["resources"][0]["resource_type"] == "script"


def test_resource_stats():
    """GET /stats returns total, by_type, total_size_bytes."""
    _reset()
    for rt, size in [("script", 100), ("script", 200), ("image", 50)]:
        h = FakeHandler("POST", "/api/v1/resource-saver/resources", {
            "resource_type": rt,
            "source": "page_load",
            "url_hash": "u",
            "content_hash": "c",
            "page_hash": "p",
            "size_bytes": size,
        })
        h._handle_resource_save()
    h2 = FakeHandler("GET", "/api/v1/resource-saver/stats")
    h2._handle_resource_stats()
    assert h2._status == 200
    data = h2._response
    assert data["total_resources"] == 3
    assert data["by_type"]["script"] == 2
    assert data["by_type"]["image"] == 1
    assert data["total_size_bytes"] == 350


def test_resource_types():
    """GET /resource-types returns 8 types."""
    h = FakeHandler("GET", "/api/v1/resource-saver/resource-types")
    h._handle_resource_types()
    assert h._status == 200
    assert len(h._response["resource_types"]) == 8


def test_resource_unauth():
    """POST without auth returns 401."""
    _reset()
    h = FakeHandler("POST", "/api/v1/resource-saver/resources", {
        "resource_type": "script",
        "source": "page_load",
        "url_hash": "u",
        "content_hash": "c",
        "page_hash": "p",
        "size_bytes": 0,
    }, auth=False)
    h._handle_resource_save()
    assert h._status == 401
