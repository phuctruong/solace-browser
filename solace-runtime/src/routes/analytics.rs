// Diagram: apps-backoffice-framework
//! Analytics — SQL queries on backoffice data (replaces Mixpanel/PostHog).
//! Uses existing SQLite databases. No DuckDB needed.

use axum::{
    extract::{Query, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::collections::HashMap;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/analytics/summary", get(summary))
        .route("/api/v1/analytics/query", post(run_query))
        .route("/api/v1/analytics/funnel", get(pipeline_funnel))
}

/// System-wide analytics summary
async fn summary(State(state): State<AppState>) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let apps = crate::utils::scan_apps();
    let part11 = crate::evidence::part11_status(&solace_home);

    // Count runs across all apps
    let mut total_runs = 0usize;
    for app in &apps {
        if let Some(dir) = crate::utils::find_app_dir(&app.id) {
            let runs_dir = dir.join("outbox").join("runs");
            if runs_dir.exists() {
                total_runs += std::fs::read_dir(&runs_dir)
                    .into_iter()
                    .flatten()
                    .filter_map(|e| e.ok())
                    .count();
            }
        }
    }

    // Backoffice stats
    let bo_apps: Vec<&str> = vec!["backoffice-crm", "backoffice-messages", "backoffice-tasks"];
    let mut bo_stats = HashMap::new();
    for app_id in &bo_apps {
        let db_path = solace_home
            .join("backoffice")
            .join(app_id)
            .join("workspace.db");
        if db_path.exists() {
            if let Ok(conn) = rusqlite::Connection::open(&db_path) {
                // Count records in all tables
                if let Ok(mut stmt) = conn.prepare(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_%'",
                ) {
                    let tables: Vec<String> = stmt
                        .query_map([], |row| row.get(0))
                        .into_iter()
                        .flatten()
                        .filter_map(|r| r.ok())
                        .collect();
                    let mut counts = HashMap::new();
                    for table in &tables {
                        let count: i64 = conn
                            .query_row(&format!("SELECT COUNT(*) FROM \"{}\"", table), [], |r| {
                                r.get(0)
                            })
                            .unwrap_or(0);
                        counts.insert(table.clone(), count);
                    }
                    bo_stats.insert(app_id.to_string(), counts);
                }
            }
        }
    }

    // Job queue stats
    let job_stats = state.job_queue.stats().unwrap_or_default();

    let domain_count = apps
        .iter()
        .map(|a| &a.domain)
        .collect::<std::collections::HashSet<_>>()
        .len();
    let wiki_dir = solace_home.join("wiki");
    let wiki_count = if wiki_dir.exists() {
        std::fs::read_dir(&wiki_dir)
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.file_name()
                    .to_string_lossy()
                    .ends_with(".prime-snapshot.md")
            })
            .count()
    } else {
        0
    };

    Json(json!({
        "apps": apps.len(),
        "total_runs": total_runs,
        "evidence_count": part11.record_count,
        "evidence_chain_valid": part11.chain_valid,
        "backoffice": bo_stats,
        "jobs": job_stats,
        "cli_workers": 12,
        "domains": domain_count,
        "wiki_snapshots": wiki_count,
    }))
}

#[derive(Deserialize)]
struct QueryRequest {
    app_id: String,
    sql: String,
}

/// Run a read-only SQL query on a backoffice database
async fn run_query(
    State(_state): State<AppState>,
    Json(req): Json<QueryRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Security: only allow SELECT queries
    let sql_upper = req.sql.trim().to_uppercase();
    if !sql_upper.starts_with("SELECT") {
        return Err((
            StatusCode::FORBIDDEN,
            Json(json!({"error": "only SELECT queries allowed"})),
        ));
    }

    let solace_home = crate::utils::solace_home();
    let db_path = solace_home
        .join("backoffice")
        .join(&req.app_id)
        .join("workspace.db");
    if !db_path.exists() {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("database not found for {}", req.app_id)})),
        ));
    }

    let conn =
        rusqlite::Connection::open_with_flags(&db_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .map_err(|e| {
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(json!({"error": format!("db: {e}")})),
                )
            })?;

    let mut stmt = conn.prepare(&req.sql).map_err(|e| {
        (
            StatusCode::BAD_REQUEST,
            Json(json!({"error": format!("sql: {e}")})),
        )
    })?;

    let col_names: Vec<String> = stmt.column_names().iter().map(|s| s.to_string()).collect();
    let mut rows = stmt.query([]).map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": format!("query: {e}")})),
        )
    })?;

    let mut results = Vec::new();
    while let Some(row) = rows.next().map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": format!("row: {e}")})),
        )
    })? {
        let mut obj = serde_json::Map::new();
        for (i, name) in col_names.iter().enumerate() {
            let val: String = row.get(i).unwrap_or_default();
            obj.insert(name.clone(), Value::String(val));
        }
        results.push(Value::Object(obj));
    }

    Ok(Json(json!({
        "app_id": req.app_id,
        "sql": req.sql,
        "columns": col_names,
        "rows": results,
        "count": results.len(),
    })))
}

/// CRM pipeline funnel — counts by stage
async fn pipeline_funnel(
    State(_state): State<AppState>,
    Query(params): Query<HashMap<String, String>>,
) -> Json<Value> {
    let app_id = params
        .get("app_id")
        .cloned()
        .unwrap_or_else(|| "backoffice-crm".to_string());
    let table = params
        .get("table")
        .cloned()
        .unwrap_or_else(|| "contacts".to_string());
    let group_by = params
        .get("group_by")
        .cloned()
        .unwrap_or_else(|| "stage".to_string());

    let solace_home = crate::utils::solace_home();
    let db_path = solace_home
        .join("backoffice")
        .join(&app_id)
        .join("workspace.db");

    let mut funnel = Vec::new();
    if db_path.exists() {
        if let Ok(conn) = rusqlite::Connection::open_with_flags(
            &db_path,
            rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
        ) {
            let sql = format!(
                "SELECT \"{}\", COUNT(*) as count FROM \"{}\" GROUP BY \"{}\" ORDER BY count DESC",
                group_by, table, group_by
            );
            if let Ok(mut stmt) = conn.prepare(&sql) {
                let mut rows = stmt.query([]).unwrap();
                while let Ok(Some(row)) = rows.next() {
                    let stage: String = row.get(0).unwrap_or_default();
                    let count: i64 = row.get(1).unwrap_or(0);
                    funnel.push(json!({"stage": stage, "count": count}));
                }
            }
        }
    }

    Json(json!({
        "app_id": app_id,
        "table": table,
        "group_by": group_by,
        "funnel": funnel,
    }))
}
