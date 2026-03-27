// Diagram: 30-budget-tracking
use axum::{extract::State, routing::get, Json, Router};
use serde_json::json;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/budget", get(budget_status.clone()))
        .route("/api/v1/budget/status", get(budget_status))
        .route(
            "/api/v1/budget/config",
            get(budget_config).put(update_budget_config),
        )
}

async fn budget_status(State(state): State<AppState>) -> Json<serde_json::Value> {
    let solace_home = crate::utils::solace_home();
    let config = crate::config::load_budget_config(&solace_home);
    let usage = state.budget_usage.read().clone();
    let blocked = usage.is_blocked(&config);

    Json(json!({
        "config": config,
        "usage": {
            "app_runs": *state.app_count.read(),
            "evidence_events": *state.evidence_count.read(),
            "daily_count": usage.daily_count,
            "daily_date": usage.daily_date,
            "monthly_count": usage.monthly_count,
            "monthly_date": usage.monthly_date,
        },
        "blocked": blocked,
        "active_budget": config.daily_limit.saturating_sub(usage.daily_count),
    }))
}

async fn budget_config() -> Json<serde_json::Value> {
    let config = crate::config::load_budget_config(&crate::utils::solace_home());
    Json(json!({"config": config}))
}

async fn update_budget_config(
    Json(payload): Json<crate::config::BudgetConfig>,
) -> Json<serde_json::Value> {
    let solace_home = crate::utils::solace_home();
    let _ = crate::config::save_budget_config(&solace_home, &payload);
    Json(json!({"config": payload}))
}

/// Record a budget event (called when evidence_count increments).
/// Returns `true` if the budget is now blocked (limit exceeded).
pub fn record_budget_event(state: &AppState) -> bool {
    let solace_home = crate::utils::solace_home();
    let config = crate::config::load_budget_config(&solace_home);
    let mut usage = state.budget_usage.write();
    usage.record_event();
    let _ = crate::config::save_budget_usage(&solace_home, &usage);
    usage.is_blocked(&config)
}
