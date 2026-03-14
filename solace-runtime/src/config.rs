// Diagram: 05-solace-runtime-architecture
use std::path::Path;

use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize)]
pub struct Settings {
    pub theme: String,
    pub telemetry: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            theme: "light".to_string(),
            telemetry: false,
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

pub fn load_budget_config(solace_home: &Path) -> BudgetConfig {
    crate::persistence::read_json(&solace_home.join("budget.json")).unwrap_or_default()
}

pub fn save_budget_config(solace_home: &Path, value: &BudgetConfig) -> Result<(), String> {
    crate::persistence::write_json(&solace_home.join("budget.json"), value)
}
