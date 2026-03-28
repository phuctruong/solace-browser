---
title: Manager Assignment Routing Workflow (SAC68)
type: prime-mermaid
---

```mermaid
graph TD
    subgraph `solace-runtime` (Back Office)
        P[Project: solace-browser]
        R1[Request C]
        A1[Assignment: design]
        A2[Assignment: coder]
        
        P --> R1
        R1 -. "Manager routing action" .-> A1
        R1 -. "Manager routing action" .-> A2
    end

    subgraph `solace-hub` (Dev Workspace)
        S[Active Workflow Selector]
        M[Manager Action: Deploy Assignment]
        
        AD[Assignment Packet: Design]
        AC[Assignment Packet: Coder]
        
        S -- "Selects Request C" --> M
        M -- "POST /assignments (target_role=design)" --> A1
        M -- "POST /assignments (target_role=coder)" --> A2
        
        A1 -- "Hydrates Workspace" --> AD
        A2 -- "Hydrates Workspace" --> AC
    end

    style P fill:#1e293b,stroke:#cbd5e1
    style R1 fill:#312e81,stroke:#818cf8,color:#fff
    style A1 fill:#064e3b,stroke:#34d399,color:#fff
    style A2 fill:#064e3b,stroke:#34d399,color:#fff
    style M fill:#d946ef,stroke:#fdf4ff,color:#000
    style S fill:#0f172a,stroke:#3b82f6,color:#fff
```

### Context
In SAC68, the Manager takes back control of assignment routing. When a new request is created, it is no longer auto-bound to a `coder` assignment. Instead, the Manager explicitly chooses target roles (`design`, `coder`, `qa`) from a dropdown and explicitly deploys work assignments that attach to the tracked `__solaceActiveRequestId`.

### Truth Binding
By explicitly routing roles to requests, the `dev-active-workflow-routes` UI can render honest downstream expectations against Back Office `assignments`. Routing now behaves as `create or activate`: if a matching request/role assignment already exists it is re-activated through the Back Office update path; otherwise a new assignment is created. If a role has not been routed for a given request, the workspace will honestly degrade into fallback state `disconnected / fallback mock` for that specialist rather than surfacing hallucinated assignments.
