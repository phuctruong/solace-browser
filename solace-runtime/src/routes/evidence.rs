use axum::{
    extract::{Query, State},
    http::StatusCode,
    routing::get,
    Json, Router,
};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/evidence", get(list_evidence).post(create_evidence))
        .route("/api/v1/evidence/part11", get(part11_status))
        .route("/api/v1/evidence/count", get(evidence_count))
}

#[derive(Deserialize)]
struct EvidenceQuery {
    limit: Option<usize>,
}

#[derive(Deserialize)]
struct EvidencePayload {
    event: String,
    actor: Option<String>,
    data: Option<Value>,
}

async fn list_evidence(Query(query): Query<EvidenceQuery>) -> Json<serde_json::Value> {
    let solace_home = crate::utils::solace_home();
    let entries = crate::evidence::list_evidence(&solace_home, query.limit.unwrap_or(25));
    Json(json!({"entries": entries}))
}

async fn create_evidence(
    State(state): State<AppState>,
    Json(payload): Json<EvidencePayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let solace_home = crate::utils::solace_home();
    let record = crate::evidence::record_event(
        &solace_home,
        &payload.event,
        payload.actor.as_deref().unwrap_or("runtime"),
        payload.data.unwrap_or_else(|| json!({})),
    )
    .map_err(|error| (StatusCode::BAD_REQUEST, Json(json!({"error": error}))))?;
    *state.evidence_count.write() += 1;
    Ok(Json(json!({"record": record})))
}

async fn part11_status() -> Json<serde_json::Value> {
    let solace_home = crate::utils::solace_home();
    Json(json!({"part11": crate::evidence::part11_status(&solace_home)}))
}

async fn evidence_count(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({"count": *state.evidence_count.read()}))
}
