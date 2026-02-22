// main.rs — Solace Browser Tauri Entry Point
//
// Responsibilities:
//   1. Spawn the Python server subprocess (solace-server sidecar)
//   2. Wait for the server to become ready (health-check /ping)
//   3. Show the setup wizard on first launch (no config file present)
//   4. Open the main browser window
//   5. Handle `setup_complete` IPC command from the wizard
//   6. Gracefully terminate the Python server on exit
//
// Rung: 641 (local correctness — no production security gates required here)

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::fs;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use std::thread;

use tauri::{
    AppHandle, Manager, RunEvent, State, Window, WindowBuilder, WindowUrl,
};

// ---------------------------------------------------------------------------
// State: Python server process handle
// ---------------------------------------------------------------------------

struct ServerProcess(Arc<Mutex<Option<Child>>>);

// ---------------------------------------------------------------------------
// IPC commands
// ---------------------------------------------------------------------------

/// Called by the setup wizard (installer/welcome.html) when the user
/// clicks "Launch Solace Browser". Closes the wizard window and shows
/// the main browser window.
#[tauri::command]
fn setup_complete(app: AppHandle) -> Result<(), String> {
    // Mark setup as done by writing the config sentinel
    if let Some(config_dir) = app.path_resolver().app_config_dir() {
        let _ = fs::create_dir_all(&config_dir);
        let sentinel = config_dir.join("setup_complete");
        let _ = fs::write(&sentinel, "true");
    }

    // Close the wizard window
    if let Some(setup_win) = app.get_window("setup") {
        let _ = setup_win.close();
    }

    // Show and focus the main window
    if let Some(main_win) = app.get_window("main") {
        let _ = main_win.show();
        let _ = main_win.set_focus();
    }

    Ok(())
}

/// Returns the current version string (from Cargo.toml / tauri.conf.json).
#[tauri::command]
fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Returns whether the Python server is reachable.
#[tauri::command]
async fn server_health() -> bool {
    is_server_ready("http://localhost:8888/ping", 1).await
}

// ---------------------------------------------------------------------------
// Server management
// ---------------------------------------------------------------------------

/// Spawn the Python server sidecar. Returns the Child process handle.
fn spawn_python_server(app: &AppHandle) -> Option<Child> {
    // Tauri sidecar: resolves the bundled `solace-server` binary
    let sidecar_cmd = app.shell().sidecar("solace-server");

    match sidecar_cmd {
        Ok(cmd) => {
            match cmd.spawn() {
                Ok(child) => {
                    log::info!("Python server spawned (sidecar)");
                    Some(child.into())
                }
                Err(e) => {
                    log::warn!("Failed to spawn sidecar: {} — falling back to system python3", e);
                    spawn_system_python()
                }
            }
        }
        Err(e) => {
            log::warn!("Sidecar not available: {} — falling back to system python3", e);
            spawn_system_python()
        }
    }
}

/// Fallback: launch python3 directly from system PATH (development mode).
fn spawn_system_python() -> Option<Child> {
    // Find the project root relative to the executable
    let server_script = find_server_script();

    let child = Command::new("python3")
        .arg(server_script)
        .spawn();

    match child {
        Ok(c) => {
            log::info!("Python server spawned via system python3");
            Some(c)
        }
        Err(e) => {
            log::error!("Failed to start Python server: {}", e);
            None
        }
    }
}

fn find_server_script() -> PathBuf {
    // Walk up from the executable directory to find solace_browser_server.py
    let exe = std::env::current_exe().unwrap_or_default();
    let mut dir = exe.parent().unwrap_or(std::path::Path::new(".")).to_path_buf();

    for _ in 0..5 {
        let candidate = dir.join("solace_browser_server.py");
        if candidate.exists() {
            return candidate;
        }
        if let Some(parent) = dir.parent() {
            dir = parent.to_path_buf();
        } else {
            break;
        }
    }

    // Last resort: assume CWD
    PathBuf::from("solace_browser_server.py")
}

/// Poll until the server responds to /ping or timeout expires.
async fn is_server_ready(url: &str, timeout_secs: u64) -> bool {
    let deadline = Instant::now() + Duration::from_secs(timeout_secs);
    while Instant::now() < deadline {
        if let Ok(resp) = reqwest::get(url).await {
            if resp.status().is_success() {
                return true;
            }
        }
        thread::sleep(Duration::from_millis(200));
    }
    false
}

/// Wait for the Python server to become ready (up to 15 seconds).
async fn wait_for_server(app: &AppHandle) {
    let url = "http://localhost:8888/ping";
    let timeout = 15u64;

    log::info!("Waiting for Python server at {}", url);

    let deadline = Instant::now() + Duration::from_secs(timeout);
    let mut ready = false;

    while Instant::now() < deadline {
        if let Ok(resp) = reqwest::get(url).await {
            if resp.status().is_success() {
                ready = true;
                break;
            }
        }
        thread::sleep(Duration::from_millis(300));
    }

    if !ready {
        log::warn!(
            "Python server did not respond within {}s — opening UI anyway",
            timeout
        );
    } else {
        log::info!("Python server is ready");
    }
}

// ---------------------------------------------------------------------------
// First-launch detection
// ---------------------------------------------------------------------------

fn is_first_launch(app: &AppHandle) -> bool {
    if let Some(config_dir) = app.path_resolver().app_config_dir() {
        let sentinel = config_dir.join("setup_complete");
        return !sentinel.exists();
    }
    true
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

fn main() {
    env_logger::init();

    tauri::Builder::default()
        .manage(ServerProcess(Arc::new(Mutex::new(None))))
        .invoke_handler(tauri::generate_handler![
            setup_complete,
            get_version,
            server_health,
        ])
        .setup(|app| {
            let handle = app.handle();

            // 1. Spawn Python server
            let child = spawn_python_server(&handle);
            {
                let state: State<ServerProcess> = app.state();
                let mut lock = state.0.lock().unwrap();
                *lock = child;
            }

            // 2. Wait for server (async block executed in background)
            let handle2 = handle.clone();
            tauri::async_runtime::spawn(async move {
                wait_for_server(&handle2).await;

                // 3. Show setup wizard on first launch; else show main window
                if is_first_launch(&handle2) {
                    log::info!("First launch — showing setup wizard");
                    if let Some(setup_win) = handle2.get_window("setup") {
                        let _ = setup_win.show();
                        let _ = setup_win.set_focus();
                    }
                    // Main window stays hidden until setup_complete IPC
                } else {
                    log::info!("Returning user — showing main window");
                    if let Some(main_win) = handle2.get_window("main") {
                        let _ = main_win.show();
                        let _ = main_win.set_focus();
                    }
                    // Close setup window (should be hidden already)
                    if let Some(setup_win) = handle2.get_window("setup") {
                        let _ = setup_win.close();
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|event| {
            // Nothing special on window events for now
            let _ = event;
        })
        .build(tauri::generate_context!())
        .expect("Failed to build Tauri app")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                // Terminate the Python server when the app exits
                let state: State<ServerProcess> = app_handle.state();
                if let Ok(mut lock) = state.0.lock() {
                    if let Some(ref mut child) = *lock {
                        log::info!("Terminating Python server (PID {})", child.id());
                        let _ = child.kill();
                    }
                }
            }
        });
}
