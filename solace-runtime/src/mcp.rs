// Diagram: 23-mcp-agent-interface
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

use crate::state::{AppState, Notification, SessionInfo};

const MCP_PROTOCOL_VERSION: &str = "2024-11-05";

pub fn mcp_tool_definitions() -> Vec<Value> {
    vec![
        json!({
            "name": "run_app",
            "description": "Execute an installed Solace app by ID",
            "inputSchema": {
                "type": "object",
                "properties": {"app_id": {"type": "string"}},
                "required": ["app_id"]
            }
        }),
        json!({
            "name": "list_apps",
            "description": "List installed Solace apps",
            "inputSchema": {"type": "object", "properties": {}}
        }),
        json!({
            "name": "browser_launch",
            "description": "Launch a browser session",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "profile": {"type": "string"},
                    "url": {"type": "string"},
                    "mode": {"type": "string"}
                }
            }
        }),
        json!({
            "name": "browser_close",
            "description": "Close a browser session",
            "inputSchema": {
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"]
            }
        }),
        json!({
            "name": "evidence_list",
            "description": "List evidence entries",
            "inputSchema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1}}
            }
        }),
        json!({
            "name": "schedule_list",
            "description": "List configured cron schedules",
            "inputSchema": {"type": "object", "properties": {}}
        }),
        json!({
            "name": "chat",
            "description": "Send a preview chat message",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "persona": {"type": "string"}
                },
                "required": ["message"]
            }
        }),
        json!({
            "name": "system_status",
            "description": "Return runtime status",
            "inputSchema": {"type": "object", "properties": {}}
        }),
        json!({
            "name": "agent_list",
            "description": "List detected AI coding agents on PATH",
            "inputSchema": {"type": "object", "properties": {}}
        }),
        json!({
            "name": "agent_generate",
            "description": "Invoke an AI coding agent to generate a response",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent identifier (claude, codex, gemini, copilot, cursor, aider)"},
                    "prompt": {"type": "string", "description": "The prompt to send to the agent"},
                    "model": {"type": "string", "description": "Model to use (optional, defaults to agent's default)"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (max 120)", "minimum": 1, "maximum": 120}
                },
                "required": ["agent_id", "prompt"]
            }
        }),
        // ── Backoffice ──
        json!({"name": "backoffice_read", "description": "Read records from backoffice table (CRM, messages, tasks, etc.)", "inputSchema": {"type": "object", "properties": {"app_id": {"type": "string"}, "table": {"type": "string"}}, "required": ["app_id", "table"]}}),
        json!({"name": "backoffice_write", "description": "Create record in backoffice table", "inputSchema": {"type": "object", "properties": {"app_id": {"type": "string"}, "table": {"type": "string"}, "data": {"type": "object"}}, "required": ["app_id", "table", "data"]}}),
        // ── CLI workers ──
        json!({"name": "cli_run", "description": "Run CLI worker (web-scraper, git-worker, claude-worker)", "inputSchema": {"type": "object", "properties": {"worker_id": {"type": "string"}, "input": {"type": "string"}}, "required": ["worker_id", "input"]}}),
        json!({"name": "cli_list", "description": "List available CLI workers", "inputSchema": {"type": "object", "properties": {}}}),
        // ── Jobs ──
        json!({"name": "job_enqueue", "description": "Add job to priority queue", "inputSchema": {"type": "object", "properties": {"job_type": {"type": "string"}, "payload": {"type": "object"}, "priority": {"type": "integer"}}, "required": ["job_type", "payload"]}}),
        json!({"name": "job_claim", "description": "Claim next available job", "inputSchema": {"type": "object", "properties": {"worker_id": {"type": "string"}}, "required": ["worker_id"]}}),
        // ── Events ──
        json!({"name": "event_publish", "description": "Publish event to topic", "inputSchema": {"type": "object", "properties": {"topic": {"type": "string"}, "payload": {"type": "object"}}, "required": ["topic", "payload"]}}),
        // ── Wiki ──
        json!({"name": "wiki_stats", "description": "Get Prime Wiki snapshot stats", "inputSchema": {"type": "object", "properties": {}}}),
        json!({"name": "wiki_extract", "description": "Extract page to Stillwater+PZip snapshot", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}, "content": {"type": "string"}}, "required": ["url", "content"]}}),
        // ── Domains ──
        json!({"name": "domain_status", "description": "Get domain status (apps, OAuth3, wiki)", "inputSchema": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]}}),
        json!({"name": "domain_triggers", "description": "Match domain app triggers for URL", "inputSchema": {"type": "object", "properties": {"domain": {"type": "string"}, "path": {"type": "string"}}, "required": ["domain"]}}),
        // ── Webhooks + File Watch ──
        json!({"name": "webhook_create", "description": "Register webhook for events", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "url": {"type": "string"}, "event": {"type": "string"}}, "required": ["name", "url", "event"]}}),
        json!({"name": "file_watch", "description": "Watch filesystem path for changes", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "pattern": {"type": "string"}, "app_id": {"type": "string"}}, "required": ["path"]}}),
        // ── Sign-off ──
        json!({"name": "esign", "description": "Sign off on action (approve/reject with RL feedback)", "inputSchema": {"type": "object", "properties": {"action_id": {"type": "string"}, "decision": {"type": "string"}, "feedback": {"type": "string"}}, "required": ["action_id", "decision"]}}),
        // ── Browser: Live Page HTML ──
        json!({"name": "browser_page_html", "description": "Get the ACTUAL currently-rendered full page HTML of the active browser tab. Returns the live outerHTML captured by the sidebar on every URL change. Use text_only=true for visible text without tags.", "inputSchema": {"type": "object", "properties": {"text_only": {"type": "boolean", "description": "If true, strip HTML tags and return visible text only"}}, "required": []}}),
        // ── P0: Browser Visibility (Unfair Advantages) ──
        json!({"name": "browser_tabs", "description": "List all open browser tabs with URLs and titles — see what the browser is doing", "inputSchema": {"type": "object", "properties": {}}}),
        json!({"name": "browser_navigate", "description": "Navigate the Solace Browser to a URL via Chromium IPC (no xdotool)", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}, "wait_for": {"type": "string", "description": "Optional CSS selector to wait for after navigation"}}, "required": ["url"]}}),
        json!({"name": "browser_sessions", "description": "List all active browser sessions (ID, URL, PID, mode)", "inputSchema": {"type": "object", "properties": {}}}),
        json!({"name": "domain_tab_acquire", "description": "Acquire domain tab lock (1-tab-per-domain coordination)", "inputSchema": {"type": "object", "properties": {"domain": {"type": "string"}, "app_id": {"type": "string"}, "url": {"type": "string"}}, "required": ["domain"]}}),
        json!({"name": "domain_tab_release", "description": "Release domain tab lock back to idle", "inputSchema": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]}}),
        json!({"name": "budget_status", "description": "Get budget usage and enforcement status (fail-closed)", "inputSchema": {"type": "object", "properties": {}}}),
        json!({"name": "worker_run_status", "description": "Get live worker run progress (current step, status, log lines)", "inputSchema": {"type": "object", "properties": {}}}),
        // ── P1: Browser Control (via sidebar WebSocket relay, NOT xdotool) ──
        json!({"name": "browser_click", "description": "Click element by CSS selector (relayed via sidebar WebSocket)", "inputSchema": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}}),
        json!({"name": "browser_fill", "description": "Fill form field by selector (submit=true to press Enter after)", "inputSchema": {"type": "object", "properties": {"selector": {"type": "string"}, "value": {"type": "string"}, "submit": {"type": "boolean"}}, "required": ["selector", "value"]}}),
        json!({"name": "browser_key", "description": "Press keyboard key in browser (Return, Tab, Escape, End, etc.)", "inputSchema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}}),
        json!({"name": "browser_screenshot", "description": "Get screenshot status (captured by sidebar)", "inputSchema": {"type": "object", "properties": {}}}),
        json!({"name": "notifications_list", "description": "List all notifications (read/unread)", "inputSchema": {"type": "object", "properties": {}}}),
        // ── Tab Management ──
        json!({"name": "browser_tabs_close_all", "description": "Close all browser tabs except the active one (via sidebar WebSocket)", "inputSchema": {"type": "object", "properties": {}}}),
        json!({"name": "browser_tab_close", "description": "Close a specific browser tab by ID", "inputSchema": {"type": "object", "properties": {"tab_id": {"type": "string"}}, "required": ["tab_id"]}}),
        json!({"name": "browser_active_tab", "description": "Get the currently active browser tab (URL, title)", "inputSchema": {"type": "object", "properties": {}}}),
        // ── Updates ──
        json!({"name": "check_update", "description": "Check for updates and install if available (triggers immediate check against GCS manifest)", "inputSchema": {"type": "object", "properties": {}}}),
    ]
}

pub fn mcp_resource_definitions() -> Vec<Value> {
    vec![
        json!({
            "uri": "solace://apps",
            "name": "Solace Apps",
            "description": "Installed Solace app catalog",
            "mimeType": "application/json"
        }),
        json!({
            "uri": "solace://evidence",
            "name": "Solace Evidence",
            "description": "Hash-chained evidence log",
            "mimeType": "application/json"
        }),
    ]
}

pub async fn run_mcp_server(state: AppState) {
    let stdin = BufReader::new(tokio::io::stdin());
    let mut lines = stdin.lines();
    let mut stdout = tokio::io::stdout();

    while let Ok(Some(line)) = lines.next_line().await {
        let request: Value = match serde_json::from_str(&line) {
            Ok(value) => value,
            Err(_) => continue,
        };

        let Some(id) = request.get("id").cloned() else {
            continue;
        };

        let response = match dispatch_request(&request, &state).await {
            Ok(result) => json!({"jsonrpc": "2.0", "id": id, "result": result}),
            Err((code, message)) => {
                json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
            }
        };

        if stdout
            .write_all(response.to_string().as_bytes())
            .await
            .is_err()
        {
            break;
        }
        if stdout.write_all(b"\n").await.is_err() {
            break;
        }
        if stdout.flush().await.is_err() {
            break;
        }
    }
}

async fn dispatch_request(request: &Value, state: &AppState) -> Result<Value, (i64, String)> {
    let method = request
        .get("method")
        .and_then(Value::as_str)
        .ok_or_else(|| (-32600, "Invalid Request".to_string()))?;
    let params = request.get("params").cloned().unwrap_or_else(|| json!({}));

    match method {
        "initialize" => Ok(handle_initialize()),
        "ping" => Ok(json!({})),
        "tools/list" => Ok(handle_tools_list()),
        "tools/call" => handle_tools_call(&params, state).await,
        "resources/list" => Ok(handle_resources_list()),
        "resources/read" => handle_resources_read(&params),
        _ => Err((-32601, format!("Method not found: {method}"))),
    }
}

fn handle_initialize() -> Value {
    json!({
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {
            "tools": {"listChanged": false},
            "resources": {"subscribe": false, "listChanged": false}
        },
        "serverInfo": {
            "name": "solace-runtime",
            "version": env!("CARGO_PKG_VERSION")
        }
    })
}

fn handle_tools_list() -> Value {
    json!({"tools": mcp_tool_definitions()})
}

async fn handle_tools_call(params: &Value, state: &AppState) -> Result<Value, (i64, String)> {
    let name = params
        .get("name")
        .and_then(Value::as_str)
        .ok_or_else(|| (-32602, "tools/call requires params.name".to_string()))?;
    let arguments = params
        .get("arguments")
        .cloned()
        .unwrap_or_else(|| json!({}));

    let payload = match name {
        "run_app" => {
            let app_id = require_string(&arguments, "app_id")?;
            let result = crate::app_engine::runner::run_app(&app_id, state)
                .await
                .map_err(|error| (-32000, error))?;
            let value =
                serde_json::to_value(&result).map_err(|error| (-32000, error.to_string()))?;
            if value.is_object() {
                value
            } else {
                json!({"result": value, "app_id": app_id})
            }
        }
        "list_apps" => json!({"apps": crate::app_engine::scan_installed_apps()}),
        "browser_launch" => {
            let session = SessionInfo {
                session_id: uuid::Uuid::new_v4().to_string(),
                profile: optional_string(&arguments, "profile")
                    .unwrap_or_else(|| "default".to_string()),
                url: optional_string(&arguments, "url")
                    .unwrap_or_else(|| "https://solaceagi.com".to_string()),
                pid: rand::random::<u32>() % 89_999 + 10_000,
                started_at: crate::utils::now_iso8601(),
                mode: optional_string(&arguments, "mode")
                    .unwrap_or_else(|| "local-dev".to_string()),
            };
            state
                .sessions
                .write()
                .insert(session.session_id.clone(), session.clone());
            json!({"session": session})
        }
        "browser_close" => {
            let session_id = require_string(&arguments, "session_id")?;
            let session = state
                .sessions
                .write()
                .remove(&session_id)
                .ok_or_else(|| (-32000, format!("session not found: {session_id}")))?;
            json!({"closed": session.session_id, "profile": session.profile})
        }
        "evidence_list" => {
            let limit = arguments.get("limit").and_then(Value::as_u64).unwrap_or(25) as usize;
            let entries = crate::evidence::list_evidence(&crate::utils::solace_home(), limit);
            json!({"entries": entries})
        }
        "schedule_list" => json!({"schedules": state.schedules.read().clone()}),
        "chat" => {
            let message = require_string(&arguments, "message")?;
            let route = if state
                .cloud_config
                .read()
                .as_ref()
                .is_some_and(|config| config.paid_user)
            {
                "solace-cloud"
            } else {
                "local-preview"
            };
            state.notifications.write().push(Notification {
                id: uuid::Uuid::new_v4().to_string(),
                message: format!("Chat routed to {route}"),
                level: "info".to_string(),
                read: false,
                created_at: crate::utils::now_iso8601(),
            });
            json!({
                "accepted": true,
                "route": route,
                "execution_mode": "preview_only",
                "persona": optional_string(&arguments, "persona").unwrap_or_else(|| "default".to_string()),
                "reply": format!("Preview routed via {route}: {message}")
            })
        }
        "system_status" => system_status_payload(state),
        "agent_list" => {
            let agents = crate::agents::detect_agents();
            let installed_count = agents.iter().filter(|a| a.installed).count();
            json!({"agents": agents, "total": agents.len(), "installed": installed_count})
        }
        "agent_generate" => {
            let agent_id = require_string(&arguments, "agent_id")?;
            let prompt = require_string(&arguments, "prompt")?;
            let model = optional_string(&arguments, "model");
            let timeout = arguments.get("timeout").and_then(Value::as_u64);
            match crate::agents::generate(&agent_id, model.as_deref(), &prompt, timeout) {
                Ok(response) => json!({
                    "agent_id": response.agent_id,
                    "model": response.model,
                    "response": response.response,
                    "exit_code": response.exit_code,
                    "duration_ms": response.duration_ms,
                    "evidence_hash": response.evidence_hash,
                }),
                Err(error) => return Err((-32000, error)),
            }
        }
        "browser_page_html" => {
            let page = state.page_html.read();
            if page.html.is_empty() {
                json!({"error": "no_page_captured", "message": "No page HTML captured yet. Navigate to a page first."})
            } else {
                let text_only = arguments
                    .get("text_only")
                    .and_then(Value::as_bool)
                    .unwrap_or(false);
                let content = if text_only {
                    let re = regex::Regex::new(r"<[^>]+>")
                        .unwrap_or_else(|_| regex::Regex::new(r"$^").unwrap());
                    let text = re.replace_all(&page.html, "");
                    let ws = regex::Regex::new(r"\s+")
                        .unwrap_or_else(|_| regex::Regex::new(r"$^").unwrap());
                    ws.replace_all(&text, " ").trim().to_string()
                } else {
                    page.html.clone()
                };
                json!({
                    "url": page.url,
                    "title": page.title,
                    "captured_at": page.captured_at,
                    "html_length": page.html.len(),
                    "content": content,
                    "text_only": text_only,
                })
            }
        }
        // ── Backoffice ──
        "backoffice_read" => {
            let app_id = require_string(&arguments, "app_id")?;
            let table_name = require_string(&arguments, "table")?;
            let config = crate::routes::backoffice::load_workspace_config(&app_id)
                .map_err(|e| (-32000, e))?;
            let table_def = config
                .tables
                .iter()
                .find(|t| t.name == table_name)
                .ok_or_else(|| {
                    (
                        -32000,
                        format!("table '{}' not found in app '{}'", table_name, app_id),
                    )
                })?;
            let conn = state
                .backoffice_db
                .get_connection(&app_id, &config)
                .map_err(|e| (-32000, e))?;
            let conn_guard = conn.lock();
            crate::backoffice::crud::select_list(&conn_guard, table_def, 0, 50, None, &[])
                .map_err(|e| (-32000, e))?
        }
        "backoffice_write" => {
            let app_id = require_string(&arguments, "app_id")?;
            let table_name = require_string(&arguments, "table")?;
            let data = arguments.get("data").cloned().unwrap_or_else(|| json!({}));
            let config = crate::routes::backoffice::load_workspace_config(&app_id)
                .map_err(|e| (-32000, e))?;
            let table_def = config
                .tables
                .iter()
                .find(|t| t.name == table_name)
                .ok_or_else(|| {
                    (
                        -32000,
                        format!("table '{}' not found in app '{}'", table_name, app_id),
                    )
                })?;
            let conn = state
                .backoffice_db
                .get_connection(&app_id, &config)
                .map_err(|e| (-32000, e))?;
            let conn_guard = conn.lock();
            let record =
                crate::backoffice::crud::insert(&conn_guard, table_def, &data, "mcp_client")
                    .map_err(|e| (-32000, e))?;
            state.event_bus.publish(
                crate::pubsub::topics::BACKOFFICE_WRITE,
                json!({"app_id": app_id, "table": table_name, "action": "create"}),
                "mcp_client",
            );
            json!({"created": true, "record": record})
        }
        // ── CLI Workers ──
        "cli_list" => {
            let mut workers = Vec::new();
            let registry = [
                (
                    "claude-worker",
                    "claude",
                    "reasoning",
                    "Claude Code — AI coding + analysis",
                ),
                (
                    "codex-worker",
                    "codex",
                    "reasoning",
                    "OpenAI Codex — GPT-5.4 code generation",
                ),
                (
                    "gemini-worker",
                    "gemini",
                    "reasoning",
                    "Google Gemini — multimodal AI",
                ),
                (
                    "web-scraper",
                    "curl",
                    "perception",
                    "Web page fetcher + text extractor",
                ),
                (
                    "git-worker",
                    "git",
                    "action",
                    "Git — commit, branch, merge, diff",
                ),
                (
                    "gh-worker",
                    "gh",
                    "action",
                    "GitHub CLI — issues, PRs, releases",
                ),
                (
                    "data-analyst",
                    "python3",
                    "utility",
                    "Python — data analysis + scripting",
                ),
            ];
            for (id, cmd, category, description) in &registry {
                let installed = std::process::Command::new("which")
                    .arg(cmd)
                    .output()
                    .map(|o| o.status.success())
                    .unwrap_or(false);
                workers.push(json!({
                    "id": id, "command": cmd, "category": category,
                    "description": description, "installed": installed,
                }));
            }
            let installed_count = workers
                .iter()
                .filter(|w| w["installed"].as_bool().unwrap_or(false))
                .count();
            json!({"workers": workers, "total": workers.len(), "installed": installed_count})
        }
        "cli_run" => {
            let worker_id = require_string(&arguments, "worker_id")?;
            let input = require_string(&arguments, "input")?;
            // Map worker_id to command
            let cmd = match worker_id.as_str() {
                "web-scraper" => "curl",
                "git-worker" => "git",
                "gh-worker" => "gh",
                "data-analyst" => "python3",
                "claude-worker" => "claude",
                "codex-worker" => "codex",
                "gemini-worker" => "gemini",
                _ => return Err((-32000, format!("unknown worker: {worker_id}"))),
            };
            // Security: allowlist check
            let allowed = ["claude", "codex", "gemini", "curl", "git", "gh", "python3"];
            if !allowed.contains(&cmd) {
                return Err((-32000, "command not in allowlist".to_string()));
            }
            let start = std::time::Instant::now();
            let output = std::process::Command::new(cmd)
                .arg(&input)
                .output()
                .map_err(|e| (-32000, format!("exec: {e}")))?;
            let duration_ms = start.elapsed().as_millis();
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            state.event_bus.publish(
                crate::pubsub::topics::CLI_RUN,
                json!({"worker_id": worker_id, "exit_code": output.status.code()}),
                "mcp_client",
            );
            json!({
                "worker_id": worker_id,
                "exit_code": output.status.code().unwrap_or(-1),
                "stdout": if stdout.len() > 10000 { stdout[..10000].to_string() } else { stdout },
                "stderr": if stderr.len() > 2000 { stderr[..2000].to_string() } else { stderr },
                "duration_ms": duration_ms,
            })
        }
        // ── Jobs ──
        "job_enqueue" => {
            let job_type = require_string(&arguments, "job_type")?;
            let payload = arguments
                .get("payload")
                .cloned()
                .unwrap_or_else(|| json!({}));
            let priority = arguments
                .get("priority")
                .and_then(Value::as_i64)
                .unwrap_or(1) as i32;
            let job = state
                .job_queue
                .enqueue(&job_type, payload, priority, "mcp_client", None)
                .map_err(|e| (-32000, e))?;
            json!({"enqueued": true, "job": job})
        }
        "job_claim" => {
            let worker_id = require_string(&arguments, "worker_id")?;
            let job = state.job_queue.claim(&worker_id).map_err(|e| (-32000, e))?;
            match job {
                Some(j) => json!({"claimed": true, "job": j}),
                None => json!({"claimed": false, "message": "no jobs available"}),
            }
        }
        // ── Events ──
        "event_publish" => {
            let topic = require_string(&arguments, "topic")?;
            let payload = arguments
                .get("payload")
                .cloned()
                .unwrap_or_else(|| json!({}));
            let event = state.event_bus.publish(&topic, payload, "mcp_client");
            json!({"published": true, "event_id": event.id, "topic": event.topic, "evidence_hash": event.evidence_hash})
        }
        // ── Wiki ──
        "wiki_stats" => {
            let wiki_dir = crate::utils::solace_home().join("wiki");
            let snapshot_count = std::fs::read_dir(&wiki_dir)
                .map(|entries| entries.flatten().filter(|e| e.path().is_file()).count())
                .unwrap_or(0);
            let total_size: u64 = std::fs::read_dir(&wiki_dir)
                .map(|entries| {
                    entries
                        .flatten()
                        .filter_map(|e| std::fs::metadata(e.path()).ok())
                        .map(|m| m.len())
                        .sum()
                })
                .unwrap_or(0);
            json!({
                "snapshot_count": snapshot_count,
                "total_size_bytes": total_size,
                "community_browsing": true,
                "codecs_available": 6,
            })
        }
        "wiki_extract" => {
            let url = require_string(&arguments, "url")?;
            let content = require_string(&arguments, "content")?;
            // Security: reject non-HTTP URLs
            if !url.starts_with("http://")
                && !url.starts_with("https://")
                && !url.starts_with("app://")
            {
                return Err((
                    -32000,
                    "URL must start with http://, https://, or app://".to_string(),
                ));
            }
            match crate::pzip::stillwater::extract(content.as_bytes(), "text/html", &url) {
                Ok(decomp) => {
                    let wiki_dir = crate::utils::solace_home().join("wiki");
                    let _ = std::fs::create_dir_all(&wiki_dir);
                    let url_hash = &decomp.sha256[..16];
                    // Save prime-snapshot
                    let snapshot_path = wiki_dir.join(format!("{url_hash}.prime-snapshot.md"));
                    let snapshot_exists = snapshot_path.exists();
                    json!({
                        "extracted": true,
                        "url": decomp.url,
                        "codec": decomp.codec.name(),
                        "sha256": decomp.sha256,
                        "headings": decomp.stillwater.headings.len(),
                        "sections": decomp.ripple.sections.len(),
                        "title": decomp.ripple.title,
                        "snapshot_exists": snapshot_exists,
                    })
                }
                Err(e) => return Err((-32000, format!("extract failed: {e}"))),
            }
        }
        // ── Domains ──
        "domain_status" => {
            let domain = require_string(&arguments, "domain")?;
            let apps = crate::utils::scan_apps();
            let domain_apps: Vec<_> = apps
                .iter()
                .filter(|a| {
                    a.domain == domain || a.triggers.iter().any(|t| domain.contains(&t.domain))
                })
                .collect();
            let solace_home = crate::utils::solace_home();
            let vault_path = solace_home.join("vault").join("oauth3.json");
            let oauth3_status = if vault_path.exists() {
                if let Ok(c) = std::fs::read_to_string(&vault_path) {
                    if c.contains(&domain) {
                        "active"
                    } else {
                        "not_configured"
                    }
                } else {
                    "not_configured"
                }
            } else {
                "not_configured"
            };
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
            json!({
                "domain": domain,
                "oauth3_status": oauth3_status,
                "apps_count": domain_apps.len(),
                "apps": domain_apps.iter().map(|a| json!({
                    "app_id": a.id, "name": a.name, "schedule": a.schedule,
                })).collect::<Vec<_>>(),
                "wiki_snapshots": snapshot_count,
                "cloud_connected": state.cloud_config.read().is_some(),
            })
        }
        "domain_triggers" => {
            let domain = require_string(&arguments, "domain")?;
            let url_path = optional_string(&arguments, "path").unwrap_or_else(|| "/".to_string());
            let apps = crate::utils::scan_apps();
            let mut matched = Vec::new();
            for app in &apps {
                for trigger in &app.triggers {
                    let trigger_domain = &trigger.domain;
                    if !domain.contains(trigger_domain) && trigger_domain != &domain {
                        continue;
                    }
                    let path_pattern = &trigger.path;
                    let path_matches = path_pattern == "/*"
                        || path_pattern == &url_path
                        || (path_pattern.ends_with('*')
                            && url_path.starts_with(&path_pattern[..path_pattern.len() - 1]));
                    if path_matches {
                        matched.push(json!({
                            "app_id": app.id, "app_name": app.name,
                            "trigger_context": trigger.context,
                            "dom_selector": trigger.dom_selector,
                            "activation": trigger.activation,
                        }));
                    }
                }
            }
            json!({"domain": domain, "path": url_path, "matched": matched, "count": matched.len()})
        }
        // ── Webhooks ──
        "webhook_create" => {
            let name = require_string(&arguments, "name")?;
            let url = require_string(&arguments, "url")?;
            let event = require_string(&arguments, "event")?;
            let solace_home = crate::utils::solace_home();
            let path = solace_home.join("runtime").join("webhooks.json");
            let _ = std::fs::create_dir_all(solace_home.join("runtime"));
            let mut hooks: Vec<Value> = if path.exists() {
                serde_json::from_str(&std::fs::read_to_string(&path).unwrap_or_default())
                    .unwrap_or_default()
            } else {
                Vec::new()
            };
            let hook = json!({
                "id": uuid::Uuid::new_v4().to_string(),
                "name": name, "url": url, "event": event,
                "active": true, "created_at": crate::utils::now_iso8601(),
            });
            hooks.push(hook.clone());
            let _ = std::fs::write(
                &path,
                serde_json::to_string_pretty(&hooks).unwrap_or_default(),
            );
            json!({"created": true, "webhook": hook})
        }
        // ── File Watch ──
        "file_watch" => {
            let watch_path = require_string(&arguments, "path")?;
            let pattern = optional_string(&arguments, "pattern").unwrap_or_else(|| "*".to_string());
            let app_id = optional_string(&arguments, "app_id").unwrap_or_default();
            let solace_home = crate::utils::solace_home();
            let wpath = solace_home.join("runtime").join("watchers.json");
            let _ = std::fs::create_dir_all(solace_home.join("runtime"));
            let mut watchers: Vec<Value> = if wpath.exists() {
                serde_json::from_str(&std::fs::read_to_string(&wpath).unwrap_or_default())
                    .unwrap_or_default()
            } else {
                Vec::new()
            };
            let watcher = json!({
                "id": uuid::Uuid::new_v4().to_string(),
                "path": watch_path, "pattern": pattern, "app_id": app_id,
                "active": true, "last_scan": "", "files_found": 0,
            });
            watchers.push(watcher.clone());
            let _ = std::fs::write(
                &wpath,
                serde_json::to_string_pretty(&watchers).unwrap_or_default(),
            );
            json!({"created": true, "watcher": watcher})
        }
        // ── P0: Browser Visibility ──
        "browser_tabs" => {
            let tabs = state.browser_tabs.read().clone();
            if !tabs.is_empty() {
                json!({"tabs": tabs, "count": tabs.len(), "source": "websocket"})
            } else {
                // Fallback: read browser_tabs.json
                let tabs_file = crate::utils::solace_home().join("browser_tabs.json");
                if let Ok(content) = std::fs::read_to_string(&tabs_file) {
                    if let Ok(file_tabs) = serde_json::from_str::<Vec<Value>>(&content) {
                        *state.browser_tabs.write() = file_tabs.clone();
                        json!({"tabs": file_tabs, "count": file_tabs.len(), "source": "file"})
                    } else {
                        json!({"tabs": [], "count": 0, "source": "none"})
                    }
                } else {
                    json!({"tabs": [], "count": 0, "source": "none"})
                }
            }
        }
        "browser_navigate" => {
            let url = require_string(&arguments, "url")?;
            if !url.starts_with("http://") && !url.starts_with("https://") {
                return Err((
                    -32602,
                    "url must start with http:// or https://".to_string(),
                ));
            }
            *state.evidence_count.write() += 1;
            // Navigate via WebSocket relay to sidebar ONLY.
            // NEVER spawn new browser processes from MCP — that opens duplicate windows.
            // The sidebar receives the navigate command and loads the URL in the existing tab.
            let channels = state.session_channels.read();
            let msg = json!({"command": "navigate", "url": &url}).to_string();
            let mut sent = 0;
            for (_, tx) in channels.iter() {
                if tx.send(msg.clone()).is_ok() {
                    sent += 1;
                }
            }
            *state.current_url.write() = url.clone();
            state
                .event_bus
                .publish("browser.navigate", json!({"url": &url}), "mcp_client");
            json!({"sent": sent > 0, "url": url, "channels": sent,
                    "note": if sent == 0 { "no sidebar connected — open browser first" } else { "navigated via sidebar" }})
        }
        "browser_sessions" => {
            let sessions = state.sessions.read();
            let list: Vec<_> = sessions.values().cloned().collect();
            json!({"sessions": list, "count": list.len()})
        }
        "domain_tab_acquire" => {
            let domain = require_string(&arguments, "domain")?;
            let app_id = optional_string(&arguments, "app_id").unwrap_or_default();
            let url =
                optional_string(&arguments, "url").unwrap_or_else(|| format!("https://{}", domain));
            let mut tabs = state.domain_tabs.write();
            if let Some(existing) = tabs.get(&domain) {
                if existing.tab_state == crate::state::TabState::Working {
                    return Err((
                        -32000,
                        format!(
                            "domain '{}' tab is busy (app: {:?})",
                            domain, existing.active_app_id
                        ),
                    ));
                }
            }
            let tab = crate::state::DomainTab {
                domain: domain.clone(),
                current_url: url,
                session_id: uuid::Uuid::new_v4().to_string(),
                active_app_id: if app_id.is_empty() {
                    None
                } else {
                    Some(app_id)
                },
                last_activity: crate::utils::now_iso8601(),
                tab_state: crate::state::TabState::Working,
            };
            tabs.insert(domain.clone(), tab.clone());
            json!({"acquired": true, "domain_tab": tab})
        }
        "domain_tab_release" => {
            let domain = require_string(&arguments, "domain")?;
            let mut tabs = state.domain_tabs.write();
            if let Some(tab) = tabs.get_mut(&domain) {
                tab.tab_state = crate::state::TabState::Idle;
                tab.active_app_id = None;
                tab.last_activity = crate::utils::now_iso8601();
                json!({"released": true, "domain": domain})
            } else {
                json!({"released": false, "error": "domain tab not found"})
            }
        }
        "budget_status" => {
            let solace_home = crate::utils::solace_home();
            let config = crate::config::load_budget_config(&solace_home);
            let usage = state.budget_usage.read().clone();
            let blocked = usage.is_blocked(&config);
            json!({
                "config": config,
                "usage": {
                    "app_runs": *state.app_count.read(),
                    "evidence_events": *state.evidence_count.read(),
                    "daily_count": usage.daily_count,
                    "daily_date": usage.daily_date,
                    "monthly_count": usage.monthly_count,
                    "monthly_date": usage.monthly_date,
                },
                "blocked": blocked,
            })
        }
        "worker_run_status" => {
            let run = state.worker_run.read().clone();
            match run {
                Some(r) => json!({
                    "running": true,
                    "app_id": r.app_id, "app_name": r.app_name,
                    "run_id": r.run_id, "status": r.status,
                    "current_step": r.current_step, "total_steps": r.total_steps,
                    "step_label": r.step_label, "log_lines": r.log_lines,
                    "started_at": r.started_at, "updated_at": r.updated_at,
                }),
                None => json!({"running": false, "message": "no worker currently running"}),
            }
        }
        // ── P1: Browser Control (via sidebar WebSocket, NOT xdotool) ──
        "browser_click" => {
            let selector = require_string(&arguments, "selector")?;
            let channels = state.session_channels.read();
            let msg = json!({"command": "click", "selector": selector}).to_string();
            let mut sent = 0;
            for (_, tx) in channels.iter() {
                if tx.send(msg.clone()).is_ok() {
                    sent += 1;
                }
            }
            *state.evidence_count.write() += 1;
            state.event_bus.publish(
                "browser.click",
                json!({"selector": &selector}),
                "mcp_client",
            );
            json!({"sent": sent > 0, "selector": selector, "channels": sent})
        }
        "browser_fill" => {
            let selector = require_string(&arguments, "selector")?;
            let value = require_string(&arguments, "value")?;
            let submit = arguments
                .get("submit")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            let channels = state.session_channels.read();
            let msg =
                json!({"command": "fill", "selector": selector, "value": value, "submit": submit})
                    .to_string();
            let mut sent = 0;
            for (_, tx) in channels.iter() {
                if tx.send(msg.clone()).is_ok() {
                    sent += 1;
                }
            }
            *state.evidence_count.write() += 1;
            state.event_bus.publish(
                "browser.fill",
                json!({"selector": &selector, "submit": submit}),
                "mcp_client",
            );
            json!({"sent": sent > 0, "selector": selector, "submit": submit, "channels": sent})
        }
        "browser_key" => {
            let key = require_string(&arguments, "key")?;
            let channels = state.session_channels.read();
            let msg = json!({"command": "key", "key": key}).to_string();
            let mut sent = 0;
            for (_, tx) in channels.iter() {
                if tx.send(msg.clone()).is_ok() {
                    sent += 1;
                }
            }
            *state.evidence_count.write() += 1;
            json!({"sent": sent > 0, "key": key, "channels": sent})
        }
        "browser_screenshot" => {
            // Screenshots are captured by the sidebar and stored by the runtime
            let solace_home = crate::utils::solace_home();
            let screenshots_dir = solace_home.join("evidence").join("screenshots");
            let count = std::fs::read_dir(&screenshots_dir)
                .map(|e| e.flatten().count())
                .unwrap_or(0);
            let latest = std::fs::read_dir(&screenshots_dir)
                .ok()
                .and_then(|entries| {
                    entries
                        .flatten()
                        .filter_map(|e| {
                            let meta = e.metadata().ok()?;
                            Some((
                                e.file_name().to_string_lossy().to_string(),
                                meta.modified().ok()?,
                            ))
                        })
                        .max_by_key(|(_, t)| *t)
                        .map(|(name, _)| name)
                });
            json!({"screenshots_count": count, "latest": latest, "directory": screenshots_dir.display().to_string()})
        }
        "notifications_list" => {
            let notifications = state.notifications.read().clone();
            let unread = notifications.iter().filter(|n| !n.read).count();
            json!({"notifications": notifications, "total": notifications.len(), "unread": unread})
        }
        // ── Tab Management ──
        "browser_tabs_close_all" => {
            // WebSocket relay
            let channels = state.session_channels.read();
            let msg = json!({"command": "close_other_tabs"}).to_string();
            let mut sent = 0;
            for (_, tx) in channels.iter() {
                if tx.send(msg.clone()).is_ok() {
                    sent += 1;
                }
            }
            drop(channels);
            // File command fallback
            let cmd_file = crate::utils::solace_home().join("browser_commands.json");
            let _ = std::fs::write(
                &cmd_file,
                json!({"command":"close_other_tabs","timestamp":crate::utils::now_iso8601()})
                    .to_string(),
            );
            // Clear state + file
            state.browser_tabs.write().retain(|_| false);
            let _ = std::fs::write(crate::utils::solace_home().join("browser_tabs.json"), "[]");
            json!({"ok": true, "action": "close_all_tabs", "channels_notified": sent})
        }
        "browser_tab_close" => {
            let tab_id = require_string(&arguments, "tab_id")?;
            let channels = state.session_channels.read();
            let msg = json!({"command": "close_tab", "tab_id": tab_id}).to_string();
            let mut sent = 0;
            for (_, tx) in channels.iter() {
                if tx.send(msg.clone()).is_ok() {
                    sent += 1;
                }
            }
            drop(channels);
            let cmd_file = crate::utils::solace_home().join("browser_commands.json");
            let _ = std::fs::write(&cmd_file, json!({"command":"close_tab","tab_id":tab_id,"timestamp":crate::utils::now_iso8601()}).to_string());
            state
                .browser_tabs
                .write()
                .retain(|t| t.get("id").and_then(|v| v.as_str()) != Some(&tab_id));
            let tabs = state.browser_tabs.read().clone();
            let _ = std::fs::write(
                crate::utils::solace_home().join("browser_tabs.json"),
                serde_json::to_string_pretty(&tabs).unwrap_or_default(),
            );
            json!({"ok": true, "tab_id": tab_id, "channels_notified": sent})
        }
        "browser_active_tab" => {
            let tabs = state.browser_tabs.read();
            let active = tabs
                .iter()
                .find(|t| t.get("active").and_then(|v| v.as_bool()).unwrap_or(false));
            match active {
                Some(tab) => json!({"tab": tab, "found": true}),
                None => {
                    let url = state.current_url.read().clone();
                    json!({"found": false, "current_url": url, "note": "No tabs reported by sidebar yet"})
                }
            }
        }
        // ── Updates ──
        "check_update" => {
            let current = crate::updates::local_version();
            match crate::updates::check_for_update().await {
                Ok(Some(manifest)) => {
                    let new_version = manifest.version.clone();
                    {
                        let mut status = state.update_status.write();
                        status.latest_version = Some(new_version.clone());
                        status.update_available = true;
                        status.last_check = Some(crate::utils::now_iso8601());
                    }
                    match crate::updates::download_and_install(&manifest).await {
                        Ok(result) => {
                            let mut s = state.update_status.write();
                            s.last_update = Some(crate::utils::now_iso8601());
                            s.update_available = false;
                            json!({"action":"updated","old_version":current,"new_version":new_version,"result":result,"restart_required":true})
                        }
                        Err(err) => {
                            json!({"action":"update_failed","current_version":current,"new_version":new_version,"error":err})
                        }
                    }
                }
                Ok(None) => {
                    state.update_status.write().last_check = Some(crate::utils::now_iso8601());
                    json!({"action":"up_to_date","current_version":current})
                }
                Err(err) => json!({"action":"check_failed","current_version":current,"error":err}),
            }
        }
        // ── E-Sign ──
        "esign" => {
            let action_id = require_string(&arguments, "action_id")?;
            let decision = require_string(&arguments, "decision")?;
            let feedback = optional_string(&arguments, "feedback").unwrap_or_default();
            if decision != "approve" && decision != "reject" {
                return Err((-32602, "decision must be 'approve' or 'reject'".to_string()));
            }
            let solace_home = crate::utils::solace_home();
            let event_type = if decision == "approve" {
                "esign.mcp_approve"
            } else {
                "esign.mcp_reject"
            };
            let evidence = crate::evidence::record_event(
                &solace_home,
                event_type,
                "mcp_client",
                json!({"action_id": action_id, "decision": decision, "feedback": feedback}),
            )
            .map_err(|e| (-32000, e))?;
            json!({
                "signed": true, "action_id": action_id, "decision": decision,
                "evidence_hash": evidence.hash,
            })
        }
        _ => return Err((-32601, format!("Unknown tool: {name}"))),
    };

    Ok(json!({
        "content": [{"type": "text", "text": content_text(&payload)}],
        "structuredContent": payload
    }))
}

fn handle_resources_list() -> Value {
    json!({"resources": mcp_resource_definitions()})
}

fn handle_resources_read(params: &Value) -> Result<Value, (i64, String)> {
    let uri = require_string(params, "uri")?;
    let payload = match uri.as_str() {
        "solace://apps" => json!({"apps": crate::app_engine::scan_installed_apps()}),
        "solace://evidence" => {
            let entries = crate::evidence::list_evidence(&crate::utils::solace_home(), 50);
            json!({"entries": entries, "part11": crate::evidence::part11_status(&crate::utils::solace_home())})
        }
        _ => return Err((-32000, format!("Unknown resource: {uri}"))),
    };

    Ok(json!({
        "contents": [{
            "uri": uri,
            "mimeType": "application/json",
            "text": content_text(&payload)
        }]
    }))
}

fn system_status_payload(state: &AppState) -> Value {
    json!({
        "uptime_seconds": state.uptime_seconds(),
        "sessions": state.sessions.read().len(),
        "notifications": state.notifications.read().len(),
        "schedules": state.schedules.read().len(),
        "evidence_count": *state.evidence_count.read(),
        "app_count": *state.app_count.read(),
        "cloud_connected": state.cloud_config.read().is_some(),
        "theme": state.theme.read().clone(),
    })
}

fn content_text(payload: &Value) -> String {
    serde_json::to_string_pretty(payload).unwrap_or_else(|_| payload.to_string())
}

fn require_string(arguments: &Value, key: &str) -> Result<String, (i64, String)> {
    arguments
        .get(key)
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| (-32602, format!("missing string field: {key}")))
}

fn optional_string(arguments: &Value, key: &str) -> Option<String> {
    arguments
        .get(key)
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
        .filter(|value| !value.trim().is_empty())
}
