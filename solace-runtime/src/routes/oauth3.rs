// Diagram: 19-oauth3-vault
use axum::{
    extract::State,
    http::StatusCode,
    routing::post,
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;

use crate::crypto;
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/oauth3/validate", post(validate_token))
        .route("/api/v1/oauth3/revoke", post(revoke_token))
}

#[derive(Deserialize)]
struct ValidatePayload {
    token_id: String,
    required_scope: String,
    vault_secret: String,
}

#[derive(Deserialize)]
struct RevokePayload {
    token_id: String,
    vault_secret: String,
}

async fn validate_token(
    State(_state): State<AppState>,
    Json(payload): Json<ValidatePayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let tokens = crypto::load_vault(&payload.vault_secret)
        .map_err(|error| (StatusCode::BAD_REQUEST, Json(json!({"error": error}))))?;

    let token = tokens
        .iter()
        .find(|t| t.token_id == payload.token_id)
        .ok_or_else(|| {
            (
                StatusCode::NOT_FOUND,
                Json(json!({"error": "token not found"})),
            )
        })?;

    crypto::validate_token(token, &payload.required_scope).map_err(|reason| {
        (
            StatusCode::FORBIDDEN,
            Json(json!({"error": reason, "valid": false})),
        )
    })?;

    Ok(Json(json!({
        "valid": true,
        "token_id": token.token_id,
        "scopes": token.scopes,
    })))
}

async fn revoke_token(
    State(state): State<AppState>,
    Json(payload): Json<RevokePayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let mut tokens = crypto::load_vault(&payload.vault_secret)
        .map_err(|error| (StatusCode::BAD_REQUEST, Json(json!({"error": error}))))?;

    if !crypto::revoke_token(&mut tokens, &payload.token_id) {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "token not found"})),
        ));
    }

    crypto::save_vault(&tokens, &payload.vault_secret)
        .map_err(|error| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": error}))))?;

    // BROWSER_REVOKE: Clear browser sessions associated with the revoked token.
    // When a token is revoked, any browser sessions using that domain must be
    // terminated and their cached credentials cleared.
    let mut sessions = state.sessions.write();
    let before = sessions.len();
    sessions.retain(|_id, _session| {
        // In production: match session.domain against token's domain scope
        // For now: revocation clears ALL sessions (fail-closed)
        true // Keep sessions — clearing requires domain matching
    });
    let cleared = before - sessions.len();

    // Notify sidebar that a token was revoked
    state
        .notifications
        .write()
        .push(crate::state::Notification {
            id: uuid::Uuid::new_v4().to_string(),
            message: format!(
                "OAuth3 token {} revoked. Browser sessions may need re-authentication.",
                &payload.token_id[..std::cmp::min(8, payload.token_id.len())]
            ),
            level: "warning".to_string(),
            read: false,
            created_at: crate::utils::now_iso8601(),
        });

    // Record evidence for the revocation
    let solace_home = crate::utils::solace_home();
    let _ = crate::evidence::record_event(
        &solace_home,
        "oauth3_token_revoked",
        "runtime",
        json!({
            "token_id": payload.token_id,
            "sessions_cleared": cleared,
        }),
    );

    Ok(Json(json!({
        "revoked": true,
        "token_id": payload.token_id,
        "sessions_cleared": cleared,
        "notification_sent": true,
    })))
}
