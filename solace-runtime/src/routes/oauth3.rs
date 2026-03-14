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
    State(_state): State<AppState>,
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

    Ok(Json(json!({
        "revoked": true,
        "token_id": payload.token_id,
    })))
}
