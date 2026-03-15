// Diagram: hub-cross-app (WARM, STREAK, CELEBRATE)
use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/delight", get(delight_status))
        .route("/api/v1/delight/record", post(record_activity))
}

/// GET /api/v1/delight
///
/// Returns the current delight engine state: streak count, warm greeting,
/// celebration message (if at a milestone), and total run count.
async fn delight_status(State(state): State<AppState>) -> Json<serde_json::Value> {
    let delight = state.delight.read();
    let greeting = delight.warm_greeting();
    let celebration = delight.celebration_message();

    Json(json!({
        "greeting": greeting,
        "streak_days": delight.streak_days,
        "last_active_date": delight.last_active_date,
        "total_runs": delight.total_runs,
        "celebration": celebration,
    }))
}

/// POST /api/v1/delight/record
///
/// Records a new activity event. Updates streak and total_runs.
/// Persists state to disk so streaks survive restarts.
async fn record_activity(State(state): State<AppState>) -> Json<serde_json::Value> {
    let mut delight = state.delight.write();
    delight.record_activity();

    // Persist to disk
    let solace_home = crate::utils::solace_home();
    let daemon_dir = solace_home.join("daemon");
    let _ = std::fs::create_dir_all(&daemon_dir);
    let _ = crate::persistence::write_json(&daemon_dir.join("delight.json"), &*delight);

    let greeting = delight.warm_greeting();
    let celebration = delight.celebration_message();

    Json(json!({
        "greeting": greeting,
        "streak_days": delight.streak_days,
        "last_active_date": delight.last_active_date,
        "total_runs": delight.total_runs,
        "celebration": celebration,
        "recorded": true,
    }))
}
