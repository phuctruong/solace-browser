---
title: Manager Execution Launch Workflow (SAC69)
type: prime-mermaid
---

```mermaid
graph TD
    subgraph `solace-runtime` (Back Office)
        R1[Request D]
        A1[Assignment D: qa]
        T1[App Run Endpoint: /api/v1/apps/run/solace-qa]
        
        R1 -. "Target Role: qa" .-> A1
        A1 -. "Execute Route" .-> T1
    end

    subgraph `solace-hub` (Dev Workspace)
        S[Active Workflow Selector]
        M[Manager Action: Deploy Assignment]
        L[Manager Action: Launch Routed Flow]
        O[Run ID Context Output]
        
        S -- "Selected Request D" --> M
        M -- "POST /assignments" --> A1
        S -- "If A1 exists" --> L
        L -- "POST /api/v1/apps/run/solace-qa" --> T1
        T1 -- "Returns Status" --> O
    end

    style R1 fill:#312e81,stroke:#818cf8,color:#fff
    style A1 fill:#064e3b,stroke:#34d399,color:#fff
    style T1 fill:#991b1b,stroke:#fca5a5,color:#fff
    style S fill:#0f172a,stroke:#3b82f6,color:#fff
    style M fill:#d946ef,stroke:#fdf4ff,color:#000
    style L fill:#10b981,stroke:#6ee7b7,color:#000
    style O fill:#000000,stroke:#4ade80,color:#4ade80
```

### Context
In SAC69, the final connection is established. After a Manager natively creates a Request (SAC67) and intrinsically routes a target Assignment (SAC68), the manager now drives the native Run execution loop from Hub directly into `solace-runtime` (SAC69).

### Truth Binding
The `__solaceLaunchRoutedFlow` explicitly prevents execution unless the selected Request legitimately possesses an actively routed assignment. It first tries to resolve the manager's explicitly selected route role for the active request; only then does it fall back to the first active assignment. It interrogates the mapping (`DEV_ROLES`) to convert the `target_role` dynamically to an `appId`, and triggers `fetch('/api/v1/apps/run/' + appId)`. The generated visual block surfaces HTTP boundaries transparently rather than obfuscating them.
