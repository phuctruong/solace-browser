// Diagram: 05-solace-runtime-architecture
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

use chrono::{DateTime, Timelike, Utc};
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
    pub delight: Arc<RwLock<DelightState>>,
    pub tutorial: Arc<RwLock<TutorialState>>,
    pub runtime_events: Arc<RwLock<Vec<serde_json::Value>>>,
    /// WebSocket command channels: session_id → sender for browser control.
    /// When a browser sidebar connects with ?session=xxx, it registers here.
    /// Hub/MCP sends commands via POST /api/v1/browser/command/{session_id}.
    pub session_channels: Arc<RwLock<HashMap<String, tokio::sync::mpsc::UnboundedSender<String>>>>,
    /// Domain tab coordination: domain → DomainTab.
    /// Rule: 1 browser tab per domain. Apps in the same domain share a tab.
    /// This prevents runaway tabs and throttles apps per domain owner's site.
    pub domain_tabs: Arc<RwLock<HashMap<String, DomainTab>>>,
    /// Tunnel state: consent + connection to solaceagi.com for remote control.
    pub tunnel: Arc<RwLock<TunnelState>>,
    /// Auto-update status: version check + download + install progress.
    pub update_status: Arc<RwLock<crate::updates::UpdateStatus>>,
    /// Pending JS to execute in Hub WebView (polled by Hub).
    pub pending_js: Arc<RwLock<Option<String>>>,
    /// Backoffice database manager: one SQLite DB per backoffice app, lazy init.
    pub backoffice_db: Arc<crate::backoffice::db::DbManager>,
    /// Pub/Sub event bus: agents subscribe to topics, events trigger subscribers.
    pub event_bus: Arc<crate::pubsub::EventBus>,
    /// Job queue: priority-based task dispatch with retry + evidence.
    pub job_queue: Arc<crate::job_queue::JobQueue>,
}

/// Tunnel state for remote access (FDA Part 11 consent + WSS connection).
#[derive(Clone, Debug, Default, serde::Serialize, serde::Deserialize)]
pub struct TunnelState {
    pub consent: Option<crate::routes::tunnel::ConsentRecord>,
    pub connected: bool,
    pub connected_at: Option<String>,
    pub cloud_url: Option<String>,
}

/// Tracks one browser tab per domain. Apps in the same domain queue here.
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct DomainTab {
    pub domain: String,
    pub current_url: String,
    pub session_id: String,
    pub active_app_id: Option<String>,
    pub last_activity: String,
    pub tab_state: TabState,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize, PartialEq)]
pub enum TabState {
    Idle,
    Working,
    Cooldown,
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

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct DelightState {
    pub streak_days: u32,
    pub last_active_date: String,
    pub total_runs: u64,
}

impl Default for DelightState {
    fn default() -> Self {
        Self {
            streak_days: 0,
            last_active_date: String::new(),
            total_runs: 0,
        }
    }
}

impl DelightState {
    /// Record a new activity. Increments total_runs and updates streak.
    pub fn record_activity(&mut self) {
        let today = Utc::now().format("%Y-%m-%d").to_string();
        self.total_runs += 1;

        if self.last_active_date == today {
            // Already active today — no streak change
            return;
        }

        // Check if yesterday was the last active date (streak continues)
        let yesterday = (Utc::now() - chrono::Duration::days(1))
            .format("%Y-%m-%d")
            .to_string();

        if self.last_active_date == yesterday {
            self.streak_days += 1;
        } else if self.last_active_date.is_empty() {
            // First ever activity
            self.streak_days = 1;
        } else {
            // Streak broken — reset to 1
            self.streak_days = 1;
        }

        self.last_active_date = today;
    }

    /// Return a warm greeting based on current hour (UTC).
    pub fn warm_greeting(&self) -> &'static str {
        let hour = Utc::now().hour();
        match hour {
            5..=11 => "Good morning",
            12..=16 => "Good afternoon",
            17..=20 => "Good evening",
            _ => "Welcome back",
        }
    }

    /// Return a celebration message for streak milestones.
    pub fn celebration_message(&self) -> Option<&'static str> {
        match self.streak_days {
            3 => Some("3-day streak! You're building a habit."),
            7 => Some("One week streak! Consistency is power."),
            14 => Some("Two week streak! You're unstoppable."),
            30 => Some("30-day streak! A month of dedication."),
            50 => Some("50-day streak! Half a century of focus."),
            100 => Some("100-day streak! Legendary commitment."),
            365 => Some("365-day streak! A full year. Incredible."),
            _ if self.streak_days > 0 && self.streak_days % 100 == 0 => {
                Some("Century milestone! Keep going.")
            }
            _ => None,
        }
    }
}

/// The three tutorial steps a new user walks through.
pub const TUTORIAL_STEPS: [&str; 3] = ["run_first_app", "view_evidence", "try_chat"];

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct TutorialState {
    pub completed_steps: Vec<String>,
}

impl Default for TutorialState {
    fn default() -> Self {
        Self {
            completed_steps: Vec::new(),
        }
    }
}

impl TutorialState {
    /// Mark a step complete. Returns true if the step was newly completed.
    pub fn complete_step(&mut self, step: &str) -> bool {
        if !TUTORIAL_STEPS.contains(&step) {
            return false;
        }
        if self.completed_steps.iter().any(|s| s == step) {
            return false;
        }
        self.completed_steps.push(step.to_string());
        true
    }

    /// Current step number (1-indexed). Returns total_steps + 1 if all done.
    pub fn current_step(&self) -> usize {
        for (i, step) in TUTORIAL_STEPS.iter().enumerate() {
            if !self.completed_steps.iter().any(|s| s == step) {
                return i + 1;
            }
        }
        TUTORIAL_STEPS.len() + 1
    }

    pub fn is_complete(&self) -> bool {
        self.current_step() > TUTORIAL_STEPS.len()
    }
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
            app_count: Arc::new(RwLock::new(
                crate::utils::scan_apps().len() as u32,
            )),
            budget_usage: Arc::new(RwLock::new(budget_usage)),
            cloud_config: Arc::new(RwLock::new(cloud_config)),
            theme: Arc::new(RwLock::new(settings.theme)),
            launch_dedup: Arc::new(RwLock::new(LaunchDedup::default())),
            pending_actions: Arc::new(RwLock::new(Vec::new())),
            delight: Arc::new(RwLock::new(
                crate::persistence::read_json::<DelightState>(
                    &solace_home.join("daemon").join("delight.json"),
                )
                .unwrap_or_default(),
            )),
            tutorial: Arc::new(RwLock::new(
                crate::persistence::read_json::<TutorialState>(
                    &solace_home.join("daemon").join("tutorial.json"),
                )
                .unwrap_or_default(),
            )),
            runtime_events: Arc::new(RwLock::new(Vec::new())),
            session_channels: Arc::new(RwLock::new(HashMap::new())),
            domain_tabs: Arc::new(RwLock::new(HashMap::new())),
            tunnel: Arc::new(RwLock::new(TunnelState::default())),
            update_status: Arc::new(RwLock::new(crate::updates::UpdateStatus::default())),
            pending_js: Arc::new(RwLock::new(None)),
            backoffice_db: Arc::new(crate::backoffice::db::DbManager::new(
                solace_home.join("backoffice"),
            )),
            event_bus: Arc::new(crate::pubsub::EventBus::new(&solace_home)),
            job_queue: Arc::new(crate::job_queue::JobQueue::new(&solace_home)),
        }
    }

    pub fn uptime_seconds(&self) -> i64 {
        (Utc::now() - self.start_time).num_seconds()
    }
}
