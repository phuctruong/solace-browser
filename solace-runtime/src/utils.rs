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
    let apps_dir = solace_home().join("apps");
    let mut apps = Vec::new();
    let entries = match fs::read_dir(&apps_dir) {
        Ok(entries) => entries,
        Err(_) => return apps,
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            if let Ok(manifest) = crate::app_engine::inbox::load_manifest(&path) {
                apps.push(manifest);
            }
        }
    }

    apps.sort_by(|left, right| left.id.cmp(&right.id));
    apps
}

pub fn modified_iso8601(path: &Path) -> Option<String> {
    let modified = fs::metadata(path).ok()?.modified().ok()?;
    let datetime: chrono::DateTime<Utc> = modified.into();
    Some(datetime.to_rfc3339())
}
