// Diagram: 12-app-engine-pipeline
use std::fs;
use std::path::Path;

use minijinja::Environment;
use serde_json::Value;

use super::AppManifest;

pub fn render_report(
    manifest: &AppManifest,
    app_dir: &Path,
    context: &Value,
) -> Result<String, String> {
    let template = load_template(manifest, app_dir)?;
    let mut env = Environment::new();
    env.add_template("report", &template)
        .map_err(|e| e.to_string())?;
    let tmpl = env.get_template("report").map_err(|e| e.to_string())?;
    tmpl.render(minijinja::context! {
        app => manifest,
        context => context,
        generated_at => crate::utils::now_iso8601(),
    })
    .map_err(|e| e.to_string())
}

fn load_template(manifest: &AppManifest, app_dir: &Path) -> Result<String, String> {
    if manifest.template.is_empty() {
        let local_default = app_dir.join("templates").join("report.html");
        if let Ok(template) = fs::read_to_string(&local_default) {
            return Ok(template);
        }
        return Ok(builtin_template("report-base.html")
            .unwrap_or_default()
            .to_string());
    }

    // Inline template: if the template field contains {{ or {%, treat as content not filename
    if manifest.template.contains("{{") || manifest.template.contains("{%") {
        return Ok(wrap_inline_template(&manifest.template));
    }

    let local_path = app_dir.join(&manifest.template);
    if let Ok(template) = fs::read_to_string(&local_path) {
        return Ok(template);
    }

    builtin_template(&manifest.template)
        .map(str::to_string)
        .ok_or_else(|| format!("template not found: {}", manifest.template))
}

/// Wrap inline template content in the standard report HTML structure.
fn wrap_inline_template(content: &str) -> String {
    let header = r#"<!-- Diagram: 05-solace-runtime-architecture -->
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ app.name }} | {{ generated_at }}</title>
  <style>
    body { font-family: system-ui; max-width: 920px; margin: auto; padding: 32px; color: #0f172a; }
    header, footer { border-bottom: 1px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px; }
    footer { border-top: 1px solid #e2e8f0; border-bottom: 0; padding-top: 16px; margin-top: 32px; }
    section { margin-bottom: 24px; }
    pre { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; overflow: auto; }
    .meta { color: #64748b; font-size: 0.9rem; }
  </style>
</head>
<body>
  <header>
    <h1>{{ app.name }}</h1>
    <p>{{ app.description }}</p>
    <p class="meta">Generated: {{ generated_at }}</p>
  </header>
  <section>"#;
    let footer = r#"  </section>
  <footer>
    <p class="meta">Solace Runtime | Evidence-chained</p>
  </footer>
</body>
</html>"#;
    [header, content, footer].join("\n")
}

fn builtin_template(name: &str) -> Option<&'static str> {
    match name {
        "feed-digest" | "feed-digest.html" => {
            Some(include_str!("../../templates/feed-digest.html"))
        }
        "morning-brief" | "morning-brief.html" | "orchestration" => {
            Some(include_str!("../../templates/morning-brief.html"))
        }
        "report-base" | "report-base.html" => {
            Some(include_str!("../../templates/report-base.html"))
        }
        _ => None,
    }
}
