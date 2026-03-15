// Diagram: 05-solace-runtime-architecture
use std::path::Path;

use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize)]
pub struct Settings {
    pub theme: String,
    pub telemetry: bool,
    /// When true, the browse-capture pipeline delegates to the browser for
    /// full-page PNG screenshots alongside the text-based prime-snapshot.
    /// Default: false (text snapshots are the default evidence format).
    #[serde(default)]
    pub auto_screenshot: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            theme: "light".to_string(),
            telemetry: false,
            auto_screenshot: false,
        }
    }
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Onboarding {
    pub completed: bool,
    pub state: String,
}

impl Default for Onboarding {
    fn default() -> Self {
        Self {
            completed: false,
            state: "grey".to_string(),
        }
    }
}

#[derive(Clone, Serialize, Deserialize)]
pub struct BudgetConfig {
    pub daily_limit: u64,
    pub monthly_limit: u64,
    pub enforce: bool,
}

impl Default for BudgetConfig {
    fn default() -> Self {
        Self {
            daily_limit: 1_000,
            monthly_limit: 20_000,
            enforce: true,
        }
    }
}

pub fn load_settings(solace_home: &Path) -> Settings {
    crate::persistence::read_json(&solace_home.join("settings.json")).unwrap_or_default()
}

pub fn save_settings(solace_home: &Path, value: &Settings) -> Result<(), String> {
    crate::persistence::write_json(&solace_home.join("settings.json"), value)
}

pub fn load_cloud_config(solace_home: &Path) -> Option<crate::state::CloudConfig> {
    crate::persistence::read_json(&solace_home.join("cloud_config.json")).ok()
}

pub fn save_cloud_config(
    solace_home: &Path,
    value: &crate::state::CloudConfig,
) -> Result<(), String> {
    crate::persistence::write_json(&solace_home.join("cloud_config.json"), value)
}

pub fn clear_cloud_config(solace_home: &Path) -> Result<(), String> {
    let path = solace_home.join("cloud_config.json");
    match std::fs::remove_file(path) {
        Ok(_) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.to_string()),
    }
}

pub fn load_onboarding(solace_home: &Path) -> Onboarding {
    crate::persistence::read_json(&solace_home.join("onboarding.json")).unwrap_or_default()
}

pub fn save_onboarding(solace_home: &Path, value: &Onboarding) -> Result<(), String> {
    crate::persistence::write_json(&solace_home.join("onboarding.json"), value)
}

/// Check if user has a BYOK (Bring Your Own Key) API key configured.
/// Looks for ~/.solace/byok.json with at least one non-empty key.
pub fn has_byok_key(solace_home: &Path) -> bool {
    let path = solace_home.join("byok.json");
    if let Ok(content) = std::fs::read_to_string(&path) {
        if let Ok(value) = serde_json::from_str::<serde_json::Value>(&content) {
            // Check for any non-empty key field
            if let Some(obj) = value.as_object() {
                return obj.values().any(|v| {
                    v.as_str().is_some_and(|s| !s.is_empty())
                });
            }
        }
    }
    // Also check environment variable
    std::env::var("SOLACE_LLM_API_KEY").is_ok_and(|k| !k.is_empty())
}

pub fn load_budget_config(solace_home: &Path) -> BudgetConfig {
    crate::persistence::read_json(&solace_home.join("budget.json")).unwrap_or_default()
}

pub fn save_budget_config(solace_home: &Path, value: &BudgetConfig) -> Result<(), String> {
    crate::persistence::write_json(&solace_home.join("budget.json"), value)
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BudgetUsage {
    /// ISO-8601 date string (YYYY-MM-DD) for the current daily window.
    pub daily_date: String,
    /// Number of evidence events recorded on `daily_date`.
    pub daily_count: u64,
    /// ISO-8601 month string (YYYY-MM) for the current monthly window.
    pub monthly_date: String,
    /// Number of evidence events recorded during `monthly_date`.
    pub monthly_count: u64,
}

impl Default for BudgetUsage {
    fn default() -> Self {
        let now = chrono::Utc::now();
        Self {
            daily_date: now.format("%Y-%m-%d").to_string(),
            daily_count: 0,
            monthly_date: now.format("%Y-%m").to_string(),
            monthly_count: 0,
        }
    }
}

impl BudgetUsage {
    /// Increment usage by one event, rolling over the daily/monthly window
    /// when the calendar date changes.
    pub fn record_event(&mut self) {
        let now = chrono::Utc::now();
        let today = now.format("%Y-%m-%d").to_string();
        let month = now.format("%Y-%m").to_string();

        if self.daily_date != today {
            self.daily_date = today;
            self.daily_count = 0;
        }
        if self.monthly_date != month {
            self.monthly_date = month;
            self.monthly_count = 0;
        }

        self.daily_count += 1;
        self.monthly_count += 1;
    }

    /// Returns `true` when enforce is on and either limit is exceeded.
    pub fn is_blocked(&self, config: &BudgetConfig) -> bool {
        if !config.enforce {
            return false;
        }
        self.daily_count >= config.daily_limit || self.monthly_count >= config.monthly_limit
    }
}

pub fn load_budget_usage(solace_home: &Path) -> BudgetUsage {
    crate::persistence::read_json(&solace_home.join("budget_usage.json")).unwrap_or_default()
}

pub fn save_budget_usage(solace_home: &Path, value: &BudgetUsage) -> Result<(), String> {
    crate::persistence::write_json(&solace_home.join("budget_usage.json"), value)
}
