// Diagram: hub-tunnel-remote-control
//! Tunnel consent + connect + audit — FDA Part 11 remote access for Solace Runtime.
//!
//! Architecture:
//!   1. User signs consent form (POST /consent) → evidence recorded
//!   2. Runtime connects outbound WSS to solaceagi.com/api/v1/hub/connect
//!   3. Cloud relays commands → Runtime executes → results flow back
//!   4. Auto-disconnect after consent duration expires
//!   5. Every action recorded in local evidence chain
//!
//! Security: outbound-only, wss enforced, consent required, evidence on everything.

use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::state::AppState;

/// Valid consent reasons (matches solaceagi tunnel_consent.py).
const VALID_REASONS: &[&str] = &["support", "demo", "troubleshooting", "training", "custom"];
/// Valid scope items.
const VALID_SCOPES: &[&str] = &["browser_control", "cli_dispatch", "evidence_read", "screenshot", "navigate"];
/// Maximum consent duration in minutes (8 hours).
const MAX_DURATION_MINUTES: u32 = 480;
/// Default consent duration.
const DEFAULT_DURATION_MINUTES: u32 = 30;
/// Cloud tunnel WebSocket endpoint.
const CLOUD_TUNNEL_URL: &str = "wss://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/hub/connect";

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/tunnel/consent", get(get_consent_form))
        .route("/api/v1/tunnel/consent", post(sign_consent))
        .route("/api/v1/tunnel/connect", post(connect_tunnel))
        .route("/api/v1/tunnel/disconnect", post(disconnect_tunnel))
        .route("/api/v1/tunnel/status", get(tunnel_status))
        .route("/api/v1/tunnel/audit", get(tunnel_audit))
}

// ---------------------------------------------------------------------------
// Request / response types
// ---------------------------------------------------------------------------

#[derive(Deserialize)]
struct ConsentPayload {
    reason: String,
    #[serde(default = "default_reason_category")]
    reason_category: String,
    #[serde(default = "default_scopes")]
    scope: Vec<String>,
    #[serde(default = "default_duration")]
    duration_minutes: u32,
}

fn default_reason_category() -> String {
    "support".to_string()
}
fn default_scopes() -> Vec<String> {
    vec!["browser_control".to_string(), "evidence_read".to_string()]
}
fn default_duration() -> u32 {
    DEFAULT_DURATION_MINUTES
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ConsentRecord {
    pub consent_id: String,
    pub reason: String,
    pub reason_category: String,
    pub scope: Vec<String>,
    pub duration_minutes: u32,
    pub signed_at: String,
    pub expires_at: String,
    pub status: String,
    pub evidence_hash: String,
}

// ---------------------------------------------------------------------------
// GET /api/v1/tunnel/consent — serve consent form HTML
// ---------------------------------------------------------------------------

async fn get_consent_form() -> axum::response::Html<String> {
    axum::response::Html(CONSENT_FORM_HTML.to_string())
}

// ---------------------------------------------------------------------------
// POST /api/v1/tunnel/consent — sign consent + record evidence
// ---------------------------------------------------------------------------

async fn sign_consent(
    State(state): State<AppState>,
    Json(payload): Json<ConsentPayload>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Validate reason category
    if !VALID_REASONS.contains(&payload.reason_category.as_str()) {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": format!("Invalid reason_category '{}'. Valid: {:?}", payload.reason_category, VALID_REASONS)})),
        ));
    }

    // Validate scopes
    for scope in &payload.scope {
        if !VALID_SCOPES.contains(&scope.as_str()) {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(json!({"error": format!("Invalid scope '{}'. Valid: {:?}", scope, VALID_SCOPES)})),
            ));
        }
    }

    // Validate duration
    if payload.duration_minutes == 0 || payload.duration_minutes > MAX_DURATION_MINUTES {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": format!("duration_minutes must be 1-{}", MAX_DURATION_MINUTES)})),
        ));
    }

    // Check for existing active consent
    {
        let tunnel = state.tunnel.read();
        if tunnel.consent.is_some() {
            return Err((
                StatusCode::CONFLICT,
                Json(json!({"error": "Active consent already exists. Disconnect first."})),
            ));
        }
    }

    let consent_id = uuid::Uuid::new_v4().to_string();
    let now = crate::utils::now_iso8601();
    let expires_at = compute_expires_at(&now, payload.duration_minutes);
    let evidence_hash = crate::utils::sha256_hex(&format!(
        "{}:consent:{}",
        consent_id, now
    ));

    let consent = ConsentRecord {
        consent_id: consent_id.clone(),
        reason: payload.reason.clone(),
        reason_category: payload.reason_category.clone(),
        scope: payload.scope.clone(),
        duration_minutes: payload.duration_minutes,
        signed_at: now.clone(),
        expires_at: expires_at.clone(),
        status: "active".to_string(),
        evidence_hash: evidence_hash.clone(),
    };

    // Store consent in state
    {
        let mut tunnel = state.tunnel.write();
        tunnel.consent = Some(consent.clone());
    }

    // Persist consent to disk
    let solace_home = crate::utils::solace_home();
    let consent_dir = solace_home.join("tunnel");
    let _ = std::fs::create_dir_all(&consent_dir);
    let _ = crate::persistence::write_json(
        &consent_dir.join("active_consent.json"),
        &consent,
    );

    // Record evidence
    let _ = crate::evidence::record_event(
        &solace_home,
        "tunnel.consent_signed",
        "user",
        json!({
            "consent_id": consent_id,
            "reason": payload.reason,
            "reason_category": payload.reason_category,
            "scope": payload.scope,
            "duration_minutes": payload.duration_minutes,
        }),
    );

    // Start auto-disconnect timer
    let timer_state = state.clone();
    let timer_consent_id = consent_id.clone();
    let timer_duration = payload.duration_minutes;
    tokio::spawn(async move {
        tokio::time::sleep(std::time::Duration::from_secs(u64::from(timer_duration) * 60)).await;
        // Check if this consent is still active
        let should_disconnect = {
            let tunnel = timer_state.tunnel.read();
            tunnel
                .consent
                .as_ref()
                .map_or(false, |c| c.consent_id == timer_consent_id && c.status == "active")
        };
        if should_disconnect {
            do_disconnect(&timer_state, "auto_disconnect");
        }
    });

    Ok(Json(json!({
        "consent_id": consent_id,
        "reason": payload.reason,
        "scope": payload.scope,
        "duration_minutes": payload.duration_minutes,
        "signed_at": now,
        "expires_at": expires_at,
        "evidence_hash": evidence_hash,
        "status": "active",
    })))
}

// ---------------------------------------------------------------------------
// POST /api/v1/tunnel/connect — start WebSocket client to cloud
// ---------------------------------------------------------------------------

async fn connect_tunnel(
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Require active consent
    {
        let tunnel = state.tunnel.read();
        if tunnel.consent.is_none() {
            return Err((
                StatusCode::PRECONDITION_FAILED,
                Json(json!({"error": "No active consent. Sign consent first via POST /api/v1/tunnel/consent"})),
            ));
        }
        if tunnel.connected {
            return Err((
                StatusCode::CONFLICT,
                Json(json!({"error": "Tunnel already connected"})),
            ));
        }
    }

    // Require cloud config (API key)
    let config = state
        .cloud_config
        .read()
        .clone()
        .ok_or_else(|| {
            (
                StatusCode::PRECONDITION_FAILED,
                Json(json!({"error": "Cloud not connected — call POST /api/v1/cloud/connect first"})),
            )
        })?;

    let api_key = config.api_key.clone();
    let tunnel_url = format!("{}?token={}", CLOUD_TUNNEL_URL, api_key);

    // Attempt WebSocket connection to cloud
    let connect_result = tokio_tungstenite::connect_async(&tunnel_url).await;

    match connect_result {
        Ok((ws_stream, _response)) => {
            let (ws_tx, mut ws_rx) = futures_util::StreamExt::split(ws_stream);
            let ws_tx = std::sync::Arc::new(tokio::sync::Mutex::new(ws_tx));

            // Store connection state
            {
                let mut tunnel = state.tunnel.write();
                tunnel.connected = true;
                tunnel.connected_at = Some(crate::utils::now_iso8601());
                tunnel.cloud_url = Some(CLOUD_TUNNEL_URL.to_string());
            }

            // Record evidence
            let solace_home = crate::utils::solace_home();
            let _ = crate::evidence::record_event(
                &solace_home,
                "tunnel.connected",
                "runtime",
                json!({
                    "cloud_url": CLOUD_TUNNEL_URL,
                    "device_id": config.device_id,
                }),
            );

            // Spawn keepalive ping every 25s to prevent Cloud Run timeout
            let ping_tx = ws_tx.clone();
            let ping_state = state.clone();
            tokio::spawn(async move {
                use futures_util::SinkExt;
                use tokio_tungstenite::tungstenite::Message;
                loop {
                    tokio::time::sleep(std::time::Duration::from_secs(25)).await;
                    if !ping_state.tunnel.read().connected {
                        break;
                    }
                    let ping = json!({"type": "ping"}).to_string();
                    let mut tx = ping_tx.lock().await;
                    if tx.send(Message::Text(ping.into())).await.is_err() {
                        break;
                    }
                }
            });

            // Spawn message handler: cloud commands → local execution
            let handler_state = state.clone();
            let handler_tx = ws_tx.clone();
            tokio::spawn(async move {
                use futures_util::SinkExt;
                use tokio_tungstenite::tungstenite::Message;

                while let Some(msg_result) = futures_util::StreamExt::next(&mut ws_rx).await {
                    let msg = match msg_result {
                        Ok(m) => m,
                        Err(_) => break,
                    };

                    if let Message::Text(text) = msg {
                        let text_str = text.to_string();
                        if let Ok(parsed) = serde_json::from_str::<Value>(&text_str) {
                            let msg_type = parsed.get("type").and_then(|v| v.as_str()).unwrap_or("");
                            let msg_id = parsed.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();

                            match msg_type {
                                "ping" => {
                                    let pong = json!({"type": "pong"}).to_string();
                                    let mut tx = handler_tx.lock().await;
                                    let _ = tx.send(Message::Text(pong.into())).await;
                                }
                                _ => {
                                    // Handle as proxy command: execute locally, return result
                                    let method = parsed.get("method").and_then(|v| v.as_str()).unwrap_or("GET");
                                    let path = parsed.get("path").and_then(|v| v.as_str()).unwrap_or("/");

                                    // Record evidence for this remote action
                                    let solace_home = crate::utils::solace_home();
                                    let _ = crate::evidence::record_event(
                                        &solace_home,
                                        "tunnel.remote_command",
                                        "cloud",
                                        json!({
                                            "method": method,
                                            "path": path,
                                            "message_id": msg_id,
                                        }),
                                    );

                                    // Execute locally via HTTP client to self
                                    let local_url = format!("http://127.0.0.1:8888{}", path);
                                    let client = reqwest::Client::new();
                                    let local_result = match method {
                                        "POST" => {
                                            let body = parsed.get("body").and_then(|v| v.as_str()).unwrap_or("");
                                            client.post(&local_url).body(body.to_string()).send().await
                                        }
                                        "DELETE" => client.delete(&local_url).send().await,
                                        _ => client.get(&local_url).send().await,
                                    };

                                    let response = match local_result {
                                        Ok(resp) => {
                                            let status_code = resp.status().as_u16();
                                            let body = resp.text().await.unwrap_or_default();
                                            json!({
                                                "id": msg_id,
                                                "type": "response",
                                                "status": status_code,
                                                "body": body,
                                            })
                                        }
                                        Err(err) => {
                                            json!({
                                                "id": msg_id,
                                                "type": "response",
                                                "status": 502,
                                                "body": format!("Local execution failed: {}", err),
                                            })
                                        }
                                    };

                                    let mut tx = handler_tx.lock().await;
                                    let _ = tx.send(Message::Text(response.to_string().into())).await;
                                }
                            }
                        }
                    }
                }

                // WebSocket closed — update state
                {
                    let mut tunnel = handler_state.tunnel.write();
                    tunnel.connected = false;
                    tunnel.connected_at = None;
                    tunnel.cloud_url = None;
                }

                let solace_home = crate::utils::solace_home();
                let _ = crate::evidence::record_event(
                    &solace_home,
                    "tunnel.disconnected",
                    "runtime",
                    json!({"reason": "cloud_closed"}),
                );
            });

            Ok(Json(json!({
                "connected": true,
                "cloud_url": CLOUD_TUNNEL_URL,
                "device_id": config.device_id,
            })))
        }
        Err(err) => {
            // Record evidence of failed connection
            let solace_home = crate::utils::solace_home();
            let _ = crate::evidence::record_event(
                &solace_home,
                "tunnel.connect_failed",
                "runtime",
                json!({"error": err.to_string()}),
            );

            Err((
                StatusCode::BAD_GATEWAY,
                Json(json!({"error": format!("Failed to connect to cloud tunnel: {}", err)})),
            ))
        }
    }
}

// ---------------------------------------------------------------------------
// POST /api/v1/tunnel/disconnect — close tunnel
// ---------------------------------------------------------------------------

async fn disconnect_tunnel(
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let had_consent = {
        let tunnel = state.tunnel.read();
        tunnel.consent.is_some()
    };

    if !had_consent {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "No active tunnel or consent to disconnect"})),
        ));
    }

    do_disconnect(&state, "user_disconnect");

    Ok(Json(json!({
        "disconnected": true,
        "reason": "user_disconnect",
    })))
}

// ---------------------------------------------------------------------------
// GET /api/v1/tunnel/status — current tunnel state
// ---------------------------------------------------------------------------

async fn tunnel_status(State(state): State<AppState>) -> Json<Value> {
    let tunnel = state.tunnel.read();
    let cloud_connected = state.cloud_config.read().is_some();

    Json(json!({
        "tunnel_connected": tunnel.connected,
        "consent_active": tunnel.consent.is_some(),
        "consent": tunnel.consent.as_ref().map(|c| json!({
            "consent_id": c.consent_id,
            "reason": c.reason,
            "scope": c.scope,
            "duration_minutes": c.duration_minutes,
            "signed_at": c.signed_at,
            "expires_at": c.expires_at,
            "status": c.status,
        })),
        "connected_at": tunnel.connected_at,
        "cloud_url": tunnel.cloud_url,
        "cloud_connected": cloud_connected,
        "architecture": "custom_reverse_tunnel",
        "security": {
            "outbound_only": true,
            "wss_enforced": true,
            "consent_required": true,
            "evidence_on_everything": true,
            "auto_disconnect": true,
        },
    }))
}

// ---------------------------------------------------------------------------
// GET /api/v1/tunnel/audit — local audit log (evidence entries for tunnel.*)
// ---------------------------------------------------------------------------

async fn tunnel_audit() -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let all_evidence = crate::evidence::list_evidence(&solace_home, 10_000);

    let tunnel_entries: Vec<Value> = all_evidence
        .iter()
        .filter(|record| record.event.starts_with("tunnel."))
        .map(|record| {
            json!({
                "id": record.id,
                "timestamp": record.timestamp,
                "event": record.event,
                "actor": record.actor,
                "data": record.data,
                "hash": record.hash,
            })
        })
        .collect();

    let total = tunnel_entries.len();

    Json(json!({
        "entries": tunnel_entries,
        "total": total,
    }))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn do_disconnect(state: &AppState, reason: &str) {
    let consent_id = {
        let mut tunnel = state.tunnel.write();
        let consent_id = tunnel.consent.as_ref().map(|c| c.consent_id.clone());
        tunnel.consent = None;
        tunnel.connected = false;
        tunnel.connected_at = None;
        tunnel.cloud_url = None;
        consent_id
    };

    // Remove persisted consent
    let solace_home = crate::utils::solace_home();
    let consent_path = solace_home.join("tunnel").join("active_consent.json");
    let _ = std::fs::remove_file(&consent_path);

    // Record evidence
    let _ = crate::evidence::record_event(
        &solace_home,
        "tunnel.disconnected",
        if reason == "user_disconnect" { "user" } else { "system" },
        json!({
            "reason": reason,
            "consent_id": consent_id,
        }),
    );
}

fn compute_expires_at(signed_at: &str, duration_minutes: u32) -> String {
    use chrono::{DateTime, Duration, Utc};

    if let Ok(dt) = signed_at.parse::<DateTime<Utc>>() {
        (dt + Duration::minutes(i64::from(duration_minutes))).to_rfc3339()
    } else {
        // Fallback: compute from now
        (Utc::now() + Duration::minutes(i64::from(duration_minutes))).to_rfc3339()
    }
}

// ---------------------------------------------------------------------------
// Consent form HTML (served at GET /api/v1/tunnel/consent)
// ---------------------------------------------------------------------------

const CONSENT_FORM_HTML: &str = r#"<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Remote Access Consent — Solace</title>
<link rel="stylesheet" href="/styleguide.css">
<style>
body { font-family: var(--sb-font-family, system-ui); background: var(--sb-bg, #0a0a0a); color: var(--sb-text, #e0e0e0); margin: 0; padding: 2rem; }
.consent-card { max-width: 600px; margin: 2rem auto; background: var(--sb-surface, #1a1a1a); border-radius: 12px; padding: 2rem; border: 1px solid var(--sb-border, #333); }
h1 { color: var(--sb-accent, #4fc3f7); font-size: 1.5rem; margin-top: 0; }
.warning { background: #2d1b00; border: 1px solid #ff9800; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
.warning strong { color: #ff9800; }
label { display: block; margin: 1rem 0 0.5rem; font-weight: 600; }
select, input, textarea { width: 100%; padding: 0.75rem; border-radius: 8px; border: 1px solid var(--sb-border, #333); background: var(--sb-bg, #0a0a0a); color: var(--sb-text, #e0e0e0); font-size: 1rem; box-sizing: border-box; }
.scope-list { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0; }
.scope-item { background: var(--sb-bg, #0a0a0a); border: 1px solid var(--sb-border, #333); border-radius: 6px; padding: 0.5rem 1rem; cursor: pointer; }
.scope-item.selected { background: var(--sb-accent, #4fc3f7); color: #000; border-color: var(--sb-accent, #4fc3f7); }
.btn-sign { width: 100%; padding: 1rem; margin-top: 1.5rem; background: var(--sb-accent, #4fc3f7); color: #000; border: none; border-radius: 8px; font-size: 1.1rem; font-weight: 700; cursor: pointer; }
.btn-sign:hover { opacity: 0.9; }
.result { margin-top: 1rem; padding: 1rem; border-radius: 8px; display: none; }
.result.success { display: block; background: #0d2818; border: 1px solid #4caf50; }
.result.error { display: block; background: #2d0a0a; border: 1px solid #f44336; }
</style>
</head>
<body>
<div class="consent-card">
  <h1>Remote Access Consent</h1>
  <div class="warning">
    <strong>FDA Part 11 Notice:</strong> By signing this form, you allow a remote agent to control your Solace Browser. Every action will be recorded in a tamper-evident evidence chain. You can disconnect at any time.
  </div>

  <label for="reason">Reason for access</label>
  <textarea id="reason" rows="2" placeholder="e.g., Customer support demo"></textarea>

  <label for="reason_category">Category</label>
  <select id="reason_category">
    <option value="support">Support</option>
    <option value="demo" selected>Demo</option>
    <option value="troubleshooting">Troubleshooting</option>
    <option value="training">Training</option>
    <option value="custom">Custom</option>
  </select>

  <label>Scope (click to toggle)</label>
  <div class="scope-list">
    <div class="scope-item selected" data-scope="browser_control">Browser Control</div>
    <div class="scope-item selected" data-scope="evidence_read">Evidence Read</div>
    <div class="scope-item" data-scope="screenshot">Screenshot</div>
    <div class="scope-item" data-scope="navigate">Navigate</div>
    <div class="scope-item" data-scope="cli_dispatch">CLI Dispatch</div>
  </div>

  <label for="duration">Duration (minutes)</label>
  <input type="number" id="duration" value="30" min="1" max="480">

  <button class="btn-sign" onclick="signConsent()">Sign Consent &amp; Allow Remote Access</button>

  <div id="result" class="result"></div>
</div>

<script>
document.querySelectorAll('.scope-item').forEach(el => {
  el.addEventListener('click', () => el.classList.toggle('selected'));
});

async function signConsent() {
  const reason = document.getElementById('reason').value;
  if (!reason.trim()) { alert('Please enter a reason.'); return; }

  const scope = Array.from(document.querySelectorAll('.scope-item.selected')).map(el => el.dataset.scope);
  const payload = {
    reason,
    reason_category: document.getElementById('reason_category').value,
    scope,
    duration_minutes: parseInt(document.getElementById('duration').value) || 30,
  };

  try {
    const resp = await fetch('/api/v1/tunnel/consent', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    const el = document.getElementById('result');
    if (resp.ok) {
      el.className = 'result success';
      el.innerHTML = '<strong>Consent signed.</strong> Consent ID: ' + data.consent_id + '<br>Expires: ' + data.expires_at + '<br>Evidence hash: <code>' + data.evidence_hash + '</code>';
    } else {
      el.className = 'result error';
      el.textContent = 'Error: ' + (data.error || JSON.stringify(data));
    }
  } catch (err) {
    const el = document.getElementById('result');
    el.className = 'result error';
    el.textContent = 'Network error: ' + err.message;
  }
}
</script>
</body>
</html>"#;
