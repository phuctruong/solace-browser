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
