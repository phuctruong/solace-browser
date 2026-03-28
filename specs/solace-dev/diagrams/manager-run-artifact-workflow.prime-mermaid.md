---
title: Manager Execution Artifact Binding Workflow (SAC71)
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
        
        S1 -- "__solaceActiveRequestId" --> R
        S2 -- "Active Assignment Context" --> R
        S3 -- "__solaceLaunchRoutedFlow" --> R
    end

    subgraph `solace-runtime` (Back Office)
        B1[requests table]
        B2[assignments table]
        B3[apps/runs/ artifacts]
        
        R -. "Verify __solaceActiveRequestId" .-> B1
        R -. "Verify Selected Run match" .-> B2
        R -. "Fetch Run State" .-> B3
        
        B3 -. "report_exists / events_exist" .-> A
    end
    
    R --> A

    style S1 fill:#0f172a,stroke:#3b82f6,color:#fff
    style S2 fill:#d946ef,stroke:#fdf4ff,color:#000
    style S3 fill:#10b981,stroke:#6ee7b7,color:#000
    style R fill:#78350f,stroke:#fcd34d,color:#fff
    style A fill:#4338ca,stroke:#818cf8,color:#fff
    
    style B1 fill:#312e81,stroke:#818cf8,color:#fff
    style B2 fill:#064e3b,stroke:#34d399,color:#fff
    style B3 fill:#991b1b,stroke:#fca5a5,color:#fff
```

### Context
In SAC71, the loop completes fully. Expanding on the Request -> Assignment -> Run binding of SAC70, the manager now receives immediate feedback on the specific artifacts (`report.html`, `events.jsonl`) generated natively by that run iteration directly inside the bound workflow panel.

### Truth Binding
By nesting the `GET /api/v1/apps/{appId}/runs` call into the `hydrateActiveWorkflowResult` binding payload, the UI actively queries the raw filesystem evidence loop for `report_exists` without needing an overarching intermediary table. The direct hyperlinks explicitly constrain execution outputs strictly mapped within the current `sap11` contextual state boundary.
