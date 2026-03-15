// Diagram: hub-cli-agent-registry
use axum::{
    extract::Path,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/agents", get(list_agents))
        .route("/api/v1/agents/models", get(list_models))
        .route("/api/v1/agents/generate", post(generate_handler))
        .route("/api/v1/agents/:id/health", get(agent_health))
}

/// GET /api/v1/agents — list all known agents with installed status.
async fn list_agents() -> Json<serde_json::Value> {
    let agents = crate::agents::detect_agents();
    let installed_count = agents.iter().filter(|a| a.installed).count();
    Json(json!({
        "agents": agents,
        "total": agents.len(),
        "installed": installed_count,
    }))
}

/// GET /api/v1/agents/models — list all models per agent.
async fn list_models() -> Json<serde_json::Value> {
    let models = crate::agents::all_models();
    Json(json!({
        "models": models,
    }))
}

#[derive(Deserialize)]
struct GenerateRequest {
    agent_id: String,
    prompt: String,
    model: Option<String>,
    timeout: Option<u64>,
}

/// POST /api/v1/agents/generate — invoke an agent CLI, return response + evidence.
async fn generate_handler(
    Json(req): Json<GenerateRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    if req.prompt.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "prompt must not be empty"})),
        ));
    }

    // Run the blocking agent spawn on a dedicated thread to avoid blocking the
    // async runtime.
    let agent_id = req.agent_id.clone();
    let model = req.model.clone();
    let prompt = req.prompt.clone();
    let timeout = req.timeout;

    let result = tokio::task::spawn_blocking(move || {
        crate::agents::generate(
            &agent_id,
            model.as_deref(),
            &prompt,
            timeout,
        )
    })
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": format!("task join error: {e}")})),
        )
    })?;

    match result {
        Ok(response) => Ok(Json(json!({
            "agent_id": response.agent_id,
            "model": response.model,
            "response": response.response,
            "exit_code": response.exit_code,
            "duration_ms": response.duration_ms,
            "evidence_hash": response.evidence_hash,
        }))),
        Err(error) => Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": error})),
        )),
    }
}

/// GET /api/v1/agents/:id/health — check if a specific agent is on PATH.
async fn agent_health(
    Path(id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    match crate::agents::check_agent_health(&id) {
        Some(agent) => Ok(Json(json!({
            "agent_id": agent.id,
            "name": agent.name,
            "installed": agent.installed,
            "path": agent.path,
            "provider": agent.provider,
        }))),
        None => Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("unknown agent: {id}")})),
        )),
    }
}
