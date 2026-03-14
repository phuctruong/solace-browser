// Diagram: 13-app-inbox-outbox
use std::fs;
use std::path::Path;

use serde_json::{json, Value};

use super::AppManifest;

pub fn load_manifest(app_dir: &Path) -> Result<AppManifest, String> {
    let yaml_path = app_dir.join("manifest.yaml");
    let yml_path = app_dir.join("manifest.yml");
    let manifest_path = if yaml_path.exists() {
        yaml_path
    } else {
        yml_path
    };
    let raw = fs::read_to_string(&manifest_path).map_err(|error| error.to_string())?;
    let mut manifest: AppManifest =
        serde_yaml::from_str(&raw).map_err(|error| error.to_string())?;
    if manifest.id.is_empty() {
        manifest.id = app_dir
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("app")
            .to_string();
    }
    if manifest.name.is_empty() {
        manifest.name = manifest.id.clone();
    }
    if manifest.version.is_empty() {
        manifest.version = "0.1.0".to_string();
    }
    if manifest.domain.is_empty() {
        manifest.domain = "general".to_string();
    }
    Ok(manifest)
}

pub fn load_config(app_dir: &Path) -> Value {
    let path = app_dir.join("config.json");
    match fs::read_to_string(path) {
        Ok(raw) => serde_json::from_str(&raw).unwrap_or_else(|_| json!({})),
        Err(_) => json!({}),
    }
}

pub fn load_inbox_payload(app_dir: &Path) -> Value {
    let inbox_dir = app_dir.join("inbox");
    let mut files = Vec::new();
    if let Ok(entries) = fs::read_dir(&inbox_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                files.push(json!({
                    "name": path.file_name().and_then(|name| name.to_str()).unwrap_or_default(),
                    "modified_at": crate::utils::modified_iso8601(&path),
                }));
            }
        }
    }

    let input_path = inbox_dir.join("input.json");
    let payload = match fs::read_to_string(&input_path) {
        Ok(raw) => serde_json::from_str(&raw).unwrap_or_else(|_| json!({})),
        Err(_) => json!({}),
    };

    json!({
        "payload": payload,
        "files": files,
    })
}
