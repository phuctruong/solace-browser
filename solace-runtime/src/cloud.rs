use std::time::Duration;

use serde_json::json;

use crate::state::AppState;

pub async fn run_heartbeat(state: AppState) {
    loop {
        tokio::time::sleep(Duration::from_secs(300)).await;
        let config = state.cloud_config.read().clone();
        if let Some(config) = config {
            if !config.paid_user {
                continue;
            }
            let request = reqwest::Client::new()
                .post("https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/heartbeat")
                .bearer_auth(&config.api_key)
                .json(&json!({
                    "device_id": config.device_id,
                    "user_email": config.user_email,
                    "uptime_seconds": state.uptime_seconds(),
                }))
                .send()
                .await;
            if let Err(error) = request {
                tracing::warn!(%error, "cloud heartbeat failed");
            }
        }
    }
}
