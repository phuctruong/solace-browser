// Diagram: 26-heartbeat-cloud-ping + hub-api-key-lifecycle
use std::time::Duration;

use serde_json::json;

use crate::state::AppState;

const CLOUD_BASE: &str = "https://solaceagi-mfjzxmegpq-uc.a.run.app";
const HEARTBEAT_INTERVAL_SECS: u64 = 300;
const OFFLINE_THRESHOLD_SECS: u64 = 600; // 10 minutes = offline

pub async fn run_heartbeat(state: AppState) {
    let mut consecutive_failures: u32 = 0;

    // On startup: validate API key if cloud_config exists (RECONNECT flow)
    {
        let config = state.cloud_config.read().clone();
        if let Some(ref config) = config {
            match validate_api_key(&config.api_key).await {
                Ok(true) => {
                    tracing::info!("cloud reconnect: API key valid, resuming heartbeat");
                    // Trigger pending evidence sync
                    let solace_home = crate::utils::solace_home();
                    let pending = crate::evidence::list_evidence(&solace_home, 100);
                    if !pending.is_empty() {
                        tracing::info!(
                            count = pending.len(),
                            "pending evidence to sync on reconnect"
                        );
                    }
                }
                Ok(false) => {
                    // On startup, don't clear config immediately — the bridge from
                    // solaceagi.com may re-send a fresh token. Only clear after
                    // multiple consecutive failures in the heartbeat loop.
                    tracing::warn!(
                        "cloud reconnect: API key validation failed — keeping config, will retry"
                    );
                    consecutive_failures += 1;
                }
                Err(error) => {
                    tracing::warn!(%error, "cloud reconnect: network error — staying offline");
                    // Stay offline, will retry on next heartbeat tick
                }
            }
        }
    }

    loop {
        tokio::time::sleep(Duration::from_secs(HEARTBEAT_INTERVAL_SECS)).await;
        let config = state.cloud_config.read().clone();
        if let Some(config) = config {
            if !config.paid_user {
                continue;
            }
            let result = reqwest::Client::new()
                .post(format!("{CLOUD_BASE}/api/v1/heartbeat"))
                .bearer_auth(&config.api_key)
                .json(&json!({
                    "device_id": config.device_id,
                    "user_email": config.user_email,
                    "uptime_seconds": state.uptime_seconds(),
                }))
                .timeout(Duration::from_secs(15))
                .send()
                .await;

            match result {
                Ok(response) => {
                    let status = response.status();
                    if status.is_success() {
                        consecutive_failures = 0;
                    } else if status.as_u16() == 401 {
                        // API key may be expired — don't clear immediately.
                        // The bridge from solaceagi.com will re-send a fresh token.
                        // Only clear after 3 consecutive 401s (15 min of failures).
                        consecutive_failures += 1;
                        tracing::warn!(
                            failures = consecutive_failures,
                            "heartbeat 401: token rejected — will clear after 3 consecutive failures"
                        );
                        if consecutive_failures >= 3 {
                            tracing::error!(
                                "heartbeat: 3 consecutive 401s — clearing cloud config"
                            );
                            *state.cloud_config.write() = None;
                            let solace_home = crate::utils::solace_home();
                            let _ = crate::config::clear_cloud_config(&solace_home);
                            state.notifications.write().push(crate::state::Notification {
                                id: uuid::Uuid::new_v4().to_string(),
                                message: "Cloud access expired after multiple failures. Sign in again at solaceagi.com"
                                    .to_string(),
                                level: "error".to_string(),
                                read: false,
                                created_at: crate::utils::now_iso8601(),
                            });
                        }
                    } else {
                        consecutive_failures += 1;
                        tracing::warn!(
                            status = %status,
                            failures = consecutive_failures,
                            "cloud heartbeat non-success"
                        );
                    }
                }
                Err(error) => {
                    consecutive_failures += 1;
                    tracing::warn!(
                        %error,
                        failures = consecutive_failures,
                        "cloud heartbeat failed"
                    );
                    // After OFFLINE_THRESHOLD (10min = 2 failures at 300s interval),
                    // mark as offline
                    if consecutive_failures * HEARTBEAT_INTERVAL_SECS as u32
                        >= OFFLINE_THRESHOLD_SECS as u32
                    {
                        tracing::warn!(
                            "device marked offline after {} consecutive failures",
                            consecutive_failures
                        );
                    }
                }
            }
        }
    }
}

/// Validate an API key against solaceagi.com.
/// Returns Ok(true) if valid, Ok(false) if expired/revoked, Err on network failure.
async fn validate_api_key(api_key: &str) -> Result<bool, String> {
    let response = reqwest::Client::new()
        .post(format!("{CLOUD_BASE}/api/v1/auth/verify"))
        .bearer_auth(api_key)
        .timeout(Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    Ok(response.status().is_success())
}
