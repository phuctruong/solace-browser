use std::collections::BTreeMap;

use axum::{extract::Path, http::StatusCode, routing::get, Json, Router};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/domains", get(list_domains))
        .route("/api/v1/domains/:domain", get(domain_detail))
}

async fn list_domains() -> Json<serde_json::Value> {
    let apps = crate::app_engine::scan_installed_apps();
    let mut counts = BTreeMap::new();
    for app in apps {
        *counts.entry(app.domain).or_insert(0usize) += 1;
    }
    Json(json!({"domains": counts}))
}

async fn domain_detail(
    Path(domain): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let apps: Vec<_> = crate::app_engine::scan_installed_apps()
        .into_iter()
        .filter(|app| app.domain == domain)
        .collect();
    if apps.is_empty() {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "domain not found"})),
        ));
    }
    Ok(Json(json!({"domain": domain, "apps": apps})))
}
