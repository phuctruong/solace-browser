// Diagram: apps-backoffice-framework
//! RTC (Real-Time Compression/Reconstruction) — rebuild pages from Stillwater + Ripple + PZip.
//! The core value proposition: Stillwater template + Ripple delta = full page HTML.

use axum::{
    extract::{Path, Query},
    http::StatusCode,
    response::Html,
    routing::get,
    Json, Router,
};
use serde_json::{json, Value};
use std::collections::HashMap;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/rtc/reconstruct/:hash", get(reconstruct_page))
        .route("/api/v1/rtc/domain/:domain", get(domain_sitemap))
        .route("/api/v1/rtc/domain/:domain/:page", get(domain_page_snapshot))
        .route("/api/v1/rtc/stats", get(rtc_stats))
}

/// Reconstruct a page from its PZip binary (exact HTML reconstruction)
async fn reconstruct_page(
    Path(hash): Path<String>,
) -> Result<Html<String>, (StatusCode, Json<Value>)> {
    let wiki_dir = crate::utils::solace_home().join("wiki");
    let pzwb_path = wiki_dir.join(format!("{}.pzwb", hash));

    if !pzwb_path.exists() {
        return Err((StatusCode::NOT_FOUND, Json(json!({"error": format!("PZWB not found: {}", hash)}))));
    }

    let data = std::fs::read(&pzwb_path).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": format!("read: {e}")})))
    })?;

    let html = crate::pzip::web::decompress(&data).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": format!("decompress: {e}")})))
    })?;

    Ok(Html(String::from_utf8_lossy(&html).to_string()))
}

/// Get domain sitemap — all captured pages for a domain
async fn domain_sitemap(
    Path(domain): Path<String>,
) -> Json<Value> {
    let wiki_dir = crate::utils::solace_home().join("wiki").join("domains").join(&domain);

    if !wiki_dir.exists() {
        return Json(json!({"domain": domain, "pages": [], "count": 0}));
    }

    let mut pages = Vec::new();
    if let Ok(entries) = std::fs::read_dir(&wiki_dir) {
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().to_string();
            if name.ends_with(".prime-snapshot.md") && name != "stillwater.prime-snapshot.md" {
                let page_name = name.replace(".prime-snapshot.md", "");
                let size = entry.metadata().map(|m| m.len()).unwrap_or(0);

                // Read first few lines for metadata
                let mut url = String::new();
                let mut codec = String::new();
                if let Ok(content) = std::fs::read_to_string(entry.path()) {
                    for line in content.lines().take(10) {
                        if line.starts_with("# Prime Snapshot:") {
                            url = line.replace("# Prime Snapshot: ", "").trim().to_string();
                        }
                        if line.contains("Codec:") {
                            codec = line.split("Codec:").nth(1).unwrap_or("").split('|').next().unwrap_or("").trim().to_string();
                        }
                    }
                }

                pages.push(json!({
                    "page": page_name,
                    "url": url,
                    "codec": codec,
                    "size_bytes": size,
                    "snapshot_path": format!("/api/v1/rtc/domain/{}/{}", domain, page_name),
                }));
            }
        }
    }

    // Check for Stillwater template
    let stillwater_path = wiki_dir.join("stillwater.prime-snapshot.md");
    let has_stillwater = stillwater_path.exists();
    let stillwater_size = std::fs::metadata(&stillwater_path).map(|m| m.len()).unwrap_or(0);

    let count = pages.len();
    Json(json!({
        "domain": domain,
        "pages": pages,
        "count": count,
        "has_stillwater": has_stillwater,
        "stillwater_size": stillwater_size,
    }))
}

/// Get a specific page's Prime Mermaid snapshot for a domain
async fn domain_page_snapshot(
    Path((domain, page)): Path<(String, String)>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let wiki_dir = crate::utils::solace_home().join("wiki").join("domains").join(&domain);
    let snapshot_path = wiki_dir.join(format!("{}.prime-snapshot.md", page));

    if !snapshot_path.exists() {
        return Err((StatusCode::NOT_FOUND, Json(json!({"error": format!("snapshot not found: {}/{}", domain, page)}))));
    }

    let content = std::fs::read_to_string(&snapshot_path).map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": format!("read: {e}")})))
    })?;

    // Also load Stillwater template
    let stillwater_path = wiki_dir.join("stillwater.prime-snapshot.md");
    let stillwater = std::fs::read_to_string(&stillwater_path).unwrap_or_default();

    Ok(Json(json!({
        "domain": domain,
        "page": page,
        "snapshot": content,
        "stillwater": stillwater,
        "size_bytes": content.len(),
    })))
}

/// RTC statistics — compression ratios, domain coverage
async fn rtc_stats() -> Json<Value> {
    let wiki_dir = crate::utils::solace_home().join("wiki");

    // Count snapshots and PZWB files
    let mut snapshot_count = 0usize;
    let mut pzwb_count = 0usize;
    let mut total_pzwb_size = 0u64;

    if wiki_dir.exists() {
        if let Ok(entries) = std::fs::read_dir(&wiki_dir) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                if name.ends_with(".prime-snapshot.md") { snapshot_count += 1; }
                if name.ends_with(".pzwb") {
                    pzwb_count += 1;
                    total_pzwb_size += entry.metadata().map(|m| m.len()).unwrap_or(0);
                }
            }
        }
    }

    // Count domains
    let mut domains = Vec::new();
    let domains_dir = wiki_dir.join("domains");
    if domains_dir.exists() {
        if let Ok(entries) = std::fs::read_dir(&domains_dir) {
            for entry in entries.flatten() {
                if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                    let domain = entry.file_name().to_string_lossy().to_string();
                    let page_count = std::fs::read_dir(entry.path())
                        .into_iter().flatten().filter_map(|e| e.ok())
                        .filter(|e| e.file_name().to_string_lossy().ends_with(".prime-snapshot.md"))
                        .count();
                    let has_stillwater = entry.path().join("stillwater.prime-snapshot.md").exists();
                    domains.push(json!({
                        "domain": domain,
                        "pages": page_count,
                        "has_stillwater": has_stillwater,
                        "rtc_ready": has_stillwater && page_count > 0,
                    }));
                }
            }
        }
    }

    let rtc_ready = domains.iter().filter(|d| d["rtc_ready"].as_bool().unwrap_or(false)).count();

    Json(json!({
        "snapshots": snapshot_count,
        "pzwb_files": pzwb_count,
        "total_compressed_bytes": total_pzwb_size,
        "domains": domains,
        "domain_count": domains.len(),
        "rtc_ready_domains": rtc_ready,
        "rtc_coverage_pct": if !domains.is_empty() { rtc_ready * 100 / domains.len() } else { 0 },
    }))
}
