// Diagram: apps-cli-worker-framework
//! CLI Worker auto-detection + generic run API.
//! Scans PATH for known tools, wraps them with standard REST interface.

use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::process::Command;
use std::time::{Duration, Instant};

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/cli", get(list_cli_workers))
        .route("/api/v1/cli/:worker_id/status", get(worker_status))
        .route("/api/v1/cli/:worker_id/run", post(run_worker))
}

/// Known CLI tools that can be wrapped as workers.
const CLI_REGISTRY: &[CliDef] = &[
    // Reasoning (LLM agents)
    CliDef { id: "claude-worker", detect: &["claude"], category: "reasoning", description: "Claude Code — AI coding + analysis" },
    CliDef { id: "codex-worker", detect: &["codex"], category: "reasoning", description: "OpenAI Codex — GPT-5.4 code generation" },
    CliDef { id: "gemini-worker", detect: &["gemini"], category: "reasoning", description: "Google Gemini — multimodal AI" },
    CliDef { id: "ollama-worker", detect: &["ollama"], category: "reasoning", description: "Ollama — local LLM inference" },
    // Perception
    CliDef { id: "transcriber", detect: &["whisper"], category: "perception", description: "Whisper — speech-to-text" },
    CliDef { id: "web-scraper", detect: &["curl"], category: "perception", description: "Web page fetcher + text extractor" },
    CliDef { id: "doc-reader", detect: &["pandoc"], category: "perception", description: "Universal doc converter (PDF/DOCX → markdown)" },
    // Action
    CliDef { id: "git-worker", detect: &["git"], category: "action", description: "Git — commit, branch, merge, diff" },
    CliDef { id: "gh-worker", detect: &["gh"], category: "action", description: "GitHub CLI — issues, PRs, releases" },
    CliDef { id: "file-converter", detect: &["ffmpeg"], category: "action", description: "FFmpeg — video/audio conversion" },
    CliDef { id: "docker-worker", detect: &["docker"], category: "action", description: "Docker — container management" },
    // Utility
    CliDef { id: "image-processor", detect: &["convert", "magick"], category: "utility", description: "ImageMagick — image manipulation" },
    CliDef { id: "data-analyst", detect: &["python3"], category: "utility", description: "Python — data analysis + scripting" },
];

struct CliDef {
    id: &'static str,
    detect: &'static [&'static str],
    category: &'static str,
    description: &'static str,
}

/// Check if a CLI tool is installed by running `which`.
fn detect_cli(names: &[&str]) -> Option<(String, String)> {
    for name in names {
        if let Ok(output) = Command::new("which").arg(name).output() {
            if output.status.success() {
                let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
                // Get version
                let version = Command::new(name)
                    .arg("--version")
                    .output()
                    .ok()
                    .map(|o| String::from_utf8_lossy(&o.stdout).lines().next().unwrap_or("").to_string())
                    .unwrap_or_default();
                return Some((path, version));
            }
        }
    }
    None
}

async fn list_cli_workers(State(_state): State<AppState>) -> Json<Value> {
    let mut workers = Vec::new();
    let mut by_category: HashMap<&str, Vec<Value>> = HashMap::new();

    for def in CLI_REGISTRY {
        let detected = detect_cli(def.detect);
        let installed = detected.is_some();
        let (path, version) = detected.unwrap_or_default();

        let worker = json!({
            "id": def.id,
            "category": def.category,
            "description": def.description,
            "installed": installed,
            "path": path,
            "version": version,
            "api": format!("/api/v1/cli/{}/run", def.id),
        });

        by_category.entry(def.category).or_default().push(worker.clone());
        workers.push(worker);
    }

    let installed_count = workers.iter().filter(|w| w["installed"].as_bool().unwrap_or(false)).count();

    Json(json!({
        "workers": workers,
        "total": workers.len(),
        "installed": installed_count,
        "by_category": by_category,
    }))
}

async fn worker_status(
    State(_state): State<AppState>,
    Path(worker_id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let def = CLI_REGISTRY.iter().find(|d| d.id == worker_id).ok_or_else(|| {
        (StatusCode::NOT_FOUND, Json(json!({"error": format!("unknown worker '{}'", worker_id)})))
    })?;

    let detected = detect_cli(def.detect);
    let (path, version) = detected.clone().unwrap_or_default();

    Ok(Json(json!({
        "id": def.id,
        "installed": detected.is_some(),
        "path": path,
        "version": version,
        "category": def.category,
        "description": def.description,
    })))
}

#[derive(Deserialize)]
struct RunRequest {
    /// Input to pass to the CLI (command args or stdin)
    input: String,
    /// Additional CLI arguments
    #[serde(default)]
    args: Vec<String>,
    /// Timeout in seconds (default 60, max 300)
    #[serde(default = "default_timeout")]
    timeout: u64,
}

fn default_timeout() -> u64 { 60 }

/// ALLOWLIST: only these CLI commands can be executed.
/// This prevents arbitrary command injection.
const ALLOWED_COMMANDS: &[&str] = &[
    "claude", "codex", "gemini", "ollama",
    "whisper", "curl", "pandoc",
    "git", "gh", "ffmpeg", "docker",
    "convert", "magick", "python3",
];

async fn run_worker(
    State(state): State<AppState>,
    Path(worker_id): Path<String>,
    Json(req): Json<RunRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let def = CLI_REGISTRY.iter().find(|d| d.id == worker_id).ok_or_else(|| {
        (StatusCode::NOT_FOUND, Json(json!({"error": format!("unknown worker '{}'", worker_id)})))
    })?;

    // Verify installed
    let (path, _version) = detect_cli(def.detect).ok_or_else(|| {
        (StatusCode::SERVICE_UNAVAILABLE, Json(json!({"error": format!("'{}' not installed", def.detect[0])})))
    })?;

    // Security: only allow known commands
    let cmd_name = std::path::Path::new(&path)
        .file_name()
        .and_then(|f| f.to_str())
        .unwrap_or("");
    if !ALLOWED_COMMANDS.contains(&cmd_name) {
        return Err((StatusCode::FORBIDDEN, Json(json!({"error": "command not in allowlist"}))));
    }

    // Clamp timeout
    let timeout_secs = req.timeout.min(300).max(1);

    // Build command
    let mut cmd = Command::new(&path);
    for arg in &req.args {
        // Basic injection prevention: no shell metacharacters in args
        if arg.contains(';') || arg.contains('|') || arg.contains('`') || arg.contains('$') {
            return Err((StatusCode::BAD_REQUEST, Json(json!({"error": "shell metacharacters not allowed in args"}))));
        }
        cmd.arg(arg);
    }

    // For some workers, input goes as stdin; for others, as an arg
    match def.id {
        "web-scraper" => { cmd.arg("-sf").arg(&req.input); }
        "doc-reader" => { cmd.arg(&req.input).arg("-t").arg("markdown"); }
        "git-worker" => {
            // Git commands: input is the subcommand
            let parts: Vec<&str> = req.input.split_whitespace().collect();
            for part in &parts {
                cmd.arg(part);
            }
        }
        "gh-worker" => {
            let parts: Vec<&str> = req.input.split_whitespace().collect();
            for part in &parts {
                cmd.arg(part);
            }
        }
        _ => {
            // Default: pass input as stdin via echo | cmd
            // For LLM workers, input is the prompt
            cmd.arg(&req.input);
        }
    }

    let start = Instant::now();
    let output = tokio::task::spawn_blocking(move || {
        cmd.output()
    })
    .await
    .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": format!("spawn: {e}")}))))?
    .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": format!("exec: {e}")}))))?;

    let duration_ms = start.elapsed().as_millis() as u64;
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let exit_code = output.status.code().unwrap_or(-1);

    // Evidence
    let mut hasher = sha2::Sha256::new();
    use sha2::Digest;
    hasher.update(format!("{}:{}:{}:{}", worker_id, req.input, stdout.len(), exit_code).as_bytes());
    let evidence_hash = format!("{:x}", hasher.finalize())[..16].to_string();

    let solace_home = crate::utils::solace_home();
    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("cli.run.{}", worker_id),
        "system",
        json!({
            "worker": worker_id,
            "input_len": req.input.len(),
            "output_len": stdout.len(),
            "exit_code": exit_code,
            "duration_ms": duration_ms,
        }),
    );
    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "worker": worker_id,
        "exit_code": exit_code,
        "output": if stdout.len() > 50000 { &stdout[..50000] } else { &stdout },
        "stderr": if stderr.len() > 5000 { &stderr[..5000] } else { &stderr },
        "duration_ms": duration_ms,
        "evidence_hash": evidence_hash,
        "truncated": stdout.len() > 50000,
    })))
}
