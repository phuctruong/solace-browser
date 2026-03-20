// Diagram: hub-ux-architecture
use std::collections::BTreeMap;
use std::fs;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::Html;
use axum::routing::get;
use axum::Router;

use crate::state::AppState;

/// Find Hub assets directory — checks dev path then installed path.
/// Works on mac/windows/linux: ~/.solace/hub/ is the production location.
fn hub_assets_dir(subdir: &str) -> std::path::PathBuf {
    // Dev path (only exists on dev machine)
    let dev = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap_or(std::path::Path::new("."))
        .join("solace-hub")
        .join("src")
        .join(subdir);
    if dev.is_dir() {
        return dev;
    }
    // Installed path (~/.solace/hub/{subdir})
    let installed = crate::utils::solace_home().join("hub").join(subdir);
    if installed.is_dir() {
        return installed;
    }
    // Fallback to dev path (will 404 gracefully via ServeDir)
    dev
}

/// Find sidebar assets — checks Hub src, Chromium source, then installed path.
fn sidebar_asset(filename: &str) -> Option<String> {
    let candidates = [
        // Hub src (development — latest edits)
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap_or(std::path::Path::new("."))
            .join("solace-hub/src")
            .join(filename),
        // Chromium source tree
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap_or(std::path::Path::new("."))
            .join("source/src/chrome/browser/resources/solace")
            .join(filename),
        // Installed path
        crate::utils::solace_home()
            .join("resources")
            .join("solace-sidebar")
            .join(filename),
    ];
    for path in &candidates {
        if let Ok(content) = fs::read_to_string(path) {
            return Some(content);
        }
    }
    None
}

/// Find Hub index.html — checks dev path then installed path.
fn hub_index_html() -> Option<String> {
    let candidates = [
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap_or(std::path::Path::new("."))
            .join("solace-hub/src/index.html"),
        crate::utils::solace_home().join("hub").join("index.html"),
    ];
    for path in &candidates {
        if let Ok(content) = fs::read_to_string(path) {
            return Some(content);
        }
    }
    None
}

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/", get(index))
        .route("/dashboard", get(dashboard_page))
        .route("/hire", get(hire_page))
        .route("/onboarding", get(onboarding_page))
        .route("/sidebar", get(sidebar_page))
        .route("/sidepanel.js", get(sidebar_js))
        .route("/sidepanel.css", get(sidebar_css))
        .route("/domains", get(domains_page))
        .route("/domains/:domain", get(domain_detail_page))
        .route("/apps/:app_id", get(app_detail_page))
        .route("/apps/:app_id/runs/:run_id", get(run_detail_page))
        .route("/evidence", get(evidence_page))
        .route("/appstore", get(appstore_page))
        .route("/llms", get(llms_page))
        .route("/budget", get(budget_page))
        .route("/recipes", get(recipes_page))
        .route("/oauth3", get(oauth3_page))
        .route("/esign", get(esign_page))
        .route("/wiki-hub", get(wiki_page))
        .route("/settings", get(settings_page))
        .route("/styleguide", get(styleguide_page))
        .route("/styleguide.css", get(styleguide_css))
        .nest_service("/assets", tower_http::services::ServeDir::new("templates"))
        .nest_service("/icons", tower_http::services::ServeDir::new(hub_assets_dir("icons")))
        .nest_service("/media", tower_http::services::ServeDir::new(hub_assets_dir("media")))
        .nest_service("/vendor", tower_http::services::ServeDir::new(hub_assets_dir("vendor")))
}

async fn index() -> Html<String> {
    if let Some(content) = hub_index_html() {
        return Html(content);
    }
    Html(page(
        "Solace Runtime",
        "Local-first runtime active on port 8888.",
    ))
}

// ---------------------------------------------------------------------------
// GET /dashboard — full Solace Dashboard (app cards, events, sessions, evidence)
// ---------------------------------------------------------------------------
async fn dashboard_page(State(state): State<AppState>) -> Html<String> {
    let apps = crate::app_engine::scan_installed_apps();
    let sessions = state.sessions.read().clone();
    let events = state.runtime_events.read().clone();
    let uptime = state.uptime_seconds();
    let theme = state.theme.read().clone();
    let delight = state.delight.read().clone();
    let notifications = state.notifications.read().clone();
    let solace_home = crate::utils::solace_home();
    let part11 = crate::evidence::part11_status(&solace_home);

    // Greeting
    let greeting = delight.warm_greeting();
    let celebration = delight
        .celebration_message()
        .map(|m| format!("<p class=\"sb-pill sb-pill--success\">{m}</p>"))
        .unwrap_or_default();

    // App status cards
    let mut app_cards = String::new();
    for app in &apps {
        let app_dir = crate::utils::find_app_dir(&app.id);
        let run_count = app_dir.as_ref().map(|d| count_runs(d)).unwrap_or(0);
        let last_run = app_dir
            .as_ref()
            .and_then(|d| latest_run_time(d))
            .unwrap_or_else(|| "Never".to_string());
        let schedule_label = if app.schedule.is_empty() {
            "Manual"
        } else {
            &app.schedule
        };
        let icon_path = domain_icon_path(&app.domain);
        app_cards.push_str(&format!(
            r#"<div class="sb-card">
  <div class="sb-card-header">
    <h3 class="sb-card-title sb-app-name"><img class="sb-app-icon" src="{icon}" alt="{name} icon" loading="lazy"><a href="/apps/{id}">{name}</a></h3>
    <span class="sb-pill sb-pill--info">{domain}</span>
  </div>
  <div class="sb-card-body">
    <p>{desc}</p>
    <div class="sb-app-meta">
      <span><strong>{run_count}</strong> runs</span>
      <span>Last: {last_run}</span>
      <span>Schedule: <code>{sched}</code></span>
    </div>
  </div>
</div>"#,
            icon = html_escape::encode_text(&icon_path),
            id = html_escape::encode_text(&app.id),
            name = html_escape::encode_text(&app.name),
            domain = html_escape::encode_text(&app.domain),
            desc = html_escape::encode_text(&app.description),
            last_run = html_escape::encode_text(&last_run),
            sched = html_escape::encode_text(schedule_label),
        ));
    }
    if app_cards.is_empty() {
        app_cards = r#"<div class="sb-empty"><div class="sb-empty-icon">&#x1F4E6;</div><p>No apps installed yet.</p></div>"#.to_string();
    }

    // Session cards
    let mut session_rows = String::new();
    for (sid, info) in &sessions {
        session_rows.push_str(&format!(
            "<tr><td><code>{}</code></td><td>{}</td><td>{}</td><td><span class=\"sb-pill sb-pill--success\">PID {}</span></td><td>{}</td></tr>",
            html_escape::encode_text(&sid[..8.min(sid.len())]),
            html_escape::encode_text(&info.profile),
            html_escape::encode_text(&info.url),
            info.pid,
            html_escape::encode_text(&info.started_at),
        ));
    }
    if session_rows.is_empty() {
        session_rows = "<tr><td colspan=\"5\" class=\"sb-text-muted\">No active browser sessions.</td></tr>".to_string();
    }

    // Recent events (last 25)
    let mut event_rows = String::new();
    let recent_events: Vec<_> = events.iter().rev().take(25).collect();
    for evt in &recent_events {
        let ts = evt.get("timestamp").and_then(|v| v.as_str()).unwrap_or("—");
        let etype = evt.get("type").and_then(|v| v.as_str()).unwrap_or("event");
        let detail = evt.get("detail").and_then(|v| v.as_str())
            .or_else(|| evt.get("message").and_then(|v| v.as_str()))
            .unwrap_or("—");
        let level = evt.get("level").and_then(|v| v.as_str()).unwrap_or("L1");
        let pill_class = match level {
            "L1" => "sb-pill--info",
            "L2" => "sb-pill--success",
            "L3" => "sb-pill--warning",
            "L4" | "L5" => "sb-pill--danger",
            _ => "sb-pill--info",
        };
        event_rows.push_str(&format!(
            "<tr><td>{}</td><td><span class=\"sb-pill {}\">{}</span></td><td><strong>{}</strong></td><td>{}</td></tr>",
            html_escape::encode_text(ts),
            pill_class,
            html_escape::encode_text(level),
            html_escape::encode_text(etype),
            html_escape::encode_text(detail),
        ));
    }
    if event_rows.is_empty() {
        event_rows = "<tr><td colspan=\"4\" class=\"sb-text-muted\">No events yet. Run an app to generate events.</td></tr>".to_string();
    }

    // Evidence summary
    let chain_badge = if part11.chain_valid {
        "<span class=\"sb-pill sb-pill--success\">Chain Valid</span>"
    } else if part11.record_count > 0 {
        "<span class=\"sb-pill sb-pill--danger\">Chain Broken</span>"
    } else {
        "<span class=\"sb-pill sb-pill--info\">No Records</span>"
    };

    // Unread notifications
    let unread = notifications.iter().filter(|n| !n.read).count();
    let notif_badge = if unread > 0 {
        format!("<span class=\"sb-pill sb-pill--warning\">{unread} unread</span>")
    } else {
        String::new()
    };

    // Format uptime
    let hours = uptime / 3600;
    let mins = (uptime % 3600) / 60;
    let uptime_str = if hours > 0 {
        format!("{}h {}m", hours, mins)
    } else {
        format!("{}m", mins)
    };

    let body = format!(
        r#"<!-- Status bar -->
<div class="sb-status-bar">
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Apps</div>
    <div class="sb-stat-value">{app_count}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Sessions</div>
    <div class="sb-stat-value">{session_count}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Evidence</div>
    <div class="sb-stat-value">{evidence_count}</div>
    <div>{chain_badge}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Uptime</div>
    <div class="sb-stat-value">{uptime_str}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Streak</div>
    <div class="sb-stat-value">{streak} days</div>
  </div>
</div>

<!-- App Status Cards -->
<section aria-labelledby="apps-heading">
  <div class="sb-section-header">
    <h2 id="apps-heading" class="sb-heading">Installed Apps</h2>
    <a href="/domains" class="sb-btn sb-btn--sm">All Domains</a>
  </div>
  <div class="sb-card-grid">{app_cards}</div>
</section>

<!-- Backoffice + Workers + Jobs (live data, loaded via JS) -->
<section class="sb-section" aria-labelledby="office-heading">
  <div class="sb-section-header">
    <h2 id="office-heading" class="sb-heading">Office + Workers</h2>
    <a href="/backoffice" class="sb-btn sb-btn--sm">Backoffice</a>
  </div>
  <div id="dash-office" class="sb-card-grid"></div>
</section>

<script>
(function() {{
  function ge(id) {{ return document.getElementById(id); }}
  function fetchJson(url) {{ return fetch(url).then(function(r){{ return r.json(); }}); }}

  // Backoffice + CLI Workers + Jobs in one dashboard strip
  Promise.all([
    fetchJson('/api/v1/backoffice'),
    fetchJson('/api/v1/cli'),
    fetchJson('/api/v1/jobs/stats'),
    fetchJson('/api/v1/events/topics')
  ]).then(function(results) {{
    var bo = results[0], cli = results[1], jobs = results[2], topics = results[3];
    var html = '';

    // Backoffice apps
    (bo.backoffice_apps||[]).forEach(function(app) {{
      var name = app.app_id.replace('backoffice-','').toUpperCase();
      html += '<div class="sb-card"><div class="sb-kicker">Backoffice</div>';
      html += '<strong><a href="/backoffice/' + app.app_id + '">' + name + '</a></strong>';
      html += '<p class="sb-text-muted sb-text-sm">' + (app.tables||[]).join(', ') + '</p></div>';
    }});

    // CLI workers summary
    html += '<div class="sb-card"><div class="sb-kicker">CLI Workers</div>';
    html += '<div class="sb-stat-value">' + (cli.installed||0) + '/' + (cli.total||0) + '</div>';
    var cats = cli.by_category || {{}};
    Object.keys(cats).forEach(function(c) {{
      var installed = cats[c].filter(function(w){{ return w.installed; }}).length;
      html += '<span class="sb-pill sb-pill--info sb-text-2xs">' + c + ': ' + installed + '</span> ';
    }});
    html += '</div>';

    // Job queue
    html += '<div class="sb-card"><div class="sb-kicker">Job Queue</div>';
    html += '<div class="sb-stat-value">' + (jobs.total||0) + '</div>';
    if (jobs.running) html += '<span class="sb-pill sb-pill--warning">' + jobs.running + ' running</span> ';
    if (jobs.queued) html += '<span class="sb-pill sb-pill--info">' + jobs.queued + ' queued</span> ';
    if (jobs.done) html += '<span class="sb-pill sb-pill--success">' + jobs.done + ' done</span> ';
    if (jobs.failed) html += '<span class="sb-pill sb-pill--danger">' + jobs.failed + ' failed</span>';
    html += '</div>';

    // Pub/Sub
    html += '<div class="sb-card"><div class="sb-kicker">Event Bus</div>';
    html += '<div class="sb-stat-value">' + (topics.total||0) + '</div>';
    html += '<p class="sb-text-muted sb-text-sm">topics active</p></div>';

    ge('dash-office').innerHTML = html;
  }});
}})();
</script>

<!-- Active Sessions -->
<section class="sb-section" aria-labelledby="sessions-heading">
  <h2 id="sessions-heading" class="sb-heading">Active Sessions {notif_badge}</h2>
  <table class="sb-table"><thead><tr><th>Session</th><th>Profile</th><th>URL</th><th>Status</th><th>Started</th></tr></thead>
  <tbody>{session_rows}</tbody></table>
</section>

<!-- Events (Transparency) -->
<section class="sb-section" aria-labelledby="events-heading">
  <div class="sb-section-header">
    <h2 id="events-heading" class="sb-heading">Recent Events</h2>
    <a href="/evidence" class="sb-btn sb-btn--sm">Evidence Chain</a>
  </div>
  <table class="sb-table" id="events-table"><thead><tr><th>Time</th><th>Level</th><th>Type</th><th>Detail</th></tr></thead>
  <tbody>{event_rows}</tbody></table>
</section>"#,
        app_count = apps.len(),
        session_count = sessions.len(),
        evidence_count = part11.record_count,
        streak = delight.streak_days,
    );

    let title = format!("{}, Dragon Rider", greeting);
    Html(hub_page(&title, &body))
}

async fn onboarding_page() -> Html<String> {
    Html(page(
        "Onboarding",
        "Four-state onboarding gate for the Solace sidebar.",
    ))
}

async fn sidebar_page() -> Html<String> {
    if let Some(content) = sidebar_asset("sidepanel.html") {
        return Html(content);
    }
    Html(page(
        "Sidebar",
        "Yinyang sidebar — sidepanel.html not found. Build Solace Browser first.",
    ))
}

async fn sidebar_js() -> (axum::http::HeaderMap, String) {
    let mut headers = axum::http::HeaderMap::new();
    headers.insert("content-type", "application/javascript".parse().unwrap());
    let content = sidebar_asset("sidepanel.js").unwrap_or_else(|| "// sidepanel.js not found".to_string());
    (headers, content)
}

async fn sidebar_css() -> (axum::http::HeaderMap, String) {
    let mut headers = axum::http::HeaderMap::new();
    headers.insert("content-type", "text/css".parse().unwrap());
    let content = sidebar_asset("sidepanel.css").unwrap_or_else(|| "/* sidepanel.css not found */".to_string());
    (headers, content)
}

// ---------------------------------------------------------------------------
// GET /domains — list all domains with app count per domain
// ---------------------------------------------------------------------------
async fn domains_page() -> Html<String> {
    let apps = crate::app_engine::scan_installed_apps();
    let mut domain_map: BTreeMap<String, Vec<&crate::app_engine::AppManifest>> = BTreeMap::new();
    for app in &apps {
        domain_map.entry(app.domain.clone()).or_default().push(app);
    }

    let mut cards = String::new();
    for (domain, domain_apps) in &domain_map {
        let count = domain_apps.len();
        let last_activity = domain_apps
            .iter()
            .filter_map(|a| {
                let dir = crate::utils::find_app_dir(&a.id)?;
                latest_run_time(&dir)
            })
            .max()
            .unwrap_or_else(|| "Never".to_string());
        let icon = domain_icon_path(domain);
        let app_names: Vec<_> = domain_apps.iter().map(|a| a.name.as_str()).take(3).collect();
        let app_preview = app_names.join(", ");
        let more = if domain_apps.len() > 3 {
            format!(" +{} more", domain_apps.len() - 3)
        } else {
            String::new()
        };
        cards.push_str(&format!(
            r#"<a href="/domains/{domain_enc}" class="sb-card sb-domain-link">
  <div class="sb-card-header">
    <h3 class="sb-card-title sb-app-name"><img class="sb-app-icon" src="{icon}" alt="{domain_disp} icon" loading="lazy">{domain_disp}</h3>
    <span class="sb-pill sb-pill--info">{count} apps</span>
  </div>
  <div class="sb-card-body">
    <p class="sb-text-muted">{app_preview}{more}</p>
    <p class="sb-timestamp">Last: {last}</p>
  </div>
</a>"#,
            domain_enc = html_escape::encode_text(domain),
            domain_disp = html_escape::encode_text(domain),
            icon = html_escape::encode_text(&icon),
            app_preview = html_escape::encode_text(&app_preview),
            last = html_escape::encode_text(&last_activity),
        ));
    }

    if cards.is_empty() {
        cards = r#"<div class="sb-empty"><p>No domains found. Install apps to get started.</p><p class="sb-section"><a href="/appstore" class="sb-btn sb-btn--sm sb-btn--primary">Browse App Store</a></p></div>"#.to_string();
    }

    let body = format!(
        r#"<p class="sb-text-muted sb-domain-desc">{total} domains with {app_total} total apps. Each domain gets 1 browser tab.</p>
<div class="sb-card-grid">{cards}</div>"#,
        total = domain_map.len(),
        app_total = apps.len(),
    );
    Html(hub_page("Domains", &body))
}

// ---------------------------------------------------------------------------
// GET /domains/:domain — domain detail page
// ---------------------------------------------------------------------------
async fn domain_detail_page(
    State(state): State<AppState>,
    Path(domain): Path<String>,
) -> Result<Html<String>, (StatusCode, Html<String>)> {
    let apps: Vec<_> = crate::app_engine::scan_installed_apps()
        .into_iter()
        .filter(|a| a.domain == domain)
        .collect();

    if apps.is_empty() {
        return Err((
            StatusCode::NOT_FOUND,
            Html(hub_page(
                "Domain Not Found",
                &format!(
                    "<p>No apps found for domain <strong>{}</strong>.</p><p><a href=\"/domains\">&larr; All Domains</a></p>",
                    html_escape::encode_text(&domain)
                ),
            )),
        ));
    }

    // Stillwater info (if domain wiki exists)
    let wiki_dir = crate::utils::solace_home().join("wiki").join("domains");
    let stillwater_section = if wiki_dir.join(format!("{domain}.json")).is_file() {
        match fs::read_to_string(wiki_dir.join(format!("{domain}.json"))) {
            Ok(raw) => format!(
                "<section class=\"stillwater\"><h2>Stillwater</h2><pre>{}</pre></section>",
                html_escape::encode_text(&raw)
            ),
            Err(_) => String::new(),
        }
    } else {
        String::new()
    };

    // App list
    let mut app_rows = String::new();
    for app in &apps {
        let app_dir = crate::utils::find_app_dir(&app.id);
        let run_count = app_dir
            .as_ref()
            .map(|d| count_runs(d))
            .unwrap_or(0);
        let last_run = app_dir
            .as_ref()
            .and_then(|d| latest_run_time(d))
            .unwrap_or_else(|| "—".to_string());
        app_rows.push_str(&format!(
            "<tr><td><a href=\"/apps/{}\">{}</a></td><td>{}</td><td>{}</td><td>{}</td></tr>",
            html_escape::encode_text(&app.id),
            html_escape::encode_text(&app.name),
            html_escape::encode_text(&app.version),
            run_count,
            html_escape::encode_text(&last_run),
        ));
    }

    // Recent runs across all apps in this domain
    let mut all_runs: Vec<(String, String, String)> = Vec::new();
    for app in &apps {
        if let Some(dir) = crate::utils::find_app_dir(&app.id) {
            for (run_id, ts) in list_runs(&dir) {
                all_runs.push((app.id.clone(), run_id, ts));
            }
        }
    }
    all_runs.sort_by(|a, b| b.2.cmp(&a.2));
    all_runs.truncate(10);

    let mut run_rows = String::new();
    for (app_id, run_id, ts) in &all_runs {
        run_rows.push_str(&format!(
            "<tr><td><a href=\"/apps/{}/runs/{}\">{}</a></td><td>{}</td><td>{}</td></tr>",
            html_escape::encode_text(app_id),
            html_escape::encode_text(run_id),
            html_escape::encode_text(run_id),
            html_escape::encode_text(app_id),
            html_escape::encode_text(ts),
        ));
    }
    if run_rows.is_empty() {
        run_rows = "<tr><td colspan=\"3\">No runs yet.</td></tr>".to_string();
    }

    // Domain tab status — read directly from AppState
    let tab_status = {
        let tabs = state.domain_tabs.read();
        if let Some(tab) = tabs.get(&domain) {
            if tab.tab_state == crate::state::TabState::Idle {
                "<span class=\"sb-pill sb-pill--success\">Idle</span> — tab available for next app".to_string()
            } else {
                format!("<span class=\"sb-pill sb-pill--warning\">Working</span> — active app: <strong>{}</strong>",
                    html_escape::encode_text(tab.active_app_id.as_deref().unwrap_or("unknown")))
            }
        } else {
            "<span class=\"sb-pill sb-pill--success\">Idle</span> — no tab registered yet".to_string()
        }
    };

    // Domain config
    let config = crate::routes::domains::load_domain_config_pub(&domain);
    let config_section = format!(
        "<table class=\"sb-table\">\
         <tr><td><strong>Session TTL</strong></td><td>{} hours</td></tr>\
         <tr><td><strong>Auth Type</strong></td><td>{}</td></tr>\
         <tr><td><strong>Keep-Alive</strong></td><td>Every {} hours</td></tr>\
         </table>",
        config.session_ttl_hours,
        html_escape::encode_text(&config.auth_type),
        config.keep_alive_interval_hours,
    );

    let icon = domain_icon_path(&domain);
    let body = format!(
        r#"<p><a href="/domains">&larr; All Domains</a></p>
<div class="sb-flex" class="sb-section-header">
  <img class="sb-app-icon" src="{icon}" alt="">
  <span class="sb-pill sb-pill--info">{app_count} apps</span>
</div>

<div class="sb-tabs" role="tablist" id="domain-tabs">
  <button class="sb-tab sb-tab--active" data-tab="apps" onclick="showTab(this,'apps')">Apps</button>
  <button class="sb-tab" data-tab="events" onclick="showTab(this,'events')">Events</button>
  <button class="sb-tab" data-tab="tab-status" onclick="showTab(this,'tab-status')">Tab Status</button>
  <button class="sb-tab" data-tab="config" onclick="showTab(this,'config')">Config</button>
  <button class="sb-tab" data-tab="share" onclick="showTab(this,'share')">Share</button>
</div>

<div id="panel-apps" class="sb-tab-panel">
  {stillwater_section}
  <table class="sb-table"><thead><tr><th>App</th><th>Version</th><th>Runs</th><th>Last Run</th></tr></thead><tbody>{app_rows}</tbody></table>
</div>

<div id="panel-events" class="sb-tab-panel" hidden>
  <h3 class="sb-heading">Recent Runs</h3>
  <table class="sb-table"><thead><tr><th>Run</th><th>App</th><th>Time</th></tr></thead><tbody>{run_rows}</tbody></table>
</div>

<div id="panel-tab-status" class="sb-tab-panel" hidden>
  <div class="sb-card"><p>{tab_status}</p>
  <p class="sb-text-muted sb-section">Rule: 1 browser tab per domain. Apps share the tab via acquire/release protocol.</p></div>
</div>

<div id="panel-config" class="sb-tab-panel" hidden>
  <div class="sb-card">{config_section}</div>
</div>

<div id="panel-share" class="sb-tab-panel" hidden>
  <div class="sb-card">
    <h3>Share this domain's apps</h3>
    <p class="sb-text-muted">Share all apps in this domain with a team member or anyone.</p>
    <div >
      <label >Recipient email</label>
      <input type="email" id="share-domain-email" placeholder="colleague@company.com" class="sb-input">
    </div>
    <button class="sb-btn sb-btn--sm sb-btn--primary" onclick="shareDomain()">Share via solaceagi.com</button>
    <p id="share-domain-result" class="sb-text-muted sb-section"></p>
    <p class="sb-text-muted" class="sb-section sb-text-muted">Free: share with 1 person. <a href="https://solaceagi.com/pricing" target="_blank" rel="noopener">Team plan</a> ($88/mo): 5 seats + workspace.</p>
  </div>
</div>

<script>
function showTab(btn, id) {{
  document.querySelectorAll('.sb-tab').forEach(t => t.classList.remove('sb-tab--active'));
  document.querySelectorAll('.sb-tab-panel').forEach(p => p.hidden = true);
  btn.classList.add('sb-tab--active');
  document.getElementById('panel-' + id).hidden = false;
}}
</script>"#,
        icon = html_escape::encode_text(&icon),
        app_count = apps.len(),
    );

    Ok(Html(hub_page(
        &format!("Domain: {}", html_escape::encode_text(&domain)),
        &body,
    )))
}

// ---------------------------------------------------------------------------
// GET /apps/:app_id — app detail page
// ---------------------------------------------------------------------------
async fn app_detail_page(
    Path(app_id): Path<String>,
) -> Result<Html<String>, (StatusCode, Html<String>)> {
    let apps = crate::app_engine::scan_installed_apps();
    let app = apps.into_iter().find(|a| a.id == app_id);

    let Some(app) = app else {
        return Err((
            StatusCode::NOT_FOUND,
            Html(hub_page(
                "App Not Found",
                &format!(
                    "<p>App <strong>{}</strong> not found.</p><p><a href=\"/domains\">&larr; All Domains</a></p>",
                    html_escape::encode_text(&app_id)
                ),
            )),
        ));
    };

    let app_dir = crate::utils::find_app_dir(&app.id);

    // Manifest info
    let schedule_display = if app.schedule.is_empty() {
        "Manual".to_string()
    } else {
        html_escape::encode_text(&app.schedule).to_string()
    };
    let tier_display = if app.tier.is_empty() {
        "free".to_string()
    } else {
        html_escape::encode_text(&app.tier).to_string()
    };

    let manifest_section = format!(
        "<section class=\"manifest\">\
         <h2>Manifest</h2>\
         <table>\
         <tr><td><strong>ID</strong></td><td>{}</td></tr>\
         <tr><td><strong>Name</strong></td><td>{}</td></tr>\
         <tr><td><strong>Version</strong></td><td>{}</td></tr>\
         <tr><td><strong>Domain</strong></td><td><a href=\"/domains/{}\">{}</a></td></tr>\
         <tr><td><strong>Schedule</strong></td><td><code>{}</code></td></tr>\
         <tr><td><strong>Tier</strong></td><td>{}</td></tr>\
         <tr><td><strong>Description</strong></td><td>{}</td></tr>\
         </table></section>",
        html_escape::encode_text(&app.id),
        html_escape::encode_text(&app.name),
        html_escape::encode_text(&app.version),
        html_escape::encode_text(&app.domain),
        html_escape::encode_text(&app.domain),
        schedule_display,
        tier_display,
        html_escape::encode_text(&app.description),
    );

    // Recent runs
    let runs = app_dir
        .as_ref()
        .map(|d| list_runs(d))
        .unwrap_or_default();

    let mut run_rows = String::new();
    for (run_id, ts) in runs.iter().rev().take(20) {
        let has_events = app_dir
            .as_ref()
            .map(|d| {
                d.join("outbox")
                    .join("runs")
                    .join(run_id)
                    .join("events.jsonl")
                    .exists()
            })
            .unwrap_or(false);
        let events_badge = if has_events {
            " <span class=\"badge\">events</span>"
        } else {
            ""
        };
        run_rows.push_str(&format!(
            "<tr><td><a href=\"/apps/{}/runs/{}\">{}</a>{}</td><td>{}</td></tr>",
            html_escape::encode_text(&app.id),
            html_escape::encode_text(run_id),
            html_escape::encode_text(run_id),
            events_badge,
            html_escape::encode_text(ts),
        ));
    }
    if run_rows.is_empty() {
        run_rows = "<tr><td colspan=\"2\">No runs yet.</td></tr>".to_string();
    }

    // Evidence for this app
    let solace_home = crate::utils::solace_home();
    let all_evidence = crate::evidence::list_evidence(&solace_home, 200);
    let app_evidence: Vec<_> = all_evidence
        .iter()
        .filter(|e| e.event.contains(&app.id) || e.actor.contains(&app.id))
        .take(20)
        .collect();
    let mut evidence_rows = String::new();
    for entry in &app_evidence {
        evidence_rows.push_str(&format!(
            "<tr><td>{}</td><td><strong>{}</strong></td><td><code title=\"{}\">{}&hellip;</code></td></tr>",
            html_escape::encode_text(&entry.timestamp),
            html_escape::encode_text(&entry.event),
            html_escape::encode_text(&entry.hash),
            html_escape::encode_text(&entry.hash[..12.min(entry.hash.len())]),
        ));
    }
    if evidence_rows.is_empty() {
        evidence_rows = "<tr><td colspan=\"3\" class=\"sb-text-muted\">No evidence records for this app yet.</td></tr>".to_string();
    }

    let icon = domain_icon_path(&app.domain);
    let body = format!(
        r#"<p><a href="/domains/{domain}">&larr; {domain}</a></p>
<div class="sb-flex" class="sb-section-header">
  <img class="sb-app-icon" src="{icon}" alt="">
  <span class="sb-pill sb-pill--info">{domain}</span>
  <span class="sb-pill sb-pill--success">v{version}</span>
</div>

<div class="sb-tabs" role="tablist">
  <button class="sb-tab sb-tab--active" data-tab="overview" onclick="showTab(this,'overview')">Overview</button>
  <button class="sb-tab" data-tab="runs" onclick="showTab(this,'runs')">Runs</button>
  <button class="sb-tab" data-tab="evidence" onclick="showTab(this,'evidence')">Evidence</button>
  <button class="sb-tab" data-tab="settings" onclick="showTab(this,'settings')">Settings</button>
  <button class="sb-tab" data-tab="share" onclick="showTab(this,'share')">Share</button>
</div>

<div id="panel-overview" class="sb-tab-panel">
  {manifest_section}
</div>

<div id="panel-runs" class="sb-tab-panel" hidden>
  <table class="sb-table"><thead><tr><th>Run ID</th><th>Time</th></tr></thead><tbody>{run_rows}</tbody></table>
</div>

<div id="panel-evidence" class="sb-tab-panel" hidden>
  <table class="sb-table"><thead><tr><th>Timestamp</th><th>Event</th><th>Hash</th></tr></thead><tbody>{evidence_rows}</tbody></table>
  <p class="sb-section"><a href="/evidence" class="sb-btn sb-btn--sm">Full Evidence Chain</a></p>
</div>

<div id="panel-settings" class="sb-tab-panel" hidden>
  <div class="sb-card">
    <table class="sb-table">
      <tr><td><strong>Schedule</strong></td><td><code>{schedule}</code></td></tr>
      <tr><td><strong>Tier</strong></td><td>{tier}</td></tr>
      <tr><td><strong>Template</strong></td><td>{template}</td></tr>
      <tr><td><strong>Source URL</strong></td><td>{source_url}</td></tr>
    </table>
  </div>
</div>

<div id="panel-share" class="sb-tab-panel" hidden>
  <div class="sb-card">
    <h3>Share this app</h3>
    <p class="sb-text-muted">Send this app to a colleague. They install it locally — your data stays yours.</p>
    <div >
      <label >Recipient email</label>
      <input type="email" id="share-app-email" placeholder="colleague@company.com" class="sb-input">
    </div>
    <button class="sb-btn sb-btn--sm sb-btn--primary" onclick="shareApp()">Share via solaceagi.com</button>
    <p id="share-app-result" class="sb-text-muted sb-section"></p>
  </div>
</div>

<script>
function showTab(btn, id) {{
  document.querySelectorAll('.sb-tab').forEach(t => t.classList.remove('sb-tab--active'));
  document.querySelectorAll('.sb-tab-panel').forEach(p => p.hidden = true);
  btn.classList.add('sb-tab--active');
  document.getElementById('panel-' + id).hidden = false;
}}
</script>"#,
        domain = html_escape::encode_text(&app.domain),
        icon = html_escape::encode_text(&icon),
        version = html_escape::encode_text(&app.version),
        schedule = schedule_display,
        tier = tier_display,
        template = html_escape::encode_text(&app.report_template),
        source_url = app.source_url.as_deref().filter(|s| !s.is_empty()).map(|s| html_escape::encode_text(s).to_string()).unwrap_or_else(|| "—".to_string()),
    );

    Ok(Html(hub_page(
        &format!("App: {}", html_escape::encode_text(&app.name)),
        &body,
    )))
}

// ---------------------------------------------------------------------------
// GET /apps/:app_id/runs/:run_id — run detail (event log viewer)
// ---------------------------------------------------------------------------
async fn run_detail_page(
    Path((app_id, run_id)): Path<(String, String)>,
) -> Result<Html<String>, (StatusCode, Html<String>)> {
    let app_dir = crate::utils::find_app_dir(&app_id).ok_or_else(|| {
        (
            StatusCode::NOT_FOUND,
            Html(hub_page(
                "App Not Found",
                &format!(
                    "<p>App <strong>{}</strong> not found.</p>",
                    html_escape::encode_text(&app_id)
                ),
            )),
        )
    })?;

    let run_dir = app_dir.join("outbox").join("runs").join(&run_id);
    if !run_dir.is_dir() {
        return Err((
            StatusCode::NOT_FOUND,
            Html(hub_page(
                "Run Not Found",
                &format!(
                    "<p>Run <strong>{}</strong> not found for app {}.</p><p><a href=\"/apps/{}\">&larr; Back to app</a></p>",
                    html_escape::encode_text(&run_id),
                    html_escape::encode_text(&app_id),
                    html_escape::encode_text(&app_id),
                ),
            )),
        ));
    }

    // Load events
    let events_path = run_dir.join("events.jsonl");
    let (event_rows, chain_valid) = if events_path.exists() {
        match crate::event_log::EventLog::load_from_file(&app_id, &run_id, &events_path) {
            Ok(log) => {
                let valid = log.verify_chain();
                let mut rows = String::new();
                for event in log.events() {
                    let css_class = event_css_class(&event.event_type);
                    let detail_text = event
                        .detail
                        .as_deref()
                        .or(event.url.as_deref())
                        .or(event.selector.as_deref())
                        .unwrap_or("—");
                    let type_str =
                        serde_json::to_string(&event.event_type).unwrap_or_default();
                    let type_display = type_str.trim_matches('"');
                    rows.push_str(&format!(
                        "<tr class=\"{css_class}\">\
                         <td>{}</td>\
                         <td><strong>{}</strong></td>\
                         <td>{}</td>\
                         <td><code title=\"{}\">{}&hellip;</code></td>\
                         </tr>",
                        html_escape::encode_text(&event.timestamp),
                        html_escape::encode_text(type_display),
                        html_escape::encode_text(detail_text),
                        html_escape::encode_text(&event.sha256),
                        html_escape::encode_text(&event.sha256[..12.min(event.sha256.len())]),
                    ));
                }
                (rows, valid)
            }
            Err(err) => (
                format!(
                    "<tr><td colspan=\"4\">Error loading events: {}</td></tr>",
                    html_escape::encode_text(&err)
                ),
                false,
            ),
        }
    } else {
        (
            "<tr><td colspan=\"4\">No events.jsonl for this run.</td></tr>".to_string(),
            false,
        )
    };

    let chain_badge = if chain_valid {
        "<span class=\"badge chain-valid\">Chain Valid</span>"
    } else if events_path.exists() {
        "<span class=\"badge chain-invalid\">Chain Invalid</span>"
    } else {
        ""
    };

    // Check for report.html
    let report_link = if run_dir.join("report.html").exists() {
        format!(
            " <a href=\"/api/v1/apps/{}/runs/{}/report\" class=\"btn\">View Full HTML</a>",
            html_escape::encode_text(&app_id),
            html_escape::encode_text(&run_id),
        )
    } else {
        String::new()
    };

    let body = format!(
        "<p><a href=\"/apps/{}\">&larr; {}</a></p>\
         <p>{chain_badge}{report_link} <a href=\"/evidence\" class=\"btn\">Evidence Chain</a></p>\
         <h2>Event Log</h2>\
         <table class=\"events\"><thead><tr><th>Timestamp</th><th>Type</th><th>Detail</th><th>Hash</th></tr></thead>\
         <tbody>{event_rows}</tbody></table>",
        html_escape::encode_text(&app_id),
        html_escape::encode_text(&app_id),
    );

    Ok(Html(hub_page(
        &format!(
            "Run: {} / {}",
            html_escape::encode_text(&app_id),
            html_escape::encode_text(&run_id)
        ),
        &body,
    )))
}

// ---------------------------------------------------------------------------
// GET /evidence — evidence chain viewer
// ---------------------------------------------------------------------------
async fn evidence_page() -> Html<String> {
    let solace_home = crate::utils::solace_home();
    let entries = crate::evidence::list_evidence(&solace_home, 100);
    let part11 = crate::evidence::part11_status(&solace_home);

    let status_badge = if part11.chain_valid {
        "<span class=\"badge chain-valid\">Chain Valid</span>"
    } else if part11.record_count > 0 {
        "<span class=\"badge chain-invalid\">Chain Broken</span>"
    } else {
        "<span class=\"badge\">No Records</span>"
    };

    let mut rows = String::new();
    for entry in &entries {
        rows.push_str(&format!(
            "<tr>\
             <td>{}</td>\
             <td><strong>{}</strong></td>\
             <td>{}</td>\
             <td><code title=\"{}\">{}&hellip;</code></td>\
             <td><code title=\"{}\">{}&hellip;</code></td>\
             </tr>",
            html_escape::encode_text(&entry.timestamp),
            html_escape::encode_text(&entry.event),
            html_escape::encode_text(&entry.actor),
            html_escape::encode_text(&entry.hash),
            html_escape::encode_text(&entry.hash[..12.min(entry.hash.len())]),
            html_escape::encode_text(&entry.previous_hash),
            if entry.previous_hash.is_empty() {
                "genesis"
            } else {
                &entry.previous_hash[..12.min(entry.previous_hash.len())]
            },
        ));
    }
    if rows.is_empty() {
        rows =
            "<tr><td colspan=\"5\">No evidence records yet. Run an app to generate evidence.</td></tr>"
                .to_string();
    }

    let body = format!(
        "<p><a href=\"/domains\">&larr; All Domains</a></p>\
         <p>Part 11 Status: {status_badge} &mdash; {} records &mdash; ALCOA: {}</p>\
         <h2>Evidence Chain</h2>\
         <table class=\"events\"><thead><tr><th>Timestamp</th><th>Event</th><th>Actor</th><th>Hash</th><th>Prev Hash</th></tr></thead>\
         <tbody>{rows}</tbody></table>",
        part11.record_count,
        part11.alcoa.join(", "),
    );

    Html(hub_page("Evidence Chain", &body))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// GET /appstore — local app store (installed vs available)
// ---------------------------------------------------------------------------
async fn appstore_page(State(state): State<AppState>) -> Html<String> {
    let apps = crate::app_engine::scan_installed_apps();
    let mut domain_map: BTreeMap<String, Vec<&crate::app_engine::AppManifest>> = BTreeMap::new();
    for app in &apps {
        domain_map.entry(app.domain.clone()).or_default().push(app);
    }

    let mut installed_cards = String::new();
    for app in &apps {
        let icon = domain_icon_path(&app.domain);
        let tier_pill = if app.tier.is_empty() || app.tier == "free" {
            "<span class=\"sb-pill sb-pill--success\">Free</span>"
        } else {
            "<span class=\"sb-pill sb-pill--info\">Paid</span>"
        };
        installed_cards.push_str(&format!(
            r#"<div class="sb-card">
  <div class="sb-card-header">
    <h3 class="sb-card-title sb-app-name"><img class="sb-app-icon" src="{icon}" alt="{name} icon" loading="lazy"><a href="/apps/{id}">{name}</a></h3>
    {tier_pill}
  </div>
  <div class="sb-card-body"><p>{desc}</p>
    <div class="sb-section"><span class="sb-pill sb-pill--info">{domain}</span> <span class="sb-text-muted">v{ver}</span></div>
  </div>
</div>"#,
            icon = html_escape::encode_text(&icon),
            id = html_escape::encode_text(&app.id),
            name = html_escape::encode_text(&app.name),
            desc = html_escape::encode_text(&app.description),
            domain = html_escape::encode_text(&app.domain),
            ver = html_escape::encode_text(&app.version),
        ));
    }

    let cloud = state.cloud_config.read().is_some();
    let store_section = if cloud {
        "<div class=\"sb-card\"><p>Connected to solaceagi.com — <a href=\"https://solaceagi.com/app-store\">Browse App Store</a></p></div>"
    } else {
        "<div class=\"sb-card\"><p class=\"sb-text-muted\">Connect to solaceagi.com to browse the full app store with 35+ apps.</p>\
         <p class=\"sb-section\"><a href=\"/settings\" class=\"sb-btn sb-btn--sm\">Connect Cloud</a> \
         <a href=\"https://solaceagi.com/app-store\" class=\"sb-btn sb-btn--sm sb-btn--primary\" target=\"_blank\">Browse Online</a></p></div>"
    };

    let body = format!(
        r#"<div class="sb-section-header">
  <div><span class="sb-pill sb-pill--success">{count} installed</span> across <strong>{domains}</strong> domains</div>
  <a href="https://solaceagi.com/app-store" class="sb-btn sb-btn--sm sb-btn--primary" target="_blank">Browse App Store</a>
</div>
<h2 class="sb-heading">Installed Apps</h2>
<div class="sb-card-grid">{installed_cards}</div>
<h2 class="sb-heading sb-section">Available from Store</h2>
{store_section}
<h2 class="sb-heading sb-section">Create Custom App</h2>
<div class="sb-card"><p>Create a folder in <code>~/.solace/apps/{{domain}}/{{app-id}}/</code> with a <code>manifest.md</code> file.</p>
<p class="sb-section">The <a href="https://solaceagi.com/docs/app-standard">Solace App Standard</a> defines the manifest format, icons, templates, and inbox/outbox structure.</p>
<p class="sb-section"><a href="https://solaceagi.com/app-store/submit" class="sb-btn sb-btn--sm" target="_blank">Submit to Store</a></p></div>"#,
        count = apps.len(),
        domains = domain_map.len(),
    );
    Html(hub_page("App Store", &body))
}

// ---------------------------------------------------------------------------
// GET /llms — connected LLM sources
// ---------------------------------------------------------------------------
async fn llms_page(State(state): State<AppState>) -> Html<String> {
    let solace_home = crate::utils::solace_home();
    let has_byok = crate::config::has_byok_key(&solace_home);
    let cloud = state.cloud_config.read().clone();
    let is_paid = cloud.as_ref().map(|c| c.paid_user).unwrap_or(false);

    // Detect CLI agents
    let agents_json = match reqwest::Client::new()
        .get("http://127.0.0.1:8888/api/v1/agents")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(resp) => resp.text().await.unwrap_or_default(),
        Err(_) => String::new(),
    };
    let agents: Vec<serde_json::Value> = serde_json::from_str(&agents_json)
        .or_else(|_| {
            serde_json::from_str::<serde_json::Value>(&agents_json)
                .map(|v| v.get("agents").cloned().unwrap_or(serde_json::Value::Array(vec![])))
                .and_then(|v| serde_json::from_value(v))
        })
        .unwrap_or_default();

    let mut agent_rows = String::new();
    for agent in &agents {
        let name = agent.get("name").and_then(|v| v.as_str()).unwrap_or("unknown");
        let path = agent.get("path").and_then(|v| v.as_str()).unwrap_or("—");
        let status = agent.get("available").and_then(|v| v.as_bool()).unwrap_or(false);
        let pill = if status {
            "<span class=\"sb-pill sb-pill--success\">Available</span>"
        } else {
            "<span class=\"sb-pill sb-pill--danger\">Not Found</span>"
        };
        agent_rows.push_str(&format!(
            "<tr><td><strong>{}</strong></td><td><code>{}</code></td><td>{}</td></tr>",
            html_escape::encode_text(name),
            html_escape::encode_text(path),
            pill,
        ));
    }
    if agent_rows.is_empty() {
        agent_rows = "<tr><td colspan=\"3\" class=\"sb-text-muted\">No AI agents detected on PATH. Install claude, codex, gemini, or ollama.</td></tr>".to_string();
    }

    let byok_status = if has_byok {
        "<span class=\"sb-pill sb-pill--success\">BYOK Key Configured</span>"
    } else {
        "<span class=\"sb-pill sb-pill--warning\">No BYOK Key</span>"
    };

    let managed_status = if is_paid {
        "<span class=\"sb-pill sb-pill--success\">Managed LLM Active</span> — Together.ai + OpenRouter"
    } else {
        "<span class=\"sb-pill sb-pill--info\">Managed LLM</span> — <a href=\"https://solaceagi.com/pricing\">Upgrade to Starter ($8/mo)</a>"
    };

    let body = format!(
        r#"<h2 class="sb-heading">Detected AI Agents</h2>
<div class="sb-card">
  <p class="sb-text-muted" >Solace auto-detects AI tools on your PATH and wraps them as HTTP endpoints.</p>
  <table class="sb-table"><thead><tr><th>Agent</th><th>Path</th><th>Status</th></tr></thead>
  <tbody>{agent_rows}</tbody></table>
</div>

<h2 class="sb-heading sb-section">API Keys (BYOK)</h2>
<div class="sb-card">
  <p>{byok_status}</p>
  <p class="sb-text-muted sb-section">BYOK keys are stored locally in AES-256-GCM encrypted vault. Never sent to solaceagi.com.</p>
</div>

<h2 class="sb-heading sb-section">Managed LLM</h2>
<div class="sb-card">
  <p>{managed_status}</p>
  <p class="sb-text-muted sb-section">Primary: Llama 3.3 70B ($0.59/M tokens) via Together.ai. Fallback: OpenRouter (Claude, GPT-4, Mixtral).</p>
</div>

<h2 class="sb-heading sb-section">Models</h2>
<div class="sb-card">
  <table class="sb-table"><thead><tr><th>Level</th><th>Use Case</th><th>Example Models</th></tr></thead>
  <tbody>
    <tr><td><strong>L1</strong></td><td>Fast tasks, formatting</td><td>Haiku, GPT-4o-mini</td></tr>
    <tr><td><strong>L2</strong></td><td>General coding, analysis</td><td>Sonnet, GPT-4o</td></tr>
    <tr><td><strong>L3</strong></td><td>Complex reasoning</td><td>Opus, GPT-5</td></tr>
    <tr><td><strong>L4</strong></td><td>Deep research, math</td><td>Opus (extended), O3</td></tr>
    <tr><td><strong>L5</strong></td><td>Architecture, strategy</td><td>Multi-model consensus</td></tr>
  </tbody></table>
</div>"#,
    );
    Html(hub_page("LLMs", &body))
}

// ---------------------------------------------------------------------------
// GET /budget — cost tracking
// ---------------------------------------------------------------------------
async fn budget_page(State(state): State<AppState>) -> Html<String> {
    let usage = state.budget_usage.read().clone();
    let solace_home = crate::utils::solace_home();
    let config = crate::config::load_budget_config(&solace_home);

    let daily_pct = if config.daily_limit > 0 {
        ((usage.daily_count as f64 / config.daily_limit as f64) * 100.0).min(100.0)
    } else {
        0.0
    };
    let monthly_pct = if config.monthly_limit > 0 {
        ((usage.monthly_count as f64 / config.monthly_limit as f64) * 100.0).min(100.0)
    } else {
        0.0
    };

    let daily_bar_class = if daily_pct > 80.0 { "sb-progress-bar--danger" } else if daily_pct > 50.0 { "sb-progress-bar--warning" } else { "sb-progress-bar--success" };
    let monthly_bar_class = if monthly_pct > 80.0 { "sb-progress-bar--danger" } else if monthly_pct > 50.0 { "sb-progress-bar--warning" } else { "sb-progress-bar--success" };

    let pause_status = if config.enforce {
        "<span class=\"sb-pill sb-pill--success\">Fail-Closed</span> — apps pause when budget exceeded"
    } else {
        "<span class=\"sb-pill sb-pill--warning\">Fail-Open</span> — apps continue past budget (not recommended)"
    };

    let body = format!(
        r#"<div class="sb-flex" class="sb-status-bar">
  <div class="sb-card" class="sb-stat-card">
    <p class="sb-kicker">Today ({date})</p>
    <div class="sb-stat-value">{daily_count} <span class="sb-text-muted" >/ {daily_limit} events</span></div>
    <div class="sb-progress"><div class="sb-progress-bar {daily_bar_class}" class="sb-progress-fill"></div></div>
  </div>
  <div class="sb-card" class="sb-stat-card">
    <p class="sb-kicker">This Month ({month})</p>
    <div class="sb-stat-value">{monthly_count} <span class="sb-text-muted" >/ {monthly_limit} events</span></div>
    <div class="sb-progress"><div class="sb-progress-bar {monthly_bar_class}" class="sb-progress-fill"></div></div>
  </div>
</div>

<h2 class="sb-heading">Budget Policy</h2>
<div class="sb-card"><p>{pause_status}</p></div>

<h2 class="sb-heading sb-section">Cost Breakdown</h2>
<div class="sb-card"><p class="sb-text-muted">Per-app and per-model cost breakdown available via <code>GET /api/v1/budget</code>.</p></div>"#,
        date = html_escape::encode_text(&usage.daily_date),
        daily_count = usage.daily_count,
        daily_limit = config.daily_limit,
        month = html_escape::encode_text(&usage.monthly_date),
        monthly_count = usage.monthly_count,
        monthly_limit = config.monthly_limit,
    );
    Html(hub_page("Budget", &body))
}

// ---------------------------------------------------------------------------
// GET /recipes — saved automations
// ---------------------------------------------------------------------------
async fn recipes_page() -> Html<String> {
    // Fetch recipes from API
    let recipes_json = match reqwest::Client::new()
        .get("http://127.0.0.1:8888/api/v1/recipes")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(resp) => resp.text().await.unwrap_or_default(),
        Err(_) => String::new(),
    };
    let recipes: Vec<serde_json::Value> = serde_json::from_str::<serde_json::Value>(&recipes_json)
        .ok()
        .and_then(|v| v.get("recipes").cloned())
        .and_then(|v| serde_json::from_value(v).ok())
        .unwrap_or_default();

    let mut recipe_cards = String::new();
    for recipe in &recipes {
        let name = recipe.get("name").and_then(|v| v.as_str()).unwrap_or("Unnamed");
        let domain = recipe.get("domain").and_then(|v| v.as_str()).unwrap_or("—");
        let hit_rate = recipe.get("hit_rate").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let hit_pill = if hit_rate >= 0.7 {
            format!("<span class=\"sb-pill sb-pill--success\">{:.0}% hit</span>", hit_rate * 100.0)
        } else if hit_rate >= 0.4 {
            format!("<span class=\"sb-pill sb-pill--warning\">{:.0}% hit</span>", hit_rate * 100.0)
        } else {
            format!("<span class=\"sb-pill sb-pill--danger\">{:.0}% hit</span>", hit_rate * 100.0)
        };
        recipe_cards.push_str(&format!(
            r#"<div class="sb-card"><div class="sb-card-header"><h3 class="sb-card-title">{name}</h3>{hit_pill}</div>
  <div class="sb-card-body"><span class="sb-pill sb-pill--info">{domain}</span></div></div>"#,
            name = html_escape::encode_text(name),
            domain = html_escape::encode_text(domain),
        ));
    }
    if recipe_cards.is_empty() {
        recipe_cards = r#"<div class="sb-empty"><div class="sb-empty-icon">&#x1F4DC;</div>
<p>No recipes yet.</p><p class="sb-text-muted">Recipes are saved automations that replay at zero LLM cost. They're created automatically when the hit rate is high enough.</p></div>"#.to_string();
    }

    let body = format!(
        r#"<p class="sb-text-muted" >Recipes = deterministic replay at $0.001/task (vs $0.01+ with LLM). 70% hit rate target.</p>
<div class="sb-card-grid">{recipe_cards}</div>"#,
    );
    Html(hub_page("Recipes", &body))
}

// ---------------------------------------------------------------------------
// GET /oauth3 — token management
// ---------------------------------------------------------------------------
async fn oauth3_page() -> Html<String> {
    let oauth3_json = match reqwest::Client::new()
        .get("http://127.0.0.1:8888/api/v1/oauth3/tokens")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(resp) => resp.text().await.unwrap_or_default(),
        Err(_) => String::new(),
    };
    let tokens: Vec<serde_json::Value> = serde_json::from_str::<serde_json::Value>(&oauth3_json)
        .ok()
        .and_then(|v| v.get("tokens").cloned())
        .and_then(|v| serde_json::from_value(v).ok())
        .unwrap_or_default();

    let mut token_rows = String::new();
    for token in &tokens {
        let scope = token.get("scope").and_then(|v| v.as_str()).unwrap_or("—");
        let app = token.get("app_id").and_then(|v| v.as_str()).unwrap_or("—");
        let expires = token.get("expires_at").and_then(|v| v.as_str()).unwrap_or("—");
        let status = token.get("revoked").and_then(|v| v.as_bool()).unwrap_or(false);
        let pill = if status {
            "<span class=\"sb-pill sb-pill--danger\">Revoked</span>"
        } else {
            "<span class=\"sb-pill sb-pill--success\">Active</span>"
        };
        token_rows.push_str(&format!(
            "<tr><td>{}</td><td><code>{}</code></td><td>{}</td><td>{}</td></tr>",
            html_escape::encode_text(app),
            html_escape::encode_text(scope),
            html_escape::encode_text(expires),
            pill,
        ));
    }
    if token_rows.is_empty() {
        token_rows = "<tr><td colspan=\"4\" class=\"sb-text-muted\">No OAuth3 tokens. Tokens are created when apps request scoped access to your data.</td></tr>".to_string();
    }

    let body = format!(
        r#"<p class="sb-text-muted" >OAuth3 tokens are scoped, time-limited, and revocable. Each app gets only the permissions it needs.</p>
<h2 class="sb-heading">Active Tokens</h2>
<div class="sb-card">
  <table class="sb-table"><thead><tr><th>App</th><th>Scope</th><th>Expires</th><th>Status</th></tr></thead>
  <tbody>{token_rows}</tbody></table>
</div>
<h2 class="sb-heading sb-section">Register New Token</h2>
<div class="sb-card"><p class="sb-text-muted">Use <code>POST /api/v1/oauth3/register</code> to create a new scoped token for an app.</p></div>"#,
    );
    Html(hub_page("OAuth3 Tokens", &body))
}

// ---------------------------------------------------------------------------
// GET /esign — e-signatures + approval queue
// ---------------------------------------------------------------------------
async fn esign_page(State(state): State<AppState>) -> Html<String> {
    let notifications = state.notifications.read().clone();
    let pending: Vec<_> = notifications.iter().filter(|n| n.level == "signoff" || n.level == "L3" || n.level == "L4" || n.level == "L5").collect();

    let mut pending_rows = String::new();
    for note in &pending {
        let level_pill = match note.level.as_str() {
            "L3" => "<span class=\"sb-pill sb-pill--warning\">L3</span>",
            "L4" => "<span class=\"sb-pill sb-pill--danger\">L4</span>",
            "L5" => "<span class=\"sb-pill sb-pill--danger\">L5 Critical</span>",
            _ => "<span class=\"sb-pill sb-pill--warning\">Signoff</span>",
        };
        pending_rows.push_str(&format!(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>\
             <button class=\"sb-btn sb-btn--sm sb-btn--primary\">Approve</button> \
             <button class=\"sb-btn sb-btn--sm\">Reject</button></td></tr>",
            level_pill,
            html_escape::encode_text(&note.message),
            html_escape::encode_text(&note.created_at),
        ));
    }
    if pending_rows.is_empty() {
        pending_rows = "<tr><td colspan=\"4\" class=\"sb-text-muted\">No pending approvals. L3+ actions require human signoff before execution.</td></tr>".to_string();
    }

    let body = format!(
        r#"<p class="sb-text-muted" >FDA Part 11 compliant electronic signatures. L3+ actions require human approval. Timeout = auto-DENY (never auto-approve).</p>
<h2 class="sb-heading">Pending Approvals</h2>
<div class="sb-card">
  <table class="sb-table"><thead><tr><th>Level</th><th>Action</th><th>Time</th><th>Decision</th></tr></thead>
  <tbody>{pending_rows}</tbody></table>
</div>

<h2 class="sb-heading sb-section">Tunnel Access Consent</h2>
<div class="sb-card">
  <p class="sb-text-muted">Remote access requires FDA Part 11 signed consent. All remote actions are fully audited.</p>
  <p class="sb-section"><a href="/settings" class="sb-btn sb-btn--sm">Configure Tunnel</a></p>
</div>

<h2 class="sb-heading sb-section">Signature History</h2>
<div class="sb-card"><p class="sb-text-muted">View past approvals and rejections via <code>GET /api/v1/evidence</code> (filtered by type=signoff).</p>
<p class="sb-section"><a href="/evidence" class="sb-btn sb-btn--sm">View Evidence Chain</a></p></div>"#,
    );
    Html(hub_page("E-Signatures", &body))
}

// ---------------------------------------------------------------------------
// GET /wiki-hub — captured knowledge
// ---------------------------------------------------------------------------
async fn wiki_page() -> Html<String> {
    let wiki_json = match reqwest::Client::new()
        .get("http://127.0.0.1:8888/api/v1/wiki/stats")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(resp) => resp.text().await.unwrap_or_default(),
        Err(_) => String::new(),
    };
    let stats: serde_json::Value = serde_json::from_str(&wiki_json).unwrap_or(serde_json::json!({}));
    let snapshot_count = stats.get("snapshot_count").and_then(|v| v.as_u64()).unwrap_or(0);
    let domain_count = stats.get("domain_count").and_then(|v| v.as_u64()).unwrap_or(0);

    let body = format!(
        r#"<div class="sb-flex" class="sb-status-bar">
  <div class="sb-card" class="sb-stat-card">
    <div class="sb-kicker">Snapshots</div>
    <div class="sb-stat-value">{snapshot_count}</div>
  </div>
  <div class="sb-card" class="sb-stat-card">
    <div class="sb-kicker">Domains</div>
    <div class="sb-stat-value">{domain_count}</div>
  </div>
</div>

<h2 class="sb-heading">Prime Wiki Snapshots</h2>
<div class="sb-card">
  <p class="sb-text-muted">Every page navigation creates a Prime Wiki snapshot: compressed, agent-readable, replayable at $0.</p>
  <p class="sb-section">Formats: <code>.prime-snapshot.md</code> (Mermaid) + <code>.pzwb</code> (PZip Web Binary)</p>
</div>

<h2 class="sb-heading sb-section">Stillwater Codecs</h2>
<div class="sb-card">
  <table class="sb-table"><thead><tr><th>Codec</th><th>Format</th><th>Use Case</th></tr></thead>
  <tbody>
    <tr><td><strong>semantic-html</strong></td><td>PZSW</td><td>Structured HTML pages</td></tr>
    <tr><td><strong>table-html</strong></td><td>PZSW</td><td>Data tables + forms</td></tr>
    <tr><td><strong>json-api</strong></td><td>PZJ0</td><td>API responses</td></tr>
    <tr><td><strong>rss-xml</strong></td><td>PZSW</td><td>RSS/Atom feeds</td></tr>
    <tr><td><strong>jinja-template</strong></td><td>PZSW</td><td>HTML templates</td></tr>
    <tr><td><strong>spa-shell</strong></td><td>PZSW</td><td>Single-page apps</td></tr>
  </tbody></table>
</div>"#,
    );
    Html(hub_page("Wiki", &body))
}

// ---------------------------------------------------------------------------
// GET /settings — global configuration
// ---------------------------------------------------------------------------
async fn settings_page(State(state): State<AppState>) -> Html<String> {
    let theme = state.theme.read().clone();
    let cloud = state.cloud_config.read().clone();
    let uptime = state.uptime_seconds();

    let cloud_status = if let Some(ref config) = cloud {
        format!(
            "<span class=\"sb-pill sb-pill--success\">Connected</span> — {} ({})",
            html_escape::encode_text(&config.user_email),
            if config.paid_user { "Paid" } else { "Free" },
        )
    } else {
        "<span class=\"sb-pill sb-pill--warning\">Not Connected</span> — <a href=\"https://solaceagi.com/dashboard\">Sign in to connect</a>".to_string()
    };

    let body = format!(
        r#"<h2 class="sb-heading">Appearance</h2>
<div class="sb-card">
  <p>Theme: <strong>{theme}</strong></p>
  <div class="sb-theme-group sb-section">
    <button class="sb-theme-btn {dark_active}" onclick="fetch('/api/v1/settings/theme',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{theme:'dark'}})}}).then(()=>location.reload())">Dark</button>
    <button class="sb-theme-btn {light_active}" onclick="fetch('/api/v1/settings/theme',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{theme:'light'}})}}).then(()=>location.reload())">Light</button>
  </div>
</div>

<h2 class="sb-heading sb-section">Cloud Connection</h2>
<div class="sb-card"><p>{cloud_status}</p></div>

<h2 class="sb-heading sb-section">Tunnel &amp; Remote Access</h2>
<div class="sb-card">
  <p class="sb-text-muted">Allow remote control from solaceagi.com for demos, support, or team collaboration.</p>
  <p class="sb-section">Status: <span class="sb-pill sb-pill--info">Not Connected</span></p>
  <p class="sb-section sb-text-muted">Requires FDA Part 11 signed consent. All remote actions audited.</p>
</div>

<h2 class="sb-heading sb-section">Runtime Info</h2>
<div class="sb-card">
  <table class="sb-table">
    <tr><td><strong>Platform</strong></td><td>{platform}</td></tr>
    <tr><td><strong>Port</strong></td><td>8888 (fixed)</td></tr>
    <tr><td><strong>Uptime</strong></td><td>{hours}h {mins}m</td></tr>
    <tr><td><strong>Data Dir</strong></td><td><code>~/.solace/</code></td></tr>
    <tr><td><strong>Version</strong></td><td>Solace Runtime v0.1.0</td></tr>
  </table>
</div>

<h2 class="sb-heading sb-section">Export / Import</h2>
<div class="sb-card">
  <p class="sb-text-muted">Export your settings, apps, and evidence as a portable bundle.</p>
  <p class="sb-section">
    <a href="/api/v1/cloud/sync/export" class="sb-btn sb-btn--sm">Export Settings</a>
    <a href="/api/v1/cloud/sync/import" class="sb-btn sb-btn--sm">Import Settings</a>
  </p>
</div>

<h2 class="sb-heading sb-section">Developer</h2>
<div class="sb-card">
  <p><a href="/api/v1/system/status">System Status API</a> | <a href="/api/v1/health">Health</a> | <a href="/styleguide">Styleguide</a></p>
  <p class="sb-section sb-text-muted">MCP: <code>solace-runtime --mcp</code> (stdio, 8 tools + 2 resources)</p>
</div>"#,
        theme = html_escape::encode_text(&theme),
        dark_active = if theme == "dark" { "sb-theme-btn--active" } else { "" },
        light_active = if theme == "light" { "sb-theme-btn--active" } else { "" },
        platform = std::env::consts::OS,
        hours = uptime / 3600,
        mins = (uptime % 3600) / 60,
    );
    Html(hub_page("Settings", &body))
}

// ---------------------------------------------------------------------------
// GET /hire — "Hire an AI Worker" job description wizard
// ---------------------------------------------------------------------------
async fn hire_page(State(state): State<AppState>) -> Html<String> {
    let apps = crate::app_engine::scan_installed_apps();
    let role_apps: Vec<_> = apps.iter().filter(|a| a.category == "role").collect();

    // Existing team org chart
    let mut team_rows = String::new();
    for app in &role_apps {
        let app_dir = crate::utils::find_app_dir(&app.id);
        let run_count = app_dir.as_ref().map(|d| count_runs(d)).unwrap_or(0);
        team_rows.push_str(&format!(
            "<tr><td><strong>{name}</strong></td><td>{id}</td><td>{sched}</td><td>{runs}</td></tr>",
            name = html_escape::encode_text(&app.name),
            id = html_escape::encode_text(&app.id),
            sched = if app.schedule.is_empty() { "Manual" } else { &app.schedule },
            runs = run_count,
        ));
    }
    if team_rows.is_empty() {
        team_rows = "<tr><td colspan=\"4\" class=\"sb-text-muted\">No AI workers hired yet. Use the form below to hire your first worker.</td></tr>".to_string();
    }

    let body = format!(
        r##"<section aria-labelledby="team-heading">
  <div class="sb-section-header">
    <h2 id="team-heading" class="sb-heading">Your AI Team</h2>
    <span class="sb-pill sb-pill--success">{team_count} workers</span>
  </div>
  <table class="sb-table"><thead><tr><th>Role</th><th>Worker ID</th><th>Schedule</th><th>Runs</th></tr></thead>
  <tbody>{team_rows}</tbody></table>
</section>

<section class="sb-section" aria-labelledby="hire-heading">
  <h2 id="hire-heading" class="sb-heading">Hire a New AI Worker</h2>
  <p class="sb-text-muted">Describe the job like a job posting. The system detects the role, assigns a persona, and creates a working AI employee.</p>

  <form method="POST" action="/api/v1/apps/create-from-job" class="sb-card" id="hire-form">
    <div class="sb-section">
      <label class="sb-kicker">Company Name</label>
      <input type="text" name="company" placeholder="e.g., BrainLife, Metalmark, Acme Corp" class="sb-input" required>
    </div>
    <div class="sb-section">
      <label class="sb-kicker">Job Description</label>
      <textarea name="job_description" rows="6" placeholder="Describe what this AI worker should do. Example: 'Monitor competitors in the neurotechnology space. Track product launches, pricing changes, partnerships, funding rounds. Produce a weekly competitor digest.'" class="sb-input" required></textarea>
    </div>
    <div class="sb-section">
      <label class="sb-kicker">Department (optional — auto-detected from description)</label>
      <select name="role" class="sb-input">
        <option value="">Auto-detect from description</option>
        <option value="bizdev">Business Development</option>
        <option value="competitor">Competitor Research</option>
        <option value="market">Market Analysis</option>
        <option value="sales">Sales Operations</option>
        <option value="customer_success">Customer Success</option>
        <option value="content">Content Marketing</option>
        <option value="recruiting">Recruiting</option>
        <option value="financial">Financial Analysis</option>
        <option value="legal">Legal &amp; Compliance</option>
        <option value="product">Product Management</option>
        <option value="security">Security &amp; Risk</option>
        <option value="operations">Operations</option>
        <option value="executive">Executive Intelligence</option>
      </select>
    </div>
    <button type="submit" class="sb-btn sb-btn--primary">Hire AI Worker</button>
  </form>
</section>

<section class="sb-section" aria-labelledby="roles-heading">
  <h2 id="roles-heading" class="sb-heading">Available Departments</h2>
  <div class="sb-card-grid">
    <div class="sb-card"><h3>Business Development</h3><p class="sb-text-muted">Find leads, research prospects, draft outreach. Persona: Alex Hormozi.</p></div>
    <div class="sb-card"><h3>Competitor Research</h3><p class="sb-text-muted">Monitor competitors, pricing, features, hiring, funding. Persona: Peter Thiel.</p></div>
    <div class="sb-card"><h3>Market Analysis</h3><p class="sb-text-muted">Market size, trends, demand drivers, growth projections. Persona: Ben Thompson.</p></div>
    <div class="sb-card"><h3>Content Marketing</h3><p class="sb-text-muted">Blog drafts, social posts, SEO keywords, content calendar. Persona: Gary Vaynerchuk.</p></div>
    <div class="sb-card"><h3>Sales Operations</h3><p class="sb-text-muted">Pipeline tracking, deal scoring, CRM sync. Persona: Grant Cardone.</p></div>
    <div class="sb-card"><h3>Financial Analysis</h3><p class="sb-text-muted">Revenue modeling, unit economics, benchmarks. Persona: Aswath Damodaran.</p></div>
    <div class="sb-card"><h3>Legal &amp; Compliance</h3><p class="sb-text-muted">Contract review, regulatory monitoring, compliance. Persona: Marc Andreessen.</p></div>
    <div class="sb-card"><h3>Executive Intelligence</h3><p class="sb-text-muted">CEO briefing, strategic signals, board prep. Persona: Peter Drucker.</p></div>
  </div>
</section>"##,
        team_count = role_apps.len(),
    );
    Html(hub_page("Hire AI Workers", &body))
}

/// Map a domain name to its icon path in /icons/apps/.
/// Tries common names: domain root, subdomain keyword, known brands.
fn domain_icon_path(domain: &str) -> String {
    // Map domain → icon filename (order: exact match, root domain, keyword)
    let mappings: &[(&str, &str)] = &[
        ("google.com", "google-search.png"),
        ("news.google.com", "google-search.png"),
        ("mail.google.com", "gmail.jpg"),
        ("drive.google.com", "google-drive.png"),
        ("calendar.google.com", "google-calendar.png"),
        ("news.ycombinator.com", "hackernews.png"),
        ("reddit.com", "reddit.jpg"),
        ("gmail.com", "gmail.jpg"),
        ("github.com", "github.png"),
        ("amazon.com", "amazon.png"),
        ("web.whatsapp.com", "whats-app.jpg"),
        ("solaceagi.com", "/icons/yinyang-logo.png"),
        ("multi-site", "/icons/orchestration.png"),
    ];

    for (d, icon) in mappings {
        if domain == *d {
            if icon.starts_with('/') {
                return icon.to_string();
            }
            return format!("/icons/apps/{}", icon);
        }
    }

    // Try the root domain (strip subdomain) — e.g. "portal.example.com" → "example"
    let parts: Vec<&str> = domain.split('.').collect();
    let root = if parts.len() >= 2 {
        parts[parts.len() - 2]
    } else {
        parts[0]
    };

    // Try common extensions in the Hub icons directory (cross-platform)
    let icons_dir = hub_assets_dir("icons").join("apps");
    for ext in &["png", "jpg", "svg"] {
        let filename = format!("{}.{}", root, ext);
        if icons_dir.join(&filename).exists() {
            return format!("/icons/apps/{}", filename);
        }
    }

    // Fallback: yinyang logo
    "/icons/yinyang-logo.png".to_string()
}

/// CSS class for event type rows.
fn event_css_class(event_type: &crate::event_log::EventType) -> &'static str {
    use crate::event_log::EventType;
    match event_type {
        EventType::Preview => "event-preview",
        EventType::SignOff => "event-signoff",
        EventType::Seal => "event-seal",
        _ => "event-normal",
    }
}

/// List run directories for an app, returning (run_id, modified_time).
fn list_runs(app_dir: &std::path::Path) -> Vec<(String, String)> {
    let runs_dir = app_dir.join("outbox").join("runs");
    let mut runs: Vec<(String, String)> = fs::read_dir(&runs_dir)
        .ok()
        .into_iter()
        .flatten()
        .flatten()
        .filter(|entry| entry.path().is_dir())
        .filter_map(|entry| {
            let name = entry.file_name().to_string_lossy().to_string();
            let ts = crate::utils::modified_iso8601(&entry.path())
                .unwrap_or_else(|| "—".to_string());
            Some((name, ts))
        })
        .collect();
    runs.sort_by(|a, b| a.0.cmp(&b.0));
    runs
}

/// Count run directories for an app.
fn count_runs(app_dir: &std::path::Path) -> usize {
    let runs_dir = app_dir.join("outbox").join("runs");
    fs::read_dir(&runs_dir)
        .ok()
        .into_iter()
        .flatten()
        .flatten()
        .filter(|entry| entry.path().is_dir())
        .count()
}

/// Get the latest run's modified time for an app directory.
fn latest_run_time(app_dir: &std::path::Path) -> Option<String> {
    let runs_dir = app_dir.join("outbox").join("runs");
    let mut dirs: Vec<_> = fs::read_dir(&runs_dir)
        .ok()?
        .flatten()
        .filter(|entry| entry.path().is_dir())
        .map(|entry| entry.path())
        .collect();
    dirs.sort();
    dirs.last()
        .and_then(|p| crate::utils::modified_iso8601(p))
}

/// Serve the styleguide page from the Hub frontend directory (cross-platform).
async fn styleguide_page() -> Html<String> {
    let path = hub_assets_dir(".").join("styleguide.html");
    if let Ok(content) = fs::read_to_string(&path) {
        return Html(content);
    }
    // Try parent (hub/src/ in dev has styleguide at same level as icons/)
    let alt = hub_assets_dir("..").join("styleguide.html");
    if let Ok(content) = fs::read_to_string(&alt) {
        return Html(content);
    }
    Html("<html><body><h1>Styleguide not found</h1><p>Place styleguide.html in ~/.solace/hub/</p></body></html>".to_string())
}

/// Serve the styleguide CSS from the Hub frontend directory (cross-platform).
async fn styleguide_css() -> (StatusCode, [(axum::http::header::HeaderName, &'static str); 1], String) {
    let path = hub_assets_dir(".").join("styleguide.css");
    if let Ok(content) = fs::read_to_string(&path) {
        return (StatusCode::OK, [(axum::http::header::CONTENT_TYPE, "text/css")], content);
    }
    let alt = hub_assets_dir("..").join("styleguide.css");
    if let Ok(content) = fs::read_to_string(&alt) {
        return (StatusCode::OK, [(axum::http::header::CONTENT_TYPE, "text/css")], content);
    }
    (StatusCode::NOT_FOUND, [(axum::http::header::CONTENT_TYPE, "text/css")], String::new())
}

/// Simple stub page (legacy — used by index, onboarding, sidebar).
fn page(title: &str, body: &str) -> String {
    format!(
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>{}</title>\
         <link rel=\"stylesheet\" href=\"/assets/runtime.css\"></head>\
         <body><main><h1>{}</h1><p>{}</p></main></body></html>",
        html_escape::encode_text(title),
        html_escape::encode_text(title),
        html_escape::encode_text(body),
    )
}

/// Full Hub App page — uses styleguide.css for all styling.
/// The styleguide is the single source of truth for visual design.
/// Rust assembles HTML using sb-* component classes from the styleguide.
/// Read the VERSION file at compile time for display in UI.
const SOLACE_VERSION: &str = include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/../VERSION"));

fn hub_page(title: &str, body_content: &str) -> String {
    let version = SOLACE_VERSION.trim();
    format!(
        r##"<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Solace Hub</title>
<link rel="icon" href="/icons/yinyang-logo.png">
<link rel="stylesheet" href="/styleguide.css">
<link rel="stylesheet" href="/vendor/jquery.dataTables.min.css">
<style>
/* Event type highlight rows (evidence/event log specific) */
.event-normal td {{ color: var(--sb-success); }}
.event-preview {{ background: rgba(255, 212, 121, 0.08); }}
.event-preview td {{ color: var(--sb-warning); }}
.event-signoff {{ background: rgba(255, 123, 123, 0.08); }}
.event-signoff td {{ color: var(--sb-danger); }}
.event-seal td {{ color: var(--sb-signal); }}
.chain-valid {{ background: var(--sb-success); color: var(--sb-on-accent); }}
.chain-invalid {{ background: var(--sb-danger); color: var(--sb-on-accent); }}
/* A11Y: Focus styles (WCAG 2.1 AA) */
:focus-visible {{ outline: 2px solid var(--sb-signal); outline-offset: 2px; }}
a:focus-visible {{ outline: 2px solid var(--sb-signal); outline-offset: 2px; }}
.sb-btn:focus-visible {{ outline: 2px solid var(--sb-signal); outline-offset: 2px; box-shadow: 0 0 0 3px rgba(0,113,227,0.2); }}
/* Skip to main content link (screen readers) */
.sb-skip-link {{ position: absolute; left: -999px; top: auto; width: 1px; height: 1px; overflow: hidden; z-index: 9999; }}
.sb-skip-link:focus {{ position: fixed; left: 1rem; top: 1rem; width: auto; height: auto; padding: 0.5rem 1rem; background: var(--sb-surface); color: var(--sb-text); border: 2px solid var(--sb-signal); border-radius: 0.25rem; font-size: 0.9rem; }}
/* Dashboard layout classes (replacing inline styles) */
.sb-status-bar {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; align-items: center; }}
.sb-stat-card {{ flex: 1; min-width: 150px; text-align: center; }}
.sb-stat-value {{ font-size: 1.8rem; font-weight: 700; }}
.sb-section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }}
.sb-section {{ margin-top: 1.5rem; }}
.sb-app-meta {{ display: flex; gap: 1.5rem; margin-top: 0.5rem; }}
.sb-main-content {{ max-width: 1100px; margin: 1.5rem auto; padding: 0 1.5rem; }}
.sb-page-title {{ font-size: 1.4rem; margin-bottom: 1rem; }}
.sb-nav-link {{ color: var(--sb-text-muted); font-size: 0.85rem; text-decoration: none; }}
.sb-nav-link:hover {{ color: var(--sb-text); }}
.sb-domain-desc {{ margin-bottom: 1rem; }}
.sb-domain-link {{ text-decoration: none; display: block; }}
/* Form inputs */
.sb-input {{ padding: 0.5rem; width: 100%; border: 1px solid var(--sb-border); border-radius: var(--sb-radius); background: var(--sb-bg); color: var(--sb-text); font-size: 0.9rem; font-family: inherit; }}
.sb-input:focus {{ border-color: var(--sb-accent); outline: none; box-shadow: 0 0 0 2px rgba(0,113,227,0.15); }}
textarea.sb-input {{ resize: vertical; min-height: 100px; }}
select.sb-input {{ cursor: pointer; }}
/* Icon fallback (replaces inline onerror) */
.sb-app-icon[src=""] {{ display: none; }}
</style>
</head>
<body>
<a href="#main-content" class="sb-skip-link">Skip to main content</a>
<header class="sb-topbar">
  <nav aria-label="Main navigation">
  <div class="sb-topbar-brand">
    <img src="/icons/yinyang-logo.png" alt="Solace Hub logo" loading="lazy">
    <span>Solace Hub</span>
  </div>
  <div class="sb-topbar-spacer"></div>
  <a href="/dashboard" class="sb-nav-link">Dashboard</a>
  <a href="/hire" class="sb-nav-link">Hire AI</a>
  <a href="/domains" class="sb-nav-link">Domains</a>
  <a href="/appstore" class="sb-nav-link">App Store</a>
  <a href="/llms" class="sb-nav-link">LLMs</a>
  <a href="/evidence" class="sb-nav-link">Evidence</a>
  <a href="/budget" class="sb-nav-link">Budget</a>
  <a href="/recipes" class="sb-nav-link">Recipes</a>
  <a href="/oauth3" class="sb-nav-link">OAuth3</a>
  <a href="/esign" class="sb-nav-link">E-Sign</a>
  <a href="/settings" class="sb-nav-link">Settings</a>
  <span class="sb-topbar-stat">v{version}</span>
  </nav>
</header>
<main id="main-content" class="sb-main-content" role="main">
<h1 class="sb-heading sb-page-title">{title}</h1>
{body_content}
</main>
<script src="/vendor/jquery-3.7.1.min.js"></script>
<script src="/vendor/jquery.dataTables.min.js"></script>
<script>
if (typeof jQuery !== 'undefined' && jQuery.fn.DataTable) {{
  jQuery.fn.dataTable.ext.errMode = 'none';
  jQuery('.sb-table').each(function() {{
    try {{
      if (!jQuery.fn.DataTable.isDataTable(this)) {{
        jQuery(this).DataTable({{ paging: true, searching: true, ordering: true, pageLength: 25, dom: 'ftip' }});
      }}
    }} catch(e) {{}}
  }});
}}
</script>
</body>
</html>"##,
        title = html_escape::encode_text(title),
        body_content = body_content,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn page_escapes_html() {
        let html = page("<script>", "x&y");
        assert!(html.contains("&lt;script&gt;"));
        assert!(html.contains("x&amp;y"));
    }

    #[test]
    fn hub_page_contains_nav() {
        let html = hub_page("Test Title", "<p>content</p>");
        assert!(html.contains("Solace Hub"));
        assert!(html.contains("/domains"));
        assert!(html.contains("/evidence"));
        assert!(html.contains("Test Title"));
        assert!(html.contains("<p>content</p>"));
    }

    #[test]
    fn event_css_class_returns_correct_class() {
        use crate::event_log::EventType;
        assert_eq!(event_css_class(&EventType::Navigate), "event-normal");
        assert_eq!(event_css_class(&EventType::Click), "event-normal");
        assert_eq!(event_css_class(&EventType::Fill), "event-normal");
        assert_eq!(event_css_class(&EventType::Fetch), "event-normal");
        assert_eq!(event_css_class(&EventType::Render), "event-normal");
        assert_eq!(event_css_class(&EventType::Preview), "event-preview");
        assert_eq!(event_css_class(&EventType::SignOff), "event-signoff");
        assert_eq!(event_css_class(&EventType::Seal), "event-seal");
    }

    #[test]
    fn hub_page_has_event_type_css() {
        let html = hub_page("Events", "");
        // Event styles are now inline (styleguide.css handles base tokens)
        assert!(html.contains(".event-normal"));
        assert!(html.contains(".event-preview"));
        assert!(html.contains(".event-signoff"));
        assert!(html.contains("--sb-success"));
        assert!(html.contains("--sb-warning"));
        assert!(html.contains("--sb-danger"));
    }
}
