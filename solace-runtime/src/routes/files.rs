// Diagram: hub-ux-architecture
use std::collections::BTreeMap;
use std::fs;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::{Html, Redirect};
use axum::routing::get;
use axum::Router;

use crate::state::AppState;

/// Find Hub assets directory — checks multiple paths for cross-platform production.
fn hub_assets_dir(subdir: &str) -> std::path::PathBuf {
    // 1. Next to the binary (MSI/deb install — production)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(bin_dir) = exe.parent() {
            let adjacent = bin_dir.join(subdir);
            if adjacent.is_dir() {
                return adjacent;
            }
            // Also check src/ subdir (Hub assets layout)
            let src_sub = bin_dir.join("src").join(subdir);
            if src_sub.is_dir() {
                return src_sub;
            }
        }
    }
    // 2. Dev path (only exists on dev machine)
    let dev = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap_or(std::path::Path::new("."))
        .join("solace-hub")
        .join("src")
        .join(subdir);
    if dev.is_dir() {
        return dev;
    }
    // 3. Installed path (~/.solace/hub/{subdir})
    let installed = crate::utils::solace_home().join("hub").join(subdir);
    if installed.is_dir() {
        return installed;
    }
    // Fallback (will 404 gracefully via ServeDir)
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
        .nest_service(
            "/icons",
            tower_http::services::ServeDir::new(hub_assets_dir("icons")),
        )
        .nest_service(
            "/media",
            tower_http::services::ServeDir::new(hub_assets_dir("media")),
        )
        .nest_service(
            "/vendor",
            tower_http::services::ServeDir::new(hub_assets_dir("vendor")),
        )
}

async fn index() -> Redirect {
    Redirect::permanent("/dashboard")
}

// ---------------------------------------------------------------------------
// GET /dashboard — local control plane dashboard
// ---------------------------------------------------------------------------
async fn dashboard_page(State(state): State<AppState>) -> Html<String> {
    let apps = crate::app_engine::scan_installed_apps();
    let sessions = state.sessions.read().clone();
    let events = state.runtime_events.read().clone();
    let uptime = state.uptime_seconds();
    let delight = state.delight.read().clone();
    let notifications = state.notifications.read().clone();
    let solace_home = crate::utils::solace_home();
    let part11 = crate::evidence::part11_status(&solace_home);

    let greeting = delight.warm_greeting();
    let celebration_banner = delight
        .celebration_message()
        .map(|message| {
            format!(
                r#"<div class="sb-card" style="margin-bottom:1rem"><span class="sb-pill sb-pill--success">{}</span></div>"#,
                html_escape::encode_text(&message)
            )
        })
        .unwrap_or_default();

    let mut app_cards = String::new();
    let mut total_runs = 0usize;
    for app in &apps {
        let app_dir = crate::utils::find_app_dir(&app.id);
        let run_count = app_dir.as_ref().map(|d| count_runs(d)).unwrap_or(0);
        total_runs += run_count;
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
        app_cards =
            r#"<div class="sb-empty"><div class="sb-empty-icon">&#x1F4E6;</div><p>No apps installed yet.</p></div>"#
                .to_string();
    }

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
        session_rows =
            "<tr><td colspan=\"5\" class=\"sb-text-muted\">No active browser sessions.</td></tr>"
                .to_string();
    }

    let mut event_rows = String::new();
    let recent_events: Vec<_> = events.iter().rev().take(25).collect();
    for evt in &recent_events {
        let ts = evt.get("timestamp").and_then(|v| v.as_str()).unwrap_or("—");
        let etype = evt.get("type").and_then(|v| v.as_str()).unwrap_or("event");
        let detail = evt
            .get("detail")
            .and_then(|v| v.as_str())
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
        event_rows =
            "<tr><td colspan=\"4\" class=\"sb-text-muted\">No events yet. Run an app to generate events.</td></tr>"
                .to_string();
    }

    let chain_badge = if part11.chain_valid {
        "<span class=\"sb-pill sb-pill--success\">Chain Valid</span>"
    } else if part11.record_count > 0 {
        "<span class=\"sb-pill sb-pill--danger\">Chain Broken</span>"
    } else {
        "<span class=\"sb-pill sb-pill--info\">No Records</span>"
    };

    let unread = notifications.iter().filter(|n| !n.read).count();
    let hours = uptime / 3600;
    let mins = (uptime % 3600) / 60;
    let uptime_str = if hours > 0 {
        format!("{}h {}m", hours, mins)
    } else {
        format!("{}m", mins)
    };

    let role_apps: Vec<_> = apps.iter().filter(|a| a.category == "role").collect();
    let backoffice_apps: Vec<_> = apps.iter().filter(|a| a.category == "backoffice").collect();
    let qa_apps: Vec<_> = apps.iter().filter(|a| a.category == "qa").collect();

    let mut domain_map: BTreeMap<String, Vec<&crate::app_engine::AppManifest>> = BTreeMap::new();
    for app in &apps {
        domain_map.entry(app.domain.clone()).or_default().push(app);
    }

    let role_cards = if role_apps.is_empty() {
        r#"<div class="sb-empty"><p>No AI workers installed yet. Hire one to start local orchestration.</p></div>"#
            .to_string()
    } else {
        role_apps
            .iter()
            .map(|app| {
                format!(
                    r#"<div class="sb-card" id="worker-{id}">
  <div class="sb-card-header">
    <h3 class="sb-card-title"><a href="/apps/{id}">{name}</a></h3>
    <span class="sb-pill sb-pill--info">{persona}</span>
  </div>
  <div class="sb-card-body">
    <p class="sb-text-sm">{desc}</p>
    <div class="sb-app-meta">
      <button class="sb-btn sb-btn--approve sb-btn--sm" onclick="runWorker('{id}', this)">Run</button>
      <a href="/apps/{id}" class="sb-btn sb-btn--sm" style="background:transparent;border:1px solid var(--sb-border);color:var(--sb-text-muted)">Manage</a>
    </div>
  </div>
</div>"#,
                    id = html_escape::encode_text(&app.id),
                    name = html_escape::encode_text(&app.name),
                    desc = html_escape::encode_text(&app.description),
                    persona = html_escape::encode_text(if app.persona.is_empty() {
                        "AI Worker"
                    } else {
                        &app.persona
                    }),
                )
            })
            .collect::<Vec<_>>()
            .join("\n")
    };

    let domain_cards = if domain_map.is_empty() {
        r#"<div class="sb-empty"><p>No domains discovered yet. Install an app or open the browser to seed domain surfaces.</p></div>"#
            .to_string()
    } else {
        domain_map
            .iter()
            .map(|(domain, domain_apps)| {
                let app_names: Vec<_> = domain_apps.iter().map(|app| app.name.as_str()).take(3).collect();
                let more = if domain_apps.len() > 3 {
                    format!(" +{} more", domain_apps.len() - 3)
                } else {
                    String::new()
                };
                format!(
                    r#"<a href="/domains/{domain}" class="sb-card sb-domain-link">
  <div class="sb-card-header">
    <h3 class="sb-card-title sb-app-name"><img class="sb-app-icon" src="{icon}" alt="{domain} icon" loading="lazy">{domain}</h3>
    <span class="sb-pill sb-pill--info">{count} apps</span>
  </div>
  <div class="sb-card-body">
    <p class="sb-text-sm">{preview}{more}</p>
    <p class="sb-text-xs sb-text-muted">Open domain workspace</p>
  </div>
</a>"#,
                    domain = html_escape::encode_text(domain),
                    icon = html_escape::encode_text(&domain_icon_path(domain)),
                    count = domain_apps.len(),
                    preview = html_escape::encode_text(&app_names.join(", ")),
                    more = html_escape::encode_text(&more),
                )
            })
            .collect::<Vec<_>>()
            .join("\n")
    };

    let backoffice_cards = if backoffice_apps.is_empty() {
        r#"<div class="sb-empty"><p>No backoffice workspaces detected yet.</p></div>"#.to_string()
    } else {
        backoffice_apps
            .iter()
            .map(|app| {
                format!(
                    r#"<a href="/backoffice/{id}" class="sb-card sb-domain-link">
  <div class="sb-card-header">
    <h3 class="sb-card-title">{name}</h3>
    <span class="sb-pill sb-pill--info">Workspace</span>
  </div>
  <div class="sb-card-body">
    <p class="sb-text-sm">{desc}</p>
    <p class="sb-text-xs sb-text-muted">Open {short_name}</p>
  </div>
</a>"#,
                    id = html_escape::encode_text(&app.id),
                    name = html_escape::encode_text(&app.name),
                    desc = html_escape::encode_text(&app.description),
                    short_name = html_escape::encode_text(
                        app.id.strip_prefix("backoffice-").unwrap_or(&app.id),
                    ),
                )
            })
            .collect::<Vec<_>>()
            .join("\n")
    };

    let mut body = String::new();
    body.push_str(&format!(
        r#"<div class="sb-status-bar">
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Dashboard</div>
    <div>
      <a href="/dashboard#overview" class="sb-btn sb-btn--sm sb-btn--primary">Local</a>
      <a href="https://solaceagi.com/dashboard" class="sb-btn sb-btn--sm">Cloud</a>
    </div>
    <div id="auth-status" class="sb-text-xs" style="color:var(--sb-text-muted);margin-top:0.2rem">Checking...</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">AI Engine</div>
    <div id="llm-status-pill"><span class="sb-pill sb-pill--warning">Scanning...</span></div>
    <div><a href="/llms" class="sb-text-xs" style="color:var(--sb-accent)">Configure</a></div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Browser</div>
    <div id="browser-status-pill"><span class="sb-pill sb-pill--info">Checking...</span></div>
    <div><button class="sb-btn sb-btn--sm" id="btn-launch" onclick="launchBrowser()">Launch</button></div>
  </div>
</div>

<div class="sb-status-bar">
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Workers</div>
    <div class="sb-stat-value">{role_count}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Apps</div>
    <div class="sb-stat-value">{app_count}</div>
    <div class="sb-text-xs" style="color:var(--sb-text-muted)">{domain_count} domains</div>
  </div>
  <div class="sb-card sb-stat-card" id="pending-stat">
    <div class="sb-kicker">Pending</div>
    <div class="sb-stat-value" id="pending-count">—</div>
    <div><a href="/signoff" class="sb-text-xs" style="color:var(--sb-accent)">Sign Off</a></div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Runs</div>
    <div class="sb-stat-value">{total_runs}</div>
    <div class="sb-text-xs" style="color:var(--sb-text-muted)">completed</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Trust</div>
    <div>{chain_badge}</div>
    <div class="sb-text-xs" style="color:var(--sb-text-muted)">{evidence_count} evidence</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Uptime</div>
    <div class="sb-stat-value">{uptime}</div>
    <div class="sb-text-xs" style="color:var(--sb-text-muted)">{unread} unread notifications</div>
  </div>
</div>

<div class="sb-tabs" role="tablist" id="dash-tabs">
  <button class="sb-tab sb-tab--active" data-tab="overview" role="tab" aria-selected="true">Overview</button>
  <button class="sb-tab" data-tab="workers" role="tab" aria-selected="false">Workers</button>
  <button class="sb-tab" data-tab="apps" role="tab" aria-selected="false">Apps</button>
  <button class="sb-tab" data-tab="backoffice" role="tab" aria-selected="false">Backoffice</button>
  <button class="sb-tab" data-tab="trust" role="tab" aria-selected="false">Trust</button>
  <button class="sb-tab" data-tab="platform" role="tab" aria-selected="false">Platform</button>
</div>"#,
        role_count = role_apps.len(),
        app_count = apps.len(),
        domain_count = domain_map.len(),
        total_runs = total_runs,
        chain_badge = chain_badge,
        evidence_count = part11.record_count,
        uptime = uptime_str,
        unread = unread,
    ));

    body.push_str(&format!(
        r#"<div id="tab-overview" class="dash-tab-panel">
  {celebration_banner}
  <div class="sb-section-header">
    <h2 class="sb-heading">Overview</h2>
    <a href="/dashboard#workers" class="sb-btn sb-btn--sm">Open Workers</a>
  </div>
  <p class="sb-text-muted">Local-first control plane for workers, approvals, backoffice work, and platform status.</p>

  <div class="sb-card-grid" style="margin-bottom:1rem">
    <a href="/dashboard#workers" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Workers</h3><span class="sb-pill sb-pill--info">{role_count}</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Hire, run, and manage AI employees.</p></div>
    </a>
    <a href="/dashboard#backoffice" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Backoffice</h3><span class="sb-pill sb-pill--info">{backoffice_count}</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">CRM, tasks, messages, docs, email, support, invoicing, and more.</p></div>
    </a>
    <a href="/signoff" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Approvals</h3><span class="sb-pill sb-pill--warning" id="overview-pending-pill">Checking</span></div>
      <div class="sb-card-body"><p class="sb-text-sm" id="pending-summary">Loading pending actions.</p></div>
    </a>
    <a href="/settings" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Platform</h3><span class="sb-pill sb-pill--info">Hub</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Tune LLMs, OAuth3, budgets, tunnel, and device settings.</p></div>
    </a>
  </div>

  <div class="sb-section-header">
    <h3 class="sb-heading">Browser Sessions</h3>
    <a href="/sidebar" class="sb-btn sb-btn--sm">Sidebar</a>
  </div>
  <table class="sb-table">
    <thead><tr><th>Session</th><th>Profile</th><th>URL</th><th>Process</th><th>Started</th></tr></thead>
    <tbody>{session_rows}</tbody>
  </table>

  <div class="sb-section-header" style="margin-top:1rem">
    <h3 class="sb-heading">Recent Events</h3>
    <a href="/evidence" class="sb-btn sb-btn--sm">Evidence</a>
  </div>
  <table class="sb-table">
    <thead><tr><th>Time</th><th>Level</th><th>Type</th><th>Detail</th></tr></thead>
    <tbody>{event_rows}</tbody>
  </table>
</div>"#,
        celebration_banner = celebration_banner,
        role_count = role_apps.len(),
        backoffice_count = backoffice_apps.len(),
        session_rows = session_rows,
        event_rows = event_rows,
    ));

    body.push_str(&format!(
        r#"<div id="tab-workers" class="dash-tab-panel" style="display:none">
  <div class="sb-section-header">
    <h2 class="sb-heading">AI Workers</h2>
    <a href="/hire" class="sb-btn sb-btn--sm">Hire New Worker</a>
  </div>
  <p class="sb-text-muted">Workers are role apps that operate locally, post evidence, and use approvals when trust gates require it.</p>
  <div class="sb-status-bar">
    <div class="sb-card sb-stat-card">
      <div class="sb-kicker">Installed</div>
      <div class="sb-stat-value">{role_count}</div>
    </div>
    <div class="sb-card sb-stat-card">
      <div class="sb-kicker">QA Apps</div>
      <div class="sb-stat-value">{qa_count}</div>
    </div>
    <div class="sb-card sb-stat-card">
      <div class="sb-kicker">Messages</div>
      <div class="sb-stat-value">{unread}</div>
      <div class="sb-text-xs" style="color:var(--sb-text-muted)">unread</div>
    </div>
  </div>
  <div class="sb-card-grid">{role_cards}</div>
</div>"#,
        role_count = role_apps.len(),
        qa_count = qa_apps.len(),
        unread = unread,
        role_cards = role_cards,
    ));

    body.push_str(&format!(
        r#"<div id="tab-apps" class="dash-tab-panel" style="display:none">
  <div class="sb-section-header">
    <h2 class="sb-heading">Apps</h2>
    <div>
      <a href="/domains" class="sb-btn sb-btn--sm">Domains</a>
      <a href="/appstore" class="sb-btn sb-btn--sm">App Store</a>
      <a href="/recipes" class="sb-btn sb-btn--sm">Recipes</a>
    </div>
  </div>
  <p class="sb-text-muted">Domain surfaces activate apps; installed apps define the local operating surface the browser can use.</p>
  <h3 class="sb-heading">Domains</h3>
  <div class="sb-card-grid">{domain_cards}</div>
  <h3 class="sb-heading" style="margin-top:1rem">Installed Apps</h3>
  <div class="sb-card-grid">{app_cards}</div>
</div>"#,
        domain_cards = domain_cards,
        app_cards = app_cards,
    ));

    body.push_str(&format!(
        r#"<div id="tab-backoffice" class="dash-tab-panel" style="display:none">
  <div class="sb-section-header">
    <h2 class="sb-heading">Backoffice</h2>
    <a href="/backoffice" class="sb-btn sb-btn--sm">Open Workspace</a>
  </div>
  <p class="sb-text-muted">Backoffice is one workspace family, not seven top-level tabs. Human and AI workspaces live here.</p>
  <div class="sb-card-grid">{backoffice_cards}</div>
</div>"#,
        backoffice_cards = backoffice_cards,
    ));

    body.push_str(&format!(
        r#"<div id="tab-trust" class="dash-tab-panel" style="display:none">
  <div class="sb-section-header">
    <h2 class="sb-heading">Trust</h2>
    <a href="/signoff" class="sb-btn sb-btn--sm">Open Sign Off</a>
  </div>
  <p class="sb-text-muted">Approvals, evidence, QA, and wiki snapshots are the trust surface for local execution.</p>

  <div class="sb-status-bar">
    <div class="sb-card sb-stat-card">
      <div class="sb-kicker">Review Queue</div>
      <div class="sb-stat-value" id="trust-review-count">—</div>
      <div class="sb-text-xs" style="color:var(--sb-text-muted)">needs review</div>
    </div>
    <div class="sb-card sb-stat-card">
      <div class="sb-kicker">Evidence Chain</div>
      <div>{chain_badge}</div>
      <div class="sb-text-xs" style="color:var(--sb-text-muted)">{evidence_count} records</div>
    </div>
    <div class="sb-card sb-stat-card">
      <div class="sb-kicker">QA Types</div>
      <div class="sb-stat-value" id="qa-type-count">{qa_count}</div>
      <div class="sb-text-xs" style="color:var(--sb-text-muted)">available</div>
    </div>
  </div>

  <div class="sb-card-grid" style="margin-bottom:1rem">
    <a href="/signoff" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Approvals</h3><span class="sb-pill sb-pill--warning">Human Gate</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Review, approve, reject, or do-now pending actions.</p></div>
    </a>
    <a href="/evidence" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Evidence</h3><span class="sb-pill sb-pill--success">Part 11</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Inspect the local evidence chain and audit trail.</p></div>
    </a>
    <a href="/wiki-hub" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Prime Wiki</h3><span class="sb-pill sb-pill--info">Knowledge</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Review living docs, snapshots, and local product memory.</p></div>
    </a>
    <a href="/esign" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">E-Sign</h3><span class="sb-pill sb-pill--info">Trust Tool</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Prepare regulated signatures and signed artifacts.</p></div>
    </a>
  </div>

  <div class="sb-section-header">
    <h3 class="sb-heading">QA</h3>
    <div id="trust-qa-summary" class="sb-text-xs" style="color:var(--sb-text-muted)">Loading QA types...</div>
  </div>
  <div id="trust-qa-grid" class="sb-card-grid"></div>
  <div id="qa-run-output" class="sb-card" style="display:none;margin-top:1rem"></div>
</div>"#,
        chain_badge = chain_badge,
        evidence_count = part11.record_count,
        qa_count = qa_apps.len(),
    ));

    body.push_str(
        r#"<div id="tab-platform" class="dash-tab-panel" style="display:none">
  <div class="sb-section-header">
    <h2 class="sb-heading">Platform</h2>
    <a href="/settings" class="sb-btn sb-btn--sm">Open Settings</a>
  </div>
  <p class="sb-text-muted">LLM sources, CLI wrappers, OAuth3, budget, cloud, and runtime configuration live here.</p>

  <div class="sb-card-grid">
    <a href="/llms" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">LLMs</h3><span class="sb-pill sb-pill--info">Model Gate</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Configure managed AI, BYOK, local CLIs, and local models.</p></div>
    </a>
    <a href="/oauth3" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">OAuth3</h3><span class="sb-pill sb-pill--info">Delegation</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Review account scopes and domain credential state.</p></div>
    </a>
    <a href="/budget" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Budget</h3><span class="sb-pill sb-pill--warning">Gate</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Tune budget policy, spend controls, and fail-closed limits.</p></div>
    </a>
    <a href="/settings" class="sb-card sb-domain-link">
      <div class="sb-card-header"><h3 class="sb-card-title">Settings</h3><span class="sb-pill sb-pill--info">Runtime</span></div>
      <div class="sb-card-body"><p class="sb-text-sm">Device, tunnel, runtime, and local bundle settings.</p></div>
    </a>
  </div>

  <div class="sb-section-header" style="margin-top:1rem">
    <h3 class="sb-heading">Detected CLI Wrappers</h3>
    <span id="platform-agent-summary" class="sb-text-xs" style="color:var(--sb-text-muted)">Scanning...</span>
  </div>
  <div id="platform-agent-list" class="sb-card-grid"></div>

  <div class="sb-section-header" style="margin-top:1rem">
    <h3 class="sb-heading">Cloud + Runtime</h3>
    <span id="platform-cloud-summary" class="sb-text-xs" style="color:var(--sb-text-muted)">Checking cloud state...</span>
  </div>
  <div class="sb-card-grid">
    <div class="sb-card">
      <div class="sb-card-header"><h3 class="sb-card-title">Cloud</h3><span class="sb-pill sb-pill--info" id="platform-cloud-pill">Checking</span></div>
      <div class="sb-card-body"><p class="sb-text-sm" id="platform-cloud-copy">Loading cloud status.</p></div>
    </div>
    <div class="sb-card">
      <div class="sb-card-header"><h3 class="sb-card-title">Sidebar Gate</h3><span class="sb-pill sb-pill--info" id="platform-sidebar-pill">Checking</span></div>
      <div class="sb-card-body"><p class="sb-text-sm" id="platform-sidebar-copy">Loading model source status.</p></div>
    </div>
  </div>
</div>"#,
    );

    body.push_str(
        r#"<script>
(function() {
  var VALID_TABS = ['overview', 'workers', 'apps', 'backoffice', 'trust', 'platform'];

  function ge(id) { return document.getElementById(id); }
  function esc(value) {
    var d = document.createElement('div');
    d.textContent = String(value == null ? '' : value);
    return d.innerHTML;
  }
  function fetchJson(url, options) {
    return fetch(url, options).then(function(response) {
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      return response.json();
    });
  }
  function normalizeTab(hash) {
    var tab = String(hash || '').replace(/^#/, '');
    return VALID_TABS.indexOf(tab) !== -1 ? tab : 'overview';
  }
  function activateTab(tab) {
    var active = normalizeTab(tab);
    document.querySelectorAll('#dash-tabs .sb-tab[data-tab]').forEach(function(btn) {
      var selected = btn.dataset.tab === active;
      btn.classList.toggle('sb-tab--active', selected);
      btn.setAttribute('aria-selected', selected ? 'true' : 'false');
    });
    document.querySelectorAll('.dash-tab-panel').forEach(function(panel) {
      panel.style.display = panel.id === 'tab-' + active ? 'block' : 'none';
    });
  }

  document.querySelectorAll('#dash-tabs .sb-tab[data-tab]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var target = btn.dataset.tab || 'overview';
      if (location.hash !== '#' + target) {
        location.hash = target;
      }
      activateTab(target);
    });
  });
  window.addEventListener('hashchange', function() {
    activateTab(location.hash);
  });
  activateTab(location.hash);

  function renderPendingSummary(summary) {
    var count = summary.needs_review || 0;
    var countEl = ge('pending-count');
    if (countEl) {
      countEl.textContent = count;
      countEl.style.color = count > 0 ? 'var(--sb-warning)' : 'var(--sb-success)';
    }
    var trustCount = ge('trust-review-count');
    if (trustCount) trustCount.textContent = count;
    var stat = ge('pending-stat');
    if (stat) stat.style.borderColor = count > 0 ? 'var(--sb-warning)' : 'var(--sb-border)';
    var overviewPill = ge('overview-pending-pill');
    if (overviewPill) {
      overviewPill.className = 'sb-pill ' + (count > 0 ? 'sb-pill--warning' : 'sb-pill--success');
      overviewPill.textContent = count > 0 ? count + ' pending' : 'All clear';
    }
    var summaryEl = ge('pending-summary');
    if (summaryEl) {
      summaryEl.textContent = count > 0
        ? count + ' actions need review before execution.'
        : 'No actions are waiting on human approval.';
    }
  }

  function renderAgentList(payload) {
    var agents = (payload && payload.agents) || [];
    var installed = agents.filter(function(agent) { return !!agent.installed; });
    var summary = ge('platform-agent-summary');
    if (summary) {
      summary.textContent = installed.length + ' detected of ' + agents.length + ' known wrappers';
    }
    var container = ge('platform-agent-list');
    if (!container) return;
    if (!agents.length) {
      container.innerHTML = '<div class="sb-empty"><p>No CLI wrappers reported.</p></div>';
      return;
    }
    container.innerHTML = agents.map(function(agent) {
      var cls = agent.installed ? 'success' : 'info';
      var label = agent.installed ? 'Detected' : 'Not found';
      var version = agent.version ? '<p class="sb-text-xs sb-text-muted">Version: ' + esc(agent.version) + '</p>' : '';
      return '<div class="sb-card"><div class="sb-card-header"><h3 class="sb-card-title">' + esc(agent.name || agent.id) + '</h3><span class="sb-pill sb-pill--' + cls + '">' + label + '</span></div><div class="sb-card-body"><p class="sb-text-sm">' + esc(agent.description || 'Local CLI wrapper') + '</p>' + version + '</div></div>';
    }).join('');
  }

  function renderQaTypes(payload) {
    var qaTypes = (payload && payload.qa_types) || [];
    var summary = ge('trust-qa-summary');
    if (summary) {
      summary.textContent = qaTypes.length + ' QA app types available for local validation.';
    }
    var typeCount = ge('qa-type-count');
    if (typeCount) typeCount.textContent = qaTypes.length;
    var container = ge('trust-qa-grid');
    if (!container) return;
    if (!qaTypes.length) {
      container.innerHTML = '<div class="sb-empty"><p>No QA types available.</p></div>';
      return;
    }
    container.innerHTML = qaTypes.map(function(qa) {
      return '<div class="sb-card"><div class="sb-card-header"><h3 class="sb-card-title">' + esc(qa.name || qa.id) + '</h3><span class="sb-pill sb-pill--info">' + esc(qa.tier || 'local') + '</span></div><div class="sb-card-body"><p class="sb-text-sm">' + esc(qa.description || '') + '</p><div class="sb-app-meta"><button class="sb-btn sb-btn--sm sb-btn--approve" onclick="runQaType(\'' + esc(qa.id) + '\', this)">Run QA</button></div></div></div>';
    }).join('');
  }

  function scanStatus() {
    fetchJson('/api/v1/sidebar/state').then(function(sidebar) {
      var llmPill = ge('llm-status-pill');
      var sidebarPill = ge('platform-sidebar-pill');
      var sidebarCopy = ge('platform-sidebar-copy');
      if (sidebar.gate === 'paid') {
        if (llmPill) llmPill.innerHTML = '<span class="sb-pill sb-pill--success">Managed LLM</span>';
      } else if (sidebar.gate === 'byok') {
        if (llmPill) llmPill.innerHTML = '<span class="sb-pill sb-pill--success">BYOK Active</span>';
      } else {
        fetchJson('/api/v1/agents').then(function(agentsPayload) {
          var installed = ((agentsPayload && agentsPayload.agents) || []).filter(function(agent) { return !!agent.installed; }).length;
          if (llmPill) {
            llmPill.innerHTML = installed > 0
              ? '<span class="sb-pill sb-pill--info">' + installed + ' CLIs</span>'
              : '<span class="sb-pill sb-pill--warning">Not configured</span>';
          }
        }).catch(function() {
          if (llmPill) llmPill.innerHTML = '<span class="sb-pill sb-pill--danger">Offline</span>';
        });
      }
      if (sidebarPill) sidebarPill.textContent = String(sidebar.gate || 'unknown').toUpperCase();
      if (sidebarCopy) {
        sidebarCopy.textContent = sidebar.apps_enabled
          ? 'Apps are enabled for the current device.'
          : 'Apps are still gated; sign in or configure a source to unlock them.';
      }
    }).catch(function() {
      var llmPill = ge('llm-status-pill');
      if (llmPill) llmPill.innerHTML = '<span class="sb-pill sb-pill--danger">Offline</span>';
    });

    fetchJson('/api/v1/browser/sessions').then(function(payload) {
      var sessions = Array.isArray(payload) ? payload : (payload.sessions || []);
      var pill = ge('browser-status-pill');
      var btn = ge('btn-launch');
      if (pill) {
        pill.innerHTML = sessions.length > 0
          ? '<span class="sb-pill sb-pill--success">Running</span>'
          : '<span class="sb-pill sb-pill--info">Stopped</span>';
      }
      if (btn) btn.textContent = sessions.length > 0 ? 'Open' : 'Launch';
    }).catch(function() {});

    fetchJson('/api/v1/cloud/status').then(function(cloud) {
      var auth = ge('auth-status');
      var cloudPill = ge('platform-cloud-pill');
      var cloudCopy = ge('platform-cloud-copy');
      var cloudSummary = ge('platform-cloud-summary');
      if (cloud.connected && cloud.config) {
        if (auth) auth.innerHTML = '<span style="color:var(--sb-success)">● ' + esc(cloud.config.user_email || 'Connected') + '</span>';
        if (cloudPill) cloudPill.className = 'sb-pill sb-pill--success';
        if (cloudPill) cloudPill.textContent = 'Connected';
        if (cloudCopy) cloudCopy.textContent = 'Authenticated as ' + (cloud.config.user_email || 'Connected device') + '.';
        if (cloudSummary) cloudSummary.textContent = 'Cloud sync path is configured for this device.';
      } else {
        if (auth) auth.innerHTML = 'Not signed in · <a href="https://solaceagi.com/auth/login" style="color:var(--sb-accent)">Sign in</a>';
        if (cloudPill) cloudPill.className = 'sb-pill sb-pill--warning';
        if (cloudPill) cloudPill.textContent = 'Local only';
        if (cloudCopy) cloudCopy.textContent = 'Cloud account not connected; local runtime still works.';
        if (cloudSummary) cloudSummary.textContent = 'Running local-first without a cloud session.';
      }
    }).catch(function() {});
  }

  window.launchBrowser = function() {
    var btn = ge('btn-launch');
    if (btn) {
      btn.textContent = '...';
      btn.disabled = true;
    }
    fetchJson('/api/v1/browser/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}'
    }).then(function(payload) {
      if (payload.session) {
        var pill = ge('browser-status-pill');
        if (pill) pill.innerHTML = '<span class="sb-pill sb-pill--success">Running</span>';
        if (btn) btn.textContent = 'Open';
      } else if (btn) {
        btn.textContent = 'Launch';
      }
    }).catch(function() {
      if (btn) btn.textContent = 'Launch';
    }).finally(function() {
      if (btn) btn.disabled = false;
    });
  };

  window.runWorker = function(appId, btn) {
    if (!btn) return;
    btn.textContent = 'Running...';
    btn.disabled = true;
    fetchJson('/api/v1/apps/run/' + appId, { method: 'POST' }).then(function(payload) {
      btn.textContent = 'Done ✓';
      btn.style.background = 'var(--sb-success, #22c55e)';
      btn.style.color = 'var(--sb-bg, #0f172a)';
      fetch('/api/v1/backoffice/backoffice-messages/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel_id: 'general',
          sender: appId,
          sender_type: 'agent',
          content: 'Run complete. ' + (payload.report ? 'Report: ' + payload.report.split('/').pop() : 'Done.'),
          message_type: 'result',
          priority: 'normal'
        })
      }).catch(function() {});
    }).catch(function() {
      btn.textContent = 'Error';
      btn.style.background = 'var(--sb-danger, #ef4444)';
    }).finally(function() {
      setTimeout(function() {
        btn.textContent = 'Run';
        btn.disabled = false;
        btn.style.background = '';
        btn.style.color = '';
      }, 2500);
    });
  };

  window.runQaType = function(qaType, btn) {
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Running...';
    }
    fetchJson('/api/v1/qa/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ qa_type: qaType, target: 'http://localhost:8888' })
    }).then(function(result) {
      var output = ge('qa-run-output');
      if (output) {
        output.style.display = 'block';
        output.innerHTML = '<div class="sb-card-header"><h3 class="sb-card-title">' + esc(result.qa_type) + ' QA</h3><span class="sb-pill ' + (result.passed ? 'sb-pill--success' : 'sb-pill--warning') + '">' + (result.passed ? 'PASS' : 'CHECK') + '</span></div><div class="sb-card-body"><p class="sb-text-sm">Target: ' + esc(result.target || 'http://localhost:8888') + '</p><p class="sb-text-sm">' + esc(String(result.passed_checks || 0)) + ' of ' + esc(String(result.total_checks || 0)) + ' checks passed.</p></div>';
      }
    }).catch(function(error) {
      var output = ge('qa-run-output');
      if (output) {
        output.style.display = 'block';
        output.innerHTML = '<div class="sb-card-body"><p class="sb-text-sm">QA run failed: ' + esc(error.message || 'unknown error') + '</p></div>';
      }
    }).finally(function() {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Run QA';
      }
    });
  };

  fetchJson('/api/v1/actions/summary').then(renderPendingSummary).catch(function() {});
  fetchJson('/api/v1/agents').then(renderAgentList).catch(function() {});
  fetchJson('/api/v1/qa/types').then(renderQaTypes).catch(function() {});
  scanStatus();
  setInterval(scanStatus, 30000);
})();
</script>"#,
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

async fn sidebar_page() -> (axum::http::HeaderMap, Html<String>) {
    let mut headers = axum::http::HeaderMap::new();
    headers.insert(
        "cache-control",
        "no-cache, no-store, must-revalidate".parse().unwrap(),
    );
    if let Some(content) = sidebar_asset("sidepanel.html") {
        return (headers, Html(content));
    }
    (
        headers,
        Html(
            page(
                "Sidebar",
                "Yinyang sidebar — sidepanel.html not found. Build Solace Browser first.",
            )
            .to_string(),
        ),
    )
}

async fn sidebar_js() -> (axum::http::HeaderMap, String) {
    let mut headers = axum::http::HeaderMap::new();
    headers.insert("content-type", "application/javascript".parse().unwrap());
    headers.insert(
        "cache-control",
        "no-cache, no-store, must-revalidate".parse().unwrap(),
    );
    let content =
        sidebar_asset("sidepanel.js").unwrap_or_else(|| "// sidepanel.js not found".to_string());
    (headers, content)
}

async fn sidebar_css() -> (axum::http::HeaderMap, String) {
    let mut headers = axum::http::HeaderMap::new();
    headers.insert("content-type", "text/css".parse().unwrap());
    headers.insert(
        "cache-control",
        "no-cache, no-store, must-revalidate".parse().unwrap(),
    );
    let content = sidebar_asset("sidepanel.css")
        .unwrap_or_else(|| "/* sidepanel.css not found */".to_string());
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
        let app_names: Vec<_> = domain_apps
            .iter()
            .map(|a| a.name.as_str())
            .take(3)
            .collect();
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
    let _stillwater_section = if wiki_dir.join(format!("{domain}.json")).is_file() {
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
        let run_count = app_dir.as_ref().map(|d| count_runs(d)).unwrap_or(0);
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
                "<span class=\"sb-pill sb-pill--success\">Idle</span> — tab available for next app"
                    .to_string()
            } else {
                format!("<span class=\"sb-pill sb-pill--warning\">Working</span> — active app: <strong>{}</strong>",
                    html_escape::encode_text(tab.active_app_id.as_deref().unwrap_or("unknown")))
            }
        } else {
            "<span class=\"sb-pill sb-pill--success\">Idle</span> — no tab registered yet"
                .to_string()
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

    // Build trigger info for domain apps
    let mut trigger_rows = String::new();
    for app in &apps {
        for trigger in &app.triggers {
            trigger_rows.push_str(&format!(
                "<tr><td><strong>{name}</strong></td><td><code>{path}</code></td><td>{ctx}</td><td><span class=\"sb-pill sb-pill--{acls}\">{act}</span></td><td><code class=\"sb-text-xs\">{sel}</code></td></tr>",
                name = html_escape::encode_text(&app.name),
                path = html_escape::encode_text(&trigger.path),
                ctx = html_escape::encode_text(&trigger.context),
                act = html_escape::encode_text(&trigger.activation),
                acls = if trigger.activation == "auto" { "success" } else { "info" },
                sel = html_escape::encode_text(&trigger.dom_selector),
            ));
        }
    }

    // OAuth3 status
    let solace_home = crate::utils::solace_home();
    let vault_path = solace_home.join("vault").join("oauth3.json");
    let oauth3_html = if vault_path.exists() {
        if let Ok(content) = fs::read_to_string(&vault_path) {
            if content.contains(&domain) {
                "<span class=\"sb-pill sb-pill--success\">OAuth3 Active</span>".to_string()
            } else {
                format!("<span class=\"sb-pill sb-pill--warning\">Not logged in</span> <a href=\"https://{domain}/login\" class=\"sb-btn sb-btn--sm\">Setup OAuth3</a>")
            }
        } else {
            format!("<span class=\"sb-pill sb-pill--warning\">Not configured</span> <a href=\"https://{domain}/login\" class=\"sb-btn sb-btn--sm\">Setup OAuth3</a>")
        }
    } else {
        format!("<span class=\"sb-pill sb-pill--warning\">Not configured</span> <a href=\"https://{domain}/login\" class=\"sb-btn sb-btn--sm\">Setup OAuth3</a>")
    };

    // Wiki snapshot count
    let wiki_dir = solace_home.join("wiki").join("domains").join(&domain);
    let snapshot_count = if wiki_dir.exists() {
        std::fs::read_dir(&wiki_dir)
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.file_name()
                    .to_string_lossy()
                    .ends_with(".prime-snapshot.md")
            })
            .count()
    } else {
        0
    };

    let body = format!(
        r#"<p><a href="/domains">&larr; All Domains</a> | <a href="/dashboard">Dashboard</a></p>
<div class="sb-status-bar">
  <div class="sb-card sb-stat-card">
    <img src="{icon}" alt="" style="width:48px;height:48px;border-radius:12px">
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Apps</div>
    <div class="sb-stat-value">{app_count}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">OAuth3</div>
    <div>{oauth3_html}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Wiki</div>
    <div class="sb-stat-value">{snapshot_count}</div>
    <div class="sb-text-xs sb-text-muted">snapshots</div>
  </div>
</div>

<!-- Domain Apps with Triggers -->
<section>
  <h2 class="sb-heading">Domain Apps</h2>
  <div class="sb-card-grid">{app_cards_html}</div>
</section>

<!-- Trigger Rules Table -->
<section class="sb-section">
  <h2 class="sb-heading">Activation Triggers</h2>
  <table class="sb-table"><thead><tr><th>App</th><th>Path</th><th>Context</th><th>Activation</th><th>DOM Selector</th></tr></thead>
  <tbody>{trigger_rows}</tbody></table>
  {no_triggers}
</section>

<!-- Recent Runs -->
<section class="sb-section">
  <h2 class="sb-heading">Recent Runs</h2>
  <table class="sb-table"><thead><tr><th>Run</th><th>App</th><th>Time</th></tr></thead>
  <tbody>{run_rows}</tbody></table>
</section>

<!-- Domain Config -->
<section class="sb-section">
  <h2 class="sb-heading">Configuration</h2>
  <div class="sb-card">{config_section}</div>
  <div class="sb-card sb-mt-md"><p>{tab_status}</p></div>
</section>"#,
        icon = html_escape::encode_text(&icon),
        app_count = apps.len(),
        oauth3_html = oauth3_html,
        snapshot_count = snapshot_count,
        app_cards_html = apps.iter().map(|a| {{
            let actions_html = a.actions.iter().map(|act|
                format!("<button class=\"sb-btn sb-btn--sm\">{}</button>", html_escape::encode_text(&act.label))
            ).collect::<Vec<_>>().join(" ");
            let triggers_html = if a.triggers.is_empty() { String::new() } else {
                format!("<p class=\"sb-text-xs sb-text-muted\">{} triggers: {}</p>",
                    a.triggers.len(),
                    a.triggers.iter().map(|t| html_escape::encode_text(&t.context).to_string()).collect::<Vec<_>>().join(", "))
            };
            format!(
                r#"<div class="sb-card"><h3><a href="/apps/{id}">{name}</a></h3>
                <p class="sb-text-sm">{desc}</p>
                {triggers_html}
                <div class="sb-app-meta">{actions_html} <a href="/apps/{id}" class="sb-btn sb-btn--sm">Run</a></div></div>"#,
                id = html_escape::encode_text(&a.id),
                name = html_escape::encode_text(&a.name),
                desc = html_escape::encode_text(&a.description),
                triggers_html = triggers_html,
                actions_html = actions_html,
            )
        }}).collect::<Vec<_>>().join("\n"),
        no_triggers = if trigger_rows.is_empty() { "<p class=\"sb-text-muted\">No trigger rules defined for apps in this domain.</p>" } else { "" },
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

    let _manifest_section = format!(
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
    let runs = app_dir.as_ref().map(|d| list_runs(d)).unwrap_or_default();

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

    let run_count = runs.len();
    let persona_display = if app.persona.is_empty() {
        "AI Worker"
    } else {
        &app.persona
    };
    let category_display = if app.category.is_empty() {
        "standard"
    } else {
        &app.category
    };
    let tags_html = app
        .tags
        .iter()
        .map(|t| {
            format!(
                "<span class=\"sb-pill sb-pill--info sb-text-2xs\">{}</span>",
                html_escape::encode_text(t)
            )
        })
        .collect::<Vec<_>>()
        .join(" ");

    let body = format!(
        r#"<p><a href="/dashboard">&larr; Dashboard</a> | <a href="/domains/{domain}">{domain}</a></p>

<!-- Worker Profile Header -->
<div class="sb-status-bar">
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Worker</div>
    <div class="sb-stat-value" style="font-size:1.2rem">{name}</div>
    <div><span class="sb-pill sb-pill--info">{persona}</span> <span class="sb-pill sb-pill--success">{category}</span></div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Runs</div>
    <div class="sb-stat-value">{run_count}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Evidence</div>
    <div class="sb-stat-value">{evidence_count}</div>
  </div>
  <div class="sb-card sb-stat-card">
    <div class="sb-kicker">Schedule</div>
    <div><code>{schedule}</code></div>
  </div>
  <div class="sb-card sb-stat-card">
    <a href="/api/v1/apps/run/{id}" class="sb-btn sb-btn--sm">Run Now</a>
    <a href="/esign" class="sb-btn sb-btn--sm" style="margin-top:0.3rem">Sign Off</a>
  </div>
</div>

<!-- Tags -->
<div style="margin-bottom:1rem">{tags_html}</div>

<!-- Worker Description -->
<div class="sb-card" style="margin-bottom:1rem">
  <p>{desc}</p>
</div>

<!-- Activity History -->
<section>
  <h2 class="sb-heading">Run History</h2>
  <table class="sb-table" id="runs-table"><thead><tr><th>Run ID</th><th>Time</th></tr></thead><tbody>{run_rows}</tbody></table>
</section>

<!-- Evidence Trail -->
<section class="sb-section">
  <div class="sb-section-header">
    <h2 class="sb-heading">Evidence Trail (Part 11)</h2>
    <a href="/evidence" class="sb-btn sb-btn--sm">Full Chain</a>
  </div>
  <table class="sb-table" id="evidence-table"><thead><tr><th>Timestamp</th><th>Event</th><th>SHA-256</th></tr></thead><tbody>{evidence_rows}</tbody></table>
</section>

<!-- Worker Config -->
<section class="sb-section">
  <h2 class="sb-heading">Configuration</h2>
  <div class="sb-card">
    <table class="sb-table">
      <tr><td><strong>ID</strong></td><td><code>{id}</code></td></tr>
      <tr><td><strong>Domain</strong></td><td><a href="/domains/{domain}">{domain}</a></td></tr>
      <tr><td><strong>Version</strong></td><td>{version}</td></tr>
      <tr><td><strong>Tier</strong></td><td>{tier}</td></tr>
      <tr><td><strong>Persona</strong></td><td>{persona}</td></tr>
      <tr><td><strong>Category</strong></td><td>{category}</td></tr>
    </table>
  </div>
</section>

<script>
if (typeof jQuery !== 'undefined' && jQuery.fn.DataTable) {{
  jQuery.fn.dataTable.ext.errMode = 'none';
  try {{ jQuery('#runs-table').DataTable({{paging:true,ordering:true,pageLength:10,dom:'ftip'}}); }} catch(e) {{}}
  try {{ jQuery('#evidence-table').DataTable({{paging:true,ordering:true,pageLength:10,dom:'ftip'}}); }} catch(e) {{}}
}}
</script>"#,
        domain = html_escape::encode_text(&app.domain),
        id = html_escape::encode_text(&app.id),
        name = html_escape::encode_text(&app.name),
        desc = html_escape::encode_text(&app.description),
        version = html_escape::encode_text(&app.version),
        persona = html_escape::encode_text(persona_display),
        category = html_escape::encode_text(category_display),
        schedule = schedule_display,
        tier = tier_display,
        run_count = run_count,
        evidence_count = app_evidence.len(),
        tags_html = tags_html,
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
                    let type_str = serde_json::to_string(&event.event_type).unwrap_or_default();
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
                .map(|v| {
                    v.get("agents")
                        .cloned()
                        .unwrap_or(serde_json::Value::Array(vec![]))
                })
                .and_then(|v| serde_json::from_value(v))
        })
        .unwrap_or_default();

    let mut agent_rows = String::new();
    for agent in &agents {
        let name = agent
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        let path = agent.get("path").and_then(|v| v.as_str()).unwrap_or("—");
        let status = agent
            .get("available")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
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

    let daily_bar_class = if daily_pct > 80.0 {
        "sb-progress-bar--danger"
    } else if daily_pct > 50.0 {
        "sb-progress-bar--warning"
    } else {
        "sb-progress-bar--success"
    };
    let monthly_bar_class = if monthly_pct > 80.0 {
        "sb-progress-bar--danger"
    } else if monthly_pct > 50.0 {
        "sb-progress-bar--warning"
    } else {
        "sb-progress-bar--success"
    };

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
        let name = recipe
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("Unnamed");
        let domain = recipe.get("domain").and_then(|v| v.as_str()).unwrap_or("—");
        let hit_rate = recipe
            .get("hit_rate")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0);
        let hit_pill = if hit_rate >= 0.7 {
            format!(
                "<span class=\"sb-pill sb-pill--success\">{:.0}% hit</span>",
                hit_rate * 100.0
            )
        } else if hit_rate >= 0.4 {
            format!(
                "<span class=\"sb-pill sb-pill--warning\">{:.0}% hit</span>",
                hit_rate * 100.0
            )
        } else {
            format!(
                "<span class=\"sb-pill sb-pill--danger\">{:.0}% hit</span>",
                hit_rate * 100.0
            )
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
        let expires = token
            .get("expires_at")
            .and_then(|v| v.as_str())
            .unwrap_or("—");
        let status = token
            .get("revoked")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
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
    let pending: Vec<_> = notifications
        .iter()
        .filter(|n| n.level == "signoff" || n.level == "L3" || n.level == "L4" || n.level == "L5")
        .collect();

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
    let stats: serde_json::Value =
        serde_json::from_str(&wiki_json).unwrap_or(serde_json::json!({}));
    let snapshot_count = stats
        .get("snapshot_count")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let domain_count = stats
        .get("domain_count")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

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
        dark_active = if theme == "dark" {
            "sb-theme-btn--active"
        } else {
            ""
        },
        light_active = if theme == "light" {
            "sb-theme-btn--active"
        } else {
            ""
        },
        platform = std::env::consts::OS,
        hours = uptime / 3600,
        mins = (uptime % 3600) / 60,
    );
    Html(hub_page("Settings", &body))
}

// ---------------------------------------------------------------------------
// GET /hire — "Hire an AI Worker" job description wizard
// ---------------------------------------------------------------------------
async fn hire_page(State(_state): State<AppState>) -> Html<String> {
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
            sched = if app.schedule.is_empty() {
                "Manual"
            } else {
                &app.schedule
            },
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
pub fn domain_icon_filename(domain: &str) -> String {
    let path = domain_icon_path(domain);
    // Strip any leading path — return just the filename
    path.rsplit('/')
        .next()
        .unwrap_or("yinyang-logo.png")
        .to_string()
}

pub fn domain_icon_path_pub(domain: &str) -> String {
    domain_icon_path(domain)
}

fn domain_icon_path(domain: &str) -> String {
    // Map domain → icon filename (order: exact match, root domain, keyword)
    let mappings: &[(&str, &str)] = &[
        ("localhost", "/media/yinyang-rotating_70pct_128px.gif"),
        ("google.com", "google-search.png"),
        ("gemini.google.com", "gemini.png"),
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
        ("whatsapp.com", "whats-app.jpg"),
        ("phuc.net", "/icons/yinyang-logo.png"),
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
            let ts =
                crate::utils::modified_iso8601(&entry.path()).unwrap_or_else(|| "—".to_string());
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
    dirs.last().and_then(|p| crate::utils::modified_iso8601(p))
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
async fn styleguide_css() -> (
    StatusCode,
    [(axum::http::header::HeaderName, &'static str); 1],
    String,
) {
    let path = hub_assets_dir(".").join("styleguide.css");
    if let Ok(content) = fs::read_to_string(&path) {
        return (
            StatusCode::OK,
            [(axum::http::header::CONTENT_TYPE, "text/css")],
            content,
        );
    }
    let alt = hub_assets_dir("..").join("styleguide.css");
    if let Ok(content) = fs::read_to_string(&alt) {
        return (
            StatusCode::OK,
            [(axum::http::header::CONTENT_TYPE, "text/css")],
            content,
        );
    }
    (
        StatusCode::NOT_FOUND,
        [(axum::http::header::CONTENT_TYPE, "text/css")],
        String::new(),
    )
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

pub fn hub_page_pub(title: &str, body_content: &str) -> String {
    hub_page(title, body_content)
}

fn hub_page(title: &str, body_content: &str) -> String {
    let version = SOLACE_VERSION.trim();
    format!(
        r##"<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Solace Dashboard</title>
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
.sb-main-content {{ max-width: 1400px; margin: 1.5rem auto; padding: 0 1.5rem; }}
/* Dashboard tabs: single row, scrollable */
.sb-tabs {{ display: flex; gap: 0.25rem; overflow-x: auto; white-space: nowrap; padding-bottom: 0.25rem; }}
.sb-tab {{ flex-shrink: 0; font-size: 0.85rem; padding: 0.4rem 0.8rem; }}
/* Backoffice custom components */
.bo-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }}
.bo-stat-card {{ background: var(--sb-surface, #1e293b); border: 1px solid var(--sb-border, #334155); border-radius: 8px; padding: 0.75rem; text-align: center; }}
.bo-stat-value {{ font-size: 1.5rem; font-weight: 700; }}
.bo-stat-label {{ font-size: 0.75rem; color: var(--sb-text-muted, #94a3b8); margin-top: 0.25rem; }}
.bo-kanban {{ display: flex; gap: 0.75rem; overflow-x: auto; padding: 0.5rem 0; }}
.bo-kanban-column {{ min-width: 180px; flex-shrink: 0; background: var(--sb-surface, #1e293b); border-radius: 8px; padding: 0.75rem; }}
.bo-kanban-column-header {{ font-weight: 600; font-size: 0.8rem; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; }}
.bo-kanban-card {{ background: var(--sb-bg, #0f172a); border: 1px solid var(--sb-border, #334155); border-radius: 6px; padding: 0.5rem; margin-bottom: 0.4rem; font-size: 0.8rem; }}
.bo-message {{ display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }}
.bo-message-avatar {{ width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.65rem; color: white; flex-shrink: 0; }}
.bo-message--agent .bo-message-avatar {{ background: #a855f7; }}
.bo-message--human .bo-message-avatar {{ background: #22c55e; }}
.bo-message-sender {{ font-weight: 600; font-size: 0.8rem; }}
.bo-message-text {{ font-size: 0.8rem; margin-top: 0.15rem; }}
.bo-message-time {{ font-size: 0.65rem; color: var(--sb-text-muted, #94a3b8); }}
.bo-chart {{ height: 200px; background: var(--sb-surface, #1e293b); border-radius: 8px; border: 1px solid var(--sb-border, #334155); }}
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
    <img src="/icons/yinyang-logo.png" alt="Solace logo" loading="lazy">
    <span>Solace Dashboard</span> <span class="sb-pill sb-pill--info sb-text-2xs" style="vertical-align:middle">Local</span>
  </div>
  <div class="sb-topbar-spacer"></div>
  <a href="/dashboard" class="sb-nav-link">Dashboard</a>
  <a href="/hire" class="sb-nav-link">Hire AI</a>
  <a href="/domains" class="sb-nav-link">Domains</a>
  <a href="/evidence" class="sb-nav-link">Evidence</a>
  <a href="/signoff" class="sb-nav-link">Sign Off</a>
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
// Solace Base JS — inspired by Crio's MVC patterns, upgraded for modern web
(function() {{
  'use strict';
  var S = window.Solace = window.Solace || {{}};

  // ── Section reload (Crio pattern: POST → replace innerHTML) ──
  S.reload = function(sectionId, url, params) {{
    fetch(url, {{
      method: params ? 'POST' : 'GET',
      headers: params ? {{'Content-Type': 'application/json'}} : {{}},
      body: params ? JSON.stringify(params) : undefined
    }}).then(function(r) {{ return r.text(); }}).then(function(html) {{
      var el = document.getElementById(sectionId);
      if (el) {{
        el.innerHTML = html;
        el.classList.add('sb-animate-in');
        S.initTables(el);
        setTimeout(function() {{ el.classList.remove('sb-animate-in'); }}, 300);
      }}
    }}).catch(function(e) {{ console.error('[Solace] reload failed:', e); }});
  }};

  // ── Form submit → reload section (Crio: reloadSectionWithForm) ──
  S.submitForm = function(sectionId, form) {{
    var data = new FormData(form);
    fetch(form.action || form.dataset.action, {{
      method: 'POST',
      body: data
    }}).then(function(r) {{ return r.text(); }}).then(function(html) {{
      var el = document.getElementById(sectionId);
      if (el) {{ el.innerHTML = html; S.highlight(sectionId); S.initTables(el); }}
    }});
  }};

  // ── Highlight flash on success (Crio: green flash dopamine) ──
  S.highlight = function(sectionId) {{
    var el = document.getElementById(sectionId);
    if (!el) return;
    el.style.transition = 'background 0.3s';
    el.style.background = 'rgba(38, 191, 140, 0.15)';
    setTimeout(function() {{ el.style.background = ''; }}, 1500);
  }};

  // ── Init DataTables on container ──
  S.initTables = function(container) {{
    if (typeof jQuery === 'undefined' || !jQuery.fn.DataTable) return;
    jQuery.fn.dataTable.ext.errMode = 'none';
    var tables = container ? jQuery(container).find('.sb-table') : jQuery('.sb-table');
    tables.each(function() {{
      try {{
        if (!jQuery.fn.DataTable.isDataTable(this)) {{
          jQuery(this).DataTable({{ paging: true, searching: true, ordering: true, pageLength: 25, dom: 'ftip' }});
        }}
      }} catch(e) {{}}
    }});
  }};

  // ── Inline edit (Crio: .editable click → load edit form) ──
  S.makeEditable = function(el, editUrl) {{
    el.style.cursor = 'pointer';
    el.title = 'Click to edit';
    el.addEventListener('click', function() {{
      S.reload(el.id, editUrl);
    }});
  }};

  // ── Toast notification ──
  S.toast = function(message, type) {{
    var toast = document.createElement('div');
    toast.className = 'sb-trust-badge sb-trust-badge--' + (type || 'verified');
    toast.style.cssText = 'position:fixed;top:1rem;right:1rem;z-index:9999;padding:0.5rem 1rem;font-size:0.85rem;box-shadow:var(--sb-shadow)';
    toast.textContent = message;
    document.body.appendChild(toast);
    toast.classList.add('sb-animate-in');
    setTimeout(function() {{ toast.remove(); }}, 3000);
  }};

  // ── Init on load ──
  S.initTables(document);
}})();
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
        assert!(html.contains("Solace Dashboard"));
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
