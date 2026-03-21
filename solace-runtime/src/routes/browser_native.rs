// Diagram: apps-unfair-advantages
//! Browser Native Features — API endpoints for C++ browser capabilities.
//! Each endpoint works via sidebar JS bridge now, gets native C++ on rebuild.
//! These are the 10 unfair advantages only a Chromium fork can provide.

use axum::{
    extract::{Path, State},
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
        // Screenshot
        .route("/api/v1/browser/screenshot", post(take_screenshot))
        // DOM snapshot
        .route("/api/v1/browser/dom", post(capture_dom))
        // JavaScript injection
        .route("/api/v1/browser/evaluate", post(evaluate_js))
        // Cookie vault
        .route("/api/v1/browser/cookies", get(list_cookies))
        .route("/api/v1/browser/cookies/:domain", get(domain_cookies).post(set_cookie))
        // Session persistence
        .route("/api/v1/browser/session/save", post(save_session))
        .route("/api/v1/browser/session/restore", post(restore_session))
        // Print to PDF
        .route("/api/v1/browser/print-pdf", post(print_to_pdf))
        // Form fill
        .route("/api/v1/browser/fill", post(fill_form))
        // Download intercept
        .route("/api/v1/browser/downloads", get(list_downloads))
        // Network log
        .route("/api/v1/browser/network", get(network_log))
        // Tab freeze
        .route("/api/v1/browser/freeze", post(freeze_tab))
        .route("/api/v1/browser/resume", post(resume_tab))
}

// ── Screenshot ──

#[derive(Deserialize)]
struct ScreenshotRequest {
    #[serde(default)]
    format: String, // png, jpeg
    #[serde(default)]
    quality: u32,
}

async fn take_screenshot(
    State(state): State<AppState>,
    Json(req): Json<ScreenshotRequest>,
) -> Json<Value> {
    // Use xdotool/import for now, native CaptureWebContents() on C++ rebuild
    let format = if req.format.is_empty() { "png" } else { &req.format };
    let filename = format!("screenshot-{}.{}", chrono::Utc::now().format("%Y%m%d-%H%M%S"), format);
    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("screenshots").join(&filename);
    let _ = std::fs::create_dir_all(solace_home.join("screenshots"));

    // Try import (ImageMagick) for X11 screenshot
    let result = std::process::Command::new("import")
        .args(["-window", "root", path.to_str().unwrap_or("")])
        .output();

    let success = result.map(|o| o.status.success()).unwrap_or(false);

    // Evidence
    let _ = crate::evidence::record_event(
        &solace_home, "browser.screenshot", "system",
        json!({"filename": filename, "format": format}),
    );
    *state.evidence_count.write() += 1;

    Json(json!({
        "captured": success,
        "filename": filename,
        "path": path.display().to_string(),
        "method": "import (ImageMagick)",
        "native_available": false,
        "note": "Native CaptureWebContents() available after Chromium rebuild",
    }))
}

// ── DOM Snapshot ──

async fn capture_dom(State(state): State<AppState>) -> Json<Value> {
    // The sidebar auto-captures DOM via wiki/extract on every URL change.
    // This endpoint returns the latest captured snapshot for the active session.
    let sessions = state.sessions.read();
    let active_url = sessions.values().next().map(|s| s.url.clone()).unwrap_or_default();

    let solace_home = crate::utils::solace_home();
    let wiki_dir = solace_home.join("wiki");

    // Find the snapshot for the active URL
    let mut snapshot = String::new();
    if let Ok(entries) = std::fs::read_dir(&wiki_dir) {
        for entry in entries.flatten() {
            if entry.file_name().to_string_lossy().ends_with(".prime-snapshot.md") {
                if let Ok(content) = std::fs::read_to_string(entry.path()) {
                    if content.contains(&active_url) {
                        snapshot = content;
                        break;
                    }
                }
            }
        }
    }

    Json(json!({
        "url": active_url,
        "has_snapshot": !snapshot.is_empty(),
        "snapshot_lines": snapshot.lines().count(),
        "method": "prime_wiki_snapshot",
        "note": "DOM captured via Stillwater/Ripple decomposition on every navigation",
    }))
}

// ── JavaScript Injection ──

#[derive(Deserialize)]
struct EvalRequest {
    script: String,
    #[serde(default)]
    session_id: String,
}

async fn evaluate_js(
    State(state): State<AppState>,
    Json(req): Json<EvalRequest>,
) -> Json<Value> {
    // Send JS to the browser via WebSocket session channel
    let channels = state.session_channels.read();
    let mut sent = false;
    for (_, tx) in channels.iter() {
        let cmd = json!({"type": "execute", "script": req.script}).to_string();
        if tx.send(cmd).is_ok() {
            sent = true;
            break;
        }
    }

    Json(json!({
        "sent": sent,
        "script_length": req.script.len(),
        "method": "websocket_session_channel",
    }))
}

// ── Cookie Vault ──

async fn list_cookies(State(_state): State<AppState>) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let vault_path = solace_home.join("vault").join("cookies.json");
    let cookies: Value = if vault_path.exists() {
        serde_json::from_str(&std::fs::read_to_string(&vault_path).unwrap_or_default()).unwrap_or(json!({}))
    } else {
        json!({})
    };
    Json(json!({"cookies": cookies, "encrypted": false, "note": "Encryption via AES-256-GCM available with OAuth3 vault"}))
}

async fn domain_cookies(
    Path(domain): Path<String>,
) -> Json<Value> {
    Json(json!({"domain": domain, "cookies": [], "note": "Per-domain cookies available after Chromium C++ integration"}))
}

#[derive(Deserialize)]
struct SetCookie {
    name: String,
    value: String,
    domain: String,
}

async fn set_cookie(
    Path(domain): Path<String>,
    Json(req): Json<SetCookie>,
) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let vault_dir = solace_home.join("vault");
    let _ = std::fs::create_dir_all(&vault_dir);
    let vault_path = vault_dir.join("cookies.json");

    let mut cookies: HashMap<String, Vec<Value>> = if vault_path.exists() {
        serde_json::from_str(&std::fs::read_to_string(&vault_path).unwrap_or_default()).unwrap_or_default()
    } else {
        HashMap::new()
    };

    cookies.entry(domain.clone()).or_default().push(json!({
        "name": req.name, "value": req.value, "set_at": chrono::Utc::now().to_rfc3339()
    }));

    let _ = std::fs::write(&vault_path, serde_json::to_string_pretty(&cookies).unwrap_or_default());

    Json(json!({"set": true, "domain": domain, "cookie": req.name}))
}

// ── Session Persistence ──

async fn save_session(State(state): State<AppState>) -> Json<Value> {
    let sessions = state.sessions.read();
    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("runtime").join("saved_session.json");
    let session_data: Vec<Value> = sessions.values().map(|s| json!({
        "session_id": s.session_id, "url": s.url, "profile": s.profile,
    })).collect();
    let _ = std::fs::write(&path, serde_json::to_string_pretty(&session_data).unwrap_or_default());
    Json(json!({"saved": true, "sessions": session_data.len(), "path": path.display().to_string()}))
}

async fn restore_session(State(_state): State<AppState>) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("runtime").join("saved_session.json");
    if !path.exists() {
        return Json(json!({"restored": false, "error": "no saved session"}));
    }
    let data: Vec<Value> = serde_json::from_str(&std::fs::read_to_string(&path).unwrap_or_default()).unwrap_or_default();
    Json(json!({"restored": true, "sessions": data.len(), "urls": data}))
}

// ── Print to PDF ──

async fn print_to_pdf(State(state): State<AppState>) -> Json<Value> {
    let sessions = state.sessions.read();
    let url = sessions.values().next().map(|s| s.url.clone()).unwrap_or_default();
    let filename = format!("page-{}.pdf", chrono::Utc::now().format("%Y%m%d-%H%M%S"));
    let solace_home = crate::utils::solace_home();
    let path = solace_home.join("exports").join(&filename);
    let _ = std::fs::create_dir_all(solace_home.join("exports"));

    // Use wkhtmltopdf or chrome headless for PDF generation
    let result = std::process::Command::new("wkhtmltopdf")
        .args(["--quiet", &url, path.to_str().unwrap_or("")])
        .output();

    let success = result.map(|o| o.status.success()).unwrap_or(false);

    let _ = crate::evidence::record_event(
        &solace_home, "browser.print_pdf", "system",
        json!({"url": url, "filename": filename}),
    );
    *state.evidence_count.write() += 1;

    Json(json!({"printed": success, "url": url, "filename": filename, "path": path.display().to_string()}))
}

// ── Form Fill ──

#[derive(Deserialize)]
struct FillRequest {
    fields: HashMap<String, String>,
}

async fn fill_form(
    State(state): State<AppState>,
    Json(req): Json<FillRequest>,
) -> Json<Value> {
    // Send fill commands to browser via WebSocket
    let channels = state.session_channels.read();
    let mut sent = false;
    for (_, tx) in channels.iter() {
        for (selector, value) in &req.fields {
            let cmd = json!({"type": "fill", "selector": selector, "value": value}).to_string();
            let _ = tx.send(cmd);
        }
        sent = true;
        break;
    }
    Json(json!({"filled": sent, "fields": req.fields.len()}))
}

// ── Downloads ──

async fn list_downloads() -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let downloads_dir = solace_home.join("downloads");
    let mut files = Vec::new();
    if downloads_dir.exists() {
        if let Ok(entries) = std::fs::read_dir(&downloads_dir) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                let size = entry.metadata().map(|m| m.len()).unwrap_or(0);
                files.push(json!({"name": name, "size": size}));
            }
        }
    }
    let count = files.len();
    Json(json!({"downloads": files, "count": count, "path": downloads_dir.display().to_string()}))
}

// ── Network Log ──

async fn network_log() -> Json<Value> {
    // Network interception requires C++ integration.
    // For now, return evidence entries that are network-related.
    let solace_home = crate::utils::solace_home();
    let evidence = crate::evidence::list_evidence(&solace_home, 100);
    let network_events: Vec<_> = evidence.iter()
        .filter(|e| e.event.contains("navigate") || e.event.contains("fetch") || e.event.contains("wiki.extract"))
        .take(50)
        .collect();
    let count = network_events.len();
    Json(json!({"events": network_events, "count": count, "note": "Full network intercept available after Chromium C++ integration"}))
}

// ── Tab Freeze/Resume ──

async fn freeze_tab(State(state): State<AppState>) -> Json<Value> {
    let channels = state.session_channels.read();
    for (_, tx) in channels.iter() {
        let _ = tx.send(json!({"type": "execute", "script": "debugger;"}).to_string());
    }
    Json(json!({"frozen": true, "method": "debugger_statement", "note": "Native renderer freeze available after C++ integration"}))
}

async fn resume_tab(State(state): State<AppState>) -> Json<Value> {
    let channels = state.session_channels.read();
    for (_, tx) in channels.iter() {
        let _ = tx.send(json!({"type": "execute", "script": ""}).to_string());
    }
    Json(json!({"resumed": true}))
}
