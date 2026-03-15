// Diagram: 12-app-engine-pipeline
pub mod inbox;
pub mod outbox;
pub mod runner;
pub mod template;

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
}

pub fn scan_installed_apps() -> Vec<AppManifest> {
    crate::utils::scan_apps()
}
