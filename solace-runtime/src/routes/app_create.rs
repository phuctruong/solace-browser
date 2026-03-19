// Diagram: apps-conductor-class + apps-cli-wrapper-class
//! App creation API — AI agents can create new Solace apps programmatically.
//!
//! POST /api/v1/apps/create — create a new app from a manifest + optional inbox files
//! This is what makes Solace the platform for AI agents:
//! An agent can build an app, test it, and share it — all via API.

use axum::{
    extract::{Path, State},
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
        .route("/api/v1/apps/create-from-job", post(create_from_job_description))
        .route("/api/v1/apps/types", get(list_app_types))
        .route("/api/v1/apps/:app_id/delete", post(delete_app))
        .route("/api/v1/apps/:app_id/update", post(update_app))
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
            {
                "id": "role",
                "name": "Role App",
                "description": "AI worker for a business function — upload a job description, get a working AI employee",
                "domain": "localhost (orchestrates external apps)",
                "input": "Job description (text or YAML)",
                "output": "Weekly role reports + actions taken",
                "roles": [
                    "bizdev", "competitor", "market", "sales", "customer_success",
                    "content", "recruiting", "financial", "legal", "product",
                    "security", "operations", "executive"
                ],
                "note": "Role apps are conductor apps organized by business function. Users upload a job description and the app configures itself.",
            },
        ],
        "total": 7,
    }))
}

/// POST /api/v1/apps/:app_id/delete — delete an app and all its data
async fn delete_app(
    Path(app_id): Path<String>,
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let app_dir = crate::utils::find_app_dir(&app_id)
        .ok_or_else(|| (StatusCode::NOT_FOUND, Json(json!({"error": format!("App {} not found", app_id)}))))?;

    // Only allow deleting apps in ~/.solace/apps/ (not bundled defaults)
    let solace_home = crate::utils::solace_home();
    if !app_dir.starts_with(solace_home.join("apps")) {
        return Err((StatusCode::FORBIDDEN, Json(json!({"error": "Cannot delete bundled default apps. Only user-created apps can be deleted."}))));
    }

    let _ = crate::evidence::record_event(
        &solace_home, &format!("app.deleted.{}", app_id), "user",
        json!({"app_id": app_id, "path": app_dir.display().to_string()}),
    );

    fs::remove_dir_all(&app_dir).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;

    *state.app_count.write() = crate::utils::scan_apps().len() as u32;

    Ok(Json(json!({"deleted": true, "app_id": app_id})))
}

#[derive(Deserialize)]
struct UpdateAppPayload {
    #[serde(default)]
    description: Option<String>,
    #[serde(default)]
    schedule: Option<String>,
    #[serde(default)]
    data_sources: Option<Vec<String>>,
    #[serde(default)]
    orchestrates: Option<Vec<String>>,
    #[serde(default)]
    binary: Option<String>,
    #[serde(default)]
    args: Option<Vec<String>>,
    #[serde(default)]
    visibility: Option<String>,
    #[serde(default)]
    system_prompt: Option<String>,
}

/// POST /api/v1/apps/:app_id/update — update app manifest fields
async fn update_app(
    Path(app_id): Path<String>,
    State(state): State<AppState>,
    Json(payload): Json<UpdateAppPayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let app_dir = crate::utils::find_app_dir(&app_id)
        .ok_or_else(|| (StatusCode::NOT_FOUND, Json(json!({"error": format!("App {} not found", app_id)}))))?;

    // Load current manifest
    let mut manifest = crate::app_engine::inbox::load_manifest(&app_dir)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    let mut updated_fields = Vec::new();

    if let Some(desc) = &payload.description {
        manifest.description = desc.clone();
        updated_fields.push("description");
    }
    if let Some(sched) = &payload.schedule {
        manifest.schedule = sched.clone();
        updated_fields.push("schedule");
    }
    if let Some(vis) = &payload.visibility {
        manifest.visibility = vis.clone();
        updated_fields.push("visibility");
    }
    if let Some(bin) = &payload.binary {
        manifest.binary = bin.clone();
        updated_fields.push("binary");
    }
    if let Some(args) = &payload.args {
        manifest.args = args.clone();
        updated_fields.push("args");
    }
    if let Some(orch) = &payload.orchestrates {
        manifest.orchestrates = orch.clone();
        updated_fields.push("orchestrates");
    }

    // Write updated manifest.yaml
    let yaml_str = serde_yaml::to_string(&manifest)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;
    fs::write(app_dir.join("manifest.yaml"), &yaml_str)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()}))))?;

    // Update system prompt if provided
    if let Some(prompt) = &payload.system_prompt {
        let prompts_dir = app_dir.join("inbox").join("prompts");
        let _ = fs::create_dir_all(&prompts_dir);
        let _ = fs::write(prompts_dir.join("system-prompt.md"), prompt);
        updated_fields.push("system_prompt");
    }

    let solace_home = crate::utils::solace_home();
    let _ = crate::evidence::record_event(
        &solace_home, &format!("app.updated.{}", app_id), "user",
        json!({"app_id": app_id, "updated_fields": updated_fields}),
    );

    Ok(Json(json!({
        "updated": true,
        "app_id": app_id,
        "fields_changed": updated_fields,
    })))
}

// ─── Job Description → Role App ─────────────────────────────────────

/// Role keywords → role type mapping
const ROLE_KEYWORDS: &[(&str, &str)] = &[
    ("business development", "bizdev"),
    ("biz dev", "bizdev"),
    ("sales", "sales"),
    ("lead generation", "bizdev"),
    ("competitor", "competitor"),
    ("competitive analysis", "competitor"),
    ("market research", "market"),
    ("market analysis", "market"),
    ("market scan", "market"),
    ("content", "content"),
    ("marketing", "content"),
    ("social media", "content"),
    ("seo", "content"),
    ("recruiting", "recruiting"),
    ("hiring", "recruiting"),
    ("talent", "recruiting"),
    ("financial", "financial"),
    ("finance", "financial"),
    ("accounting", "financial"),
    ("legal", "legal"),
    ("compliance", "legal"),
    ("regulatory", "legal"),
    ("product manager", "product"),
    ("product management", "product"),
    ("security", "security"),
    ("cybersecurity", "security"),
    ("risk", "security"),
    ("operations", "operations"),
    ("ops", "operations"),
    ("customer success", "customer_success"),
    ("customer support", "customer_success"),
    ("executive", "executive"),
    ("ceo", "executive"),
    ("strategy", "executive"),
];

/// Apps commonly used by each role
fn role_apps(role: &str) -> Vec<&'static str> {
    match role {
        "bizdev" => vec!["google-search-trends", "hackernews-feed", "reddit-scanner"],
        "competitor" => vec!["google-search-trends", "reddit-scanner", "hackernews-feed"],
        "market" => vec!["google-search-trends", "reddit-scanner"],
        "sales" => vec!["google-search-trends"],
        "customer_success" => vec!["google-search-trends"],
        "content" => vec!["hackernews-feed", "reddit-scanner", "google-search-trends"],
        "recruiting" => vec!["google-search-trends", "hackernews-feed"],
        "financial" => vec!["google-search-trends"],
        "legal" => vec!["google-search-trends"],
        "product" => vec!["hackernews-feed", "reddit-scanner", "google-search-trends"],
        "security" => vec!["hackernews-feed", "reddit-scanner"],
        "operations" => vec!["google-search-trends"],
        "executive" => vec!["google-search-trends", "hackernews-feed", "reddit-scanner"],
        _ => vec!["google-search-trends"],
    }
}

fn role_persona(role: &str) -> &'static str {
    match role {
        "bizdev" => "Alex Hormozi",
        "competitor" => "Peter Thiel",
        "market" => "Ben Thompson",
        "sales" => "Grant Cardone",
        "customer_success" => "Lincoln Murphy",
        "content" => "Gary Vaynerchuk",
        "recruiting" => "Liz Ryan",
        "financial" => "Aswath Damodaran",
        "legal" => "Marc Andreessen",
        "product" => "Marty Cagan",
        "security" => "Bruce Schneier",
        "operations" => "Eliyahu Goldratt",
        "executive" => "Peter Drucker",
        _ => "Peter Drucker",
    }
}

#[derive(Deserialize)]
struct JobDescriptionPayload {
    /// The job description text (plain text or structured)
    job_description: String,
    /// Optional: override the detected role
    #[serde(default)]
    role: Option<String>,
    /// Optional: company name for customization
    #[serde(default)]
    company: Option<String>,
}

/// POST /api/v1/apps/create-from-job — create a role app from a job description
async fn create_from_job_description(
    State(state): State<AppState>,
    Json(payload): Json<JobDescriptionPayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let jd_lower = payload.job_description.to_lowercase();

    // Detect role from job description keywords
    let detected_role = payload.role.clone().unwrap_or_else(|| {
        for (keyword, role) in ROLE_KEYWORDS {
            if jd_lower.contains(keyword) {
                return role.to_string();
            }
        }
        "executive".to_string() // default
    });

    let company = payload.company.clone().unwrap_or_else(|| "My Company".to_string());
    let app_id = format!("{}-role-{}", company.to_lowercase().replace(' ', "-"), detected_role);
    let app_name = format!("{} — {}", company, detected_role.replace('_', " "));
    let persona = role_persona(&detected_role);
    let apps = role_apps(&detected_role);

    // Create the app directory
    let solace_home = crate::utils::solace_home();
    let app_dir = solace_home.join("apps").join("localhost").join(&app_id);
    std::fs::create_dir_all(&app_dir).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()})))
    })?;
    std::fs::create_dir_all(app_dir.join("inbox")).ok();
    std::fs::create_dir_all(app_dir.join("outbox")).ok();

    // Write manifest.yaml
    let manifest = format!(
        r#"id: {app_id}
name: "{app_name}"
version: "1.0.0"
description: "{desc}"
domain: localhost
app_type: conductor
category: role
tier: free
visibility: team
schedule: "0 8 * * 1"
orchestrates:
{orch}
levels:
  default: "L2"
  synthesis: "L3"
"#,
        app_id = app_id,
        app_name = app_name,
        desc = payload.job_description.chars().take(200).collect::<String>().replace('"', "'"),
        orch = apps.iter().map(|a| format!("  - {}", a)).collect::<Vec<_>>().join("\n"),
    );

    std::fs::write(app_dir.join("manifest.yaml"), &manifest).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e.to_string()})))
    })?;

    // Write manifest.md with Prime Mermaid format
    let manifest_md = format!(
        "<!-- Diagram: apps-role-based -->\n# Solace Role: {role}\n## DNA: `{role} = {apps_dna} → report(weekly)`\n\n## Job Description\n{jd}\n\n## Persona: {persona}\n\n## Orchestrates\n{orch_list}\n",
        role = detected_role,
        apps_dna = apps.iter().map(|a| a.replace("-", "_")).collect::<Vec<_>>().join(" × "),
        jd = payload.job_description,
        persona = persona,
        orch_list = apps.iter().map(|a| format!("- {}", a)).collect::<Vec<_>>().join("\n"),
    );
    std::fs::write(app_dir.join("manifest.md"), manifest_md).ok();

    // Save job description to inbox
    std::fs::write(app_dir.join("inbox").join("job-description.md"), &payload.job_description).ok();

    // Record evidence
    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("app.created_from_job.{}", app_id),
        "user",
        json!({"app_id": app_id, "role": detected_role, "company": company, "persona": persona}),
    );

    // Update app count
    *state.app_count.write() = crate::app_engine::scan_installed_apps().len() as u32;

    Ok(Json(json!({
        "created": true,
        "app_id": app_id,
        "role": detected_role,
        "persona": persona,
        "orchestrates": apps,
        "company": company,
        "path": app_dir.display().to_string(),
        "usage": "This role app runs weekly. Edit inbox/job-description.md to customize.",
    })))
}
