use std::fs;
use std::sync::{Mutex, OnceLock};

use axum::{
    body::{to_bytes, Body},
    http::{Request, StatusCode},
};
use chrono::{TimeZone, Utc};
use serde_json::{json, Value};
use solace_runtime::{build_router, cron, pzip, AppState};
use tower::ServiceExt;

fn test_lock() -> &'static Mutex<()> {
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
}

fn test_home(name: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "solace-runtime-tests-{name}-{}-{}",
        std::process::id(),
        Utc::now().timestamp_nanos_opt().unwrap_or_default()
    ));
    fs::create_dir_all(&dir).unwrap();
    dir
}

fn configure_home(path: &std::path::Path) {
    std::env::set_var("SOLACE_HOME", path);
}

async fn response_json(response: axum::response::Response) -> Value {
    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    serde_json::from_slice(&body).unwrap()
}

fn install_app(home: &std::path::Path, domain: &str, app_id: &str, manifest: &str) {
    let app_dir = home.join("apps").join(domain).join(app_id);
    fs::create_dir_all(&app_dir).unwrap();
    fs::write(app_dir.join("manifest.yaml"), manifest).unwrap();
}

#[tokio::test]
async fn test_health_endpoint() {
    let _guard = test_lock().lock().unwrap();
    let home = test_home("health");
    configure_home(&home);

    let app = build_router(AppState::new());
    let resp = app
        .oneshot(Request::get("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_apps_list() {
    let _guard = test_lock().lock().unwrap();
    let home = test_home("apps-list");
    configure_home(&home);
    install_app(
        &home,
        "news.ycombinator.com",
        "hackernews-feed",
        "id: hackernews-feed\nname: Hacker News Feed\ndescription: Daily digest\ntemplate: feed-digest.html\n",
    );

    let app = build_router(AppState::new());
    let resp = app
        .oneshot(Request::get("/api/apps").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = response_json(resp).await;
    assert_eq!(body["apps"][0]["id"], "hackernews-feed");
}

#[tokio::test]
async fn test_schedules_crud() {
    let _guard = test_lock().lock().unwrap();
    let home = test_home("schedules-crud");
    configure_home(&home);
    let app = build_router(AppState::new());

    let create = app
        .clone()
        .oneshot(
            Request::post("/api/schedules")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"app_id": "morning-brief", "cron": "*/5 * * * *", "label": "Morning brief"}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(create.status(), StatusCode::OK);
    let created = response_json(create).await;
    let schedule_id = created["schedule"]["id"].as_str().unwrap().to_string();

    let list = app
        .clone()
        .oneshot(Request::get("/api/schedules").body(Body::empty()).unwrap())
        .await
        .unwrap();
    let list_body = response_json(list).await;
    assert_eq!(list_body["schedules"].as_array().unwrap().len(), 1);

    let update = app
        .clone()
        .oneshot(
            Request::put(format!("/api/schedules/{schedule_id}"))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"app_id": "morning-brief", "cron": "0 8 * * *", "label": "Daily brief", "enabled": true}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(update.status(), StatusCode::OK);

    let delete = app
        .oneshot(
            Request::delete(format!("/api/schedules/{schedule_id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(delete.status(), StatusCode::OK);

    let persisted: Value = serde_json::from_str(
        &fs::read_to_string(home.join("daemon").join("schedules.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(persisted.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn test_cron_matches() {
    let now = Utc.with_ymd_and_hms(2026, 3, 10, 8, 15, 0).unwrap();
    assert!(cron::cron_matches("*/15 8 * * 2", &now));
    assert!(cron::cron_matches("15 8 10 3 2", &now));
    assert!(cron::cron_matches("15 8 9-11 3 1,2,3", &now));
    assert!(!cron::cron_matches("14 8 * * 2", &now));
}

#[tokio::test]
async fn test_pzip_json_roundtrip() {
    let raw = br#"[{"id":1,"name":"solace"},{"id":2,"name":"runtime","ok":true}]"#;
    let packed = pzip::json::compress(raw).unwrap();
    let unpacked = pzip::json::decompress(&packed).unwrap();
    assert_eq!(unpacked, raw);
}

#[tokio::test]
async fn test_evidence_chain_integrity() {
    let mut chain = pzip::evidence::EvidenceChain::new();
    chain.append("brief", "run-1", b"report-1", "local@solace");
    chain.append("brief", "run-2", b"report-2", "local@solace");
    assert!(chain.verify());
}
