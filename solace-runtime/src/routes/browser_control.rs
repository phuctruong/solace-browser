// Diagram: hub-browser-control
use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/navigate", post(navigate))
        .route("/api/click", post(click))
        .route("/api/fill", post(fill))
        .route("/api/evaluate", post(evaluate))
        .route("/api/dom-snapshot", get(dom_snapshot))
        .route("/api/aria-snapshot", get(aria_snapshot))
        .route("/api/page-snapshot", get(page_snapshot))
}

// ── Request schemas ──────────────────────────────────────────────────

#[derive(Deserialize)]
struct NavigateRequest {
    url: String,
    wait_for: Option<String>,
}

#[derive(Deserialize)]
struct ClickRequest {
    selector: String,
}

#[derive(Deserialize)]
struct FillRequest {
    selector: String,
    value: String,
}

#[derive(Deserialize)]
struct EvaluateRequest {
    script: String,
}

// ── Helpers ──────────────────────────────────────────────────────────

/// Record a browser control evidence event and return the result.
fn record_browser_event(action: &str, data: Value) -> Result<Value, (StatusCode, Json<Value>)> {
    let solace_home = crate::utils::solace_home();
    crate::evidence::record_event(&solace_home, &format!("browser_control.{action}"), "runtime", data)
        .map(|record| json!({"evidence_id": record.id, "hash": record.hash}))
        .map_err(|error| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": format!("evidence recording failed: {error}")})),
            )
        })
}

/// Validate that a URL is non-empty and starts with http:// or https://.
fn validate_url(url: &str) -> Result<(), (StatusCode, Json<Value>)> {
    if url.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "url must not be empty"})),
        ));
    }
    if !url.starts_with("http://") && !url.starts_with("https://") {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "url must start with http:// or https://"})),
        ));
    }
    Ok(())
}

/// Validate that a CSS selector is non-empty.
fn validate_selector(selector: &str) -> Result<(), (StatusCode, Json<Value>)> {
    if selector.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "selector must not be empty"})),
        ));
    }
    Ok(())
}

// ── Handlers ─────────────────────────────────────────────────────────

/// POST /api/navigate — navigate to URL
///
/// Accepts `{ url, wait_for? }`. Records evidence and returns accepted status.
/// Actual navigation requires Chromium — this stub prepares the API contract.
async fn navigate(
    State(state): State<AppState>,
    Json(payload): Json<NavigateRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    validate_url(&payload.url)?;

    let evidence = record_browser_event(
        "navigate",
        json!({
            "url": payload.url,
            "wait_for": payload.wait_for,
        }),
    )?;

    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "status": "accepted",
        "action": "navigate",
        "url": payload.url,
        "wait_for": payload.wait_for,
        "evidence": evidence,
        "delegate_to_browser": true,
        "message": "Navigation request recorded. Actual navigation requires the browser process.",
    })))
}

/// POST /api/click — click element by CSS selector
///
/// Accepts `{ selector }`. Records evidence and returns accepted status.
async fn click(
    State(state): State<AppState>,
    Json(payload): Json<ClickRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    validate_selector(&payload.selector)?;

    let evidence = record_browser_event(
        "click",
        json!({ "selector": payload.selector }),
    )?;

    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "status": "accepted",
        "action": "click",
        "selector": payload.selector,
        "evidence": evidence,
        "delegate_to_browser": true,
        "message": "Click request recorded. Actual click requires the browser process.",
    })))
}

/// POST /api/fill — type into input field
///
/// Accepts `{ selector, value }`. Records evidence and returns accepted status.
async fn fill(
    State(state): State<AppState>,
    Json(payload): Json<FillRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    validate_selector(&payload.selector)?;

    if payload.value.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "value must not be empty"})),
        ));
    }

    let evidence = record_browser_event(
        "fill",
        json!({
            "selector": payload.selector,
            "value_length": payload.value.len(),
        }),
    )?;

    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "status": "accepted",
        "action": "fill",
        "selector": payload.selector,
        "value_length": payload.value.len(),
        "evidence": evidence,
        "delegate_to_browser": true,
        "message": "Fill request recorded. Actual fill requires the browser process.",
    })))
}

/// POST /api/evaluate — run JavaScript in page
///
/// Accepts `{ script }`. Records evidence and returns accepted status.
async fn evaluate(
    State(state): State<AppState>,
    Json(payload): Json<EvaluateRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    if payload.script.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "script must not be empty"})),
        ));
    }

    let evidence = record_browser_event(
        "evaluate",
        json!({
            "script_length": payload.script.len(),
            "script_preview": if payload.script.len() > 100 {
                format!("{}...", &payload.script[..100])
            } else {
                payload.script.clone()
            },
        }),
    )?;

    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "status": "accepted",
        "action": "evaluate",
        "script_length": payload.script.len(),
        "evidence": evidence,
        "delegate_to_browser": true,
        "message": "Evaluate request recorded. Actual JS execution requires the browser process.",
    })))
}

/// GET /api/dom-snapshot — get DOM tree
///
/// Returns delegation status. Actual DOM capture requires Chromium.
async fn dom_snapshot(
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let evidence = record_browser_event(
        "dom_snapshot",
        json!({"requested": true}),
    )?;

    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "status": "delegate_to_browser",
        "action": "dom_snapshot",
        "evidence": evidence,
        "message": "DOM snapshot requires the browser process. \
                    The browser should capture the DOM and POST it back.",
    })))
}

/// GET /api/aria-snapshot — get accessibility tree
///
/// Returns delegation status. Actual accessibility tree capture requires Chromium.
async fn aria_snapshot(
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let evidence = record_browser_event(
        "aria_snapshot",
        json!({"requested": true}),
    )?;

    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "status": "delegate_to_browser",
        "action": "aria_snapshot",
        "evidence": evidence,
        "message": "ARIA snapshot requires the browser process. \
                    The browser should capture the accessibility tree and POST it back.",
    })))
}

/// GET /api/page-snapshot — get Prime Wiki snapshot
///
/// Delegates to /api/v1/wiki/extract. The caller should use that endpoint
/// with the page content to produce a Stillwater + Ripple decomposition.
async fn page_snapshot() -> Json<Value> {
    Json(json!({
        "status": "delegate_to_browser",
        "action": "page_snapshot",
        "delegate_endpoint": "/api/v1/wiki/extract",
        "message": "Page snapshot delegates to /api/v1/wiki/extract. \
                    POST { url, content, content_type } to that endpoint with the page HTML.",
    }))
}
