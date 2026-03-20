// Diagram: 05-solace-runtime-architecture
use axum::http::Request;
use axum::middleware::{self, Next};
use axum::response::Response;
use axum::Router;
use std::time::Instant;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;

async fn add_service_headers(req: Request<axum::body::Body>, next: Next) -> Response {
    let start = Instant::now();
    let mut response = next.run(req).await;
    let duration_ms = start.elapsed().as_millis();
    response
        .headers_mut()
        .insert("X-Service-Id", "solace-runtime".parse().unwrap());
    response
        .headers_mut()
        .insert("X-Duration-Ms", duration_ms.to_string().parse().unwrap());
    response
        .headers_mut()
        .insert("X-Frame-Options", "DENY".parse().unwrap());
    response
        .headers_mut()
        .insert("X-Content-Type-Options", "nosniff".parse().unwrap());
    response
        .headers_mut()
        .insert(
            "Content-Security-Policy",
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:* https://*.solaceagi.com; img-src 'self' data: https:; connect-src 'self' ws://localhost:* http://localhost:* https://*.solaceagi.com https://*.googleapis.com"
                .parse()
                .unwrap(),
        );
    response
}

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
        .merge(crate::routes::app_create::routes())
        .merge(crate::routes::esign::routes())
        .merge(crate::routes::hub_control::routes())
        .merge(crate::routes::tunnel::routes())
        .merge(crate::routes::qa::routes())
        .merge(crate::routes::events::routes())
        .merge(crate::routes::backoffice::routes())
        .layer(middleware::from_fn(add_service_headers))
        .layer(TraceLayer::new_for_http())
        .layer(cors)
        .with_state(state)
}
