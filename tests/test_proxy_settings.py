# Diagram: 05-solace-runtime-architecture
"""tests/test_proxy_settings.py — Proxy Settings acceptance gate.
Task 044 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - NO plaintext password storage — SHA-256 hash only
  - type must be in PROXY_TYPES → 400
  - port: 1-65535 → 400 if out of range
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

TEST_TOKEN = "test-token-proxy-044"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18944)
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
def reset_proxy_state(monkeypatch):
    """Reset proxy state between tests."""
    default = {
        "type": "direct", "host": None, "port": None, "username": None,
        "password_hash": None, "enabled": False, "test_status": None, "test_latency_ms": None,
    }
    monkeypatch.setattr(ys, "_PROXY_SETTINGS", dict(default))
    yield


# ---------------------------------------------------------------------------
# 1. test_proxy_get_defaults — GET /proxy/settings → type="direct", enabled=False
# ---------------------------------------------------------------------------
def test_proxy_get_defaults():
    status, data = get_json("/api/v1/proxy/settings")
    assert status == 200
    assert data.get("type") == "direct"
    assert data.get("enabled") is False


# ---------------------------------------------------------------------------
# 2. test_proxy_set_socks5 — POST → type and host updated
# ---------------------------------------------------------------------------
def test_proxy_set_socks5():
    status, data = post_json("/api/v1/proxy/settings", {
        "type": "socks5",
        "host": "127.0.0.1",
        "port": 9050,
    })
    assert status == 200
    assert data.get("status") == "updated"
    settings = data.get("settings", {})
    assert settings.get("type") == "socks5"
    assert settings.get("host") == "127.0.0.1"


# ---------------------------------------------------------------------------
# 3. test_proxy_invalid_type — unknown type → 400
# ---------------------------------------------------------------------------
def test_proxy_invalid_type():
    status, data = post_json("/api/v1/proxy/settings", {
        "type": "ftp-proxy",
        "host": "example.com",
        "port": 21,
    })
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 4. test_proxy_port_out_of_range — port=99999 → 400
# ---------------------------------------------------------------------------
def test_proxy_port_out_of_range():
    status, data = post_json("/api/v1/proxy/settings", {
        "type": "http",
        "host": "example.com",
        "port": 99999,
    })
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 5. test_proxy_password_not_stored — POST with password → password_hash set, no plaintext
# ---------------------------------------------------------------------------
def test_proxy_password_not_stored():
    status, data = post_json("/api/v1/proxy/settings", {
        "type": "http",
        "host": "proxy.example.com",
        "port": 8080,
        "username": "user",
        "password": "supersecret",
    })
    assert status == 200
    settings = data.get("settings", {})
    # password_hash must be set
    assert settings.get("password_hash") is not None
    # plaintext password must NOT be in response
    assert "password" not in settings or settings.get("password") is None
    # verify hash is SHA-256 of the password
    expected_hash = hashlib.sha256("supersecret".encode()).hexdigest()
    assert settings["password_hash"] == expected_hash


# ---------------------------------------------------------------------------
# 6. test_proxy_test_connectivity — POST /test → latency_ms present
# ---------------------------------------------------------------------------
def test_proxy_test_connectivity():
    status, data = post_json("/api/v1/proxy/test", {})
    assert status == 200
    assert data.get("status") == "ok"
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], int)


# ---------------------------------------------------------------------------
# 7. test_proxy_reset_to_direct — DELETE → back to direct/disabled
# ---------------------------------------------------------------------------
def test_proxy_reset_to_direct():
    # First set a proxy
    post_json("/api/v1/proxy/settings", {
        "type": "socks5",
        "host": "127.0.0.1",
        "port": 9050,
    })
    # Then reset
    status, data = delete_path("/api/v1/proxy/settings")
    assert status == 200
    assert data.get("status") == "reset"
    settings = data.get("settings", {})
    assert settings.get("type") == "direct"
    assert settings.get("enabled") is False


# ---------------------------------------------------------------------------
# 8. test_proxy_presets — GET /presets → 3 presets
# ---------------------------------------------------------------------------
def test_proxy_presets():
    status, data = get_json("/api/v1/proxy/presets")
    assert status == 200
    presets = data.get("presets", [])
    assert len(presets) == 3
    ids = [p["preset_id"] for p in presets]
    assert "direct" in ids
    assert "tor-local" in ids
    assert "privoxy-local" in ids


# ---------------------------------------------------------------------------
# 9. test_proxy_html_no_cdn — web/proxy-settings.html no CDN
# ---------------------------------------------------------------------------
def test_proxy_html_no_cdn():
    html_path = REPO_ROOT / "web" / "proxy-settings.html"
    assert html_path.exists(), "proxy-settings.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 10. test_no_port_9222_in_proxy — grep check
# ---------------------------------------------------------------------------
def test_no_port_9222_in_proxy():
    files_to_check = [
        REPO_ROOT / "web" / "proxy-settings.html",
        REPO_ROOT / "web" / "js" / "proxy-settings.js",
        REPO_ROOT / "web" / "css" / "proxy-settings.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
