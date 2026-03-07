from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
        self._capture_pipeline = None
        self._capture_count = 0


class _Req:
    def __init__(
        self,
        body: dict | None = None,
        fail_json: bool = False,
        query: dict[str, str] | None = None,
    ) -> None:
        self._body = body or {}
        self._fail_json = fail_json
        self.query = query or {}

    async def json(self):
        if self._fail_json:
            raise ValueError("bad-json")
        return self._body


class _FakeSyncClient:
    def __init__(self) -> None:
        self.heartbeats: list[str] = []
        self.closed = False

    async def heartbeat(self, client_version: str) -> dict[str, object]:
        self.heartbeats.append(client_version)
        return {"ok": True}

    async def close(self) -> None:
        self.closed = True

    def get_status(self, *, pending_evidence: int = 0, pending_runs: int = 0):
        return SimpleNamespace(
            connected=True,
            last_push_iso=None,
            last_pull_iso=None,
            pending_evidence_count=pending_evidence,
            pending_runs_count=pending_runs,
            api_url="https://sync.example.test",
            auto_sync_enabled=False,
            evidence_auto_upload=False,
        )


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
async def test_status_includes_api_contract_and_capabilities() -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    resp = await server._handle_status(None)  # type: ignore[arg-type]
    data = json.loads(resp.text)
    assert data["api_methods"]["screenshot"] == "POST"
    assert data["api_methods"]["snapshot"] == "POST"
    assert data["api_methods"]["page_snapshot"] == "GET"
    assert data["capabilities"]["snapshot_modes"] == ["aria", "dom", "page", "screenshot", "snapshot"]
    assert data["capabilities"]["prime_wiki_local"] is False
    assert data["capabilities"]["prime_mermaid_local"] is False


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


def test_build_sync_config_from_args_overrides_env() -> None:
    if not sbs.SYNC_AVAILABLE:
        pytest.skip("sync module unavailable")

    args = sbs.build_arg_parser().parse_args(
        [
            "--sync-api-url",
            "https://sync.example.test",
            "--sync-api-key",
            "cli-key-123",
            "--sync-interval",
            "60",
        ]
    )

    with patch.dict(
        "os.environ",
        {
            "SOLACE_API_URL": "https://env.example.test",
            "SOLACE_API_KEY": "env-key-456",
            "SOLACE_AUTO_SYNC_INTERVAL": "5",
        },
        clear=False,
    ):
        config = sbs.build_sync_config(args)

    assert config is not None
    assert config.api_url == "https://sync.example.test"
    assert config.api_key == "cli-key-123"
    assert config.auto_sync_interval_seconds == 60


def test_version_flag_prints_version_and_exits(capsys: pytest.CaptureFixture[str]) -> None:
    parser = sbs.build_arg_parser()

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--version"])

    captured = capsys.readouterr()
    assert excinfo.value.code == 0
    assert captured.out.strip() == f"solace-browser {sbs.__version__}"


def test_ensure_playwright_browsers_path_sets_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setattr(sbs.Path, "home", lambda *args, **kwargs: tmp_path)

    path = sbs._ensure_playwright_browsers_path()

    assert path == tmp_path / ".cache" / "ms-playwright"
    assert path.is_dir()
    assert sbs.os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(path)


def test_is_missing_playwright_executable_error_detects_expected_message() -> None:
    exc = RuntimeError(
        "BrowserType.launch: Executable doesn't exist at /tmp/x\n"
        "Please run the following command to download new browsers: playwright install"
    )
    assert sbs._is_missing_playwright_executable_error(exc) is True
    assert sbs._is_missing_playwright_executable_error(RuntimeError("other")) is False


def test_install_playwright_browser_uses_driver_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import playwright._impl._driver as driver

    target = tmp_path / "pw-cache"
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(target))
    monkeypatch.setattr(driver, "compute_driver_executable", lambda: ("/tmp/node", "/tmp/cli.js"))
    monkeypatch.setattr(driver, "get_driver_env", lambda: {"BASE": "1"})

    calls: list[dict[str, object]] = []

    def fake_run(cmd, *, capture_output, text, env, timeout):
        calls.append(
            {
                "cmd": cmd,
                "capture_output": capture_output,
                "text": text,
                "env": env,
                "timeout": timeout,
            }
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(sbs.subprocess, "run", fake_run)

    sbs._install_playwright_browser("chromium", timeout_seconds=12)

    assert len(calls) == 1
    assert calls[0]["cmd"] == ["/tmp/node", "/tmp/cli.js", "install", "chromium"]
    assert calls[0]["timeout"] == 12
    env = calls[0]["env"]
    assert isinstance(env, dict)
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(target)


@pytest.mark.asyncio
async def test_start_sync_services_sends_startup_heartbeat_when_api_key_present() -> None:
    if not sbs.SYNC_AVAILABLE:
        pytest.skip("sync module unavailable")

    config = sbs.SyncConfig(api_key="sync-key", auto_sync_interval_seconds=0)
    server = sbs.SolaceBrowserServer(
        _DummyBrowser(headless=True),
        port=9222,
        sync_config=config,
    )
    fake_client = _FakeSyncClient()
    server._sync_client = fake_client

    await server._start_sync_services()
    await server._stop_sync_services()

    assert fake_client.heartbeats == [f"solace-browser {sbs.__version__}"]
    assert fake_client.closed is True


@pytest.mark.asyncio
async def test_start_sync_services_skips_heartbeat_without_api_key() -> None:
    if not sbs.SYNC_AVAILABLE:
        pytest.skip("sync module unavailable")

    config = sbs.SyncConfig(api_key="", auto_sync_interval_seconds=60)
    server = sbs.SolaceBrowserServer(
        _DummyBrowser(headless=True),
        port=9222,
        sync_config=config,
    )
    fake_client = _FakeSyncClient()
    server._sync_client = fake_client

    await server._start_sync_services()
    await server._stop_sync_services()

    assert fake_client.heartbeats == []
    assert server._sync_heartbeat_task is None


@pytest.mark.asyncio
async def test_start_sync_services_starts_background_heartbeat_task() -> None:
    if not sbs.SYNC_AVAILABLE:
        pytest.skip("sync module unavailable")

    config = sbs.SyncConfig(api_key="sync-key", auto_sync_interval_seconds=60)
    server = sbs.SolaceBrowserServer(
        _DummyBrowser(headless=True),
        port=9222,
        sync_config=config,
    )
    fake_client = _FakeSyncClient()
    server._sync_client = fake_client

    await server._start_sync_services()

    assert fake_client.heartbeats == [f"solace-browser {sbs.__version__}"]
    assert server._sync_heartbeat_task is not None

    await server._stop_sync_services()
    assert fake_client.closed is True


@pytest.mark.asyncio
async def test_finalize_part11_result_calls_upload_hook_after_evidence_capture() -> None:
    browser = sbs.SolaceBrowser(headless=True)
    browser.part11["enabled"] = True

    async def fake_upload_hook(evidence: dict[str, object]) -> dict[str, object]:
        return {"status": "complete", "event_id": evidence["event_id"]}

    browser.set_part11_upload_hook(fake_upload_hook)
    browser._capture_part11_evidence = AsyncMock(  # type: ignore[method-assign]
        return_value={"event_id": "e000001", "session_id": "session-001"}
    )

    payload = await browser._finalize_part11_result("navigate", "https://example.com", {})

    assert payload["part11"]["event_id"] == "e000001"
    assert payload["part11_upload"]["status"] == "complete"


@pytest.mark.asyncio
async def test_auto_upload_pending_evidence_skips_when_disabled() -> None:
    if not sbs.SYNC_AVAILABLE:
        pytest.skip("sync module unavailable")

    config = sbs.SyncConfig(api_key="sync-key", evidence_auto_upload=False)
    server = sbs.SolaceBrowserServer(
        _DummyBrowser(headless=True),
        port=9222,
        sync_config=config,
    )
    server._sync_client = _FakeSyncClient()

    result = await server._auto_upload_pending_evidence({"event_id": "e000001"})

    assert result["status"] == "skipped"
    assert result["reason"] == "evidence_auto_upload_disabled"


@pytest.mark.asyncio
async def test_auto_upload_pending_evidence_runs_when_enabled() -> None:
    if not sbs.SYNC_AVAILABLE:
        pytest.skip("sync module unavailable")

    config = sbs.SyncConfig(api_key="sync-key", evidence_auto_upload=True)
    server = sbs.SolaceBrowserServer(
        _DummyBrowser(headless=True),
        port=9222,
        sync_config=config,
    )
    server._sync_client = _FakeSyncClient()

    class _Collector:
        audit_dir = Path("/tmp/test-audit")
        pending_count = 1

    server._evidence_collector = _Collector()

    with patch.object(
        sbs,
        "upload_pending_evidence",
        autospec=True,
        return_value={"status": "complete", "uploaded": 1, "failed": 0},
    ) as upload_mock:
        result = await server._auto_upload_pending_evidence({"event_id": "e000001"})

    upload_mock.assert_awaited_once()
    assert result["status"] == "complete"
    assert result["uploaded"] == 1
    assert server._last_evidence_upload["status"] == "complete"


@pytest.mark.asyncio
async def test_sync_status_includes_last_evidence_upload() -> None:
    if not sbs.SYNC_AVAILABLE:
        pytest.skip("sync module unavailable")

    config = sbs.SyncConfig(api_key="sync-key", evidence_auto_upload=True)
    server = sbs.SolaceBrowserServer(
        _DummyBrowser(headless=True),
        port=9222,
        sync_config=config,
    )
    server._sync_client = _FakeSyncClient()
    server._last_evidence_upload = {"status": "complete", "uploaded": 1}

    class _Collector:
        pending_count = 0

    server._evidence_collector = _Collector()

    resp = await server._handle_sync_status(None)  # type: ignore[arg-type]
    data = json.loads(resp.text)

    assert data["last_evidence_upload"]["status"] == "complete"


@pytest.mark.asyncio
async def test_captcha_handler_returns_503_when_competitive_features_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    monkeypatch.setattr(sbs, "solve_captcha", None)

    resp = await server._handle_captcha_solve(
        _Req(
            {
                "provider": "mock",
                "captcha_type": "recaptcha_v2",
                "site_key": "abc",
                "page_url": "https://example.com",
            }
        )
    )

    assert resp.status == 503


@pytest.mark.asyncio
async def test_proxy_load_returns_503_when_competitive_features_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    monkeypatch.setattr(sbs, "load_proxy_config", None)

    resp = await server._handle_proxy_load(_Req({"path": "data/custom/proxy-config.yaml"}))

    assert resp.status == 503


@pytest.mark.asyncio
async def test_proxy_select_returns_503_when_competitive_features_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    monkeypatch.setattr(sbs, "select_proxy", None)

    resp = await server._handle_proxy_select(_Req(query={"country": "us"}))

    assert resp.status == 503


@pytest.mark.asyncio
async def test_webvoyager_score_returns_503_when_competitive_features_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    server = sbs.SolaceBrowserServer(_DummyBrowser(headless=True), port=9222)
    monkeypatch.setattr(sbs, "webvoyager_score", None)

    resp = await server._handle_webvoyager_score(_Req({"cases": []}))

    assert resp.status == 503
