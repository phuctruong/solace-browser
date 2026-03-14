// Diagram: 12-app-engine-pipeline
use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/apps", get(list_apps))
        .route("/api/v1/apps/:app_id", get(app_detail))
        .route("/api/v1/apps/run/:app_id", post(run_app))
}

async fn list_apps() -> Json<serde_json::Value> {
    Json(json!({"apps": crate::app_engine::scan_installed_apps()}))
}

async fn app_detail(
    Path(app_id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let apps = crate::app_engine::scan_installed_apps();
    let Some(app) = apps.into_iter().find(|app| app.id == app_id) else {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "app not found"})),
        ));
    };
    Ok(Json(json!({"app": app})))
}

async fn run_app(State(state): State<AppState>, Path(app_id): Path<String>) -> impl IntoResponse {
    match crate::app_engine::runner::run_app(&app_id, &state).await {
        Ok(path) => Json(json!({"ok": true, "report": path.to_string_lossy()})).into_response(),
        Err(error) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": error})),
        )
            .into_response(),
    }
}
