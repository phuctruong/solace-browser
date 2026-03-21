// Diagram: apps-backoffice-framework
//! File Watcher — monitor local filesystem, trigger apps on change.
//! Replaces: GCloud Cloud Functions (file triggers).

use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/watchers", get(list_watchers).post(create_watcher))
        .route("/api/v1/watchers/scan", post(scan_now))
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FileWatcher {
    id: String,
    path: String,
    pattern: String, // glob pattern e.g. "*.csv"
    app_id: String,  // app to trigger on change
    active: bool,
    last_scan: String,
    files_found: usize,
}

async fn list_watchers(State(_state): State<AppState>) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("runtime").join("watchers.json");
    let watchers: Vec<FileWatcher> = if path.exists() {
        serde_json::from_str(&std::fs::read_to_string(&path).unwrap_or_default()).unwrap_or_default()
    } else {
        Vec::new()
    };
    let count = watchers.len();
    Json(json!({"watchers": watchers, "count": count}))
}

#[derive(Deserialize)]
struct CreateWatcher {
    path: String,
    pattern: String,
    app_id: String,
}

async fn create_watcher(
    State(_state): State<AppState>,
    Json(body): Json<CreateWatcher>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    if body.path.is_empty() {
        return Err((StatusCode::BAD_REQUEST, Json(json!({"error": "path required"}))));
    }

    let watcher = FileWatcher {
        id: uuid::Uuid::new_v4().to_string(),
        path: body.path,
        pattern: if body.pattern.is_empty() { "*".to_string() } else { body.pattern },
        app_id: body.app_id,
        active: true,
        last_scan: String::new(),
        files_found: 0,
    };

    let solace_home = crate::utils::solace_home();
    let wpath = solace_home.join("runtime").join("watchers.json");
    let mut watchers: Vec<FileWatcher> = if wpath.exists() {
        serde_json::from_str(&std::fs::read_to_string(&wpath).unwrap_or_default()).unwrap_or_default()
    } else {
        Vec::new()
    };
    watchers.push(watcher.clone());
    let _ = std::fs::write(&wpath, serde_json::to_string_pretty(&watchers).unwrap_or_default());

    Ok(Json(json!({"created": true, "watcher": watcher})))
}

/// Manual scan: check all watched paths for changes
async fn scan_now(State(state): State<AppState>) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let wpath = solace_home.join("runtime").join("watchers.json");
    let mut watchers: Vec<FileWatcher> = if wpath.exists() {
        serde_json::from_str(&std::fs::read_to_string(&wpath).unwrap_or_default()).unwrap_or_default()
    } else {
        Vec::new()
    };

    let mut triggered = 0;
    for watcher in watchers.iter_mut() {
        if !watcher.active { continue; }
        let pattern = format!("{}/{}", watcher.path, watcher.pattern);
        let files: Vec<_> = glob::glob(&pattern)
            .into_iter()
            .flatten()
            .filter_map(|r| r.ok())
            .collect();
        watcher.files_found = files.len();
        watcher.last_scan = chrono::Utc::now().to_rfc3339();

        if !files.is_empty() && !watcher.app_id.is_empty() {
            // Publish event for the app
            state.event_bus.publish(
                "file.changed",
                json!({
                    "watcher_id": watcher.id,
                    "path": watcher.path,
                    "files_count": files.len(),
                    "app_id": watcher.app_id,
                }),
                "file_watcher",
            );
            triggered += 1;
        }
    }

    let _ = std::fs::write(&wpath, serde_json::to_string_pretty(&watchers).unwrap_or_default());
    let count = watchers.len();
    Json(json!({"scanned": count, "triggered": triggered, "watchers": watchers}))
}
