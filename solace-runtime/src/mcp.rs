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

        if stdout.write_all(response.to_string().as_bytes()).await.is_err() {
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
    let arguments = params.get("arguments").cloned().unwrap_or_else(|| json!({}));

    let payload = match name {
        "run_app" => {
            let app_id = require_string(&arguments, "app_id")?;
            serde_json::to_value(crate::app_engine::runner::run_app(&app_id, state).await.map_err(|error| (-32000, error))?)
                .map_err(|error| (-32000, error.to_string()))?
        }
        "list_apps" => json!({"apps": crate::app_engine::scan_installed_apps()}),
        "browser_launch" => {
            let session = SessionInfo {
                session_id: uuid::Uuid::new_v4().to_string(),
                profile: optional_string(&arguments, "profile").unwrap_or_else(|| "default".to_string()),
                url: optional_string(&arguments, "url").unwrap_or_else(|| "https://solaceagi.com".to_string()),
                pid: rand::random::<u32>() % 89_999 + 10_000,
                started_at: crate::utils::now_iso8601(),
                mode: optional_string(&arguments, "mode").unwrap_or_else(|| "local-dev".to_string()),
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
            let limit = arguments
                .get("limit")
                .and_then(Value::as_u64)
                .unwrap_or(25) as usize;
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
