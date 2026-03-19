// Diagram: hub-dashboard
//! Hub control endpoints — AI agents interact with Hub UI programmatically.
//! Supports: status, accessibility tree, screenshot, click, type, JS eval.
//! Uses xprop to find windows, xdotool for input, ImageMagick for screenshots.

use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/hub/status", get(hub_status))
        .route("/api/v1/hub/accessibility", get(hub_accessibility))
        .route("/api/v1/hub/action", post(hub_action))
        .route("/api/v1/hub/screenshot", post(hub_screenshot))
        .route("/api/v1/hub/click", post(hub_click))
        .route("/api/v1/hub/type", post(hub_type_text))
        .route("/api/v1/hub/key", post(hub_key))
        .route("/api/v1/hub/eval", post(hub_eval))
        .route("/api/v1/hub/dom", get(hub_dom))
}

/// Find the Solace Hub window ID using xprop (more reliable than xdotool search)
fn find_hub_window() -> Option<String> {
    let output = std::process::Command::new("xprop")
        .args(["-root", "_NET_CLIENT_LIST"])
        .output()
        .ok()?;
    let list = String::from_utf8_lossy(&output.stdout);

    for token in list.split(|c: char| c == ',' || c == ' ' || c == '\n') {
        let wid = token.trim();
        if !wid.starts_with("0x") { continue; }

        let class_out = std::process::Command::new("xprop")
            .args(["-id", wid, "WM_CLASS"])
            .output()
            .ok()?;
        let class_str = String::from_utf8_lossy(&class_out.stdout).to_lowercase();
        if class_str.contains("solace-hub") || class_str.contains("solace_hub") {
            return Some(wid.to_string());
        }
    }
    None
}

/// Find the Solace Browser window ID
fn find_browser_window() -> Option<String> {
    let output = std::process::Command::new("xprop")
        .args(["-root", "_NET_CLIENT_LIST"])
        .output()
        .ok()?;
    let list = String::from_utf8_lossy(&output.stdout);

    for token in list.split(|c: char| c == ',' || c == ' ' || c == '\n') {
        let wid = token.trim();
        if !wid.starts_with("0x") { continue; }

        let class_out = std::process::Command::new("xprop")
            .args(["-id", wid, "WM_CLASS"])
            .output()
            .ok()?;
        let class_str = String::from_utf8_lossy(&class_out.stdout).to_lowercase();
        if class_str.contains("chromium") || class_str.contains("solace") && !class_str.contains("hub") {
            return Some(wid.to_string());
        }
    }
    None
}

async fn hub_status(State(state): State<AppState>) -> Json<Value> {
    let cloud = state.cloud_config.read().clone();
    let tunnel = state.tunnel.read().clone();
    let update = state.update_status.read().clone();
    let hub_wid = find_hub_window();
    let browser_wid = find_browser_window();

    Json(json!({
        "hub": "solace-hub",
        "runtime_version": crate::updates::local_version(),
        "uptime_seconds": state.uptime_seconds(),
        "port": 8888,
        "cloud_connected": cloud.is_some(),
        "cloud_email": cloud.as_ref().map(|c| c.user_email.clone()),
        "tunnel_connected": tunnel.connected,
        "sessions": state.sessions.read().len(),
        "app_count": *state.app_count.read(),
        "evidence_count": *state.evidence_count.read(),
        "notifications": state.notifications.read().len(),
        "hub_window": hub_wid,
        "browser_window": browser_wid,
        "auto_update": {
            "enabled": update.auto_update_enabled,
            "current_version": update.current_version,
            "latest_version": update.latest_version,
            "update_available": update.update_available,
        },
    }))
}

async fn hub_accessibility(State(state): State<AppState>) -> Json<Value> {
    let cloud = state.cloud_config.read().clone();
    let has_llm = cloud.is_some() || crate::config::has_byok_key(&crate::utils::solace_home());

    Json(json!({
        "window": "solace-hub",
        "tabs": [
            {"id": "overview", "label": "Overview"},
            {"id": "sessions", "label": "Sessions"},
            {"id": "events", "label": "Events"},
            {"id": "remote", "label": "Remote"},
            {"id": "settings", "label": "Settings"},
        ],
        "overview": {
            "ai_engine_gate": {
                "label": "Choose Your AI Engine",
                "has_llm": has_llm,
                "gate_passed": has_llm,
            },
            "launch_browser": { "enabled": has_llm },
            "app_discovery": {
                "count": *state.app_count.read(),
                "url": "http://127.0.0.1:8888/dashboard",
            },
        },
        "auth": {
            "connected": cloud.is_some(),
            "email": cloud.as_ref().map(|c| c.user_email.clone()),
        },
        "actions": [
            {"id": "sign_in", "enabled": cloud.is_none()},
            {"id": "sign_out", "enabled": cloud.is_some()},
            {"id": "launch_browser", "enabled": has_llm},
            {"id": "open_local_dashboard", "enabled": true},
        ],
    }))
}

#[derive(Deserialize)]
struct ActionPayload {
    action: String,
    #[serde(default)]
    params: Value,
}

async fn hub_action(
    State(state): State<AppState>,
    Json(payload): Json<ActionPayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    match payload.action.as_str() {
        "sign_out" => {
            *state.cloud_config.write() = None;
            let solace_home = crate::utils::solace_home();
            let _ = crate::config::clear_cloud_config(&solace_home);
            Ok(Json(json!({"action": "sign_out", "result": "disconnected"})))
        }
        "launch_browser" => {
            let has_llm = state.cloud_config.read().is_some()
                || crate::config::has_byok_key(&crate::utils::solace_home());
            if !has_llm {
                return Err((
                    StatusCode::PRECONDITION_FAILED,
                    Json(json!({"error": "No AI engine configured", "llm_gate": true})),
                ));
            }
            let url = payload.params.get("url").and_then(|v| v.as_str()).unwrap_or("https://solaceagi.com/dashboard");
            Ok(Json(json!({"action": "launch_browser", "result": "use POST /api/v1/browser/launch instead", "url": url})))
        }
        _ => Err((StatusCode::BAD_REQUEST, Json(json!({"error": format!("Unknown action: {}", payload.action)})))),
    }
}

async fn hub_screenshot() -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let window_id = find_hub_window().ok_or((
        StatusCode::NOT_FOUND,
        Json(json!({"error": "Hub window not found. Is Solace Hub running?"})),
    ))?;

    let path = format!("/tmp/solace-hub-{}.png", uuid::Uuid::new_v4());
    let capture = std::process::Command::new("import")
        .args(["-window", &window_id, &path])
        .output();

    match capture {
        Ok(output) if output.status.success() => {
            let bytes = std::fs::read(&path).map_err(|e| {
                (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()})))
            })?;
            let b64 = ::base64::Engine::encode(
                &::base64::engine::general_purpose::STANDARD,
                &bytes,
            );
            let _ = std::fs::remove_file(&path);

            let solace_home = crate::utils::solace_home();
            let _ = crate::evidence::record_event(
                &solace_home,
                "hub.screenshot",
                "agent",
                json!({"window_id": window_id, "size_bytes": bytes.len()}),
            );

            Ok(Json(json!({
                "screenshot": b64,
                "window_id": window_id,
                "size_bytes": bytes.len(),
                "format": "png",
            })))
        }
        _ => Err((StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "Screenshot failed. Install ImageMagick (import command)."})))),
    }
}

/// Click at x,y coordinates in the Hub window, or click by searching for text
#[derive(Deserialize)]
struct ClickPayload {
    /// Click at specific x,y coordinates relative to window
    #[serde(default)]
    x: Option<i32>,
    #[serde(default)]
    y: Option<i32>,
    /// OR: target window ("hub" or "browser", default "hub")
    #[serde(default = "default_target_window")]
    target: String,
}

fn default_target_window() -> String {
    "hub".to_string()
}

async fn hub_click(
    Json(payload): Json<ClickPayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let window_id = if payload.target == "browser" {
        find_browser_window()
    } else {
        find_hub_window()
    }.ok_or((
        StatusCode::NOT_FOUND,
        Json(json!({"error": format!("{} window not found", payload.target)})),
    ))?;

    let x = payload.x.unwrap_or(0);
    let y = payload.y.unwrap_or(0);

    // Focus the window first
    let _ = std::process::Command::new("xdotool")
        .args(["windowfocus", "--sync", &window_id])
        .output();

    // Move mouse and click relative to window
    let result = std::process::Command::new("xdotool")
        .args([
            "mousemove", "--window", &window_id,
            &x.to_string(), &y.to_string(),
            "click", "1",
        ])
        .output();

    match result {
        Ok(output) if output.status.success() => {
            // Take a screenshot after clicking
            std::thread::sleep(std::time::Duration::from_millis(500));
            let path = format!("/tmp/solace-click-{}.png", uuid::Uuid::new_v4());
            let _ = std::process::Command::new("import")
                .args(["-window", &window_id, &path])
                .output();

            let b64 = std::fs::read(&path).ok().map(|bytes| {
                let encoded = ::base64::Engine::encode(
                    &::base64::engine::general_purpose::STANDARD,
                    &bytes,
                );
                let _ = std::fs::remove_file(&path);
                encoded
            });

            let solace_home = crate::utils::solace_home();
            let _ = crate::evidence::record_event(
                &solace_home,
                "hub.click",
                "agent",
                json!({"window_id": window_id, "x": x, "y": y, "target": payload.target}),
            );

            Ok(Json(json!({
                "clicked": true,
                "x": x,
                "y": y,
                "window_id": window_id,
                "target": payload.target,
                "screenshot_after": b64,
            })))
        }
        Ok(output) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": String::from_utf8_lossy(&output.stderr).to_string()})),
        )),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": format!("xdotool failed: {}", e)})),
        )),
    }
}

/// Type text into the focused element
#[derive(Deserialize)]
struct TypePayload {
    text: String,
    #[serde(default = "default_target_window")]
    target: String,
}

async fn hub_type_text(
    Json(payload): Json<TypePayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let window_id = if payload.target == "browser" {
        find_browser_window()
    } else {
        find_hub_window()
    }.ok_or((
        StatusCode::NOT_FOUND,
        Json(json!({"error": format!("{} window not found", payload.target)})),
    ))?;

    let _ = std::process::Command::new("xdotool")
        .args(["windowfocus", "--sync", &window_id])
        .output();

    let result = std::process::Command::new("xdotool")
        .args(["type", "--clearmodifiers", "--delay", "50", &payload.text])
        .output();

    match result {
        Ok(output) if output.status.success() => {
            Ok(Json(json!({"typed": true, "text": payload.text, "window_id": window_id})))
        }
        _ => Err((StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "xdotool type failed"})))),
    }
}

/// Send a key combination (e.g., "Tab", "Return", "ctrl+a")
#[derive(Deserialize)]
struct KeyPayload {
    key: String,
    #[serde(default = "default_target_window")]
    target: String,
}

async fn hub_key(
    Json(payload): Json<KeyPayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let window_id = if payload.target == "browser" {
        find_browser_window()
    } else {
        find_hub_window()
    }.ok_or((
        StatusCode::NOT_FOUND,
        Json(json!({"error": format!("{} window not found", payload.target)})),
    ))?;

    let _ = std::process::Command::new("xdotool")
        .args(["windowfocus", "--sync", &window_id])
        .output();

    let result = std::process::Command::new("xdotool")
        .args(["key", "--clearmodifiers", &payload.key])
        .output();

    match result {
        Ok(output) if output.status.success() => {
            Ok(Json(json!({"key_sent": true, "key": payload.key, "window_id": window_id})))
        }
        _ => Err((StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "xdotool key failed"})))),
    }
}

/// Execute JavaScript in the Hub window via xdotool (Ctrl+Shift+J to open devtools, type JS)
/// Better approach: use the runtime to serve a special eval endpoint that the Hub polls
#[derive(Deserialize)]
struct EvalPayload {
    js: String,
}

async fn hub_eval(
    State(state): State<AppState>,
    Json(payload): Json<EvalPayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Store the JS to execute — the Hub's inline script polls this
    *state.pending_js.write() = Some(payload.js.clone());

    Ok(Json(json!({
        "queued": true,
        "js": payload.js,
        "note": "JS queued. Hub polls /api/v1/hub/pending-js every 2s and executes."
    })))
}

/// Get the current DOM structure of a page served by the runtime
async fn hub_dom() -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Fetch the Hub's page from ourselves and extract structure
    let client = reqwest::Client::new();
    let resp = client.get("http://localhost:8888/")
        .timeout(std::time::Duration::from_secs(3))
        .send()
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;

    let html = resp.text().await.map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()})))
    })?;

    // Extract key elements
    let tabs: Vec<&str> = html.match_indices("data-tab=\"")
        .map(|(i, _)| {
            let start = i + 10;
            let end = html[start..].find('"').map(|e| start + e).unwrap_or(start);
            &html[start..end]
        })
        .collect();

    let buttons: usize = html.matches("<button").count();
    let links: usize = html.matches("<a ").count();
    let inputs: usize = html.matches("<input").count();
    let images: usize = html.matches("<img").count();

    Ok(Json(json!({
        "page": "/",
        "html_length": html.len(),
        "tabs": tabs,
        "interactive_elements": {
            "buttons": buttons,
            "links": links,
            "inputs": inputs,
            "images": images,
        },
        "has_topbar": html.contains("sb-topbar"),
        "has_tabs": html.contains("sb-tabs"),
        "has_launch_button": html.contains("Launch Solace Browser"),
        "has_feature_grid": html.contains("FREE"),
    })))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_target_is_hub() {
        assert_eq!(default_target_window(), "hub");
    }
}
