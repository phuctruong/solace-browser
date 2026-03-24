// Diagram: 05-solace-runtime-architecture
use std::fs;
use std::path::{Path, PathBuf};

use chrono::Utc;
use sha2::{Digest, Sha256};

pub fn solace_home() -> PathBuf {
    resolve_solace_home_from_env(|key| std::env::var(key).ok(), cfg!(windows))
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
        if let Ok(mut manifest) = crate::app_engine::inbox::load_manifest(&path) {
            // Default empty domain to "localhost" (home domain)
            if manifest.domain.is_empty() || manifest.domain == "general" {
                manifest.domain = "localhost".to_string();
            }
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

    // Production: apps bundled next to or near the binary (MSI/deb install)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(bin_dir) = exe.parent() {
            // Search multiple possible layouts
            let candidates = [
                // Flat MSI: <install_dir>/data/default/apps/
                bin_dir.join("data").join("default").join("apps"),
                // Bundle subdir: <install_dir>/solace-browser-release/data/default/apps/
                bin_dir
                    .join("solace-browser-release")
                    .join("data")
                    .join("default")
                    .join("apps"),
                // Linux .deb: <install_dir>/../data/default/apps/
                bin_dir
                    .parent()
                    .unwrap_or(bin_dir)
                    .join("data")
                    .join("default")
                    .join("apps"),
                // Windows Program Files: check if apps are alongside the binary
                bin_dir.join("apps"),
            ];
            for candidate in &candidates {
                if candidate.is_dir() && !paths.iter().any(|p| p == candidate) {
                    paths.push(candidate.clone());
                }
            }
        }
    }

    // Development: SOLACE_CLI_ROOT env var
    if let Ok(cli_root) = std::env::var("SOLACE_CLI_ROOT") {
        let dev = PathBuf::from(cli_root)
            .join("data")
            .join("default")
            .join("apps");
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

fn resolve_solace_home_from_env<F>(get_env: F, _is_windows: bool) -> PathBuf
where
    F: Fn(&str) -> Option<String>,
{
    if let Some(path) = get_env("SOLACE_HOME") {
        return PathBuf::from(path);
    }
    if _is_windows {
        if let Some(userprofile) = get_env("USERPROFILE") {
            return PathBuf::from(userprofile).join(".solace");
        }
        if let (Some(home_drive), Some(home_path)) = (get_env("HOMEDRIVE"), get_env("HOMEPATH")) {
            return PathBuf::from(format!("{home_drive}{home_path}")).join(".solace");
        }
    }
    if let Some(home) = get_env("HOME") {
        return PathBuf::from(home).join(".solace");
    }
    PathBuf::from(".solace")
}

#[cfg(test)]
mod tests {
    use super::resolve_solace_home_from_env;
    use std::path::PathBuf;

    #[test]
    fn resolve_solace_home_prefers_solace_home_env() {
        let resolved = resolve_solace_home_from_env(
            |key| match key {
                "SOLACE_HOME" => Some("/tmp/solace-custom".to_string()),
                "HOME" => Some("/tmp/home".to_string()),
                _ => None,
            },
            false,
        );

        assert_eq!(resolved, PathBuf::from("/tmp/solace-custom"));
    }

    #[test]
    fn resolve_solace_home_uses_userprofile_on_windows_when_home_missing() {
        let resolved = resolve_solace_home_from_env(
            |key| match key {
                "USERPROFILE" => Some(r"C:\Users\solace".to_string()),
                _ => None,
            },
            true,
        );

        assert_eq!(resolved, PathBuf::from(r"C:\Users\solace").join(".solace"));
    }

    #[test]
    fn resolve_solace_home_uses_home_drive_and_path_on_windows() {
        let resolved = resolve_solace_home_from_env(
            |key| match key {
                "HOMEDRIVE" => Some("C:".to_string()),
                "HOMEPATH" => Some(r"\Users\solace".to_string()),
                _ => None,
            },
            true,
        );

        assert_eq!(resolved, PathBuf::from(r"C:\Users\solace").join(".solace"));
    }
}
