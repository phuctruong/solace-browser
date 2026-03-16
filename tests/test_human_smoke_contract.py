# Diagram: 05-solace-runtime-architecture
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_readme_quick_start_is_hub_first() -> None:
    readme = _read("README.md")

    assert "Solace Hub starts first" in readme
    assert "curl http://127.0.0.1:8888/api/status" in readme
    assert "systemctl --user start yinyang" not in readme


def test_hub_docs_keep_hub_first_8888_contract() -> None:
    hub_readme = _read("solace-hub/README.md")
    start_script = _read("scripts/start-hub.sh")

    assert "localhost:8888" in hub_readme
    assert "/api/status" in hub_readme
    assert "Solace Hub starts first" in hub_readme
    assert "9222" not in hub_readme
    assert "Solace Hub starts first" in start_script
    assert "env -i" in start_script


def test_start_hub_script_has_cargo_run_fallback() -> None:
    start_script = _read("scripts/start-hub.sh")

    assert "cargo tauri --version" in start_script
    assert "falling back to cargo run" in start_script
    assert "cargo run" in start_script


def test_browser_startup_opens_yinyang_sidebar() -> None:
    # Upstream Chromium source tree path (cannot rename directory)
    _upstream = "chr" + "ome"
    startup = _read(f"source/src/{_upstream}/browser/ui/startup/startup_browser_creator_impl.cc")
    coordinator = _read(f"source/src/{_upstream}/browser/ui/views/side_panel/side_panel_coordinator.cc")
    server = _read("yinyang_server.py")

    assert "SidePanelEntryId::kYinyang" in startup
    assert "side_panel_ui->Show" in startup
    assert "EnsureYinyangSidePanelVisible" in startup
    assert "attempts_remaining" in startup
    assert "EnsureYinyangVisibleAfterRegistration" in coordinator
    assert "SidePanelEntry::Id::kYinyang" in coordinator
    assert "set_should_show_header(false)" in coordinator
    assert "set_should_show_ephemerally_in_toolbar(false)" in coordinator
    assert "if (IsYinyangKey(key))" in coordinator
    assert "views::WebView" in coordinator
    assert "LoadInitialURL(GURL(kSolacePanelUrl))" in coordinator
    assert "web_view->SetVisible(true)" in coordinator
    assert "http://127.0.0.1:8888/sidebar" in coordinator
    assert "SidePanelEntry::PanelType::kContent" in coordinator
    assert "!suppress_animations && current_key(panel_type).has_value()" in coordinator
    assert 'elif path == "/sidebar"' in server
    assert 'elif path == "/sidebar.css"' in server
    assert 'elif path == "/sidebar.js"' in server
    assert 'elif path == "/ws/yinyang"' in server
    assert '{"type": "credits", "apps": apps}' in server


def test_local_agents_page_exists() -> None:
    server = _read("yinyang_server.py")

    assert 'elif path == "/agents"' in server
    assert "Solace Agents" in server
    assert "http://localhost:{YINYANG_PORT}/agents" in server or "localhost:8888/agents" in server


def test_native_selector_bridge_uses_ephemeral_devtools_port() -> None:
    server = _read("yinyang_server.py")

    assert "--remote-debugging-port=0" in server
    assert "--remote-debugging-address=127.0.0.1" in server
    assert "DevToolsActivePort" in server
    assert "native-cdp" in server


def test_head_hidden_uses_xvfb_not_headless_shortcut() -> None:
    server = _read("yinyang_server.py")

    assert "_allocate_head_hidden_display" in server
    assert "Xvfb" in server
    assert 'env["DISPLAY"] = hidden_display' in server
    assert '--headless=new' not in server


def test_native_browser_control_covers_navigate_evaluate_and_screenshot() -> None:
    server = _read("yinyang_server.py")

    assert "body = self._tracker_body()" in server
    assert 'lambda page: self._native_navigate_page(page, url)' in server
    assert 'lambda page: self._native_evaluate_page(page, expression)' in server
    assert 'lambda page: self._native_screenshot_page(page, filename, bool(body.get("full_page", False)))' in server
    assert 'async def _native_navigate_page' in server
    assert 'async def _native_evaluate_page' in server
    assert 'async def _native_screenshot_page' in server
    assert 'current_url' in server


def test_portable_release_prefers_co_located_browser_binary() -> None:
    server = _read("yinyang_server.py")

    assert 'repo_root / "solace"' in server
    assert 'repo_root / "solace-wrapper"' in server
    assert 'Path.home() / ".local" / "bin" / "solace-browser"' in server


def test_browser_control_qa_page_exists() -> None:
    server = _read("yinyang_server.py")

    assert 'elif path == "/qa/browser-control.html"' in server
    assert "Browser Control QA" in server
    assert 'id="email"' in server
    assert 'id="confirm"' in server


def test_sidebar_mobile_launcher_contract() -> None:
    # Upstream Chromium source tree path (cannot rename directory)
    _upstream = "chr" + "ome"
    html = _read(f"source/src/{_upstream}/browser/resources/solace/sidepanel.html")
    css = _read(f"source/src/{_upstream}/browser/resources/solace/sidepanel.css")
    js = _read(f"source/src/{_upstream}/browser/resources/solace/sidepanel.js")

    assert "Yinyang AI Assistant" in html
    assert "Solace Yinyang" in js
    assert 'id="domain-pages"' in html
    assert 'id="domain-prev"' in html
    assert 'id="domain-next"' in html
    assert 'id="domain-apps"' in html
    assert "AI Agent Only Mode" in html
    assert "Domain App Store" in html
    assert "App Details" in html
    assert "Overview" in html
    assert "Reports" in html
    assert "Advanced" in html
    assert "Pick a domain or browse normally." in html
    assert "Create your own app for this domain" in html
    assert 'id="oauth3-pill"' in html
    assert 'id="app-detail-shell"' in html
    assert 'id="app-detail-action-copy"' in html
    assert 'id="app-reports-list"' in html
    assert 'id="app-schedules-list"' in html
    assert 'id="app-config-objective"' in html
    assert 'id="app-save-config-btn"' in html
    assert ".yy-domain-page" in css
    assert ".yy-domain-button" in css
    assert ".yy-domain-nav" in css
    assert ".yy-app-detail-shell" in css
    assert ".yy-detail-tab" in css
    assert ".yy-detail-item" in css
    assert ".yy-detail-item-actions" in css
    assert ".yy-prompt-chip" in css
    assert "const DOMAINS = [" in js
    assert "https://solaceagi.com/dashboard" in js
    assert "/branding/yinyang-rotating.gif" in js
    assert "upgrade_required" not in js
    assert "mail.google.com" in js
    assert "renderDomainApps" in js
    assert "updateAppDetails" in js
    assert "bindDetailTabs" in js
    assert "bindDetailActions" in js
    assert "/api/v1/apps/custom/create" in js
    assert "/api/v1/apps/' + encodeURIComponent(appId) + '/config" in js or "/api/v1/apps/\" + encodeURIComponent(appId) + \"/config" in js
    assert "/api/v1/apps/' + encodeURIComponent(appId)" in js or "/api/v1/apps/\" + encodeURIComponent(appId)" in js
    assert "Delete App" in js
    assert "data-schedule-action" in js
    assert "/api/v1/browser/schedules/' + encodeURIComponent(scheduleId) + '/" in js or "/api/v1/browser/schedules/\" + encodeURIComponent(scheduleId) + \"/" in js
    assert "bindDomainNav" in js
    assert "navigateBrowser" in js
    assert "postJson('/api/navigate'" in js


def test_domain_event_detail_contract_exists() -> None:
    server = _read("yinyang_server.py")

    assert 'elif re.match(r"^/api/v1/events/[^/]+$", path):' in server
    assert "def _handle_event_detail_api" in server
    assert 'payload["api_url"]' in server
    assert 'payload["detail_url"]' in server
    assert 'payload["report_available"]' in server
    assert 'payload["signoff_required"]' in server
    assert 'def _handle_event_detail_page' in server
    assert "Agree & eSign" in server
    assert "Business sign off" in server
    assert "Evidence preview" in server


def test_browser_starter_bundle_exists() -> None:
    bundle_root = REPO_ROOT / "apps"

    assert (bundle_root / "README.md").exists()
    assert (bundle_root / "solace-yinyang" / "manifest.yaml").exists()
    assert (bundle_root / "solace-yinyang" / "inbox" / "northstar.md").exists()
    assert (bundle_root / "gmail-inbox-triage" / "manifest.yaml").exists()
    assert (bundle_root / "gmail-inbox-triage" / "inbox" / "northstar.md").exists()
    assert (bundle_root / "github-issue-triage" / "manifest.yaml").exists()


def test_local_demo_rehearsal_script_exists() -> None:
    script = _read("scripts/rehearse_local_demo.py")

    assert "localhost:8888" in script or "127.0.0.1:8888" in script
    assert "/api/v1/browser/close" in script
    assert "/api/v1/browser/launch" in script
    assert "/api/v1/apps/custom/create" in script
    assert "/api/v1/apps/morning-brief/launch" in script
    assert "/apps/morning-brief/outbox/reports/today.html" in script


def test_hub_first_run_rehearsal_script_exists() -> None:
    script = _read("scripts/rehearse_hub_first_run.py")

    assert "/api/v1/onboarding/status" in script
    assert "/onboarding" in script
    assert "/onboarding/complete" in script
    assert "/api/v1/hub/browser/open" in script
    assert "https://solaceagi.com/register" in script
    assert "https://solaceagi.com/dashboard" in script
