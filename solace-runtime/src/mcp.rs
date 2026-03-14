use serde_json::{json, Value};

pub fn mcp_tool_definitions() -> Vec<Value> {
    vec![
        json!({"name": "run_app", "description": "Run a Solace app by ID"}),
        json!({"name": "list_apps", "description": "List installed apps"}),
        json!({"name": "browser_launch", "description": "Launch browser session"}),
        json!({"name": "evidence_list", "description": "List evidence entries"}),
    ]
}
