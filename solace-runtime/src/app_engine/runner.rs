// Diagram: 12-app-engine-pipeline
use std::path::PathBuf;
use std::time::Duration;

use chrono::Utc;
use serde_json::{Map, Value};

use crate::state::{AppState, Notification};

pub async fn run_app(app_id: &str, state: &AppState) -> Result<PathBuf, String> {
    let app_dir =
        crate::utils::find_app_dir(app_id).ok_or_else(|| format!("app not found: {app_id}"))?;
    let manifest = crate::app_engine::inbox::load_manifest(&app_dir)?;
    let run_id = Utc::now().format("%Y%m%d-%H%M%S").to_string();

    let mut data = fetch_data_sources(&manifest).await?;
    data.insert(
        "config".to_string(),
        crate::app_engine::inbox::load_config(&app_dir),
    );
    data.insert(
        "inbox".to_string(),
        crate::app_engine::inbox::load_inbox_payload(&app_dir),
    );
    data.insert(
        "source_reports".to_string(),
        Value::Array(load_source_reports(app_id)),
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

    Ok(report_path)
}

async fn fetch_data_sources(
    manifest: &crate::app_engine::AppManifest,
) -> Result<Map<String, Value>, String> {
    let client = reqwest::Client::new();
    let mut data = Map::new();
    let mut items = Vec::new();

    if manifest.data_sources.is_empty() {
        if let Some(url) = &manifest.source_url {
            let remote = fetch_json(&client, url).await?;
            items.extend(normalize_items("remote", &remote, usize::MAX));
            data.insert("remote".to_string(), remote);
        }
    } else {
        for source in &manifest.data_sources {
            let json = fetch_json(&client, &source.url).await?;
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
    client
        .get(url)
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|error| error.to_string())?
        .error_for_status()
        .map_err(|error| error.to_string())?
        .json::<Value>()
        .await
        .map_err(|error| error.to_string())
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
