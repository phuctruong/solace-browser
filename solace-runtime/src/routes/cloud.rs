use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;

use crate::state::{AppState, CloudConfig, Notification};

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/cloud/status", get(cloud_status))
        .route("/api/v1/cloud/connect", post(connect_cloud))
        .route("/api/v1/cloud/disconnect", post(disconnect_cloud))
}

#[derive(Deserialize)]
struct ConnectPayload {
    api_key: String,
    user_email: String,
    device_id: String,
    paid_user: bool,
}

async fn cloud_status(State(state): State<AppState>) -> Json<serde_json::Value> {
    let config = state.cloud_config.read().clone();
    Json(json!({
        "connected": config.is_some(),
        "config": config.map(|config| json!({
            "user_email": config.user_email,
            "device_id": config.device_id,
            "paid_user": config.paid_user,
            "api_key_hint": mask_key(&config.api_key),
        })),
    }))
}

async fn connect_cloud(
    State(state): State<AppState>,
    Json(payload): Json<ConnectPayload>,
) -> Json<serde_json::Value> {
    let config = CloudConfig {
        api_key: payload.api_key,
        user_email: payload.user_email,
        device_id: payload.device_id,
        paid_user: payload.paid_user,
    };
    *state.cloud_config.write() = Some(config.clone());
    let solace_home = crate::utils::solace_home();
    let _ = crate::config::save_cloud_config(&solace_home, &config);
    state.notifications.write().push(Notification {
        id: uuid::Uuid::new_v4().to_string(),
        message: format!("Cloud connected for {}", config.user_email),
        level: "info".to_string(),
        read: false,
        created_at: crate::utils::now_iso8601(),
    });
    Json(json!({"connected": true, "paid_user": config.paid_user}))
}

async fn disconnect_cloud(State(state): State<AppState>) -> Json<serde_json::Value> {
    *state.cloud_config.write() = None;
    let solace_home = crate::utils::solace_home();
    let _ = crate::config::clear_cloud_config(&solace_home);
    Json(json!({"connected": false}))
}

fn mask_key(api_key: &str) -> String {
    if api_key.len() <= 8 {
        return "********".to_string();
    }
    format!("{}…{}", &api_key[..4], &api_key[api_key.len() - 4..])
}
