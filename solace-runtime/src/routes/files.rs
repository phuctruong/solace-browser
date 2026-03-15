// Diagram: hub-ux-architecture
use std::collections::BTreeMap;
use std::fs;

use axum::extract::Path;
use axum::http::StatusCode;
use axum::response::Html;
use axum::routing::get;
use axum::Router;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/", get(index))
        .route("/onboarding", get(onboarding_page))
        .route("/sidebar", get(sidebar_page))
        .route("/domains", get(domains_page))
        .route("/domains/:domain", get(domain_detail_page))
        .route("/apps/:app_id", get(app_detail_page))
        .route("/apps/:app_id/runs/:run_id", get(run_detail_page))
        .route("/evidence", get(evidence_page))
        .route("/styleguide", get(styleguide_page))
        .route("/styleguide.css", get(styleguide_css))
        .nest_service("/assets", tower_http::services::ServeDir::new("templates"))
        .nest_service(
            "/icons",
            tower_http::services::ServeDir::new("/home/phuc/projects/solace-browser/solace-hub/src/icons"),
        )
        .nest_service(
            "/media",
            tower_http::services::ServeDir::new("/home/phuc/projects/solace-browser/solace-hub/src/media"),
        )
        .nest_service(
            "/vendor",
            tower_http::services::ServeDir::new("/home/phuc/projects/solace-browser/solace-hub/src/vendor"),
        )
}

async fn index() -> Html<String> {
    // Serve the real Hub index.html if available
    let candidates = [
        std::path::PathBuf::from("/home/phuc/projects/solace-browser/solace-hub/src/index.html"),
        crate::utils::solace_home().join("hub").join("index.html"),
    ];
    for path in &candidates {
        if let Ok(content) = fs::read_to_string(path) {
            return Html(content);
        }
    }
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

// ---------------------------------------------------------------------------
// GET /domains — list all domains with app count per domain
// ---------------------------------------------------------------------------
async fn domains_page() -> Html<String> {
    let apps = crate::app_engine::scan_installed_apps();
    let mut domain_map: BTreeMap<String, Vec<&crate::app_engine::AppManifest>> = BTreeMap::new();
    for app in &apps {
        domain_map.entry(app.domain.clone()).or_default().push(app);
    }

    let mut rows = String::new();
    for (domain, domain_apps) in &domain_map {
        let count = domain_apps.len();
        let last_activity = domain_apps
            .iter()
            .filter_map(|a| {
                let dir = crate::utils::find_app_dir(&a.id)?;
                latest_run_time(&dir)
            })
            .max()
            .unwrap_or_else(|| "—".to_string());
        rows.push_str(&format!(
            "<tr><td><a href=\"/domains/{}\">{}</a></td><td>{}</td><td>{}</td></tr>",
            html_escape::encode_text(domain),
            html_escape::encode_text(domain),
            count,
            html_escape::encode_text(&last_activity),
        ));
    }

    if rows.is_empty() {
        rows = "<tr><td colspan=\"3\">No domains found. Install apps to get started.</td></tr>"
            .to_string();
    }

    let body = format!(
        "<table><thead><tr><th>Domain</th><th>Apps</th><th>Last Activity</th></tr></thead><tbody>{rows}</tbody></table>"
    );
    Html(hub_page("Domains", &body))
}

// ---------------------------------------------------------------------------
// GET /domains/:domain — domain detail page
// ---------------------------------------------------------------------------
async fn domain_detail_page(
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

    let body = format!(
        "<p><a href=\"/domains\">&larr; All Domains</a></p>\
         {stillwater_section}\
         <h2>Apps ({count})</h2>\
         <table><thead><tr><th>App</th><th>Version</th><th>Runs</th><th>Last Run</th></tr></thead><tbody>{app_rows}</tbody></table>\
         <h2>Recent Runs</h2>\
         <table><thead><tr><th>Run</th><th>App</th><th>Time</th></tr></thead><tbody>{run_rows}</tbody></table>",
        count = apps.len(),
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

    let body = format!(
        "<p><a href=\"/domains/{domain}\">&larr; {domain}</a></p>\
         {manifest_section}\
         <h2>Runs</h2>\
         <table><thead><tr><th>Run ID</th><th>Time</th></tr></thead><tbody>{run_rows}</tbody></table>",
        domain = html_escape::encode_text(&app.domain),
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

/// Serve the styleguide page from the Hub frontend directory.
async fn styleguide_page() -> Html<String> {
    // Try to find the styleguide.html in the Hub src directory
    let candidates = [
        std::path::PathBuf::from("/home/phuc/projects/solace-browser/solace-hub/src/styleguide.html"),
        crate::utils::solace_home().join("hub").join("styleguide.html"),
    ];
    for path in &candidates {
        if let Ok(content) = fs::read_to_string(path) {
            return Html(content);
        }
    }
    Html("<html><body><h1>Styleguide not found</h1><p>Place styleguide.html in solace-hub/src/</p></body></html>".to_string())
}

/// Serve the styleguide CSS from the Hub frontend directory.
async fn styleguide_css() -> (StatusCode, [(axum::http::header::HeaderName, &'static str); 1], String) {
    let candidates = [
        std::path::PathBuf::from("/home/phuc/projects/solace-browser/solace-hub/src/styleguide.css"),
        crate::utils::solace_home().join("hub").join("styleguide.css"),
    ];
    for path in &candidates {
        if let Ok(content) = fs::read_to_string(path) {
            return (StatusCode::OK, [(axum::http::header::CONTENT_TYPE, "text/css")], content);
        }
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
fn hub_page(title: &str, body_content: &str) -> String {
    format!(
        r#"<!doctype html>
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
.chain-invalid {{ background: var(--sb-danger); color: #fff; }}
</style>
</head>
<body>
<header class="sb-topbar">
  <div class="sb-topbar-brand">
    <img src="/icons/yinyang-logo.png" alt="Solace">
    <span>Solace Hub</span>
  </div>
  <div class="sb-topbar-spacer"></div>
  <a href="/domains" style="color:var(--sb-text-muted);font-size:0.85rem">Domains</a>
  <a href="/evidence" style="color:var(--sb-text-muted);font-size:0.85rem">Evidence</a>
  <a href="/styleguide" style="color:var(--sb-text-muted);font-size:0.85rem">Styleguide</a>
  <a href="/health" style="color:var(--sb-text-muted);font-size:0.85rem">Health</a>
</header>
<main style="max-width:1100px;margin:1.5rem auto;padding:0 1.5rem">
<h1 class="sb-heading" style="font-size:1.4rem;margin-bottom:1rem">{title}</h1>
{body_content}
</main>
<script src="/vendor/jquery-3.7.1.min.js"></script>
<script src="/vendor/jquery.dataTables.min.js"></script>
<script>
if (typeof jQuery !== 'undefined' && jQuery.fn.DataTable) {{
  jQuery('.sb-table').each(function() {{
    if (!jQuery.fn.DataTable.isDataTable(this)) {{
      jQuery(this).DataTable({{ paging: true, searching: true, ordering: true, pageLength: 25, dom: 'ftip' }});
    }}
  }});
}}
</script>
</body>
</html>"#,
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
