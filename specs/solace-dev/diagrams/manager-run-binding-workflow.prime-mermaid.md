---
title: Manager Execution Result Binding Workflow (SAC70)
type: prime-mermaid
---

```mermaid
graph TD
    subgraph `solace-hub` (Dev Workspace)
        S1[Manager Action: Select Request]
        S2[Manager Action: Route Target Role]
        S3[Manager Action: Launch Routed Flow]
        S4[Manager Action / Deep Link: Inspect Run Result]
        
        R[Active Workflow Result Binding]
        
        S1 -- "__solaceActiveRequestId" --> R
        S2 -- "Active Assignment Context" --> R
        S3 -- "__solaceLaunchRoutedFlow" --> R
        S4 -- "sap11: Selected Run Hash" --> R
    end

    subgraph `solace-runtime` (Back Office)
        B1[requests table]
        B2[assignments table]
        B3[apps/runs/ report.html]
        
        R -. "Verify __solaceActiveRequestId" .-> B1
        R -. "Verify Selected Run match" .-> B2
        R -. "Fetch Run Context" .-> B3
    end

    style S1 fill:#0f172a,stroke:#3b82f6,color:#fff
    style S2 fill:#d946ef,stroke:#fdf4ff,color:#000
    style S3 fill:#10b981,stroke:#6ee7b7,color:#000
    style S4 fill:#1e293b,stroke:#818cf8,color:#fff
    style R fill:#78350f,stroke:#fcd34d,color:#fff
    
    style B1 fill:#312e81,stroke:#818cf8,color:#fff
    style B2 fill:#064e3b,stroke:#34d399,color:#fff
    style B3 fill:#991b1b,stroke:#fca5a5,color:#fff
```

### Context
In SAC70, the final linkage is materialized. Previously, users could launch a workflow natively (SAC69), but the executed Run ID would float detached from the active Request or active Assignment context within the UI.

### Truth Binding
By hooking `hydrateActiveWorkflowResult` into both the launch lifecycle and the deep-link/selection `sap11` lifecycle, the Hub now distinguishes between two cases:

1. a stronger workflow-launch session binding saved at launch time with `requestId + assignmentId + appId + runId`
2. a weaker fallback based only on the currently selected run

If the launch binding matches the active request and assignment, the result is displayed as workflow-bound. If only a generic selected run exists, the UI must say so honestly rather than overstating durable workflow truth.
