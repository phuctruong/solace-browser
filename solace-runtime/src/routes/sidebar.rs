// Diagram: 08-sidebar-auth-gate
use axum::{
    extract::{
        ws::{Message, WebSocket},
        State, WebSocketUpgrade,
    },
    http::StatusCode,
    response::IntoResponse,
    routing::get,
    Json, Router,
};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/sidebar/state", get(sidebar_state))
        .route("/api/v1/sidebar/ws", get(sidebar_ws))
}

async fn sidebar_state(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(compute_sidebar_state(&state))
}

async fn sidebar_ws(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let payload = compute_sidebar_state(&state);
    if payload["gate"] == "needs_onboarding" {
        return Err((
            StatusCode::FORBIDDEN,
            Json(json!({"error": "onboarding required"})),
        ));
    }
    Ok(ws.on_upgrade(move |socket| sidebar_socket(socket, payload)))
}

async fn sidebar_socket(mut socket: WebSocket, initial: serde_json::Value) {
    let _ = socket.send(Message::Text(initial.to_string().into())).await;
    while let Some(Ok(message)) = socket.recv().await {
        match message {
            Message::Text(text) => {
                let response = json!({"ok": true, "echo": text.to_string(), "time": crate::utils::now_iso8601()});
                let _ = socket
                    .send(Message::Text(response.to_string().into()))
                    .await;
            }
            Message::Close(_) => break,
            _ => {}
        }
    }
}

/// Sidebar auth gate — 4 states per diagram 08:
///   unregistered → needs onboarding / no cloud config
///   no_llm       → registered but no BYOK key and not paid (can't chat)
///   byok         → user has own LLM API key (chat enabled, user's key)
///   paid         → managed LLM subscription (chat enabled + uplifts injected)
pub(crate) fn compute_sidebar_state(state: &AppState) -> serde_json::Value {
    let solace_home = crate::utils::solace_home();
    let onboarding = crate::config::load_onboarding(&solace_home);
    let cloud = state.cloud_config.read().clone();
    let has_byok = crate::config::has_byok_key(&solace_home);

    let gate = if !onboarding.completed {
        "unregistered"
    } else if let Some(ref config) = cloud {
        if config.paid_user {
            "paid"
        } else if has_byok {
            "byok"
        } else {
            "no_llm"
        }
    } else if has_byok {
        "byok"
    } else {
        "no_llm"
    };

    let chat_enabled = gate == "byok" || gate == "paid";
    let llm_mode = match gate {
        "paid" => "managed",
        "byok" => "byok",
        _ => "none",
    };

    json!({
        "gate": gate,
        "chat_enabled": chat_enabled,
        "llm_mode": llm_mode,
        "theme": state.theme.read().clone(),
        "sessions": state.sessions.read().len(),
        "unread_notifications": state.notifications.read().iter().filter(|note| !note.read).count(),
        "uptime_seconds": state.uptime_seconds(),
        "apps_installed": crate::utils::scan_app_dirs().len(),
    })
}
