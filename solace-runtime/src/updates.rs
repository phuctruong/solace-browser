// Diagram: hub-deployment-pipeline
//! Auto-update module — checks GCS for new versions, downloads, verifies, swaps binaries.
//!
//! Architecture:
//!   1. Check https://storage.googleapis.com/solace-downloads/solace-browser/latest/manifest.json
//!   2. Compare remote version with local VERSION file
//!   3. If newer: download tarball + SHA256, verify integrity
//!   4. Extract to ~/.solace/updates/{version}/
//!   5. Backup current binaries to ~/.solace/backups/{old_version}/
//!   6. Swap binaries in place
//!   7. Record evidence + notify user
//!   8. Runtime restart handled by Hub or systemd
//!
//! Safety: SHA256 verified. Backup before swap. Evidence on everything. Rollback possible.

use serde::{Deserialize, Serialize};
use serde_json::json;
use std::path::{Path, PathBuf};

const GCS_BASE: &str = "https://storage.googleapis.com/solace-downloads/solace-browser/latest";
const UPDATE_CHECK_INTERVAL_SECS: u64 = 3600; // 1 hour

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RemoteManifest {
    pub version: String,
    #[serde(default)]
    pub bundle: String,
    #[serde(default)]
    pub hub_binary: String,
    #[serde(default)]
    pub browser_binary: String,
    #[serde(default)]
    pub runtime_port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateStatus {
    pub current_version: String,
    pub latest_version: Option<String>,
    pub update_available: bool,
    pub auto_update_enabled: bool,
    pub last_check: Option<String>,
    pub last_update: Option<String>,
    pub last_error: Option<String>,
}

impl Default for UpdateStatus {
    fn default() -> Self {
        Self {
            current_version: local_version(),
            latest_version: None,
            update_available: false,
            auto_update_enabled: true,
            last_check: None,
            last_update: None,
            last_error: None,
        }
    }
}

/// Read local version from VERSION file or manifest.json
pub fn local_version() -> String {
    let solace_home = crate::utils::solace_home();

    // Try VERSION file in bundle dir
    for candidate in &[
        solace_home.join("VERSION"),
        PathBuf::from("/usr/lib/solace-browser/solace-browser-release/VERSION"),
        std::env::current_exe()
            .unwrap_or_default()
            .parent()
            .unwrap_or(Path::new("."))
            .join("VERSION"),
    ] {
        if let Ok(v) = std::fs::read_to_string(candidate) {
            let trimmed = v.trim().to_string();
            if !trimmed.is_empty() {
                return trimmed;
            }
        }
    }

    "0.0.0".to_string()
}

/// Check GCS for latest version. Returns remote manifest if newer.
pub async fn check_for_update() -> Result<Option<RemoteManifest>, String> {
    let manifest_url = format!("{}/manifest.json", GCS_BASE);

    let client = reqwest::Client::new();
    let response = client
        .get(&manifest_url)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| format!("Update check failed: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("GCS returned {}", response.status()));
    }

    let manifest: RemoteManifest = response
        .json()
        .await
        .map_err(|e| format!("Invalid manifest: {}", e))?;

    let current = local_version();
    if is_newer(&manifest.version, &current) {
        Ok(Some(manifest))
    } else {
        Ok(None)
    }
}

/// Download, verify, and install update.
pub async fn download_and_install(manifest: &RemoteManifest) -> Result<String, String> {
    let solace_home = crate::utils::solace_home();
    let updates_dir = solace_home.join("updates");
    let backups_dir = solace_home.join("backups");
    let _ = std::fs::create_dir_all(&updates_dir);
    let _ = std::fs::create_dir_all(&backups_dir);

    let tarball_url = format!(
        "{}/solace-browser-chromium-linux-x86_64.tar.gz",
        GCS_BASE
    );
    let sha256_url = format!("{}.sha256", tarball_url);

    // 1. Download SHA256
    let client = reqwest::Client::new();
    let sha_resp = client
        .get(&sha256_url)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("SHA256 download failed: {}", e))?;

    let expected_hash = sha_resp
        .text()
        .await
        .map_err(|e| format!("SHA256 read failed: {}", e))?
        .split_whitespace()
        .next()
        .unwrap_or("")
        .to_string();

    if expected_hash.len() != 64 {
        return Err(format!("Invalid SHA256 hash length: {}", expected_hash.len()));
    }

    // 2. Download tarball
    let tarball_path = updates_dir.join(format!("solace-browser-{}.tar.gz", manifest.version));
    let resp = client
        .get(&tarball_url)
        .timeout(std::time::Duration::from_secs(300))
        .send()
        .await
        .map_err(|e| format!("Tarball download failed: {}", e))?;

    let bytes = resp
        .bytes()
        .await
        .map_err(|e| format!("Tarball read failed: {}", e))?;

    std::fs::write(&tarball_path, &bytes)
        .map_err(|e| format!("Tarball write failed: {}", e))?;

    // 3. Verify SHA256
    let actual_hash = crate::utils::sha256_bytes(&bytes);
    if actual_hash != expected_hash {
        let _ = std::fs::remove_file(&tarball_path);
        return Err(format!(
            "SHA256 mismatch! Expected {} got {}",
            expected_hash, actual_hash
        ));
    }

    // 4. Backup current binaries
    let current_version = local_version();
    let backup_dir = backups_dir.join(&current_version);
    let _ = std::fs::create_dir_all(&backup_dir);

    let bin_dir = solace_home.join("bin");
    for binary in &["solace-runtime", "solace-hub", "solace_crashpad_handler"] {
        let src = bin_dir.join(binary);
        if src.exists() {
            let _ = std::fs::copy(&src, backup_dir.join(binary));
        }
    }

    // 5. Extract tarball
    let extract_dir = updates_dir.join(format!("v{}", manifest.version));
    let _ = std::fs::remove_dir_all(&extract_dir);
    let _ = std::fs::create_dir_all(&extract_dir);

    let output = std::process::Command::new("tar")
        .args([
            "-xzf",
            tarball_path.to_str().unwrap_or(""),
            "-C",
            extract_dir.to_str().unwrap_or(""),
        ])
        .output()
        .map_err(|e| format!("Extract failed: {}", e))?;

    if !output.status.success() {
        return Err(format!(
            "Extract failed: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }

    // 6. Swap binaries
    let extracted_bundle = extract_dir.join("solace-browser-release");
    for binary in &["solace-runtime", "solace-hub-bin"] {
        let src = extracted_bundle.join(binary);
        let dst = bin_dir.join(if *binary == "solace-hub-bin" { "solace-hub" } else { binary });
        if src.exists() {
            let _ = std::fs::copy(&src, &dst);
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = std::fs::set_permissions(&dst, std::fs::Permissions::from_mode(0o755));
            }
        }
    }

    // 7. Update VERSION file
    let _ = std::fs::write(bin_dir.join("VERSION"), &manifest.version);

    // 8. Record evidence
    let _ = crate::evidence::record_event(
        &solace_home,
        "system.auto_update",
        "runtime",
        json!({
            "old_version": current_version,
            "new_version": manifest.version,
            "sha256": expected_hash,
            "tarball_bytes": bytes.len(),
        }),
    );

    // 9. Cleanup tarball (keep backup)
    let _ = std::fs::remove_file(&tarball_path);
    let _ = std::fs::remove_dir_all(&extract_dir);

    Ok(format!(
        "Updated {} → {}",
        current_version, manifest.version
    ))
}

/// Semantic version comparison: is `remote` newer than `local`?
fn is_newer(remote: &str, local: &str) -> bool {
    let parse = |v: &str| -> (u32, u32, u32) {
        let parts: Vec<u32> = v
            .trim()
            .split('.')
            .filter_map(|p| p.parse().ok())
            .collect();
        (
            parts.first().copied().unwrap_or(0),
            parts.get(1).copied().unwrap_or(0),
            parts.get(2).copied().unwrap_or(0),
        )
    };
    parse(remote) > parse(local)
}

/// Background task: check for updates periodically.
pub fn spawn_update_checker(state: crate::state::AppState) {
    tokio::spawn(async move {
        // Wait 60s after startup before first check
        tokio::time::sleep(std::time::Duration::from_secs(60)).await;

        loop {
            // Check if auto-update is enabled
            let enabled = state.update_status.read().auto_update_enabled;
            if enabled {
                match check_for_update().await {
                    Ok(Some(manifest)) => {
                        let msg = format!("Update available: v{}", manifest.version);
                        state.notifications.write().push(crate::state::Notification {
                            id: uuid::Uuid::new_v4().to_string(),
                            message: msg.clone(),
                            level: "info".to_string(),
                            read: false,
                            created_at: crate::utils::now_iso8601(),
                        });

                        {
                            let mut status = state.update_status.write();
                            status.latest_version = Some(manifest.version.clone());
                            status.update_available = true;
                            status.last_check = Some(crate::utils::now_iso8601());
                        }

                        // Auto-download and install
                        match download_and_install(&manifest).await {
                            Ok(result) => {
                                state.notifications.write().push(crate::state::Notification {
                                    id: uuid::Uuid::new_v4().to_string(),
                                    message: format!("Auto-update complete: {}", result),
                                    level: "success".to_string(),
                                    read: false,
                                    created_at: crate::utils::now_iso8601(),
                                });
                                let mut status = state.update_status.write();
                                status.last_update = Some(crate::utils::now_iso8601());
                                status.update_available = false;
                                status.last_error = None;
                            }
                            Err(err) => {
                                let mut status = state.update_status.write();
                                status.last_error = Some(err);
                            }
                        }
                    }
                    Ok(None) => {
                        // Already up to date
                        let mut status = state.update_status.write();
                        status.last_check = Some(crate::utils::now_iso8601());
                        status.update_available = false;
                    }
                    Err(err) => {
                        let mut status = state.update_status.write();
                        status.last_check = Some(crate::utils::now_iso8601());
                        status.last_error = Some(err);
                    }
                }
            }

            tokio::time::sleep(std::time::Duration::from_secs(UPDATE_CHECK_INTERVAL_SECS)).await;
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_newer() {
        assert!(is_newer("2.1.0", "2.0.0"));
        assert!(is_newer("3.0.0", "2.9.9"));
        assert!(is_newer("2.0.1", "2.0.0"));
        assert!(!is_newer("2.0.0", "2.0.0"));
        assert!(!is_newer("1.9.9", "2.0.0"));
    }

    #[test]
    fn test_local_version() {
        let v = local_version();
        // Should return something (even if "0.0.0")
        assert!(!v.is_empty());
    }
}
