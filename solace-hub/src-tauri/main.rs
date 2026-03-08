//! Solace Hub — Tauri desktop app for Solace Browser orchestration
//!
//! Lifecycle (enforced, non-negotiable):
//!   1. spawn_yinyang_server()   — Python backend on port 8888
//!   2. wait_for_server()        — polls /health until ready (max 10s)
//!   3. read_port_lock()         — parse ~/.solace/port.lock
//!   4. store_token_keychain()   — OS keychain; NEVER plaintext in files
//!   5. build system tray
//!   6. "Open Browser" → launch_solace_browser()
//!   7. "Quit" → SIGTERM server → delete_port_lock() → clear keychain → exit
//!
//! Port 8888 ONLY. Extensions ZERO. "Solace Hub" ONLY.

#![cfg_attr(all(not(debug_assertions), target_os = "windows"), windows_subsystem = "windows")]

use std::fs;
use std::io::{self, Write};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use keyring::Entry;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::{
    CustomMenuItem, Manager, RunEvent, State, SystemTray, SystemTrayEvent, SystemTrayMenu,
    SystemTrayMenuItem,
};

// ────────────────────────────────────────────────────────────────────────────
// Constants
// ────────────────────────────────────────────────────────────────────────────

/// Port for Yinyang Server. NEVER changed. NEVER 9222.
const YINYANG_PORT: u16 = 8888;

const KEYCHAIN_SERVICE: &str = "com.solaceagi.hub";
const KEYCHAIN_USER: &str = "yinyang-token";
const PORT_LOCK_FILE: &str = ".solace/port.lock";
const SERVER_HEALTH_TIMEOUT_SECS: u64 = 10;

// ────────────────────────────────────────────────────────────────────────────
// Data structures
// ────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
struct PortLock {
    port: u16,
    /// SHA-256 hex digest of the session token. NEVER the plaintext token.
    token_hash: String,
}

#[derive(Debug, Default)]
struct HubState {
    server_child: Mutex<Option<Child>>,
    browser_child: Mutex<Option<Child>>,
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

fn write_port_lock(port: u16, token_hash: &str) -> Result<(), io::Error> {
    let lock = PortLock {
        port,
        token_hash: token_hash.to_owned(),
    };
    let path = port_lock_path();

    // Ensure parent directory exists
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    let json = serde_json::to_string_pretty(&lock)
        .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;

    let mut file = fs::File::create(&path)?;
    file.write_all(json.as_bytes())?;
    file.flush()?;
    Ok(())
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

// ────────────────────────────────────────────────────────────────────────────
// Process management
// ────────────────────────────────────────────────────────────────────────────

/// Spawn yinyang-server.py. server_path is absolute path to the script.
/// Returns the Child process; caller must retain it to prevent premature termination.
fn spawn_yinyang_server(server_path: &str) -> Result<Child, io::Error> {
    // Locate python3 on PATH
    let python = python_executable();
    Command::new(&python)
        .arg(server_path)
        .spawn()
}

/// Returns "python3" on Unix, "python" on Windows.
fn python_executable() -> &'static str {
    #[cfg(target_family = "unix")]
    { "python3" }
    #[cfg(target_family = "windows")]
    { "python" }
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

    let (host, port_str) = host_port
        .split_once(':')
        .unwrap_or((host_port, "8888"));
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

/// Launch the Solace Browser binary. browser_path is the absolute path to the binary.
fn launch_solace_browser(browser_path: &str) -> Result<Child, io::Error> {
    Command::new(browser_path).spawn()
}

// ────────────────────────────────────────────────────────────────────────────
// Tauri commands (invokable from index.html)
// ────────────────────────────────────────────────────────────────────────────

#[tauri::command]
fn cmd_open_browser(state: State<HubState>, app: tauri::AppHandle) -> Result<String, String> {
    // Locate browser binary relative to the app resource dir
    let resource_path = app
        .path_resolver()
        .resource_dir()
        .ok_or("resource dir unavailable")?;

    // Convention: Solace Browser binary lives two levels up from solace-hub resource dir
    let browser_binary = {
        #[cfg(target_os = "linux")]
        { resource_path.join("../../solace-browser") }
        #[cfg(target_os = "macos")]
        { resource_path.join("../../Solace Browser.app/Contents/MacOS/Solace Browser") }
        #[cfg(target_os = "windows")]
        { resource_path.join("../../solace_browser.exe") }
    };

    let path_str = browser_binary.to_string_lossy().to_string();
    let child = launch_solace_browser(&path_str)
        .map_err(|e| format!("Failed to launch browser: {e}"))?;

    let mut guard = state.browser_child.lock().unwrap();
    *guard = Some(child);

    Ok(format!("Browser launched from {path_str}"))
}

#[tauri::command]
fn cmd_get_server_status() -> Result<bool, String> {
    let health_url = format!("http://localhost:{}/health", YINYANG_PORT);
    ureq_get(&health_url).map_err(|e| e.to_string())
}

#[tauri::command]
fn cmd_get_token_hash() -> Result<String, String> {
    match retrieve_token_keychain() {
        Ok(token) => Ok(sha256_hex(&token)),
        Err(e) => Err(format!("Keychain error: {e}")),
    }
}

// ────────────────────────────────────────────────────────────────────────────
// main
// ────────────────────────────────────────────────────────────────────────────

fn main() {
    // ── Step 1: Find yinyang-server.py (sibling to this binary) ──────────────
    let exe_dir = std::env::current_exe()
        .expect("Cannot determine executable path")
        .parent()
        .expect("Executable must have a parent directory")
        .to_path_buf();

    let server_script = exe_dir.join("yinyang-server.py");
    let server_path = server_script.to_string_lossy().to_string();

    // ── Step 2: Spawn Yinyang Server ─────────────────────────────────────────
    let server_child = spawn_yinyang_server(&server_path)
        .expect("FATAL: Cannot spawn yinyang-server.py — check that python3 is on PATH and script exists");

    // ── Step 3: Wait for server to be healthy ────────────────────────────────
    let health_url = format!("http://localhost:{}/health", YINYANG_PORT);
    let ready = wait_for_server(&health_url, SERVER_HEALTH_TIMEOUT_SECS);
    if !ready {
        eprintln!(
            "FATAL: Yinyang Server did not become healthy within {}s at {}",
            SERVER_HEALTH_TIMEOUT_SECS, health_url
        );
        std::process::exit(1);
    }
    eprintln!("INFO: Yinyang Server healthy at {}", health_url);

    // ── Step 4: Read port.lock ────────────────────────────────────────────────
    let lock = read_port_lock().unwrap_or_else(|e| {
        eprintln!("WARN: Cannot read port.lock ({e}); using defaults");
        PortLock {
            port: YINYANG_PORT,
            token_hash: String::new(),
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

    // ── Step 5: Store token in OS keychain ────────────────────────────────────
    // token_hash in port.lock is SHA-256 of the real token.
    // The yinyang-server writes the plaintext token to keychain before we read it.
    // We verify round-trip integrity: retrieve from keychain, re-hash, compare.
    if !lock.token_hash.is_empty() {
        match retrieve_token_keychain() {
            Ok(stored_token) => {
                let computed_hash = sha256_hex(&stored_token);
                if computed_hash != lock.token_hash {
                    eprintln!("FATAL: Keychain token hash mismatch — possible tampering");
                    std::process::exit(1);
                }
            }
            Err(e) => {
                eprintln!("WARN: No token in keychain yet ({e}); server will populate on first auth");
            }
        }
    }

    // ── Step 6: Build system tray ─────────────────────────────────────────────
    let tray_menu = SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("open_browser", "Open Browser"))
        .add_item(CustomMenuItem::new("show_hub", "Show Solace Hub"))
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(CustomMenuItem::new("quit", "Quit Solace Hub"));

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
        .invoke_handler(tauri::generate_handler![
            cmd_open_browser,
            cmd_get_server_status,
            cmd_get_token_hash,
        ])
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "open_browser" => {
                    // Fire-and-forget via Tauri invoke is not available from system tray context.
                    // We dispatch the same logic inline here.
                    let resource_path = app.path_resolver().resource_dir();
                    if let Some(rp) = resource_path {
                        let browser_binary = {
                            #[cfg(target_os = "linux")]
                            { rp.join("../../solace-browser") }
                            #[cfg(target_os = "macos")]
                            { rp.join("../../Solace Browser.app/Contents/MacOS/Solace Browser") }
                            #[cfg(target_os = "windows")]
                            { rp.join("../../solace_browser.exe") }
                        };
                        let path_str = browser_binary.to_string_lossy().to_string();
                        if let Err(e) = launch_solace_browser(&path_str) {
                            eprintln!("ERROR: Cannot launch browser from tray: {e}");
                        }
                    }
                }
                "show_hub" => {
                    if let Some(win) = app.get_window("main") {
                        let _ = win.show();
                        let _ = win.set_focus();
                    }
                }
                "quit" => {
                    // ── Step 8: Clean shutdown ──────────────────────────────
                    let state: State<HubState> = app.state();

                    // SIGTERM the server child
                    if let Ok(mut guard) = state.server_child.lock() {
                        if let Some(child) = guard.as_mut() {
                            #[cfg(target_family = "unix")]
                            {
                                unsafe { libc_kill(child.id() as i32, 15 /* SIGTERM */); }
                            }
                            #[cfg(not(target_family = "unix"))]
                            {
                                let _ = child.kill();
                            }
                        }
                        *guard = None;
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
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            }
            _ => {}
        })
        .on_window_event(|event| {
            // Closing the window hides it instead of terminating the app.
            // Use "Quit Solace Hub" from tray for a clean shutdown.
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
