// Diagram: 27-prime-wiki-snapshots
use std::fs;

use axum::{routing::get, Json, Router};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new().route("/api/v1/wiki/snapshots", get(list_snapshots))
}

async fn list_snapshots() -> Json<serde_json::Value> {
    let wiki_dir = crate::utils::solace_home().join("wiki");
    let mut snapshots = Vec::new();
    if let Ok(entries) = fs::read_dir(&wiki_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                snapshots.push(json!({
                    "name": path.file_name().and_then(|name| name.to_str()).unwrap_or_default(),
                    "modified_at": crate::utils::modified_iso8601(&path),
                    "size_bytes": fs::metadata(&path).map(|meta| meta.len()).unwrap_or(0),
                }));
            }
        }
    }
    Json(json!({"snapshots": snapshots}))
}
