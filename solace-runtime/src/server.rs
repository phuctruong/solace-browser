// Diagram: 05-solace-runtime-architecture
use axum::Router;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;

pub fn build_router(state: crate::state::AppState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        .merge(crate::routes::health::routes())
        .merge(crate::routes::agents::routes())
        .merge(crate::routes::apps::routes())
        .merge(crate::routes::schedules::routes())
        .merge(crate::routes::sessions::routes())
        .merge(crate::routes::evidence::routes())
        .merge(crate::routes::notifications::routes())
        .merge(crate::routes::oauth3::routes())
        .merge(crate::routes::domains::routes())
        .merge(crate::routes::cloud::routes())
        .merge(crate::routes::sidebar::routes())
        .merge(crate::routes::websocket::routes())
        .merge(crate::routes::chat::routes())
        .merge(crate::routes::recipes::routes())
        .merge(crate::routes::wiki::routes())
        .merge(crate::routes::budget::routes())
        .merge(crate::routes::browser_control::routes())
        .merge(crate::routes::files::routes())
        .merge(crate::routes::delight::routes())
        .merge(crate::routes::tutorial::routes())
        .merge(crate::routes::tunnel::routes())
        .merge(crate::routes::events::routes())
        .layer(TraceLayer::new_for_http())
        .layer(cors)
        .with_state(state)
}
