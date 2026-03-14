// Diagram: 09-yinyang-fsm
use axum::{extract::State, http::StatusCode, routing::post, Json, Router};
use serde::Deserialize;
use serde_json::json;

use crate::state::{AppState, Notification};

pub fn routes() -> Router<AppState> {
    Router::new().route("/api/v1/chat/message", post(chat_message))
}

#[derive(Deserialize)]
struct ChatPayload {
    message: String,
    persona: Option<String>,
}

async fn chat_message(
    State(state): State<AppState>,
    Json(payload): Json<ChatPayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    if payload.message.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "message required"})),
        ));
    }
    let routed_to = if state
        .cloud_config
        .read()
        .as_ref()
        .is_some_and(|config| config.paid_user)
    {
        "solace-cloud"
    } else {
        "local-preview"
    };
    state.notifications.write().push(Notification {
        id: uuid::Uuid::new_v4().to_string(),
        message: format!("Chat routed to {}", routed_to),
        level: "info".to_string(),
        read: false,
        created_at: crate::utils::now_iso8601(),
    });
    Ok(Json(json!({
        "accepted": true,
        "route": routed_to,
        "execution_mode": "preview_only",
        "persona": payload.persona.unwrap_or_else(|| "default".to_string()),
        "reply": format!("Preview routed via {}: {}", routed_to, payload.message),
    })))
}
