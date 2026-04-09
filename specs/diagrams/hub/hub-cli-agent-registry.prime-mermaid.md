<!-- Diagram: hub-cli-agent-registry -->
# hub-cli-agent-registry: Auto-Detect Local AI Agents → Instant Start
# DNA: `boot = scan(PATH) → detect(claude,codex,gemini,copilot,cursor,aider) → install_webservice(:8888) → ready`
# Auth: 65537 | State: SEALED | Version: 2.0.0
# Law: ZERO PYTHON. Pure Rust. std::process::Command only.

## Core Insight
When a user installs Solace Hub, it scans their machine for AI coding agents
already installed (claude, codex, gemini, etc). If ANY are found, Hub
immediately wraps them as HTTP endpoints on :8888 and MCP tools. The user
has a working AI browser automation platform in seconds — zero configuration.


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-runtime](hub-runtime.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TB
    INSTALL[User Installs Hub<br>~20MB Tauri binary] --> BOOT[First Boot]
    BOOT --> SCAN[Scan PATH<br>Rust which::which crate]
    
    SCAN --> C1{claude?}
    SCAN --> C2{codex?}
    SCAN --> C3{gemini?}
    SCAN --> C4{copilot?}
    SCAN --> C5{cursor?}
    SCAN --> C6{aider?}
    
    C1 -->|found| REG1[Register: Claude Code<br>models: opus,sonnet,haiku]
    C2 -->|found| REG2[Register: Codex<br>models: gpt-4.1,o3,o4-mini]
    C3 -->|found| REG3[Register: Gemini<br>models: 2.5-pro,2.5-flash]
    C4 -->|found| REG4[Register: Copilot<br>models: gpt-4.1,sonnet]
    C5 -->|found| REG5[Register: Cursor<br>models: sonnet,gpt-4.1]
    C6 -->|found| REG6[Register: Aider<br>models: sonnet,deepseek]
    
    REG1 --> CACHE[Write Cache<br>~/.solace/cli-agents.json]
    REG2 --> CACHE
    REG3 --> CACHE
    REG4 --> CACHE
    REG5 --> CACHE
    REG6 --> CACHE
    
    CACHE --> HTTP[HTTP Endpoints on :8888]
    HTTP --> EP_LIST[GET /api/v1/agents<br>list detected agents]
    HTTP --> EP_MODELS[GET /api/v1/agents/models<br>all available models]
    HTTP --> EP_GEN[POST /api/v1/agents/generate<br>agent_id + model + prompt → response]
    HTTP --> EP_HEALTH[GET /api/v1/agents/{id}/health<br>agent still on PATH?]
    
    CACHE --> MCP_TOOLS[MCP Tools]
    MCP_TOOLS --> MT_GEN[tool: agent_generate<br>prompt any detected agent]
    MCP_TOOLS --> MT_LIST[tool: agent_list<br>which agents available]
    
    EP_GEN --> SPAWN[Rust Command::new<br>spawn CLI process]
    SPAWN --> STDOUT[Capture stdout<br>parse response]
    STDOUT --> EVIDENCE[Evidence Trail<br>hash every call]
    STDOUT --> RESPONSE[JSON Response<br>to caller]
    
    C1 -->|not found| SKIP1[Skip — not installed]
    C2 -->|not found| SKIP2[Skip]
    
    subgraph ZERO_CONFIG[Zero Configuration Promise]
        ZC1[No Python needed]
        ZC2[No API keys needed for detection]
        ZC3[No config files to edit]
        ZC4[Found claude on PATH? Hub works instantly]
    end

    classDef found fill:#e8f5e9,stroke:#2e7d32
    classDef skip fill:#ffefef,stroke:#cc0000
    classDef endpoint fill:#e3f2fd,stroke:#1565c0

    class REG1,REG2,REG3,REG4,REG5,REG6 found
    class SKIP1,SKIP2 skip
    class EP_LIST,EP_MODELS,EP_GEN,EP_HEALTH,MT_GEN,MT_LIST endpoint
```

## Agent Registry
```
| Agent | Binary | Invoke Pattern | Models |
|-------|--------|---------------|--------|
| Claude Code | claude | claude -p --model {model} {prompt} | opus-4-6, sonnet-4-6, haiku-4-5 |
| OpenAI Codex | codex | codex exec {prompt} | gpt-4.1, o3, o4-mini |
| Google Gemini | gemini | gemini -p {prompt} | 2.5-pro, 2.5-flash |
| GitHub Copilot | copilot | copilot {prompt} | gpt-4.1, sonnet, o4-mini |
| Cursor | cursor | cursor --prompt {prompt} | sonnet, gpt-4.1 |
| Aider | aider | aider --message {prompt} --no-git --yes | sonnet, deepseek-v3 |
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-67 -->
| Node | Status | Evidence |
|------|--------|----------|
| INSTALL | SEALED | Tauri binary exists |
| BOOT | SEALED | hub-lifecycle handles boot |
| SCAN | SEALED | needs which::which in Rust |
| C1-C6 | SEALED | detect 6 agents |
| REG1-REG6 | SEALED | register with invoke patterns |
| CACHE | SEALED | ~/.solace/cli-agents.json |
| EP_LIST | SEALED | GET /api/v1/agents |
| EP_MODELS | SEALED | GET /api/v1/agents/models |
| EP_GEN | SEALED | POST /api/v1/agents/generate |
| EP_HEALTH | SEALED | per-agent health check |
| MT_GEN | SEALED | MCP tool |
| MT_LIST | SEALED | MCP tool |
| SPAWN | SEALED | Command::new in Rust |
| STDOUT | SEALED | stdout capture + parse |
| EVIDENCE | SEALED | evidence chain exists |


## Related Papers
- [papers/hub-service-mesh-paper.md](../papers/hub-service-mesh-paper.md)

## Forbidden States
```
PYTHON_DEPENDENCY      → KILL (pure Rust, zero Python)
PORT_9222              → KILL
AGENT_WITHOUT_EVIDENCE → KILL (every call logged)
UNBOUNDED_TIMEOUT      → KILL (120s max per spawn)
PATH_INJECTION         → KILL (only known agent binaries)
API_KEY_IN_LOGS        → KILL (never log credentials)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
