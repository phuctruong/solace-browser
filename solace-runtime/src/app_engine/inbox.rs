// Diagram: 13-app-inbox-outbox
use std::fs;
use std::path::Path;

use serde_json::{json, Value};

use super::AppManifest;

/// Load app manifest. Prefers manifest.md (Prime Mermaid), falls back to manifest.yaml.
pub fn load_manifest(app_dir: &Path) -> Result<AppManifest, String> {
    let md_path = app_dir.join("manifest.md");
    let yaml_path = app_dir.join("manifest.yaml");
    let yml_path = app_dir.join("manifest.yml");

    let mut manifest = if md_path.exists() {
        parse_prime_mermaid_manifest(&md_path)?
    } else {
        let manifest_path = if yaml_path.exists() { yaml_path } else { yml_path };
        let raw = fs::read_to_string(&manifest_path).map_err(|error| error.to_string())?;
        serde_yaml::from_str::<AppManifest>(&raw).map_err(|error| error.to_string())?
    };

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

/// Parse a Prime Mermaid manifest.md into an AppManifest.
/// Extracts structured data from markdown sections.
fn parse_prime_mermaid_manifest(path: &Path) -> Result<AppManifest, String> {
    let raw = fs::read_to_string(path).map_err(|e| e.to_string())?;

    let mut manifest = AppManifest::default();

    // Parse ## Identity section for key-value pairs
    for line in raw.lines() {
        let trimmed = line.trim().trim_start_matches("- ");
        if let Some(rest) = trimmed.strip_prefix("**ID**:") {
            manifest.id = rest.trim().to_string();
        } else if let Some(rest) = trimmed.strip_prefix("**Version**:") {
            manifest.version = rest.trim().to_string();
        } else if let Some(rest) = trimmed.strip_prefix("**Domain**:") {
            manifest.domain = rest.trim().to_string();
        } else if let Some(rest) = trimmed.strip_prefix("**Category**:") {
            manifest.category = rest.trim().to_string();
        } else if let Some(rest) = trimmed.strip_prefix("**Type**:") {
            manifest.app_type = rest.trim().to_string();
        }
    }

    // Parse title line: # App: Name
    for line in raw.lines() {
        if let Some(rest) = line.strip_prefix("# App:") {
            manifest.name = rest.trim().to_string();
            break;
        }
    }

    // Parse Configuration code block for schedule, tier, template
    let mut in_config = false;
    for line in raw.lines() {
        if line.trim() == "## Configuration" {
            in_config = true;
            continue;
        }
        if in_config && line.trim().starts_with("##") {
            break;
        }
        if in_config {
            let trimmed = line.trim();
            if let Some(rest) = trimmed.strip_prefix("schedule:") {
                manifest.schedule = rest.trim().trim_matches('"').to_string();
            } else if let Some(rest) = trimmed.strip_prefix("report_template:") {
                manifest.report_template = rest.trim().to_string();
            } else if let Some(rest) = trimmed.strip_prefix("tier:") {
                manifest.tier = rest.trim().to_string();
            }
        }
    }

    // Parse description from DNA line
    for line in raw.lines() {
        if line.starts_with("# DNA:") {
            manifest.description = line
                .strip_prefix("# DNA: `")
                .and_then(|s| s.strip_suffix('`'))
                .unwrap_or(line)
                .to_string();
            break;
        }
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
