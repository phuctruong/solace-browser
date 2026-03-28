---
title: Manager Execution Preview Binding Workflow (SAC72)
type: prime-mermaid
---

```mermaid
graph TD
    subgraph `solace-hub` (Dev Workspace)
        S1[Manager Action: Select Request]
        S2[Manager Action: Route Target Role]
        S3[Manager Action: Launch Routed Flow]
        
        R[Active Workflow Result Binding]
        A[Run Artifact Links]
        P[Run Artifact Live Preview]
        
        S1 -- "__solaceActiveRequestId" --> R
        S2 -- "Active Assignment Context" --> R
        S3 -- "__solaceLaunchRoutedFlow" --> R
        
        R --> A
        R -- "Runtime Fetch" --> P
    end

    subgraph `solace-runtime` (Back Office)
        B1[requests table]
        B2[assignments table]
        B3[apps/runs/ artifacts]
        
        R -. "Verify __solaceActiveRequestId" .-> B1
        R -. "Verify Selected Run match" .-> B2
        R -. "Fetch Run State" .-> B3
        
        B3 -. "report_exists / events_exist" .-> A
        B3 -. "fetchArtifactText payload" .-> P
    end

    style S1 fill:#0f172a,stroke:#3b82f6,color:#fff
    style S2 fill:#d946ef,stroke:#fdf4ff,color:#000
    style S3 fill:#10b981,stroke:#6ee7b7,color:#000
    style R fill:#78350f,stroke:#fcd34d,color:#fff
    style A fill:#4338ca,stroke:#818cf8,color:#fff
    style P fill:#047857,stroke:#34d399,color:#fff
    
    style B1 fill:#312e81,stroke:#818cf8,color:#fff
    style B2 fill:#064e3b,stroke:#34d399,color:#fff
    style B3 fill:#991b1b,stroke:#fca5a5,color:#fff
```

### Context
In SAC72, the final mile of execution visibility is brought inline securely into the workflow bounding box. Not only does the worker run prove its artifact bindings (SAC71), it now leverages the identical `fetchArtifactText` components isolated to the native UI loops to inline a real DOM preview of the text payloads.

### Truth Binding
By nesting the artifact HTTP text pulls immediately after the assignment verification sequence, the workflow box securely scopes the preview data pull strictly to the context of the explicit `boundRun.runId`. The manager now assesses final `report.html` HTML outputs or `payload.json` bundles natively mapped to the generated execution trace without touching the history panel.
