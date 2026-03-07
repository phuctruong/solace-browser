"""i18n coverage + hardcoded-text regression tests.

Goals:
1) `/api/locale` must serve all locale files in app/locales/yinyang (47 locales).
2) Rail scripts must use runtime i18n plumbing (no hardcoded English UI copy).
"""
from __future__ import annotations

import importlib.util
import json
import socket
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO_ROOT / "web" / "server.py"
LOCALES_DIR = REPO_ROOT / "app" / "locales" / "yinyang"
YINYANG_RAIL_JS = REPO_ROOT / "web" / "js" / "yinyang-rail.js"
BOTTOM_RAIL_JS = REPO_ROOT / "static" / "bottom_rail.js"
YINYANG_TUTORIAL_JS = REPO_ROOT / "web" / "js" / "yinyang-tutorial.js"


def _load_server_module() -> Any:
    spec = importlib.util.spec_from_file_location("solace_web_server_i18n", SERVER_PATH)
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
    """Create a minimal Solace home for web/server tests."""
    home = tmp_path / "solace-home"
    app_root = home / "apps" / "test-app"
    for d in [app_root / "inbox", app_root / "outbox"]:
        d.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "test-app",
        "name": "Test App",
        "description": "i18n test app",
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
    """Spin up a real ThreadingHTTPServer and return base URL."""
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


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


class TestLocaleEndpointCoverage:
    """`/api/locale` should faithfully return each locale payload."""

    def test_api_locale_round_trips_all_locale_files(self, running_server: str) -> None:
        locale_files = sorted(LOCALES_DIR.glob("*.json"))
        assert len(locale_files) == 47, "Expected 47 locale files in app/locales/yinyang"

        for locale_file in locale_files:
            locale = locale_file.stem
            expected = json.loads(locale_file.read_text(encoding="utf-8"))
            expected = {k: v for k, v in expected.items() if not k.startswith("_")}

            query = urllib.parse.urlencode({"locale": locale})
            actual = _get_json(f"{running_server}/api/locale?{query}")

            assert actual == expected, f"Locale payload mismatch for locale='{locale}'"


class TestRailI18nRegression:
    """Block regressions back to hardcoded English in rail scripts."""

    def test_bottom_rail_uses_injected_i18n_bundle(self) -> None:
        js = BOTTOM_RAIL_JS.read_text(encoding="utf-8")
        assert "window.YINYANG_I18N" in js
        assert "Ask Yinyang" not in js
        assert "Reconnecting" not in js

    def test_yinyang_rail_loads_ui_locale_bundle(self) -> None:
        js = YINYANG_RAIL_JS.read_text(encoding="utf-8")
        assert "/api/locale?key=ui" in js
        assert "Run Gmail Triage" not in js
        assert "Ask Yinyang anything" not in js

    def test_tutorial_uses_locale_api_instead_of_embedded_copy(self) -> None:
        js = YINYANG_TUTORIAL_JS.read_text(encoding="utf-8")
        assert "/api/locale?key=tutorial" in js
        assert "step1_title" not in js
        assert "Choose your language" not in js
