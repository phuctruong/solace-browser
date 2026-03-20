// Diagram: 11-domain-ecosystem
use std::collections::BTreeMap;
use std::path::PathBuf;

use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::get,
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::json;

use crate::state::AppState;

/// Extract root domain from a subdomain.
/// `mail.google.com` → `google.com`, `github.com` → `github.com`.
/// Handles compound TLDs like `.co.uk` by checking if the second-to-last
/// part is a known short TLD segment (co, com, org, net, ac, gov, edu).
pub fn extract_root_domain(domain: &str) -> String {
    let parts: Vec<&str> = domain.split('.').collect();
    if parts.len() <= 2 {
        return domain.to_string();
    }
    // Known second-level TLD segments (e.g. co.uk, com.au, org.uk)
    let compound_tlds = ["co", "com", "org", "net", "ac", "gov", "edu"];
    let len = parts.len();
    if len >= 3 && compound_tlds.contains(&parts[len - 2]) {
        // e.g. bbc.co.uk → take last 3 parts
        parts[len - 3..].join(".")
    } else {
        // e.g. mail.google.com → take last 2 parts
        parts[len - 2..].join(".")
    }
}

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/domains", get(list_domains))
        .route("/api/v1/domains/:domain", get(domain_detail))
        .route(
            "/api/v1/domains/:domain/config",
            get(get_domain_config).post(set_domain_config),
        )
        .route(
            "/api/v1/domains/:domain/keep-alive",
            get(keep_alive_analysis),
        )
        .route("/api/v1/domains/tabs", get(list_domain_tabs))
        .route(
            "/api/v1/domains/:domain/tab",
            get(get_domain_tab).post(acquire_domain_tab),
        )
        .route(
            "/api/v1/domains/:domain/tab/release",
            axum::routing::post(release_domain_tab),
        )
        .route(
            "/api/v1/domains/:domain/triggers",
            get(match_triggers),
        )
        .route(
            "/api/v1/domains/:domain/status",
            get(domain_status),
        )
}

/// Per-domain session policy — controls TTL, auth type, keep-alive interval.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionPolicy {
    /// Session time-to-live in hours (e.g. 24 for auth domains, 0 for public/no-expiry).
    pub session_ttl_hours: u64,
    /// Authentication type: "oauth2", "oauth3", "cookie", "none".
    pub auth_type: String,
    /// Keep-alive interval in hours (TTL/4 by default).
    pub keep_alive_interval_hours: u64,
    /// URL to navigate for keep-alive checks.
    #[serde(default)]
    pub keep_alive_url: String,
    /// CSS selector to verify session is alive.
    #[serde(default)]
    pub check_selector: String,
}

impl Default for SessionPolicy {
    fn default() -> Self {
        Self {
            session_ttl_hours: 24,
            auth_type: "none".to_string(),
            keep_alive_interval_hours: 6,
            keep_alive_url: String::new(),
            check_selector: String::new(),
        }
    }
}

#[derive(Deserialize)]
struct SessionPolicyPayload {
    session_ttl_hours: Option<u64>,
    auth_type: Option<String>,
    keep_alive_interval_hours: Option<u64>,
    keep_alive_url: Option<String>,
    check_selector: Option<String>,
}

fn domain_config_path(domain: &str) -> PathBuf {
    crate::utils::solace_home()
        .join("wiki")
        .join("domains")
        .join(domain)
        .join("session_policy.json")
}

/// Public accessor for domain config (used by files.rs for domain detail tabs).
pub fn load_domain_config_pub(domain: &str) -> SessionPolicy {
    load_domain_config(domain)
}

fn load_domain_config(domain: &str) -> SessionPolicy {
    let path = domain_config_path(domain);
    crate::persistence::read_json(&path).unwrap_or_default()
}

fn save_domain_config(domain: &str, policy: &SessionPolicy) -> Result<(), String> {
    let path = domain_config_path(domain);
    crate::persistence::write_json(&path, policy)
}

async fn list_domains() -> Json<serde_json::Value> {
    let apps = crate::app_engine::scan_installed_apps();
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    for app in &apps {
        *counts.entry(app.domain.clone()).or_insert(0) += 1;
    }
    // Return both the simple counts map and a sidebar-friendly items array
    let items: Vec<serde_json::Value> = counts
        .iter()
        .map(|(domain, count)| {
            json!({
                "id": domain,
                "host": domain,
                "label": domain,
                "url": format!("http://127.0.0.1:8888/domains/{}", domain),
                "app_count": count,
            })
        })
        .collect();
    Json(json!({"domains": counts, "items": items, "total": apps.len()}))
}

async fn domain_detail(
    Path(domain): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let apps: Vec<_> = crate::app_engine::scan_installed_apps()
        .into_iter()
        .filter(|app| app.domain == domain)
        .collect();
    if apps.is_empty() {
        return Err((
            StatusCode::NOT_FOUND,
            Json(json!({"error": "domain not found"})),
        ));
    }
    Ok(Json(json!({"domain": domain, "apps": apps})))
}

/// GET /api/v1/domains/:domain/config
///
/// Returns the session policy for a domain. If no config exists,
/// returns the default (24h TTL for auth domains, none for public).
async fn get_domain_config(
    Path(domain): Path<String>,
) -> Json<serde_json::Value> {
    let policy = load_domain_config(&domain);
    Json(json!({
        "domain": domain,
        "session_policy": policy,
    }))
}

/// POST /api/v1/domains/:domain/config
///
/// Set or update the session policy for a domain.
/// Partial updates supported — only provided fields are changed.
async fn set_domain_config(
    Path(domain): Path<String>,
    Json(payload): Json<SessionPolicyPayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let mut policy = load_domain_config(&domain);

    if let Some(ttl) = payload.session_ttl_hours {
        policy.session_ttl_hours = ttl;
        // Auto-compute keep-alive as TTL/4 if user didn't explicitly set it
        if payload.keep_alive_interval_hours.is_none() && ttl > 0 {
            policy.keep_alive_interval_hours = std::cmp::max(1, ttl / 4);
        }
    }
    if let Some(auth_type) = payload.auth_type {
        let valid_types = ["oauth2", "oauth3", "cookie", "none"];
        if !valid_types.contains(&auth_type.as_str()) {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(json!({"error": format!("invalid auth_type: {auth_type}. Must be one of: {}", valid_types.join(", "))})),
            ));
        }
        policy.auth_type = auth_type;
    }
    if let Some(interval) = payload.keep_alive_interval_hours {
        policy.keep_alive_interval_hours = interval;
    }
    if let Some(url) = payload.keep_alive_url {
        policy.keep_alive_url = url;
    }
    if let Some(selector) = payload.check_selector {
        policy.check_selector = selector;
    }

    save_domain_config(&domain, &policy).map_err(|error| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": error})),
        )
    })?;

    Ok(Json(json!({
        "domain": domain,
        "session_policy": policy,
        "saved": true,
    })))
}

/// Gap analysis result for a single domain.
#[derive(Serialize)]
struct GapAnalysis {
    domain: String,
    session_ttl_hours: u64,
    active_apps: Vec<AppScheduleInfo>,
    max_gap_hours: f64,
    keep_alive_needed: bool,
    recommendation: String,
}

#[derive(Serialize)]
struct AppScheduleInfo {
    app_id: String,
    schedule: String,
    enabled: bool,
}

/// GET /api/v1/domains/:domain/keep-alive
///
/// Returns gap analysis: active apps, their schedules, max gap,
/// and whether keep-alive is needed to prevent session expiry.
async fn keep_alive_analysis(
    State(state): State<AppState>,
    Path(domain): Path<String>,
) -> Json<serde_json::Value> {
    let policy = load_domain_config(&domain);

    // Collect all schedules for apps belonging to this domain
    let domain_apps: Vec<_> = crate::app_engine::scan_installed_apps()
        .into_iter()
        .filter(|app| app.domain == domain)
        .collect();

    let schedules = state.schedules.read().clone();

    let mut active_apps = Vec::new();
    let mut scheduled_intervals: Vec<u64> = Vec::new();

    for app in &domain_apps {
        // Check if there's an enabled schedule for this app
        let app_schedule = schedules.iter().find(|s| s.app_id == app.id && s.enabled);
        if let Some(schedule) = app_schedule {
            active_apps.push(AppScheduleInfo {
                app_id: app.id.clone(),
                schedule: schedule.cron.clone(),
                enabled: true,
            });
            // Estimate interval from cron expression
            if let Some(interval) = estimate_cron_interval_hours(&schedule.cron) {
                scheduled_intervals.push(interval);
            }
        } else if !app.schedule.is_empty() {
            // App has a manifest schedule but no runtime schedule entry
            active_apps.push(AppScheduleInfo {
                app_id: app.id.clone(),
                schedule: app.schedule.clone(),
                enabled: false,
            });
        }
    }

    let ttl = policy.session_ttl_hours;

    // Compute max gap: if no scheduled apps, gap is infinite.
    // If scheduled apps exist, max gap = longest interval between any runs.
    let (max_gap_hours, keep_alive_needed, recommendation) = if ttl == 0 {
        // No TTL means public domain, no keep-alive needed
        (0.0, false, "Public domain — no session expiry".to_string())
    } else if scheduled_intervals.is_empty() {
        // No scheduled apps — gap is infinite, keep-alive must run at TTL/4
        let interval = std::cmp::max(1, ttl / 4);
        (
            f64::INFINITY,
            true,
            format!(
                "No scheduled apps. Keep-alive should run every {interval}h (TTL/4 of {ttl}h)"
            ),
        )
    } else {
        // Max gap = largest interval among scheduled apps
        let max_interval = scheduled_intervals.iter().copied().max().unwrap_or(ttl);
        let max_gap = max_interval as f64;
        let threshold = ttl as f64 / 2.0;

        if max_gap < threshold {
            (
                max_gap,
                false,
                format!(
                    "Apps cover all windows. Max gap {max_gap}h < threshold {threshold}h (TTL/2)"
                ),
            )
        } else {
            let interval = std::cmp::max(1, ttl / 4);
            (
                max_gap,
                true,
                format!(
                    "Gap {max_gap}h exceeds threshold {threshold}h. Keep-alive needed every {interval}h"
                ),
            )
        }
    };

    let analysis = GapAnalysis {
        domain: domain.clone(),
        session_ttl_hours: ttl,
        active_apps,
        max_gap_hours,
        keep_alive_needed,
        recommendation,
    };

    Json(serde_json::to_value(analysis).unwrap_or(json!({"error": "serialization failed"})))
}

/// Estimate the interval in hours from a cron expression.
/// Returns None if the expression is too complex to estimate simply.
fn estimate_cron_interval_hours(cron: &str) -> Option<u64> {
    let parts: Vec<&str> = cron.split_whitespace().collect();
    if parts.len() != 5 {
        return None;
    }

    let (minute_field, hour_field, _day, _month, _weekday) =
        (parts[0], parts[1], parts[2], parts[3], parts[4]);

    // "0 */N * * *" → every N hours
    if let Some(step) = hour_field.strip_prefix("*/") {
        if let Ok(n) = step.parse::<u64>() {
            return Some(n);
        }
    }

    // "*/N * * * *" where minute step → convert to fractional hours (round up to 1)
    if let Some(step) = minute_field.strip_prefix("*/") {
        if hour_field == "*" {
            if let Ok(n) = step.parse::<u64>() {
                // Every N minutes ≈ runs very frequently
                return Some(if n >= 60 { n / 60 } else { 1 });
            }
        }
    }

    // "0 8 * * *" → specific hour, once per day = 24h gap
    if hour_field != "*" && !hour_field.contains('/') && !hour_field.contains(',') {
        // Single specific hour → runs once per day
        return Some(24);
    }

    // "0 8,20 * * *" → list of hours
    if hour_field.contains(',') {
        let hours: Vec<u64> = hour_field
            .split(',')
            .filter_map(|h| h.parse::<u64>().ok())
            .collect();
        if hours.len() >= 2 {
            let mut sorted = hours;
            sorted.sort();
            let mut max_gap = 0u64;
            for window in sorted.windows(2) {
                max_gap = std::cmp::max(max_gap, window[1] - window[0]);
            }
            // Also consider wrap-around gap (from last to first + 24)
            if let (Some(&first), Some(&last)) = (sorted.first(), sorted.last()) {
                let wrap_gap = 24 - last + first;
                max_gap = std::cmp::max(max_gap, wrap_gap);
            }
            return Some(max_gap);
        }
    }

    // Default: assume daily (24h)
    Some(24)
}

// ---------------------------------------------------------------------------
// Domain Tab Coordination — 1 browser tab per domain
// Apps in the same domain SHARE a tab. Prevents runaway tabs + throttles.
// ---------------------------------------------------------------------------

/// GET /api/v1/domains/tabs — list all active domain tabs
async fn list_domain_tabs(State(state): State<AppState>) -> Json<serde_json::Value> {
    let tabs = state.domain_tabs.read().clone();
    Json(json!({
        "tabs": tabs,
        "count": tabs.len(),
    }))
}

/// GET /api/v1/domains/:domain/tab — get current tab state for a domain
async fn get_domain_tab(
    State(state): State<AppState>,
    Path(domain): Path<String>,
) -> Json<serde_json::Value> {
    let tabs = state.domain_tabs.read();
    if let Some(tab) = tabs.get(&domain) {
        Json(json!({"tab": tab, "available": tab.tab_state == crate::state::TabState::Idle}))
    } else {
        Json(json!({"tab": null, "available": true}))
    }
}

#[derive(Deserialize)]
struct AcquireTabPayload {
    app_id: String,
    url: String,
    session_id: Option<String>,
}

/// POST /api/v1/domains/:domain/tab — acquire the domain tab for an app.
/// Returns the tab assignment. If another app is using it, returns busy status.
/// This is the coordination point: apps call this BEFORE navigating.
async fn acquire_domain_tab(
    State(state): State<AppState>,
    Path(domain): Path<String>,
    Json(payload): Json<AcquireTabPayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let domain = extract_root_domain(&domain);
    let now = crate::utils::now_iso8601();

    // Read session_id BEFORE acquiring domain_tabs write lock (avoid deadlock)
    let session_id = payload
        .session_id
        .unwrap_or_else(|| {
            state.sessions.read().keys().next().cloned().unwrap_or_else(|| "no-session".to_string())
        });

    // Now acquire the domain_tabs write lock
    let tab = {
        let mut tabs = state.domain_tabs.write();

        if let Some(existing) = tabs.get(&domain) {
            match existing.tab_state {
                crate::state::TabState::Working | crate::state::TabState::Cooldown => {
                    return Err((
                        StatusCode::CONFLICT,
                        Json(json!({
                            "error": "domain_tab_busy",
                            "domain": domain,
                            "active_app_id": existing.active_app_id,
                            "tab_state": format!("{:?}", existing.tab_state),
                            "message": format!(
                                "Domain tab for {} is {:?} (app {}). Wait for release.",
                                domain,
                                existing.tab_state,
                                existing.active_app_id.as_deref().unwrap_or("unknown")
                            ),
                        })),
                    ));
                }
                _ => {}
            }
        }

        let tab = crate::state::DomainTab {
            domain: domain.clone(),
            current_url: payload.url.clone(),
            session_id: session_id.clone(),
            active_app_id: Some(payload.app_id.clone()),
            last_activity: now,
            tab_state: crate::state::TabState::Working,
        };
        tabs.insert(domain.clone(), tab.clone());
        tab
    }; // write lock dropped here

    // Notify sidebars AFTER releasing domain_tabs lock
    let channels = state.session_channels.read();
    for (_sid, tx) in channels.iter() {
        let msg = serde_json::json!({
            "type": "domain_tab_changed",
            "domain": &domain,
            "tab_state": "Working",
            "app_id": &payload.app_id,
        });
        let _ = tx.send(msg.to_string());
    }

    Ok(Json(json!({
        "acquired": true,
        "tab": tab,
        "message": format!("App {} acquired domain tab for {}", payload.app_id, domain),
    })))
}

/// POST /api/v1/domains/:domain/tab/release — release the domain tab after an app finishes.
/// Sets state to Cooldown for 30 seconds before returning to Idle.
async fn release_domain_tab(
    State(state): State<AppState>,
    Path(domain): Path<String>,
) -> Json<serde_json::Value> {
    let domain = extract_root_domain(&domain);
    let prev_app;
    {
        let mut tabs = state.domain_tabs.write();
        if let Some(tab) = tabs.get_mut(&domain) {
            prev_app = tab.active_app_id.take();
            tab.tab_state = crate::state::TabState::Cooldown;
            tab.last_activity = crate::utils::now_iso8601();
        } else {
            return Json(json!({
                "released": false,
                "domain": domain,
                "message": "No active tab for this domain",
            }));
        }
    } // drop write lock

    // Notify all connected sidebars of cooldown state
    {
        let channels = state.session_channels.read();
        for (_sid, tx) in channels.iter() {
            let msg = serde_json::json!({
                "type": "domain_tab_changed",
                "domain": &domain,
                "tab_state": "Cooldown",
                "app_id": serde_json::Value::Null,
            });
            let _ = tx.send(msg.to_string());
        }
    }

    // Spawn cooldown timer — after 30s, transition Cooldown → Idle
    let cooldown_state = state.clone();
    let cooldown_domain = domain.clone();
    tokio::spawn(async move {
        tokio::time::sleep(std::time::Duration::from_secs(30)).await;
        let mut tabs = cooldown_state.domain_tabs.write();
        if let Some(tab) = tabs.get_mut(&cooldown_domain) {
            if tab.tab_state == crate::state::TabState::Cooldown {
                tab.tab_state = crate::state::TabState::Idle;
                tab.last_activity = crate::utils::now_iso8601();
            }
        }
        drop(tabs);
        // Notify sidebars that cooldown is over
        let channels = cooldown_state.session_channels.read();
        for (_sid, tx) in channels.iter() {
            let msg = serde_json::json!({
                "type": "domain_tab_changed",
                "domain": &cooldown_domain,
                "tab_state": "Idle",
                "app_id": serde_json::Value::Null,
            });
            let _ = tx.send(msg.to_string());
        }
    });

    Json(json!({
        "released": true,
        "domain": domain,
        "previous_app": prev_app,
        "cooldown_seconds": 30,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_session_policy() {
        let policy = SessionPolicy::default();
        assert_eq!(policy.session_ttl_hours, 24);
        assert_eq!(policy.auth_type, "none");
        assert_eq!(policy.keep_alive_interval_hours, 6);
    }

    #[test]
    fn estimate_cron_every_6h() {
        assert_eq!(estimate_cron_interval_hours("0 */6 * * *"), Some(6));
    }

    #[test]
    fn estimate_cron_every_4h() {
        assert_eq!(estimate_cron_interval_hours("0 */4 * * *"), Some(4));
    }

    #[test]
    fn estimate_cron_once_daily() {
        assert_eq!(estimate_cron_interval_hours("0 8 * * *"), Some(24));
    }

    #[test]
    fn estimate_cron_twice_daily() {
        // 8am and 8pm → max gap = 12h
        assert_eq!(estimate_cron_interval_hours("0 8,20 * * *"), Some(12));
    }

    #[test]
    fn estimate_cron_three_times_daily() {
        // 0, 8, 16 → gaps: 8, 8, 8 (wrap: 24-16+0=8)
        assert_eq!(estimate_cron_interval_hours("0 0,8,16 * * *"), Some(8));
    }

    #[test]
    fn estimate_cron_every_15_min() {
        assert_eq!(estimate_cron_interval_hours("*/15 * * * *"), Some(1));
    }

    #[test]
    fn estimate_cron_invalid() {
        assert_eq!(estimate_cron_interval_hours("bad"), None);
    }

    #[test]
    fn session_policy_roundtrip() {
        let policy = SessionPolicy {
            session_ttl_hours: 48,
            auth_type: "oauth3".to_string(),
            keep_alive_interval_hours: 12,
            keep_alive_url: "https://example.com".to_string(),
            check_selector: "div.logged-in".to_string(),
        };
        let json = serde_json::to_string(&policy).unwrap();
        let parsed: SessionPolicy = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.session_ttl_hours, 48);
        assert_eq!(parsed.auth_type, "oauth3");
        assert_eq!(parsed.keep_alive_interval_hours, 12);
    }

    #[test]
    fn domain_config_path_structure() {
        // Verify the path follows ~/.solace/wiki/domains/{domain}/session_policy.json
        let path = domain_config_path("gmail.com");
        let path_str = path.to_string_lossy();
        assert!(path_str.contains("wiki"));
        assert!(path_str.contains("domains"));
        assert!(path_str.contains("gmail.com"));
        assert!(path_str.ends_with("session_policy.json"));
    }

    #[test]
    fn extract_root_domain_subdomain() {
        assert_eq!(extract_root_domain("mail.google.com"), "google.com");
        assert_eq!(extract_root_domain("drive.google.com"), "google.com");
    }

    #[test]
    fn extract_root_domain_already_root() {
        assert_eq!(extract_root_domain("github.com"), "github.com");
        assert_eq!(extract_root_domain("example.com"), "example.com");
    }

    #[test]
    fn extract_root_domain_co_uk() {
        assert_eq!(extract_root_domain("bbc.co.uk"), "bbc.co.uk");
    }
}

/// Match triggers: which domain apps should activate for a given URL?
async fn match_triggers(
    State(_state): State<AppState>,
    Path(domain): Path<String>,
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Json<serde_json::Value> {
    let url_path = params.get("path").cloned().unwrap_or_else(|| "/".to_string());

    let apps = crate::utils::scan_apps();
    let mut matched = Vec::new();

    for app in &apps {
        for trigger in &app.triggers {
            // Domain match (exact or subdomain)
            let trigger_domain = &trigger.domain;
            if !domain.contains(trigger_domain) && trigger_domain != &domain {
                continue;
            }

            // Path match (glob-like: /* matches everything)
            let path_pattern = &trigger.path;
            let path_matches = path_pattern == "/*"
                || path_pattern == &url_path
                || (path_pattern.ends_with('*') && url_path.starts_with(&path_pattern[..path_pattern.len()-1]));

            if path_matches {
                matched.push(serde_json::json!({
                    "app_id": app.id,
                    "app_name": app.name,
                    "trigger_context": trigger.context,
                    "dom_selector": trigger.dom_selector,
                    "activation": trigger.activation,
                    "actions": app.actions,
                    "category": app.category,
                    "persona": app.persona,
                }));
            }
        }
    }

    Json(serde_json::json!({
        "domain": domain,
        "path": url_path,
        "matched_apps": matched,
        "count": matched.len(),
    }))
}

/// Domain status: OAuth3, apps, wiki snapshots.
async fn domain_status(
    State(state): State<AppState>,
    Path(domain): Path<String>,
) -> Json<serde_json::Value> {
    let apps = crate::utils::scan_apps();
    let domain_apps: Vec<_> = apps.iter()
        .filter(|a| a.triggers.iter().any(|t| domain.contains(&t.domain)))
        .collect();

    // Check OAuth3 tokens for this domain
    let solace_home = crate::utils::solace_home();
    let vault_path = solace_home.join("vault").join("oauth3.json");
    let oauth3_status = if vault_path.exists() {
        if let Ok(content) = std::fs::read_to_string(&vault_path) {
            if content.contains(&domain) { "active" } else { "not_configured" }
        } else { "not_configured" }
    } else { "not_configured" };

    // Wiki snapshot count for this domain
    let wiki_dir = solace_home.join("wiki").join("domains").join(&domain);
    let snapshot_count = if wiki_dir.exists() {
        std::fs::read_dir(&wiki_dir)
            .into_iter().flatten().filter_map(|e| e.ok())
            .filter(|e| e.file_name().to_string_lossy().ends_with(".prime-snapshot.md"))
            .count()
    } else { 0 };

    let cloud = state.cloud_config.read().is_some();

    Json(serde_json::json!({
        "domain": domain,
        "oauth3_status": oauth3_status,
        "apps_count": domain_apps.len(),
        "apps": domain_apps.iter().map(|a| serde_json::json!({
            "app_id": a.id,
            "name": a.name,
            "triggers": a.triggers.len(),
            "actions": a.actions.len(),
        })).collect::<Vec<_>>(),
        "wiki_snapshots": snapshot_count,
        "cloud_connected": cloud,
    }))
}
