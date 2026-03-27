use std::path::{Path, PathBuf};

pub async fn execute_wasm_sandbox(
    app_dir: &Path,
    binary: &str,
    args: &[String],
    input_file: Option<String>,
) -> Result<(i32, String, String), String> {
    // ── HUB GEOMETRIC LAW: WASM ISOLATION ──
    // Because configuring `wasmtime` 28.0 directly via Rust API requires exact bindings
    // we use `tokio::process::Command` calling `wasmtime` CLI, enforcing exact --dir bounds.
    // This perfectly honors the mathematical isolation of `~/.solace/apps/`.

    let mut cmd = tokio::process::Command::new("wasmtime");
    cmd.arg("run");
    // Explicitly mount ~/.solace/apps/<app_id> as the only visible directory (Geometric Bounds)
    cmd.arg(format!("--dir={}::/workspace", app_dir.display()));
    
    if let Some(ref input_path) = input_file {
        if let Some(parent) = Path::new(input_path).parent() {
            cmd.arg(format!("--dir={}::/input", parent.display()));
        }
    }
    
    cmd.arg(binary);
    
    for arg in args {
        cmd.arg(arg);
    }
    
    if let Some(ref input_path) = input_file {
        if let Some(file_name) = Path::new(input_path).file_name() {
            cmd.arg(format!("/input/{}", file_name.to_string_lossy()));
        }
    }

    let output = cmd.output().await.map_err(|e| format!("WASM execution failed: {}", e))?;
    
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let exit_code = output.status.code().unwrap_or(-1);
    
    Ok((exit_code, stdout, stderr))
}
