use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use rand::Rng;
use serde::Deserialize;
use serde_json::json;

use crate::state::{AppState, SessionInfo};

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/browser/sessions", get(list_sessions))
        .route("/api/v1/browser/launch", post(launch_session))
        .route("/api/v1/browser/close/:session_id", post(close_session))
        .route("/api/v1/browser/profiles", get(list_profiles))
}

#[derive(Deserialize)]
struct LaunchPayload {
    profile: Option<String>,
    url: Option<String>,
    mode: Option<String>,
}

async fn list_sessions(State(state): State<AppState>) -> Json<serde_json::Value> {
    let sessions: Vec<SessionInfo> = state.sessions.read().values().cloned().collect();
    Json(json!({"sessions": sessions}))
}

async fn launch_session(
    State(state): State<AppState>,
    Json(payload): Json<LaunchPayload>,
) -> Json<serde_json::Value> {
    let session = SessionInfo {
        session_id: uuid::Uuid::new_v4().to_string(),
        profile: payload.profile.unwrap_or_else(|| "default".to_string()),
        url: payload
            .url
            .unwrap_or_else(|| "https://solaceagi.com".to_string()),
        pid: rand::thread_rng().gen_range(10_000..99_999),
        started_at: crate::utils::now_iso8601(),
        mode: payload.mode.unwrap_or_else(|| "local-dev".to_string()),
    };
    state
        .sessions
        .write()
        .insert(session.session_id.clone(), session.clone());
    Json(json!({"session": session}))
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
    Ok(Json(
        json!({"closed": session.session_id, "profile": session.profile}),
    ))
}

async fn list_profiles() -> Json<serde_json::Value> {
    Json(json!({"profiles": ["default", "work", "research", "automation"]}))
}
