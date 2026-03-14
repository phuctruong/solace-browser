use std::path::PathBuf;

use serde::Serialize;
use serde_json::{json, Value};

use crate::state::{AppState, Notification};

#[derive(Serialize)]
pub struct AppRunResult {
    pub app_id: String,
    pub app_name: String,
    pub output_dir: String,
    pub evidence_hash: String,
    pub fetched_remote: bool,
}

pub async fn run_app(app_id: &str, state: &AppState) -> Result<AppRunResult, String> {
    let app_dir = crate::utils::solace_home().join("apps").join(app_id);
    let manifest = crate::app_engine::inbox::load_manifest(&app_dir)?;
    let config = crate::app_engine::inbox::load_config(&app_dir);
    let inbox = crate::app_engine::inbox::load_inbox_payload(&app_dir);
    let remote = fetch_remote_data(manifest.source_url.clone()).await?;
    let context = json!({
        "manifest": manifest,
        "config": config,
        "inbox": inbox,
        "remote": remote,
        "generated_at": crate::utils::now_iso8601(),
    });

    let manifest = crate::app_engine::inbox::load_manifest(&app_dir)?;
    let report = crate::app_engine::template::render_report(&manifest, &app_dir, &context)?;
    let evidence = crate::evidence::record_event(
        &crate::utils::solace_home(),
        "app_run",
        "app_engine",
        json!({"app_id": app_id, "name": manifest.name}),
    )?;
    let run_dir =
        crate::app_engine::outbox::write_run_output(app_id, &report, &evidence, &context)?;

    *state.app_count.write() += 1;
    *state.evidence_count.write() += 1;
    state.notifications.write().push(Notification {
        id: uuid::Uuid::new_v4().to_string(),
        message: format!("App {} completed", manifest.name),
        level: "info".to_string(),
        read: false,
        created_at: crate::utils::now_iso8601(),
    });

    Ok(AppRunResult {
        app_id: app_id.to_string(),
        app_name: manifest.name,
        output_dir: run_dir.display().to_string(),
        evidence_hash: evidence.hash,
        fetched_remote: remote_present(&context),
    })
}

async fn fetch_remote_data(source_url: Option<String>) -> Result<Value, String> {
    let Some(url) = source_url else {
        return Ok(Value::Null);
    };
    let response = reqwest::get(url).await.map_err(|error| error.to_string())?;
    let text = response.text().await.map_err(|error| error.to_string())?;
    match serde_json::from_str(&text) {
        Ok(json) => Ok(json),
        Err(_) => Ok(json!({"text": text})),
    }
}

fn remote_present(context: &Value) -> bool {
    context
        .get("remote")
        .is_some_and(|value| !value.is_null() && value != &json!({}))
}

#[allow(dead_code)]
fn app_path(app_id: &str) -> PathBuf {
    crate::utils::solace_home().join("apps").join(app_id)
}
