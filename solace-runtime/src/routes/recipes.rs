// Diagram: 15-recipe-engine-fsm
use axum::{extract::State, routing::{get, post}, Json, Router};
use serde::Deserialize;
use serde_json::json;

use crate::recipe::{execute_recipe, RecipeCache};
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/recipes", get(list_recipes))
        .route("/api/v1/recipes/execute", post(run_recipe))
}

async fn list_recipes() -> Json<serde_json::Value> {
    let cache = RecipeCache::new();
    let recipes: Vec<_> = cache.list().iter().map(|r| {
        json!({
            "recipe_id": r.recipe_id,
            "task_hash": r.task_hash,
            "steps": r.steps.len(),
            "replay_count": r.replay_count,
            "verified": r.verified,
            "created_at": r.created_at,
        })
    }).collect();
    Json(json!({"recipes": recipes, "count": recipes.len()}))
}

#[derive(Deserialize)]
struct ExecuteRequest {
    task: String,
}

async fn run_recipe(
    State(state): State<AppState>,
    Json(req): Json<ExecuteRequest>,
) -> Json<serde_json::Value> {
    let mut cache = RecipeCache::new();
    let result = execute_recipe(&req.task, &mut cache);

    *state.evidence_count.write() += 1;
    crate::routes::budget::record_budget_event(&state);

    Json(json!({
        "state": result.state,
        "recipe_id": result.recipe_id,
        "task_hash": result.task_hash,
        "cache_hit": result.cache_hit,
        "replay_count": result.replay_count,
        "steps_executed": result.steps_executed,
        "evidence_hash": result.evidence_hash,
    }))
}
