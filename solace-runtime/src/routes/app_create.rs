// Diagram: apps-conductor-class + apps-cli-wrapper-class
//! App creation API — AI agents can create new Solace apps programmatically.
//!
//! POST /api/v1/apps/create — create a new app from a manifest + optional inbox files
//! This is what makes Solace the platform for AI agents:
//! An agent can build an app, test it, and share it — all via API.

use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::fs;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/apps/create", post(create_app))
        .route("/api/v1/apps/types", get(list_app_types))
}

#[derive(Deserialize)]
struct CreateAppPayload {
    /// App ID (kebab-case, unique)
    id: String,
    /// Human-readable name
    name: String,
    /// App type: standard, conductor, monitor, agent, bridge, cli
    #[serde(default = "default_type")]
    app_type: String,
    /// Domain (e.g., "localhost", "google.com", "github.com")
    #[serde(default = "default_domain")]
    domain: String,
    /// Description of what the app does
    #[serde(default)]
    description: String,
    /// Schedule (cron expression, empty for on-demand)
    #[serde(default)]
    schedule: String,
    /// For conductor: list of app IDs to orchestrate
    #[serde(default)]
    orchestrates: Vec<String>,
    /// For CLI: binary to execute
    #[serde(default)]
    binary: String,
    /// For CLI: arguments
    #[serde(default)]
    args: Vec<String>,
    /// For standard: data source URLs
    #[serde(default)]
    data_sources: Vec<String>,
    /// Optional system prompt for the app
    #[serde(default)]
    system_prompt: String,
    /// Optional template HTML
    #[serde(default)]
    template: String,
}

fn default_type() -> String { "standard".to_string() }
fn default_domain() -> String { "general".to_string() }

/// POST /api/v1/apps/create — create a new Solace app
async fn create_app(
    State(state): State<AppState>,
    Json(payload): Json<CreateAppPayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Validate ID
    if payload.id.is_empty() || payload.id.len() > 100 {
        return Err((StatusCode::BAD_REQUEST, Json(json!({"error": "id required (1-100 chars, kebab-case)"}))));
    }
    if !payload.id.chars().all(|c| c.is_alphanumeric() || c == '-' || c == '_') {
        return Err((StatusCode::BAD_REQUEST, Json(json!({"error": "id must be kebab-case (a-z, 0-9, hyphens)"}))));
    }

    // Validate type
    let valid_types = ["standard", "conductor", "monitor", "agent", "bridge", "cli"];
    if !valid_types.contains(&payload.app_type.as_str()) {
        return Err((StatusCode::BAD_REQUEST, Json(json!({"error": format!("Invalid type. Must be one of: {:?}", valid_types)}))));
    }

    // Create app directory
    let solace_home = crate::utils::solace_home();
    let app_dir = solace_home.join("apps").join(&payload.domain).join(&payload.id);

    if app_dir.exists() {
        return Err((StatusCode::CONFLICT, Json(json!({"error": format!("App {} already exists", payload.id)}))));
    }

    fs::create_dir_all(&app_dir).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
    fs::create_dir_all(app_dir.join("inbox")).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
    fs::create_dir_all(app_dir.join("inbox").join("pending")).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
    fs::create_dir_all(app_dir.join("outbox")).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
    fs::create_dir_all(app_dir.join("outbox").join("runs")).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;

    // Generate manifest.md
    let mut manifest = format!(
        r#"<!-- Diagram: 12-app-engine-pipeline -->
# App: {}
# DNA: `app({}) = inbox → engine → outbox → evidence`
# Auth: 65537 | Status: installed | Tier: free

## Identity
- **ID**: {}
- **Version**: 1.0.0
- **Domain**: {}
- **Category**: {}
- **Type**: {}
- **Safety**: A
"#,
        payload.name, payload.id, payload.id, payload.domain,
        if payload.app_type == "cli" { "developer" } else if payload.app_type == "conductor" { "orchestration" } else { "general" },
        payload.app_type,
    );

    // Add type-specific fields
    if !payload.orchestrates.is_empty() {
        manifest.push_str(&format!("- **Orchestrates**: {}\n", payload.orchestrates.join(", ")));
    }
    if !payload.binary.is_empty() {
        manifest.push_str(&format!("- **Binary**: {}\n", payload.binary));
    }
    if !payload.args.is_empty() {
        manifest.push_str(&format!("- **Args**: {}\n", payload.args.join(", ")));
    }

    manifest.push_str(&format!(
        r#"
## Configuration
```
schedule: "{}"
tier: free
report_template: {}
```

## Description
{}
"#,
        payload.schedule,
        if payload.app_type == "cli" { "cli-output" } else { "feed-digest" },
        if payload.description.is_empty() { format!("Custom {} app", payload.app_type) } else { payload.description.clone() },
    ));

    fs::write(app_dir.join("manifest.md"), &manifest)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;

    // Also write manifest.yaml for data_sources (the .md parser doesn't handle complex fields)
    if !payload.data_sources.is_empty() || !payload.orchestrates.is_empty() {
        let yaml_manifest = serde_json::json!({
            "id": payload.id,
            "name": payload.name,
            "version": "1.0.0",
            "domain": payload.domain,
            "category": if payload.app_type == "cli" { "developer" } else { "general" },
            "type": payload.app_type,
            "schedule": payload.schedule,
            "tier": "free",
            "report_template": if payload.app_type == "cli" { "cli-output" } else { "feed-digest" },
            "description": if payload.description.is_empty() { format!("Custom {} app", payload.app_type) } else { payload.description.clone() },
            "source_url": payload.data_sources.first().cloned(),
            "data_sources": payload.data_sources.iter().enumerate().map(|(i, url)| {
                serde_json::json!({"url": url, "name": format!("source_{}", i + 1), "source_type": "json", "limit": 25})
            }).collect::<Vec<_>>(),
            "orchestrates": payload.orchestrates,
            "binary": payload.binary,
            "args": payload.args,
        });
        let _ = fs::write(
            app_dir.join("manifest.yaml"),
            serde_yaml::to_string(&yaml_manifest).unwrap_or_default(),
        );
    }

    // Write system prompt if provided
    if !payload.system_prompt.is_empty() {
        fs::create_dir_all(app_dir.join("inbox").join("prompts"))
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
        fs::write(app_dir.join("inbox").join("prompts").join("system-prompt.md"), &payload.system_prompt)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
    }

    // Write template if provided
    if !payload.template.is_empty() {
        fs::create_dir_all(app_dir.join("inbox").join("templates"))
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
        fs::write(app_dir.join("inbox").join("templates").join("report.html"), &payload.template)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
    }

    // Write data sources config if provided
    if !payload.data_sources.is_empty() {
        let sources_json: Vec<Value> = payload.data_sources.iter().enumerate().map(|(i, url)| {
            json!({"url": url, "name": format!("source_{}", i + 1), "source_type": "json", "limit": 25})
        }).collect();
        fs::write(
            app_dir.join("inbox").join("data-sources.json"),
            serde_json::to_string_pretty(&sources_json).unwrap_or_default(),
        ).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
    }

    // Update app count
    *state.app_count.write() = crate::utils::scan_apps().len() as u32;

    // Record evidence
    let _ = crate::evidence::record_event(
        &solace_home,
        "app.created",
        "agent",
        json!({
            "app_id": payload.id,
            "app_type": payload.app_type,
            "domain": payload.domain,
            "binary": payload.binary,
        }),
    );

    Ok(Json(json!({
        "created": true,
        "app_id": payload.id,
        "app_type": payload.app_type,
        "domain": payload.domain,
        "path": app_dir.display().to_string(),
        "manifest": "manifest.md",
        "ready_to_run": true,
    })))
}

/// GET /api/v1/apps/types — list all supported app types
async fn list_app_types() -> Json<Value> {
    Json(json!({
        "types": [
            {
                "id": "standard",
                "name": "Standard App",
                "description": "Fetch from external domain, render report",
                "domain": "External (google.com, github.com, etc.)",
                "input": "data_sources URLs",
                "output": "report.html",
            },
            {
                "id": "conductor",
                "name": "Conductor App",
                "description": "Orchestrate other apps, synthesize across sources",
                "domain": "localhost",
                "input": "Other apps' outboxes",
                "output": "Digest report",
                "requires": "orchestrates list",
            },
            {
                "id": "cli",
                "name": "CLI Wrapper App",
                "description": "Spawn local CLI binary, capture output",
                "domain": "localhost",
                "input": "Files or prompts in inbox/pending/",
                "output": "stdout captured to outbox",
                "requires": "binary name",
            },
            {
                "id": "monitor",
                "name": "Monitor App",
                "description": "Watch for changes, alert on conditions",
                "domain": "External",
                "input": "Poll URL on schedule",
                "output": "Alert when condition met",
            },
            {
                "id": "agent",
                "name": "Agent App",
                "description": "Long-running autonomous task with HITL approval gates",
                "domain": "External",
                "input": "Task specification",
                "output": "Work product (draft, PR, report)",
            },
            {
                "id": "bridge",
                "name": "Bridge App",
                "description": "Connect two services, sync data between them",
                "domain": "Two domains",
                "input": "Service A data",
                "output": "Transformed data pushed to Service B",
            },
        ],
        "total": 6,
    }))
}
