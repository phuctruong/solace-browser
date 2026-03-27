// Diagram: 09-yinyang-fsm
use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Query, State,
    },
    response::IntoResponse,
    routing::get,
    Router,
};
use futures_util::{SinkExt, StreamExt};
use serde::Deserialize;
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/ws/dashboard", get(ws_dashboard))
        .route("/ws/yinyang", get(ws_yinyang))
}

#[derive(Deserialize)]
struct YinyangParams {
    session: Option<String>,
}

async fn ws_dashboard(ws: WebSocketUpgrade, State(state): State<AppState>) -> impl IntoResponse {
    ws.on_upgrade(|socket| handle_dashboard_ws(socket, state))
}

async fn ws_yinyang(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    Query(params): Query<YinyangParams>,
) -> impl IntoResponse {
    let session_id = params.session.unwrap_or_default();
    ws.on_upgrade(move |socket| handle_yinyang_ws(socket, state, session_id))
}

async fn handle_dashboard_ws(mut socket: WebSocket, state: AppState) {
    loop {
        let status = json!({
            "uptime": state.uptime_seconds(),
            "sessions": state.sessions.read().len(),
            "apps": *state.app_count.read(),
            "evidence": *state.evidence_count.read(),
            "theme": state.theme.read().clone(),
        });
        if socket
            .send(Message::Text(status.to_string().into()))
            .await
            .is_err()
        {
            break;
        }
        tokio::time::sleep(std::time::Duration::from_secs(5)).await;
    }
}

/// Yinyang sidebar WebSocket — two-way control channel per browser session.
///
/// Browser → Runtime: url_changed, event, screenshot, status
/// Runtime → Browser: navigate, reload, focus, screenshot_request, execute
async fn handle_yinyang_ws(socket: WebSocket, state: AppState, session_id: String) {
    let (mut ws_tx, mut ws_rx) = socket.split();

    // Send initial sidebar state
    let sidebar_state = crate::routes::sidebar::compute_sidebar_state(&state);
    let _ = ws_tx
        .send(Message::Text(sidebar_state.to_string().into()))
        .await;

    // Register command channel for this session
    let (cmd_tx, mut cmd_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    if !session_id.is_empty() {
        state
            .session_channels
            .write()
            .insert(session_id.clone(), cmd_tx);
    }

    // Spawn task to forward commands from channel → WebSocket
    let tx_state = state.clone();
    let tx_session = session_id.clone();
    let send_task = tokio::spawn(async move {
        while let Some(cmd) = cmd_rx.recv().await {
            if ws_tx.send(Message::Text(cmd.into())).await.is_err() {
                break;
            }
        }
        // Cleanup on disconnect
        tx_state.session_channels.write().remove(&tx_session);
    });

    // Receive messages from browser sidebar
    while let Some(Ok(msg)) = ws_rx.next().await {
        if let Message::Text(text) = msg {
            let text_str = text.to_string();
            // Parse incoming message from sidebar
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&text_str) {
                let msg_type = parsed.get("type").and_then(|v| v.as_str()).unwrap_or("");
                match msg_type {
                    "url_changed" => {
                        // Browser navigated — update session's current URL
                        let nav_url = parsed
                            .get("url")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();
                        if !nav_url.is_empty() {
                            *state.current_url.write() = nav_url.clone();
                        }
                        if !nav_url.is_empty() && !session_id.is_empty() {
                            let mut sessions = state.sessions.write();
                            if let Some(session) =
                                sessions.values_mut().find(|s| s.session_id == session_id)
                            {
                                session.url = nav_url.clone();
                            }
                        }
                        // Auto-capture: if sidebar sent page content, store as live page HTML
                        // AND create Prime Wiki snapshot
                        if let Some(content) = parsed.get("content").and_then(|v| v.as_str()) {
                            let title = parsed.get("title").and_then(|v| v.as_str()).unwrap_or("");
                            let looks_like_sidebar_shell = title.contains("Yinyang AI Assistant")
                                || content.contains("id=\"yy-shell\"")
                                || content.contains("class=\"yy-status-pill\"")
                                || content.contains("yy-shell--working");
                            // Store live page HTML in state (GET /api/v1/browser/page-html reads this)
                            if !nav_url.is_empty() && content.len() > 100 && !looks_like_sidebar_shell {
                                let mut page = state.page_html.write();
                                page.html = content.to_string();
                                page.url = nav_url.clone();
                                page.title = title.to_string();
                                page.captured_at = crate::utils::now_iso8601();
                            }
                            // Also send to wiki/extract for Stillwater compression + Prime Wiki snapshot
                            if !nav_url.is_empty() && content.len() > 100 && !looks_like_sidebar_shell {
                                let wiki_url = nav_url.clone();
                                let wiki_content = content.to_string();
                                let _handle = tokio::spawn(async move {
                                    let client = reqwest::Client::new();
                                    let _ = client.post("http://127.0.0.1:8888/api/v1/wiki/extract")
                                        .json(&serde_json::json!({"url": wiki_url, "content": wiki_content}))
                                        .send().await;
                                });
                            }
                        }
                    }
                    "status" => {
                        // Browser reporting its status (title, url, etc.)
                        if let (Some(url), Some(title)) = (
                            parsed.get("url").and_then(|v| v.as_str()),
                            parsed.get("title").and_then(|v| v.as_str()),
                        ) {
                            if !session_id.is_empty() {
                                let mut sessions = state.sessions.write();
                                if let Some(session) =
                                    sessions.values_mut().find(|s| s.session_id == session_id)
                                {
                                    session.url = url.to_string();
                                }
                            }
                            let _ = title; // available for future use
                        }
                    }
                    "navigate_request" => {
                        // Sidebar requests navigation — send via session channel if available
                        if let Some(url) = parsed.get("url").and_then(|v| v.as_str()) {
                            let channels = state.session_channels.read();
                            for (_, tx) in channels.iter() {
                                let cmd =
                                    serde_json::json!({"type": "navigate", "url": url}).to_string();
                                let _ = tx.send(cmd);
                            }
                        }
                    }
                    "tab_info" | "tabs_list" => {
                        // Sidebar reports tab list — store in state for GET /api/v1/browser/tabs
                        if let Some(tabs) = parsed.get("tabs").and_then(|v| v.as_array()) {
                            *state.browser_tabs.write() = tabs.clone();
                            tracing::debug!(tab_count = tabs.len(), "tabs updated");
                        }
                    }
                    "auth_handshake" => {
                        // Browser sidebar detected login on solaceagi.com/dashboard
                        // Payload: { type: "auth_handshake", token: "firebase_id_token", email: "user@example.com" }
                        if let (Some(token), Some(email)) = (
                            parsed.get("token").and_then(|v| v.as_str()),
                            parsed.get("email").and_then(|v| v.as_str()),
                        ) {
                            let handshake_state = state.clone();
                            let handshake_token = token.to_string();
                            let handshake_email = email.to_string();
                            tokio::spawn(async move {
                                handle_auth_handshake(
                                    &handshake_state,
                                    &handshake_token,
                                    &handshake_email,
                                )
                                .await;
                            });
                        }
                    }
                    _ => {
                        // Default: echo as chat reply
                    }
                }
            }
        }
    }

    // Browser disconnected — cleanup
    send_task.abort();
    state.session_channels.write().remove(&session_id);
}

/// Handle auth handshake from browser sidebar after user logs into solaceagi.com/dashboard.
///
/// Flow:
/// 1. Sidebar detects URL = solaceagi.com/dashboard + user is logged in
/// 2. Sidebar sends { type: "auth_handshake", token: "...", email: "..." } via WebSocket
/// 3. Runtime calls solaceagi.com to get/create API key for this device
/// 4. Stores cloud config locally (activates sidebar + apps)
/// 5. Downloads default apps if missing
async fn handle_auth_handshake(state: &AppState, token: &str, email: &str) {
    let solace_home = crate::utils::solace_home();

    // Skip if already connected
    if state.cloud_config.read().is_some() {
        return;
    }

    // Call solaceagi.com to verify token and get API key
    let client = reqwest::Client::new();
    let verify_url = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/auth/verify";
    let verify_result = client
        .get(verify_url)
        .bearer_auth(token)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await;

    let api_key = match verify_result {
        Ok(resp) if resp.status().is_success() => {
            match resp.json::<serde_json::Value>().await {
                Ok(body) => {
                    // Try to get existing API key or use the token
                    body.get("api_key")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string())
                        .unwrap_or_else(|| format!("firebase_{}", &token[..20.min(token.len())]))
                }
                Err(_) => return,
            }
        }
        _ => return,
    };

    // Generate stable device ID from email + machine ID
    let machine_id = std::fs::read_to_string("/etc/machine-id")
        .unwrap_or_else(|_| uuid::Uuid::new_v4().to_string());
    let device_id = format!(
        "hub-{}",
        &crate::utils::sha256_hex(&format!("{}:{}", email, machine_id.trim()))[..12]
    );

    // Store cloud config
    let config = crate::state::CloudConfig {
        api_key: api_key.clone(),
        user_email: email.to_string(),
        device_id: device_id.clone(),
        paid_user: false, // Updated later from account info
    };
    *state.cloud_config.write() = Some(config.clone());
    let _ = crate::config::save_cloud_config(&solace_home, &config);

    // Record evidence
    let _ = crate::evidence::record_event(
        &solace_home,
        "auth.handshake_complete",
        "sidebar",
        serde_json::json!({
            "email": email,
            "device_id": device_id,
        }),
    );

    // Push notification
    state
        .notifications
        .write()
        .push(crate::state::Notification {
            id: uuid::Uuid::new_v4().to_string(),
            message: format!("Connected as {}", email),
            level: "info".to_string(),
            read: false,
            created_at: crate::utils::now_iso8601(),
        });

    // Download default apps from solaceagi.com if missing
    let app_count = crate::utils::scan_apps().len();
    if app_count < 5 {
        let download_url = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/appstore/bundle";
        if let Ok(resp) = client
            .get(download_url)
            .bearer_auth(&api_key)
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await
        {
            if resp.status().is_success() {
                if let Ok(body) = resp.json::<serde_json::Value>().await {
                    if let Some(apps) = body.get("apps").and_then(|v| v.as_array()) {
                        for app in apps {
                            if let Some(app_id) = app.get("id").and_then(|v| v.as_str()) {
                                let app_dir = solace_home.join("apps").join(app_id);
                                if !app_dir.exists() {
                                    let _ = std::fs::create_dir_all(&app_dir);
                                    // Write manifest
                                    if let Ok(manifest_str) = serde_json::to_string_pretty(app) {
                                        let _ = std::fs::write(
                                            app_dir.join("manifest.json"),
                                            manifest_str,
                                        );
                                    }
                                }
                            }
                        }
                        // Update app count
                        *state.app_count.write() = crate::utils::scan_apps().len() as u32;
                    }
                }
            }
        }
    }
}
