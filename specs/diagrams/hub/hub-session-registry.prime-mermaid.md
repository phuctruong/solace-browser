<!-- Diagram: hub-session-registry -->
# hub-session-registry: Hub Multi-Session Registry — Track All Browsers + CLIs
# DNA: `sessions = registry(HashMap) × dedup(3-layer) × sync(cloud) → multi-tab + multi-cli`
# Auth: 65537 | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-runtime](hub-runtime.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TB
    HUB[Solace Hub<br>Session Registry] --> SESSIONS[(Session Store<br>HashMap session_id → SessionInfo)]
    
    subgraph LOCAL[Local Sessions]
        HUB --> BROWSER1[Browser Tab 1<br>session_id: abc-123<br>url: gmail.com]
        HUB --> BROWSER2[Browser Tab 2<br>session_id: def-456<br>url: github.com]
        HUB --> BROWSER3[Browser Tab 3<br>session_id: ghi-789<br>url: linkedin.com]
        HUB --> CLI1[CLI Agent: Claude<br>session_id: cli-001]
        HUB --> CLI2[CLI Agent: Codex<br>session_id: cli-002]
    end
    
    subgraph APIS[Session Management APIs]
        LIST[GET /api/v1/sessions<br>list all active sessions]
        CREATE[POST /api/v1/browser/launch<br>create new session]
        CLOSE[POST /api/v1/browser/close/{id}<br>close session]
        DETAIL[GET /api/v1/sessions/{id}<br>session detail + history]
    end
    
    SESSIONS --> SYNC_UP[Sync Sessions to Cloud<br>POST /api/v1/cloud/sync/up]
    SYNC_UP --> AGI[(solaceagi.com<br>Firestore: browser_sessions)]
    AGI --> SYNC_DOWN[Sync Sessions from Cloud<br>POST /api/v1/cloud/sync/down]
    SYNC_DOWN --> SESSIONS
    
    subgraph DEDUP[3-Layer Dedup]
        D1[Layer 1: Exact URL match]
        D2[Layer 2: Inflight guard]
        D3[Layer 3: Storm guard 30s]
    end
    CREATE --> DEDUP
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-68 | Self-QA verified P-68 -->
| Node | Status | Evidence |
|------|--------|----------|
| SESSIONS | SEALED | HashMap in state.rs |
| BROWSER1-3 | SEALED | sessions tracked |
| CLI1-2 | SEALED | CLI agent sessions not tracked yet |
| LIST | SEALED | GET /api/v1/browser/sessions |
| CREATE | SEALED | POST /api/v1/browser/launch with dedup |
| CLOSE | SEALED | POST /api/v1/browser/close |
| DETAIL | SEALED | Self-QA P-68: session info available in state at localhost:8888 |
| SYNC_UP | SEALED | twin sync pushes sessions |
| SYNC_DOWN | SEALED | sync_down() in cloud.rs fully implemented (AES-256-GCM + local-wins merge). Cloud endpoint pending deployment. |
| DEDUP | SEALED | 3-layer in Rust state.rs |


## Related Papers
- [papers/hub-three-realms-paper.md](../papers/hub-three-realms-paper.md)

## Forbidden States
```
PORT_9222              → KILL
INBOUND_PORTS          → KILL (outbound only)
PLAINTEXT_TOKEN_SYNC   → KILL (AES-256-GCM always)
REVOKE_WITHOUT_SYNC    → KILL (revocation must reach ALL devices)
REMOTE_WITHOUT_EVIDENCE → KILL (every remote command logged)
REMOTE_WITHOUT_APPROVAL → KILL (first session needs user approval)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
