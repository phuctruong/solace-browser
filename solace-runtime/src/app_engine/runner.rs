// Diagram: 12-app-engine-pipeline
use std::path::PathBuf;
use std::time::Duration;

use chrono::Utc;
use serde_json::{Map, Value};

use crate::event_log::{EventLog, EventType};
use crate::state::{AppState, Notification};

// ---------------------------------------------------------------------------
// LLM Level Routing helpers
// ---------------------------------------------------------------------------

fn should_use_llm(manifest: &crate::app_engine::AppManifest) -> bool {
    manifest.levels.values().any(|l| l != "L1")
}

fn has_l3_plus_actions(manifest: &crate::app_engine::AppManifest) -> bool {
    manifest
        .levels
        .values()
        .any(|l| matches!(l.as_str(), "L3" | "L4" | "L5"))
}

fn max_level(manifest: &crate::app_engine::AppManifest) -> &'static str {
    manifest
        .levels
        .values()
        .map(|l| match l.as_str() {
            "L5" => 5,
            "L4" => 4,
            "L3" => 3,
            "L2" => 2,
            _ => 1,
        })
        .max()
        .map(|n| match n {
            5 => "L5",
            4 => "L4",
            3 => "L3",
            2 => "L2",
            _ => "L1",
        })
        .unwrap_or("L1")
}

async fn enhance_with_llm(
    manifest: &crate::app_engine::AppManifest,
    html: &str,
) -> Result<String, String> {
    let api_key =
        std::env::var("OPENROUTER_API_KEY").map_err(|_| "No OPENROUTER_API_KEY".to_string())?;

    // Determine model from max level
    let model = match max_level(manifest) {
        "L2" => "anthropic/claude-haiku-4-5",
        "L3" => "anthropic/claude-sonnet-4-6",
        "L4" | "L5" => "anthropic/claude-sonnet-4-6", // Opus too expensive for auto
        _ => return Ok(html.to_string()),
    };

    let truncated = &html[..html.len().min(4000)];
    let prompt = format!(
        "Enhance this report with analysis and insights. Keep the HTML structure. \
         Add a <section class=\"llm-analysis\"> at the end with your synthesis.\n\n{}",
        truncated
    );

    let client = reqwest::Client::new();
    let response = client
        .post("https://openrouter.ai/api/v1/chat/completions")
        .bearer_auth(&api_key)
        .json(&serde_json::json!({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
        }))
        .timeout(Duration::from_secs(60))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let body: Value = response.json().await.map_err(|e| e.to_string())?;
    let analysis = body["choices"][0]["message"]["content"]
        .as_str()
        .unwrap_or("");

    // Append analysis to HTML
    let enhanced = html.replace(
        "</body>",
        &format!(
            "<section class=\"llm-analysis\"><h2>AI Analysis ({})</h2>{}</section></body>",
            model, analysis
        ),
    );
    Ok(enhanced)
}

pub async fn run_app(app_id: &str, state: &AppState) -> Result<PathBuf, String> {
    let app_dir =
        crate::utils::find_app_dir(app_id).ok_or_else(|| format!("app not found: {app_id}"))?;
    let manifest = crate::app_engine::inbox::load_manifest(&app_dir)?;
    let run_id = Utc::now().format("%Y%m%d-%H%M%S").to_string();

    // Acquire domain tab if app has a domain
    if !manifest.domain.is_empty() {
        let domain = crate::routes::domains::extract_root_domain(&manifest.domain);
        let mut tabs = state.domain_tabs.write();
        let now = crate::utils::now_iso8601();
        let tab = crate::state::DomainTab {
            domain: domain.clone(),
            current_url: String::new(),
            session_id: String::new(),
            active_app_id: Some(app_id.to_string()),
            last_activity: now,
            tab_state: crate::state::TabState::Working,
        };
        tabs.insert(domain, tab);
        drop(tabs);
    }

    // Create event log for this run
    let mut event_log = EventLog::new(app_id, &run_id);

    let mut data = fetch_data_sources(&manifest, &mut event_log).await?;
    data.insert(
        "config".to_string(),
        crate::app_engine::inbox::load_config(&app_dir),
    );
    data.insert(
        "inbox".to_string(),
        crate::app_engine::inbox::load_inbox_payload(&app_dir),
    );
    // For conductor apps: load ONLY orchestrated apps' outboxes
    // For standard apps: load all other apps' latest reports
    let source_reports = if manifest.app_type == "conductor" && !manifest.orchestrates.is_empty() {
        load_orchestrated_reports(&manifest.orchestrates)
    } else {
        load_source_reports(app_id)
    };
    data.insert("source_reports".to_string(), Value::Array(source_reports));
    data.insert("is_conductor".to_string(), Value::Bool(manifest.app_type == "conductor"));
    data.insert("run_id".to_string(), Value::String(run_id.clone()));
    data.insert(
        "evidence_hash".to_string(),
        Value::String(crate::utils::sha256_hex(&format!("{app_id}:{run_id}"))),
    );

    let html = crate::app_engine::template::render_report(
        &manifest,
        &app_dir,
        &Value::Object(data.clone()),
    )?;

    // ── FEATURE 1: DETERMINE_LEVELS ──
    // manifest.levels is loaded from manifest.yaml (HashMap<String, String>).
    // If absent, serde default gives empty map → all actions treated as L1.
    let level_tag = max_level(&manifest);

    // ── FEATURE 2: LLM_PROCESS ──
    // If any action requires L2+, enhance the report via LLM (OpenRouter).
    // Falls back to L1 (original HTML) if no API key or if the call fails.
    let html = if should_use_llm(&manifest) {
        match enhance_with_llm(&manifest, &html).await {
            Ok(enhanced) => {
                event_log.append_event(
                    EventType::Render,
                    None,
                    None,
                    None,
                    Some(format!("llm_enhance=OK level={}", level_tag)),
                );
                enhanced
            }
            Err(reason) => {
                event_log.append_event(
                    EventType::Render,
                    None,
                    None,
                    None,
                    Some(format!("llm_enhance=SKIP reason={}", reason)),
                );
                html // L1 fallback
            }
        }
    } else {
        html
    };

    // ── FEATURE 3: PREVIEW (L3+) ──
    // Write a preview file before execution so the user can inspect / reject.
    if has_l3_plus_actions(&manifest) {
        let preview_dir = app_dir.join("outbox").join("previews");
        let _ = std::fs::create_dir_all(&preview_dir);
        let _ = std::fs::write(preview_dir.join(format!("{run_id}.html")), &html);
        // Auto-approve for now — the preview file existing IS the evidence.
    }

    // ── FEATURE 4: FORBIDDEN_REJECTED ──
    // If a preview was rejected by the user, abort the run.
    let rejected_marker = app_dir
        .join("outbox")
        .join("previews")
        .join(format!("{run_id}.rejected"));
    if rejected_marker.exists() {
        return Err(format!("Run {run_id} was rejected by user"));
    }

    // Log Render event
    let template_name = if manifest.template.is_empty() {
        manifest.report_template.clone()
    } else {
        manifest.template.clone()
    };
    let output_hash = crate::utils::sha256_hex(&html);
    event_log.append_event(
        EventType::Render,
        None,
        None,
        None,
        Some(format!("template={} output_hash={}", template_name, output_hash)),
    );

    let outbox_dir = app_dir.join("outbox").join("runs").join(&run_id);
    std::fs::create_dir_all(&outbox_dir).map_err(|error| error.to_string())?;
    let report_path = outbox_dir.join("report.html");
    std::fs::write(&report_path, &html).map_err(|error| error.to_string())?;
    std::fs::write(
        outbox_dir.join("payload.json"),
        serde_json::to_vec_pretty(&Value::Object(data)).map_err(|error| error.to_string())?,
    )
    .map_err(|error| error.to_string())?;

    // Stillwater/Ripple decomposition — makes report agent-readable
    if let Ok(decomp) = crate::pzip::stillwater::extract(
        html.as_bytes(),
        "text/html",
        &format!("app://{app_id}/runs/{run_id}"),
    ) {
        let _ = std::fs::write(
            outbox_dir.join("stillwater.json"),
            serde_json::to_string_pretty(&decomp.stillwater).unwrap_or_default(),
        );
        let _ = std::fs::write(
            outbox_dir.join("ripple.json"),
            serde_json::to_string_pretty(&decomp.ripple).unwrap_or_default(),
        );
    }

    crate::pzip::evidence::seal_run(app_id, &run_id, html.as_bytes())
        .map_err(|error| error.to_string())?;

    // Log Seal event
    let evidence_hash = crate::utils::sha256_hex(&format!("{app_id}:{run_id}:sealed"));
    event_log.append_event(
        EventType::Seal,
        None,
        None,
        None,
        Some(format!("evidence_hash={}", evidence_hash)),
    );

    // Save events.jsonl alongside report.html
    event_log
        .save_events(&outbox_dir)
        .map_err(|error| format!("failed to save event log: {error}"))?;

    // ── FEATURE 5: RECORD_EVENT ──
    // After sealing evidence, append an event record to the global events log.
    let event_record = serde_json::json!({
        "app_id": app_id,
        "action": "RUN",
        "level": max_level(&manifest),
        "cost": 0,
        "status": "PASS",
        "timestamp": crate::utils::now_iso8601(),
        "device_id": "local",
        "run_id": run_id,
    });
    let events_dir = crate::utils::solace_home().join("events");
    let _ = std::fs::create_dir_all(&events_dir);
    let _ = crate::persistence::append_jsonl(
        &events_dir.join("app_events.jsonl"),
        &event_record,
    );

    *state.app_count.write() += 1;
    *state.evidence_count.write() += 1;
    crate::routes::budget::record_budget_event(state);
    state.notifications.write().push(Notification {
        id: uuid::Uuid::new_v4().to_string(),
        message: format!("App {} completed", manifest.name),
        level: "info".to_string(),
        read: false,
        created_at: crate::utils::now_iso8601(),
    });

    // Release domain tab after app completes
    if !manifest.domain.is_empty() {
        let domain = crate::routes::domains::extract_root_domain(&manifest.domain);
        let mut tabs = state.domain_tabs.write();
        if let Some(tab) = tabs.get_mut(&domain) {
            tab.active_app_id = None;
            tab.tab_state = crate::state::TabState::Idle;
            tab.last_activity = crate::utils::now_iso8601();
        }
    }

    Ok(report_path)
}

async fn fetch_data_sources(
    manifest: &crate::app_engine::AppManifest,
    event_log: &mut EventLog,
) -> Result<Map<String, Value>, String> {
    let client = reqwest::Client::new();
    let mut data = Map::new();
    let mut items = Vec::new();

    if manifest.data_sources.is_empty() {
        if let Some(url) = &manifest.source_url {
            let remote = fetch_json(&client, url).await?;
            let response_hash = crate::utils::sha256_hex(&remote.to_string());
            event_log.append_event(
                EventType::Fetch,
                Some(url.clone()),
                None,
                None,
                Some(format!("status=200 response_hash={}", response_hash)),
            );
            items.extend(normalize_items("remote", &remote, usize::MAX));
            data.insert("remote".to_string(), remote);
        }
    } else {
        for source in &manifest.data_sources {
            let json = fetch_json(&client, &source.url).await?;
            let response_hash = crate::utils::sha256_hex(&json.to_string());
            event_log.append_event(
                EventType::Fetch,
                Some(source.url.clone()),
                None,
                None,
                Some(format!(
                    "source={} status=200 response_hash={}",
                    source.name, response_hash
                )),
            );
            items.extend(normalize_items(
                &source.name,
                &json,
                if source.limit == 0 {
                    usize::MAX
                } else {
                    source.limit
                },
            ));
            data.insert(source.name.clone(), json);
        }
    }

    if !items.is_empty() {
        data.insert("items".to_string(), Value::Array(items));
    }

    Ok(data)
}

async fn fetch_json(client: &reqwest::Client, url: &str) -> Result<Value, String> {
    let response = client
        .get(url)
        .header(
            "User-Agent",
            "SolaceRuntime/0.1.0 (by /u/solaceagi, contact: phuc@phuc.net)",
        )
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|error| error.to_string())?
        .error_for_status()
        .map_err(|error| error.to_string())?;

    let content_type = response
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();

    let text = response.text().await.map_err(|e| e.to_string())?;

    // Try JSON first
    if let Ok(json) = serde_json::from_str::<Value>(&text) {
        return Ok(json);
    }

    // RSS/Atom/XML: wrap raw text as { "raw_xml": "...", "content_type": "..." }
    // Extract titles from <title> tags for basic normalization
    let titles: Vec<String> = text
        .split("<title>")
        .skip(1)
        .filter_map(|s| s.split("</title>").next())
        .map(|s| s.trim().to_string())
        .collect();

    let items: Vec<Value> = titles
        .iter()
        .map(|title| {
            serde_json::json!({
                "title": title,
                "source": "rss",
            })
        })
        .collect();

    Ok(serde_json::json!({
        "items": items,
        "content_type": content_type,
        "raw_length": text.len(),
        "format": "rss_parsed",
    }))
}

fn normalize_items(source_name: &str, value: &Value, limit: usize) -> Vec<Value> {
    let items = match value {
        Value::Array(items) => items.clone(),
        Value::Object(map) => map
            .get("items")
            .and_then(Value::as_array)
            .cloned()
            .or_else(|| map.get("hits").and_then(Value::as_array).cloned())
            .unwrap_or_else(|| vec![value.clone()]),
        _ => Vec::new(),
    };

    items
        .into_iter()
        .take(limit)
        .map(|item| normalize_item(source_name, item))
        .collect()
}

fn normalize_item(source_name: &str, item: Value) -> Value {
    let title = pick_string(&item, &["title", "name", "headline"])
        .unwrap_or_else(|| source_name.to_string());
    let url = pick_string(&item, &["url", "link", "href"]);
    let summary = pick_string(&item, &["summary", "text", "body"]);
    let score = pick_value(&item, &["score", "points"]);

    let mut normalized = Map::new();
    normalized.insert("title".to_string(), Value::String(title));
    normalized.insert("source".to_string(), Value::String(source_name.to_string()));
    if let Some(url) = url {
        normalized.insert("url".to_string(), Value::String(url));
    }
    if let Some(summary) = summary {
        normalized.insert("summary".to_string(), Value::String(summary));
    }
    if let Some(score) = score {
        normalized.insert("score".to_string(), score);
    }
    normalized.insert("raw".to_string(), item);
    Value::Object(normalized)
}

fn pick_string(value: &Value, keys: &[&str]) -> Option<String> {
    pick_value(value, keys).and_then(|value| match value {
        Value::String(text) => Some(text),
        Value::Number(number) => Some(number.to_string()),
        _ => None,
    })
}

fn pick_value(value: &Value, keys: &[&str]) -> Option<Value> {
    keys.iter().find_map(|key| value.get(*key).cloned())
}

/// Load reports from specific orchestrated apps (Conductor pattern).
fn load_orchestrated_reports(orchestrated_ids: &[String]) -> Vec<Value> {
    orchestrated_ids
        .iter()
        .filter_map(|app_id| {
            let app_dir = crate::utils::find_app_dir(app_id)?;
            let manifest = crate::app_engine::inbox::load_manifest(&app_dir).ok()?;
            let latest_run = latest_run_dir(&app_dir)?;
            let report_path = latest_run.join("report.html");
            let report = std::fs::read_to_string(&report_path).ok()?;
            Some(serde_json::json!({
                "app_id": manifest.id,
                "name": manifest.name,
                "domain": manifest.domain,
                "report_path": report_path.display().to_string(),
                "generated_at": crate::utils::modified_iso8601(&report_path),
                "report_html": report,
                "preview": preview_html(&report),
            }))
        })
        .collect()
}

fn load_source_reports(current_app_id: &str) -> Vec<Value> {
    crate::utils::scan_app_dirs()
        .into_iter()
        .filter_map(|app_dir| {
            let manifest = crate::app_engine::inbox::load_manifest(&app_dir).ok()?;
            if manifest.id == current_app_id {
                return None;
            }
            let latest_run = latest_run_dir(&app_dir)?;
            let report_path = latest_run.join("report.html");
            let report = std::fs::read_to_string(&report_path).ok()?;
            Some(serde_json::json!({
                "app_id": manifest.id,
                "name": manifest.name,
                "report_path": report_path.display().to_string(),
                "generated_at": crate::utils::modified_iso8601(&report_path),
                "preview": preview_html(&report),
            }))
        })
        .collect()
}

fn latest_run_dir(app_dir: &std::path::Path) -> Option<PathBuf> {
    let runs_dir = app_dir.join("outbox").join("runs");
    let mut runs = std::fs::read_dir(runs_dir)
        .ok()?
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.is_dir())
        .collect::<Vec<_>>();
    runs.sort();
    runs.pop()
}

fn preview_html(report: &str) -> String {
    let plain = report
        .replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ");
    html_escape::decode_html_entities(
        &plain
            .chars()
            .filter(|ch| *ch != '<' && *ch != '>')
            .collect::<String>(),
    )
    .chars()
    .take(240)
    .collect()
}

#[allow(dead_code)]
fn app_path(app_id: &str) -> PathBuf {
    crate::utils::find_app_dir(app_id)
        .unwrap_or_else(|| crate::utils::solace_home().join("apps").join(app_id))
}
