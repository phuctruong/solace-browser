// Diagram: 31-notifications-system
use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{delete, get, put},
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;

use crate::state::{AppState, Notification};

pub fn routes() -> Router<AppState> {
    Router::new()
        .route(
            "/api/v1/notifications",
            get(list_notifications).post(create_notification),
        )
        .route("/api/v1/notifications/:id/read", put(mark_read))
        .route("/api/v1/notifications/:id", delete(delete_notification))
}

#[derive(Deserialize)]
struct NotificationPayload {
    message: String,
    level: Option<String>,
}

async fn list_notifications(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({"notifications": state.notifications.read().clone()}))
}

async fn create_notification(
    State(state): State<AppState>,
    Json(payload): Json<NotificationPayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    // Security: sanitize message to prevent XSS
    let sanitized = html_escape::encode_text(&payload.message).to_string();

    // Security: enforce max message length (1024 chars)
    if sanitized.len() > 1024 {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "message too long (max 1024 chars)"})),
        ));
    }

    let level = payload.level.unwrap_or_else(|| "info".to_string());
    let valid_levels = ["info", "warn", "warning", "error", "success"];
    if !valid_levels.contains(&level.as_str()) {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(
                json!({"error": format!("invalid level: {level}. Must be one of: {}", valid_levels.join(", "))}),
            ),
        ));
    }

    let notification = Notification {
        id: uuid::Uuid::new_v4().to_string(),
        message: sanitized,
        level,
        read: false,
        created_at: crate::utils::now_iso8601(),
    };
    let mut notifications = state.notifications.write();
    // Security: cap at 500 notifications to prevent memory bomb
    if notifications.len() >= 500 {
        // Remove oldest unread, or oldest read
        if let Some(pos) = notifications.iter().position(|n| n.read) {
            notifications.remove(pos);
        } else {
            notifications.remove(0);
        }
    }
    notifications.push(notification.clone());
    Ok(Json(json!({"notification": notification})))
}

async fn mark_read(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let mut notifications = state.notifications.write();
    let Some(notification) = notifications.iter_mut().find(|note| note.id == id) else {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "notification not found"})),
        ));
    };
    notification.read = true;
    Ok(Json(json!({"notification": notification.clone()})))
}

async fn delete_notification(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let mut notifications = state.notifications.write();
    let original_len = notifications.len();
    notifications.retain(|notification| notification.id != id);
    if notifications.len() == original_len {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "notification not found"})),
        ));
    }
    Ok(Json(json!({"deleted": id})))
}
