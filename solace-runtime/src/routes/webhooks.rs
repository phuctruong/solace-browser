// Diagram: apps-backoffice-framework
//! Webhook system — trigger HTTP callbacks on events (replaces Cloud Functions).

use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{delete, get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/webhooks", get(list_webhooks).post(create_webhook))
        .route("/api/v1/webhooks/:id", delete(delete_webhook))
        .route("/api/v1/webhooks/test/:id", post(test_webhook))
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Webhook {
    id: String,
    name: String,
    url: String,
    event: String, // e.g. "backoffice.write", "app.lifecycle", "cli.run"
    active: bool,
    created_at: String,
}

/// List all registered webhooks
async fn list_webhooks(State(_state): State<AppState>) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("runtime").join("webhooks.json");
    let hooks: Vec<Webhook> = if path.exists() {
        serde_json::from_str(&std::fs::read_to_string(&path).unwrap_or_default())
            .unwrap_or_default()
    } else {
        Vec::new()
    };
    let count = hooks.len();
    Json(json!({"webhooks": hooks, "count": count}))
}

#[derive(Deserialize)]
struct CreateWebhook {
    name: String,
    url: String,
    event: String,
}

/// Register a new webhook
async fn create_webhook(
    State(_state): State<AppState>,
    Json(body): Json<CreateWebhook>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    if body.url.is_empty() || body.event.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "url and event required"})),
        ));
    }

    let hook = Webhook {
        id: uuid::Uuid::new_v4().to_string(),
        name: body.name,
        url: body.url,
        event: body.event,
        active: true,
        created_at: chrono::Utc::now().to_rfc3339(),
    };

    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("runtime").join("webhooks.json");
    let mut hooks: Vec<Webhook> = if path.exists() {
        serde_json::from_str(&std::fs::read_to_string(&path).unwrap_or_default())
            .unwrap_or_default()
    } else {
        Vec::new()
    };
    hooks.push(hook.clone());
    let _ = std::fs::write(
        &path,
        serde_json::to_string_pretty(&hooks).unwrap_or_default(),
    );

    Ok(Json(json!({"created": true, "webhook": hook})))
}

/// Delete a webhook
async fn delete_webhook(State(_state): State<AppState>, Path(id): Path<String>) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("runtime").join("webhooks.json");
    let mut hooks: Vec<Webhook> = if path.exists() {
        serde_json::from_str(&std::fs::read_to_string(&path).unwrap_or_default())
            .unwrap_or_default()
    } else {
        Vec::new()
    };
    let before = hooks.len();
    hooks.retain(|h| h.id != id);
    let _ = std::fs::write(
        &path,
        serde_json::to_string_pretty(&hooks).unwrap_or_default(),
    );
    Json(json!({"deleted": before != hooks.len(), "remaining": hooks.len()}))
}

/// Test fire a webhook
async fn test_webhook(
    State(_state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("runtime").join("webhooks.json");
    let hooks: Vec<Webhook> = if path.exists() {
        serde_json::from_str(&std::fs::read_to_string(&path).unwrap_or_default())
            .unwrap_or_default()
    } else {
        Vec::new()
    };

    let hook = hooks.iter().find(|h| h.id == id).ok_or_else(|| {
        (
            StatusCode::NOT_FOUND,
            Json(json!({"error": "webhook not found"})),
        )
    })?;

    let client = reqwest::Client::new();
    let result = client
        .post(&hook.url)
        .json(&json!({
            "event": hook.event,
            "webhook_id": hook.id,
            "test": true,
            "timestamp": chrono::Utc::now().to_rfc3339(),
        }))
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await;

    match result {
        Ok(resp) => Ok(Json(json!({
            "fired": true,
            "status": resp.status().as_u16(),
            "webhook": hook.name,
        }))),
        Err(e) => Ok(Json(json!({
            "fired": false,
            "error": e.to_string(),
            "webhook": hook.name,
        }))),
    }
}
