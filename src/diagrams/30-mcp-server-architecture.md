# Diagram 30: MCP Server Architecture — Dynamic App-to-Tool Mapping
# DNA: `mcp(discover, generate, route, gate) > hardcoded(drift, stale, fragile)`
# Forbidden: `HARDCODED_TOOLS | ORPHAN_API | ORPHAN_TOOL | UNGATED_MCP | TRADE_SECRET_LEAK`
# Paper: 47 §24 | Auth: 65537

```mermaid
graph TB
    subgraph AI_Agents["AI Coding Agents"]
        CC[Claude Code]
        CX[Codex]
        GC[Gemini CLI]
        CU[Cursor / Windsurf]
    end

    subgraph MCP_Layer["MCP Server (stdio / SSE)"]
        TL["tools/list<br/>(dynamic registry)"]
        TC["tools/call<br/>(route to handler)"]
        OG["OAuth3 Gate<br/>(scope check)"]
    end

    subgraph Tool_Registry["Dynamic Tool Registry"]
        CT["Core Browser Tools<br/>navigate, screenshot, click,<br/>type, scroll, snapshot"]
        AT["App Tools (Dynamic)<br/>Generated from manifests<br/>25 apps → 75 tools"]
        MT["Model + Evidence Tools<br/>list_models, benchmarks,<br/>search_evidence, verify"]
    end

    subgraph Shared_Handlers["Shared Handler Layer"]
        SH["browser_server methods<br/>(same code for HTTP + MCP)"]
    end

    subgraph Manifests["App Manifests"]
        M1["gmail-inbox-triage/<br/>manifest.yaml"]
        M2["linkedin-poster/<br/>manifest.yaml"]
        M3["...24 more apps"]
    end

    subgraph Browser["Solace Browser (Chromium)"]
        PW[Playwright Engine]
        WS["Webservice :9222<br/>(HTTP + WebSocket)"]
        YY["Yinyang Sidebar<br/>(Chrome Extension)"]
    end

    CC -->|stdio| TL
    CX -->|stdio| TL
    GC -->|stdio| TL
    CU -->|SSE| TL

    CC -->|stdio| TC
    CX -->|stdio| TC

    TL --> CT
    TL --> AT
    TL --> MT

    AT -.->|reads| M1
    AT -.->|reads| M2
    AT -.->|reads| M3

    TC --> OG
    OG -->|authorized| SH

    SH --> PW
    SH --> WS

    WS <-->|same handlers| SH
    YY <-->|HTTP/WS| WS

    classDef agent fill:#4A90D9,color:white
    classDef mcp fill:#7B68EE,color:white
    classDef tools fill:#2ECC71,color:white
    classDef handler fill:#F39C12,color:white
    classDef manifest fill:#95A5A6,color:white
    classDef browser fill:#E74C3C,color:white

    class CC,CX,GC,CU agent
    class TL,TC,OG mcp
    class CT,AT,MT tools
    class SH handler
    class M1,M2,M3 manifest
    class PW,WS,YY browser
```

## Key Architecture Properties

| Property | Implementation |
|----------|---------------|
| **Zero drift** | Tools generated from manifests at runtime |
| **Single handler** | MCP + HTTP both call same browser_server methods |
| **OAuth3 everywhere** | MCP calls scoped same as HTTP calls |
| **Trade secret safe** | Response filtering in shared handler layer |
| **Evidence chain** | Every MCP call produces evidence bundle |
| **Hot reload** | Manifest change → tool list updates (mtime cache) |

## Transport Modes

```mermaid
stateDiagram-v2
    [*] --> stdio: solace-browser mcp
    [*] --> SSE: GET /mcp/sse

    stdio --> Local: Claude Code / Codex
    SSE --> Remote: Through tunnel

    Local --> OAuth3Check
    Remote --> OAuth3Check

    OAuth3Check --> Authorized: scope valid
    OAuth3Check --> Denied: scope missing

    Authorized --> Execute
    Execute --> Evidence: emit bundle
    Evidence --> Response

    Denied --> Error: 403 + required scope
```

## Dynamic Tool Generation Flow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Registry as Tool Registry
    participant Manifests as App Manifests
    participant Handler as Shared Handler
    participant Browser as Chromium

    Agent->>MCP: tools/list
    MCP->>Registry: get_all_tools()
    Registry->>Manifests: read manifest.yaml files
    Manifests-->>Registry: 25 app definitions
    Registry-->>MCP: core(16) + app(75) + evidence(6) = 97 tools
    MCP-->>Agent: tool schemas

    Agent->>MCP: tools/call("solace_app_gmail_inbox_triage_run", {model: "solace_managed"})
    MCP->>Handler: _handle_apps_run("gmail-inbox-triage", ...)
    Handler->>Browser: execute recipe
    Browser-->>Handler: result + evidence
    Handler-->>MCP: {status, recipe, cost}
    MCP-->>Agent: tool result
```
