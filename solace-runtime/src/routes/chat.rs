// Diagram: 09-yinyang-fsm
// Chat pipeline FSM: IDLE → LISTENING → INTENT_CLASSIFIED → PREVIEW → COOLDOWN → APPROVED → SEALED → EXECUTING → DONE
use axum::{extract::State, http::StatusCode, routing::post, Json, Router};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::time::{Duration, Instant};

use crate::state::{AppState, Notification};

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/chat/message", post(chat_message))
        .route("/api/v1/chat/approve", post(chat_approve))
        .route("/api/v1/chat/reject", post(chat_reject))
}

// ─── Intent Classification ───────────────────────────────────────────

/// Classified intent from user message
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Intent {
    /// Informational query — no side effects, no approval needed
    Query,
    /// Navigate to a URL — low risk, auto-approved
    Navigate,
    /// Run an installed app — medium risk, preview + cooldown
    RunApp,
    /// Browser automation — high risk, requires explicit approval
    Automate,
    /// System configuration — high risk, requires approval
    Configure,
    /// Unknown — ask for clarification
    Unknown,
}

impl Intent {
    fn risk_tier(self) -> RiskTier {
        match self {
            Intent::Query => RiskTier::None,
            Intent::Navigate => RiskTier::Low,
            Intent::RunApp => RiskTier::Medium,
            Intent::Automate => RiskTier::High,
            Intent::Configure => RiskTier::High,
            Intent::Unknown => RiskTier::None,
        }
    }

    fn cooldown_secs(self) -> u64 {
        match self.risk_tier() {
            RiskTier::None => 0,
            RiskTier::Low => 0,
            RiskTier::Medium => 5,
            RiskTier::High => 15,
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
enum RiskTier {
    None,
    Low,
    Medium,
    High,
}

/// Classify intent from user message using keyword matching.
/// In production, this would call an LLM for classification.
fn classify_intent(message: &str) -> Intent {
    let lower = message.to_ascii_lowercase();

    // Configuration patterns (check BEFORE app names — "schedule morning brief" = configure, not run)
    if lower.starts_with("set ")
        || lower.starts_with("configure ")
        || lower.starts_with("change ")
        || lower.starts_with("schedule ")
        || lower.contains("budget ")
        || lower.contains("api key")
    {
        return Intent::Configure;
    }

    // Navigation patterns
    if lower.starts_with("go to ")
        || lower.starts_with("open ")
        || lower.starts_with("navigate ")
        || lower.contains("http://")
        || lower.contains("https://")
    {
        return Intent::Navigate;
    }

    // App execution patterns
    if lower.starts_with("run ")
        || lower.starts_with("execute ")
        || lower.starts_with("launch ")
        || lower.contains("morning brief")
        || lower.contains("hackernews")
        || lower.contains("reddit scan")
    {
        return Intent::RunApp;
    }

    // Automation patterns
    if lower.contains("click ")
        || lower.contains("fill ")
        || lower.contains("submit ")
        || lower.contains("scrape ")
        || lower.contains("automate ")
        || lower.contains("recipe ")
    {
        return Intent::Automate;
    }

    // Query patterns (questions, info requests)
    if lower.contains('?')
        || lower.starts_with("what ")
        || lower.starts_with("how ")
        || lower.starts_with("why ")
        || lower.starts_with("when ")
        || lower.starts_with("where ")
        || lower.starts_with("show ")
        || lower.starts_with("list ")
        || lower.starts_with("status")
        || lower.starts_with("help")
    {
        return Intent::Query;
    }

    Intent::Unknown
}

// ─── FSM States ──────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "snake_case")]
enum FsmState {
    IntentClassified,
    PreviewReady,
    Cooldown,
    AutoApproved,
    WaitingApproval,
    Executing,
    Done,
}

// ─── Chat Message Handler (IDLE → INTENT → PREVIEW → COOLDOWN) ──────

#[derive(Deserialize)]
struct ChatPayload {
    message: String,
    persona: Option<String>,
}

async fn chat_message(
    State(state): State<AppState>,
    Json(payload): Json<ChatPayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    if payload.message.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "message required"})),
        ));
    }

    let routed_to = if state
        .cloud_config
        .read()
        .as_ref()
        .is_some_and(|config| config.paid_user)
    {
        "solace-cloud"
    } else {
        "local-preview"
    };

    // Step 1: Classify intent
    let intent = classify_intent(&payload.message);
    let risk = intent.risk_tier();
    let cooldown = intent.cooldown_secs();

    // Step 2: Generate preview based on intent
    let (preview, fsm_state, needs_approval) = match intent {
        Intent::Query => {
            let preview = format!("I'll answer: {}", payload.message);
            (preview, FsmState::AutoApproved, false)
        }
        Intent::Navigate => {
            let url = extract_url(&payload.message).unwrap_or_else(|| payload.message.clone());
            let preview = format!("Navigate to: {url}");
            (preview, FsmState::AutoApproved, false)
        }
        Intent::RunApp => {
            let app = extract_app_name(&payload.message);
            let preview = format!("Run app '{app}' → will fetch data, render template, write to outbox");
            if cooldown > 0 {
                (preview, FsmState::Cooldown, true)
            } else {
                (preview, FsmState::AutoApproved, false)
            }
        }
        Intent::Automate => {
            let preview = format!(
                "Browser automation requested: '{}'. This requires explicit approval.",
                payload.message
            );
            (preview, FsmState::WaitingApproval, true)
        }
        Intent::Configure => {
            let preview = format!(
                "Configuration change: '{}'. This requires approval.",
                payload.message
            );
            (preview, FsmState::WaitingApproval, true)
        }
        Intent::Unknown => {
            let preview = format!(
                "I'm not sure what you'd like me to do. Try: 'run morning brief', 'open https://...', 'show status', or ask a question."
            );
            (preview, FsmState::IntentClassified, false)
        }
    };

    // Step 3: Auto-execute if no approval needed
    let (reply, final_state) = if !needs_approval {
        let result = execute_intent(&intent, &payload.message, &state).await;
        (result, FsmState::Done)
    } else {
        // Store pending action for approval
        let action_id = uuid::Uuid::new_v4().to_string();
        state.pending_actions.write().push(PendingAction {
            id: action_id.clone(),
            intent,
            message: payload.message.clone(),
            preview: preview.clone(),
            cooldown_secs: cooldown,
            created_at: Instant::now(),
        });
        (preview.clone(), fsm_state)
    };

    state.notifications.write().push(Notification {
        id: uuid::Uuid::new_v4().to_string(),
        message: format!("Chat [{:?}]: {}", intent, &payload.message.chars().take(50).collect::<String>()),
        level: "info".to_string(),
        read: false,
        created_at: crate::utils::now_iso8601(),
    });

    Ok(Json(json!({
        "accepted": true,
        "route": routed_to,
        "intent": intent,
        "risk_tier": risk,
        "cooldown_secs": cooldown,
        "fsm_state": final_state,
        "needs_approval": needs_approval,
        "preview": preview,
        "reply": reply,
        "persona": payload.persona.unwrap_or_else(|| "default".to_string()),
    })))
}

// ─── Approve/Reject Handlers ─────────────────────────────────────────

#[derive(Deserialize)]
struct ApprovePayload {
    action_id: String,
}

async fn chat_approve(
    State(state): State<AppState>,
    Json(payload): Json<ApprovePayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let action = {
        let mut actions = state.pending_actions.write();
        let idx = actions.iter().position(|a| a.id == payload.action_id);
        match idx {
            Some(i) => actions.remove(i),
            None => {
                return Err((
                    StatusCode::NOT_FOUND,
                    Json(json!({"error": "action not found or already processed"})),
                ))
            }
        }
    };

    // Check cooldown
    let elapsed = action.created_at.elapsed();
    if elapsed < Duration::from_secs(action.cooldown_secs) {
        let remaining = action.cooldown_secs - elapsed.as_secs();
        return Err((
            StatusCode::TOO_EARLY,
            Json(json!({
                "error": "cooldown active",
                "remaining_secs": remaining,
                "fsm_state": "cooldown",
            })),
        ));
    }

    // Execute the approved action
    let result = execute_intent(&action.intent, &action.message, &state).await;

    Ok(Json(json!({
        "action_id": action.id,
        "fsm_state": "done",
        "intent": action.intent,
        "result": result,
    })))
}

async fn chat_reject(
    State(state): State<AppState>,
    Json(payload): Json<ApprovePayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let mut actions = state.pending_actions.write();
    let idx = actions.iter().position(|a| a.id == payload.action_id);
    match idx {
        Some(i) => {
            let action = actions.remove(i);
            Ok(Json(json!({
                "action_id": action.id,
                "fsm_state": "rejected",
                "intent": action.intent,
            })))
        }
        None => Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "action not found or already processed"})),
        )),
    }
}

// ─── Intent Execution ────────────────────────────────────────────────

async fn execute_intent(intent: &Intent, message: &str, state: &AppState) -> String {
    match intent {
        Intent::Query => {
            // Answer queries about system status
            let lower = message.to_ascii_lowercase();
            if lower.contains("status") || lower.contains("health") {
                let sessions = state.sessions.read().len();
                let evidence = *state.evidence_count.read();
                let cloud = state.cloud_config.read().is_some();
                format!(
                    "System status: {} active sessions, {} evidence entries, cloud {}.",
                    sessions, evidence, if cloud { "connected" } else { "disconnected" }
                )
            } else if lower.contains("app") {
                let apps = crate::utils::scan_app_dirs();
                format!("You have {} apps installed.", apps.len())
            } else {
                format!("I understand your question: '{}'. In production, this would query an LLM for a detailed answer.", message)
            }
        }
        Intent::Navigate => {
            let url = extract_url(message).unwrap_or_else(|| message.to_string());
            format!("Navigation to '{}' dispatched via runtime.", url)
        }
        Intent::RunApp => {
            let app_name = extract_app_name(message);
            match crate::app_engine::runner::run_app(&app_name, state).await {
                Ok(path) => format!("App '{}' completed. Report: {}", app_name, path.display()),
                Err(e) => format!("App '{}' failed: {}", app_name, e),
            }
        }
        Intent::Automate => {
            format!("Automation '{}' would be dispatched to the browser engine. Not yet wired to Chromium.", message)
        }
        Intent::Configure => {
            format!("Configuration change '{}' noted. Apply via the appropriate API endpoint.", message)
        }
        Intent::Unknown => {
            "I didn't understand that. Try 'run morning brief', 'show status', or ask a question.".to_string()
        }
    }
}

// ─── Helpers ─────────────────────────────────────────────────────────

fn extract_url(message: &str) -> Option<String> {
    message
        .split_whitespace()
        .find(|w| w.starts_with("http://") || w.starts_with("https://"))
        .map(|s| s.to_string())
}

fn extract_app_name(message: &str) -> String {
    let lower = message.to_ascii_lowercase();
    // Try to match known app patterns
    let patterns = [
        ("morning brief", "morning-brief"),
        ("hackernews", "hackernews-feed"),
        ("hacker news", "hackernews-feed"),
        ("reddit", "reddit-scanner"),
        ("google", "google-search-trends"),
    ];
    for (pattern, app_id) in &patterns {
        if lower.contains(pattern) {
            return app_id.to_string();
        }
    }
    // Extract word after "run " or "execute " or "launch "
    for prefix in &["run ", "execute ", "launch "] {
        if let Some(rest) = lower.strip_prefix(prefix) {
            return rest.trim().replace(' ', "-");
        }
    }
    lower.trim().replace(' ', "-")
}

/// Pending action awaiting user approval
#[derive(Debug)]
pub struct PendingAction {
    pub id: String,
    pub intent: Intent,
    pub message: String,
    pub preview: String,
    pub cooldown_secs: u64,
    pub created_at: Instant,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classify_query() {
        assert_eq!(classify_intent("what is my status?"), Intent::Query);
        assert_eq!(classify_intent("how many apps do I have?"), Intent::Query);
        assert_eq!(classify_intent("show me the evidence"), Intent::Query);
        assert_eq!(classify_intent("help"), Intent::Query);
    }

    #[test]
    fn classify_navigate() {
        assert_eq!(classify_intent("open https://google.com"), Intent::Navigate);
        assert_eq!(classify_intent("go to https://solaceagi.com"), Intent::Navigate);
    }

    #[test]
    fn classify_run_app() {
        assert_eq!(classify_intent("run morning brief"), Intent::RunApp);
        assert_eq!(classify_intent("execute hackernews feed"), Intent::RunApp);
        assert_eq!(classify_intent("launch reddit scanner"), Intent::RunApp);
    }

    #[test]
    fn classify_automate() {
        assert_eq!(classify_intent("click the submit button"), Intent::Automate);
        assert_eq!(classify_intent("fill in the form with my info"), Intent::Automate);
        assert_eq!(classify_intent("automate my email workflow"), Intent::Automate);
    }

    #[test]
    fn classify_configure() {
        assert_eq!(classify_intent("set budget to $10/day"), Intent::Configure);
        assert_eq!(classify_intent("schedule morning brief at 7am"), Intent::Configure);
    }

    #[test]
    fn classify_unknown() {
        assert_eq!(classify_intent("banana"), Intent::Unknown);
    }

    #[test]
    fn risk_tiers_correct() {
        assert_eq!(Intent::Query.cooldown_secs(), 0);
        assert_eq!(Intent::Navigate.cooldown_secs(), 0);
        assert_eq!(Intent::RunApp.cooldown_secs(), 5);
        assert_eq!(Intent::Automate.cooldown_secs(), 15);
        assert_eq!(Intent::Configure.cooldown_secs(), 15);
    }

    #[test]
    fn extract_url_from_message() {
        assert_eq!(extract_url("open https://google.com"), Some("https://google.com".to_string()));
        assert_eq!(extract_url("no url here"), None);
    }

    #[test]
    fn extract_app_names() {
        assert_eq!(extract_app_name("run morning brief"), "morning-brief");
        assert_eq!(extract_app_name("run hackernews feed"), "hackernews-feed");
        assert_eq!(extract_app_name("run reddit scanner"), "reddit-scanner");
        assert_eq!(extract_app_name("run custom-app"), "custom-app");
    }
}
