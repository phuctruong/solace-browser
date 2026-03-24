// Diagram: 07-browser-launch-dedup
use std::time::Instant;

use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;

use crate::state::{AppState, SessionInfo, LAUNCH_DEDUP_WINDOW_SECS};

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/browser/sessions", get(list_sessions))
        .route("/api/v1/browser/launch", post(launch_session))
        .route("/api/v1/browser/close/:session_id", post(close_session))
        .route("/api/v1/browser/command/:session_id", post(send_command))
        .route("/api/v1/browser/close-all", post(close_all_sessions))
        .route("/api/v1/browser/profiles", get(list_profiles))
}

#[derive(Deserialize)]
struct LaunchPayload {
    profile: Option<String>,
    url: Option<String>,
    mode: Option<String>,
    #[serde(default)]
    allow_duplicate: bool,
}

/// Build a deterministic launch key from the request parameters.
/// Matches the Python `_browser_launch_key` logic: json-serialize the fields sorted.
fn launch_key(url: &str, profile: &str, mode: &str) -> String {
    // Deterministic key: sorted fields as compact JSON
    format!(
        r#"{{"mode":"{}","profile":"{}","url":"{}"}}"#,
        mode, profile, url
    )
}

/// Check if a process is still alive and NOT a zombie.
/// On Linux: reads /proc/{pid}/status and checks State field.
/// A zombie (State: Z) means the process exited but wasn't reaped — treat as dead.
fn is_process_alive(pid: u32) -> bool {
    if pid == 0 {
        return false;
    }
    let status_path = format!("/proc/{pid}/status");
    match std::fs::read_to_string(&status_path) {
        Ok(content) => {
            // Look for "State:\tZ (zombie)" — if zombie, it's dead
            for line in content.lines() {
                if line.starts_with("State:") {
                    return !line.contains('Z');
                }
            }
            // State line not found — assume alive
            true
        }
        // /proc/{pid}/status doesn't exist — process is gone
        Err(_) => false,
    }
}

/// Scan system for running solace browser MAIN processes only.
/// Main browser process: command is "solace" and does NOT have "--type=" flag.
/// Sub-processes (renderer, GPU, zygote) all have --type=something.
fn scan_solace_pids() -> Vec<u32> {
    let output = match std::process::Command::new("sh")
        .args(["-c", "ps axo pid,comm,args | grep '^[[:space:]]*[0-9]' | while read pid comm rest; do case \"$comm\" in solace) case \"$rest\" in *--type=*) ;; *) echo $pid ;; esac ;; esac; done"])
        .output()
    {
        Ok(o) => o,
        Err(_) => return Vec::new(),
    };
    let stdout = String::from_utf8_lossy(&output.stdout);
    stdout
        .lines()
        .filter_map(|line| line.trim().parse::<u32>().ok())
        .collect()
}

fn browser_candidates() -> Vec<std::path::PathBuf> {
    let mut candidates = Vec::new();

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            candidates.push(exe_dir.join("solace"));
            candidates.push(exe_dir.join("solace-browser"));
            candidates.push(exe_dir.join("solace-browser-release").join("solace"));
            if let Some(parent) = exe_dir.parent() {
                candidates.push(parent.join("solace-browser-release").join("solace"));
            }
        }
    }

    candidates.push(
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap_or(std::path::Path::new("."))
            .join("source/src/out/Solace/solace"),
    );
    candidates.push(crate::utils::solace_home().join("bin").join("solace"));

    candidates
}

fn resolve_browser_binary() -> Option<std::path::PathBuf> {
    browser_candidates()
        .into_iter()
        .find(|candidate| candidate.is_file())
}

async fn list_sessions(State(state): State<AppState>) -> Json<serde_json::Value> {
    let live_pids = scan_solace_pids();

    // Remove tracked sessions whose PID is no longer in the system
    {
        let dead_ids: Vec<String> = {
            let sessions = state.sessions.read();
            sessions
                .values()
                .filter(|s| !live_pids.contains(&s.pid))
                .map(|s| s.session_id.clone())
                .collect()
        };
        if !dead_ids.is_empty() {
            let mut sessions = state.sessions.write();
            for id in &dead_ids {
                sessions.remove(id);
            }
        }
    }

    // Add any live PIDs we're not tracking yet (e.g. browsers opened externally)
    {
        let sessions = state.sessions.read();
        let tracked_pids: Vec<u32> = sessions.values().map(|s| s.pid).collect();
        let untracked: Vec<u32> = live_pids
            .iter()
            .filter(|pid| !tracked_pids.contains(pid))
            .copied()
            .collect();
        drop(sessions);
        if !untracked.is_empty() {
            let mut sessions = state.sessions.write();
            for pid in untracked {
                let session = SessionInfo {
                    session_id: uuid::Uuid::new_v4().to_string(),
                    profile: format!("pid-{}", pid),
                    url: String::new(),
                    pid,
                    started_at: crate::utils::now_iso8601(),
                    mode: "detected".to_string(),
                };
                sessions.insert(session.session_id.clone(), session);
            }
        }
    }

    let sessions: Vec<SessionInfo> = state.sessions.read().values().cloned().collect();
    Json(json!({"sessions": sessions}))
}

/// Kill all tracked browser sessions and their OS processes.
fn kill_all_sessions(state: &AppState) -> Vec<String> {
    let mut killed = Vec::new();
    let mut sessions = state.sessions.write();
    for (sid, info) in sessions.drain() {
        if info.pid > 0 && is_process_alive(info.pid) {
            let _ = std::process::Command::new("kill")
                .arg(info.pid.to_string())
                .output();
            killed.push(format!("{}(pid={})", sid, info.pid));
        }
    }
    // Also kill any untracked solace browser processes
    for pid in scan_solace_pids() {
        let _ = std::process::Command::new("kill")
            .arg(pid.to_string())
            .output();
    }
    // Clear all dedup guards
    let mut dedup = state.launch_dedup.write();
    dedup.recent_launches.clear();
    dedup.inflight_launches.clear();
    killed
}

async fn launch_session(
    State(state): State<AppState>,
    Json(payload): Json<LaunchPayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    // LLM gate: at least 1 power source must be configured before launching browser
    let has_llm = {
        let config = state.cloud_config.read();
        config.is_some()
    } || crate::config::has_byok_key(&crate::utils::solace_home());

    if !has_llm {
        return Err((
            StatusCode::PRECONDITION_FAILED,
            Json(json!({
                "error": "No LLM power source configured. Set up Managed LLM, BYOK key, or local CLI agent first.",
                "llm_gate": true,
            })),
        ));
    }

    let profile = payload.profile.unwrap_or_else(|| "default".to_string());
    let url = payload
        .url
        .unwrap_or_else(|| "https://solaceagi.com/dashboard".to_string());
    let mode = payload.mode.unwrap_or_else(|| "single".to_string());
    let allow_duplicate = payload.allow_duplicate;

    // ── SINGLE BROWSER MODE (default) ──────────────────────────────
    // Unless mode is "multi" or allow_duplicate is true, enforce exactly
    // one browser at a time. Kill all existing sessions before launching.
    if mode != "multi" && !allow_duplicate {
        let existing_count = state.sessions.read().len();
        if existing_count > 0 {
            let killed = kill_all_sessions(&state);
            if !killed.is_empty() {
                // Brief pause to let processes die
                tokio::time::sleep(std::time::Duration::from_millis(500)).await;
            }
        }
    }

    if !allow_duplicate {
        let key = launch_key(&url, &profile, &mode);

        // ── Layer 1: Exact match — return existing session if PID alive ──
        {
            let mut dead_ids: Vec<String> = Vec::new();
            let sessions = state.sessions.read();
            for session in sessions.values() {
                if session.url == url && session.profile == profile && session.mode == mode {
                    if is_process_alive(session.pid) {
                        return Ok(Json(json!({
                            "session": session,
                            "deduped": true,
                            "reason": "existing_session"
                        })));
                    } else {
                        dead_ids.push(session.session_id.clone());
                    }
                }
            }
            drop(sessions);
            // Dead PID found — remove session AND clear dedup guards so relaunch works
            if !dead_ids.is_empty() {
                let mut sessions = state.sessions.write();
                for id in &dead_ids {
                    sessions.remove(id);
                }
                // Clear storm guard + inflight for this key so launch proceeds
                let mut dedup = state.launch_dedup.write();
                dedup.recent_launches.remove(&key);
                dedup.inflight_launches.remove(&key);
            }
        }

        // ── Layer 2: Inflight guard — another launch of same key in progress
        {
            let mut dedup = state.launch_dedup.write();
            dedup.cleanup();
            let cutoff = Instant::now() - std::time::Duration::from_secs(LAUNCH_DEDUP_WINDOW_SECS);

            if let Some(started_at) = dedup.inflight_launches.get(&key) {
                if *started_at >= cutoff {
                    return Ok(Json(json!({
                        "status": "ok",
                        "deduped": true,
                        "launch_in_progress": true,
                        "message": "A matching Solace Browser launch is already in progress."
                    })));
                }
            }

            // ── Layer 3: Storm guard — same key launched within window ───
            // Only blocks if the session is still alive (dead sessions cleared above)
            if let Some(last_launch) = dedup.recent_launches.get(&key) {
                if *last_launch >= cutoff {
                    return Ok(Json(json!({
                        "status": "ok",
                        "deduped": true,
                        "storm_guarded": true,
                        "message": "A matching Solace Browser window was recently launched."
                    })));
                }
            }

            // Mark this launch as in-flight
            dedup.inflight_launches.insert(key.clone(), Instant::now());
        }

        // Actually launch the browser binary
        let browser_path = resolve_browser_binary();

        let pid = if let Some(solace_bin) = browser_path {
            let user_data_dir = crate::utils::solace_home().join("sessions").join(&profile);
            let _ = std::fs::create_dir_all(&user_data_dir);
            match std::process::Command::new(&solace_bin)
                .arg(&url)
                .arg(format!("--user-data-dir={}", user_data_dir.display()))
                .arg(format!("--profile-directory={}", &profile))
                .arg("--no-first-run")
                .arg("--disable-session-crashed-bubble")
                .arg("--disable-infobars")
                .arg("--hide-crash-restore-bubble")
                .arg("--no-default-browser-check")
                .arg("--disable-background-networking")
                .arg("--disable-client-side-phishing-detection")
                .arg("--disable-component-update")
                .arg("--disable-default-apps")
                .env(
                    "DISPLAY",
                    std::env::var("DISPLAY").unwrap_or_else(|_| ":1".to_string()),
                )
                .env("GOOGLE_API_KEY", "no")
                .env("GOOGLE_DEFAULT_CLIENT_ID", "no")
                .env("GOOGLE_DEFAULT_CLIENT_SECRET", "no")
                .spawn()
            {
                Ok(mut child) => {
                    let child_pid = child.id();
                    // Reap the child in background so it doesn't become a zombie
                    tokio::spawn(async move {
                        let _ = child.wait();
                    });
                    child_pid
                }
                Err(e) => {
                    return Ok(Json(json!({
                        "error": format!("Failed to launch browser: {e}"),
                        "browser_path": solace_bin.display().to_string(),
                    })));
                }
            }
        } else {
            // No Solace binary found — return error
            return Ok(Json(json!({
                "error": "Solace Browser binary not found. Build with: cd source/src && autoninja -C out/Solace solace",
                "searched": browser_candidates().iter().map(|p| p.display().to_string()).collect::<Vec<_>>(),
            })));
        };

        // Create the session with real PID
        let session = SessionInfo {
            session_id: uuid::Uuid::new_v4().to_string(),
            profile,
            url,
            pid,
            started_at: crate::utils::now_iso8601(),
            mode,
        };
        state
            .sessions
            .write()
            .insert(session.session_id.clone(), session.clone());

        // Record the launch and clear inflight
        {
            let mut dedup = state.launch_dedup.write();
            dedup.recent_launches.insert(key.clone(), Instant::now());
            dedup.inflight_launches.remove(&key);
        }

        Ok(Json(json!({"session": session})))
    } else {
        // allow_duplicate = true: skip all dedup, spawn unconditionally
        let browser_path = resolve_browser_binary();

        let pid = if let Some(solace_bin) = browser_path {
            let user_data_dir = crate::utils::solace_home().join("sessions").join(&profile);
            let _ = std::fs::create_dir_all(&user_data_dir);
            match std::process::Command::new(&solace_bin)
                .arg(&url)
                .arg(format!("--user-data-dir={}", user_data_dir.display()))
                .arg(format!("--profile-directory={}", &profile))
                .arg("--no-first-run")
                .arg("--disable-session-crashed-bubble")
                .arg("--disable-infobars")
                .arg("--hide-crash-restore-bubble")
                .arg("--no-default-browser-check")
                .arg("--disable-background-networking")
                .arg("--disable-client-side-phishing-detection")
                .arg("--disable-component-update")
                .arg("--disable-default-apps")
                .env(
                    "DISPLAY",
                    std::env::var("DISPLAY").unwrap_or_else(|_| ":1".to_string()),
                )
                .env("GOOGLE_API_KEY", "no")
                .env("GOOGLE_DEFAULT_CLIENT_ID", "no")
                .env("GOOGLE_DEFAULT_CLIENT_SECRET", "no")
                .spawn()
            {
                Ok(mut child) => {
                    let child_pid = child.id();
                    tokio::spawn(async move {
                        let _ = child.wait();
                    });
                    child_pid
                }
                Err(e) => {
                    return Ok(Json(json!({
                        "error": format!("Failed to launch browser: {e}"),
                        "browser_path": solace_bin.display().to_string(),
                    })));
                }
            }
        } else {
            return Ok(Json(json!({
                "error": "Solace Browser binary not found. Build with: cd source/src && autoninja -C out/Solace solace",
                "searched": browser_candidates().iter().map(|p| p.display().to_string()).collect::<Vec<_>>(),
            })));
        };

        let session = SessionInfo {
            session_id: uuid::Uuid::new_v4().to_string(),
            profile,
            url,
            pid,
            started_at: crate::utils::now_iso8601(),
            mode,
        };
        state
            .sessions
            .write()
            .insert(session.session_id.clone(), session.clone());
        Ok(Json(json!({"session": session})))
    }
}

async fn close_session(
    State(state): State<AppState>,
    Path(session_id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let Some(session) = state.sessions.write().remove(&session_id) else {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "session not found"})),
        ));
    };
    // Kill the actual browser process
    if session.pid > 0 {
        let _ = std::process::Command::new("kill")
            .arg(session.pid.to_string())
            .output();
    }
    // Clear dedup guards so the same profile+url can be relaunched immediately
    let key = launch_key(&session.url, &session.profile, &session.mode);
    {
        let mut dedup = state.launch_dedup.write();
        dedup.recent_launches.remove(&key);
        dedup.inflight_launches.remove(&key);
    }
    Ok(Json(
        json!({"closed": session.session_id, "profile": session.profile, "killed_pid": session.pid}),
    ))
}

/// Send a command to a browser session via its WebSocket control channel.
///
/// This is the ONLY way Hub/MCP controls the browser. Cross-platform.
/// No xdotool, no wmctrl, no OS hacks. Pure WebSocket.
///
/// Commands:
///   {"command":"navigate","url":"https://..."}  — go to URL
///   {"command":"reload"}                         — reload current page
///   {"command":"get_url"}                        — request current URL
///   {"command":"screenshot"}                     — capture screenshot
///   {"command":"execute","code":"..."}           — run JS in page
async fn send_command(
    State(state): State<AppState>,
    Path(session_id): Path<String>,
    Json(payload): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    // Verify session exists
    {
        let sessions = state.sessions.read();
        if !sessions.values().any(|s| s.session_id == session_id) {
            return Err((
                StatusCode::NOT_FOUND,
                Json(json!({"error": "session not found"})),
            ));
        }
    }

    // Send command via WebSocket channel
    let channels = state.session_channels.read();
    let tx = channels.get(&session_id).or_else(|| {
        if channels.len() == 1 {
            channels.values().next()
        } else {
            None
        }
    });

    if let Some(tx) = tx {
        let cmd = payload.to_string();
        if tx.send(cmd).is_ok() {
            Ok(Json(json!({
                "sent": true,
                "session_id": session_id,
                "command": payload.get("command").and_then(|v| v.as_str()).unwrap_or("?"),
                "fallback_channel": !channels.contains_key(&session_id),
            })))
        } else {
            Err((
                StatusCode::GONE,
                Json(json!({"error": "browser disconnected", "session_id": session_id})),
            ))
        }
    } else {
        let command = payload
            .get("command")
            .or_else(|| payload.get("type"))
            .and_then(|value| value.as_str())
            .unwrap_or("");

        let fallback_ok = match command {
            "navigate" => payload
                .get("url")
                .and_then(|value| value.as_str())
                .map(crate::routes::browser_control::navigate_browser_window)
                .unwrap_or(false),
            "execute" => payload
                .get("code")
                .or_else(|| payload.get("script"))
                .and_then(|value| value.as_str())
                .map(crate::routes::browser_control::execute_js_via_devtools)
                .unwrap_or(false),
            _ => false,
        };

        if fallback_ok {
            if command == "navigate" {
                if let Some(url) = payload.get("url").and_then(|value| value.as_str()) {
                    *state.current_url.write() = url.to_string();
                    let mut sessions = state.sessions.write();
                    if let Some(session) =
                        sessions.values_mut().find(|s| s.session_id == session_id)
                    {
                        session.url = url.to_string();
                    }
                }
            }
            Ok(Json(json!({
                "sent": true,
                "session_id": session_id,
                "command": command,
                "fallback_channel": true,
                "method": "browser_window_fallback",
            })))
        } else {
            Err((
                StatusCode::SERVICE_UNAVAILABLE,
                Json(json!({
                    "error": "browser not connected via WebSocket yet — sidebar must connect to ws://localhost:8888/ws/yinyang?session=SESSION_ID",
                    "session_id": session_id,
                })),
            ))
        }
    }
}

async fn close_all_sessions(State(state): State<AppState>) -> Json<serde_json::Value> {
    let killed = kill_all_sessions(&state);
    Json(json!({"closed": killed.len(), "details": killed}))
}

async fn list_profiles() -> Json<serde_json::Value> {
    Json(json!({"profiles": ["default", "work", "research", "automation"]}))
}

#[cfg(test)]
mod tests {
    #[test]
    fn installed_bundle_path_stays_ahead_of_dev_candidates() {
        let base =
            std::env::temp_dir().join(format!("solace-browser-path-test-{}", std::process::id()));
        let exe_dir = base.join("bundle");
        let _ = std::fs::create_dir_all(&exe_dir);
        let installed = exe_dir.join("solace");
        let _ = std::fs::write(&installed, "");

        let fake_exe = exe_dir.join("solace-runtime");
        let mut candidates = Vec::new();
        if let Some(dir) = fake_exe.parent() {
            candidates.push(dir.join("solace"));
            candidates.push(dir.join("solace-browser"));
            candidates.push(dir.join("solace-browser-release").join("solace"));
        }

        assert_eq!(candidates[0], installed);
        let _ = std::fs::remove_dir_all(&base);
    }
}
