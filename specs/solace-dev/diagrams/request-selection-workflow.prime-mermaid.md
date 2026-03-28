---
title: Manager Request Selection Workflow (SAC67)
type: prime-mermaid
---

```mermaid
graph TD
    subgraph `solace-runtime` (Back Office)
        P[Project: solace-browser]
        R1[Request A: SAC66]
        R2[Request B: SAC67]
        A1[Assignment A]
        A2[Assignment B]
        
        P --> R1
        P --> R2
        R1 --> A1
        R2 --> A2
    end

    subgraph `solace-hub` (Dev Workspace)
        F[Manager Action: New Request]
        S[Active Workflow Selector]
        
        W[Worker Panel Context]
        I[Worker Inbox Context]
        
        F -. "POST /requests" .-> R2
        S -. "GET /requests" .-> R2
        S -- "Active Request = Request B" --> W
        S -- "Active Request = Request B" --> I
        
        A2 -. "find(req_b + role)" .-> W
        A2 -. "find(req_b + role)" .-> I
    end

    style P fill:#1e293b,stroke:#cbd5e1
    style R2 fill:#312e81,stroke:#818cf8,color:#fff
    style A2 fill:#064e3b,stroke:#34d399,color:#fff
    style F fill:#d946ef,stroke:#fdf4ff,color:#000
    style S fill:#0f172a,stroke:#3b82f6,color:#fff
```

### Context
In SAC67, the Hub workspace transcends generic assignment fetches. The Dev Manager natively creates new request packets straight into the `solace-runtime` API. These requests are then hydrated into an active workflow selection bound to `window.__solaceActiveRequestId`.

### Truth Binding
By explicitly selecting a workflow, downstream role components (Assignment Packet, Inbox/Outbox) dynamically filter local API results down to only the assignment objects mapped directly to the selected `request_id`.
