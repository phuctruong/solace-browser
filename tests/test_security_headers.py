"""Tests for security headers on all HTTP responses from web/server.py.

Tower 6 (Hackers) audit: verify Content-Security-Policy, X-Content-Type-Options,
X-Frame-Options, X-XSS-Protection, Referrer-Policy, and Permissions-Policy
are present on every response.
"""
from __future__ import annotations

import importlib.util
import socket
import threading
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO_ROOT / "web" / "server.py"


def _load_server_module() -> Any:
    spec = importlib.util.spec_from_file_location("solace_web_server_sec", SERVER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def solace_home(tmp_path: Path) -> Path:
    """Create a minimal solace home directory for the server."""
    home = tmp_path / "solace-home"
    app_root = home / "apps" / "test-app"
    for d in [app_root / "inbox", app_root / "outbox"]:
        d.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "test-app",
        "name": "Test App",
        "description": "Security header test app",
        "category": "test",
        "status": "installed",
        "safety": "B",
        "site": "example.com",
        "scopes": [],
    }
    (app_root / "manifest.yaml").write_text(yaml.dump(manifest), encoding="utf-8")
    settings = {
        "privacy": {"history_local_only": True, "vault_encrypted": True, "cloud_sync_optional": True},
        "yinyang": {"top_rail": True, "bottom_rail": True, "max_transcript": 24, "session_ttl_min": 30},
        "about": {"version": "0.5.0-dev", "build": "source", "web_ui_port": 8791},
    }
    (home / "settings.yaml").write_text(yaml.dump(settings), encoding="utf-8")
    return home


@pytest.fixture()
def running_server(solace_home: Path) -> str:
    """Spin up a real ThreadingHTTPServer and return its base URL."""
    server_module = _load_server_module()
    port = _find_free_port()
    server = server_module.create_server(
        "127.0.0.1",
        port,
        data_store=server_module.SolaceDataStore(solace_home=solace_home),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get_headers(url: str) -> dict[str, str]:
    """Perform a GET request and return response headers as a dict."""
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=5) as response:
        return dict(response.headers)


# ---------------------------------------------------------------------------
# Individual header tests
# ---------------------------------------------------------------------------

class TestContentSecurityPolicy:
    """Content-Security-Policy header blocks XSS and injection attacks."""

    def test_csp_header_present(self, running_server: str) -> None:
        headers = _get_headers(f"{running_server}/api/apps")
        assert "Content-Security-Policy" in headers

    def test_csp_default_src_self(self, running_server: str) -> None:
        csp = _get_headers(f"{running_server}/api/apps")["Content-Security-Policy"]
        assert "default-src 'self'" in csp

    def test_csp_script_src(self, running_server: str) -> None:
        csp = _get_headers(f"{running_server}/api/apps")["Content-Security-Policy"]
        assert "script-src 'self' 'unsafe-inline'" in csp

    def test_csp_style_src(self, running_server: str) -> None:
        csp = _get_headers(f"{running_server}/api/apps")["Content-Security-Policy"]
        assert "style-src 'self' 'unsafe-inline'" in csp

    def test_csp_img_src(self, running_server: str) -> None:
        csp = _get_headers(f"{running_server}/api/apps")["Content-Security-Policy"]
        assert "img-src 'self' data: https:" in csp

    def test_csp_font_src(self, running_server: str) -> None:
        csp = _get_headers(f"{running_server}/api/apps")["Content-Security-Policy"]
        assert "font-src 'self'" in csp

    def test_csp_connect_src_includes_prod(self, running_server: str) -> None:
        csp = _get_headers(f"{running_server}/api/apps")["Content-Security-Policy"]
        assert "https://solaceagi-mfjzxmegpq-uc.a.run.app" in csp

    def test_csp_connect_src_includes_qa(self, running_server: str) -> None:
        csp = _get_headers(f"{running_server}/api/apps")["Content-Security-Policy"]
        assert "https://solaceagi-qa-mfjzxmegpq-uc.a.run.app" in csp


class TestXContentTypeOptions:
    """X-Content-Type-Options prevents MIME-type sniffing."""

    def test_header_present(self, running_server: str) -> None:
        headers = _get_headers(f"{running_server}/api/apps")
        assert headers.get("X-Content-Type-Options") == "nosniff"


class TestXFrameOptions:
    """X-Frame-Options prevents clickjacking via iframe embedding."""

    def test_header_present(self, running_server: str) -> None:
        headers = _get_headers(f"{running_server}/api/apps")
        assert headers.get("X-Frame-Options") == "DENY"


class TestXXSSProtection:
    """X-XSS-Protection enables browser-level XSS filtering."""

    def test_header_present(self, running_server: str) -> None:
        headers = _get_headers(f"{running_server}/api/apps")
        assert headers.get("X-XSS-Protection") == "1; mode=block"


class TestReferrerPolicy:
    """Referrer-Policy controls how much referrer info is sent."""

    def test_header_present(self, running_server: str) -> None:
        headers = _get_headers(f"{running_server}/api/apps")
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class TestPermissionsPolicy:
    """Permissions-Policy restricts access to browser features."""

    def test_header_present(self, running_server: str) -> None:
        headers = _get_headers(f"{running_server}/api/apps")
        assert headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"


class TestSecurityHeadersOnDifferentEndpoints:
    """Verify security headers are set on all response types, not just API."""

    REQUIRED_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    def test_api_endpoint_has_all_headers(self, running_server: str) -> None:
        headers = _get_headers(f"{running_server}/api/apps")
        for name, value in self.REQUIRED_HEADERS.items():
            assert headers.get(name) == value, f"Missing or wrong: {name}"
        assert "Content-Security-Policy" in headers

    def test_home_page_has_all_headers(self, running_server: str) -> None:
        headers = _get_headers(f"{running_server}/")
        for name, value in self.REQUIRED_HEADERS.items():
            assert headers.get(name) == value, f"Missing or wrong on /: {name}"
        assert "Content-Security-Policy" in headers
