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
    let template_path = if manifest.template.is_empty() {
        app_dir.join("templates").join("report.html")
    } else {
        app_dir.join(&manifest.template)
    };
    let template =
        fs::read_to_string(&template_path).unwrap_or_else(|_| default_template().to_string());
    let mut env = Environment::new();
    env.add_template("report", &template)
        .map_err(|e| e.to_string())?;
    let tmpl = env.get_template("report")
        .map_err(|e| e.to_string())?;
    tmpl.render(minijinja::context! {
            app => manifest,
            context => context,
            generated_at => crate::utils::now_iso8601(),
        })
        .map_err(|e| e.to_string())
}

fn default_template() -> &'static str {
    r#"<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{{ app.name }}</title>
  <style>body{font-family:system-ui;padding:32px;max-width:900px;margin:auto}pre{background:#f4f4f4;padding:16px;border-radius:8px;overflow:auto}</style>
</head>
<body>
  <h1>{{ app.name|e }}</h1>
  <p>{{ app.description|e }}</p>
  <p><strong>Generated:</strong> {{ generated_at }}</p>
  <pre>{{ context|tojson(indent=2) }}</pre>
</body>
</html>"#
}
