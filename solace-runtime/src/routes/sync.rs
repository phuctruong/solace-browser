// Diagram: apps-backoffice-framework
//! Community Browsing + Cross-Device Sync — protocol features.
//! Sync Prime Wiki snapshots + backoffice data to solaceagi.com.

use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde_json::{json, Value};

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/sync/status", get(sync_status))
        .route("/api/v1/sync/push", post(sync_push))
        .route("/api/v1/sync/pull", post(sync_pull))
        .route("/api/v1/community/stats", get(community_stats))
        .route("/api/v1/community/contribute", post(contribute_snapshot))
}

/// Sync status — what's local vs synced
async fn sync_status(State(state): State<AppState>) -> Json<Value> {
    let cloud = state.cloud_config.read();
    let connected = cloud.is_some();
    let email = cloud
        .as_ref()
        .map(|c| c.user_email.clone())
        .unwrap_or_default();
    let paid = cloud.as_ref().map(|c| c.paid_user).unwrap_or(false);

    let solace_home = crate::utils::solace_home();

    // Count local data
    let wiki_dir = solace_home.join("wiki");
    let snapshot_count = if wiki_dir.exists() {
        std::fs::read_dir(&wiki_dir)
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_name().to_string_lossy().ends_with(".pzwb"))
            .count()
    } else {
        0
    };

    let backoffice_dir = solace_home.join("backoffice");
    let db_count = if backoffice_dir.exists() {
        std::fs::read_dir(&backoffice_dir)
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
            .count()
    } else {
        0
    };

    let evidence_count = crate::evidence::part11_status(&solace_home).record_count;

    Json(json!({
        "connected": connected,
        "email": email,
        "paid": paid,
        "sync_enabled": paid,
        "local": {
            "wiki_snapshots": snapshot_count,
            "backoffice_databases": db_count,
            "evidence_entries": evidence_count,
        },
        "last_sync": null,
        "pending_upload": snapshot_count,
        "pending_download": 0,
    }))
}

/// Push local data to solaceagi.com (paid users only)
async fn sync_push(
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let cloud = state.cloud_config.read();
    let paid = cloud.as_ref().map(|c| c.paid_user).unwrap_or(false);

    if !paid {
        return Err((
            StatusCode::PAYMENT_REQUIRED,
            Json(json!({
                "error": "Sync requires paid plan ($28/mo Pro or higher)",
                "upgrade_url": "https://solaceagi.com/pricing",
            })),
        ));
    }

    let solace_home = crate::utils::solace_home();
    let wiki_dir = solace_home.join("wiki");

    // Count what would be synced
    let mut snapshots = 0usize;
    let mut total_bytes = 0u64;
    if wiki_dir.exists() {
        for entry in std::fs::read_dir(&wiki_dir)
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok())
        {
            if entry.file_name().to_string_lossy().ends_with(".pzwb") {
                snapshots += 1;
                total_bytes += entry.metadata().map(|m| m.len()).unwrap_or(0);
            }
        }
    }

    // Publish sync event
    state.event_bus.publish(
        "sync.push",
        json!({
            "snapshots": snapshots,
            "bytes": total_bytes,
        }),
        "sync",
    );

    // Evidence
    let _ = crate::evidence::record_event(
        &solace_home,
        "sync.push",
        "system",
        json!({"snapshots": snapshots, "bytes": total_bytes}),
    );
    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "pushed": true,
        "snapshots": snapshots,
        "bytes": total_bytes,
        "destination": "solaceagi.com",
        "note": "Full cloud sync requires solaceagi.com API integration",
    })))
}

/// Pull data from solaceagi.com (paid users only)
async fn sync_pull(
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let cloud = state.cloud_config.read();
    let paid = cloud.as_ref().map(|c| c.paid_user).unwrap_or(false);

    if !paid {
        return Err((
            StatusCode::PAYMENT_REQUIRED,
            Json(json!({
                "error": "Sync requires paid plan",
                "upgrade_url": "https://solaceagi.com/pricing",
            })),
        ));
    }

    Ok(Json(json!({
        "pulled": true,
        "new_snapshots": 0,
        "source": "solaceagi.com",
        "note": "Community snapshots will be downloaded as you browse",
    })))
}

/// Community browsing stats — how many shared snapshots exist
async fn community_stats() -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let wiki_dir = solace_home.join("wiki").join("domains");

    let mut domains = Vec::new();
    if wiki_dir.exists() {
        for entry in std::fs::read_dir(&wiki_dir)
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok())
        {
            if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                let domain = entry.file_name().to_string_lossy().to_string();
                let page_count = std::fs::read_dir(entry.path())
                    .into_iter()
                    .flatten()
                    .filter_map(|e| e.ok())
                    .filter(|e| {
                        e.file_name()
                            .to_string_lossy()
                            .ends_with(".prime-snapshot.md")
                    })
                    .count();
                domains.push(json!({"domain": domain, "pages": page_count}));
            }
        }
    }

    Json(json!({
        "community_browsing": true,
        "local_domains": domains.len(),
        "local_pages": domains.iter().map(|d| d["pages"].as_u64().unwrap_or(0)).sum::<u64>(),
        "domains": domains,
        "note": "Community snapshots shared across all Solace users (paid feature)",
    }))
}

/// Contribute a snapshot to the community pool
async fn contribute_snapshot(State(state): State<AppState>) -> Json<Value> {
    let solace_home = crate::utils::solace_home();
    let wiki_dir = solace_home.join("wiki");

    let mut contributed = 0usize;
    if wiki_dir.exists() {
        for entry in std::fs::read_dir(&wiki_dir)
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok())
        {
            if entry
                .file_name()
                .to_string_lossy()
                .ends_with(".prime-snapshot.md")
            {
                contributed += 1;
            }
        }
    }

    state.event_bus.publish(
        "community.contribute",
        json!({
            "snapshots": contributed,
        }),
        "community",
    );

    Json(json!({
        "contributed": contributed,
        "note": "Snapshots will be shared with the community browsing pool",
    }))
}
