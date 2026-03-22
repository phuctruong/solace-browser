// Diagram: 05-solace-runtime-architecture
use axum::{extract::State, routing::get, Json, Router};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/health", get(health))
        .route("/api/status", get(health))
        .route("/api/v1/system/status", get(system_status))
        .route("/api/v1/system/updates", get(update_status))
        .route("/api/v1/system/check-update", axum::routing::post(check_update_now))
        .route("/agents", get(agents))
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({
        "ok": true,
        "service": "solace-runtime",
        "version": crate::updates::local_version(),
        "port": 8888,
        "time": crate::utils::now_iso8601(),
    }))
}

async fn update_status(State(state): State<AppState>) -> Json<serde_json::Value> {
    let status = state.update_status.read().clone();
    Json(serde_json::to_value(status).unwrap_or(json!({"error": "serialization failed"})))
}

/// POST /api/v1/system/check-update — trigger immediate update check + install
async fn check_update_now(State(state): State<AppState>) -> Json<serde_json::Value> {
    let current = crate::updates::local_version();

    match crate::updates::check_for_update().await {
        Ok(Some(manifest)) => {
            let new_version = manifest.version.clone();
            // Update found — try to install
            {
                let mut status = state.update_status.write();
                status.latest_version = Some(new_version.clone());
                status.update_available = true;
                status.last_check = Some(crate::utils::now_iso8601());
            }

            match crate::updates::download_and_install(&manifest).await {
                Ok(result) => {
                    let mut status = state.update_status.write();
                    status.last_update = Some(crate::utils::now_iso8601());
                    status.update_available = false;
                    status.last_error = None;
                    Json(json!({
                        "action": "updated",
                        "old_version": current,
                        "new_version": new_version,
                        "result": result,
                        "restart_required": true,
                    }))
                }
                Err(err) => {
                    let mut status = state.update_status.write();
                    status.last_error = Some(err.clone());
                    Json(json!({
                        "action": "update_failed",
                        "current_version": current,
                        "new_version": new_version,
                        "error": err,
                    }))
                }
            }
        }
        Ok(None) => {
            let mut status = state.update_status.write();
            status.last_check = Some(crate::utils::now_iso8601());
            status.update_available = false;
            Json(json!({
                "action": "up_to_date",
                "current_version": current,
            }))
        }
        Err(err) => {
            let mut status = state.update_status.write();
            status.last_check = Some(crate::utils::now_iso8601());
            status.last_error = Some(err.clone());
            Json(json!({
                "action": "check_failed",
                "current_version": current,
                "error": err,
            }))
        }
    }
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
            "version": crate::updates::local_version(),
            "port": 8888,
            "endpoints": 75,
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
            "app_creation", "cli_wrapper", "conductor_orchestration",
            "team_sharing", "esign_fda_part11", "auto_update",
            "tunnel_remote_control", "approval_queue",
            "qa_platform",
        ],
        "app_types": ["standard", "conductor", "cli", "monitor", "agent", "bridge", "qa", "role"],
        "role_types": [
            "bizdev", "competitor", "market", "sales", "customer_success",
            "content", "recruiting", "financial", "legal", "product",
            "security", "operations", "executive",
        ],
        "create_app_api": {
            "endpoint": "POST /api/v1/apps/create",
            "description": "AI agents can create new Solace apps programmatically",
            "example": {
                "id": "my-custom-app",
                "name": "My Custom App",
                "app_type": "cli",
                "domain": "localhost",
                "binary": "claude",
                "args": ["--print", "--model", "haiku"],
                "description": "AI-powered analysis tool"
            },
            "list_types": "GET /api/v1/apps/types",
        },
        "key_endpoints": {
            "create_app": "POST /api/v1/apps/create",
            "run_app": "POST /api/v1/apps/run/{app-id}",
            "list_apps": "GET /api/apps",
            "app_types": "GET /api/v1/apps/types",
            "hub_status": "GET /api/v1/hub/status",
            "hub_accessibility": "GET /api/v1/hub/accessibility",
            "evidence": "GET /api/v1/evidence",
            "esign": "POST /api/v1/esign/sign",
            "approvals": "GET /api/v1/approvals/pending",
            "chat": "POST /api/v1/chat/message",
            "domains": "GET /api/v1/domains",
            "tunnel": "GET /api/v1/tunnel/status",
            "team_share": "POST /api/v1/team/share (via solaceagi.com)",
            "qa_run": "POST /api/v1/qa/run",
            "qa_report": "GET /api/v1/qa/report",
            "qa_types": "GET /api/v1/qa/types",
            "qa_reports": "GET /api/v1/qa/reports",
            "qa_status": "GET /api/v1/qa/status",
        },
        "qa_platform": {
            "description": "QA-as-a-Platform: the browser tests itself and lets you test anything",
            "types": [
                {"id": "visual", "name": "Visual QA", "desc": "Screenshot diff, CSS tokens, responsive"},
                {"id": "api", "name": "API QA", "desc": "Endpoint smoke, schema, latency"},
                {"id": "accessibility", "name": "Accessibility QA", "desc": "WCAG 2.1 AA, ARIA, keyboard"},
                {"id": "security", "name": "Security QA", "desc": "XSS, CSRF, injection, headers"},
                {"id": "performance", "name": "Performance QA", "desc": "FCP, LCP, CLS, memory"},
                {"id": "evidence", "name": "Evidence QA", "desc": "Hash chain, ALCOA+, Part 11"},
                {"id": "integration", "name": "Integration QA", "desc": "Cross-app, e2e journeys"},
            ],
            "visibility": "public",
            "tier": "free",
            "extends_to": "AI coding agents can use QA apps to test any web project — not just Solace apps",
            "usage": "POST /api/v1/qa/run {\"qa_type\": \"visual\", \"target\": \"https://example.com\"}",
        },
    }))
}
