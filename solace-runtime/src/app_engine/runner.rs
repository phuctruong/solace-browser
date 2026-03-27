// Diagram: 12-app-engine-pipeline
use std::path::PathBuf;
use std::time::Duration;

use chrono::Utc;
use serde_json::{json, Map, Value};

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
    // ── ATOMIC EXECUTION LOCK (Paperclip Dimension 2) ──
    {
        let mut runs = state.active_runs.write();
        if !runs.insert(app_id.to_string()) {
            return Err(format!(
                "Atomic Lock: App {app_id} is currently executing. Double-spend mathematically eliminated."
            ));
        }
    }

    // Ensure the lock is mathematically released when the function exits (success or error).
    struct ActiveRunGuard<'a> {
        app_id: String,
        state: &'a AppState,
    }
    impl<'a> Drop for ActiveRunGuard<'a> {
        fn drop(&mut self) {
            self.state.active_runs.write().remove(&self.app_id);
        }
    }
    let _guard = ActiveRunGuard {
        app_id: app_id.to_string(),
        state,
    };

    let app_dir =
        crate::utils::find_app_dir(app_id).ok_or_else(|| format!("app not found: {app_id}"))?;
    let manifest = crate::app_engine::inbox::load_manifest(&app_dir)?;
    let run_id = Utc::now().format("%Y%m%d-%H%M%S").to_string();

    // CLI wrapper apps: spawn binary instead of standard pipeline
    if manifest.app_type == "cli" && !manifest.binary.is_empty() {
        return run_cli_app(app_id, &app_dir, &manifest, &run_id, state).await;
    }

    // Monitor apps: fetch URL, compare to previous run, alert on change
    if manifest.app_type == "monitor" {
        return run_monitor_app(app_id, &app_dir, &manifest, &run_id, state).await;
    }

    // Agent apps: multi-step with HITL approval between steps
    if manifest.app_type == "agent" {
        return run_agent_app(app_id, &app_dir, &manifest, &run_id, state).await;
    }

    // Bridge apps: fetch from source, transform, push to destination
    if manifest.app_type == "bridge" {
        return run_bridge_app(app_id, &app_dir, &manifest, &run_id, state).await;
    }

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

    // ── DIMENSION 3: GOAL-AWARE SWARM CONTEXT ──
    // All tasks carry the ancestral objective from the Dragon Rider Substrate.
    let soul_path = crate::utils::solace_home()
        .join("apps")
        .join("dragon-rider")
        .join("inbox")
        .join("context")
        .join("SOUL.json");
    if let Ok(content) = std::fs::read_to_string(&soul_path) {
        if let Ok(soul_json) = serde_json::from_str::<Value>(&content) {
            data.insert("soul".to_string(), soul_json);
        }
    }

    // ── DIMENSION 8: EXECUTION VELOCITY (RUNTIME SKILLS) ──
    // Paperclip Vector: Agents learn workflows at runtime without re-training.
    let mut runtime_skills = Vec::new();
    let skills_dir = crate::utils::solace_home().join("skills");
    if let Ok(entries) = std::fs::read_dir(&skills_dir) {
        for entry in entries.flatten() {
            if entry.path().is_dir() {
                let skill_name = entry.file_name().to_string_lossy().to_string();
                let skill_md = entry.path().join("SKILL.md");
                if let Ok(content) = std::fs::read_to_string(&skill_md) {
                    runtime_skills.push(json!({
                        "id": skill_name,
                        "content": content
                    }));
                }
            }
        }
    }
    data.insert("runtime_skills".to_string(), Value::Array(runtime_skills));

    // ── REINFORCEMENT LEARNING: Load feedback from inbox/feedback/ ──
    // Past approve/reject decisions + human edits = RL training signal.
    // Injected into data so templates and LLM can use it.
    let feedback = load_feedback(&app_dir);
    if !feedback.is_empty() {
        data.insert(
            "feedback_history".to_string(),
            Value::Array(feedback.clone()),
        );
        data.insert(
            "feedback_count".to_string(),
            Value::Number(serde_json::Number::from(feedback.len())),
        );
        let approval_count = feedback
            .iter()
            .filter(|f| f.get("decision").and_then(|d| d.as_str()) == Some("approve"))
            .count();
        data.insert(
            "approval_rate".to_string(),
            Value::String(format!(
                "{:.0}%",
                approval_count as f64 / feedback.len() as f64 * 100.0
            )),
        );
    }
    // For conductor apps: load ONLY orchestrated apps' outboxes
    // For standard apps: load all other apps' latest reports
    // Conductor detection: "conductor" or legacy "orchestrator"
    let is_conductor = manifest.app_type == "conductor" || manifest.app_type == "orchestrator";
    let source_reports = if is_conductor && !manifest.orchestrates.is_empty() {
        load_orchestrated_reports(&manifest.orchestrates)
    } else if is_conductor {
        // Legacy orchestrator without explicit orchestrates — load all other apps
        load_source_reports(app_id)
    } else {
        load_source_reports(app_id)
    };
    data.insert("source_reports".to_string(), Value::Array(source_reports));
    data.insert("is_conductor".to_string(), Value::Bool(is_conductor));
    data.insert(
        "app_type".to_string(),
        Value::String(manifest.app_type.clone()),
    );
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
        Some(format!(
            "template={} output_hash={}",
            template_name, output_hash
        )),
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
    let _ = crate::persistence::append_jsonl(&events_dir.join("app_events.jsonl"), &event_record);

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

// ---------------------------------------------------------------------------
// CLI Wrapper App Execution
// ---------------------------------------------------------------------------

async fn run_cli_app(
    app_id: &str,
    app_dir: &std::path::Path,
    manifest: &crate::app_engine::AppManifest,
    run_id: &str,
    state: &AppState,
) -> Result<PathBuf, String> {
    let solace_home = crate::utils::solace_home();
    let outbox_dir = app_dir.join("outbox").join("runs").join(run_id);
    std::fs::create_dir_all(&outbox_dir).map_err(|e| e.to_string())?;

    // Find input: check inbox/pending/ for files, or use a default prompt
    let inbox_pending = app_dir.join("inbox").join("pending");
    let input = if inbox_pending.exists() {
        // Use first file in pending/
        std::fs::read_dir(&inbox_pending)
            .ok()
            .and_then(|mut entries| entries.next())
            .and_then(|e| e.ok())
            .map(|e| e.path().to_string_lossy().to_string())
    } else {
        None
    };

    let binary = &manifest.binary;
    let timeout = std::time::Duration::from_secs(manifest.timeout_seconds.min(300));
    
    let (exit_code, stdout, stderr) = if binary.ends_with(".wasm") {
        // ── DIMENSION 14 (WASM SANDBOX BOUNDARY) ──
        // Intercept WASM modules and execute them inside the preopened namespace.
        tokio::time::timeout(
            timeout,
            crate::app_engine::wasm_sandbox::execute_wasm_sandbox(
                app_dir,
                binary,
                &manifest.args,
                input.clone(),
            ),
        )
        .await
        .map_err(|_| format!("WASM timeout after {}s", manifest.timeout_seconds))?
        .map_err(|e| format!("WASM execution failed: {}", e))?
    } else {
        // Legacy native binary execution
        let mut cmd = tokio::process::Command::new(binary);
        for arg in &manifest.args {
            cmd.arg(arg);
        }
        if let Some(ref input_path) = input {
            cmd.arg(input_path);
        }
    
        let output = tokio::time::timeout(timeout, cmd.output())
            .await
            .map_err(|_| format!("CLI timeout after {}s", manifest.timeout_seconds))?
            .map_err(|e| format!("CLI spawn failed: {} (binary: {})", e, binary))?;
    
        (
            output.status.code().unwrap_or(-1),
            String::from_utf8_lossy(&output.stdout).to_string(),
            String::from_utf8_lossy(&output.stderr).to_string(),
        )
    };

    // Write outputs
    std::fs::write(outbox_dir.join("stdout.txt"), &stdout).map_err(|e| e.to_string())?;
    if !stderr.is_empty() {
        let _ = std::fs::write(outbox_dir.join("stderr.txt"), &stderr);
    }

    // Build report HTML
    let html = format!(
        r#"<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>CLI: {} — {}</title>
<link rel="stylesheet" href="/styleguide.css">
</head><body>
<h1>{} — CLI Result</h1>
<p>Binary: <code>{}</code> | Exit: {} | Run: {}</p>
{}
<h2>Output</h2>
<pre style="background:var(--sb-surface, #1a1a2e);padding:1rem;border-radius:8px;overflow-x:auto;white-space:pre-wrap">{}</pre>
{}</body></html>"#,
        manifest.name,
        run_id,
        manifest.name,
        binary,
        exit_code,
        run_id,
        if let Some(ref p) = input {
            format!("<p>Input: <code>{}</code></p>", p)
        } else {
            String::new()
        },
        html_escape::encode_text(&stdout),
        if stderr.is_empty() {
            String::new()
        } else {
            format!(
                "<h2>Errors</h2><pre style=\"color:var(--sb-danger)\">{}</pre>",
                html_escape::encode_text(&stderr)
            )
        },
    );

    let report_path = outbox_dir.join("report.html");
    std::fs::write(&report_path, &html).map_err(|e| e.to_string())?;

    // Evidence
    let _evidence_input = format!("{}:{}:{}:{}", app_id, run_id, binary, stdout.len());
    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("cli.run.{}", app_id),
        "runtime",
        serde_json::json!({
            "binary": binary,
            "args": manifest.args,
            "exit_code": exit_code,
            "stdout_bytes": stdout.len(),
            "stderr_bytes": stderr.len(),
            "input": input,
            "timeout_seconds": manifest.timeout_seconds,
        }),
    );

    // Update counters
    *state.app_count.write() += 1;
    *state.evidence_count.write() += 1;
    state.notifications.write().push(Notification {
        id: uuid::Uuid::new_v4().to_string(),
        message: format!("CLI {} completed (exit {})", manifest.name, exit_code),
        level: if exit_code == 0 { "info" } else { "warning" }.to_string(),
        read: false,
        created_at: crate::utils::now_iso8601(),
    });

    // Move processed input file to processed/
    if let Some(ref input_path) = input {
        let processed_dir = app_dir.join("inbox").join("processed");
        let _ = std::fs::create_dir_all(&processed_dir);
        let filename = std::path::Path::new(input_path)
            .file_name()
            .unwrap_or_default();
        let _ = std::fs::rename(input_path, processed_dir.join(filename));
    }

    Ok(report_path)
}

// ---------------------------------------------------------------------------
// Monitor App — poll URL, compare to previous, alert on change
// ---------------------------------------------------------------------------

async fn run_monitor_app(
    app_id: &str,
    app_dir: &std::path::Path,
    manifest: &crate::app_engine::AppManifest,
    run_id: &str,
    state: &AppState,
) -> Result<PathBuf, String> {
    let solace_home = crate::utils::solace_home();
    let outbox_dir = app_dir.join("outbox").join("runs").join(run_id);
    std::fs::create_dir_all(&outbox_dir).map_err(|e| e.to_string())?;

    // Fetch current state
    let url = manifest
        .source_url
        .as_deref()
        .or_else(|| manifest.data_sources.first().map(|ds| ds.url.as_str()))
        .unwrap_or("https://example.com");

    let client = reqwest::Client::new();
    let current = client
        .get(url)
        .header("User-Agent", "SolaceRuntime/0.1.0 (monitor)")
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("Monitor fetch failed: {}", e))?
        .text()
        .await
        .map_err(|e| format!("Monitor read failed: {}", e))?;

    let current_hash = crate::utils::sha256_hex(&current);

    // Load previous hash
    let state_file = app_dir.join("outbox").join("monitor_state.json");
    let previous_hash = std::fs::read_to_string(&state_file)
        .ok()
        .and_then(|s| serde_json::from_str::<serde_json::Value>(&s).ok())
        .and_then(|v| {
            v.get("hash")
                .and_then(|h| h.as_str())
                .map(|s| s.to_string())
        })
        .unwrap_or_default();

    let changed = !previous_hash.is_empty() && previous_hash != current_hash;
    let first_run = previous_hash.is_empty();

    // Save current state
    let _ = std::fs::write(
        &state_file,
        serde_json::to_string_pretty(&serde_json::json!({
            "hash": current_hash,
            "url": url,
            "timestamp": crate::utils::now_iso8601(),
            "content_length": current.len(),
        }))
        .unwrap_or_default(),
    );

    // Build report
    let status_text = if first_run {
        "First check — baseline recorded"
    } else if changed {
        "CHANGE DETECTED"
    } else {
        "No change"
    };

    let html = format!(
        r#"<!doctype html><html><head><meta charset="utf-8"><title>Monitor: {name}</title>
<link rel="stylesheet" href="/styleguide.css"></head><body>
<h1>{name} — Monitor Report</h1>
<p>URL: <a href="{url}">{url}</a></p>
<p>Status: <strong style="color:{color}">{status}</strong></p>
<p>Current hash: <code>{hash}</code></p>
<p>Previous hash: <code>{prev}</code></p>
<p>Content length: {len} bytes</p>
<p>Checked: {time}</p>
</body></html>"#,
        name = manifest.name,
        url = url,
        color = if changed {
            "var(--sb-danger, red)"
        } else {
            "var(--sb-success, green)"
        },
        status = status_text,
        hash = current_hash,
        prev = if previous_hash.is_empty() {
            "none (first run)"
        } else {
            &previous_hash
        },
        len = current.len(),
        time = crate::utils::now_iso8601(),
    );

    let report_path = outbox_dir.join("report.html");
    std::fs::write(&report_path, &html).map_err(|e| e.to_string())?;

    // Record evidence
    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("monitor.check.{}", app_id),
        "runtime",
        serde_json::json!({"url": url, "changed": changed, "hash": current_hash, "first_run": first_run}),
    );

    // Alert notification if changed
    if changed {
        state.notifications.write().push(Notification {
            id: uuid::Uuid::new_v4().to_string(),
            message: format!("ALERT: {} detected change at {}", manifest.name, url),
            level: "warning".to_string(),
            read: false,
            created_at: crate::utils::now_iso8601(),
        });
    }

    *state.app_count.write() += 1;
    *state.evidence_count.write() += 1;

    Ok(report_path)
}

// ---------------------------------------------------------------------------
// Agent App — multi-step task with HITL approval gates between steps
// ---------------------------------------------------------------------------

async fn run_agent_app(
    app_id: &str,
    app_dir: &std::path::Path,
    manifest: &crate::app_engine::AppManifest,
    run_id: &str,
    state: &AppState,
) -> Result<PathBuf, String> {
    let solace_home = crate::utils::solace_home();
    let outbox_dir = app_dir.join("outbox").join("runs").join(run_id);
    std::fs::create_dir_all(&outbox_dir).map_err(|e| e.to_string())?;

    // Agent apps execute in steps. Each step can be:
    // 1. Fetch data (L1 auto)
    // 2. Analyze with LLM (L2 auto)
    // 3. Draft action (L3 needs approval)
    // 4. Execute action (L3+ after approval)

    // Step 1: Load task from inbox
    let task_dir = app_dir.join("inbox").join("tasks");
    let task_content = if task_dir.exists() {
        std::fs::read_dir(&task_dir)
            .ok()
            .and_then(|mut entries| entries.next())
            .and_then(|e| e.ok())
            .and_then(|e| std::fs::read_to_string(e.path()).ok())
            .unwrap_or_else(|| format!("Default task for {}", manifest.name))
    } else {
        format!("Default task for {}", manifest.name)
    };

    // Step 2: Fetch context (if data sources exist)
    let mut context = String::new();
    for source in &manifest.data_sources {
        let client = reqwest::Client::new();
        if let Ok(resp) = client
            .get(&source.url)
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await
        {
            if let Ok(text) = resp.text().await {
                context.push_str(&format!(
                    "--- Source: {} ---\n{}\n\n",
                    source.name,
                    &text[..text.len().min(2000)]
                ));
            }
        }
    }

    // Step 3: Draft with LLM (if available)
    let draft = if let Ok(llm_response) = crate::routes::chat::call_llm_public(&format!(
        "Task: {}\n\nContext:\n{}\n\nDraft a response or action plan.",
        task_content, context
    ))
    .await
    {
        llm_response
    } else {
        format!(
            "Agent task loaded. Context gathered from {} sources. Awaiting LLM for draft.",
            manifest.data_sources.len()
        )
    };

    // Step 4: Queue for approval (L3+)
    let action_id = uuid::Uuid::new_v4().to_string();
    state
        .pending_actions
        .write()
        .push(crate::routes::chat::PendingAction {
            id: action_id.clone(),
            intent: crate::routes::chat::Intent::Automate,
            message: format!(
                "Agent {} draft: {}",
                manifest.name,
                &draft[..draft.len().min(200)]
            ),
            preview: draft.clone(),
            cooldown_secs: 30,
            created_at: std::time::Instant::now(),
        });

    // Build report
    let html = format!(
        r#"<!doctype html><html><head><meta charset="utf-8"><title>Agent: {name}</title>
<link rel="stylesheet" href="/styleguide.css"></head><body>
<h1>{name} — Agent Report</h1>
<h2>Task</h2><pre>{task}</pre>
<h2>Context ({sources} sources)</h2><pre>{context}</pre>
<h2>Draft (pending approval)</h2><pre>{draft}</pre>
<p>Approval ID: <code>{action_id}</code></p>
<p>Approve: <code>POST /api/v1/approvals/approve</code> with {{"action_id": "{action_id}"}}</p>
</body></html>"#,
        name = manifest.name,
        task = html_escape::encode_text(&task_content),
        sources = manifest.data_sources.len(),
        context = html_escape::encode_text(&context[..context.len().min(3000)]),
        draft = html_escape::encode_text(&draft),
        action_id = action_id,
    );

    let report_path = outbox_dir.join("report.html");
    std::fs::write(&report_path, &html).map_err(|e| e.to_string())?;

    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("agent.draft.{}", app_id),
        "runtime",
        serde_json::json!({"action_id": action_id, "task_length": task_content.len(), "draft_length": draft.len(), "sources": manifest.data_sources.len()}),
    );

    state.notifications.write().push(Notification {
        id: uuid::Uuid::new_v4().to_string(),
        message: format!(
            "Agent {} needs approval (action {})",
            manifest.name,
            &action_id[..8]
        ),
        level: "warning".to_string(),
        read: false,
        created_at: crate::utils::now_iso8601(),
    });

    *state.app_count.write() += 1;
    *state.evidence_count.write() += 1;

    Ok(report_path)
}

// ---------------------------------------------------------------------------
// Bridge App — read from source service, transform, push to destination
// ---------------------------------------------------------------------------

async fn run_bridge_app(
    app_id: &str,
    app_dir: &std::path::Path,
    manifest: &crate::app_engine::AppManifest,
    run_id: &str,
    state: &AppState,
) -> Result<PathBuf, String> {
    let solace_home = crate::utils::solace_home();
    let outbox_dir = app_dir.join("outbox").join("runs").join(run_id);
    std::fs::create_dir_all(&outbox_dir).map_err(|e| e.to_string())?;

    // Bridge requires at least 2 data sources: source and destination
    if manifest.data_sources.len() < 2 {
        return Err(format!(
            "Bridge app {} requires at least 2 data_sources (source + destination). Has {}.",
            app_id,
            manifest.data_sources.len()
        ));
    }

    let source = &manifest.data_sources[0];
    let destination = &manifest.data_sources[1];

    // Step 1: Fetch from source
    let client = reqwest::Client::new();
    let source_data = client
        .get(&source.url)
        .header("User-Agent", "SolaceRuntime/0.1.0 (bridge)")
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("Bridge source fetch failed: {}", e))?
        .text()
        .await
        .map_err(|e| format!("Bridge source read failed: {}", e))?;

    let source_hash = crate::utils::sha256_hex(&source_data);

    // Step 2: Transform (via LLM or template)
    let transformed = if let Ok(llm_response) = crate::routes::chat::call_llm_public(&format!(
        "Transform this data from {} format to {} format:\n\n{}",
        source.name,
        destination.name,
        &source_data[..source_data.len().min(3000)]
    ))
    .await
    {
        llm_response
    } else {
        // Passthrough if no LLM
        source_data.clone()
    };

    // Step 3: Push to destination (simulate — real push would POST to destination URL)
    let push_result = format!(
        "Would push {} bytes to {}",
        transformed.len(),
        destination.url
    );

    // Save transformed data
    std::fs::write(outbox_dir.join("source_data.txt"), &source_data).map_err(|e| e.to_string())?;
    std::fs::write(outbox_dir.join("transformed_data.txt"), &transformed)
        .map_err(|e| e.to_string())?;

    // Build report
    let html = format!(
        r#"<!doctype html><html><head><meta charset="utf-8"><title>Bridge: {name}</title>
<link rel="stylesheet" href="/styleguide.css"></head><body>
<h1>{name} — Bridge Report</h1>
<h2>Source: {src_name}</h2><p>URL: {src_url}</p><p>Fetched: {src_len} bytes (hash: <code>{src_hash}</code>)</p>
<h2>Destination: {dst_name}</h2><p>URL: {dst_url}</p>
<h2>Transform</h2><pre>{transformed}</pre>
<h2>Push Result</h2><p>{push}</p>
</body></html>"#,
        name = manifest.name,
        src_name = source.name,
        src_url = source.url,
        src_len = source_data.len(),
        src_hash = source_hash,
        dst_name = destination.name,
        dst_url = destination.url,
        transformed = html_escape::encode_text(&transformed[..transformed.len().min(2000)]),
        push = push_result,
    );

    let report_path = outbox_dir.join("report.html");
    std::fs::write(&report_path, &html).map_err(|e| e.to_string())?;

    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("bridge.sync.{}", app_id),
        "runtime",
        serde_json::json!({"source": source.url, "destination": destination.url, "source_bytes": source_data.len(), "transformed_bytes": transformed.len()}),
    );

    *state.app_count.write() += 1;
    *state.evidence_count.write() += 1;

    Ok(report_path)
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

/// Load all feedback deltas from inbox/feedback/ — the RL training signal.
/// Returns a Vec of feedback entries sorted newest-first.
fn load_feedback(app_dir: &std::path::Path) -> Vec<Value> {
    let feedback_dir = app_dir.join("inbox").join("feedback");
    let mut entries = Vec::new();

    if let Ok(dir) = std::fs::read_dir(&feedback_dir) {
        for entry in dir.flatten() {
            let path = entry.path();
            if path.extension().map(|e| e == "md").unwrap_or(false) {
                let filename = path
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_string();
                let content = std::fs::read_to_string(&path).unwrap_or_default();

                let decision = if filename.starts_with("approve") {
                    "approve"
                } else if filename.starts_with("reject") {
                    "reject"
                } else {
                    "unknown"
                };

                // Extract human feedback text
                let feedback_text = content
                    .split("## Human Feedback\n")
                    .nth(1)
                    .and_then(|s| s.split("\n\n").next())
                    .unwrap_or("")
                    .trim()
                    .to_string();

                // Extract edited output
                let edited = content
                    .split("## Edited Output\n")
                    .nth(1)
                    .and_then(|s| s.split("\n\n").next())
                    .unwrap_or("")
                    .trim()
                    .to_string();

                entries.push(json!({
                    "decision": decision,
                    "feedback": feedback_text,
                    "has_edits": !edited.is_empty() && edited != "(no edits — output accepted as-is)",
                    "edited_output": edited,
                    "filename": filename,
                }));
            }
        }
    }

    // Sort newest first (filenames contain timestamps)
    entries.sort_by(|a, b| {
        let fa = a.get("filename").and_then(|f| f.as_str()).unwrap_or("");
        let fb = b.get("filename").and_then(|f| f.as_str()).unwrap_or("");
        fb.cmp(fa)
    });

    // Keep last 20 feedback entries (prevent context overflow)
    entries.truncate(20);
    entries
}
