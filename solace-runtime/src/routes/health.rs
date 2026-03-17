// Diagram: 05-solace-runtime-architecture
use axum::{extract::State, routing::get, Json, Router};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/health", get(health))
        .route("/api/status", get(health))
        .route("/api/v1/system/status", get(system_status))
        .route("/agents", get(agents))
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({
        "ok": true,
        "service": "solace-runtime",
        "version": "0.1.0",
        "port": 8888,
        "time": crate::utils::now_iso8601(),
    }))
}

async fn system_status(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({
        "uptime_seconds": state.uptime_seconds(),
        "sessions": state.sessions.read().len(),
        "notifications": state.notifications.read().len(),
        "schedules": state.schedules.read().len(),
        "evidence_count": *state.evidence_count.read(),
        "app_count": *state.app_count.read(),
        "cloud_connected": state.cloud_config.read().is_some(),
        "theme": state.theme.read().clone(),
    }))
}

async fn agents() -> Json<serde_json::Value> {
    let cli_agents = crate::agents::detect_agents();
    let apps = crate::app_engine::scan_installed_apps();
    let domains: std::collections::HashSet<String> = apps.iter().map(|a| a.domain.clone()).collect();

    Json(json!({
        "runtime": {
            "id": "solace-runtime",
            "version": "0.1.0",
            "port": 8888,
            "endpoints": 70,
            "mcp_tools": crate::mcp::mcp_tool_definitions().len(),
        },
        "cli_agents": {
            "detected": cli_agents.len(),
            "agents": cli_agents.iter().map(|a| json!({
                "id": a.id, "name": a.name, "installed": a.installed, "provider": a.provider,
            })).collect::<Vec<_>>(),
        },
        "apps": {
            "installed": apps.len(),
            "domains": domains.len(),
        },
        "capabilities": [
            "browser_automation", "evidence_chain", "recipe_replay",
            "oauth3_vault", "budget_enforcement", "community_browsing",
            "managed_llm", "cron_scheduling", "cloud_sync",
        ],
        "developer_guide": "See APP-BUILDER-GUIDE.md in data/default/apps/",
        "build_app": {
            "step_1": "Create folder: ~/.solace/apps/{domain}/{app-id}/",
            "step_2": "Write manifest.md (Prime Mermaid format)",
            "step_3": "Add inbox/ content (prompts, templates, context)",
            "step_4": "Hub auto-discovers — test with: curl localhost:8888/api/apps",
            "step_5": "Run: curl -X POST localhost:8888/api/v1/apps/run/{app-id}",
        },
    }))
}
