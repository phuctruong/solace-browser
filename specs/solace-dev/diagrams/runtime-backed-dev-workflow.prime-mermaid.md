---
title: Runtime-Backed Dev Workflow Binding (SAC66)
type: prime-mermaid
---

```mermaid
graph TD
    subgraph `solace-runtime` (Back Office Database)
        P[Project: solace-browser]
        R[Request: SAC66 Binding]
        C[Assignment: Coder]
        Q[Assignment: QA]
        AR[Artifact Record]
        AP[Approval Record]
        
        P --> R
        R --> C
        R --> Q
        C --> AR
        C --> AP
    end

    subgraph `solace-hub` (Dev Workspace)
        W[Worker Workspace: Coder]
        A(Assignment Context Panel)
        I(Inbox Context Panel)
        
        W --> A
        W --> I
        
        C -. "runtime fetch" .-> A
        R -. "runtime fetch" .-> A
        AP -. "runtime fetch" .-> A
        C -. "runtime fetch" .-> I
        AR -. "runtime fetch" .-> I
        AP -. "runtime fetch" .-> I
    end
    
    subgraph `solace-coder` / `localhost`
        E[Run Outbox Artifacts]
        
        A -. "evidence link" .-> E
        I -. "output path" .-> E
    end

    style P fill:#1e293b,stroke:#cbd5e1
    style R fill:#312e81,stroke:#818cf8,color:#fff
    style C fill:#064e3b,stroke:#34d399,color:#fff
    style Q fill:#1e293b,stroke:#64748b,color:#fff
    style W fill:#0f172a,stroke:#3b82f6,color:#fff
```

### Context
Unlike purely role-derived mocks, SAC66 establishes a literal, runtime-backed request/assignment connection. The browser workflow retrieves active assignments, artifacts, and approvals via `GET /api/v1/backoffice/solace-dev-manager/...` endpoints served by `solace-runtime`.

### Outcomes
1. Requests and assignments are durable SQLite records.
2. The UI handles both `seeded` (connected) and `fallback` (disconnected) states.
3. Assignment-linked artifact and approval records are visible in the same workflow chain.
