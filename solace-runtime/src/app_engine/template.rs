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

    let local_path = app_dir.join(&manifest.template);
    if let Ok(template) = fs::read_to_string(&local_path) {
        return Ok(template);
    }

    builtin_template(&manifest.template)
        .map(str::to_string)
        .ok_or_else(|| format!("template not found: {}", manifest.template))
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
