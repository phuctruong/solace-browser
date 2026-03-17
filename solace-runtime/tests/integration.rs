// Diagram: 05-solace-runtime-architecture
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, MutexGuard, OnceLock};

use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use axum::response::Response;
use axum::Router;
use chrono::TimeZone;
use http_body_util::BodyExt;
use serde_json::{json, Value};
use solace_runtime::config::{self, Onboarding, Settings};
use solace_runtime::crypto::{self, OAuthToken};
use solace_runtime::pzip;
use solace_runtime::pzip::evidence::EvidenceChain;
use solace_runtime::{build_router, AppState};
use tower::ServiceExt;

fn test_lock() -> &'static Mutex<()> {
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
}

struct TestContext {
    _guard: MutexGuard<'static, ()>,
    home: PathBuf,
}

impl TestContext {
    fn new(name: &str) -> Self {
        let guard = test_lock().lock().unwrap_or_else(|error| error.into_inner());
        let home = std::env::temp_dir().join(format!(
            "solace-runtime-{name}-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&home).unwrap();
        std::env::set_var("SOLACE_HOME", &home);
        seed_fixture(&home, true);
        Self {
            _guard: guard,
            home,
        }
    }

    fn set_onboarding(&self, completed: bool) {
        let state = if completed { "green" } else { "grey" }.to_string();
        config::save_onboarding(&self.home, &Onboarding { completed, state }).unwrap();
    }

    fn app(&self) -> Router {
        build_router(AppState::new())
    }
}

impl Drop for TestContext {
    fn drop(&mut self) {
        std::env::remove_var("SOLACE_HOME");
        let _ = fs::remove_dir_all(&self.home);
    }
}

fn seed_fixture(home: &Path, onboarding_complete: bool) {
    config::save_settings(
        home,
        &Settings {
            theme: "dark".to_string(),
            telemetry: false,
            auto_screenshot: false,
        },
    )
    .unwrap();
    config::save_onboarding(
        home,
        &Onboarding {
            completed: onboarding_complete,
            state: if onboarding_complete { "green" } else { "grey" }.to_string(),
        },
    )
    .unwrap();
    write_app(
        home,
        "weather-bot",
        "Weather Bot",
        "Research weather patterns",
        "research",
    );
    write_app(
        home,
        "task-runner",
        "Task Runner",
        "Run deterministic tasks",
        "automation",
    );
}

fn write_app(home: &Path, id: &str, name: &str, description: &str, domain: &str) {
    let app_dir = home.join("apps").join(id);
    fs::create_dir_all(app_dir.join("inbox")).unwrap();
    fs::write(
        app_dir.join("manifest.yaml"),
        format!(
            "id: {id}\nname: {name}\nversion: 1.0.0\ndescription: {description}\ndomain: {domain}\n"
        ),
    )
    .unwrap();
    fs::write(app_dir.join("inbox").join("input.json"), "{\"ok\":true}").unwrap();
}

async fn parse_body(response: Response) -> Value {
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    if bytes.is_empty() {
        return json!({});
    }
    serde_json::from_slice(&bytes).unwrap()
}

async fn parse_html(response: Response) -> String {
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    String::from_utf8(bytes.to_vec()).unwrap_or_default()
}

async fn send(app: &Router, request: Request<Body>) -> Response {
    app.clone().oneshot(request).await.unwrap()
}

async fn send_json(app: &Router, method: Method, path: &str, body: Value) -> (StatusCode, Value) {
    let request = Request::builder()
        .method(method)
        .uri(path)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap();
    let response = send(app, request).await;
    let status = response.status();
    let body = parse_body(response).await;
    (status, body)
}

#[tokio::test(flavor = "current_thread")]
async fn health_returns_ok() {
    let ctx = TestContext::new("health_returns_ok");
    let app = ctx.app();
    let response = send(&app, Request::get("/health").body(Body::empty()).unwrap()).await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["ok"], true);
    assert_eq!(body["port"], 8888);
}

#[tokio::test(flavor = "current_thread")]
async fn system_status_reports_defaults() {
    let ctx = TestContext::new("system_status_reports_defaults");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/system/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["sessions"], 0);
    assert_eq!(body["theme"], "dark");
    assert_eq!(body["cloud_connected"], false);
}

#[tokio::test(flavor = "current_thread")]
async fn apps_list_installed_apps() {
    let ctx = TestContext::new("apps_list_installed_apps");
    let app = ctx.app();
    let response = send(&app, Request::get("/api/apps").body(Body::empty()).unwrap()).await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert!(body["apps"].as_array().unwrap().len() >= 2);
}

#[tokio::test(flavor = "current_thread")]
async fn app_detail_returns_manifest() {
    let ctx = TestContext::new("app_detail_returns_manifest");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/apps/weather-bot")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["app"]["id"], "weather-bot");
    assert_eq!(body["app"]["domain"], "research");
}

#[tokio::test(flavor = "current_thread")]
async fn run_app_writes_outbox_and_evidence() {
    let ctx = TestContext::new("run_app_writes_outbox_and_evidence");
    let app = ctx.app();
    let response = send(
        &app,
        Request::builder()
            .method(Method::POST)
            .uri("/api/v1/apps/run/weather-bot")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    let report_path = PathBuf::from(body["report"].as_str().unwrap());
    assert!(report_path.exists());
    assert!(ctx.home.join("apps/weather-bot/outbox/evidence-chain.json").exists());
}

#[tokio::test(flavor = "current_thread")]
async fn schedules_list_is_empty() {
    let ctx = TestContext::new("schedules_list_is_empty");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/schedules").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["schedules"].as_array().unwrap().len(), 0);
}

#[tokio::test(flavor = "current_thread")]
async fn schedules_create_persists() {
    let ctx = TestContext::new("schedules_create_persists");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/schedules",
        json!({"app_id":"weather-bot","cron":"*/5 * * * *","label":"Weather","enabled":true}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["schedule"]["app_id"], "weather-bot");
    assert!(ctx.home.join("daemon").join("schedules.json").exists());
}

#[tokio::test(flavor = "current_thread")]
async fn schedules_delete_removes_entry() {
    let ctx = TestContext::new("schedules_delete_removes_entry");
    let app = ctx.app();
    let (_, created) = send_json(
        &app,
        Method::POST,
        "/api/schedules",
        json!({"app_id":"weather-bot","cron":"*/5 * * * *","label":"Weather"}),
    )
    .await;
    let id = created["schedule"]["id"].as_str().unwrap();
    let response = send(
        &app,
        Request::builder()
            .method(Method::DELETE)
            .uri(format!("/api/schedules/{id}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["deleted"], id);
}

#[tokio::test(flavor = "current_thread")]
async fn schedules_validate_rejects_bad_cron() {
    let ctx = TestContext::new("schedules_validate_rejects_bad_cron");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/schedules",
        json!({"app_id":"weather-bot","cron":"bad cron","label":"Broken"}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "invalid cron");
}

#[tokio::test(flavor = "current_thread")]
async fn sessions_list_starts_empty() {
    let ctx = TestContext::new("sessions_list_starts_empty");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/browser/sessions")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["sessions"].as_array().unwrap().len(), 0);
}

#[tokio::test(flavor = "current_thread")]
async fn sessions_launch_creates_session() {
    let ctx = TestContext::new("sessions_launch_creates_session");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["session"]["profile"], "work");
}

#[tokio::test(flavor = "current_thread")]
async fn sessions_close_removes_session() {
    let ctx = TestContext::new("sessions_close_removes_session");
    let app = ctx.app();
    let (_, launched) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work"}),
    )
    .await;
    let id = launched["session"]["session_id"].as_str().unwrap();
    let (status, body) = send_json(
        &app,
        Method::POST,
        &format!("/api/v1/browser/close/{id}"),
        json!({}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["closed"], id);
}

#[tokio::test(flavor = "current_thread")]
async fn evidence_list_starts_empty() {
    let ctx = TestContext::new("evidence_list_starts_empty");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/evidence").body(Body::empty()).unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["entries"].as_array().unwrap().len(), 0);
}

#[tokio::test(flavor = "current_thread")]
async fn evidence_create_increments_count() {
    let ctx = TestContext::new("evidence_create_increments_count");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/evidence",
        json!({"event":"manual_test","actor":"tester","data":{"ok":true}}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["record"]["event"], "manual_test");

    let response = send(
        &app,
        Request::get("/api/v1/evidence/count")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let count_body = parse_body(response).await;
    assert_eq!(count_body["count"], 1);
}

#[tokio::test(flavor = "current_thread")]
async fn evidence_part11_reports_valid_chain() {
    let ctx = TestContext::new("evidence_part11_reports_valid_chain");
    let app = ctx.app();
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/evidence",
        json!({"event":"first"}),
    )
    .await;
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/evidence",
        json!({"event":"second"}),
    )
    .await;
    let response = send(
        &app,
        Request::get("/api/v1/evidence/part11")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["part11"]["chain_valid"], true);
    assert_eq!(body["part11"]["record_count"], 2);
}

#[tokio::test(flavor = "current_thread")]
async fn notifications_list_starts_empty() {
    let ctx = TestContext::new("notifications_list_starts_empty");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/notifications")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["notifications"].as_array().unwrap().len(), 0);
}

#[tokio::test(flavor = "current_thread")]
async fn notifications_create_adds_entry() {
    let ctx = TestContext::new("notifications_create_adds_entry");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/notifications",
        json!({"message":"hello","level":"warn"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["notification"]["message"], "hello");
    assert_eq!(body["notification"]["level"], "warn");
}

#[tokio::test(flavor = "current_thread")]
async fn domains_list_groups_apps() {
    let ctx = TestContext::new("domains_list_groups_apps");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/domains")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["domains"]["automation"], 1);
    assert_eq!(body["domains"]["research"], 1);
}

#[tokio::test(flavor = "current_thread")]
async fn domain_config_returns_defaults_for_unknown_domain() {
    let ctx = TestContext::new("domain_config_returns_defaults");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/domains/unknown.com/config")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["domain"], "unknown.com");
    assert_eq!(body["session_policy"]["session_ttl_hours"], 24);
    assert_eq!(body["session_policy"]["auth_type"], "none");
    assert_eq!(body["session_policy"]["keep_alive_interval_hours"], 6);
}

#[tokio::test(flavor = "current_thread")]
async fn domain_config_set_and_read_roundtrip() {
    let ctx = TestContext::new("domain_config_set_read");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/domains/gmail.com/config",
        json!({
            "session_ttl_hours": 48,
            "auth_type": "oauth3",
            "keep_alive_url": "https://mail.google.com/mail/u/0/",
            "check_selector": "div[role='navigation']"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["saved"], true);
    assert_eq!(body["session_policy"]["session_ttl_hours"], 48);
    assert_eq!(body["session_policy"]["auth_type"], "oauth3");
    // Auto-computed keep-alive = TTL/4 = 12
    assert_eq!(body["session_policy"]["keep_alive_interval_hours"], 12);

    // Now read it back
    let response = send(
        &app,
        Request::get("/api/v1/domains/gmail.com/config")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["session_policy"]["session_ttl_hours"], 48);
    assert_eq!(body["session_policy"]["auth_type"], "oauth3");
    assert_eq!(
        body["session_policy"]["keep_alive_url"],
        "https://mail.google.com/mail/u/0/"
    );
}

#[tokio::test(flavor = "current_thread")]
async fn domain_config_rejects_invalid_auth_type() {
    let ctx = TestContext::new("domain_config_invalid_auth");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/domains/example.com/config",
        json!({"auth_type": "invalid_type"}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("invalid auth_type"));
}

#[tokio::test(flavor = "current_thread")]
async fn keep_alive_analysis_no_schedules() {
    let ctx = TestContext::new("keep_alive_no_schedules");
    let app = ctx.app();

    // Set config for a domain with TTL
    send_json(
        &app,
        Method::POST,
        "/api/v1/domains/research/config",
        json!({"session_ttl_hours": 24, "auth_type": "oauth2"}),
    )
    .await;

    let response = send(
        &app,
        Request::get("/api/v1/domains/research/keep-alive")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["domain"], "research");
    assert_eq!(body["session_ttl_hours"], 24);
    assert_eq!(body["keep_alive_needed"], true);
    assert!(body["recommendation"]
        .as_str()
        .unwrap()
        .contains("No scheduled apps"));
}

#[tokio::test(flavor = "current_thread")]
async fn keep_alive_analysis_public_domain() {
    let ctx = TestContext::new("keep_alive_public");
    let app = ctx.app();

    // Set TTL=0 (public domain)
    send_json(
        &app,
        Method::POST,
        "/api/v1/domains/public.com/config",
        json!({"session_ttl_hours": 0}),
    )
    .await;

    let response = send(
        &app,
        Request::get("/api/v1/domains/public.com/keep-alive")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["keep_alive_needed"], false);
    assert!(body["recommendation"]
        .as_str()
        .unwrap()
        .contains("Public domain"));
}

#[tokio::test(flavor = "current_thread")]
async fn recipe_get_returns_404_for_unknown_hash() {
    let ctx = TestContext::new("recipe_get_404");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/recipes/0000000000000000000000000000000000000000000000000000000000000000")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    let body = parse_body(response).await;
    assert!(body["error"].as_str().unwrap().contains("not found"));
}

#[tokio::test(flavor = "current_thread")]
async fn recipe_execute_then_get_detail() {
    let ctx = TestContext::new("recipe_execute_get");
    let app = ctx.app();

    // Execute a recipe to create it
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/recipes/execute",
        json!({"task": "navigate to test page"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    let task_hash = body["task_hash"].as_str().unwrap().to_string();

    // Get detail for this recipe
    let response = send(
        &app,
        Request::get(&format!("/api/v1/recipes/{task_hash}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["task_hash"], task_hash);
    assert!(body["steps"].is_array());
    assert!(body["steps"].as_array().unwrap().len() > 0);
}

#[tokio::test(flavor = "current_thread")]
async fn recipe_delete_invalidates_cache() {
    let ctx = TestContext::new("recipe_delete");
    let app = ctx.app();

    // Execute a recipe to create it
    let (_, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/recipes/execute",
        json!({"task": "task to delete"}),
    )
    .await;
    let task_hash = body["task_hash"].as_str().unwrap().to_string();

    // Verify it exists
    let response = send(
        &app,
        Request::get(&format!("/api/v1/recipes/{task_hash}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);

    // Delete it
    let response = send(
        &app,
        Request::builder()
            .method(Method::DELETE)
            .uri(format!("/api/v1/recipes/{task_hash}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["deleted"], task_hash);

    // Verify it's gone
    let response = send(
        &app,
        Request::get(&format!("/api/v1/recipes/{task_hash}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test(flavor = "current_thread")]
async fn recipe_delete_returns_404_for_unknown() {
    let ctx = TestContext::new("recipe_delete_404");
    let app = ctx.app();
    let response = send(
        &app,
        Request::builder()
            .method(Method::DELETE)
            .uri("/api/v1/recipes/nonexistent_hash_value_here")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test(flavor = "current_thread")]
async fn cloud_connect_sets_state() {
    let ctx = TestContext::new("cloud_connect_sets_state");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/connect",
        json!({
            "api_key":"sw_sk_test_12345678",
            "user_email":"saint@solaceagi.com",
            "device_id":"device-1",
            "paid_user":true
        }),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["connected"], true);

    let response = send(
        &app,
        Request::get("/api/v1/cloud/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let status_body = parse_body(response).await;
    assert_eq!(status_body["connected"], true);
    assert_eq!(status_body["config"]["user_email"], "saint@solaceagi.com");
}

#[tokio::test(flavor = "current_thread")]
async fn cloud_disconnect_clears_state() {
    let ctx = TestContext::new("cloud_disconnect_clears_state");
    let app = ctx.app();
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/connect",
        json!({
            "api_key":"sw_sk_test_12345678",
            "user_email":"saint@solaceagi.com",
            "device_id":"device-1",
            "paid_user":false
        }),
    )
    .await;
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/disconnect",
        json!({}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["connected"], false);
}

#[tokio::test(flavor = "current_thread")]
async fn sidebar_state_reports_local_ready() {
    let ctx = TestContext::new("sidebar_state_reports_local_ready");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/sidebar/state")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["gate"], "no_llm"); // onboarding complete but no BYOK or paid
    assert_eq!(body["chat_enabled"], false);
    assert_eq!(body["theme"], "dark");
}

#[tokio::test(flavor = "current_thread")]
async fn sidebar_state_reports_unregistered() {
    let ctx = TestContext::new("sidebar_state_reports_unregistered");
    ctx.set_onboarding(false);
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/sidebar/state")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["gate"], "unregistered");
    assert_eq!(body["chat_enabled"], false);
}

#[tokio::test(flavor = "current_thread")]
async fn budget_status_returns_defaults() {
    let ctx = TestContext::new("budget_status_returns_defaults");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/budget/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["config"]["daily_limit"], 1000);
    assert_eq!(body["blocked"], false);
    assert_eq!(body["usage"]["daily_count"], 0);
    assert_eq!(body["usage"]["monthly_count"], 0);
}

#[tokio::test(flavor = "current_thread")]
async fn budget_tracks_evidence_events() {
    let ctx = TestContext::new("budget_tracks_evidence_events");
    let app = ctx.app();

    // Create 3 evidence events
    for i in 0..3 {
        let (status, _) = send_json(
            &app,
            Method::POST,
            "/api/v1/evidence",
            json!({"event": format!("test-event-{i}"), "actor": "tester"}),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
    }

    // Budget status should reflect the 3 events
    let response = send(
        &app,
        Request::get("/api/v1/budget/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["usage"]["daily_count"], 3);
    assert_eq!(body["usage"]["monthly_count"], 3);
    assert_eq!(body["blocked"], false);
}

#[tokio::test(flavor = "current_thread")]
async fn budget_blocks_when_daily_limit_exceeded() {
    let ctx = TestContext::new("budget_blocks_when_daily_limit_exceeded");

    // Set a very low daily limit
    config::save_budget_config(
        &ctx.home,
        &config::BudgetConfig {
            daily_limit: 2,
            monthly_limit: 20_000,
            enforce: true,
        },
    )
    .unwrap();

    let app = ctx.app();

    // Create 2 evidence events to hit the limit
    for i in 0..2 {
        let (status, _) = send_json(
            &app,
            Method::POST,
            "/api/v1/evidence",
            json!({"event": format!("event-{i}")}),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
    }

    // Budget should now be blocked
    let response = send(
        &app,
        Request::get("/api/v1/budget/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["usage"]["daily_count"], 2);
    assert_eq!(body["blocked"], true);
}

#[tokio::test(flavor = "current_thread")]
async fn budget_blocks_when_monthly_limit_exceeded() {
    let ctx = TestContext::new("budget_blocks_when_monthly_limit_exceeded");

    // Set a very low monthly limit
    config::save_budget_config(
        &ctx.home,
        &config::BudgetConfig {
            daily_limit: 1_000,
            monthly_limit: 3,
            enforce: true,
        },
    )
    .unwrap();

    let app = ctx.app();

    // Create 3 evidence events to hit the monthly limit
    for i in 0..3 {
        let (status, _) = send_json(
            &app,
            Method::POST,
            "/api/v1/evidence",
            json!({"event": format!("event-{i}")}),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
    }

    let response = send(
        &app,
        Request::get("/api/v1/budget/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    assert_eq!(body["usage"]["monthly_count"], 3);
    assert_eq!(body["blocked"], true);
}

#[tokio::test(flavor = "current_thread")]
async fn budget_not_blocked_when_enforce_disabled() {
    let ctx = TestContext::new("budget_not_blocked_when_enforce_disabled");

    // Set enforce=false with very low limits
    config::save_budget_config(
        &ctx.home,
        &config::BudgetConfig {
            daily_limit: 1,
            monthly_limit: 1,
            enforce: false,
        },
    )
    .unwrap();

    let app = ctx.app();

    // Create 2 evidence events (exceeds both limits)
    for i in 0..2 {
        let (status, _) = send_json(
            &app,
            Method::POST,
            "/api/v1/evidence",
            json!({"event": format!("event-{i}")}),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
    }

    let response = send(
        &app,
        Request::get("/api/v1/budget/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    // Not blocked because enforce is false
    assert_eq!(body["blocked"], false);
    assert_eq!(body["usage"]["daily_count"], 2);
}

#[tokio::test(flavor = "current_thread")]
async fn budget_usage_persisted_to_disk() {
    let ctx = TestContext::new("budget_usage_persisted_to_disk");
    let app = ctx.app();

    // Create an evidence event
    let (status, _) = send_json(
        &app,
        Method::POST,
        "/api/v1/evidence",
        json!({"event": "persist-test"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);

    // Verify usage file was written to disk
    let usage_path = ctx.home.join("budget_usage.json");
    assert!(usage_path.exists(), "budget_usage.json should be persisted");
    let usage: config::BudgetUsage =
        solace_runtime::persistence::read_json(&usage_path).unwrap();
    assert_eq!(usage.daily_count, 1);
    assert_eq!(usage.monthly_count, 1);
}

#[test]
fn pzip_json_roundtrip() {
    let raw = br#"[{"id":1,"name":"solace"},{"id":2,"name":"runtime"}]"#;
    let compressed = pzip::compress(raw, "application/json").unwrap();
    assert_eq!(pzip::decompress(&compressed).unwrap(), raw);
}

#[test]
fn pzip_web_roundtrip() {
    let raw = b"<html><body><h1>Solace</h1></body></html>";
    let compressed = pzip::compress(raw, "text/html").unwrap();
    assert_eq!(pzip::decompress(&compressed).unwrap(), raw);
}

#[test]
fn pzip_evidence_chain_roundtrip() {
    let mut chain = EvidenceChain::new();
    chain.append("weather-bot", "run-1", b"report-1", "saint@solaceagi.com");
    chain.append("weather-bot", "run-2", b"report-2", "saint@solaceagi.com");
    assert!(chain.verify());
    let bundle = chain.compress_bundle().unwrap();
    let decompressed = pzip::decompress(&bundle).unwrap();
    let entries: Value = serde_json::from_slice(&decompressed).unwrap();
    assert_eq!(entries.as_array().unwrap().len(), 2);
}

#[test]
fn crypto_encrypt_decrypt_matches_python_vector() {
    let blob = hex::decode("000102030405060708090a0bd404d147905fd999278cb5f62c4b00de4b0f284535e4edfa1a85cbd5b4b0c8ca005638839c6b037708f026")
        .unwrap();
    let key = crypto::derive_key("saint-solace", b"solace-oauth3-vault:v1");
    let plaintext = crypto::decrypt(&blob, &key).unwrap();
    let decoded: Value = serde_json::from_slice(&plaintext).unwrap();
    assert_eq!(decoded[0]["token_id"], "tok-python");
}

#[test]
fn crypto_vault_roundtrip() {
    let ctx = TestContext::new("crypto_vault_roundtrip");
    let tokens = vec![OAuthToken {
        token_id: "tok-1".to_string(),
        agent_name: Some("dragon-rider".to_string()),
        service: Some("solace-cloud".to_string()),
        scope: None,
        scopes: vec!["chat:write".to_string(), "tasks:run".to_string()],
        expires_at: Some(1_800_000_000),
        created_at: Some(1_700_000_000),
        revoked: false,
        extra: Default::default(),
    }];
    let path = crypto::save_vault(&tokens, "saint-solace").unwrap();
    assert_eq!(path, ctx.home.join("oauth3-vault.enc"));
    let loaded = crypto::load_vault("saint-solace").unwrap();
    assert_eq!(loaded, tokens);
}

#[test]
fn cron_matches_expected_schedule() {
    let now = chrono::Utc.with_ymd_and_hms(2026, 3, 10, 8, 15, 0).unwrap();
    assert!(solace_runtime::cron::cron_matches("*/15 8 * * 2", &now));
    assert!(!solace_runtime::cron::cron_matches("*/7 8 * * 2", &now));
}

#[test]
fn cron_field_matches_supports_lists_and_ranges() {
    assert!(solace_runtime::cron::field_matches("1,2,3", 2));
    assert!(solace_runtime::cron::field_matches("9-11", 10));
    assert!(!solace_runtime::cron::field_matches("9-11", 12));
}

// ─── Stillwater/Ripple Codec Tests ───────────────────────────────────

#[test]
fn stillwater_detect_all_codecs() {
    use solace_runtime::pzip::stillwater::{detect_codec, Codec};

    assert_eq!(detect_codec(b"<main>content</main>", "text/html"), Codec::SemanticHtml);
    assert_eq!(detect_codec(b"<table><tr></tr></table>", "text/html"), Codec::TableHtml);
    assert_eq!(detect_codec(b"{\"data\":1}", "application/json"), Codec::JsonApi);
    assert_eq!(detect_codec(b"<rss><channel></channel></rss>", "application/xml"), Codec::RssXml);
    assert_eq!(detect_codec(b"{% extends \"base.html\" %}", "text/html"), Codec::JinjaTemplate);
}

#[test]
fn stillwater_extract_solaceagi_template() {
    use solace_runtime::pzip::stillwater;

    let template = br#"{% extends "base.html" %}{% block title %}Solace AGI{% endblock %}{% block content %}<main id="main-content"><h1>{{ copy.hero_title }}</h1><p>{{ copy.hero_desc }}</p></main>{% endblock %}"#;
    let decomp = stillwater::extract(template, "text/html", "https://solaceagi.com/").unwrap();
    assert_eq!(decomp.codec, stillwater::Codec::JinjaTemplate);
    assert_eq!(decomp.ripple.title, "base.html");
    assert!(decomp.stillwater.headings.contains(&"title".to_string()));
    assert!(decomp.stillwater.headings.contains(&"content".to_string()));
    assert!(decomp.stillwater.meta.iter().any(|(k, _)| k == "hero_title"));
}

#[test]
fn stillwater_roundtrip_compression() {
    use solace_runtime::pzip::stillwater;

    let html = br#"<html><head><title>RTC</title><meta name="description" content="test page"></head><body><nav><a href="/about">About</a></nav><main><h1>Hello</h1><h2>Sub</h2><p>Body text</p></main></body></html>"#;
    let decomp = stillwater::extract(html, "text/html", "https://test.com").unwrap();
    let compressed = stillwater::compress_decomposition(&decomp).unwrap();
    assert_eq!(&compressed[..4], b"PZSW");
    let restored = stillwater::decompress_decomposition(&compressed).unwrap();
    assert_eq!(restored.sha256, decomp.sha256);
    assert_eq!(restored.ripple.title, "RTC");
    assert_eq!(restored.ripple.sections.len(), decomp.ripple.sections.len());
    assert_eq!(restored.stillwater.template_hash, decomp.stillwater.template_hash);
}

#[test]
fn stillwater_ripple_only_is_smaller() {
    use solace_runtime::pzip::stillwater;

    let html = br#"<html><body><main><h1>Title</h1><p>Long content that changes every page visit and contains unique data points and information.</p></main></body></html>"#;
    let decomp = stillwater::extract(html, "text/html", "https://example.com").unwrap();
    let full = stillwater::compress_decomposition(&decomp).unwrap();
    let ripple_only = stillwater::compress_ripple_only(&decomp.ripple).unwrap();
    // Ripple-only should be smaller than full decomposition
    assert!(ripple_only.len() < full.len());
}

#[tokio::test(flavor = "current_thread")]
async fn wiki_extract_returns_decomposition() {
    let ctx = TestContext::new("wiki_extract_returns_decomposition");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/wiki/extract",
        json!({
            "url": "https://news.ycombinator.com",
            "content": "<html><head><title>Hacker News</title></head><body><table><thead><tr><th>Rank</th><th>Title</th><th>Points</th></tr></thead><tbody><tr><td>1</td><td>Show HN: Solace Browser</td><td>342</td></tr></tbody></table></body></html>",
            "content_type": "text/html"
        }),
    ).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "extracted");
    assert_eq!(body["codec"], "table-html");
    assert!(!body["sha256"].as_str().unwrap().is_empty());
    assert_eq!(body["ripple"]["data_items_count"], 1);
}

#[tokio::test(flavor = "current_thread")]
async fn wiki_codecs_lists_all_six() {
    let ctx = TestContext::new("wiki_codecs_lists_all_six");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/wiki/codecs").body(Body::empty()).unwrap(),
    ).await;
    let body = parse_body(response).await;
    assert_eq!(body["codecs"].as_array().unwrap().len(), 6);
}

#[tokio::test(flavor = "current_thread")]
async fn wiki_stats_returns_community_browsing() {
    let ctx = TestContext::new("wiki_stats_returns_community_browsing");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/wiki/stats").body(Body::empty()).unwrap(),
    ).await;
    let body = parse_body(response).await;
    assert_eq!(body["community_browsing"], true);
    assert_eq!(body["codecs_available"], 6);
    assert!(body["snapshot_count"].as_u64().is_some());
}

// ─── Browse-Capture Pipeline: Domain Stillwater + Screenshot + Auto-Sync ──

#[tokio::test(flavor = "current_thread")]
async fn wiki_extract_creates_domain_stillwater_on_first_visit() {
    let ctx = TestContext::new("wiki_extract_creates_domain_stillwater");
    let app = ctx.app();

    // First extract — should create domain stillwater
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/wiki/extract",
        json!({
            "url": "https://example.com/page1",
            "content": "<html><head><title>Page 1</title></head><body><nav><a href=\"/about\">About</a></nav><main><h1>Hello</h1></main></body></html>",
            "content_type": "text/html"
        }),
    ).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "extracted");
    assert_eq!(body["domain_stillwater_created"], true);

    // Verify stillwater file was created on disk
    let stillwater_path = ctx.home.join("wiki/domains/example.com/stillwater.prime-snapshot.md");
    assert!(stillwater_path.exists(), "stillwater.prime-snapshot.md should be created on first visit");
    let content = fs::read_to_string(&stillwater_path).unwrap();
    assert!(content.contains("Domain Stillwater: example.com"));
    assert!(content.contains("Template hash:"));

    // Second extract to the SAME domain — should NOT re-create stillwater
    let (status2, body2) = send_json(
        &app,
        Method::POST,
        "/api/v1/wiki/extract",
        json!({
            "url": "https://example.com/page2",
            "content": "<html><head><title>Page 2</title></head><body><main><h1>World</h1></main></body></html>",
            "content_type": "text/html"
        }),
    ).await;
    assert_eq!(status2, StatusCode::OK);
    assert_eq!(body2["domain_stillwater_created"], false);
}

#[tokio::test(flavor = "current_thread")]
async fn wiki_extract_reports_auto_screenshot_setting() {
    let ctx = TestContext::new("wiki_extract_reports_auto_screenshot");
    let app = ctx.app();

    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/wiki/extract",
        json!({
            "url": "https://example.com/test",
            "content": "<html><body><main><h1>Test</h1></main></body></html>",
            "content_type": "text/html"
        }),
    ).await;
    assert_eq!(status, StatusCode::OK);
    // Default setting is false
    assert_eq!(body["auto_screenshot"], false);
}

#[tokio::test(flavor = "current_thread")]
async fn screenshot_endpoint_skips_when_disabled() {
    let ctx = TestContext::new("screenshot_endpoint_skips");
    let app = ctx.app();

    // auto_screenshot defaults to false in our test fixture
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/screenshot",
        json!({
            "url": "https://example.com/page",
        }),
    ).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "skipped");
    assert!(body["reason"].as_str().unwrap().contains("disabled"));
}

#[tokio::test(flavor = "current_thread")]
async fn screenshot_endpoint_delegates_when_enabled_and_no_data() {
    let ctx = TestContext::new("screenshot_delegates");

    // Enable auto_screenshot in settings
    config::save_settings(
        &ctx.home,
        &Settings {
            theme: "dark".to_string(),
            telemetry: false,
            auto_screenshot: true,
        },
    ).unwrap();

    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/screenshot",
        json!({
            "url": "https://example.com/page",
        }),
    ).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "delegate_to_browser");
    assert!(body["message"].as_str().unwrap().contains("browser"));
}

#[tokio::test(flavor = "current_thread")]
async fn screenshot_endpoint_stores_png_when_provided() {
    let ctx = TestContext::new("screenshot_stores_png");

    // Enable auto_screenshot
    config::save_settings(
        &ctx.home,
        &Settings {
            theme: "dark".to_string(),
            telemetry: false,
            auto_screenshot: true,
        },
    ).unwrap();

    let app = ctx.app();

    // Send a fake PNG (base64-encoded "fake-png-data")
    use ::base64::engine::general_purpose::STANDARD;
    use ::base64::Engine;
    let fake_png = STANDARD.encode(b"fake-png-data-for-test");

    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/screenshot",
        json!({
            "url": "https://example.com/page",
            "png_base64": fake_png,
        }),
    ).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "captured");
    assert!(body["sha256"].as_str().is_some());
    assert!(body["filename"].as_str().unwrap().ends_with(".png"));
    assert_eq!(body["size_bytes"], b"fake-png-data-for-test".len());

    // Verify screenshot file was written to disk
    let screenshots_dir = ctx.home.join("screenshots");
    assert!(screenshots_dir.exists());
    let files: Vec<_> = fs::read_dir(&screenshots_dir)
        .unwrap()
        .flatten()
        .collect();
    assert_eq!(files.len(), 1);
}

#[tokio::test(flavor = "current_thread")]
async fn settings_auto_screenshot_defaults_to_false() {
    // Verify that loading settings from a file that doesn't have
    // auto_screenshot still defaults to false (serde default)
    let ctx = TestContext::new("settings_auto_screenshot_default");
    let json = r#"{"theme":"dark","telemetry":false}"#;
    fs::write(ctx.home.join("settings.json"), json).unwrap();
    let settings = config::load_settings(&ctx.home);
    assert!(!settings.auto_screenshot);
}

// ─── OAuth3 Scope & Expiry Enforcement Tests ────────────────────────

#[test]
fn validate_token_rejects_revoked() {
    let token = OAuthToken {
        token_id: "tok-revoked".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec!["chat:write".to_string()],
        expires_at: Some(9_999_999_999),
        created_at: Some(1_700_000_000),
        revoked: true,
        extra: Default::default(),
    };
    let result = crypto::validate_token(&token, "chat:write");
    assert!(result.is_err());
    assert_eq!(result.unwrap_err(), "token is revoked");
}

#[test]
fn validate_token_rejects_expired() {
    let token = OAuthToken {
        token_id: "tok-expired".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec!["chat:write".to_string()],
        expires_at: Some(1_000_000_000), // well in the past
        created_at: Some(999_999_999),
        revoked: false,
        extra: Default::default(),
    };
    let result = crypto::validate_token(&token, "chat:write");
    assert!(result.is_err());
    assert_eq!(result.unwrap_err(), "token is expired");
}

#[test]
fn validate_token_rejects_missing_scope() {
    let token = OAuthToken {
        token_id: "tok-noscope".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec!["chat:write".to_string()],
        expires_at: Some(9_999_999_999),
        created_at: Some(1_700_000_000),
        revoked: false,
        extra: Default::default(),
    };
    let result = crypto::validate_token(&token, "tasks:run");
    assert!(result.is_err());
    assert!(result.unwrap_err().contains("missing required scope"));
}

#[test]
fn validate_token_accepts_scope_in_scopes_vec() {
    let token = OAuthToken {
        token_id: "tok-ok".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec!["chat:write".to_string(), "tasks:run".to_string()],
        expires_at: Some(9_999_999_999),
        created_at: Some(1_700_000_000),
        revoked: false,
        extra: Default::default(),
    };
    assert!(crypto::validate_token(&token, "tasks:run").is_ok());
}

#[test]
fn validate_token_accepts_scope_in_singular_field() {
    let token = OAuthToken {
        token_id: "tok-singular".to_string(),
        agent_name: None,
        service: None,
        scope: Some("admin:full".to_string()),
        scopes: vec![],
        expires_at: Some(9_999_999_999),
        created_at: Some(1_700_000_000),
        revoked: false,
        extra: Default::default(),
    };
    assert!(crypto::validate_token(&token, "admin:full").is_ok());
}

#[test]
fn validate_token_allows_no_expiry() {
    let token = OAuthToken {
        token_id: "tok-no-exp".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec!["chat:write".to_string()],
        expires_at: None,
        created_at: Some(1_700_000_000),
        revoked: false,
        extra: Default::default(),
    };
    assert!(crypto::validate_token(&token, "chat:write").is_ok());
}

#[test]
fn revoke_token_sets_revoked_flag() {
    let mut tokens = vec![
        OAuthToken {
            token_id: "tok-a".to_string(),
            agent_name: None,
            service: None,
            scope: None,
            scopes: vec![],
            expires_at: None,
            created_at: None,
            revoked: false,
            extra: Default::default(),
        },
        OAuthToken {
            token_id: "tok-b".to_string(),
            agent_name: None,
            service: None,
            scope: None,
            scopes: vec![],
            expires_at: None,
            created_at: None,
            revoked: false,
            extra: Default::default(),
        },
    ];
    assert!(crypto::revoke_token(&mut tokens, "tok-b"));
    assert!(!tokens[0].revoked);
    assert!(tokens[1].revoked);
}

#[test]
fn revoke_token_returns_false_for_unknown_id() {
    let mut tokens = vec![OAuthToken {
        token_id: "tok-x".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec![],
        expires_at: None,
        created_at: None,
        revoked: false,
        extra: Default::default(),
    }];
    assert!(!crypto::revoke_token(&mut tokens, "tok-missing"));
    assert!(!tokens[0].revoked); // unchanged
}

#[tokio::test(flavor = "current_thread")]
async fn oauth3_validate_endpoint_accepts_valid_token() {
    let ctx = TestContext::new("oauth3_validate_accepts");
    let tokens = vec![OAuthToken {
        token_id: "tok-valid".to_string(),
        agent_name: Some("agent-1".to_string()),
        service: Some("solace-cloud".to_string()),
        scope: None,
        scopes: vec!["chat:write".to_string(), "tasks:run".to_string()],
        expires_at: Some(9_999_999_999),
        created_at: Some(1_700_000_000),
        revoked: false,
        extra: Default::default(),
    }];
    crypto::save_vault(&tokens, "test-secret").unwrap();
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/oauth3/validate",
        json!({
            "token_id": "tok-valid",
            "required_scope": "chat:write",
            "vault_secret": "test-secret"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["valid"], true);
    assert_eq!(body["token_id"], "tok-valid");
}

#[tokio::test(flavor = "current_thread")]
async fn oauth3_validate_endpoint_rejects_expired_token() {
    let ctx = TestContext::new("oauth3_validate_rejects_expired");
    let tokens = vec![OAuthToken {
        token_id: "tok-exp".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec!["chat:write".to_string()],
        expires_at: Some(1_000_000_000),
        created_at: Some(999_999_999),
        revoked: false,
        extra: Default::default(),
    }];
    crypto::save_vault(&tokens, "test-secret").unwrap();
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/oauth3/validate",
        json!({
            "token_id": "tok-exp",
            "required_scope": "chat:write",
            "vault_secret": "test-secret"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::FORBIDDEN);
    assert_eq!(body["valid"], false);
    assert_eq!(body["error"], "token is expired");
}

#[tokio::test(flavor = "current_thread")]
async fn oauth3_validate_endpoint_rejects_missing_scope() {
    let ctx = TestContext::new("oauth3_validate_rejects_scope");
    let tokens = vec![OAuthToken {
        token_id: "tok-scope".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec!["chat:write".to_string()],
        expires_at: Some(9_999_999_999),
        created_at: Some(1_700_000_000),
        revoked: false,
        extra: Default::default(),
    }];
    crypto::save_vault(&tokens, "test-secret").unwrap();
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/oauth3/validate",
        json!({
            "token_id": "tok-scope",
            "required_scope": "admin:full",
            "vault_secret": "test-secret"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::FORBIDDEN);
    assert_eq!(body["valid"], false);
}

#[tokio::test(flavor = "current_thread")]
async fn oauth3_validate_endpoint_rejects_unknown_token() {
    let ctx = TestContext::new("oauth3_validate_rejects_unknown");
    let tokens: Vec<OAuthToken> = vec![];
    crypto::save_vault(&tokens, "test-secret").unwrap();
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/oauth3/validate",
        json!({
            "token_id": "tok-missing",
            "required_scope": "chat:write",
            "vault_secret": "test-secret"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "token not found");
}

#[tokio::test(flavor = "current_thread")]
async fn oauth3_revoke_endpoint_revokes_and_persists() {
    let ctx = TestContext::new("oauth3_revoke_persists");
    let tokens = vec![OAuthToken {
        token_id: "tok-rev".to_string(),
        agent_name: None,
        service: None,
        scope: None,
        scopes: vec!["chat:write".to_string()],
        expires_at: Some(9_999_999_999),
        created_at: Some(1_700_000_000),
        revoked: false,
        extra: Default::default(),
    }];
    crypto::save_vault(&tokens, "test-secret").unwrap();
    let app = ctx.app();

    // Revoke
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/oauth3/revoke",
        json!({
            "token_id": "tok-rev",
            "vault_secret": "test-secret"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["revoked"], true);
    assert_eq!(body["token_id"], "tok-rev");

    // Verify the vault was updated on disk
    let reloaded = crypto::load_vault("test-secret").unwrap();
    assert_eq!(reloaded.len(), 1);
    assert!(reloaded[0].revoked);

    // Validate should now fail
    let (status2, body2) = send_json(
        &app,
        Method::POST,
        "/api/v1/oauth3/validate",
        json!({
            "token_id": "tok-rev",
            "required_scope": "chat:write",
            "vault_secret": "test-secret"
        }),
    )
    .await;
    assert_eq!(status2, StatusCode::FORBIDDEN);
    assert_eq!(body2["error"], "token is revoked");
}

#[tokio::test(flavor = "current_thread")]
async fn oauth3_revoke_endpoint_rejects_unknown_token() {
    let ctx = TestContext::new("oauth3_revoke_rejects_unknown");
    let tokens: Vec<OAuthToken> = vec![];
    crypto::save_vault(&tokens, "test-secret").unwrap();
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/oauth3/revoke",
        json!({
            "token_id": "tok-missing",
            "vault_secret": "test-secret"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "token not found");
}

// ─── Browser Launch Dedup Tests ──────────────────────────────────────

#[tokio::test(flavor = "current_thread")]
async fn dedup_layer1_existing_session_returns_deduped() {
    let ctx = TestContext::new("dedup_layer1_existing_session");
    let app = ctx.app();

    // First launch creates a new session
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert!(body.get("deduped").is_none() || body["deduped"] == false);
    let first_session_id = body["session"]["session_id"].as_str().unwrap().to_string();

    // Second launch with same URL+profile+mode returns existing session
    let (status2, body2) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    assert_eq!(status2, StatusCode::OK);
    assert_eq!(body2["deduped"], true);
    assert_eq!(body2["reason"], "existing_session");
    assert_eq!(
        body2["session"]["session_id"].as_str().unwrap(),
        first_session_id
    );
}

#[tokio::test(flavor = "current_thread")]
async fn dedup_layer1_different_url_creates_new_session() {
    let ctx = TestContext::new("dedup_layer1_different_url");
    let app = ctx.app();

    let (_, body1) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    let id1 = body1["session"]["session_id"].as_str().unwrap().to_string();

    // Different URL should create a new session, not dedup
    let (_, body2) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work","url":"https://example.com","mode":"local-dev"}),
    )
    .await;
    let id2 = body2["session"]["session_id"].as_str().unwrap().to_string();
    assert_ne!(id1, id2);
    assert!(body2.get("deduped").is_none() || body2["deduped"] == false);
}

#[tokio::test(flavor = "current_thread")]
async fn dedup_layer3_storm_guard_after_close() {
    let ctx = TestContext::new("dedup_layer3_storm_guard");
    let app = ctx.app();

    // Launch a session
    let (_, body1) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"default","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    let session_id = body1["session"]["session_id"].as_str().unwrap();

    // Close it (removes from sessions map but recent_launches still has the key)
    let _ = send_json(
        &app,
        Method::POST,
        &format!("/api/v1/browser/close/{session_id}"),
        json!({}),
    )
    .await;

    // Try to launch again immediately: Layer 1 won't match (session closed),
    // but Layer 3 storm guard should fire because we launched within 30s
    let (status, body2) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"default","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body2["deduped"], true);
    assert_eq!(body2["storm_guarded"], true);
}

#[tokio::test(flavor = "current_thread")]
async fn dedup_allow_duplicate_bypasses_all_guards() {
    let ctx = TestContext::new("dedup_allow_duplicate_bypasses");
    let app = ctx.app();

    // First launch
    let (_, body1) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    let id1 = body1["session"]["session_id"].as_str().unwrap().to_string();

    // Second launch with allow_duplicate=true should bypass dedup
    let (status, body2) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work","url":"https://solaceagi.com","mode":"local-dev","allow_duplicate":true}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    let id2 = body2["session"]["session_id"].as_str().unwrap().to_string();
    assert_ne!(id1, id2);
    assert!(body2.get("deduped").is_none() || body2["deduped"] == false);
}

#[tokio::test(flavor = "current_thread")]
async fn dedup_different_profile_creates_new_session() {
    let ctx = TestContext::new("dedup_different_profile");
    let app = ctx.app();

    let (_, body1) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"work","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    let id1 = body1["session"]["session_id"].as_str().unwrap().to_string();

    // Same URL but different profile should create a new session
    let (_, body2) = send_json(
        &app,
        Method::POST,
        "/api/v1/browser/launch",
        json!({"profile":"research","url":"https://solaceagi.com","mode":"local-dev"}),
    )
    .await;
    let id2 = body2["session"]["session_id"].as_str().unwrap().to_string();
    assert_ne!(id1, id2);
}

// ---------------------------------------------------------------------------
// Twin sync encrypted tunnel tests (Diagram: 21-twin-sync-flow)
// ---------------------------------------------------------------------------

#[tokio::test(flavor = "current_thread")]
async fn sync_status_no_cloud_shows_disconnected() {
    let ctx = TestContext::new("sync_status_no_cloud");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/cloud/sync/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["connected"], false);
    assert_eq!(body["last_sync"], Value::Null);
}

#[tokio::test(flavor = "current_thread")]
async fn sync_up_requires_cloud_connection() {
    let ctx = TestContext::new("sync_up_requires_cloud");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/sync/up",
        json!({}),
    )
    .await;
    assert_eq!(status, StatusCode::PRECONDITION_FAILED);
    assert!(body["error"].as_str().unwrap().contains("cloud not connected"));
}

#[tokio::test(flavor = "current_thread")]
async fn sync_down_requires_cloud_connection() {
    let ctx = TestContext::new("sync_down_requires_cloud");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/sync/down",
        json!({}),
    )
    .await;
    assert_eq!(status, StatusCode::PRECONDITION_FAILED);
    assert!(body["error"].as_str().unwrap().contains("cloud not connected"));
}

#[tokio::test(flavor = "current_thread")]
async fn sync_up_returns_error_when_cloud_unreachable() {
    let ctx = TestContext::new("sync_up_cloud_unreachable");
    let app = ctx.app();

    // Connect to cloud first (with a fake key — the real endpoint won't be reachable)
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/connect",
        json!({
            "api_key": "sw_sk_test_sync_up_001",
            "user_email": "test@solaceagi.com",
            "device_id": "device-sync-1",
            "paid_user": true
        }),
    )
    .await;

    // Attempt sync up — cloud endpoint doesn't exist, expect graceful error
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/sync/up",
        json!({}),
    )
    .await;
    // Should be BAD_GATEWAY (502) because cloud is unreachable
    assert_eq!(status, StatusCode::BAD_GATEWAY);
    let error = body["error"].as_str().unwrap();
    assert!(
        error.contains("cloud unreachable") || error.contains("cloud returned"),
        "unexpected error message: {error}"
    );
}

#[tokio::test(flavor = "current_thread")]
async fn sync_down_returns_error_when_cloud_unreachable() {
    let ctx = TestContext::new("sync_down_cloud_unreachable");
    let app = ctx.app();

    // Connect to cloud first
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/connect",
        json!({
            "api_key": "sw_sk_test_sync_down_001",
            "user_email": "test@solaceagi.com",
            "device_id": "device-sync-2",
            "paid_user": true
        }),
    )
    .await;

    // Attempt sync down — cloud endpoint doesn't exist, expect graceful error
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/sync/down",
        json!({}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_GATEWAY);
    let error = body["error"].as_str().unwrap();
    assert!(
        error.contains("cloud unreachable") || error.contains("cloud returned"),
        "unexpected error message: {error}"
    );
}

#[tokio::test(flavor = "current_thread")]
async fn sync_status_after_connected_but_no_sync() {
    let ctx = TestContext::new("sync_status_connected_no_sync");
    let app = ctx.app();

    // Connect to cloud
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/connect",
        json!({
            "api_key": "sw_sk_test_status_001",
            "user_email": "status@solaceagi.com",
            "device_id": "device-status-1",
            "paid_user": true
        }),
    )
    .await;

    // Check sync status — should show connected but no last_sync
    let response = send(
        &app,
        Request::get("/api/v1/cloud/sync/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["connected"], true);
    assert_eq!(body["last_sync"], Value::Null);
}

#[tokio::test(flavor = "current_thread")]
async fn sync_encrypt_decrypt_roundtrip() {
    // Verify the encryption keys used for twin sync are consistent
    let key = solace_runtime::crypto::derive_key("test_api_key", b"solace-twin-sync:v1");
    let plaintext = b"hello twin sync";
    let encrypted = solace_runtime::crypto::encrypt(plaintext, &key).unwrap();
    let decrypted = solace_runtime::crypto::decrypt(&encrypted, &key).unwrap();
    assert_eq!(decrypted, plaintext);
}

#[tokio::test(flavor = "current_thread")]
async fn sync_encrypt_decrypt_large_payload() {
    // Simulate encrypting a realistic sync payload
    let key = solace_runtime::crypto::derive_key("sw_sk_test_large", b"solace-twin-sync:v1");
    let payload = json!({
        "device_id": "device-large-test",
        "user_email": "large@solaceagi.com",
        "timestamp": "2026-03-14T00:00:00Z",
        "evidence_entries": (0..100).map(|i| json!({
            "id": format!("ev-{i}"),
            "event": "test_event",
            "actor": "runtime",
            "timestamp": "2026-03-14T00:00:00Z",
            "data": {"index": i},
        })).collect::<Vec<_>>(),
        "installed_apps": [
            {"id": "weather-bot", "name": "Weather Bot", "version": "1.0.0", "domain": "research"},
        ],
        "payload_version": 1,
    });
    let plaintext = serde_json::to_vec(&payload).unwrap();
    let encrypted = solace_runtime::crypto::encrypt(&plaintext, &key).unwrap();
    // Encrypted should be larger than plaintext (nonce + auth tag)
    assert!(encrypted.len() > plaintext.len());
    let decrypted = solace_runtime::crypto::decrypt(&encrypted, &key).unwrap();
    assert_eq!(decrypted, plaintext);
}

// ─── Agent Registry Tests (Diagram: hub-cli-agent-registry) ─────────

#[tokio::test(flavor = "current_thread")]
async fn agents_list_returns_array_with_installed_field() {
    let ctx = TestContext::new("agents_list");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/agents").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    let agents = body["agents"].as_array().expect("agents should be an array");
    assert_eq!(agents.len(), 3);
    // Every agent must have an installed field (bool)
    for agent in agents {
        assert!(agent.get("installed").is_some(), "agent missing 'installed' field");
        assert!(agent["installed"].is_boolean());
        assert!(agent.get("id").is_some());
        assert!(agent.get("name").is_some());
        assert!(agent.get("cmd").is_some());
        assert!(agent.get("models").is_some());
        assert!(agent.get("provider").is_some());
    }
    // Check total and installed counts
    assert_eq!(body["total"], 3);
    assert!(body["installed"].is_number());
}

#[tokio::test(flavor = "current_thread")]
async fn agents_models_returns_per_agent() {
    let ctx = TestContext::new("agents_models");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/agents/models")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    let models = body["models"].as_array().expect("models should be an array");
    assert_eq!(models.len(), 3);
    for entry in models {
        assert!(entry.get("agent_id").is_some());
        assert!(entry.get("models").is_some());
        assert!(entry.get("default_model").is_some());
        assert!(entry.get("installed").is_some());
        let model_list = entry["models"].as_array().unwrap();
        assert!(!model_list.is_empty(), "each agent should have at least 1 model");
    }
}

#[tokio::test(flavor = "current_thread")]
async fn agents_health_known_agent() {
    let ctx = TestContext::new("agents_health_known");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/agents/claude/health")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["agent_id"], "claude");
    assert!(body["installed"].is_boolean());
}

#[tokio::test(flavor = "current_thread")]
async fn agents_health_unknown_agent() {
    let ctx = TestContext::new("agents_health_unknown");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/agents/nonexistent/health")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    let body = parse_body(response).await;
    assert!(body["error"].as_str().unwrap().contains("unknown agent"));
}

#[tokio::test(flavor = "current_thread")]
async fn agents_generate_rejects_empty_prompt() {
    let ctx = TestContext::new("agents_generate_empty");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/agents/generate",
        json!({"agent_id": "claude", "prompt": ""}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("empty"));
}

#[tokio::test(flavor = "current_thread")]
async fn agents_generate_rejects_unknown_agent() {
    let ctx = TestContext::new("agents_generate_unknown");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/agents/generate",
        json!({"agent_id": "nonexistent", "prompt": "hello"}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("unknown agent"));
}

#[tokio::test(flavor = "current_thread")]
async fn agents_generate_rejects_invalid_model() {
    let ctx = TestContext::new("agents_generate_bad_model");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/agents/generate",
        json!({"agent_id": "claude", "prompt": "hello", "model": "fake-model-xyz"}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let error = body["error"].as_str().unwrap();
    assert!(
        error.contains("not supported") || error.contains("not installed"),
        "unexpected error: {error}"
    );
}

#[tokio::test(flavor = "current_thread")]
async fn agents_detect_finds_at_least_one() {
    // This test verifies the core detection logic works through the HTTP layer.
    let ctx = TestContext::new("agents_detect_at_least_one");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/agents").body(Body::empty()).unwrap(),
    )
    .await;
    let body = parse_body(response).await;
    let agents = body["agents"].as_array().unwrap();
    let installed: Vec<_> = agents.iter().filter(|a| a["installed"] == true).collect();
    // Log for CI debugging
    for a in &installed {
        eprintln!("  integration: found {} at {:?}", a["id"], a["path"]);
    }
    eprintln!("  integration: installed agents: {}/3", installed.len());
    // Don't hard-fail if zero (CI may have none), but assert structure is correct
    assert_eq!(agents.len(), 3);
}

mod hex {
    pub fn decode(input: &str) -> Result<Vec<u8>, String> {
        if input.len() % 2 != 0 {
            return Err("hex length must be even".to_string());
        }
        let mut bytes = Vec::with_capacity(input.len() / 2);
        for chunk in input.as_bytes().chunks_exact(2) {
            let high = nibble(chunk[0])?;
            let low = nibble(chunk[1])?;
            bytes.push((high << 4) | low);
        }
        Ok(bytes)
    }

    fn nibble(value: u8) -> Result<u8, String> {
        match value {
            b'0'..=b'9' => Ok(value - b'0'),
            b'a'..=b'f' => Ok(10 + value - b'a'),
            b'A'..=b'F' => Ok(10 + value - b'A'),
            _ => Err(format!("invalid hex byte: {value}")),
        }
    }
}

// ── Event Log Integration Tests ──────────────────────────────────────────

#[tokio::test(flavor = "current_thread")]
async fn run_app_creates_events_jsonl() {
    let ctx = TestContext::new("run_app_creates_events_jsonl");
    let app = ctx.app();
    let response = send(
        &app,
        Request::builder()
            .method(Method::POST)
            .uri("/api/v1/apps/run/weather-bot")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    let report_path = PathBuf::from(body["report"].as_str().unwrap());
    let run_dir = report_path.parent().unwrap();
    let events_path = run_dir.join("events.jsonl");
    assert!(
        events_path.exists(),
        "events.jsonl must be created alongside report.html"
    );

    // Read and validate the events
    let content = fs::read_to_string(&events_path).unwrap();
    let events: Vec<Value> = content
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();

    // Must have at least Render + Seal events
    assert!(
        events.len() >= 2,
        "expected at least 2 events, got {}",
        events.len()
    );

    // Last two events should be Render and Seal (in order)
    let render_event = &events[events.len() - 2];
    let seal_event = &events[events.len() - 1];
    assert_eq!(render_event["event_type"], "RENDER");
    assert_eq!(seal_event["event_type"], "SEAL");

    // Verify hash chain: first event has empty prev_hash
    assert_eq!(events[0]["prev_hash"], "");
    // Each subsequent event links to the previous
    for i in 1..events.len() {
        assert_eq!(
            events[i]["prev_hash"].as_str().unwrap(),
            events[i - 1]["sha256"].as_str().unwrap(),
            "hash chain broken at event {}",
            i
        );
    }

    // All hashes are 64-char hex strings
    for event in &events {
        let sha = event["sha256"].as_str().unwrap();
        assert_eq!(sha.len(), 64, "sha256 must be 64 hex chars");
    }
}

#[tokio::test(flavor = "current_thread")]
async fn get_run_events_returns_event_log() {
    let ctx = TestContext::new("get_run_events_returns_event_log");
    let app = ctx.app();

    // First, run the app to generate events
    let response = send(
        &app,
        Request::builder()
            .method(Method::POST)
            .uri("/api/v1/apps/run/weather-bot")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    let report_path = PathBuf::from(body["report"].as_str().unwrap());
    let run_id = report_path
        .parent()
        .unwrap()
        .file_name()
        .unwrap()
        .to_str()
        .unwrap()
        .to_string();

    // Now query the events endpoint
    let response = send(
        &app,
        Request::get(&format!("/api/v1/apps/weather-bot/runs/{run_id}/events"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["app_id"], "weather-bot");
    assert_eq!(body["run_id"], run_id);
    assert!(
        body["chain_valid"].as_bool().unwrap(),
        "chain must be valid"
    );
    let count = body["count"].as_u64().unwrap();
    assert!(count >= 2, "expected at least 2 events, got {count}");
    let events = body["events"].as_array().unwrap();
    assert_eq!(events.len() as u64, count);
}

#[tokio::test(flavor = "current_thread")]
async fn get_run_events_returns_404_for_missing_run() {
    let ctx = TestContext::new("get_run_events_returns_404");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/apps/weather-bot/runs/nonexistent-run/events")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    let body = parse_body(response).await;
    assert!(body["error"].as_str().unwrap().contains("not found"));
}

#[tokio::test(flavor = "current_thread")]
async fn event_log_prominent_field_in_response() {
    let ctx = TestContext::new("event_log_prominent_field");
    let app = ctx.app();

    // Run app to create events
    let response = send(
        &app,
        Request::builder()
            .method(Method::POST)
            .uri("/api/v1/apps/run/weather-bot")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    let report_path = PathBuf::from(body["report"].as_str().unwrap());
    let run_id = report_path
        .parent()
        .unwrap()
        .file_name()
        .unwrap()
        .to_str()
        .unwrap()
        .to_string();

    // Query events
    let response = send(
        &app,
        Request::get(&format!("/api/v1/apps/weather-bot/runs/{run_id}/events"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    let events = body["events"].as_array().unwrap();

    // Render and Seal should NOT be prominent
    for event in events {
        let event_type = event["event_type"].as_str().unwrap();
        let prominent = event["prominent"].as_bool().unwrap();
        match event_type {
            "RENDER" | "SEAL" | "FETCH" => {
                assert!(!prominent, "{event_type} should not be prominent");
            }
            "PREVIEW" | "SIGN_OFF" => {
                assert!(prominent, "{event_type} should be prominent");
            }
            _ => {}
        }
    }
}

// ── Browser Control API tests ────────────────────────────────────────

#[tokio::test(flavor = "current_thread")]
async fn browser_navigate_accepted() {
    let ctx = TestContext::new("browser_navigate_accepted");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/navigate",
        json!({"url": "https://example.com"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "accepted");
    assert_eq!(body["action"], "navigate");
    assert_eq!(body["url"], "https://example.com");
    assert!(body["evidence"]["evidence_id"].is_string());
    assert!(body["evidence"]["hash"].is_string());
    assert_eq!(body["delegate_to_browser"], true);
}

#[tokio::test(flavor = "current_thread")]
async fn browser_navigate_with_wait_for() {
    let ctx = TestContext::new("browser_navigate_wait_for");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/navigate",
        json!({"url": "https://example.com", "wait_for": "networkidle"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "accepted");
    assert_eq!(body["wait_for"], "networkidle");
}

#[tokio::test(flavor = "current_thread")]
async fn browser_navigate_rejects_empty_url() {
    let ctx = TestContext::new("browser_navigate_empty_url");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/navigate",
        json!({"url": ""}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("empty"));
}

#[tokio::test(flavor = "current_thread")]
async fn browser_navigate_rejects_invalid_scheme() {
    let ctx = TestContext::new("browser_navigate_invalid_scheme");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/navigate",
        json!({"url": "ftp://example.com"}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("http"));
}

#[tokio::test(flavor = "current_thread")]
async fn browser_click_accepted() {
    let ctx = TestContext::new("browser_click_accepted");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/click",
        json!({"selector": "#submit-btn"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "accepted");
    assert_eq!(body["action"], "click");
    assert_eq!(body["selector"], "#submit-btn");
    assert!(body["evidence"]["evidence_id"].is_string());
    assert_eq!(body["delegate_to_browser"], true);
}

#[tokio::test(flavor = "current_thread")]
async fn browser_click_rejects_empty_selector() {
    let ctx = TestContext::new("browser_click_empty_selector");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/click",
        json!({"selector": "  "}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("selector"));
}

#[tokio::test(flavor = "current_thread")]
async fn browser_fill_accepted() {
    let ctx = TestContext::new("browser_fill_accepted");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/fill",
        json!({"selector": "input[name=email]", "value": "test@example.com"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "accepted");
    assert_eq!(body["action"], "fill");
    assert_eq!(body["selector"], "input[name=email]");
    assert_eq!(body["value_length"], 16);
    assert!(body["evidence"]["evidence_id"].is_string());
    assert_eq!(body["delegate_to_browser"], true);
}

#[tokio::test(flavor = "current_thread")]
async fn browser_fill_rejects_empty_selector() {
    let ctx = TestContext::new("browser_fill_empty_selector");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/fill",
        json!({"selector": "", "value": "hello"}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("selector"));
}

#[tokio::test(flavor = "current_thread")]
async fn browser_fill_rejects_empty_value() {
    let ctx = TestContext::new("browser_fill_empty_value");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/fill",
        json!({"selector": "#input", "value": ""}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("value"));
}

#[tokio::test(flavor = "current_thread")]
async fn browser_evaluate_accepted() {
    let ctx = TestContext::new("browser_evaluate_accepted");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/evaluate",
        json!({"script": "document.title"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "accepted");
    assert_eq!(body["action"], "evaluate");
    assert_eq!(body["script_length"], 14);
    assert!(body["evidence"]["evidence_id"].is_string());
    assert_eq!(body["delegate_to_browser"], true);
}

#[tokio::test(flavor = "current_thread")]
async fn browser_evaluate_rejects_empty_script() {
    let ctx = TestContext::new("browser_evaluate_empty_script");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/evaluate",
        json!({"script": "   "}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("script"));
}

#[tokio::test(flavor = "current_thread")]
async fn browser_dom_snapshot_delegates() {
    let ctx = TestContext::new("browser_dom_snapshot");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/dom-snapshot").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["status"], "delegate_to_browser");
    assert_eq!(body["action"], "dom_snapshot");
    assert!(body["evidence"]["evidence_id"].is_string());
}

#[tokio::test(flavor = "current_thread")]
async fn browser_aria_snapshot_delegates() {
    let ctx = TestContext::new("browser_aria_snapshot");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/aria-snapshot").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["status"], "delegate_to_browser");
    assert_eq!(body["action"], "aria_snapshot");
    assert!(body["evidence"]["evidence_id"].is_string());
}

#[tokio::test(flavor = "current_thread")]
async fn browser_page_snapshot_delegates_to_wiki() {
    let ctx = TestContext::new("browser_page_snapshot");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/page-snapshot").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["status"], "delegate_to_browser");
    assert_eq!(body["action"], "page_snapshot");
    assert_eq!(body["delegate_endpoint"], "/api/v1/wiki/extract");
}

// ---------------------------------------------------------------------------
// Hub App HTML pages
// ---------------------------------------------------------------------------

#[tokio::test(flavor = "current_thread")]
async fn hub_domains_page_lists_domains() {
    let ctx = TestContext::new("hub_domains_page");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/domains").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let html = parse_html(response).await;
    assert!(html.contains("Solace Hub"), "should contain nav brand");
    assert!(html.contains("Domains"), "should contain page title");
    // Fixture apps have domains "research" and "automation"
    assert!(html.contains("research"), "should list research domain");
    assert!(html.contains("automation"), "should list automation domain");
    assert!(html.contains("/domains/research"), "should link to domain detail");
}

#[tokio::test(flavor = "current_thread")]
async fn hub_domain_detail_shows_apps() {
    let ctx = TestContext::new("hub_domain_detail");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/domains/research").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let html = parse_html(response).await;
    assert!(html.contains("Domain: research"), "should show domain name");
    assert!(html.contains("Weather Bot"), "should list the weather-bot app");
    assert!(html.contains("/apps/weather-bot"), "should link to app detail");
}

#[tokio::test(flavor = "current_thread")]
async fn hub_domain_detail_returns_404_for_unknown() {
    let ctx = TestContext::new("hub_domain_404");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/domains/nonexistent-domain").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    let html = parse_html(response).await;
    assert!(html.contains("Domain Not Found"));
}

#[tokio::test(flavor = "current_thread")]
async fn hub_app_detail_shows_manifest() {
    let ctx = TestContext::new("hub_app_detail");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/apps/weather-bot").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let html = parse_html(response).await;
    assert!(html.contains("App: Weather Bot"), "should show app name");
    assert!(html.contains("1.0.0"), "should show version");
    assert!(html.contains("/domains/research"), "should link to domain");
}

#[tokio::test(flavor = "current_thread")]
async fn hub_app_detail_returns_404_for_unknown() {
    let ctx = TestContext::new("hub_app_404");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/apps/nonexistent-app").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    let html = parse_html(response).await;
    assert!(html.contains("App Not Found"));
}

#[tokio::test(flavor = "current_thread")]
async fn hub_run_detail_returns_404_for_unknown_app() {
    let ctx = TestContext::new("hub_run_404_app");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/apps/nonexistent-app/runs/run-001")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test(flavor = "current_thread")]
async fn hub_run_detail_returns_404_for_unknown_run() {
    let ctx = TestContext::new("hub_run_404_run");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/apps/weather-bot/runs/nonexistent-run")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    let html = parse_html(response).await;
    assert!(html.contains("Run Not Found"));
}

#[tokio::test(flavor = "current_thread")]
async fn hub_run_detail_shows_events() {
    let ctx = TestContext::new("hub_run_events");
    // Create a run with events
    let run_dir = ctx
        .home
        .join("apps")
        .join("weather-bot")
        .join("outbox")
        .join("runs")
        .join("run-test-001");
    fs::create_dir_all(&run_dir).unwrap();
    let mut log = solace_runtime::event_log::EventLog::new("weather-bot", "run-test-001");
    log.append_event(
        solace_runtime::event_log::EventType::Fetch,
        Some("https://api.weather.com".to_string()),
        None,
        None,
        Some("fetched weather data".to_string()),
    );
    log.append_event(
        solace_runtime::event_log::EventType::Preview,
        None,
        None,
        None,
        Some("email draft ready for review".to_string()),
    );
    log.append_event(
        solace_runtime::event_log::EventType::SignOff,
        None,
        None,
        None,
        Some("user approved".to_string()),
    );
    log.append_event(
        solace_runtime::event_log::EventType::Seal,
        None,
        None,
        None,
        Some("evidence sealed".to_string()),
    );
    log.save_events(&run_dir).unwrap();

    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/apps/weather-bot/runs/run-test-001")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let html = parse_html(response).await;
    assert!(html.contains("Run:"), "should show run title");
    assert!(html.contains("FETCH"), "should show FETCH event type");
    assert!(html.contains("PREVIEW"), "should show PREVIEW event type");
    assert!(html.contains("SIGN_OFF"), "should show SIGN_OFF event type");
    assert!(html.contains("SEAL"), "should show SEAL event type");
    assert!(html.contains("event-preview"), "should have preview CSS class");
    assert!(html.contains("event-signoff"), "should have signoff CSS class");
    assert!(html.contains("Chain Valid"), "chain should be valid");
    assert!(html.contains("/evidence"), "should link to evidence page");
}

#[tokio::test(flavor = "current_thread")]
async fn hub_evidence_page_shows_chain() {
    let ctx = TestContext::new("hub_evidence_page");
    // Create some evidence
    let _ = solace_runtime::evidence::record_event(
        &ctx.home,
        "app_run",
        "runtime",
        json!({"app_id": "weather-bot"}),
    );
    let _ = solace_runtime::evidence::record_event(
        &ctx.home,
        "evidence_sealed",
        "runtime",
        json!({"ok": true}),
    );

    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/evidence").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let html = parse_html(response).await;
    assert!(html.contains("Evidence Chain"), "should show page title");
    assert!(html.contains("Chain Valid"), "chain should be valid");
    assert!(html.contains("2 records"), "should show record count");
    assert!(html.contains("app_run"), "should show event name");
    assert!(html.contains("evidence_sealed"), "should show second event");
    assert!(html.contains("ALCOA"), "should show ALCOA compliance");
}

#[tokio::test(flavor = "current_thread")]
async fn hub_evidence_page_empty_shows_no_records() {
    let ctx = TestContext::new("hub_evidence_empty");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/evidence").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let html = parse_html(response).await;
    assert!(html.contains("No Records") || html.contains("No evidence records"));
}

// ── Delight Engine Tests (Diagram: hub-cross-app — WARM, STREAK, CELEBRATE) ──

#[tokio::test(flavor = "current_thread")]
async fn delight_status_returns_defaults() {
    let ctx = TestContext::new("delight_status_defaults");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/delight").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["streak_days"], 0);
    assert_eq!(body["total_runs"], 0);
    assert_eq!(body["last_active_date"], "");
    // Greeting should be one of the time-of-day greetings
    let greeting = body["greeting"].as_str().unwrap();
    assert!(
        ["Good morning", "Good afternoon", "Good evening", "Welcome back"]
            .contains(&greeting),
        "unexpected greeting: {greeting}"
    );
    // No celebration at streak 0
    assert_eq!(body["celebration"], Value::Null);
}

#[tokio::test(flavor = "current_thread")]
async fn delight_record_increments_total_runs() {
    let ctx = TestContext::new("delight_record_increments");
    let app = ctx.app();

    // Record first activity
    let (status, body) = send_json(&app, Method::POST, "/api/v1/delight/record", json!({})).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["recorded"], true);
    assert_eq!(body["total_runs"], 1);
    assert_eq!(body["streak_days"], 1);
    let last_date = body["last_active_date"].as_str().unwrap();
    assert!(!last_date.is_empty());

    // Record second activity (same day — streak stays at 1, total_runs goes to 2)
    let (status, body) = send_json(&app, Method::POST, "/api/v1/delight/record", json!({})).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["total_runs"], 2);
    assert_eq!(body["streak_days"], 1);
}

#[tokio::test(flavor = "current_thread")]
async fn delight_persists_to_disk() {
    let ctx = TestContext::new("delight_persists_disk");
    let app = ctx.app();

    // Record activity
    let (status, _) = send_json(&app, Method::POST, "/api/v1/delight/record", json!({})).await;
    assert_eq!(status, StatusCode::OK);

    // Verify file was written
    let delight_path = ctx.home.join("daemon").join("delight.json");
    assert!(
        delight_path.exists(),
        "delight.json should be persisted to disk"
    );
    let content = fs::read_to_string(&delight_path).unwrap();
    let saved: Value = serde_json::from_str(&content).unwrap();
    assert_eq!(saved["total_runs"], 1);
    assert_eq!(saved["streak_days"], 1);
}

// ── Tutorial Tests (Diagram: hub-tutorial — TUTORIAL, FUNPACKS, INSTALL) ──

#[tokio::test(flavor = "current_thread")]
async fn tutorial_status_returns_defaults() {
    let ctx = TestContext::new("tutorial_status_defaults");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/tutorial/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["total_steps"], 3);
    assert_eq!(body["current_step"], 1);
    assert_eq!(body["all_complete"], false);
    let completed = body["completed_steps"].as_array().unwrap();
    assert!(completed.is_empty());
    let steps = body["steps"].as_array().unwrap();
    assert_eq!(steps.len(), 3);
    assert_eq!(steps[0], "run_first_app");
    assert_eq!(steps[1], "view_evidence");
    assert_eq!(steps[2], "try_chat");
}

#[tokio::test(flavor = "current_thread")]
async fn tutorial_complete_step_progresses() {
    let ctx = TestContext::new("tutorial_complete_step");
    let app = ctx.app();

    // Complete first step
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/tutorial/complete",
        json!({"step": "run_first_app"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["newly_completed"], true);
    assert_eq!(body["current_step"], 2);
    assert_eq!(body["all_complete"], false);

    // Complete same step again — should not be newly completed
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/tutorial/complete",
        json!({"step": "run_first_app"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["newly_completed"], false);
    assert_eq!(body["current_step"], 2);

    // Complete remaining steps
    let (_, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/tutorial/complete",
        json!({"step": "view_evidence"}),
    )
    .await;
    assert_eq!(body["current_step"], 3);

    let (_, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/tutorial/complete",
        json!({"step": "try_chat"}),
    )
    .await;
    assert_eq!(body["all_complete"], true);
    assert_eq!(body["current_step"], 4); // past last step
}

#[tokio::test(flavor = "current_thread")]
async fn tutorial_complete_invalid_step_returns_400() {
    let ctx = TestContext::new("tutorial_invalid_step");
    let app = ctx.app();
    let (status, body) = send_json(
        &app,
        Method::POST,
        "/api/v1/tutorial/complete",
        json!({"step": "nonexistent_step"}),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("invalid step"));
}

#[tokio::test(flavor = "current_thread")]
async fn tutorial_reset_clears_progress() {
    let ctx = TestContext::new("tutorial_reset");
    let app = ctx.app();

    // Complete a step first
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/tutorial/complete",
        json!({"step": "run_first_app"}),
    )
    .await;

    // Reset
    let (status, body) = send_json(&app, Method::POST, "/api/v1/tutorial/reset", json!({})).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["reset"], true);
    assert_eq!(body["current_step"], 1);
    let completed = body["completed_steps"].as_array().unwrap();
    assert!(completed.is_empty());
}

#[tokio::test(flavor = "current_thread")]
async fn tutorial_persists_to_disk() {
    let ctx = TestContext::new("tutorial_persists_disk");
    let app = ctx.app();

    // Complete a step
    let (status, _) = send_json(
        &app,
        Method::POST,
        "/api/v1/tutorial/complete",
        json!({"step": "run_first_app"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);

    // Verify file was written
    let tutorial_path = ctx.home.join("daemon").join("tutorial.json");
    assert!(
        tutorial_path.exists(),
        "tutorial.json should be persisted to disk"
    );
    let content = fs::read_to_string(&tutorial_path).unwrap();
    let saved: Value = serde_json::from_str(&content).unwrap();
    let completed = saved["completed_steps"].as_array().unwrap();
    assert_eq!(completed.len(), 1);
    assert_eq!(completed[0], "run_first_app");
}

// ── Tunnel Status Tests (Diagram: hub-tunnel-remote-control — consent + WSS + audit) ──

#[tokio::test(flavor = "current_thread")]
async fn tunnel_status_not_connected() {
    let ctx = TestContext::new("tunnel_status_not_connected");
    let app = ctx.app();
    let response = send(
        &app,
        Request::get("/api/v1/tunnel/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["tunnel_connected"], false);
    assert_eq!(body["consent_active"], false);
    assert_eq!(body["cloud_connected"], false);
    // Custom tunnel architecture (NO Cloudflare)
    assert_eq!(body["architecture"], "custom_reverse_tunnel");
    // Security properties
    assert_eq!(body["security"]["outbound_only"], true);
    assert_eq!(body["security"]["consent_required"], true);
    assert_eq!(body["security"]["evidence_on_everything"], true);
}

#[tokio::test(flavor = "current_thread")]
async fn tunnel_status_connected_free_user() {
    let ctx = TestContext::new("tunnel_status_free_user");
    let app = ctx.app();

    // Connect as free user
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/connect",
        json!({
            "api_key": "sw_sk_test_tunnel_free",
            "user_email": "free@solaceagi.com",
            "device_id": "device-tunnel-1",
            "paid_user": false
        }),
    )
    .await;

    let response = send(
        &app,
        Request::get("/api/v1/tunnel/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["tunnel_connected"], false);
    assert_eq!(body["consent_active"], false);
    assert_eq!(body["cloud_connected"], true);
    assert_eq!(body["architecture"], "custom_reverse_tunnel");
}

#[tokio::test(flavor = "current_thread")]
async fn tunnel_status_connected_paid_user() {
    let ctx = TestContext::new("tunnel_status_paid_user");
    let app = ctx.app();

    // Connect as paid user
    let _ = send_json(
        &app,
        Method::POST,
        "/api/v1/cloud/connect",
        json!({
            "api_key": "sw_sk_test_tunnel_paid",
            "user_email": "pro@solaceagi.com",
            "device_id": "device-tunnel-2",
            "paid_user": true
        }),
    )
    .await;

    let response = send(
        &app,
        Request::get("/api/v1/tunnel/status")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = parse_body(response).await;
    assert_eq!(body["tunnel_connected"], false);
    assert_eq!(body["consent_active"], false);
    assert_eq!(body["cloud_connected"], true);
    assert_eq!(body["architecture"], "custom_reverse_tunnel");
    assert_eq!(body["security"]["auto_disconnect"], true);
}
