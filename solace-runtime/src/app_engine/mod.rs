// Diagram: 12-app-engine-pipeline
pub mod inbox;
pub mod outbox;
pub mod runner;
pub mod template;

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

fn default_source_type() -> String {
    "json".to_string()
}

fn default_limit() -> usize {
    25
}

#[derive(Clone, Serialize, Deserialize)]
pub struct DataSource {
    pub url: String,
    pub name: String,
    #[serde(default = "default_source_type")]
    pub source_type: String,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

#[derive(Clone, Default, Serialize, Deserialize)]
pub struct AppManifest {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub domain: String,
    #[serde(default, alias = "report_template")]
    pub template: String,
    #[serde(default)]
    pub report_template: String,
    #[serde(default)]
    pub schedule: String,
    #[serde(default)]
    pub source_url: Option<String>,
    #[serde(default)]
    pub data_sources: Vec<DataSource>,
    #[serde(default)]
    pub category: String,
    #[serde(default, alias = "type")]
    pub app_type: String,
    #[serde(default)]
    pub tier: String,
    #[serde(default)]
    pub levels: HashMap<String, String>,
    /// Conductor apps: list of app IDs whose outboxes this app reads.
    #[serde(default)]
    pub orchestrates: Vec<String>,
    /// CLI wrapper apps: binary to execute.
    #[serde(default)]
    pub binary: String,
    /// CLI wrapper apps: arguments to pass to binary.
    #[serde(default)]
    pub args: Vec<String>,
    /// CLI wrapper apps: input type (file, prompt, stdin).
    #[serde(default)]
    pub input_type: String,
    /// CLI wrapper apps: timeout in seconds (default 60).
    #[serde(default = "default_cli_timeout")]
    pub timeout_seconds: u64,
}

fn default_cli_timeout() -> u64 {
    60
}

pub fn scan_installed_apps() -> Vec<AppManifest> {
    crate::utils::scan_apps()
}
