// Diagram: 21-twin-sync-flow + 26-heartbeat-cloud-ping
use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::state::{AppState, CloudConfig, Notification};

const CLOUD_BASE_URL: &str = "https://solaceagi-mfjzxmegpq-uc.a.run.app";

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/cloud/status", get(cloud_status))
        .route("/api/v1/cloud/connect", post(connect_cloud))
        .route("/api/v1/cloud/disconnect", post(disconnect_cloud))
        .route("/api/v1/cloud/sync/up", post(sync_up))
        .route("/api/v1/cloud/sync/down", post(sync_down))
        .route("/api/v1/cloud/sync/status", get(sync_status))
}

// ---------------------------------------------------------------------------
// Existing cloud connect/disconnect/status
// ---------------------------------------------------------------------------

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
    format!("{}...{}", &api_key[..4], &api_key[api_key.len() - 4..])
}

// ---------------------------------------------------------------------------
// Twin sync: encrypted tunnel between local runtime and solaceagi.com cloud
// ---------------------------------------------------------------------------

/// Persisted sync receipt stored at ~/.solace/sync/last_sync.json
#[derive(Clone, Debug, Serialize, Deserialize)]
struct SyncReceipt {
    sync_id: String,
    direction: String,
    timestamp: String,
    device_id: String,
    evidence_count: usize,
    app_count: usize,
    conflict_count: u64,
    cloud_response_hash: String,
    success: bool,
}

/// The cleartext payload that gets encrypted before transmission.
#[derive(Serialize, Deserialize)]
struct SyncPayload {
    device_id: String,
    user_email: String,
    timestamp: String,
    evidence_entries: Vec<Value>,
    installed_apps: Vec<AppSummary>,
    payload_version: u32,
}

/// Minimal app summary sent during sync (not the full manifest).
#[derive(Clone, Serialize, Deserialize)]
struct AppSummary {
    id: String,
    name: String,
    version: String,
    domain: String,
}

/// POST /api/v1/cloud/sync/up
///
/// Collects local evidence + installed apps, encrypts with AES-256-GCM using
/// the vault key derived from the cloud API key, and POSTs the ciphertext to
/// the solaceagi.com twin sync endpoint. Stores a sync receipt locally.
async fn sync_up(State(state): State<AppState>) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = require_cloud_config(&state)?;
    let solace_home = crate::utils::solace_home();

    // 1. Collect evidence entries
    let evidence_entries = crate::evidence::list_evidence(&solace_home, 10_000);
    let evidence_values: Vec<Value> = evidence_entries
        .iter()
        .map(|record| serde_json::to_value(record).unwrap_or(json!({})))
        .collect();

    // 2. Collect installed apps
    let apps = crate::utils::scan_apps();
    let app_summaries: Vec<AppSummary> = apps
        .iter()
        .map(|manifest| AppSummary {
            id: manifest.id.clone(),
            name: manifest.name.clone(),
            version: manifest.version.clone(),
            domain: manifest.domain.clone(),
        })
        .collect();

    // 3. Build cleartext payload
    let payload = SyncPayload {
        device_id: config.device_id.clone(),
        user_email: config.user_email.clone(),
        timestamp: crate::utils::now_iso8601(),
        evidence_entries: evidence_values.clone(),
        installed_apps: app_summaries.clone(),
        payload_version: 1,
    };

    let plaintext = serde_json::to_vec(&payload)
        .map_err(|error| sync_error(format!("payload serialization failed: {error}")))?;

    // 4. Encrypt with AES-256-GCM
    let key = crate::crypto::derive_key(&config.api_key, b"solace-twin-sync:v1");
    let ciphertext = crate::crypto::encrypt(&plaintext, &key)
        .map_err(|error| sync_error(format!("encryption failed: {error}")))?;

    let encoded = base64::encode_block(&ciphertext);

    // 5. POST to cloud
    let sync_url = format!("{CLOUD_BASE_URL}/api/v1/twin/sync");
    let cloud_response = reqwest::Client::new()
        .post(&sync_url)
        .bearer_auth(&config.api_key)
        .json(&json!({
            "device_id": config.device_id,
            "encrypted_payload": encoded,
        }))
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await;

    let (success, cloud_hash) = match cloud_response {
        Ok(response) => {
            let status = response.status();
            let body_text = response.text().await.unwrap_or_default();
            let cloud_hash = crate::utils::sha256_hex(&body_text);
            if status.is_success() {
                (true, cloud_hash)
            } else {
                return Err(sync_error(format!("cloud returned {status}: {body_text}")));
            }
        }
        Err(error) => {
            return Err(sync_error(format!("cloud unreachable: {error}")));
        }
    };

    // 6. Store sync receipt locally
    let receipt = SyncReceipt {
        sync_id: uuid::Uuid::new_v4().to_string(),
        direction: "up".to_string(),
        timestamp: crate::utils::now_iso8601(),
        device_id: config.device_id.clone(),
        evidence_count: evidence_values.len(),
        app_count: app_summaries.len(),
        conflict_count: 0,
        cloud_response_hash: cloud_hash,
        success,
    };
    save_sync_receipt(&solace_home, &receipt);

    // 7. Record evidence event for the sync itself
    let _ = crate::evidence::record_event(
        &solace_home,
        "twin_sync_up",
        "runtime",
        json!({
            "sync_id": receipt.sync_id,
            "evidence_count": receipt.evidence_count,
            "app_count": receipt.app_count,
        }),
    );

    Ok(Json(json!({
        "sync_id": receipt.sync_id,
        "direction": "up",
        "evidence_count": receipt.evidence_count,
        "app_count": receipt.app_count,
        "success": true,
    })))
}

/// POST /api/v1/cloud/sync/down
///
/// Pulls encrypted state from solaceagi.com cloud, decrypts it, and merges
/// into local state. Local always wins on conflict.
async fn sync_down(
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = require_cloud_config(&state)?;
    let solace_home = crate::utils::solace_home();

    // 1. GET from cloud
    let pull_url = format!("{CLOUD_BASE_URL}/api/v1/twin/pull");
    let cloud_response = reqwest::Client::new()
        .get(&pull_url)
        .bearer_auth(&config.api_key)
        .query(&[("device_id", &config.device_id)])
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await;

    let response_body = match cloud_response {
        Ok(response) => {
            let status = response.status();
            let body_text = response.text().await.unwrap_or_default();
            if status.is_success() {
                body_text
            } else {
                return Err(sync_error(format!("cloud returned {status}: {body_text}")));
            }
        }
        Err(error) => {
            return Err(sync_error(format!("cloud unreachable: {error}")));
        }
    };

    // 2. Parse the cloud envelope
    let envelope: Value = serde_json::from_str(&response_body)
        .map_err(|error| sync_error(format!("invalid cloud response: {error}")))?;

    let encrypted_b64 = envelope["encrypted_payload"]
        .as_str()
        .ok_or_else(|| sync_error("missing encrypted_payload in cloud response".to_string()))?;

    let ciphertext = base64::decode_block(encrypted_b64)
        .map_err(|error| sync_error(format!("base64 decode failed: {error}")))?;

    // 3. Decrypt with AES-256-GCM
    let key = crate::crypto::derive_key(&config.api_key, b"solace-twin-sync:v1");
    let plaintext = crate::crypto::decrypt(&ciphertext, &key)
        .map_err(|error| sync_error(format!("decryption failed: {error}")))?;

    let cloud_payload: SyncPayload = serde_json::from_slice(&plaintext)
        .map_err(|error| sync_error(format!("payload deserialization failed: {error}")))?;

    // 4. Merge into local state (local wins on conflict)
    let merge_result = merge_cloud_state(&solace_home, &cloud_payload);

    // 5. Store sync receipt locally
    let receipt = SyncReceipt {
        sync_id: uuid::Uuid::new_v4().to_string(),
        direction: "down".to_string(),
        timestamp: crate::utils::now_iso8601(),
        device_id: config.device_id.clone(),
        evidence_count: cloud_payload.evidence_entries.len(),
        app_count: cloud_payload.installed_apps.len(),
        conflict_count: merge_result.conflict_count,
        cloud_response_hash: crate::utils::sha256_hex(&response_body),
        success: true,
    };
    save_sync_receipt(&solace_home, &receipt);

    // 6. Record evidence event
    let _ = crate::evidence::record_event(
        &solace_home,
        "twin_sync_down",
        "runtime",
        json!({
            "sync_id": receipt.sync_id,
            "evidence_merged": merge_result.evidence_merged,
            "evidence_skipped": merge_result.evidence_skipped,
            "conflict_count": merge_result.conflict_count,
        }),
    );

    Ok(Json(json!({
        "sync_id": receipt.sync_id,
        "direction": "down",
        "evidence_merged": merge_result.evidence_merged,
        "evidence_skipped": merge_result.evidence_skipped,
        "conflict_count": merge_result.conflict_count,
        "success": true,
    })))
}

/// GET /api/v1/cloud/sync/status
///
/// Returns the last sync receipt (time, direction, conflict count).
async fn sync_status(State(state): State<AppState>) -> Json<Value> {
    let config = state.cloud_config.read().clone();
    let solace_home = crate::utils::solace_home();
    let receipt = load_sync_receipt(&solace_home);

    Json(json!({
        "connected": config.is_some(),
        "last_sync": receipt.map(|r| json!({
            "sync_id": r.sync_id,
            "direction": r.direction,
            "timestamp": r.timestamp,
            "device_id": r.device_id,
            "evidence_count": r.evidence_count,
            "app_count": r.app_count,
            "conflict_count": r.conflict_count,
            "success": r.success,
        })),
    }))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn require_cloud_config(state: &AppState) -> Result<CloudConfig, (StatusCode, Json<Value>)> {
    state.cloud_config.read().clone().ok_or_else(|| {
        (
            StatusCode::PRECONDITION_FAILED,
            Json(json!({"error": "cloud not connected — call POST /api/v1/cloud/connect first"})),
        )
    })
}

fn sync_error(message: String) -> (StatusCode, Json<Value>) {
    (StatusCode::BAD_GATEWAY, Json(json!({"error": message})))
}

fn sync_dir(solace_home: &std::path::Path) -> std::path::PathBuf {
    solace_home.join("sync")
}

fn save_sync_receipt(solace_home: &std::path::Path, receipt: &SyncReceipt) {
    let dir = sync_dir(solace_home);
    let _ = std::fs::create_dir_all(&dir);
    let _ = crate::persistence::write_json(&dir.join("last_sync.json"), receipt);
}

fn load_sync_receipt(solace_home: &std::path::Path) -> Option<SyncReceipt> {
    crate::persistence::read_json(&sync_dir(solace_home).join("last_sync.json")).ok()
}

struct MergeResult {
    evidence_merged: usize,
    evidence_skipped: usize,
    conflict_count: u64,
}

/// Merge cloud state into local state. Local wins on conflict.
///
/// For evidence: we append cloud entries whose IDs don't already exist locally.
/// For apps: no-op (we don't auto-install apps from cloud — that's a separate flow).
fn merge_cloud_state(solace_home: &std::path::Path, cloud: &SyncPayload) -> MergeResult {
    let local_evidence = crate::evidence::list_evidence(solace_home, usize::MAX);
    let local_ids: std::collections::HashSet<String> = local_evidence
        .iter()
        .map(|record| record.id.clone())
        .collect();

    let mut merged = 0usize;
    let mut skipped = 0usize;
    let mut conflicts = 0u64;

    for entry in &cloud.evidence_entries {
        let cloud_id = entry["id"].as_str().unwrap_or_default();
        if cloud_id.is_empty() {
            skipped += 1;
            continue;
        }
        if local_ids.contains(cloud_id) {
            // Local wins — skip the cloud entry
            conflicts += 1;
            skipped += 1;
            continue;
        }
        // Append cloud evidence entry to local evidence file
        let _ = crate::persistence::append_evidence_jsonl(solace_home, &entry);
        merged += 1;
    }

    MergeResult {
        evidence_merged: merged,
        evidence_skipped: skipped,
        conflict_count: conflicts,
    }
}

// ---------------------------------------------------------------------------
// Base64 encoding helpers (using the base64 crate's block API)
// ---------------------------------------------------------------------------

mod base64 {
    use ::base64::engine::general_purpose::STANDARD;
    use ::base64::Engine;

    pub fn encode_block(input: &[u8]) -> String {
        STANDARD.encode(input)
    }

    pub fn decode_block(input: &str) -> Result<Vec<u8>, String> {
        STANDARD
            .decode(input)
            .map_err(|error| format!("base64 decode: {error}"))
    }
}
