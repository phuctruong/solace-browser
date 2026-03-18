// Diagram: hub-dashboard
//! Hub control endpoints — AI agents interact with Hub UI programmatically.

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
}

async fn hub_status(State(state): State<AppState>) -> Json<Value> {
    let cloud = state.cloud_config.read().clone();
    let tunnel = state.tunnel.read().clone();
    let update = state.update_status.read().clone();

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
            "launch_browser": {
                "enabled": has_llm,
            },
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
            // Use the existing browser launch endpoint internally
            Ok(Json(json!({
                "action": "launch_browser",
                "result": "use POST /api/v1/browser/launch instead",
                "url": url,
            })))
        }
        _ => Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": format!("Unknown action: {}", payload.action)})),
        )),
    }
}

async fn hub_screenshot() -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Find Solace Hub window via xdotool
    let find = std::process::Command::new("xdotool")
        .args(["search", "--name", "Solace Hub"])
        .output();

    let window_id = match find {
        Ok(output) if output.status.success() => {
            String::from_utf8_lossy(&output.stdout)
                .trim()
                .lines()
                .next()
                .unwrap_or("")
                .to_string()
        }
        _ => return Err((StatusCode::NOT_FOUND, Json(json!({"error": "Hub window not found"})))),
    };

    if window_id.is_empty() {
        return Err((StatusCode::NOT_FOUND, Json(json!({"error": "Hub window not found"}))));
    }

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
        _ => Err((StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "Screenshot failed. Install ImageMagick."})))),
    }
}
