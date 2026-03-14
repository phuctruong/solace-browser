use std::net::SocketAddr;

use tokio::signal;

mod app_engine;
mod cloud;
mod config;
mod cron;
mod evidence;
mod mcp;
mod persistence;
mod pzip;
mod routes;
mod server;
mod state;
mod utils;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let state = state::AppState::new();
    let solace_home = utils::solace_home();

    if let Err(error) = persistence::write_port_lock(&solace_home, 8888, &state.token_hash) {
        tracing::error!(%error, "failed to write port.lock");
    }

    let cron_state = state.clone();
    tokio::spawn(async move { cron::run_scheduler(cron_state).await });

    let cloud_state = state.clone();
    tokio::spawn(async move { cloud::run_heartbeat(cloud_state).await });

    tracing::info!(
        tools = mcp::mcp_tool_definitions().len(),
        "mcp tool catalog loaded"
    );

    let app = server::build_router(state.clone());
    let addr = SocketAddr::from(([127, 0, 0, 1], 8888));
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

async fn shutdown_signal() {
    let _ = signal::ctrl_c().await;
}
