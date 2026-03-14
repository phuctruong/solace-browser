pub mod inbox;
pub mod outbox;
pub mod runner;
pub mod template;

use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize)]
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
    #[serde(default)]
    pub template: String,
    #[serde(default)]
    pub source_url: Option<String>,
}

pub fn scan_installed_apps() -> Vec<AppManifest> {
    crate::utils::scan_apps()
}
