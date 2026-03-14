use axum::{response::Html, routing::get, Router};
use tower_http::services::ServeDir;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/", get(index))
        .route("/onboarding", get(onboarding_page))
        .route("/sidebar", get(sidebar_page))
        .nest_service("/assets", ServeDir::new("templates"))
}

async fn index() -> Html<String> {
    Html(page(
        "Solace Runtime",
        "Local-first runtime active on port 8888.",
    ))
}

async fn onboarding_page() -> Html<String> {
    Html(page(
        "Onboarding",
        "Four-state onboarding gate for the Solace sidebar.",
    ))
}

async fn sidebar_page() -> Html<String> {
    Html(page(
        "Sidebar",
        "Yinyang sidebar backend is available at /api/v1/sidebar/state.",
    ))
}

fn page(title: &str, body: &str) -> String {
    format!(
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>{}</title><link rel=\"stylesheet\" href=\"/assets/runtime.css\"></head><body><main><h1>{}</h1><p>{}</p></main></body></html>",
        html_escape::encode_text(title),
        html_escape::encode_text(title),
        html_escape::encode_text(body),
    )
}
