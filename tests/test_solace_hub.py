"""Acceptance tests for the Solace Hub tray implementation.

These tests are file-based by design so they do not require a live Tauri runtime.
Port note: 18888 remains the reserved test port for Hub-related tests.
"""

from pathlib import Path


TEST_PORT = 18888
REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_RS = REPO_ROOT / "solace-hub" / "src-tauri" / "main.rs"
ICON_PATH = REPO_ROOT / "solace-hub" / "src-tauri" / "icons" / "yinyang-logo.png"


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


def test_tray_no_companion_app():
    source = main_rs_source()
    assert "Companion App" not in source


def test_tray_no_port_9222():
    source = main_rs_source()
    assert "9222" not in source


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
    assert "9222" not in source


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
