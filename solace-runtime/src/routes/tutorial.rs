// Diagram: hub-tutorial (TUTORIAL, FUNPACKS, INSTALL)
use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;

use crate::state::{AppState, TUTORIAL_STEPS};

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/tutorial/status", get(tutorial_status))
        .route("/api/v1/tutorial/complete", post(complete_step))
        .route("/api/v1/tutorial/reset", post(reset_tutorial))
        .route("/api/v1/funpacks", get(list_funpacks))
}

/// Built-in fun packs — personality themes for the sidebar.
const FUNPACKS: &[(&str, &str, &str)] = &[
    ("zen", "Zen Garden", "Calm, minimal, meditative responses. Uses nature metaphors."),
    ("pirate", "Pirate Mode", "Arr! Every response in pirate speak. Treasure = evidence."),
    ("haiku", "Haiku Master", "Responses in 5-7-5 syllable haiku format when possible."),
    ("coach", "Motivational Coach", "Energetic, encouraging. Every task is a victory lap."),
    ("detective", "Detective Noir", "Mysterious, investigative tone. Evidence = clues."),
    ("chef", "Chef's Kitchen", "Cooking metaphors. Tasks = recipes. Results = dishes served."),
    ("space", "Mission Control", "NASA-style communications. Tasks = missions. T-minus countdown."),
];

/// GET /api/v1/funpacks
///
/// Returns available fun packs — personality themes for the sidebar.
/// Users can activate a fun pack to change the sidebar's tone and style.
async fn list_funpacks() -> Json<serde_json::Value> {
    let packs: Vec<_> = FUNPACKS
        .iter()
        .map(|(id, name, description)| {
            json!({
                "id": id,
                "name": name,
                "description": description,
            })
        })
        .collect();
    Json(json!({
        "funpacks": packs,
        "count": packs.len(),
        "active": serde_json::Value::Null,
    }))
}

/// GET /api/v1/tutorial/status
///
/// Returns the current tutorial progress: completed steps, total steps,
/// current step number, and the list of all step names.
async fn tutorial_status(State(state): State<AppState>) -> Json<serde_json::Value> {
    let tutorial = state.tutorial.read();
    let steps: Vec<&str> = TUTORIAL_STEPS.to_vec();

    Json(json!({
        "completed_steps": tutorial.completed_steps,
        "total_steps": TUTORIAL_STEPS.len(),
        "current_step": tutorial.current_step(),
        "all_complete": tutorial.is_complete(),
        "steps": steps,
    }))
}

#[derive(Deserialize)]
struct CompletePayload {
    step: String,
}

/// POST /api/v1/tutorial/complete
///
/// Marks a tutorial step as completed. Valid steps: "run_first_app",
/// "view_evidence", "try_chat". Returns error if step name is invalid.
async fn complete_step(
    State(state): State<AppState>,
    Json(payload): Json<CompletePayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let mut tutorial = state.tutorial.write();
    let newly_completed = tutorial.complete_step(&payload.step);

    if !TUTORIAL_STEPS.contains(&payload.step.as_str()) {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({
                "error": format!("invalid step: '{}'. Valid steps: {:?}", payload.step, TUTORIAL_STEPS),
            })),
        ));
    }

    // Persist to disk
    let solace_home = crate::utils::solace_home();
    let daemon_dir = solace_home.join("daemon");
    let _ = std::fs::create_dir_all(&daemon_dir);
    let _ = crate::persistence::write_json(&daemon_dir.join("tutorial.json"), &*tutorial);

    Ok(Json(json!({
        "step": payload.step,
        "newly_completed": newly_completed,
        "completed_steps": tutorial.completed_steps,
        "total_steps": TUTORIAL_STEPS.len(),
        "current_step": tutorial.current_step(),
        "all_complete": tutorial.is_complete(),
    })))
}

/// POST /api/v1/tutorial/reset
///
/// Resets the tutorial progress — clears all completed steps.
async fn reset_tutorial(State(state): State<AppState>) -> Json<serde_json::Value> {
    let mut tutorial = state.tutorial.write();
    tutorial.completed_steps.clear();

    // Persist to disk
    let solace_home = crate::utils::solace_home();
    let daemon_dir = solace_home.join("daemon");
    let _ = std::fs::create_dir_all(&daemon_dir);
    let _ = crate::persistence::write_json(&daemon_dir.join("tutorial.json"), &*tutorial);

    Json(json!({
        "reset": true,
        "completed_steps": tutorial.completed_steps,
        "total_steps": TUTORIAL_STEPS.len(),
        "current_step": tutorial.current_step(),
    }))
}
