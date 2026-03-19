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

    // QA patterns — check BEFORE navigation (so "run visual qa on http://..." → RunApp, not Navigate)
    if lower.starts_with("qa ")
        || lower.starts_with("test ")
        || lower.contains(" qa")
        || lower.contains("visual qa")
        || lower.contains("api qa")
        || lower.contains("security qa")
        || lower.contains("accessibility qa")
        || lower.contains("performance qa")
        || lower.contains("evidence qa")
        || lower.contains("integration qa")
    {
        return Intent::RunApp;
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
        || lower.starts_with("who ")
        || lower.starts_with("show ")
        || lower.starts_with("list ")
        || lower.starts_with("tell ")
        || lower.starts_with("explain ")
        || lower.starts_with("describe ")
        || lower.starts_with("summarize ")
        || lower.starts_with("summarise ")
        || lower.starts_with("compare ")
        || lower.starts_with("analyze ")
        || lower.starts_with("analyse ")
        || lower.starts_with("can ")
        || lower.starts_with("does ")
        || lower.starts_with("is ")
        || lower.starts_with("are ")
        || lower.starts_with("do ")
        || lower.starts_with("status")
        || lower.starts_with("help")
    {
        return Intent::Query;
    }

    // Fallback: if nothing else matched, treat as a query (send to LLM)
    Intent::Query
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

/// Public wrapper for approval queue to call
pub async fn execute_approved_intent(intent: &Intent, message: &str, state: &AppState) -> String {
    execute_intent(intent, message, state).await
}

async fn execute_intent(intent: &Intent, message: &str, state: &AppState) -> String {
    match intent {
        Intent::Query => {
            // Answer queries — try local context first, then LLM
            let lower = message.to_ascii_lowercase();
            if lower.contains("status") || lower.contains("health") {
                let sessions = state.sessions.read().len();
                let evidence = *state.evidence_count.read();
                let cloud = state.cloud_config.read().is_some();
                format!(
                    "System status: {} active sessions, {} evidence entries, cloud {}.",
                    sessions, evidence, if cloud { "connected" } else { "disconnected" }
                )
            } else if lower.contains("app") && (lower.contains("how many") || lower.contains("list") || lower.contains("count")) {
                let apps = crate::utils::scan_app_dirs();
                format!("You have {} apps installed.", apps.len())
            } else {
                // Call LLM — try Claude CLI first, then OpenRouter API
                match call_llm(message).await {
                    Ok(response) => response,
                    Err(_) => format!("I understand: '{}'. Connect an LLM (sign in or add API key) for detailed answers.", message),
                }
            }
        }
        Intent::Navigate => {
            let url = extract_url(message).unwrap_or_else(|| message.to_string());
            format!("Navigation to '{}' dispatched via runtime.", url)
        }
        Intent::RunApp => {
            let app_name = extract_app_name(message);
            let lower_msg = message.to_ascii_lowercase();

            // QA dispatch: "run visual qa", "qa api", "test security", etc.
            let qa_types = ["visual", "api", "accessibility", "security", "performance", "evidence", "integration"];
            let matched_qa = qa_types.iter().find(|t| lower_msg.contains(*t));

            if lower_msg.contains("qa") || lower_msg.starts_with("test ") {
                if let Some(qa_type) = matched_qa {
                    // Extract target URL if present, default to localhost:8888
                    let target = extract_url(message)
                        .unwrap_or_else(|| "http://localhost:8888/dashboard".to_string());
                    let client = reqwest::Client::new();
                    match client.post("http://localhost:8888/api/v1/qa/run")
                        .json(&serde_json::json!({"qa_type": qa_type, "target": target}))
                        .send().await
                    {
                        Ok(resp) => {
                            if let Ok(result) = resp.json::<serde_json::Value>().await {
                                let passed = result.get("passed").and_then(|v| v.as_bool()).unwrap_or(false);
                                let total = result.get("total_checks").and_then(|v| v.as_u64()).unwrap_or(0);
                                let pass_count = result.get("passed_checks").and_then(|v| v.as_u64()).unwrap_or(0);
                                let run_id = result.get("run_id").and_then(|v| v.as_str()).unwrap_or("unknown");
                                let status = if passed { "PASS" } else { "FAIL" };
                                format!("{} QA on {}: {} ({}/{} checks). Run ID: {}",
                                    qa_type.to_uppercase(), target, status, pass_count, total, run_id)
                            } else {
                                format!("{} QA completed but could not parse result.", qa_type)
                            }
                        }
                        Err(e) => format!("{} QA failed: {}", qa_type, e),
                    }
                } else {
                    // Run all 7 QA types
                    let target = extract_url(message)
                        .unwrap_or_else(|| "http://localhost:8888/dashboard".to_string());
                    let client = reqwest::Client::new();
                    let mut results = Vec::new();
                    for qt in &qa_types {
                        if let Ok(resp) = client.post("http://localhost:8888/api/v1/qa/run")
                            .json(&serde_json::json!({"qa_type": qt, "target": target}))
                            .send().await
                        {
                            if let Ok(r) = resp.json::<serde_json::Value>().await {
                                let p = r.get("passed").and_then(|v| v.as_bool()).unwrap_or(false);
                                let pc = r.get("passed_checks").and_then(|v| v.as_u64()).unwrap_or(0);
                                let tc = r.get("total_checks").and_then(|v| v.as_u64()).unwrap_or(0);
                                results.push(format!("{}: {}/{} {}", qt, pc, tc, if p { "PASS" } else { "FAIL" }));
                            }
                        }
                    }
                    format!("Full QA on {}:\n{}", target, results.join("\n"))
                }
            } else {
                match crate::app_engine::runner::run_app(&app_name, state).await {
                    Ok(path) => format!("App '{}' completed. Report: {}", app_name, path.display()),
                    Err(e) => format!("App '{}' failed: {}", app_name, e),
                }
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

// ─── LLM Integration ────────────────────────────────────────────────

/// Public wrapper for other modules to call LLM
pub async fn call_llm_public(message: &str) -> Result<String, String> {
    call_llm(message).await
}

/// Call an LLM to answer a query. Tries: OpenRouter API → Claude CLI → error.
async fn call_llm(message: &str) -> Result<String, String> {
    // Try 1: OpenRouter API (if OPENROUTER_API_KEY set)
    if let Ok(api_key) = std::env::var("OPENROUTER_API_KEY") {
        if !api_key.is_empty() {
            let client = reqwest::Client::new();
            let resp = client
                .post("https://openrouter.ai/api/v1/chat/completions")
                .bearer_auth(&api_key)
                .json(&serde_json::json!({
                    "model": "anthropic/claude-haiku-4-5",
                    "messages": [
                        {"role": "system", "content": "You are Yinyang, the AI assistant for Solace Browser. Answer concisely in 1-3 sentences. You help users manage their AI apps, domains, and automation workflows."},
                        {"role": "user", "content": message}
                    ],
                    "max_tokens": 300,
                }))
                .timeout(std::time::Duration::from_secs(15))
                .send()
                .await
                .map_err(|e| e.to_string())?;

            if resp.status().is_success() {
                let body: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
                if let Some(content) = body["choices"][0]["message"]["content"].as_str() {
                    return Ok(content.to_string());
                }
            }
        }
    }

    // Try 2: Claude CLI (if installed)
    let claude_path = which_claude();
    if let Some(path) = claude_path {
        let output = tokio::process::Command::new(&path)
            .args(["--print", "--model", "haiku", message])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            let response = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !response.is_empty() {
                return Ok(response);
            }
        }
    }

    Err("No LLM available".to_string())
}

fn which_claude() -> Option<String> {
    for path in &[
        "/home/phuc/.local/bin/claude",
        "/usr/local/bin/claude",
        "/usr/bin/claude",
    ] {
        if std::path::Path::new(path).exists() {
            return Some(path.to_string());
        }
    }
    // Try which
    std::process::Command::new("which")
        .arg("claude")
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                Some(String::from_utf8_lossy(&o.stdout).trim().to_string())
            } else {
                None
            }
        })
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
#[derive(Debug, Clone)]
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
    fn classify_fallback_to_query() {
        // Unknown inputs now fall back to Query (GLOW 617 — broadened intent)
        assert_eq!(classify_intent("banana"), Intent::Query);
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
