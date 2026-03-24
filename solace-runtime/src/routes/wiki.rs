// Diagram: 27-prime-wiki-snapshots
use std::fs;

use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
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
        .route("/api/v1/wiki/export", get(export_wiki))
        .route("/api/v1/screenshot", post(capture_screenshot))
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
    // Security: reject non-HTTP URLs (prevent file:// traversal)
    if !req.url.starts_with("http://")
        && !req.url.starts_with("https://")
        && !req.url.starts_with("app://")
    {
        return Json(json!({
            "status": "error",
            "error": "URL must start with http://, https://, or app://",
        }));
    }

    let content = req.content.as_bytes();
    match stillwater::extract(content, &req.content_type, &req.url) {
        Ok(decomp) => {
            // Save snapshot to wiki dir
            let wiki_dir = crate::utils::solace_home().join("wiki");
            let _ = fs::create_dir_all(&wiki_dir);

            let url_hash = &decomp.sha256[..16];

            // 0. Compress with PZip FIRST (need size for snapshot metadata)
            let pzwb_path = wiki_dir.join(format!("{url_hash}.pzwb"));
            let compressed = if let Ok(pzwb) = crate::pzip::web::compress(content, "text/html") {
                let len = pzwb.len();
                let _ = fs::write(&pzwb_path, &pzwb);
                len
            } else {
                0
            };

            // 1. Save .prime-snapshot.md (Prime Mermaid format — geometric language)
            // Mermaid flowchart captures page STRUCTURE, not just counts.
            // This enables: page reconstruction, regression testing, AI comprehension.
            let section_nodes: String = if decomp.ripple.sections.is_empty() {
                // If no sections extracted, use headings as nodes
                decomp
                    .stillwater
                    .headings
                    .iter()
                    .enumerate()
                    .map(|(i, h)| {
                        let safe = h
                            .replace('"', "'")
                            .replace('\n', " ")
                            .chars()
                            .take(40)
                            .collect::<String>();
                        format!("    PAGE --> S{}[{}]", i, safe)
                    })
                    .collect::<Vec<_>>()
                    .join("\n")
            } else {
                decomp
                    .ripple
                    .sections
                    .iter()
                    .enumerate()
                    .map(|(i, s)| {
                        let label = if s.heading.is_empty() {
                            "Section"
                        } else {
                            &s.heading
                        };
                        let safe = label
                            .replace('"', "'")
                            .replace('\n', " ")
                            .chars()
                            .take(40)
                            .collect::<String>();
                        format!("    PAGE --> S{}[{}]", i, safe)
                    })
                    .collect::<Vec<_>>()
                    .join("\n")
            };
            let title_short = decomp.ripple.title.chars().take(50).collect::<String>();
            let page_label = extract_path(&decomp.url);
            let snapshot_md = format!(
                "<!-- Diagram: hub-browse-capture-pipeline -->\n\
                 # Prime Snapshot: {url}\n\
                 # SHA-256: {sha}\n\
                 # DNA: `page({path}) = stillwater(nav+meta) × ripple(sections) × seal(sha256)`\n\
                 # Auth: 65537 | Codec: {codec} | Compression: {ratio}\n\n\
                 ## Identity\n\
                 - **URL**: {url}\n\
                 - **Codec**: {codec}\n\
                 - **Original**: {orig} bytes → **Compressed**: {comp} bytes\n\n\
                 ## Canonical Diagram\n\n\
                 ```mermaid\n\
                 flowchart TB\n\
                     PAGE[PAGE<br>{path}<br>{title}]\n\
                 {nodes}\n\
                 ```\n\n\
                 ## Stillwater (Generator — shared across domain)\n\
                 - headings: {h_count}\n\
                 - nav_links: {n_count}\n\
                 - meta: {m_count}\n\
                 - template_hash: {th}\n\n\
                 ## Ripple (Residual — this page only)\n\
                 - title: {title}\n\
                 - sections: {s_count}\n\n\
                 ## Verification\n\
                 ```\n\
                 ASSERT: SHA-256 matches content\n\
                 ASSERT: Codec detected as {codec}\n\
                 ASSERT: Stillwater template_hash present\n\
                 ```\n",
                url = decomp.url,
                sha = decomp.sha256,
                path = page_label,
                codec = decomp.codec.name(),
                ratio = if compressed > 0 {
                    format!("{:.1}:1", content.len() as f64 / compressed as f64)
                } else {
                    "N/A".to_string()
                },
                orig = content.len(),
                comp = compressed,
                title = title_short,
                nodes = section_nodes,
                h_count = decomp.stillwater.headings.len(),
                n_count = decomp.stillwater.nav_links.len(),
                m_count = decomp.stillwater.meta.len(),
                th = decomp.stillwater.template_hash,
                s_count = decomp.ripple.sections.len(),
            );
            // 2. Write the snapshot (PZip already saved above)
            let snapshot_path = wiki_dir.join(format!("{url_hash}.prime-snapshot.md"));
            let _ = fs::write(&snapshot_path, &snapshot_md);

            // 3. Update domain sitemap (auto-create prime-wiki per domain)
            let domain = extract_domain(&decomp.url);
            let page_path_str = extract_path(&decomp.url);
            let mut domain_stillwater_created = false;
            if !domain.is_empty() {
                let domain_dir = wiki_dir.join("domains").join(&domain);
                let _ = fs::create_dir_all(&domain_dir);

                // 3a. Domain stillwater check — create on FIRST visit
                // Stillwater = shared nav/header/footer structure, reused across pages
                let stillwater_path = domain_dir.join("stillwater.prime-snapshot.md");
                if !stillwater_path.exists() {
                    let stillwater_md = format!(
                        "<!-- Diagram: hub-browse-capture-pipeline -->\n\
                         # Domain Stillwater: {domain}\n\
                         # First captured: {ts}\n\
                         # Template hash: {th}\n\n\
                         ## Shared Structure (reused across all pages on this domain)\n\n\
                         ### Navigation\n\
                         {nav}\n\n\
                         ### Headings\n\
                         {headings}\n\n\
                         ### CSS Tokens\n\
                         {css}\n\n\
                         ### Meta\n\
                         {meta}\n",
                        domain = domain,
                        ts = decomp.ripple.timestamp,
                        th = decomp.stillwater.template_hash,
                        nav = decomp
                            .stillwater
                            .nav_links
                            .iter()
                            .map(|l| format!("- {l}"))
                            .collect::<Vec<_>>()
                            .join("\n"),
                        headings = decomp
                            .stillwater
                            .headings
                            .iter()
                            .map(|h| format!("- {h}"))
                            .collect::<Vec<_>>()
                            .join("\n"),
                        css = decomp
                            .stillwater
                            .css_tokens
                            .iter()
                            .map(|t| format!("- `{t}`"))
                            .collect::<Vec<_>>()
                            .join("\n"),
                        meta = decomp
                            .stillwater
                            .meta
                            .iter()
                            .map(|(k, v)| format!("- {k}: {v}"))
                            .collect::<Vec<_>>()
                            .join("\n"),
                    );
                    let _ = fs::write(&stillwater_path, &stillwater_md);
                    domain_stillwater_created = true;
                }

                // Save page snapshot in domain dir
                let page_name = if page_path_str.is_empty() || page_path_str == "/" {
                    "index".to_string()
                } else {
                    page_path_str.trim_matches('/').replace('/', "-")
                };
                let _ = fs::write(
                    domain_dir.join(format!("{page_name}.prime-snapshot.md")),
                    &snapshot_md,
                );

                // Update domain sitemap (append or create)
                let sitemap_path = domain_dir.join("sitemap.prime-wiki.md");
                let entry = format!(
                    "| {} | {} | {} | {} |\n",
                    page_path_str,
                    decomp.ripple.title,
                    decomp.ripple.sections.len(),
                    decomp.codec.name(),
                );
                if sitemap_path.exists() {
                    if let Ok(existing) = fs::read_to_string(&sitemap_path) {
                        if !existing.contains(&page_path_str) {
                            let updated = format!("{}{}", existing, entry);
                            let _ = fs::write(&sitemap_path, updated);
                        }
                    }
                } else {
                    let header = format!(
                        "# Prime Wiki: {}\n\
                         # Auto-generated by community browsing\n\n\
                         | Path | Title | Sections | Codec |\n\
                         |------|-------|----------|-------|\n\
                         {}",
                        domain, entry
                    );
                    let _ = fs::write(&sitemap_path, header);
                }
            }

            // Two files per page + domain sitemap auto-updated

            // Update evidence count + budget tracking
            {
                let mut count = state.evidence_count.write();
                *count += 1;
            }
            crate::routes::budget::record_budget_event(&state);

            // Auto-sync trigger: after evidence seal, push if paid user
            // Non-blocking — spawn a background task so we don't delay the response
            let is_paid = state
                .cloud_config
                .read()
                .as_ref()
                .map(|c| c.paid_user)
                .unwrap_or(false);
            if is_paid {
                let sync_state = state.clone();
                tokio::spawn(async move {
                    // Fire-and-forget sync push — errors are logged, not propagated
                    if let Err(error) = trigger_auto_sync(&sync_state).await {
                        tracing::warn!(%error, "auto-sync after extract failed");
                    }
                });
            }

            // Check screenshot setting
            let auto_screenshot =
                crate::config::load_settings(&crate::utils::solace_home()).auto_screenshot;

            // Token savings: raw HTML tokens vs compressed snapshot tokens
            let raw_tokens = content.len() / 4;
            let snap_tokens = compressed / 4;
            let tokens_saved = raw_tokens.saturating_sub(snap_tokens);
            let savings_pct = if raw_tokens > 0 {
                tokens_saved * 100 / raw_tokens
            } else {
                0
            };

            Json(json!({
                "status": "extracted",
                "codec": decomp.codec.name(),
                "url": decomp.url,
                "sha256": decomp.sha256,
                "token_savings": {
                    "raw_html_tokens": raw_tokens,
                    "snapshot_tokens": snap_tokens,
                    "tokens_saved": tokens_saved,
                    "savings_pct": savings_pct,
                },
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
                "domain_stillwater_created": domain_stillwater_created,
                "auto_screenshot": auto_screenshot,
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

/// GET /api/v1/wiki/export
///
/// Bulk export all wiki snapshots as a JSON array.
/// Used by community browsing to share/download domain knowledge.
async fn export_wiki() -> Json<serde_json::Value> {
    let wiki_dir = crate::utils::solace_home().join("wiki");
    let domains_dir = wiki_dir.join("domains");
    let mut exports = Vec::new();

    if let Ok(domains) = fs::read_dir(&domains_dir) {
        for domain_entry in domains.flatten() {
            let domain_path = domain_entry.path();
            if !domain_path.is_dir() {
                continue;
            }
            let domain = domain_path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("")
                .to_string();

            if let Ok(files) = fs::read_dir(&domain_path) {
                for file_entry in files.flatten() {
                    let path = file_entry.path();
                    if path.extension().is_some_and(|e| e == "md") {
                        let filename = path
                            .file_name()
                            .and_then(|n| n.to_str())
                            .unwrap_or("")
                            .to_string();
                        let size = fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
                        exports.push(json!({
                            "domain": domain,
                            "filename": filename,
                            "size_bytes": size,
                        }));
                    }
                }
            }
        }
    }

    Json(json!({
        "exports": exports,
        "count": exports.len(),
        "format": "prime-snapshot-index",
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

/// Extract domain from URL string (no url crate dependency)
fn extract_domain(url: &str) -> String {
    url.strip_prefix("https://")
        .or_else(|| url.strip_prefix("http://"))
        .unwrap_or(url)
        .split('/')
        .next()
        .unwrap_or("")
        .split(':')
        .next()
        .unwrap_or("")
        .to_string()
}

/// Extract path from URL string
fn extract_path(url: &str) -> String {
    let after_scheme = url
        .strip_prefix("https://")
        .or_else(|| url.strip_prefix("http://"))
        .unwrap_or(url);
    match after_scheme.find('/') {
        Some(pos) => after_scheme[pos..].to_string(),
        None => "/".to_string(),
    }
}

/// POST /api/v1/screenshot
///
/// Screenshot capture endpoint. Full-page PNG rendering requires a browser
/// engine (Chromium), which the Rust runtime does not embed. This endpoint
/// acts as a delegation point: the Hub or browser process calls this to
/// record the intent, and the actual capture is performed by the browser.
///
/// When auto_screenshot is enabled in settings, the extract_page response
/// includes `"auto_screenshot": true` so the caller knows to follow up
/// with a screenshot capture via the browser.
#[derive(Deserialize)]
struct ScreenshotRequest {
    url: String,
    /// Base64-encoded PNG bytes provided by the browser after capture.
    /// When empty, this is a "request to capture" (browser should capture
    /// and call back with the data).
    #[serde(default)]
    png_base64: String,
}

async fn capture_screenshot(
    State(state): State<AppState>,
    Json(req): Json<ScreenshotRequest>,
) -> Json<serde_json::Value> {
    let solace_home = crate::utils::solace_home();
    let settings = crate::config::load_settings(&solace_home);

    if !settings.auto_screenshot {
        return Json(json!({
            "status": "skipped",
            "reason": "auto_screenshot is disabled in settings",
        }));
    }

    if req.png_base64.is_empty() {
        // No screenshot data provided — tell the caller to delegate to browser
        return Json(json!({
            "status": "delegate_to_browser",
            "url": req.url,
            "message": "Screenshot capture requires the browser. \
                        Capture the page and POST back with png_base64.",
        }));
    }

    // Browser provided the screenshot — store it
    let screenshots_dir = solace_home.join("screenshots");
    let _ = fs::create_dir_all(&screenshots_dir);

    let url_hash = &crate::utils::sha256_hex(&req.url)[..16];
    let timestamp = chrono::Utc::now().format("%Y%m%d-%H%M%S").to_string();
    let filename = format!("{timestamp}_{url_hash}.png");
    let filepath = screenshots_dir.join(&filename);

    // Decode base64 and write PNG
    match base64_decode(&req.png_base64) {
        Ok(png_bytes) => {
            let screenshot_hash = crate::utils::sha256_hex(&String::from_utf8_lossy(&png_bytes));
            let _ = fs::write(&filepath, &png_bytes);

            // Record evidence for the screenshot
            let _ = crate::evidence::record_event(
                &solace_home,
                "screenshot_captured",
                "runtime",
                json!({
                    "url": req.url,
                    "filename": filename,
                    "sha256": screenshot_hash,
                    "size_bytes": png_bytes.len(),
                }),
            );

            // Increment evidence count
            {
                let mut count = state.evidence_count.write();
                *count += 1;
            }

            Json(json!({
                "status": "captured",
                "filename": filename,
                "sha256": screenshot_hash,
                "size_bytes": png_bytes.len(),
            }))
        }
        Err(error) => Json(json!({
            "status": "error",
            "error": format!("base64 decode failed: {error}"),
        })),
    }
}

/// Decode base64 string to bytes (using the base64 crate).
fn base64_decode(input: &str) -> Result<Vec<u8>, String> {
    use ::base64::engine::general_purpose::STANDARD;
    use ::base64::Engine;
    STANDARD.decode(input).map_err(|error| format!("{error}"))
}

/// Trigger an async cloud sync push. Called after evidence is sealed for
/// paid users. Errors are returned (not panicked) so callers can log them.
async fn trigger_auto_sync(state: &AppState) -> Result<(), String> {
    let config = state
        .cloud_config
        .read()
        .clone()
        .ok_or_else(|| "no cloud config".to_string())?;

    if !config.paid_user {
        return Ok(());
    }

    let solace_home = crate::utils::solace_home();

    // Collect recent evidence (last 100 entries for incremental sync)
    let evidence_entries = crate::evidence::list_evidence(&solace_home, 100);
    let evidence_values: Vec<serde_json::Value> = evidence_entries
        .iter()
        .filter_map(|record| serde_json::to_value(record).ok())
        .collect();

    let payload = json!({
        "device_id": config.device_id,
        "user_email": config.user_email,
        "timestamp": crate::utils::now_iso8601(),
        "evidence_count": evidence_values.len(),
        "auto_sync": true,
    });

    let sync_url = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/twin/sync";
    let key = crate::crypto::derive_key(&config.api_key, b"solace-twin-sync:v1");
    let plaintext = serde_json::to_vec(&payload).map_err(|e| e.to_string())?;
    let ciphertext = crate::crypto::encrypt(&plaintext, &key)?;

    use ::base64::engine::general_purpose::STANDARD;
    use ::base64::Engine;
    let encoded = STANDARD.encode(&ciphertext);

    let response = reqwest::Client::new()
        .post(sync_url)
        .bearer_auth(&config.api_key)
        .json(&json!({
            "device_id": config.device_id,
            "encrypted_payload": encoded,
        }))
        .timeout(std::time::Duration::from_secs(15))
        .send()
        .await
        .map_err(|e| format!("auto-sync request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(format!("auto-sync cloud returned {status}: {body}"));
    }

    // Record evidence for the auto-sync itself
    let _ = crate::evidence::record_event(
        &solace_home,
        "auto_sync_triggered",
        "runtime",
        json!({
            "evidence_count": evidence_values.len(),
            "trigger": "extract_page",
        }),
    );

    Ok(())
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
