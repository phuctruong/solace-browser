// Diagram: 05-solace-runtime-architecture
use std::net::SocketAddr;

use solace_runtime::{cloud, cron, mcp, persistence, server, updates, utils, AppState};
use tokio::signal;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    // Suppress Google API warning in child Chromium processes
    std::env::set_var("GOOGLE_API_KEY", "no");
    std::env::set_var("GOOGLE_DEFAULT_CLIENT_ID", "no");
    std::env::set_var("GOOGLE_DEFAULT_CLIENT_SECRET", "no");

    let state = AppState::new();
    if std::env::args().skip(1).any(|arg| arg == "--mcp") {
        tracing::info!("starting MCP stdio server");
        mcp::run_mcp_server(state).await;
        return;
    }
    let solace_home = utils::solace_home();

    let lock_port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8888);
    if let Err(error) = persistence::write_port_lock(&solace_home, lock_port, &state.token_hash) {
        tracing::error!(%error, "failed to write port.lock");
    }

    let cron_state = state.clone();
    tokio::spawn(async move { cron::run_scheduler(cron_state).await });

    let cloud_state = state.clone();
    tokio::spawn(async move { cloud::run_heartbeat(cloud_state).await });

    // Auto-update checker — checks GCS every hour, downloads + installs if newer
    let update_state = state.clone();
    updates::spawn_update_checker(update_state);

    // Runtime heartbeat — emit event every 60s so Events tab always has data
    let heartbeat_state = state.clone();
    tokio::spawn(async move { run_runtime_heartbeat(heartbeat_state).await });

    tracing::info!(
        tools = mcp::mcp_tool_definitions().len(),
        "mcp tool catalog loaded"
    );

    let app = server::build_router(state.clone());
    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8888);
    // Cloud Run: bind 0.0.0.0 (not 127.0.0.1) so health checks work
    let bind_addr =
        if std::env::var("SOLACE_CLOUD_TWIN").is_ok() || std::env::var("K_SERVICE").is_ok() {
            [0, 0, 0, 0]
        } else {
            [127, 0, 0, 1]
        };
    let addr = SocketAddr::from((bind_addr, port));
    tracing::info!(%addr, "Solace Runtime v0.1.0");

    let listener = match tokio::net::TcpListener::bind(addr).await {
        Ok(listener) => listener,
        Err(error) => {
            tracing::error!(%error, "bind failed");
            return;
        }
    };

    if let Err(error) = axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
    {
        tracing::error!(%error, "server error");
    }

    if let Err(error) = persistence::remove_port_lock(&solace_home) {
        tracing::error!(%error, "failed to remove port.lock");
    }
    tracing::info!("Solace Runtime stopped");
}

async fn run_runtime_heartbeat(state: AppState) {
    // Emit a startup event immediately
    {
        let mut events = state.runtime_events.write();
        events.push(serde_json::json!({
            "event_type": "HEARTBEAT",
            "timestamp": utils::now_iso8601(),
            "level": "L1",
            "domain": "system",
            "app_id": "solace-runtime",
            "message": "Solace Runtime started",
            "data": {
                "apps": *state.app_count.read(),
                "sessions": state.sessions.read().len(),
            }
        }));
    }

    let mut interval = tokio::time::interval(std::time::Duration::from_secs(60));
    loop {
        interval.tick().await;
        let sessions = state.sessions.read().len();
        let apps = *state.app_count.read();
        let uptime = state.uptime_seconds();
        let mut events = state.runtime_events.write();
        events.push(serde_json::json!({
            "event_type": "HEARTBEAT",
            "timestamp": utils::now_iso8601(),
            "level": "L1",
            "domain": "system",
            "app_id": "solace-runtime",
            "message": format!("uptime={}s sessions={} apps={}", uptime, sessions, apps),
            "data": {
                "uptime_seconds": uptime,
                "sessions": sessions,
                "apps": apps,
            }
        }));
        // Cap at 1000 events
        if events.len() > 1000 {
            let drain = events.len() - 1000;
            events.drain(..drain);
        }
    }
}

async fn shutdown_signal() {
    let _ = signal::ctrl_c().await;
}
