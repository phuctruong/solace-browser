// Diagram: 05-solace-runtime-architecture
use std::fs;
use std::path::{Path, PathBuf};

use chrono::Utc;
use sha2::{Digest, Sha256};

pub fn solace_home() -> PathBuf {
    match std::env::var("SOLACE_HOME") {
        Ok(path) => PathBuf::from(path),
        Err(_) => match std::env::var("HOME") {
            Ok(home) => PathBuf::from(home).join(".solace"),
            Err(_) => PathBuf::from(".solace"),
        },
    }
}

pub fn sha256_hex(input: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    format!("{:x}", hasher.finalize())
}

pub fn sha256_bytes(input: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input);
    format!("{:x}", hasher.finalize())
}

pub fn now_iso8601() -> String {
    Utc::now().to_rfc3339()
}

pub fn scan_apps() -> Vec<crate::app_engine::AppManifest> {
    let mut apps = Vec::new();
    for path in scan_app_dirs() {
        if let Ok(manifest) = crate::app_engine::inbox::load_manifest(&path) {
            apps.push(manifest);
        }
    }

    apps.sort_by(|left, right| left.id.cmp(&right.id));
    apps
}

pub fn scan_app_dirs() -> Vec<PathBuf> {
    let mut app_dirs = Vec::new();

    // Scan all app directories: production (~/.solace/apps/) + development
    for search_dir in app_search_paths() {
        let entries = match fs::read_dir(&search_dir) {
            Ok(entries) => entries,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if !path.is_dir() {
                continue;
            }
            if has_manifest(&path) {
                app_dirs.push(path);
                continue;
            }
            // Check subdirectories (domain/app-id structure)
            if let Ok(children) = fs::read_dir(&path) {
                for child in children.flatten() {
                    let child_path = child.path();
                    if child_path.is_dir() && has_manifest(&child_path) {
                        app_dirs.push(child_path);
                    }
                }
            }
        }
    }

    // Dedup by directory name (production overrides development)
    app_dirs.sort();
    app_dirs.dedup_by(|a, b| a.file_name() == b.file_name());
    app_dirs
}

fn app_search_paths() -> Vec<PathBuf> {
    let mut paths = vec![solace_home().join("apps")];

    // Development: SOLACE_CLI_ROOT env var
    if let Ok(cli_root) = std::env::var("SOLACE_CLI_ROOT") {
        let dev = PathBuf::from(cli_root).join("data").join("default").join("apps");
        if dev.is_dir() {
            paths.push(dev);
        }
    }

    // Fallback: dev path relative to CARGO_MANIFEST_DIR (cross-platform)
    let dev_fallback = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|p| p.parent())
        .unwrap_or(std::path::Path::new("."))
        .join("solace-cli/data/default/apps");
    if dev_fallback.is_dir() && !paths.iter().any(|p| p == &dev_fallback) {
        paths.push(dev_fallback);
    }

    paths
}

pub fn find_app_dir(app_id: &str) -> Option<PathBuf> {
    let direct = solace_home().join("apps").join(app_id);
    if has_manifest(&direct) {
        return Some(direct);
    }

    scan_app_dirs().into_iter().find(|path| {
        path.file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name == app_id)
            || crate::app_engine::inbox::load_manifest(path)
                .map(|manifest| manifest.id == app_id)
                .unwrap_or(false)
    })
}

fn has_manifest(path: &Path) -> bool {
    path.join("manifest.yaml").is_file()
        || path.join("manifest.yml").is_file()
        || path.join("manifest.md").is_file()
}

pub fn modified_iso8601(path: &Path) -> Option<String> {
    let modified = fs::metadata(path).ok()?.modified().ok()?;
    let datetime: chrono::DateTime<Utc> = modified.into();
    Some(datetime.to_rfc3339())
}
