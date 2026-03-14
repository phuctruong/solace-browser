// Diagram: 07-browser-launch-dedup
use std::time::Instant;

use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use rand::Rng;
use serde::Deserialize;
use serde_json::json;

use crate::state::{AppState, SessionInfo, LAUNCH_DEDUP_WINDOW_SECS};

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

async fn list_sessions(State(state): State<AppState>) -> Json<serde_json::Value> {
    let sessions: Vec<SessionInfo> = state.sessions.read().values().cloned().collect();
    Json(json!({"sessions": sessions}))
}

async fn launch_session(
    State(state): State<AppState>,
    Json(payload): Json<LaunchPayload>,
) -> Json<serde_json::Value> {
    let profile = payload.profile.unwrap_or_else(|| "default".to_string());
    let url = payload
        .url
        .unwrap_or_else(|| "https://solaceagi.com".to_string());
    let mode = payload.mode.unwrap_or_else(|| "local-dev".to_string());
    let allow_duplicate = payload.allow_duplicate;

    if !allow_duplicate {
        let key = launch_key(&url, &profile, &mode);

        // ── Layer 1: Exact match — return existing session ──────────────
        {
            let sessions = state.sessions.read();
            for session in sessions.values() {
                if session.url == url && session.profile == profile && session.mode == mode {
                    return Json(json!({
                        "session": session,
                        "deduped": true,
                        "reason": "existing_session"
                    }));
                }
            }
        }

        // ── Layer 2: Inflight guard — another launch of same key in progress
        {
            let mut dedup = state.launch_dedup.write();
            dedup.cleanup();
            let cutoff =
                Instant::now() - std::time::Duration::from_secs(LAUNCH_DEDUP_WINDOW_SECS);

            if let Some(started_at) = dedup.inflight_launches.get(&key) {
                if *started_at >= cutoff {
                    return Json(json!({
                        "status": "ok",
                        "deduped": true,
                        "launch_in_progress": true,
                        "message": "A matching Solace Browser launch is already in progress."
                    }));
                }
            }

            // ── Layer 3: Storm guard — same key launched within window ───
            if let Some(last_launch) = dedup.recent_launches.get(&key) {
                if *last_launch >= cutoff {
                    return Json(json!({
                        "status": "ok",
                        "deduped": true,
                        "storm_guarded": true,
                        "message": "A matching Solace Browser window was recently launched."
                    }));
                }
            }

            // Mark this launch as in-flight
            dedup.inflight_launches.insert(key.clone(), Instant::now());
        }

        // Create the session
        let session = SessionInfo {
            session_id: uuid::Uuid::new_v4().to_string(),
            profile,
            url,
            pid: rand::thread_rng().gen_range(10_000..99_999),
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

        Json(json!({"session": session}))
    } else {
        // allow_duplicate = true: skip all dedup, create unconditionally
        let session = SessionInfo {
            session_id: uuid::Uuid::new_v4().to_string(),
            profile,
            url,
            pid: rand::thread_rng().gen_range(10_000..99_999),
            started_at: crate::utils::now_iso8601(),
            mode,
        };
        state
            .sessions
            .write()
            .insert(session.session_id.clone(), session.clone());
        Json(json!({"session": session}))
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
    Ok(Json(
        json!({"closed": session.session_id, "profile": session.profile}),
    ))
}

async fn list_profiles() -> Json<serde_json::Value> {
    Json(json!({"profiles": ["default", "work", "research", "automation"]}))
}
