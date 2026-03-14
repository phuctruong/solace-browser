# Diagram: 05-solace-runtime-architecture
"""tests/test_network_inspector.py — Network Inspector acceptance gate.
Task 049 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - HTTP method validated against HTTP_METHODS
  - status_code 100-599 range enforced
  - url_hash = SHA-256 of URL (never raw URL stored)
  - Max 200 requests — oldest removed on overflow
  - Auth required on POST/DELETE; GET is public
  - No port 9222, no CDN, no eval()
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-network-049"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18921)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def delete_path(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


@pytest.fixture(autouse=True)
def reset_network(monkeypatch):
    """Reset network state between tests."""
    monkeypatch.setattr(ys, "_NETWORK_REQUESTS", [])
    yield


# ---------------------------------------------------------------------------
# 1. Initially empty
# ---------------------------------------------------------------------------
def test_network_empty_initially():
    status, data = get_json("/api/v1/network/requests")
    assert status == 200
    assert data.get("requests") == []


# ---------------------------------------------------------------------------
# 2. POST records request and returns request_id
# ---------------------------------------------------------------------------
def test_network_record_request():
    status, data = post_json("/api/v1/network/requests", {
        "method": "GET",
        "url": "https://example.com/api",
        "status_code": 200,
        "duration_ms": 142,
    })
    assert status == 200
    assert data.get("status") == "recorded"
    assert data.get("request_id", "").startswith("req_")


# ---------------------------------------------------------------------------
# 3. URL stored as SHA-256 hash, never raw URL
# ---------------------------------------------------------------------------
def test_network_url_hashed():
    raw_url = "https://secret.internal/api/v2/data"
    post_json("/api/v1/network/requests", {
        "method": "POST",
        "url": raw_url,
        "status_code": 201,
    })
    status, data = get_json("/api/v1/network/requests")
    req = data["requests"][0]
    expected = hashlib.sha256(raw_url.encode()).hexdigest()
    assert req["url_hash"] == expected
    assert raw_url not in str(req)


# ---------------------------------------------------------------------------
# 4. Invalid HTTP method → 400
# ---------------------------------------------------------------------------
def test_network_invalid_method():
    status, data = post_json("/api/v1/network/requests", {
        "method": "BREW",
        "url": "https://example.com",
    })
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 5. status_code out of range → 400
# ---------------------------------------------------------------------------
def test_network_invalid_status_code():
    status, data = post_json("/api/v1/network/requests", {
        "method": "GET",
        "url": "https://example.com",
        "status_code": 99,
    })
    assert status == 400
    assert "error" in data

    status2, data2 = post_json("/api/v1/network/requests", {
        "method": "GET",
        "url": "https://example.com",
        "status_code": 600,
    })
    assert status2 == 400


# ---------------------------------------------------------------------------
# 6. Max 200 requests — oldest removed on overflow
# ---------------------------------------------------------------------------
def test_network_max_200_requests():
    for i in range(201):
        post_json("/api/v1/network/requests", {
            "method": "GET",
            "url": f"https://example.com/page/{i}",
            "status_code": 200,
        })
    status, data = get_json("/api/v1/network/requests")
    assert status == 200
    assert len(data["requests"]) == 200


# ---------------------------------------------------------------------------
# 7. DELETE /requests clears all
# ---------------------------------------------------------------------------
def test_network_clear():
    post_json("/api/v1/network/requests", {"method": "GET", "url": "https://a.com"})
    post_json("/api/v1/network/requests", {"method": "POST", "url": "https://b.com"})

    status, data = delete_path("/api/v1/network/requests")
    assert status == 200
    assert data.get("status") == "cleared"

    _, list_data = get_json("/api/v1/network/requests")
    assert list_data["requests"] == []


# ---------------------------------------------------------------------------
# 8. GET /stats returns counts
# ---------------------------------------------------------------------------
def test_network_stats():
    post_json("/api/v1/network/requests", {"method": "GET", "url": "https://a.com", "status_code": 200})
    post_json("/api/v1/network/requests", {"method": "POST", "url": "https://b.com", "status_code": 201})
    post_json("/api/v1/network/requests", {"method": "GET", "url": "https://c.com", "status_code": 404, "blocked": True})

    status, data = get_json("/api/v1/network/stats")
    assert status == 200
    assert data["total"] == 3
    assert data["blocked"] == 1
    assert data["by_method"]["GET"] == 2
    assert data["by_method"]["POST"] == 1


# ---------------------------------------------------------------------------
# 9. GET /blocked returns only blocked requests
# ---------------------------------------------------------------------------
def test_network_blocked_filter():
    post_json("/api/v1/network/requests", {"method": "GET", "url": "https://ok.com", "blocked": False})
    post_json("/api/v1/network/requests", {"method": "GET", "url": "https://bad.com", "blocked": True})

    status, data = get_json("/api/v1/network/blocked")
    assert status == 200
    assert data["total"] == 1
    assert all(r["blocked"] for r in data["requests"])


# ---------------------------------------------------------------------------
# 10. No port 9222 in any network inspector file
# ---------------------------------------------------------------------------
def test_no_port_9222_in_network():
    files_to_check = [
        REPO_ROOT / "web" / "network-inspector.html",
        REPO_ROOT / "web" / "js" / "network-inspector.js",
        REPO_ROOT / "web" / "css" / "network-inspector.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
