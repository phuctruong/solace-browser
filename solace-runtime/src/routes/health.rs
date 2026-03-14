use axum::{extract::State, routing::get, Json, Router};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/health", get(health))
        .route("/api/v1/system/status", get(system_status))
        .route("/agents", get(agents))
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({
        "ok": true,
        "service": "solace-runtime",
        "version": "0.1.0",
        "port": 8888,
        "time": crate::utils::now_iso8601(),
    }))
}

async fn system_status(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({
        "uptime_seconds": state.uptime_seconds(),
        "sessions": state.sessions.read().len(),
        "notifications": state.notifications.read().len(),
        "schedules": state.schedules.read().len(),
        "evidence_count": *state.evidence_count.read(),
        "app_count": *state.app_count.read(),
        "cloud_connected": state.cloud_config.read().is_some(),
        "theme": state.theme.read().clone(),
    }))
}

async fn agents() -> Json<serde_json::Value> {
    Json(json!({
        "agents": [{
            "id": "solace-runtime",
            "kind": "local-runtime",
            "port": 8888,
            "mcp_tools": crate::mcp::mcp_tool_definitions(),
        }],
    }))
}
