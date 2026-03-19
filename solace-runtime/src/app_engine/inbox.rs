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

    let mut manifest = if yaml_path.exists() {
        // Prefer YAML when it exists (has proper data_sources, orchestrates, etc.)
        let raw = fs::read_to_string(&yaml_path).map_err(|error| error.to_string())?;
        serde_yaml::from_str::<AppManifest>(&raw).map_err(|error| error.to_string())?
    } else if md_path.exists() {
        parse_prime_mermaid_manifest(&md_path)?
    } else {
        let manifest_path = yml_path;
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

    let mut manifest = AppManifest {
        timeout_seconds: 60, // Default timeout for CLI apps
        ..AppManifest::default()
    };

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
        } else if let Some(rest) = trimmed.strip_prefix("**Orchestrates**:") {
            // Parse comma-separated list of app IDs
            manifest.orchestrates = rest
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();
        } else if let Some(rest) = trimmed.strip_prefix("**Safety**:") {
            let _ = rest;
        } else if let Some(rest) = trimmed.strip_prefix("**Binary**:") {
            manifest.binary = rest.trim().to_string();
        } else if let Some(rest) = trimmed.strip_prefix("**Args**:") {
            manifest.args = rest.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
        } else if let Some(rest) = trimmed.strip_prefix("**Input Type**:") {
            manifest.input_type = rest.trim().to_string();
        } else if let Some(rest) = trimmed.strip_prefix("**Timeout**:") {
            manifest.timeout_seconds = rest.trim().parse().unwrap_or(60);
        } else if let Some(rest) = trimmed.strip_prefix("**Visibility**:") {
            manifest.visibility = rest.trim().to_string();
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

    // Parse Data Sources from ## Data Sources code block
    // Format:
    //   sources:
    //     - name: topstories
    //       url: https://example.com/api
    //       type: json
    //       limit: 30
    let mut in_sources = false;
    let mut current_source: Option<super::DataSource> = None;
    for line in raw.lines() {
        let trimmed = line.trim();
        if trimmed == "## Data Sources" {
            in_sources = true;
            continue;
        }
        if in_sources && trimmed.starts_with("##") {
            break;
        }
        if !in_sources {
            continue;
        }
        if trimmed.starts_with("- name:") {
            // Save previous source if any
            if let Some(src) = current_source.take() {
                if !src.url.is_empty() {
                    manifest.data_sources.push(src);
                }
            }
            current_source = Some(super::DataSource {
                name: trimmed.strip_prefix("- name:").unwrap_or("").trim().to_string(),
                url: String::new(),
                source_type: "json".to_string(),
                limit: 25,
            });
        } else if let Some(ref mut src) = current_source {
            if let Some(rest) = trimmed.strip_prefix("url:") {
                src.url = rest.trim().to_string();
            } else if let Some(rest) = trimmed.strip_prefix("type:") {
                src.source_type = rest.trim().to_string();
            } else if let Some(rest) = trimmed.strip_prefix("limit:") {
                src.limit = rest.trim().parse().unwrap_or(25);
            }
        }
    }
    // Don't forget the last source
    if let Some(src) = current_source {
        if !src.url.is_empty() {
            manifest.data_sources.push(src);
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn parse_prime_mermaid_manifest_identity() {
        let dir = tempfile::tempdir().unwrap();
        let manifest = dir.path().join("manifest.md");
        let mut f = std::fs::File::create(&manifest).unwrap();
        write!(f, r#"<!-- Diagram: 12-app-engine-pipeline -->
# App: Test App
# DNA: `test = fetch → render → seal`
# Auth: 65537 | Status: installed | Tier: free

## Identity
- **ID**: test-app
- **Version**: 2.0.0
- **Domain**: example.com
- **Category**: research
- **Type**: standard

## Configuration
```
schedule: "0 8 * * *"
tier: free
report_template: feed-digest
```
"#).unwrap();

        let result = parse_prime_mermaid_manifest(&manifest).unwrap();
        assert_eq!(result.id, "test-app");
        assert_eq!(result.name, "Test App");
        assert_eq!(result.version, "2.0.0");
        assert_eq!(result.domain, "example.com");
        assert_eq!(result.category, "research");
        assert_eq!(result.schedule, "0 8 * * *");
        assert_eq!(result.report_template, "feed-digest");
    }

    #[test]
    fn parse_prime_mermaid_data_sources() {
        let dir = tempfile::tempdir().unwrap();
        let manifest = dir.path().join("manifest.md");
        let mut f = std::fs::File::create(&manifest).unwrap();
        write!(f, r#"# App: Feed App

## Identity
- **ID**: feed-app

## Data Sources
```
sources:
  - name: api-data
    url: https://api.example.com/items.json
    type: json
    limit: 50
  - name: rss-feed
    url: https://example.com/feed.rss
    type: rss
    limit: 10
```
"#).unwrap();

        let result = parse_prime_mermaid_manifest(&manifest).unwrap();
        assert_eq!(result.data_sources.len(), 2);
        assert_eq!(result.data_sources[0].name, "api-data");
        assert_eq!(result.data_sources[0].url, "https://api.example.com/items.json");
        assert_eq!(result.data_sources[0].limit, 50);
        assert_eq!(result.data_sources[1].name, "rss-feed");
        assert_eq!(result.data_sources[1].url, "https://example.com/feed.rss");
        assert_eq!(result.data_sources[1].source_type, "rss");
        assert_eq!(result.data_sources[1].limit, 10);
    }

    #[test]
    fn parse_prime_mermaid_no_data_sources() {
        let dir = tempfile::tempdir().unwrap();
        let manifest = dir.path().join("manifest.md");
        let mut f = std::fs::File::create(&manifest).unwrap();
        write!(f, "# App: Simple\n\n## Identity\n- **ID**: simple\n").unwrap();

        let result = parse_prime_mermaid_manifest(&manifest).unwrap();
        assert!(result.data_sources.is_empty());
    }

    #[test]
    fn load_manifest_prefers_md_over_missing_yaml() {
        let dir = tempfile::tempdir().unwrap();
        let manifest = dir.path().join("manifest.md");
        let mut f = std::fs::File::create(&manifest).unwrap();
        write!(f, "# App: MD App\n\n## Identity\n- **ID**: md-app\n- **Version**: 3.0.0\n").unwrap();

        let result = load_manifest(dir.path()).unwrap();
        assert_eq!(result.id, "md-app");
        assert_eq!(result.version, "3.0.0");
    }
}
