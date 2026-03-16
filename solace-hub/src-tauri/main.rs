// Diagram: 04-hub-lifecycle
//! Solace Hub — Tauri desktop app for Solace Browser orchestration
//!
//! Lifecycle (enforced, non-negotiable):
//!   1. generate_session_token() — Hub-owned session secret
//!   2. store_token_keychain()   — OS keychain; NEVER plaintext in files
//!   3. spawn_backend_server()   — Rust runtime on port 8888 (Python fallback)
//!   4. wait_for_server()        — polls /health until ready (max 10s)
//!   5. build system tray
//!   6. "Open Solace Browser" → launch_solace_browser()
//!   7. "Quit" → graceful server stop → delete_port_lock() → clear keychain → exit
//!
//! Port 8888 ONLY. Extensions ZERO. "Solace Hub" ONLY.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::fs;
use std::io::{self, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use keyring::Entry;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::{
    CustomMenuItem, LogicalSize, Manager, RunEvent, Size, State, SystemTray, SystemTrayEvent,
    SystemTrayMenu, SystemTrayMenuItem, Window,
};

// ────────────────────────────────────────────────────────────────────────────
// Constants
// ────────────────────────────────────────────────────────────────────────────

/// Port for Yinyang Server. NEVER changed.
const YINYANG_PORT: u16 = 8888;

const KEYCHAIN_SERVICE: &str = "solace-hub";
const KEYCHAIN_USER: &str = "oauth3-token";
const PORT_LOCK_FILE: &str = ".solace/port.lock";
const SERVER_HEALTH_TIMEOUT_SECS: u64 = 10;

// ────────────────────────────────────────────────────────────────────────────
// Data structures
// ────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
struct PortLock {
    port: u16,
    /// SHA-256 hex digest of the session token. NEVER the plaintext token.
    token_sha256: String,
    /// PID of the yinyang-server process.
    #[serde(default)]
    pid: u32,
}

#[derive(Debug, Default)]
struct HubState {
    server_child: Mutex<Option<Child>>,
    browser_child: Mutex<Option<Child>>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum BrowserLaunchMode {
    Auto,
    LocalDev,
    ProductionBundle,
}

// ────────────────────────────────────────────────────────────────────────────
// Port lock helpers
// ────────────────────────────────────────────────────────────────────────────

fn port_lock_path() -> PathBuf {
    let home = dirs_home();
    home.join(PORT_LOCK_FILE)
}

/// Returns the user's home directory.
fn dirs_home() -> PathBuf {
    // $HOME on Unix; USERPROFILE on Windows
    #[cfg(target_family = "unix")]
    {
        std::env::var("HOME")
            .map(PathBuf::from)
            .expect("$HOME must be set")
    }
    #[cfg(target_family = "windows")]
    {
        std::env::var("USERPROFILE")
            .map(PathBuf::from)
            .expect("USERPROFILE must be set")
    }
}

fn read_port_lock() -> Result<PortLock, Box<dyn std::error::Error>> {
    let path = port_lock_path();
    let content = fs::read_to_string(&path)?;
    let lock: PortLock = serde_json::from_str(&content)?;
    Ok(lock)
}

fn delete_port_lock() -> Result<(), io::Error> {
    let path = port_lock_path();
    if path.exists() {
        fs::remove_file(&path)?;
    }
    Ok(())
}

// ────────────────────────────────────────────────────────────────────────────
// Token helpers
// ────────────────────────────────────────────────────────────────────────────

/// Compute SHA-256 hex digest. Only this hash enters port.lock; plaintext never written.
fn sha256_hex(input: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    hex::encode(hasher.finalize())
}

fn generate_session_token() -> String {
    #[cfg(target_family = "unix")]
    {
        use std::io::Read;

        let mut bytes = [0u8; 32];
        let mut file = std::fs::File::open("/dev/urandom")
            .expect("FATAL: Cannot open /dev/urandom");
        file.read_exact(&mut bytes)
            .expect("FATAL: Cannot read random bytes");
        hex::encode(bytes)
    }
    #[cfg(not(target_family = "unix"))]
    {
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos();
        let pid = std::process::id();
        sha256_hex(&format!("hub-{pid}-{ts}"))
    }
}

/// Store token in OS keychain (Keychain on macOS, libsecret on Linux, DPAPI on Windows).
fn store_token_keychain(token: &str) -> Result<(), keyring::Error> {
    let entry = Entry::new(KEYCHAIN_SERVICE, KEYCHAIN_USER)?;
    entry.set_password(token)?;
    Ok(())
}

/// Retrieve token from OS keychain.
fn retrieve_token_keychain() -> Result<String, keyring::Error> {
    let entry = Entry::new(KEYCHAIN_SERVICE, KEYCHAIN_USER)?;
    entry.get_password()
}

/// Delete token from OS keychain (called on quit).
fn clear_token_keychain() -> Result<(), keyring::Error> {
    let entry = Entry::new(KEYCHAIN_SERVICE, KEYCHAIN_USER)?;
    entry.delete_password()
}

fn browser_launch_mode() -> BrowserLaunchMode {
    match std::env::var("SOLACE_BROWSER_MODE").ok().as_deref() {
        Some("local-dev") => BrowserLaunchMode::LocalDev,
        Some("production-bundle") => BrowserLaunchMode::ProductionBundle,
        _ => BrowserLaunchMode::Auto,
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Process management
// ────────────────────────────────────────────────────────────────────────────

/// Spawn the Solace Runtime backend. Prefers Rust binary; falls back to Python.
/// Returns the Child process; caller must retain it to prevent premature termination.
fn spawn_backend_server(
    server_path: &Path,
    repo_root: &Path,
    token_sha256: &str,
) -> Result<Child, io::Error> {
    // If server_path points to the Rust binary, spawn it directly (no Python needed)
    if is_rust_runtime(server_path) {
        return Command::new(server_path).spawn();
    }
    // Legacy fallback: Python yinyang-server.py
    let python = python_executable();
    Command::new(python)
        .arg(server_path)
        .arg(repo_root)
        .arg("--token-sha256")
        .arg(token_sha256)
        .spawn()
}

/// Check if a path points to the Rust solace-runtime binary (not a .py script).
fn is_rust_runtime(path: &Path) -> bool {
    path.file_name()
        .and_then(|n| n.to_str())
        .map(|n| n == "solace-runtime")
        .unwrap_or(false)
}

/// Returns "python3" on Unix, "python" on Windows.
fn python_executable() -> &'static str {
    #[cfg(target_family = "unix")]
    {
        "python3"
    }
    #[cfg(target_family = "windows")]
    {
        "python"
    }
}

/// Locate the backend server binary. Prefers Rust solace-runtime; falls back to Python.
///
/// Search order:
///   1. solace-runtime/target/release/solace-runtime (Rust — preferred)
///   2. ~/.solace/bin/solace-runtime (installed Rust binary)
///   3. yinyang-server.py (legacy Python fallback)
fn resolve_server_script() -> Result<PathBuf, String> {
    let exe_path = std::env::current_exe().map_err(|e| e.to_string())?;
    let exe_dir = exe_path
        .parent()
        .ok_or_else(|| "Executable must have a parent directory".to_string())?;

    // Search for Rust binary first
    for candidate_root in exe_dir.ancestors() {
        let rust_binary = candidate_root
            .join("solace-runtime")
            .join("target")
            .join("release")
            .join("solace-runtime");
        if rust_binary.exists() {
            return Ok(rust_binary);
        }
    }

    // Check ~/.solace/bin/solace-runtime
    let home_bin = dirs_home().join(".solace").join("bin").join("solace-runtime");
    if home_bin.exists() {
        return Ok(home_bin);
    }

    // Fallback: Python yinyang-server.py
    for candidate_root in exe_dir.ancestors() {
        let server_script = candidate_root.join("yinyang-server.py");
        if server_script.exists() {
            return Ok(server_script);
        }
    }

    Err(format!(
        "Could not locate solace-runtime or yinyang-server.py from {}",
        exe_path.display()
    ))
}

fn resolve_browser_binary(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    let mode = browser_launch_mode();

    if let Some(resource_path) = app.path_resolver().resource_dir() {
        #[cfg(target_os = "linux")]
        {
            push_linux_browser_candidates(&mut candidates, &resource_path, mode);
            if let Some(parent) = resource_path.parent() {
                push_linux_browser_candidates(&mut candidates, parent, mode);
            }
        }
        #[cfg(target_os = "macos")]
        {
            candidates.push(resource_path.join("../../Solace Browser.app/Contents/MacOS/Solace Browser"));
        }
        #[cfg(target_os = "windows")]
        {
            candidates.push(resource_path.join("../../solace_browser.exe"));
        }
    }

    let exe_path = std::env::current_exe().map_err(|e| e.to_string())?;
    let exe_dir = exe_path
        .parent()
        .ok_or_else(|| "Executable must have a parent directory".to_string())?;

    for candidate_root in exe_dir.ancestors() {
        #[cfg(target_os = "linux")]
        {
            push_linux_browser_candidates(&mut candidates, candidate_root, mode);
        }
        #[cfg(target_os = "macos")]
        {
            candidates.push(
                candidate_root.join("dist/Solace Browser.app/Contents/MacOS/Solace Browser"),
            );
        }
        #[cfg(target_os = "windows")]
        {
            candidates.push(candidate_root.join("dist/solace_browser.exe"));
        }
    }

    for candidate in candidates {
        if candidate.is_file() {
            return Ok(candidate);
        }
    }

    Err(format!(
        "Could not locate Solace Browser binary from executable path {}",
        exe_path.display()
    ))
}

#[cfg(target_os = "linux")]
fn push_linux_browser_candidates(
    candidates: &mut Vec<PathBuf>,
    candidate_root: &Path,
    mode: BrowserLaunchMode,
) {
    let local_dev = [
        candidate_root.join("source/src/out/Solace/chrome-wrapper"),
        candidate_root.join("source/src/out/Solace/chrome"),
    ];
    let production_bundle = [
        candidate_root.join("solace-browser-release/chrome"),
        candidate_root.join("dist/solace-browser-release/chrome"),
    ];

    match mode {
        BrowserLaunchMode::LocalDev => {
            candidates.extend(local_dev);
            candidates.extend(production_bundle);
        }
        BrowserLaunchMode::ProductionBundle => {
            candidates.extend(production_bundle);
            candidates.extend(local_dev);
        }
        BrowserLaunchMode::Auto => {
            candidates.extend(production_bundle);
            candidates.extend(local_dev);
        }
    }
}

fn ensure_runtime_port_available() -> Result<(), String> {
    if TcpStream::connect(("127.0.0.1", YINYANG_PORT)).is_ok() {
        let lock_hint = match read_port_lock() {
            Ok(lock) => format!(
                "port.lock pid={}, token_sha256_present={}",
                lock.pid,
                !lock.token_sha256.is_empty()
            ),
            Err(_) => "port.lock unreadable or missing".to_string(),
        };
        return Err(format!(
            "Refusing to start Solace Hub: localhost:{} is already occupied. {}",
            YINYANG_PORT, lock_hint
        ));
    }
    Ok(())
}

/// Poll GET /health on the given URL until 200 OK or timeout.
/// Returns true if server became healthy within timeout_secs.
fn wait_for_server(url: &str, timeout_secs: u64) -> bool {
    let deadline = Instant::now() + Duration::from_secs(timeout_secs);
    while Instant::now() < deadline {
        if let Ok(resp) = ureq_get(url) {
            if resp {
                return true;
            }
        }
        thread::sleep(Duration::from_millis(500));
    }
    false
}

/// Minimal HTTP GET that returns the full response body as a String.
/// Uses only stdlib (TcpStream + raw HTTP/1.0) — no external crates.
fn http_get_body(url: &str) -> Result<String, Box<dyn std::error::Error>> {
    use std::io::{BufRead, BufReader, Read};
    use std::net::TcpStream;

    let url_str = url.to_string();
    let stripped = url_str
        .strip_prefix("http://")
        .ok_or("only http:// supported")?;
    let (host_port, path) = stripped.split_once('/').unwrap_or((stripped, ""));
    let path = format!("/{}", path);
    let (host, port_str) = host_port.split_once(':').unwrap_or((host_port, "8888"));
    let port: u16 = port_str.parse()?;

    let mut stream = TcpStream::connect((host, port))?;
    stream.set_read_timeout(Some(Duration::from_secs(5)))?;

    let request = format!(
        "GET {} HTTP/1.0\r\nHost: {}\r\nConnection: close\r\n\r\n",
        path, host_port
    );
    stream.write_all(request.as_bytes())?;

    let mut reader = BufReader::new(stream);
    // Skip headers: read until blank line
    loop {
        let mut line = String::new();
        reader.read_line(&mut line)?;
        if line == "\r\n" || line == "\n" || line.is_empty() {
            break;
        }
    }
    // Read body
    let mut body = String::new();
    reader.read_to_string(&mut body)?;
    Ok(body)
}

/// Minimal HTTP GET returning Ok(true) on 2xx status.
/// Uses only stdlib (TcpStream + raw HTTP) to avoid heavy crate dependency at this layer.
fn ureq_get(url: &str) -> Result<bool, Box<dyn std::error::Error>> {
    // Parse url: only http://localhost:8888/... is expected
    let url_str = url.to_string();
    let stripped = url_str
        .strip_prefix("http://")
        .ok_or("only http:// supported")?;
    let (host_port, path) = stripped.split_once('/').unwrap_or((stripped, ""));
    let path = format!("/{}", path);

    let (host, port_str) = host_port.split_once(':').unwrap_or((host_port, "8888"));
    let port: u16 = port_str.parse()?;

    use std::io::{BufRead, BufReader};
    use std::net::TcpStream;

    let mut stream = TcpStream::connect((host, port))?;
    stream.set_read_timeout(Some(Duration::from_secs(2)))?;

    let request = format!(
        "GET {} HTTP/1.0\r\nHost: {}\r\nConnection: close\r\n\r\n",
        path, host_port
    );
    stream.write_all(request.as_bytes())?;

    let mut reader = BufReader::new(stream);
    let mut first_line = String::new();
    reader.read_line(&mut first_line)?;

    // First line looks like: "HTTP/1.0 200 OK"
    let status_ok = first_line
        .split_whitespace()
        .nth(1)
        .and_then(|s| s.parse::<u16>().ok())
        .map(|code| (200..300).contains(&code))
        .unwrap_or(false);

    Ok(status_ok)
}

/// Poll for ~/.solace/port.lock to appear (written by yinyang-server on startup).
/// Returns true if the lock file exists and is valid within timeout_secs.
fn wait_for_port_lock(timeout_secs: u64) -> bool {
    let deadline = Instant::now() + Duration::from_secs(timeout_secs);
    while Instant::now() < deadline {
        if let Ok(lock) = read_port_lock() {
            if lock.port != 0 && !lock.token_sha256.is_empty() {
                return true;
            }
        }
        thread::sleep(Duration::from_millis(500));
    }
    false
}

/// Check whether the user has completed onboarding by reading ~/.solace/onboarding.json.
/// Returns true only if the file exists and contains "completed": true.
/// Falls back to false on any read or parse error (fail-closed).
fn check_onboarding_complete() -> bool {
    let home = dirs_next::home_dir().unwrap_or_default();
    let onboarding_path = home.join(".solace").join("onboarding.json");
    if !onboarding_path.exists() {
        return false;
    }
    let content = match std::fs::read_to_string(&onboarding_path) {
        Ok(c) => c,
        Err(_) => return false,
    };
    content.contains("\"completed\": true") || content.contains("\"completed\":true")
}

// launch_solace_browser removed in GLOW 461 — all browser launches now route
// through launch_browser_via_runtime() → POST /api/v1/browser/launch (dedup-safe).

fn http_post_json(url: &str, body: &str) -> Result<String, Box<dyn std::error::Error>> {
    use std::io::{BufRead, BufReader, Read};

    let url_str = url.to_string();
    let stripped = url_str
        .strip_prefix("http://")
        .ok_or("only http:// supported")?;
    let (host_port, path) = stripped.split_once('/').unwrap_or((stripped, ""));
    let path = format!("/{}", path);
    let (host, port_str) = host_port.split_once(':').unwrap_or((host_port, "8888"));
    let port: u16 = port_str.parse()?;

    let mut stream = TcpStream::connect((host, port))?;
    stream.set_read_timeout(Some(Duration::from_secs(10)))?;

    let request = format!(
        "POST {} HTTP/1.0\r\nHost: {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        path,
        host_port,
        body.len(),
        body
    );
    stream.write_all(request.as_bytes())?;

    let mut reader = BufReader::new(stream);
    let mut status_line = String::new();
    reader.read_line(&mut status_line)?;
    let status_code = status_line
        .split_whitespace()
        .nth(1)
        .ok_or("missing status code")?
        .parse::<u16>()?;
    if !(200..300).contains(&status_code) {
        return Err(format!("request failed with status {}", status_code).into());
    }
    loop {
        let mut line = String::new();
        reader.read_line(&mut line)?;
        if line == "\r\n" || line == "\n" || line.is_empty() {
            break;
        }
    }
    let mut response_body = String::new();
    reader.read_to_string(&mut response_body)?;
    Ok(response_body)
}

fn launch_browser_via_runtime(url: &str) -> Result<String, String> {
    let payload = serde_json::json!({
        "url": url,
        "source": "hub-ui",
    })
    .to_string();
    let endpoint = format!("http://localhost:{}/api/v1/browser/launch", YINYANG_PORT);
    http_post_json(&endpoint, &payload).map_err(|e| e.to_string())
}

fn launch_browser_for_hub(
    _state: State<HubState>,
    app: &tauri::AppHandle,
    requested_url: Option<&str>,
    respect_onboarding_gate: bool,
) -> Result<String, String> {
    let target_url = if respect_onboarding_gate && !check_onboarding_complete() {
        format!("http://localhost:{}/onboarding", YINYANG_PORT)
    } else if let Some(url) = requested_url {
        url.to_string()
    } else {
        "https://solaceagi.com/dashboard".to_string()
    };

    if !wait_for_port_lock(SERVER_HEALTH_TIMEOUT_SECS) {
        return Err("Yinyang Server not ready: port.lock missing after 10s".to_string());
    }

    if let Ok(response_body) = launch_browser_via_runtime(&target_url) {
        return Ok(format!("Browser launched via runtime to {target_url}: {response_body}"));
    }

    let browser_binary = resolve_browser_binary(app)?;
    let path_str = browser_binary.to_string_lossy().to_string();
    Err(format!(
        "Yinyang runtime launch failed for {target_url}. Refusing uncontrolled direct browser launch from {path_str}."
    ))
}

fn shutdown_server_process(child: &mut Child) -> Result<(), io::Error> {
    #[cfg(target_family = "unix")]
    {
        let signal_result = unsafe { libc_kill(child.id() as i32, 15) };
        if signal_result != 0 {
            return Err(io::Error::last_os_error());
        }

        thread::sleep(Duration::from_secs(3));

        if child.try_wait()?.is_none() {
            child.kill()?;
            let _ = child.wait()?;
        }

        return Ok(());
    }

    #[cfg(not(target_family = "unix"))]
    {
        child.kill()?;
        let _ = child.wait()?;
        Ok(())
    }
}

fn active_session_count(state: &HubState) -> usize {
    if let Ok(mut guard) = state.browser_child.lock() {
        if let Some(child) = guard.as_mut() {
            return match child.try_wait() {
                Ok(None) => 1,
                Ok(Some(_)) => {
                    *guard = None;
                    0
                }
                Err(_) => 0,
            };
        }
    }

    0
}

fn tray_tooltip(server_running: bool, sessions: usize) -> String {
    let status = if server_running { "running" } else { "stopped" };
    format!("Solace Hub | Yinyang Server: {status} | Sessions: {sessions}")
}

fn update_tray_tooltip(app: &tauri::AppHandle) {
    let state: State<HubState> = app.state();
    let server_running = cmd_get_server_status().unwrap_or(false);
    let sessions = active_session_count(state.inner());
    let _ = app
        .tray_handle()
        .set_tooltip(&tray_tooltip(server_running, sessions));
}

fn restore_dashboard_window(win: &Window) {
    // Force a real dashboard geometry so the tray app cannot get stuck as a tiny shell window.
    let _ = win.unminimize();
    let _ = win.set_min_size(Some(Size::Logical(LogicalSize {
        width: 800.0,
        height: 800.0,
    })));
    let _ = win.set_size(Size::Logical(LogicalSize {
        width: 1400.0,
        height: 1440.0,
    }));
    let _ = win.center();
    let _ = win.show();
    let _ = win.set_focus();
}

fn show_status_notification(_app: &tauri::AppHandle) {
    let server_running = cmd_get_server_status().unwrap_or(false);
    let status = if server_running { "running" } else { "stopped" };
    let body = format!("Yinyang Server: {status}");
    let _ = tauri::api::notification::Notification::new(KEYCHAIN_SERVICE)
        .title("Solace Hub")
        .body(&body)
        .show();
}

// ────────────────────────────────────────────────────────────────────────────
// Tauri commands (invokable from index.html)
// ────────────────────────────────────────────────────────────────────────────

#[tauri::command]
fn cmd_open_browser(state: State<HubState>, app: tauri::AppHandle) -> Result<String, String> {
    launch_browser_for_hub(state, &app, None, true)
}

#[tauri::command]
fn cmd_open_browser_url(
    state: State<HubState>,
    app: tauri::AppHandle,
    url: String,
    respect_onboarding_gate: Option<bool>,
) -> Result<String, String> {
    launch_browser_for_hub(
        state,
        &app,
        Some(&url),
        respect_onboarding_gate.unwrap_or(false),
    )
}

#[tauri::command]
fn cmd_get_server_status() -> Result<bool, String> {
    let health_url = format!("http://localhost:{}/health", YINYANG_PORT);
    ureq_get(&health_url).map_err(|e| e.to_string())
}

#[tauri::command]
fn cmd_token_is_present() -> bool {
    retrieve_token_keychain().is_ok()
}

#[tauri::command]
fn cmd_list_sessions() -> Result<String, String> {
    let url = format!("http://localhost:{}/api/v1/sessions", YINYANG_PORT);
    http_get_body(&url).map_err(|e| e.to_string())
}

#[tauri::command]
fn cmd_kill_all_sessions(state: State<HubState>) -> Result<String, String> {
    let endpoint = format!("http://localhost:{}/api/v1/browser/close", YINYANG_PORT);
    let payload = serde_json::json!({ "all": true }).to_string();
    let _ = http_post_json(&endpoint, &payload);
    // Kill local browser child if any
    {
        let mut guard = state.browser_child.lock().map_err(|e| e.to_string())?;
        if let Some(ref mut child) = *guard {
            let _ = child.kill();
        }
        *guard = None;
    }
    // Server handles its own session registry — we return success for local child.
    Ok("All local sessions terminated".to_string())
}

// ────────────────────────────────────────────────────────────────────────────
// main
// ────────────────────────────────────────────────────────────────────────────

fn main() {
    ensure_runtime_port_available()
        .unwrap_or_else(|msg| panic!("{msg}"));

    // ── Step 1: Find solace-runtime (Rust) or yinyang-server.py (Python fallback)
    let server_path = resolve_server_script()
        .expect("Cannot locate solace-runtime binary or yinyang-server.py");
    let repo_root = server_path
        .parent()
        .expect("Server binary must have a parent directory");

    // ── Step 2: Generate session token ───────────────────────────────────────
    let session_token = generate_session_token();
    let session_sha256 = sha256_hex(&session_token);
    store_token_keychain(&session_token)
        .unwrap_or_else(|e| eprintln!("WARN: Could not store token in keychain: {e}"));

    // ── Step 3: Spawn Backend Server (Rust preferred, Python fallback) ───────
    let is_rust = is_rust_runtime(&server_path);
    let server_child = spawn_backend_server(&server_path, repo_root, &session_sha256).unwrap_or_else(|e| {
        panic!(
            "FATAL: Cannot spawn {} — {}",
            if is_rust { "solace-runtime" } else { "yinyang-server.py" },
            e
        );
    });

    // ── Step 4: Wait for server to be healthy ────────────────────────────────
    let health_url = format!("http://localhost:{}/health", YINYANG_PORT);
    let ready = wait_for_server(&health_url, SERVER_HEALTH_TIMEOUT_SECS);
    if !ready {
        eprintln!(
            "FATAL: Yinyang Server did not become healthy within {}s at {}",
            SERVER_HEALTH_TIMEOUT_SECS, health_url
        );
        std::process::exit(1);
    }
    eprintln!(
        "INFO: {} healthy at {}",
        if is_rust { "Solace Runtime (Rust)" } else { "Yinyang Server (Python)" },
        health_url
    );

    // ── Step 5: Read port.lock ────────────────────────────────────────────────
    let lock = read_port_lock().unwrap_or_else(|e| {
        eprintln!("WARN: Cannot read port.lock ({e}); using defaults");
        PortLock {
            port: YINYANG_PORT,
            token_sha256: String::new(),
            pid: 0,
        }
    });

    // Verify port matches expected
    if lock.port != YINYANG_PORT {
        eprintln!(
            "FATAL: port.lock declares port {} but Solace Hub requires {}",
            lock.port, YINYANG_PORT
        );
        std::process::exit(1);
    }

    // ── Step 6: Build system tray ─────────────────────────────────────────────
    let tray_menu = SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("open_browser", "Open Solace Browser"))
        .add_item(CustomMenuItem::new("show_dashboard", "Show Dashboard"))
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(CustomMenuItem::new("status", "Status"))
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(CustomMenuItem::new("quit", "Quit"));

    let tray = SystemTray::new().with_menu(tray_menu);

    // ── Shared state ──────────────────────────────────────────────────────────
    let hub_state = HubState {
        server_child: Mutex::new(Some(server_child)),
        browser_child: Mutex::new(None),
    };

    // ── Step 7–8: Build Tauri app ─────────────────────────────────────────────
    tauri::Builder::default()
        .system_tray(tray)
        .manage(hub_state)
        .setup(|app| {
            update_tray_tooltip(&app.handle());
            if let Some(win) = app.get_window("main") {
                restore_dashboard_window(&win);
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            cmd_open_browser,
            cmd_open_browser_url,
            cmd_get_server_status,
            cmd_token_is_present,
            cmd_list_sessions,
            cmd_kill_all_sessions,
        ])
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "open_browser" => {
                    // Route through the runtime API so dedup + session tracking apply.
                    // Direct launch_solace_browser() bypasses all guards → multiple windows.
                    let start_url = if check_onboarding_complete() {
                        "https://solaceagi.com/dashboard".to_string()
                    } else {
                        format!("http://localhost:{}/onboarding", YINYANG_PORT)
                    };
                    if !wait_for_port_lock(SERVER_HEALTH_TIMEOUT_SECS) {
                        eprintln!("ERROR: Yinyang Server not ready (port.lock missing)");
                        return;
                    }
                    match launch_browser_via_runtime(&start_url) {
                        Ok(_) => update_tray_tooltip(app),
                        Err(e) => eprintln!("ERROR: Cannot launch browser via runtime: {e}"),
                    }
                }
                "show_dashboard" => {
                    if let Some(win) = app.get_window("main") {
                        restore_dashboard_window(&win);
                    }
                }
                "status" => {
                    update_tray_tooltip(app);
                    show_status_notification(app);
                }
                "quit" => {
                    // ── Step 8: Clean shutdown ──────────────────────────────
                    let state: State<HubState> = app.state();

                    if let Ok(mut guard) = state.server_child.lock() {
                        if let Some(mut child) = guard.take() {
                            if let Err(e) = shutdown_server_process(&mut child) {
                                eprintln!("WARN: Could not stop Yinyang Server cleanly: {e}");
                            }
                        }
                    }

                    // Delete port.lock
                    if let Err(e) = delete_port_lock() {
                        eprintln!("WARN: Could not delete port.lock: {e}");
                    }

                    // Clear token from keychain
                    if let Err(e) = clear_token_keychain() {
                        eprintln!("WARN: Could not clear keychain token: {e}");
                    }

                    std::process::exit(0);
                }
                _ => {}
            },
            SystemTrayEvent::LeftClick { .. } => {
                if let Some(win) = app.get_window("main") {
                    restore_dashboard_window(&win);
                }
            }
            _ => {}
        })
        .on_window_event(|event| {
            // Closing the window hides it instead of terminating the app.
            // Use "Quit" from tray for a clean shutdown.
            if let tauri::WindowEvent::CloseRequested { api, .. } = event.event() {
                event.window().hide().unwrap();
                api.prevent_close();
            }
        })
        .build(tauri::generate_context!())
        .expect("FATAL: Tauri app failed to build")
        .run(|_app, event| {
            if let RunEvent::ExitRequested { api, .. } = event {
                api.prevent_exit();
            }
        });
}

// ────────────────────────────────────────────────────────────────────────────
// Platform shims
// ────────────────────────────────────────────────────────────────────────────

// On Unix, bind to the real libc kill() symbol to send SIGTERM.
// This avoids adding the `libc` crate as a dependency.
#[cfg(target_family = "unix")]
#[link(name = "c")]
extern "C" {
    #[link_name = "kill"]
    fn libc_kill(pid: i32, sig: i32) -> i32;
}
