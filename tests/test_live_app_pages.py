from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_app_store_page_has_live_results_mount() -> None:
    html = _read(WEB_DIR / "app-store.html")
    assert 'id="app-store-categories"' in html
    assert 'src="/js/yinyang-delight.js"' in html


def test_app_detail_page_has_dynamic_sections() -> None:
    html = _read(WEB_DIR / "app-detail.html")
    assert 'id="app-inbox-sections"' in html
    assert 'id="app-outbox-sections"' in html
    assert 'id="app-runs-table-body"' in html
    assert 'src="/js/yinyang-delight.js"' in html


def test_settings_page_has_live_form_mounts_and_save_buttons() -> None:
    html = _read(WEB_DIR / "settings.html")
    assert 'data-settings-section="account"' in html
    assert 'data-settings-section="history"' in html
    assert 'data-settings-save="history"' in html
    assert 'data-settings-save="yinyang"' in html


def test_solace_js_fetches_live_app_and_settings_apis() -> None:
    script = _read(WEB_DIR / "js" / "solace.js")
    assert 'fetchJson("/api/apps"' in script
    assert 'fetchJson(`/api/apps/${encodeURIComponent(appId)}`' in script
    assert 'fetchJson("/api/settings"' in script
    assert "YinyangDelight" in script


def test_solace_js_wires_delight_events() -> None:
    script = _read(WEB_DIR / "js" / "solace.js")
    assert "respond(warmToken)" in script or ".respond(" in script
    assert ".celebrate(" in script
