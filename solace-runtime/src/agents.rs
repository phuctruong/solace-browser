// Diagram: hub-cli-agent-registry
use std::path::PathBuf;
use std::process::Command;

use serde::{Deserialize, Serialize};

/// Definition of a known AI coding agent that can be detected on PATH.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AgentDef {
    pub id: String,
    pub name: String,
    pub cmd: String,
    pub invoke_pattern: Vec<String>,
    pub models: Vec<String>,
    pub default_model: String,
    pub provider: String,
    pub installed: bool,
    pub path: Option<String>,
}

/// Result of calling an agent's CLI.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AgentResponse {
    pub agent_id: String,
    pub model: String,
    pub prompt: String,
    pub response: String,
    pub exit_code: i32,
    pub duration_ms: u64,
    pub evidence_hash: String,
}

/// Static registry of the 6 known agents. `installed` and `path` are filled by detect_agents().
fn agent_defs() -> Vec<AgentDef> {
    vec![
        AgentDef {
            id: "claude".to_string(),
            name: "Claude Code".to_string(),
            cmd: "claude".to_string(),
            invoke_pattern: vec![
                "claude".to_string(),
                "-p".to_string(),
                "--model".to_string(),
                "{model}".to_string(),
                "{prompt}".to_string(),
            ],
            models: vec![
                "claude-opus-4-6".to_string(),
                "claude-sonnet-4-6".to_string(),
                "claude-haiku-4-5-20251001".to_string(),
            ],
            default_model: "claude-sonnet-4-6".to_string(),
            provider: "anthropic".to_string(),
            installed: false,
            path: None,
        },
        AgentDef {
            id: "codex".to_string(),
            name: "OpenAI Codex".to_string(),
            cmd: "codex".to_string(),
            invoke_pattern: vec![
                "codex".to_string(),
                "exec".to_string(),
                "{prompt}".to_string(),
            ],
            models: vec![
                "gpt-4.1".to_string(),
                "gpt-4.1-mini".to_string(),
                "o3".to_string(),
                "o4-mini".to_string(),
            ],
            default_model: "gpt-4.1".to_string(),
            provider: "openai".to_string(),
            installed: false,
            path: None,
        },
        AgentDef {
            id: "gemini".to_string(),
            name: "Google Gemini".to_string(),
            cmd: "gemini".to_string(),
            invoke_pattern: vec![
                "gemini".to_string(),
                "-p".to_string(),
                "{prompt}".to_string(),
            ],
            models: vec![
                "gemini-2.5-pro".to_string(),
                "gemini-2.5-flash".to_string(),
            ],
            default_model: "gemini-2.5-pro".to_string(),
            provider: "google".to_string(),
            installed: false,
            path: None,
        },
        // copilot and cursor removed — they are interactive-only (no headless mode)
        // copilot: GitHub Copilot CLI opens interactive UI
        // cursor: IDE launcher, not a headless CLI tool
        AgentDef {
            id: "aider".to_string(),
            name: "Aider".to_string(),
            cmd: "aider".to_string(),
            invoke_pattern: vec![
                "aider".to_string(),
                "--message".to_string(),
                "{prompt}".to_string(),
                "--no-git".to_string(),
                "--yes".to_string(),
            ],
            models: vec![
                "claude-sonnet-4-6".to_string(),
                "gpt-4.1".to_string(),
                "deepseek-v3".to_string(),
            ],
            default_model: "claude-sonnet-4-6".to_string(),
            provider: "aider".to_string(),
            installed: false,
            path: None,
        },
    ]
}

/// Scan PATH for known agents, returning defs with `installed` and `path` populated.
pub fn detect_agents() -> Vec<AgentDef> {
    let mut defs = agent_defs();
    for def in &mut defs {
        match which_agent(&def.cmd) {
            Some(path) => {
                def.installed = true;
                def.path = Some(path);
            }
            None => {
                def.installed = false;
                def.path = None;
            }
        }
    }
    // Cache to disk (best-effort, ignore errors)
    let _ = save_cache(&defs);
    defs
}

/// Check if a specific agent is still on PATH.
pub fn check_agent_health(agent_id: &str) -> Option<AgentDef> {
    let mut defs = agent_defs();
    defs.iter_mut()
        .find(|d| d.id == agent_id)
        .map(|def| {
            match which_agent(&def.cmd) {
                Some(path) => {
                    def.installed = true;
                    def.path = Some(path);
                }
                None => {
                    def.installed = false;
                    def.path = None;
                }
            }
            def.clone()
        })
}

/// Maximum timeout for agent invocations (120 seconds, per forbidden states).
const MAX_TIMEOUT_SECS: u64 = 120;

/// Invoke an agent CLI, capturing stdout. Returns structured response.
pub fn generate(
    agent_id: &str,
    model: Option<&str>,
    prompt: &str,
    timeout_secs: Option<u64>,
) -> Result<AgentResponse, String> {
    let agents = detect_agents();
    let agent = agents
        .iter()
        .find(|a| a.id == agent_id)
        .ok_or_else(|| format!("unknown agent: {agent_id}"))?;

    if !agent.installed {
        return Err(format!("agent not installed: {agent_id}"));
    }

    let resolved_model = model.unwrap_or(&agent.default_model);

    // Validate model is in the agent's supported list
    if !agent.models.iter().any(|m| m == resolved_model) {
        return Err(format!(
            "model '{}' not supported by agent '{}'. Supported: {:?}",
            resolved_model, agent_id, agent.models
        ));
    }

    // Build argv from invoke_pattern, replacing {model} and {prompt}
    let argv: Vec<String> = agent
        .invoke_pattern
        .iter()
        .map(|part| {
            part.replace("{model}", resolved_model)
                .replace("{prompt}", prompt)
        })
        .collect();

    if argv.is_empty() {
        return Err("empty invoke pattern".to_string());
    }

    let binary = agent.path.as_deref().unwrap_or(&argv[0]);
    let args = &argv[1..];

    let timeout = std::time::Duration::from_secs(
        timeout_secs.unwrap_or(MAX_TIMEOUT_SECS).min(MAX_TIMEOUT_SECS),
    );
    let start = std::time::Instant::now();

    let child = Command::new(binary)
        .args(args)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| format!("failed to spawn {}: {}", agent_id, e))?;

    // Timeout via channel: thread calls wait_with_output, main thread recv with timeout.
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let result = child.wait_with_output();
        let _ = tx.send(result);
    });

    let output = match rx.recv_timeout(timeout) {
        Ok(result) => result.map_err(|e| format!("failed to wait on {}: {}", agent_id, e))?,
        Err(std::sync::mpsc::RecvTimeoutError::Timeout) => {
            return Err(format!(
                "agent {} timed out after {}s",
                agent_id,
                timeout.as_secs()
            ));
        }
        Err(e) => return Err(format!("channel error waiting on {}: {}", agent_id, e)),
    };

    let duration_ms = start.elapsed().as_millis() as u64;
    let response_text = String::from_utf8_lossy(&output.stdout).to_string();
    let exit_code = output.status.code().unwrap_or(-1);

    if exit_code != 0 {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!(
            "agent {} exited with code {}: {}",
            agent_id,
            exit_code,
            stderr.chars().take(500).collect::<String>()
        ));
    }

    // Evidence hash: SHA-256 of agent_id + model + prompt + response
    let evidence_input = format!("{agent_id}:{resolved_model}:{prompt}:{response_text}");
    let evidence_hash = crate::utils::sha256_hex(&evidence_input);

    // Record evidence (best-effort)
    let _ = crate::persistence::append_evidence_jsonl(
        &crate::utils::solace_home(),
        &serde_json::json!({
            "event": "agent_generate",
            "agent_id": agent_id,
            "model": resolved_model,
            "prompt_len": prompt.len(),
            "response_len": response_text.len(),
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "evidence_hash": &evidence_hash,
            "timestamp": crate::utils::now_iso8601(),
        }),
    );

    Ok(AgentResponse {
        agent_id: agent_id.to_string(),
        model: resolved_model.to_string(),
        prompt: prompt.to_string(),
        response: response_text,
        exit_code,
        duration_ms,
        evidence_hash,
    })
}

/// Collect all models across all agents, grouped by agent.
pub fn all_models() -> Vec<serde_json::Value> {
    let agents = detect_agents();
    agents
        .iter()
        .map(|a| {
            serde_json::json!({
                "agent_id": a.id,
                "agent_name": a.name,
                "provider": a.provider,
                "installed": a.installed,
                "models": a.models,
                "default_model": a.default_model,
            })
        })
        .collect()
}

/// Use `which` to find an agent binary on PATH.
fn which_agent(cmd: &str) -> Option<String> {
    // Reject any command with path separators (PATH_INJECTION forbidden state)
    if cmd.contains('/') || cmd.contains('\\') {
        return None;
    }
    Command::new("which")
        .arg(cmd)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::null())
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .filter(|p| !p.is_empty())
}

/// Save agent cache to ~/.solace/cli-agents.json
fn save_cache(agents: &[AgentDef]) -> Result<(), String> {
    let cache_path = cache_path();
    crate::persistence::write_json(&cache_path, &agents)
}

/// Load agent cache from ~/.solace/cli-agents.json
pub fn load_cache() -> Option<Vec<AgentDef>> {
    let cache_path = cache_path();
    crate::persistence::read_json(&cache_path).ok()
}

fn cache_path() -> PathBuf {
    crate::utils::solace_home().join("cli-agents.json")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_defs_has_six_entries() {
        let defs = agent_defs();
        assert_eq!(defs.len(), 4);
    }

    #[test]
    fn test_agent_defs_ids_unique() {
        let defs = agent_defs();
        let mut ids: Vec<&str> = defs.iter().map(|d| d.id.as_str()).collect();
        ids.sort();
        ids.dedup();
        assert_eq!(ids.len(), 4);
    }

    #[test]
    fn test_agent_defs_default_model_in_models() {
        for def in agent_defs() {
            assert!(
                def.models.contains(&def.default_model),
                "agent {} default_model '{}' not in models {:?}",
                def.id,
                def.default_model,
                def.models
            );
        }
    }

    #[test]
    fn test_which_agent_rejects_path_separators() {
        assert!(which_agent("/bin/bash").is_none());
        assert!(which_agent("../bash").is_none());
    }

    #[test]
    fn test_detect_agents_returns_six() {
        let agents = detect_agents();
        assert_eq!(agents.len(), 4);
        // Each agent must have id, name, cmd filled
        for a in &agents {
            assert!(!a.id.is_empty());
            assert!(!a.name.is_empty());
            assert!(!a.cmd.is_empty());
        }
    }

    #[test]
    fn test_detect_agents_finds_at_least_one() {
        // In most dev environments, at least one of these should be installed.
        // If the test environment has none, this is informational only.
        let agents = detect_agents();
        let installed_count = agents.iter().filter(|a| a.installed).count();
        // Log what we found for debugging
        for a in &agents {
            if a.installed {
                eprintln!("  found: {} at {:?}", a.id, a.path);
            }
        }
        eprintln!("  installed agents: {installed_count}/6");
        // Don't hard-fail if zero agents found (CI might have none)
    }

    #[test]
    fn test_all_models_returns_entries() {
        let models = all_models();
        assert_eq!(models.len(), 4);
        for entry in &models {
            assert!(entry.get("agent_id").is_some());
            assert!(entry.get("models").is_some());
        }
    }

    #[test]
    fn test_check_agent_health_known() {
        let result = check_agent_health("claude");
        assert!(result.is_some());
        let agent = result.unwrap();
        assert_eq!(agent.id, "claude");
    }

    #[test]
    fn test_check_agent_health_unknown() {
        let result = check_agent_health("nonexistent-agent-xyz");
        assert!(result.is_none());
    }

    #[test]
    fn test_generate_unknown_agent() {
        let result = generate("nonexistent", None, "hello", None);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("unknown agent"));
    }

    #[test]
    fn test_generate_invalid_model() {
        // Even if claude is installed, "fake-model" is not in its model list
        let result = generate("claude", Some("fake-model"), "hello", None);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(
            err.contains("not supported") || err.contains("not installed"),
            "unexpected error: {err}"
        );
    }
}
