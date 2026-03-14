// Diagram: 05-solace-runtime-architecture
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

use chrono::{DateTime, Utc};
use parking_lot::RwLock;

/// Window in seconds: launches of the same key within this period are deduped.
pub const LAUNCH_DEDUP_WINDOW_SECS: u64 = 30;

/// Tracks recent and in-flight browser launches for 3-layer dedup.
#[derive(Default)]
pub struct LaunchDedup {
    /// Maps launch_key -> timestamp of last successful launch.
    pub recent_launches: HashMap<String, Instant>,
    /// Maps launch_key -> timestamp when an in-flight launch started.
    pub inflight_launches: HashMap<String, Instant>,
}

impl LaunchDedup {
    /// Remove entries older than the dedup window from both maps.
    pub fn cleanup(&mut self) {
        let cutoff = Instant::now() - std::time::Duration::from_secs(LAUNCH_DEDUP_WINDOW_SECS);
        self.recent_launches.retain(|_, ts| *ts >= cutoff);
        self.inflight_launches.retain(|_, ts| *ts >= cutoff);
    }
}

#[derive(Clone)]
pub struct AppState {
    pub start_time: DateTime<Utc>,
    pub token_hash: String,
    pub sessions: Arc<RwLock<HashMap<String, SessionInfo>>>,
    pub notifications: Arc<RwLock<Vec<Notification>>>,
    pub schedules: Arc<RwLock<Vec<Schedule>>>,
    pub evidence_count: Arc<RwLock<u64>>,
    pub app_count: Arc<RwLock<u32>>,
    pub budget_usage: Arc<RwLock<crate::config::BudgetUsage>>,
    pub cloud_config: Arc<RwLock<Option<CloudConfig>>>,
    pub theme: Arc<RwLock<String>>,
    pub launch_dedup: Arc<RwLock<LaunchDedup>>,
    pub pending_actions: Arc<RwLock<Vec<crate::routes::chat::PendingAction>>>,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct SessionInfo {
    pub session_id: String,
    pub profile: String,
    pub url: String,
    pub pid: u32,
    pub started_at: String,
    pub mode: String,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct Notification {
    pub id: String,
    pub message: String,
    pub level: String,
    pub read: bool,
    pub created_at: String,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct Schedule {
    pub id: String,
    pub app_id: String,
    pub cron: String,
    pub enabled: bool,
    pub label: String,
    pub next_run: Option<String>,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct CloudConfig {
    pub api_key: String,
    pub user_email: String,
    pub device_id: String,
    pub paid_user: bool,
}

impl AppState {
    pub fn new() -> Self {
        let solace_home = crate::utils::solace_home();
        let token = uuid::Uuid::new_v4().to_string();
        let token_hash = crate::utils::sha256_hex(&token);
        let settings = crate::config::load_settings(&solace_home);
        let cloud_config = crate::config::load_cloud_config(&solace_home);
        let budget_usage = crate::config::load_budget_usage(&solace_home);
        let schedules = crate::persistence::read_json::<Vec<Schedule>>(
            &solace_home.join("daemon").join("schedules.json"),
        )
        .unwrap_or_default();

        Self {
            start_time: Utc::now(),
            token_hash,
            sessions: Arc::new(RwLock::new(HashMap::new())),
            notifications: Arc::new(RwLock::new(Vec::new())),
            schedules: Arc::new(RwLock::new(schedules)),
            evidence_count: Arc::new(RwLock::new(0)),
            app_count: Arc::new(RwLock::new(0)),
            budget_usage: Arc::new(RwLock::new(budget_usage)),
            cloud_config: Arc::new(RwLock::new(cloud_config)),
            theme: Arc::new(RwLock::new(settings.theme)),
            launch_dedup: Arc::new(RwLock::new(LaunchDedup::default())),
            pending_actions: Arc::new(RwLock::new(Vec::new())),
        }
    }

    pub fn uptime_seconds(&self) -> i64 {
        (Utc::now() - self.start_time).num_seconds()
    }
}
