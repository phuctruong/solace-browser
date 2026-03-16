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
            if ws_tx
                .send(Message::Text(cmd.into()))
                .await
                .is_err()
            {
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
                        if let Some(url) = parsed.get("url").and_then(|v| v.as_str()) {
                            if !session_id.is_empty() {
                                let mut sessions = state.sessions.write();
                                if let Some(session) = sessions.values_mut().find(|s| s.session_id == session_id) {
                                    session.url = url.to_string();
                                }
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
                                if let Some(session) = sessions.values_mut().find(|s| s.session_id == session_id) {
                                    session.url = url.to_string();
                                }
                            }
                            let _ = title; // available for future use
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
