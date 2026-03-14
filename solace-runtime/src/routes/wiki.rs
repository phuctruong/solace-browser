// Diagram: 27-prime-wiki-snapshots
use std::fs;

use axum::{extract::State, routing::{get, post}, Json, Router};
use serde::Deserialize;
use serde_json::json;

use crate::pzip::stillwater;
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/wiki/snapshots", get(list_snapshots))
        .route("/api/v1/wiki/extract", post(extract_page))
        .route("/api/v1/wiki/codecs", get(list_codecs))
        .route("/api/v1/wiki/stats", get(wiki_stats))
}

async fn list_snapshots() -> Json<serde_json::Value> {
    let wiki_dir = crate::utils::solace_home().join("wiki");
    let mut snapshots = Vec::new();
    if let Ok(entries) = fs::read_dir(&wiki_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                snapshots.push(json!({
                    "name": path.file_name().and_then(|name| name.to_str()).unwrap_or_default(),
                    "modified_at": crate::utils::modified_iso8601(&path),
                    "size_bytes": fs::metadata(&path).map(|meta| meta.len()).unwrap_or(0),
                }));
            }
        }
    }
    Json(json!({"snapshots": snapshots}))
}

#[derive(Deserialize)]
struct ExtractRequest {
    url: String,
    content: String,
    #[serde(default = "default_content_type")]
    content_type: String,
}

fn default_content_type() -> String {
    "text/html".to_string()
}

async fn extract_page(
    State(state): State<AppState>,
    Json(req): Json<ExtractRequest>,
) -> Json<serde_json::Value> {
    let content = req.content.as_bytes();
    match stillwater::extract(content, &req.content_type, &req.url) {
        Ok(decomp) => {
            // Save snapshot to wiki dir
            let wiki_dir = crate::utils::solace_home().join("wiki");
            let _ = fs::create_dir_all(&wiki_dir);

            let compressed = stillwater::compress_decomposition(&decomp)
                .map(|c| c.len())
                .unwrap_or(0);

            // Save as JSON for agent readability
            let url_hash = &decomp.sha256[..16];
            let snapshot_path = wiki_dir.join(format!("{url_hash}.json"));
            let _ = fs::write(&snapshot_path, serde_json::to_string_pretty(&decomp).unwrap_or_default());

            // Update evidence count
            {
                let mut count = state.evidence_count.write();
                *count += 1;
            }

            Json(json!({
                "status": "extracted",
                "codec": decomp.codec.name(),
                "url": decomp.url,
                "sha256": decomp.sha256,
                "stillwater": {
                    "headings": decomp.stillwater.headings,
                    "nav_links_count": decomp.stillwater.nav_links.len(),
                    "css_tokens_count": decomp.stillwater.css_tokens.len(),
                    "meta_count": decomp.stillwater.meta.len(),
                    "template_hash": decomp.stillwater.template_hash,
                },
                "ripple": {
                    "title": decomp.ripple.title,
                    "sections_count": decomp.ripple.sections.len(),
                    "data_items_count": decomp.ripple.data_items.len(),
                },
                "compressed_size": compressed,
                "original_size": content.len(),
                "ratio": if compressed > 0 {
                    format!("{:.1}:1", content.len() as f64 / compressed as f64)
                } else {
                    "N/A".to_string()
                },
            }))
        }
        Err(e) => Json(json!({
            "status": "error",
            "error": e.to_string(),
        })),
    }
}

async fn wiki_stats() -> Json<serde_json::Value> {
    let wiki_dir = crate::utils::solace_home().join("wiki");
    let snapshot_count = fs::read_dir(&wiki_dir)
        .map(|entries| entries.flatten().filter(|e| e.path().is_file()).count())
        .unwrap_or(0);
    let total_size: u64 = fs::read_dir(&wiki_dir)
        .map(|entries| {
            entries
                .flatten()
                .filter_map(|e| fs::metadata(e.path()).ok())
                .map(|m| m.len())
                .sum()
        })
        .unwrap_or(0);
    Json(json!({
        "snapshot_count": snapshot_count,
        "total_size_bytes": total_size,
        "total_size_human": format_size(total_size),
        "community_browsing": true,
        "codecs_available": 6,
    }))
}

fn format_size(bytes: u64) -> String {
    if bytes < 1024 {
        format!("{bytes}B")
    } else if bytes < 1024 * 1024 {
        format!("{:.1}KB", bytes as f64 / 1024.0)
    } else {
        format!("{:.1}MB", bytes as f64 / (1024.0 * 1024.0))
    }
}

async fn list_codecs() -> Json<serde_json::Value> {
    Json(json!({
        "codecs": [
            {"id": "semantic-html", "detect": "<main> or <article> present", "compression": "PZWB 3-6:1"},
            {"id": "table-html", "detect": "<table> dominant, no <main>", "compression": "PZWB 4-8:1"},
            {"id": "json-api", "detect": "Content-Type: application/json", "compression": "PZJS 3-5:1"},
            {"id": "rss-xml", "detect": "<rss> or <feed> root", "compression": "PZWB 4-7:1"},
            {"id": "jinja-template", "detect": "{% extends %} + {{ t() }}", "compression": "PZWB 3-4:1"},
            {"id": "spa-shell", "detect": "Small HTML + large JS", "compression": "PZWB 2-4:1"},
        ]
    }))
}
