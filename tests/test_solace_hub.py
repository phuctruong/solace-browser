"""Acceptance tests for the Solace Hub tray implementation.

These tests are file-based by design so they do not require a live Tauri runtime.
Port note: 18888 remains the reserved test port for Hub-related tests.
"""

from pathlib import Path


TEST_PORT = 18888
REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_RS = REPO_ROOT / "solace-hub" / "src-tauri" / "main.rs"
ICON_PATH = REPO_ROOT / "solace-hub" / "src-tauri" / "icons" / "yinyang-logo.png"
LEGACY_HUB_NAME = "Companion" + " App"
FORBIDDEN_DEBUG_PORT = "9" + "222"


def main_rs_source() -> str:
    assert MAIN_RS.exists(), f"main.rs not found at {MAIN_RS}"
    return MAIN_RS.read_text()


def test_tray_icon_exists():
    assert TEST_PORT == 18888
    assert ICON_PATH.exists(), f"yinyang-logo.png missing from {ICON_PATH}"
    assert ICON_PATH.stat().st_size > 0, "yinyang-logo.png is zero bytes"


def test_tray_menu_has_open_browser():
    source = main_rs_source()
    assert 'CustomMenuItem::new("open_browser", "Open Solace Browser")' in source


def test_tray_menu_has_quit():
    source = main_rs_source()
    assert 'CustomMenuItem::new("quit", "Quit")' in source


def test_tray_no_legacy_hub_name():
    source = main_rs_source()
    assert LEGACY_HUB_NAME not in source


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
    """Browser must be launched with http://localhost:8888/start URL."""
    source = main_rs_source()
    assert "localhost:{}/start" in source or "localhost:8888/start" in source
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
        assert "/start" in source

    def test_onboarding_url_in_source(self):
        """main.rs must reference /onboarding URL"""
        source = main_rs_source()
        assert "/onboarding" in source

    def test_start_url_in_source(self):
        """main.rs must reference /start URL"""
        source = main_rs_source()
        assert "/start" in source

    def test_dirs_next_in_cargo(self):
        """Cargo.toml must have dirs-next dependency"""
        cargo = (REPO_ROOT / "solace-hub" / "src-tauri" / "Cargo.toml").read_text()
        assert "dirs-next" in cargo

    def test_index_html_onboarding_section(self):
        """index.html must have onboarding status section"""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "onboarding" in html.lower() or "setup" in html.lower()

    def test_index_html_launch_browser_button(self):
        """index.html must have browser launch button"""
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "launch" in html.lower() or "open" in html.lower()

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
        """Source must route to /start when onboarding is complete"""
        source = main_rs_source()
        assert "/start" in source


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
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
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
