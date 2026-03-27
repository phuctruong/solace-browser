// Diagram: 12-app-engine-pipeline
pub mod inbox;
pub mod outbox;
pub mod runner;
pub mod template;
pub mod wasm_sandbox;

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
    /// Hierarchical Org Chart: The ID of the App/Manager this agent reports to.
    #[serde(default)]
    pub reports_to: Option<String>,
    /// Company isolation matrix: Domain or UUID bounding this agent's state.
    #[serde(default)]
    pub company_id: Option<String>,
    /// Budget guard rails (Adversarial QA / Protocol Security).
    #[serde(default = "default_budget")]
    pub budget_limit: f64,
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
    /// Visibility: public (app store), team (workspace), secret (creator), template (partner).
    #[serde(default = "default_visibility")]
    pub visibility: String,
    /// Domain app triggers: activate on specific URL + DOM state.
    #[serde(default)]
    pub triggers: Vec<Trigger>,
    /// Domain app actions: what the user can do when app is active.
    #[serde(default)]
    pub actions: Vec<AppAction>,
    /// Backoffice workspace config (SQLite-backed apps).
    #[serde(default)]
    pub backoffice: Option<serde_json::Value>,
    /// Worker power sources (L1-L5).
    #[serde(default)]
    pub worker: Option<serde_json::Value>,
    /// Persona assigned to this app.
    #[serde(default)]
    pub persona: String,
    /// Tags for categorization and search.
    #[serde(default)]
    pub tags: Vec<String>,
}

/// Domain app trigger: activate when URL + DOM match.
#[derive(Clone, Default, Serialize, Deserialize, Debug)]
pub struct Trigger {
    #[serde(default)]
    pub domain: String,
    #[serde(default)]
    pub path: String,
    #[serde(default)]
    pub url_match: Vec<String>,
    #[serde(default)]
    pub dom_selector: String,
    #[serde(default)]
    pub context: String,
    #[serde(default = "default_activation")]
    pub activation: String,
}

fn default_activation() -> String {
    "auto".to_string()
}

/// Action a domain app can perform.
#[derive(Clone, Default, Serialize, Deserialize, Debug)]
pub struct AppAction {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub label: String,
    #[serde(default)]
    pub description: String,
}

fn default_cli_timeout() -> u64 {
    60
}

fn default_visibility() -> String {
    "public".to_string()
}

pub fn scan_installed_apps() -> Vec<AppManifest> {
    crate::utils::scan_apps()
}

fn default_budget() -> f64 {
    0.0
}
