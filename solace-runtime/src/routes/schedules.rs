use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;

use crate::state::{AppState, Schedule};

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/schedules", get(list_schedules).post(create_schedule))
        .route("/api/schedules/validate", post(validate_schedule))
        .route(
            "/api/schedules/:id",
            get(get_schedule)
                .put(update_schedule)
                .delete(delete_schedule),
        )
}

#[derive(Deserialize)]
struct SchedulePayload {
    app_id: String,
    cron: String,
    label: String,
    enabled: Option<bool>,
}

async fn list_schedules(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({"schedules": state.schedules.read().clone()}))
}

async fn create_schedule(
    State(state): State<AppState>,
    Json(payload): Json<SchedulePayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    if !crate::cron::validate_cron(&payload.cron) {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "invalid cron"})),
        ));
    }
    let schedule = Schedule {
        id: uuid::Uuid::new_v4().to_string(),
        app_id: payload.app_id,
        cron: payload.cron,
        enabled: payload.enabled.unwrap_or(true),
        label: payload.label,
        next_run: Some(crate::utils::now_iso8601()),
    };
    state.schedules.write().push(schedule.clone());
    persist_schedules(&state)?;
    Ok(Json(json!({"schedule": schedule})))
}

async fn get_schedule(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let Some(schedule) = state
        .schedules
        .read()
        .iter()
        .find(|schedule| schedule.id == id)
        .cloned()
    else {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "schedule not found"})),
        ));
    };
    Ok(Json(json!({"schedule": schedule})))
}

async fn update_schedule(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(payload): Json<SchedulePayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    if !crate::cron::validate_cron(&payload.cron) {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "invalid cron"})),
        ));
    }
    let mut schedules = state.schedules.write();
    let Some(schedule) = schedules.iter_mut().find(|schedule| schedule.id == id) else {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "schedule not found"})),
        ));
    };
    schedule.app_id = payload.app_id;
    schedule.cron = payload.cron;
    schedule.label = payload.label;
    schedule.enabled = payload.enabled.unwrap_or(schedule.enabled);
    schedule.next_run = Some(crate::utils::now_iso8601());
    let updated = schedule.clone();
    drop(schedules);
    persist_schedules(&state)?;
    Ok(Json(json!({"schedule": updated})))
}

async fn delete_schedule(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let mut schedules = state.schedules.write();
    let original_len = schedules.len();
    schedules.retain(|schedule| schedule.id != id);
    if schedules.len() == original_len {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "schedule not found"})),
        ));
    }
    drop(schedules);
    persist_schedules(&state)?;
    Ok(Json(json!({"deleted": id})))
}

async fn validate_schedule(Json(payload): Json<SchedulePayload>) -> Json<serde_json::Value> {
    Json(json!({"valid": crate::cron::validate_cron(&payload.cron)}))
}

fn persist_schedules(state: &AppState) -> Result<(), (StatusCode, Json<serde_json::Value>)> {
    let path = crate::utils::solace_home()
        .join("daemon")
        .join("schedules.json");
    crate::persistence::write_json(&path, &state.schedules.read().clone()).map_err(|error| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": error})),
        )
    })
}
