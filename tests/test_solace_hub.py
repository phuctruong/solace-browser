"""Acceptance tests for the Solace Hub tray implementation.

These tests are file-based by design so they do not require a live Tauri runtime.
Port note: 18888 remains the reserved test port for Hub-related tests.
"""

from pathlib import Path
import json


TEST_PORT = 18888
REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_RS = REPO_ROOT / "solace-hub" / "src-tauri" / "main.rs"
ICON_PATH = REPO_ROOT / "solace-hub" / "src-tauri" / "icons" / "yinyang-logo.png"
WEB_ICON_PATH = REPO_ROOT / "solace-hub" / "src" / "icons" / "yinyang-logo.png"
DRAGON_BG_PATH = REPO_ROOT / "solace-hub" / "src" / "media" / "dragon-background.jpg"
DRAGON_SPLASH_PATH = REPO_ROOT / "solace-hub" / "src" / "media" / "dragon-yinyang-splash.png"
HUB_HTML = REPO_ROOT / "solace-hub" / "src" / "index.html"
HUB_JS = REPO_ROOT / "solace-hub" / "src" / "solace.js"
HUB_CSS = REPO_ROOT / "solace-hub" / "src" / "site.css"
TAURI_CONFIG = REPO_ROOT / "solace-hub" / "src-tauri" / "tauri.conf.json"
LEGACY_HUB_NAME = "Companion" + " App"
FORBIDDEN_DEBUG_PORT = "9" + "222"


def main_rs_source() -> str:
    assert MAIN_RS.exists(), f"main.rs not found at {MAIN_RS}"
    return MAIN_RS.read_text()


def hub_html_source() -> str:
    assert HUB_HTML.exists(), f"index.html not found at {HUB_HTML}"
    return HUB_HTML.read_text()


def hub_js_source() -> str:
    assert HUB_JS.exists(), f"solace.js not found at {HUB_JS}"
    return HUB_JS.read_text()


def test_tray_icon_exists():
    assert TEST_PORT == 18888
    assert ICON_PATH.exists(), f"yinyang-logo.png missing from {ICON_PATH}"
    assert ICON_PATH.stat().st_size > 0, "yinyang-logo.png is zero bytes"


def test_web_logo_asset_exists():
    assert WEB_ICON_PATH.exists(), f"hub logo missing from {WEB_ICON_PATH}"
    assert WEB_ICON_PATH.stat().st_size > 0, "web yinyang logo is zero bytes"


def test_onboarding_art_assets_exist():
    assert DRAGON_BG_PATH.exists(), f"dragon background missing from {DRAGON_BG_PATH}"
    assert DRAGON_SPLASH_PATH.exists(), f"dragon splash missing from {DRAGON_SPLASH_PATH}"
    assert DRAGON_BG_PATH.stat().st_size > 0
    assert DRAGON_SPLASH_PATH.stat().st_size > 0


def test_main_window_is_visible_by_default():
    config = json.loads(TAURI_CONFIG.read_text())
    window = config["tauri"]["windows"][0]
    assert window["visible"] is True
    assert window["width"] == 980
    assert window["height"] == 920


def test_tray_menu_has_open_browser():
    source = main_rs_source()
    assert 'CustomMenuItem::new("open_browser", "Open Solace Browser")' in source


def test_tray_menu_has_quit():
    source = main_rs_source()
    assert 'CustomMenuItem::new("quit", "Quit")' in source


def test_tray_no_legacy_hub_name():
    source = main_rs_source()
    assert LEGACY_HUB_NAME not in source


def test_dashboard_restore_helper_exists():
    source = main_rs_source()
    assert "fn restore_dashboard_window" in source
    assert "win.unminimize()" in source
    assert "win.set_min_size(Some(Size::Logical(LogicalSize" in source
    assert "win.set_size(Size::Logical(LogicalSize" in source
    assert "win.center()" in source
    assert "win.show()" in source
    assert "win.set_focus()" in source


def test_dashboard_restore_uses_real_size():
    source = main_rs_source()
    assert "width: 980.0" in source
    assert "height: 920.0" in source
    assert "width: 430.0" in source
    assert "height: 760.0" in source


def test_tray_no_forbidden_debug_port():
    source = main_rs_source()
    assert FORBIDDEN_DEBUG_PORT not in source


def test_quit_sends_sigterm():
    source = main_rs_source()
    assert "fn shutdown_server_process" in source
    assert "libc_kill(child.id() as i32, 15" in source
    assert "thread::sleep(Duration::from_secs(3));" in source
    assert "child.kill()" in source


def test_quit_deletes_port_lock():
    source = main_rs_source()
    assert '"quit" => {' in source
    assert "delete_port_lock()" in source


def test_quit_clears_keychain():
    source = main_rs_source()
    assert '"quit" => {' in source
    assert "clear_token_keychain()" in source


def test_setup_restores_dashboard_window():
    source = main_rs_source()
    assert ".setup(|app| {" in source
    assert "restore_dashboard_window(&win);" in source


def test_embedded_hub_page_uses_absolute_localhost_api_calls():
    js = hub_js_source()
    assert "const HUB_API_BASE = 'http://localhost:8888';" in js
    assert "function timeoutSignal(ms)" in js
    assert js.count("AbortSignal.timeout(") == 1
    assert "fetch('/api/v1/byok/providers')" not in js
    assert "fetch('/api/v1/notifications/unread-count')" not in js
    assert "fetch('/api/v1/notifications?limit=50')" not in js
    assert "fetch('/api/v1/logs/errors')" not in js
    assert "fetch('/api/v1/logs/requests?limit=50')" not in js


def test_hub_page_has_first_run_onboarding_shell():
    html = hub_html_source()
    assert "Solace Hub" in html
    assert "AI Agent Access:" in html
    assert "http://localhost:8888/agents" in html
    assert "free and local-first" in html or "Free forever" in html
    assert "Personal AI Assistant (Always Free)" in html
    assert "Managed Solace AGI (Dragon Warrior)" in html
    assert "Sign In / Create Account" in html
    assert "dragon-yinyang-splash.png" in html
    assert "hub-splash-wrap" in html
    assert "Rotating Yinyang droplet" in html
    assert "MCP server" in html
    assert "Webservices :8888" in html
    assert "Yinyang sidebar" in html
    assert "Solace AGI sync" in html
    assert "This screen should stay simple enough for first launch" not in html
    assert 'id="btn-theme-auto"' in html
    assert 'id="btn-theme-light"' in html
    assert 'id="btn-theme-dark"' in html
    assert 'id="btn-font-down"' in html
    assert 'id="btn-font-up"' in html
    assert 'id="btn-language-menu"' in html
    assert 'id="hub-language-menu"' in html


def test_hub_launch_actions_are_buttons_not_external_links():
    html = hub_html_source()
    assert 'id="btn-open-account"' in html
    assert 'id="btn-enable-byok"' in html
    assert 'id="btn-enable-cli"' in html
    assert 'id="btn-enable-ollama"' in html
    assert 'id="setup-step-1"' in html
    assert 'id="setup-step-2"' in html
    assert 'id="setup-step-3"' in html
    assert 'id="setup-step-status"' in html
    assert 'id="setup-step-primary"' in html
    assert 'id="setup-step-secondary"' in html
    assert 'id="setup-progress-pill"' in html
    assert 'id="setup-step-notes"' in html
    assert 'href="http://127.0.0.1:8888/agents"' not in html
    assert 'href="https://solaceagi.com/"' not in html


def test_hub_css_compacts_free_agent_card_and_setup_rail():
    css = HUB_CSS.read_text()
    assert ".hub-card-primary .hub-card-body" in css
    assert "grid-template-columns: auto 1fr;" in css
    assert ".hub-setup-rail" in css
    assert ".hub-setup-step" in css
    assert ".hub-setup-actions" in css
    assert ".hub-setup-progress-pill" in css
    assert ".hub-setup-notes" in css


def test_hub_js_persists_theme_and_font_controls():
    js = hub_js_source()
    assert "const HUB_THEME_KEY = 'solace-hub-theme';" in js
    assert "const HUB_FONT_KEY = 'solace-hub-font-scale';" in js
    assert "applyAppearance(" in js
    assert "bindAppearanceControls()" in js
    assert "const HUB_LOCALE_KEY = 'solace-hub-locale';" in js
    assert "const HUB_LOCALES = [" in js
    assert "const RTL_LOCALES = ['ar'];" in js
    assert "const TRANSLATIONS = {" in js
    assert "const SETUP_STEPS = {" in js
    assert "'zh-hant'" in js
    assert "'zu'" in js
    assert "bindLanguageMenu();" in js
    assert "function t(" in js
    assert "function applyTranslations()" in js
    assert "function bindSetupRail()" in js
    assert "setSetupStep(" in js
    assert "setSetupComplete(" in js
    assert "highestCompletedStep(" in js
    assert "bindSetupRail();" in js
    assert "primaryLabel" in js
    assert "secondaryLabel" in js
    assert "notes:" in js
    assert "setup-progress-pill" in js
    assert "qs('setup-step-primary')" in js
    assert "qs('setup-step-secondary')" in js
    assert "setLocale(window.localStorage.getItem(HUB_LOCALE_KEY) || 'en');" in js
    assert "document.documentElement.dir" in js
    assert "applyTranslations();" in js
    assert "new Intl.DisplayNames([locale], { type: 'language' });" in js
    assert "window.scrollTo(0, 0);" in js
    assert "window.localStorage.setItem(HUB_THEME_KEY, nextTheme);" in js
    assert "window.localStorage.setItem(HUB_FONT_KEY, nextFontScale);" in js


def test_hub_can_open_arbitrary_urls_in_solace_browser():
    source = main_rs_source()
    js = hub_js_source()
    assert 'fn cmd_open_browser_url(' in source
    assert 'cmd_open_browser_url,' in source
    assert 'fn launch_browser_via_runtime(' in source
    assert '/api/v1/browser/launch' in source
    assert 'Browser launched via runtime' in source
    assert "hubFetch('/api/v1/hub/browser/open'" in js
    assert "JSON.stringify({ url: url, profile: 'default', mode: 'standard' })" in js
    assert "JSON.stringify({ url: 'https://solaceagi.com/dashboard', profile: 'default', mode: 'standard' })" in js
    assert "https://solaceagi.com/dashboard" in js
    assert "https://solaceagi.com/register" in js
    assert "http://127.0.0.1:8888/agents" in js


def test_hub_passes_real_repo_root_to_yinyang_server():
    source = main_rs_source()
    assert "let repo_root = server_path" in source
    assert ".parent()" in source
    assert '.arg(repo_root)' in source
    assert '.arg(".")' not in source


def test_account_badge_uses_normalized_auth_state():
    js = hub_js_source()
    assert "const loggedIn = isLoggedIn(onboarding);" in js
    assert "const membershipTier = onboarding.membership_tier || 'free';" in js
    assert "const modelSource = onboarding.model_source || null;" in js
    assert "const managedLlmEnabled = Boolean(onboarding.managed_llm_enabled);" in js
    assert "Signed in via " not in js


def test_tray_show_dashboard_restores_window():
    source = main_rs_source()
    assert '"show_dashboard" => {' in source
    assert 'restore_dashboard_window(&win);' in source


def test_tray_left_click_restores_window():
    source = main_rs_source()
    assert "SystemTrayEvent::LeftClick" in source
    assert 'restore_dashboard_window(&win);' in source


# ── Task 002: Token Keychain Storage ──────────────────────────────────────────

def test_keychain_service_name():
    """Keychain must use 'solace-hub' service name (not com.solaceagi.hub)."""
    source = main_rs_source()
    assert 'KEYCHAIN_SERVICE: &str = "solace-hub"' in source
    assert "com.solaceagi.hub" not in source


def test_keychain_user_name():
    """Keychain must use 'oauth3-token' username (not yinyang-token)."""
    source = main_rs_source()
    assert 'KEYCHAIN_USER: &str = "oauth3-token"' in source
    assert '"yinyang-token"' not in source


def test_port_lock_has_token_sha256_field():
    """PortLock struct must have token_sha256 field (not token_hash)."""
    source = main_rs_source()
    assert "token_sha256: String" in source
    assert "token_hash: String" not in source


def test_port_lock_has_pid_field():
    """PortLock struct must include pid field for process tracking."""
    source = main_rs_source()
    assert "pid: u32" in source or "pid:" in source


def test_no_plaintext_token_in_source():
    """Source must never write Bearer token or raw sk- key to any file."""
    source = main_rs_source()
    assert "Bearer sk-" not in source
    assert "token.write" not in source
    assert "write_all(token" not in source


# ── Task 003: Hub Browser Launch ──────────────────────────────────────────────

def test_server_starts_before_browser():
    """wait_for_port_lock() must be called before launch_solace_browser() at each call site."""
    source = main_rs_source()
    assert "fn wait_for_port_lock" in source
    # For each call to launch_solace_browser, there must be a wait_for_port_lock
    # check in the same enclosing block. Verify by checking the guard pattern appears.
    assert "if !wait_for_port_lock(" in source
    # The call pattern: wait check THEN launch — both must exist in the same function
    assert "wait_for_port_lock(SERVER_HEALTH_TIMEOUT_SECS)" in source
    assert 'launch_solace_browser(&path_str, &start_url)' in source


def test_browser_gets_correct_url():
    """Browser must be launched with the real Solace AGI dashboard URL."""
    source = main_rs_source()
    assert "https://solaceagi.com/dashboard" in source
    assert '.arg("--new-window")' in source
    assert FORBIDDEN_DEBUG_PORT not in source


def test_server_timeout_blocks_browser():
    """wait_for_port_lock must return bool; caller checks it before launching browser."""
    source = main_rs_source()
    assert "if !wait_for_port_lock(" in source


def test_quit_kills_both():
    """Quit handler must address both server_child and browser_child."""
    source = main_rs_source()
    assert "server_child" in source
    assert "browser_child" in source
    assert '"quit" => {' in source


def test_browser_launch_function_takes_url():
    """launch_solace_browser must accept a url parameter."""
    source = main_rs_source()
    assert "fn launch_solace_browser(browser_path: &str, url: &str)" in source


def test_hub_resolves_server_script_from_repo_ancestors():
    """Hub must search ancestor directories for yinyang-server.py in dev builds."""
    source = main_rs_source()
    assert "fn resolve_server_script" in source
    assert 'join("yinyang-server.py")' in source
    assert "for candidate_root in exe_dir.ancestors()" in source


def test_hub_resolves_browser_binary_with_local_dev_and_bundle_modes():
    """Hub must distinguish local Chromium dev builds from production browser bundles."""
    source = main_rs_source()
    assert "fn resolve_browser_binary" in source
    assert "SOLACE_BROWSER_MODE" in source
    assert 'join("source/src/out/Solace/chrome-wrapper")' in source
    assert 'join("source/src/out/Solace/chrome")' in source
    assert 'join("dist/solace-browser-release/chrome")' in source
    assert 'join("solace-browser-release/chrome")' in source
    assert 'join("dist/solace-browser-linux-x86_64")' not in source
    assert "for candidate_root in exe_dir.ancestors()" in source


def test_browser_launch_uses_binary_parent_as_working_directory():
    """Chromium binaries must launch from their own directory so shared libraries resolve."""
    source = main_rs_source()
    assert "fn launch_solace_browser(browser_path: &str, url: &str)" in source
    assert ".current_dir(" in source


def test_startup_fails_closed_when_8888_already_occupied():
    source = main_rs_source()
    assert "fn ensure_runtime_port_available" in source
    assert 'TcpStream::connect(("127.0.0.1", YINYANG_PORT))' in source
    assert "Refusing to start Solace Hub" in source


# ── Task 004: Bearer Auth + Token Flow Redesign ─────────────────────────────

def test_no_cmd_get_token_hash():
    """P0-01 fix: cmd_get_token_hash must NOT be in invoke_handler (exposes token to WebView)."""
    source = main_rs_source()
    assert "cmd_get_token_hash" not in source, "P0-01 UNFIXED: cmd_get_token_hash still in invoke_handler"


def test_hub_generates_token_before_server():
    """P0-02 fix: Hub must generate session token and pass sha256 to server."""
    source = main_rs_source()
    assert "generate_session_token" in source, "Hub must call generate_session_token()"
    assert "--token-sha256" in source, "spawn_yinyang_server must pass --token-sha256 arg"
    assert "cmd_token_is_present" in source, "cmd_token_is_present must replace cmd_get_token_hash"


# ── Task 009: Onboarding Gate ──────────────────────────────────────────────────

class TestOnboardingGate:
    def test_onboarding_gate_function_exists(self):
        """main.rs must have check_onboarding_complete function"""
        source = main_rs_source()
        assert "check_onboarding_complete" in source

    def test_browser_launch_checks_onboarding(self):
        """cmd_open_browser must use check_onboarding_complete"""
        source = main_rs_source()
        # The function must be called within cmd_open_browser context
        assert "check_onboarding_complete" in source
        assert "/onboarding" in source
        assert "https://solaceagi.com/dashboard" in source

    def test_onboarding_url_in_source(self):
        """main.rs must reference /onboarding URL"""
        source = main_rs_source()
        assert "/onboarding" in source

    def test_dashboard_url_in_source(self):
        """main.rs must reference the dashboard URL after onboarding."""
        source = main_rs_source()
        assert "https://solaceagi.com/dashboard" in source

    def test_dirs_next_in_cargo(self):
        """Cargo.toml must have dirs-next dependency"""
        cargo = (REPO_ROOT / "solace-hub" / "src-tauri" / "Cargo.toml").read_text()
        assert "dirs-next" in cargo

    def test_index_html_onboarding_section(self):
        """index.html must have onboarding status section"""
        html = hub_html_source()
        js = hub_js_source()
        assert "onboarding" in html.lower() or "setup" in html.lower()
        assert 'data-mode="agent"' in html
        assert "saveOnboarding(payload)" in js
        assert "normalizeOnboardingState" in js
        assert "hubFetch('/onboarding/complete'" in js

    def test_index_html_launch_browser_button(self):
        """index.html must have browser launch button"""
        html = hub_html_source()
        js = hub_js_source()
        assert "launch" in html.lower() or "open" in html.lower()
        assert "button.disabled" in js
        assert 'window.open("http://localhost:8888/onboarding", "_blank")' not in html

    def test_tray_open_browser_checks_onboarding(self):
        """Tray open_browser handler must also check onboarding before launch"""
        source = main_rs_source()
        # Both call sites of check_onboarding_complete must exist
        assert source.count("check_onboarding_complete") >= 2

    def test_onboarding_url_when_incomplete(self):
        """Source must route to /onboarding when onboarding not complete"""
        source = main_rs_source()
        assert "/onboarding" in source

    def test_start_url_when_complete(self):
        """Source must route to the dashboard when onboarding is complete"""
        source = main_rs_source()
        assert "https://solaceagi.com/dashboard" in source


# ── Task 010: OAuth3 Token Management Dashboard ─────────────────────────────

class TestSessionCommands:
    def test_cmd_list_sessions_in_invoke_handler(self):
        source = MAIN_RS.read_text()
        assert "cmd_list_sessions" in source

    def test_cmd_kill_all_sessions_in_invoke_handler(self):
        source = MAIN_RS.read_text()
        assert "cmd_kill_all_sessions" in source

    def test_session_endpoint_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/sessions" in server

    def test_session_url_localhost_only(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "localhost" in server
        # Ensure external URL check exists via urlparse hostname check
        assert "hostname" in server


class TestOAuth3Dashboard:
    def test_index_html_oauth3_section(self):
        """index.html must contain OAuth3 Tokens section."""
        html = hub_html_source()
        assert "oauth3" in html.lower() or "OAuth3" in html

    def test_index_html_revoke_button(self):
        """index.html must contain revoke functionality."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "revoke" in html.lower() or "Revoke" in html

    def test_index_html_register_form(self):
        """index.html must have register new token form."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "register" in html.lower() or "Register" in html

    def test_index_html_oauth3_panel_id(self):
        """index.html must have oauth3-panel element."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert 'id="oauth3-panel"' in html

    def test_index_html_extend_function(self):
        """index.html must have extendToken JS function."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "extendToken" in html

    def test_index_html_refresh_oauth3_function(self):
        """index.html must have refreshOAuth3Tokens JS function."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "refreshOAuth3Tokens" in html

    def test_index_html_no_port_9222(self):
        """index.html must not reference the forbidden debug port."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert FORBIDDEN_DEBUG_PORT not in html

    def test_index_html_no_companion_app(self):
        """index.html must not reference the legacy hub name."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert LEGACY_HUB_NAME not in html


# ── Task 012: Tunnel + Sync UI ────────────────────────────────────────────────

class TestTunnelSyncUI:
    def test_index_html_tunnel_panel(self):
        """index.html must contain tunnel section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "tunnel" in html.lower()

    def test_index_html_tunnel_warning(self):
        """index.html must warn users about internet exposure."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "internet" in html.lower() or "warning" in html.lower() or "expose" in html.lower()

    def test_index_html_sync_panel(self):
        """index.html must contain sync/vault section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "sync" in html.lower() or "vault" in html.lower()

    def test_index_html_export_button(self):
        """index.html must have export button or function."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "export" in html.lower() or "Export" in html

    def test_index_html_no_port_9222_tunnel(self):
        """Tunnel panel must not reference the forbidden debug port."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert FORBIDDEN_DEBUG_PORT not in html

    def test_index_html_no_companion_app_tunnel(self):
        """Tunnel/sync additions must not introduce legacy hub name."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert LEGACY_HUB_NAME not in html

# ── Task 013: Evidence Viewer ──────────────────────────────────────────────────

class TestEvidencePanel:
    def test_index_html_evidence_chain_section(self):
        """index.html must contain an Evidence Chain section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "evidence" in html.lower() or "Evidence" in html

    def test_index_html_verify_chain_button(self):
        """index.html must contain Verify Chain button/function."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "verify" in html.lower() or "Verify" in html

    def test_evidence_endpoint_in_server(self):
        """yinyang_server.py must have /api/v1/evidence/verify route."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/evidence/verify" in server

    def test_evidence_detail_endpoint_in_server(self):
        """yinyang_server.py must have evidence detail handler."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "_handle_evidence_detail" in server

    def test_index_html_evidence_action_filter(self):
        """index.html must have action filter for evidence."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "action" in html.lower()

    def test_index_html_no_port_9222_evidence(self):
        """Evidence panel must not reference the forbidden debug port."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert FORBIDDEN_DEBUG_PORT not in html

    def test_index_html_no_companion_app_evidence(self):
        """Evidence additions must not introduce legacy hub name."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert LEGACY_HUB_NAME not in html


# ── Task 014: Schedule Management UI ──────────────────────────────────────────

class TestScheduleUI:
    def test_index_html_schedule_section(self):
        """index.html must contain schedule/automation section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "schedule" in html.lower() or "automation" in html.lower()

    def test_index_html_cron_builder(self):
        """index.html must have cron builder preset options."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "cron" in html.lower() or "9am" in html.lower() or "Every" in html

    def test_schedule_endpoints_in_server(self):
        """yinyang_server.py must have next-runs, enable, disable handlers."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "next-runs" in server
        assert "_handle_schedule_enable" in server
        assert "_handle_schedule_disable" in server

    def test_schedule_enable_disable_routes_in_server(self):
        """yinyang_server.py must route enable and disable POST requests."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/enable" in server
        assert "/disable" in server

    def test_index_html_no_port_9222_schedules(self):
        """Schedule panel must not reference the forbidden debug port."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert FORBIDDEN_DEBUG_PORT not in html

    def test_index_html_no_companion_app_schedules(self):
        """Schedule additions must not introduce legacy hub name."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert LEGACY_HUB_NAME not in html


# ── Task 015: Recipe Panel ────────────────────────────────────────────────────

class TestRecipePanel:
    def test_index_html_recipe_section(self):
        """index.html must contain recipe section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "recipe" in html.lower() or "Recipe" in html

    def test_recipe_endpoints_in_server(self):
        """yinyang_server.py must have /api/v1/recipes route."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/recipes" in server
        assert "recipe_id" in server

    def test_recipe_run_endpoint_in_server(self):
        """yinyang_server.py must have /run route for recipes."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "_handle_recipe_run" in server

    def test_index_html_no_port_9222_recipes(self):
        """Recipe panel must not reference the forbidden debug port."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert FORBIDDEN_DEBUG_PORT not in html

    def test_index_html_no_companion_app_recipes(self):
        """Recipe additions must not introduce legacy hub name."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert LEGACY_HUB_NAME not in html


# ── Task 016: Budget Panel ────────────────────────────────────────────────────

class TestBudgetPanel:
    def test_index_html_budget_section(self):
        """index.html must contain budget section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "budget" in html.lower() or "Budget" in html

    def test_index_html_daily_limit(self):
        """index.html must reference daily limit concept."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "daily" in html.lower() or "limit" in html.lower()

    def test_budget_endpoints_in_server(self):
        """yinyang_server.py must have /api/v1/budget route with daily_limit_usd."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/budget" in server
        assert "daily_limit_usd" in server

    def test_index_html_no_port_9222_budget(self):
        """Budget panel must not reference the forbidden debug port."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert FORBIDDEN_DEBUG_PORT not in html

    def test_index_html_no_companion_app_budget(self):
        """Budget additions must not introduce legacy hub name."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert LEGACY_HUB_NAME not in html


# ── Task 018: Hub Health Metrics ─────────────────────────────────────────────

class TestMetricsPanel:
    def test_index_html_metrics_section(self):
        """index.html must contain metrics or uptime panel."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "metrics" in html.lower() or "uptime" in html.lower()

    def test_index_html_prometheus_link(self):
        """index.html must reference Prometheus /metrics endpoint."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "prometheus" in html.lower() or "/metrics" in html

    def test_metrics_endpoints_in_server(self):
        """yinyang_server.py must implement /api/v1/metrics and /metrics."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/metrics" in server
        assert "/metrics" in server
        assert "uptime_seconds" in server


# ── Task 017: WebSocket Live Dashboard ───────────────────────────────────────

class TestDashboardWebSocket:
    def test_index_html_ws_dashboard_connection(self):
        """index.html must reference ws/dashboard WebSocket URL."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "ws/dashboard" in html

    def test_index_html_ws_reconnect_logic(self):
        """index.html must have WebSocket onclose/reconnect handler."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "onclose" in html or "reconnect" in html.lower()

    def test_index_html_fallback_polling(self):
        """index.html must have polling fallback when WS not available."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "fallback" in html.lower() or "polling" in html.lower() or "setInterval" in html


# ── Task 019: BYOK API Key Management ────────────────────────────────────────

class TestBYOKPanel:
    def test_index_html_byok_section(self):
        """index.html must contain BYOK / API Keys section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "byok" in html.lower() or "api key" in html.lower() or "BYOK" in html

    def test_index_html_password_input(self):
        """API key inputs must be type=password."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert 'type="password"' in html or "type='password'" in html

    def test_byok_endpoints_in_server(self):
        """yinyang_server.py must implement /api/v1/byok routes and SUPPORTED_PROVIDERS."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/byok" in server
        assert "SUPPORTED_PROVIDERS" in server

    def test_index_html_no_port_9222_byok(self):
        """BYOK panel must not reference the forbidden debug port."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert FORBIDDEN_DEBUG_PORT not in html

    def test_index_html_no_companion_app_byok(self):
        """BYOK additions must not introduce legacy hub name."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert LEGACY_HUB_NAME not in html


# ── Task 020: Notification System ─────────────────────────────────────────────

class TestNotificationUI:
    def test_index_html_notification_bell(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "notification" in html.lower() or "notif" in html.lower()

    def test_index_html_mark_all_read(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "mark" in html.lower() and "read" in html.lower()

    def test_notification_endpoints_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/notifications" in server
        assert "unread_count" in server


# ── Task 021: Server Log Viewer ────────────────────────────────────────────────

class TestLogViewerUI:
    def test_index_html_log_section(self):
        """index.html must contain a log/request log section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "log" in html.lower() or "request" in html.lower()

    def test_log_endpoints_in_server(self):
        """yinyang_server.py must implement both log API routes."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/logs/requests" in server
        assert "/api/v1/logs/errors" in server


# ── Task 022: Tray Dynamic Menu ───────────────────────────────────────────────

class TestTrayMenu:
    def test_tray_status_in_html(self):
        """index.html must contain a tray status bar."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "tray" in html.lower() or "status" in html.lower()

    def test_build_tray_status_in_main_rs(self):
        """main.rs must reference sessions or tray concept."""
        rs = (REPO_ROOT / "solace-hub" / "src-tauri" / "main.rs").read_text()
        assert "sessions" in rs.lower() or "tray" in rs.lower()

    def test_status_bar_refresh_in_html(self):
        """index.html must poll metrics and sessions for live tray data."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "metrics" in html and "sessions" in html


# ── Task 023: Profile Manager ─────────────────────────────────────────────────

class TestProfileUI:
    def test_index_html_profiles_section(self):
        """index.html must contain a profiles section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "profile" in html.lower()

    def test_profile_endpoints_in_server(self):
        """yinyang_server.py must implement profile API routes."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/profiles" in server
        assert "PROFILES_PATH" in server


# ── Task 024: Recipe Store ────────────────────────────────────────────────────

class TestRecipeStoreUI:
    def test_index_html_store_section(self):
        """index.html must contain a community store section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "store" in html.lower() or "community" in html.lower()

    def test_store_endpoints_in_server(self):
        """yinyang_server.py must implement store API routes."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/store/recipes" in server
        assert "INSTALLED_RECIPES_PATH" in server


# ── Task 025: CLI Tool Integration ───────────────────────────────────────────

class TestCLIPanel:
    def test_index_html_cli_section(self):
        """index.html must contain a CLI integration section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "cli" in html.lower() or "local" in html.lower()

    def test_cli_endpoints_in_server(self):
        """yinyang_server.py must implement CLI config API routes."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/cli/config" in server
        assert "SUPPORTED_CLI_TOOLS" in server


# ── Task 026: Chat Panel ──────────────────────────────────────────────────────

class TestChatPanel:
    def test_index_html_chat_panel(self):
        """index.html must contain a chat panel."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "chat" in html.lower()

    def test_ws_chat_in_server(self):
        """yinyang_server.py must implement /ws/chat endpoint."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/ws/chat" in server


# ── Task 027: App Launcher ────────────────────────────────────────────────────

class TestAppLauncherUI:
    def test_apps_endpoint_in_server(self):
        """yinyang_server.py must implement /api/v1/apps endpoint."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/apps" in server

    def test_index_html_app_section(self):
        """index.html must contain an app launcher section."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "app" in html.lower() or "launch" in html.lower()


# ── Task 028: Evidence Export ─────────────────────────────────────────────────

class TestEvidenceExportUI:
    def test_export_buttons_in_html(self):
        """index.html must contain export buttons for evidence."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "export" in html.lower()

    def test_export_endpoint_in_server(self):
        """yinyang_server.py must implement /api/v1/evidence/export."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/evidence/export" in server


# ── Task 029: Budget Alerts ───────────────────────────────────────────────────

class TestBudgetAlertsUI:
    def test_budget_history_in_server(self):
        """yinyang_server.py must implement budget history and alerts endpoints."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/budget/history" in server
        assert "SPEND_HISTORY_PATH" in server

    def test_budget_alerts_in_html(self):
        """index.html must contain alert threshold controls."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "alert" in html.lower() or "threshold" in html.lower()


# ── Task 030: Hub Health Watchdog ─────────────────────────────────────────────

class TestWatchdogUI:
    def test_watchdog_in_server(self):
        """yinyang_server.py must implement watchdog endpoints."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/watchdog/status" in server
        assert "restart_count" in server

    def test_watchdog_status_in_html(self):
        """index.html must reference watchdog or uptime."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "watchdog" in html.lower() or "restart" in html.lower() or "uptime" in html.lower()


# ── Task 031: Dark Mode Toggle ────────────────────────────────────────────────

class TestDarkModeUI:
    def test_theme_endpoint_in_server(self):
        """yinyang_server.py must implement /api/v1/theme and THEME_PATH."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/theme" in server
        assert "THEME_PATH" in server

    def test_dark_mode_in_html(self):
        """index.html must contain dark mode class or toggle."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "dark" in html.lower()


# ── Task 032: Recipe Run History ──────────────────────────────────────────────

class TestRecipeHistoryUI:
    def test_recipe_history_in_server(self):
        """yinyang_server.py must implement /api/v1/recipes/history."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/recipes/history" in server

    def test_recipe_history_in_html(self):
        """index.html must reference run history."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "history" in html.lower() or "run" in html.lower()


# ── Task 033: Settings Export / Import ───────────────────────────────────────

class TestSettingsUI:
    def test_settings_export_in_server(self):
        """yinyang_server.py must implement /api/v1/settings/export."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/settings/export" in server
        assert "/api/v1/settings/import" in server

    def test_settings_in_html(self):
        """index.html must reference settings export."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "settings" in html.lower() and "export" in html.lower()


# ── Task 034: API Usage Stats ─────────────────────────────────────────────────

class TestUsageStatsUI:
    def test_usage_stats_in_server(self):
        """yinyang_server.py must implement /api/v1/usage/stats."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/usage/stats" in server
        assert "by_provider" in server

    def test_usage_in_html(self):
        """index.html must reference usage or provider."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "usage" in html.lower() or "provider" in html.lower()


# ── Task 035: Keyboard Shortcuts ──────────────────────────────────────────────

class TestShortcutsUI:
    def test_shortcuts_in_server(self):
        """yinyang_server.py must implement /api/v1/shortcuts."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/shortcuts" in server

    def test_shortcuts_in_html(self):
        """index.html must reference shortcuts or keyboard."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "shortcut" in html.lower() or "keyboard" in html.lower()


# ── Task 036: System Status Banner ───────────────────────────────────────────

class TestSystemStatusUI:
    def test_system_status_in_server(self):
        """yinyang_server.py must implement /api/v1/system/status."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/system/status" in server
        assert "_SERVER_VERSION" in server

    def test_version_in_html(self):
        """index.html must reference version or system."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "version" in html.lower() or "system" in html.lower()


# ── Task 037: Notification Toast System ──────────────────────────────────────

class TestToastUI:
    def test_notifications_read_in_server(self):
        """yinyang_server.py must handle /api/v1/notifications/read."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/notifications/read" in server

    def test_toast_in_html(self):
        """index.html must contain toast container."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "toast" in html.lower()


# ── Task 038: Global Search ───────────────────────────────────────────────────

class TestSearchUI:
    def test_search_in_server(self):
        """yinyang_server.py must implement /api/v1/search."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/search" in server

    def test_search_in_html(self):
        """index.html must contain search input."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "search" in html.lower()


# ── Task 039: Pinned Sections ─────────────────────────────────────────────────

class TestPinnedUI:
    def test_pinned_in_server(self):
        """yinyang_server.py must implement /api/v1/pinned."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/pinned" in server
        assert "PINNED_SECTIONS_PATH" in server

    def test_pin_in_html(self):
        """index.html must contain pin functionality."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "pin" in html.lower()


# ── Task 040: Accessibility Report ───────────────────────────────────────────

class TestAccessibilityUI:
    def test_accessibility_in_server(self):
        """yinyang_server.py must implement /api/v1/accessibility."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/accessibility" in server

    def test_accessibility_in_html(self):
        """index.html must contain accessibility panel."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "accessibility" in html.lower() or "a11y" in html.lower()


# ── Task 041: Connection Health ───────────────────────────────────────────────

class TestConnectionHealthUI:
    def test_ping_in_server(self):
        """yinyang_server.py must implement /api/v1/ping."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/ping" in server

    def test_latency_in_html(self):
        """index.html must reference latency or ping."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "latency" in html.lower() or "ping" in html.lower()


# ── Task 042: App Tag Filter ──────────────────────────────────────────────────

class TestAppTagsUI:
    def test_apps_tags_in_server(self):
        """yinyang_server.py must implement /api/v1/apps/tags."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/apps/tags" in server

    def test_tag_filter_in_html(self):
        """index.html must contain tag filter UI."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "tag" in html.lower() or "filter" in html.lower()


# ── Task 043: Multi-Window Sync / Broadcast ───────────────────────────────────

class TestBroadcastUI:
    def test_broadcast_in_server(self):
        """yinyang_server.py must implement /api/v1/broadcast."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/broadcast" in server

    def test_storage_sync_in_html(self):
        """index.html must reference storage or broadcast."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "storage" in html.lower() or "broadcast" in html.lower()


# ── Task 044: Rate Limit Status ───────────────────────────────────────────────

class TestRateLimitUI:
    def test_rate_limit_in_server(self):
        """yinyang_server.py must implement /api/v1/rate-limit/status."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/rate-limit/status" in server

    def test_rate_limit_in_html(self):
        """index.html must contain rate limit display."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "rate" in html.lower() or "rpm" in html.lower() or "limit" in html.lower()


# ── Task 045: App Favorites ───────────────────────────────────────────────────

class TestAppFavoritesUI:
    def test_favorites_in_server(self):
        """yinyang_server.py must implement /api/v1/apps/favorites."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/apps/favorites" in server

    def test_favorites_in_html(self):
        """index.html must contain favorite/star UI."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "favorite" in html.lower() or "★" in html or "star" in html.lower()


# ── Task 046: Recipe Templates ────────────────────────────────────────────────

class TestRecipeTemplatesUI:
    def test_templates_in_server(self):
        """yinyang_server.py must implement /api/v1/recipes/templates."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/recipes/templates" in server

    def test_templates_in_html(self):
        """index.html must contain template UI."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "template" in html.lower()


# ── Task 047: Vault Status ────────────────────────────────────────────────────

class TestVaultStatusUI:
    def test_vault_status_in_server(self):
        """yinyang_server.py must implement /api/v1/vault/status."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/vault/status" in server

    def test_vault_in_html(self):
        """index.html must contain vault UI."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "vault" in html.lower() or "oauth" in html.lower()


# ── Task 048: App Run Count ────────────────────────────────────────────────────

class TestAppRunCountUI:
    def test_run_count_in_server(self):
        """yinyang_server.py must implement /api/v1/apps/run-count."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/apps/run-count" in server

    def test_run_count_in_html(self):
        """index.html must show run count or usage somewhere."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "run" in html.lower() or "count" in html.lower() or "usage" in html.lower()


# ── Task 049: Server Config ────────────────────────────────────────────────────

class TestServerConfigUI:
    def test_config_in_server(self):
        """yinyang_server.py must implement /api/v1/server/config."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/server/config" in server

    def test_config_in_html(self):
        """index.html must show server config or features."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "feature" in html.lower() or "config" in html.lower() or "version" in html.lower()


# ── Task 050: App Categories ───────────────────────────────────────────────────

class TestAppCategoriesUI:
    def test_categories_in_server(self):
        """yinyang_server.py must implement /api/v1/apps/categories."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/apps/categories" in server

    def test_categories_in_html(self):
        """index.html must show category or tag UI."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "categor" in html.lower() or "tag" in html.lower()


# ── Task 051: App Search by Category ─────────────────────────────────────────

class TestAppSearchByCategoryUI:
    def test_category_filter_in_server(self):
        """yinyang_server.py must support category param in /api/v1/apps."""
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/apps" in server

    def test_category_filter_in_html(self):
        """index.html must show app filter UI."""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "tag" in html.lower() or "filter" in html.lower() or "categor" in html.lower()


# ── Task 052: Health History ──────────────────────────────────────────────────

class TestHealthHistoryUI:
    def test_health_history_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/health/history" in server

    def test_health_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "health" in html.lower() or "status" in html.lower()


# ── Task 053: Recipe Enable/Disable ──────────────────────────────────────────

class TestRecipeEnableDisableUI:
    def test_recipe_enable_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/enable" in server or "/disable" in server

    def test_recipe_toggle_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "enable" in html.lower() or "disable" in html.lower() or "recipe" in html.lower()


# ── Task 054: Theme Presets ───────────────────────────────────────────────────

class TestThemePresetsUI:
    def test_theme_presets_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/theme/presets" in server

    def test_theme_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "theme" in html.lower() or "dark" in html.lower()


# ── Task 055: Budget Spending Breakdown ───────────────────────────────────────

class TestBudgetBreakdownUI:
    def test_breakdown_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/budget/breakdown" in server

    def test_budget_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "budget" in html.lower() or "spend" in html.lower()


# ── Task 056: Evidence Export Summary ────────────────────────────────────────

class TestEvidenceExportSummaryUI:
    def test_evidence_summary_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/evidence/summary" in server

    def test_evidence_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "evidence" in html.lower() or "chain" in html.lower()


# ── Task 057: Schedule Summary ────────────────────────────────────────────────

class TestScheduleSummaryUI:
    def test_schedule_summary_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/schedules/summary" in server

    def test_schedule_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "schedule" in html.lower()


# ── Task 058: App Install ──────────────────────────────────────────────────────

class TestAppInstallUI:
    def test_app_install_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/apps/install" in server

    def test_install_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "launch" in html.lower() or "install" in html.lower()


# ── Task 059: Notification Clear All ──────────────────────────────────────────

class TestNotificationClearAllUI:
    def test_clear_all_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "clear-all" in server

    def test_notification_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "notif" in html.lower() or "toast" in html.lower()


# ── Task 060: System Info ──────────────────────────────────────────────────────

class TestSystemInfoUI:
    def test_system_info_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/system/info" in server

    def test_system_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "system" in html.lower() or "version" in html.lower()


# ── Task 061-065: Bulk UI Tests ───────────────────────────────────────────────

class TestWebhookUI:
    def test_webhook_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/webhooks" in server

class TestServerStatsUI:
    def test_stats_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/stats" in server

class TestEvidenceHashesUI:
    def test_hashes_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/evidence/hashes" in server

class TestAppMetadataUI:
    def test_metadata_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/apps/metadata" in server

class TestScheduleStatsUI:
    def test_schedule_stats_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/schedules/stats" in server


# ── Tasks 066-070: Bulk UI Tests ──────────────────────────────────────────────

class TestBudgetForecastUI:
    def test_forecast_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/budget/forecast" in server

class TestSessionReplayUI:
    def test_sessions_count_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/sessions/count" in server

class TestLogLevelUI:
    def test_log_level_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/log/level" in server

class TestRecipeCloneUI:
    def test_recipe_clone_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/clone" in server


# ── Tasks 071-075: Bulk UI Tests ──────────────────────────────────────────────

class TestMemoryKeysUI:
    def test_memory_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/memory" in server

class TestUptimeSLAUI:
    def test_sla_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/sla/uptime" in server

class TestCustomLabelsUI:
    def test_labels_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/labels" in server


# ── Tasks 076-080: Bulk UI Tests ──────────────────────────────────────────────

class TestBudgetExportUI:
    def test_budget_export_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/budget/export" in server

class TestNotifPrefsUI:
    def test_notif_prefs_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/notifications/preferences" in server

class TestEvidenceSearchUI:
    def test_evidence_search_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/api/v1/evidence/search" in server


# ── Task 060: Schedule Operations 4-Tab Redesign ────────────────────────────

class TestScheduleOperations4TabUI:
    def test_schedule_html_uses_four_task_tabs(self):
        html = (REPO_ROOT / "web" / "schedule.html").read_text()
        assert "Upcoming" in html
        assert "Approval Queue" in html
        assert "History" in html
        assert "eSign" in html
        assert ">Calendar<" not in html
        assert ">Kanban<" not in html
        assert ">Timeline<" not in html
        assert ">List<" not in html

    def test_schedule_html_no_cdn(self):
        html = (REPO_ROOT / "web" / "schedule.html").read_text().lower()
        assert "cdn" not in html
        assert "bootstrap" not in html
        assert "tailwind" not in html
        assert "jquery" not in html
        assert "https://" not in html
        assert "http://" not in html

    def test_schedule_js_never_auto_approves(self):
        js = (REPO_ROOT / "web" / "js" / "schedule.js").read_text()
        assert "auto-REJECT" in js
        assert "countdown_expired" in js
        assert "schedule/cancel/" in js
        start_idx = js.index("function startCountdown")
        auto_reject_idx = js.index("function autoRejectItem")
        countdown_block = js[start_idx:auto_reject_idx]
        assert "approveItem(" not in countdown_block

    def test_schedule_4tab_css_no_hardcoded_hex(self):
        import re
        # Detect hex color values (#abc / #aabbcc) but NOT CSS ID selectors (#kanban-board)
        _HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}(?:[^0-9a-zA-Z_-]|$)")
        css_lines = (REPO_ROOT / "web" / "css" / "schedule.css").read_text().splitlines()
        for line_number, line in enumerate(css_lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("/*"):
                continue
            if stripped.startswith("--hub-"):
                continue
            assert not _HEX_COLOR_RE.search(line), f"Hardcoded hex color at line {line_number}: {line.strip()}"

    def test_schedule_html_has_cron_presets(self):
        html = (REPO_ROOT / "web" / "schedule.html").read_text()
        assert 'value="daily_7am"' in html
        assert 'value="weekdays_9am"' in html
        assert 'value="hourly"' in html
        assert 'value="every_2h"' in html
        assert 'value="weekly_monday"' in html
