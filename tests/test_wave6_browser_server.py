from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import solace_browser_server as sbs


class _DummyPage:
    url = "https://example.com"


class _DummyBrowser:
    def __init__(self, *, headless: bool) -> None:
        self.browser = object()
        self.headless = headless
        self.debug_ui = False
        self.current_page = _DummyPage()
        self.pages = {"p1": _DummyPage()}
        self.event_history = [{"type": "x"}]
        self.session_file = "artifacts/solace_session.json"


class _Req:
    def __init__(self, body: dict | None = None, fail_json: bool = False) -> None:
        self._body = body or {}
        self._fail_json = fail_json

    async def json(self):
        if self._fail_json:
            raise ValueError("bad-json")
        return self._body


@pytest.mark.asyncio
async def test_health_reports_headless_mode() -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    resp = await server._handle_health(None)  # type: ignore[arg-type]
    data = json.loads(resp.text)
    assert data["ok"] is True
    assert data["mode"] == "headless"


@pytest.mark.asyncio
async def test_health_reports_headed_mode() -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=False), port=9222)
    resp = await server._handle_health(None)  # type: ignore[arg-type]
    data = json.loads(resp.text)
    assert data["mode"] == "headed"


@pytest.mark.asyncio
async def test_status_includes_mode_and_session_block() -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    resp = await server._handle_status(None)  # type: ignore[arg-type]
    data = json.loads(resp.text)
    assert data["running"] is True
    assert data["mode"] == "headless"
    assert "session" in data
    assert "active_oauth3_tokens" in data


@pytest.mark.asyncio
async def test_discovery_rejects_invalid_json() -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    resp = await server._handle_discovery_map_site(_Req(fail_json=True))
    assert resp.status == 400


@pytest.mark.asyncio
async def test_discovery_requires_url() -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    resp = await server._handle_discovery_map_site(_Req({}))
    assert resp.status == 422


@pytest.mark.asyncio
async def test_discovery_generates_pm_triplet_and_recipe() -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    site = "wave6-test.example.com"
    resp = await server._handle_discovery_map_site(_Req({"url": f"https://{site}/"}))
    assert resp.status == 201
    data = json.loads(resp.text)
    assert data["ok"] is True
    artifacts = data["artifacts"]

    root = Path(sbs.__file__).resolve().parent
    mmd = root / artifacts["mmd"]
    sha = root / artifacts["sha256"]
    pm = root / artifacts["prime_mermaid"]
    recipe = root / artifacts["recipe"]
    assert mmd.exists()
    assert sha.exists()
    assert pm.exists()
    assert recipe.exists()


@pytest.mark.asyncio
async def test_discovery_normalizes_site_name() -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    resp = await server._handle_discovery_map_site(_Req({"url": "HTTPS://MixedCase.Example.COM/path"}))
    assert resp.status == 201
    data = json.loads(resp.text)
    assert data["site"] == "mixedcase.example.com"
