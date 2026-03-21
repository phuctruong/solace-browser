// Diagram: apps-backoffice-framework
//! Backoffice REST API + HTML page routes.
//! Generic CRUD for any backoffice app defined by YAML config.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Html,
    routing::{delete, get, post, put},
    Json, Router,
};
use serde_json::{json, Value};
use std::collections::HashMap;

use crate::backoffice::schema::WorkspaceConfig;
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        // REST API
        .route("/api/v1/backoffice/:app_id/:table", get(list_records))
        .route("/api/v1/backoffice/:app_id/:table", post(create_record))
        .route("/api/v1/backoffice/:app_id/:table/:id", get(get_record))
        .route("/api/v1/backoffice/:app_id/:table/:id", put(update_record))
        .route("/api/v1/backoffice/:app_id/:table/:id", delete(delete_record))
        .route("/api/v1/backoffice/:app_id/:table/search", get(search_records))
        .route("/api/v1/backoffice/:app_id/schema", get(get_schema))
        .route("/api/v1/backoffice", get(list_backoffice_apps))
        // HTML pages
        .route("/backoffice", get(backoffice_home))
        .route("/backoffice/:app_id", get(backoffice_app_home))
        .route("/backoffice/:app_id/:table", get(backoffice_table_view))
}

/// Load workspace config for a backoffice app from its manifest.yaml
pub fn load_workspace_config(app_id: &str) -> Result<WorkspaceConfig, String> {
    let solace_home = crate::utils::solace_home();

    // Search in multiple locations
    let candidates = [
        solace_home.join("apps").join("localhost").join(app_id).join("manifest.yaml"),
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent().unwrap_or(std::path::Path::new("."))
            .parent().unwrap_or(std::path::Path::new("."))
            .join("solace-cli/data/default/apps").join(app_id).join("manifest.yaml"),
        // Installed .deb path
        std::path::PathBuf::from("/usr/lib/solace-browser/solace-browser-release/data/default/apps")
            .join(app_id).join("manifest.yaml"),
    ];

    for path in &candidates {
        if path.exists() {
            if let Ok(content) = std::fs::read_to_string(path) {
                if let Ok(manifest) = serde_yaml::from_str::<Value>(&content) {
                    if let Some(bo) = manifest.get("backoffice") {
                        if let Ok(config) = serde_json::from_value::<WorkspaceConfig>(
                            serde_json::to_value(bo).unwrap_or_default()
                        ) {
                            return Ok(config);
                        }
                    }
                }
            }
        }
    }

    Err(format!("no backoffice config found for app '{}'", app_id))
}

/// Find a table definition by name within a workspace config
fn find_table<'a>(config: &'a WorkspaceConfig, table_name: &str) -> Result<&'a crate::backoffice::schema::TableDef, String> {
    config.tables.iter().find(|t| t.name == table_name)
        .ok_or_else(|| format!("table '{}' not found", table_name))
}

// ── REST API Handlers ──

async fn list_backoffice_apps(State(_state): State<AppState>) -> Json<Value> {
    // Find all apps with category: backoffice
    let known = ["backoffice-messages", "backoffice-tasks", "backoffice-crm", "backoffice-docs", "backoffice-email", "backoffice-analytics", "backoffice-support", "backoffice-invoicing", "backoffice-scheduling", "backoffice-forms"];
    let mut apps = Vec::new();

    for app_id in &known {
        if let Ok(config) = load_workspace_config(app_id) {
            apps.push(json!({
                "app_id": app_id,
                "tables": config.tables.iter().map(|t| &t.name).collect::<Vec<_>>(),
                "views": config.views.iter().map(|v| &v.name).collect::<Vec<_>>(),
            }));
        }
    }

    Json(json!({ "backoffice_apps": apps, "count": apps.len() }))
}

async fn get_schema(
    State(_state): State<AppState>,
    Path(app_id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;

    Ok(Json(json!({
        "app_id": app_id,
        "tables": config.tables,
        "views": config.views,
        "config_hash": config.config_hash(),
    })))
}

async fn list_records(
    State(state): State<AppState>,
    Path((app_id, table)): Path<(String, String)>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;
    let table_def = find_table(&config, &table).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;

    let conn = state.backoffice_db.get_connection(&app_id, &config).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e})))
    })?;

    let page: u32 = params.get("page").and_then(|p| p.parse().ok()).unwrap_or(0);
    let page_size: u32 = params.get("page_size").and_then(|p| p.parse().ok()).unwrap_or(25);
    let sort_by = params.get("sort_by").map(|s| s.as_str());

    // Collect filter params (any param that matches a column name)
    let filters: Vec<(String, String)> = params.iter()
        .filter(|(k, _)| !["page", "page_size", "sort_by", "q"].contains(&k.as_str()))
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect();

    let c = conn.lock();
    let result = crate::backoffice::crud::select_list(&c, table_def, page, page_size, sort_by, &filters)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    Ok(Json(result))
}

async fn create_record(
    State(state): State<AppState>,
    Path((app_id, table)): Path<(String, String)>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;
    let table_def = find_table(&config, &table).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;

    let conn = state.backoffice_db.get_connection(&app_id, &config).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e})))
    })?;

    // Determine actor from cloud config or default
    let actor = state.cloud_config.read()
        .as_ref()
        .map(|c| c.user_email.clone())
        .unwrap_or_else(|| "system".to_string());

    let c = conn.lock();
    let record = crate::backoffice::crud::insert(&c, table_def, &body, &actor)
        .map_err(|e| (StatusCode::BAD_REQUEST, Json(json!({"error": e}))))?;

    // Record in global evidence chain
    let solace_home = crate::utils::solace_home();
    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("backoffice.create.{}.{}", app_id, table),
        &actor,
        json!({"record_id": record.get("id"), "table": table}),
    );
    *state.evidence_count.write() += 1;

    Ok(Json(json!({"created": true, "record": record})))
}

async fn get_record(
    State(state): State<AppState>,
    Path((app_id, table, id)): Path<(String, String, String)>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;
    let table_def = find_table(&config, &table).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;

    let conn = state.backoffice_db.get_connection(&app_id, &config).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e})))
    })?;

    let c = conn.lock();
    let record = crate::backoffice::crud::select_one(&c, table_def, &id)
        .map_err(|e| (StatusCode::NOT_FOUND, Json(json!({"error": e}))))?;

    Ok(Json(record))
}

async fn update_record(
    State(state): State<AppState>,
    Path((app_id, table, id)): Path<(String, String, String)>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;
    let table_def = find_table(&config, &table).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;

    let conn = state.backoffice_db.get_connection(&app_id, &config).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e})))
    })?;

    let actor = state.cloud_config.read()
        .as_ref()
        .map(|c| c.user_email.clone())
        .unwrap_or_else(|| "system".to_string());

    let c = conn.lock();
    let record = crate::backoffice::crud::update(&c, table_def, &id, &body, &actor)
        .map_err(|e| (StatusCode::BAD_REQUEST, Json(json!({"error": e}))))?;

    let solace_home = crate::utils::solace_home();
    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("backoffice.update.{}.{}", app_id, table),
        &actor,
        json!({"record_id": id, "table": table}),
    );
    *state.evidence_count.write() += 1;

    Ok(Json(json!({"updated": true, "record": record})))
}

async fn delete_record(
    State(state): State<AppState>,
    Path((app_id, table, id)): Path<(String, String, String)>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;
    let table_def = find_table(&config, &table).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;

    let conn = state.backoffice_db.get_connection(&app_id, &config).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e})))
    })?;

    let actor = state.cloud_config.read()
        .as_ref()
        .map(|c| c.user_email.clone())
        .unwrap_or_else(|| "system".to_string());

    let c = conn.lock();
    let result = crate::backoffice::crud::delete(&c, table_def, &id, &actor)
        .map_err(|e| (StatusCode::NOT_FOUND, Json(json!({"error": e}))))?;

    let solace_home = crate::utils::solace_home();
    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("backoffice.delete.{}.{}", app_id, table),
        &actor,
        json!({"record_id": id, "table": table}),
    );
    *state.evidence_count.write() += 1;

    Ok(Json(result))
}

async fn search_records(
    State(state): State<AppState>,
    Path((app_id, table)): Path<(String, String)>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;
    let table_def = find_table(&config, &table).map_err(|e| {
        (StatusCode::NOT_FOUND, Json(json!({"error": e})))
    })?;

    let query = params.get("q").cloned().unwrap_or_default();
    if query.is_empty() {
        return Err((StatusCode::BAD_REQUEST, Json(json!({"error": "q parameter required"}))));
    }

    let conn = state.backoffice_db.get_connection(&app_id, &config).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e})))
    })?;

    let c = conn.lock();
    let result = crate::backoffice::crud::search(&c, table_def, &query, 50)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    Ok(Json(result))
}

// ── HTML Page Handlers ──

async fn backoffice_home(State(_state): State<AppState>) -> Html<String> {
    let known = ["backoffice-messages", "backoffice-tasks", "backoffice-crm", "backoffice-docs", "backoffice-email", "backoffice-analytics", "backoffice-support", "backoffice-invoicing", "backoffice-scheduling", "backoffice-forms"];
    let mut cards = String::new();

    for app_id in &known {
        if let Ok(config) = load_workspace_config(app_id) {
            let name = app_id.replace("backoffice-", "").to_uppercase();
            let table_count = config.tables.len();
            cards.push_str(&format!(
                r#"<a href="/backoffice/{app_id}" class="sb-card" style="text-decoration:none;display:block;margin-bottom:1rem">
                  <h3>{name}</h3>
                  <p class="sb-text-muted">{table_count} tables</p>
                </a>"#,
            ));
        }
    }

    Html(format!(
        r#"<!-- Diagram: apps-backoffice-framework -->
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Solace Backoffice</title>
<link rel="stylesheet" href="/styleguide.css">
</head><body>
<div class="sb-topbar"><span class="sb-topbar-brand">Solace Backoffice</span></div>
<main class="sb-container" style="max-width:800px;margin:2rem auto;padding:1rem">
<h1>Backoffice Apps</h1>
<p class="sb-text-muted">SQLite-backed workspace apps for AI workers + humans.</p>
{cards}
</main></body></html>"#
    ))
}

async fn backoffice_app_home(
    State(_state): State<AppState>,
    Path(app_id): Path<String>,
) -> Result<Html<String>, (StatusCode, Html<String>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Html(format!("<h1>Not found: {e}</h1>")))
    })?;

    let name = app_id.replace("backoffice-", "").to_uppercase();
    let mut table_links = String::new();
    for table in &config.tables {
        table_links.push_str(&format!(
            r#"<a href="/backoffice/{app_id}/{table}" class="sb-card" style="text-decoration:none;display:block;margin-bottom:0.75rem">
              <h3>{table}</h3>
              <p class="sb-text-muted">{cols} columns</p>
            </a>"#,
            table = table.name,
            cols = table.columns.len(),
        ));
    }

    Ok(Html(format!(
        r#"<!-- Diagram: apps-backoffice-framework -->
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — Solace Backoffice</title>
<link rel="stylesheet" href="/styleguide.css">
</head><body>
<div class="sb-topbar">
  <a href="/backoffice" class="sb-topbar-brand" style="text-decoration:none">Solace Backoffice</a>
  <span class="sb-text-muted"> / {name}</span>
</div>
<main class="sb-container" style="max-width:800px;margin:2rem auto;padding:1rem">
<h1>{name}</h1>
{table_links}
</main></body></html>"#
    )))
}

async fn backoffice_table_view(
    State(state): State<AppState>,
    Path((app_id, table)): Path<(String, String)>,
) -> Result<Html<String>, (StatusCode, Html<String>)> {
    let config = load_workspace_config(&app_id).map_err(|e| {
        (StatusCode::NOT_FOUND, Html(format!("<h1>Not found: {e}</h1>")))
    })?;
    let table_def = find_table(&config, &table).map_err(|e| {
        (StatusCode::NOT_FOUND, Html(format!("<h1>{e}</h1>")))
    })?;

    let name = app_id.replace("backoffice-", "").to_uppercase();

    // Build table headers
    let mut headers = String::from("<th>ID</th>");
    for col in &table_def.columns {
        headers.push_str(&format!("<th>{}</th>", col.name));
    }
    headers.push_str("<th>Created</th>");

    // Fetch rows
    let mut rows_html = String::new();
    if let Ok(conn) = state.backoffice_db.get_connection(&app_id, &config) {
        let c = conn.lock();
        if let Ok(result) = crate::backoffice::crud::select_list(&c, table_def, 0, 100, None, &[]) {
            if let Some(items) = result.get("items").and_then(|v| v.as_array()) {
                for item in items {
                    let mut row = format!("<td class=\"sb-text-mono sb-text-xs\">{}</td>",
                        item.get("id").and_then(|v| v.as_str()).unwrap_or("").chars().take(8).collect::<String>());
                    for col in &table_def.columns {
                        let val = item.get(&col.name).and_then(|v| v.as_str()).unwrap_or("");
                        let display = if col.col_type == "enum" && !val.is_empty() {
                            format!("<span class=\"sb-pill sb-pill--info\">{val}</span>")
                        } else {
                            html_escape::encode_text(val).to_string()
                        };
                        row.push_str(&format!("<td>{display}</td>"));
                    }
                    let created = item.get("created_at").and_then(|v| v.as_str()).unwrap_or("");
                    row.push_str(&format!("<td class=\"sb-text-muted sb-text-xs\">{}</td>", &created[..std::cmp::min(19, created.len())]));
                    rows_html.push_str(&format!("<tr>{row}</tr>"));
                }
            }
        }
    }

    let total = rows_html.matches("<tr>").count();

    Ok(Html(format!(
        r#"<!-- Diagram: apps-backoffice-framework -->
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{table} — {name} — Solace Backoffice</title>
<link rel="stylesheet" href="/styleguide.css">
<link rel="stylesheet" href="/vendor/jquery.dataTables.min.css">
</head><body>
<div class="sb-topbar">
  <a href="/backoffice" class="sb-topbar-brand" style="text-decoration:none">Backoffice</a>
  <span class="sb-text-muted"> / <a href="/backoffice/{app_id}">{name}</a> / {table}</span>
</div>
<main class="sb-container" style="max-width:1200px;margin:2rem auto;padding:1rem">
<h1>{table} <span class="sb-pill sb-pill--info">{total} records</span></h1>
<table class="sb-table bo-table" style="width:100%">
  <thead><tr>{headers}</tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</main>
<script src="/vendor/jquery.min.js"></script>
<script src="/vendor/jquery.dataTables.min.js"></script>
<script>
if(typeof jQuery!=='undefined'&&jQuery.fn.DataTable){{
  jQuery.fn.dataTable.ext.errMode='none';
  jQuery('.bo-table').DataTable({{paging:true,searching:true,ordering:true,pageLength:25,dom:'ftip'}});
}}
</script>
</body></html>"#
    )))
}
