use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::IntoResponse,
    routing::get,
    Router,
};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/ws/dashboard", get(ws_dashboard))
        .route("/ws/yinyang", get(ws_yinyang))
}

async fn ws_dashboard(ws: WebSocketUpgrade, State(state): State<AppState>) -> impl IntoResponse {
    ws.on_upgrade(|socket| handle_dashboard_ws(socket, state))
}

async fn ws_yinyang(ws: WebSocketUpgrade, State(state): State<AppState>) -> impl IntoResponse {
    ws.on_upgrade(|socket| handle_yinyang_ws(socket, state))
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

async fn handle_yinyang_ws(mut socket: WebSocket, state: AppState) {
    let sidebar_state = crate::routes::sidebar::compute_sidebar_state(&state);
    let _ = socket
        .send(Message::Text(sidebar_state.to_string().into()))
        .await;

    while let Some(Ok(msg)) = socket.recv().await {
        if let Message::Text(text) = msg {
            let reply = json!({"type": "chat", "reply": text.to_string(), "source": "local"});
            if socket
                .send(Message::Text(reply.to_string().into()))
                .await
                .is_err()
            {
                break;
            }
        }
    }
}
