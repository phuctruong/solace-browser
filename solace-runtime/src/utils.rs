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
    let apps_dir = solace_home().join("apps");
    let entries = match fs::read_dir(&apps_dir) {
        Ok(entries) => entries,
        Err(_) => return Vec::new(),
    };

    let mut app_dirs = Vec::new();
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        if has_manifest(&path) {
            app_dirs.push(path);
            continue;
        }
        if let Ok(children) = fs::read_dir(&path) {
            for child in children.flatten() {
                let child_path = child.path();
                if child_path.is_dir() && has_manifest(&child_path) {
                    app_dirs.push(child_path);
                }
            }
        }
    }
    app_dirs.sort();
    app_dirs
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
    path.join("manifest.yaml").is_file() || path.join("manifest.yml").is_file()
}

pub fn modified_iso8601(path: &Path) -> Option<String> {
    let modified = fs::metadata(path).ok()?.modified().ok()?;
    let datetime: chrono::DateTime<Utc> = modified.into();
    Some(datetime.to_rfc3339())
}
