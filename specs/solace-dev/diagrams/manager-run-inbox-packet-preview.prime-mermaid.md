---
title: Manager Execution Inbox Packet Preview (SAC78)
type: prime-mermaid
---

```mermaid
graph TD
    subgraph `solace-hub` (Dev Workspace)
        S1[Manager Action: Select Request]
        S2[Manager Action: Route Target Role]
        S3[Manager Action: Launch Routed Flow]
        
        R[Active Workflow Result Binding]
        P1[Inbox Packet Live Preview]
        P2[Run Artifact Live Preview]
        
        V[Approval / Signoff State]
        O[Next-Step Route State]
        I[Worker Inbox Packet Truth]
        
        A1(Mutate: Approve)
        R1(Mutate: Reject)
        N1(Mutate: Route Next Step)
        L1(Mutate: Launch New Run)
        
        S1 -- "__solaceActiveRequestId" --> R
        S2 -- "Active Assignment Context" --> R
        S3 -- "__solaceLaunchRoutedFlow" --> R
        
        R -- "`payloadExists`" --> I
        R -- "`reportExists`" --> P2
        R -- "`eventsExist`" --> P2
        R -- "Runtime Fetch" --> V
        
        R -- "fetchArtifactText(payload.json)" --> P1
        R -- "fetchArtifactText(report.html)" --> P2
        
        V -- "window.__solaceSignoffWorkflow" --> A1
        V -- "window.__solaceSignoffWorkflow" --> R1
        
        V -- "window.__solaceRouteActiveRequest" --> N1
        N1 -- "__solaceLastWorkflowRouteAction" --> O
        
        O -- "window.__solaceLaunchRoutedFlow" --> L1
    end

    subgraph `solace-runtime` (Back Office / System)
        B1[requests table]
        B2[assignments table]
        B3[approvals table]
        B4[apps/runs/ artifacts]
        B5[apps/runs/ launch execution]
        
        R -. "Verify __solaceActiveRequestId" .-> B1
        R -. "Verify Selected Run match" .-> B2
        R -. "Verify Assignment Signoff" .-> B3
        
        B4 -. "/artifact/payload.json" .-> I
        B4 -. "payload content string" .-> P1
        B4 -. "report content string" .-> P2
        
        A1 -. "POST/PUT /approvals" .-> B3
        R1 -. "POST/PUT /approvals" .-> B3
        
        N1 -. "POST/PUT /assignments" .-> B2
        
        L1 -. "POST /api/v1/apps/run/{appId}" .-> B5
        B5 -. "New Run Created" .-> B4
    end

    style S1 fill:#0f172a,stroke:#3b82f6,color:#fff
    style S2 fill:#d946ef,stroke:#fdf4ff,color:#000
    style S3 fill:#10b981,stroke:#6ee7b7,color:#000
    style R fill:#78350f,stroke:#fcd34d,color:#fff
    style P1 fill:#d97706,stroke:#fcd34d,color:#000
    style P2 fill:#047857,stroke:#34d399,color:#fff
    style V fill:#9f1239,stroke:#f43f5e,color:#fff
    style O fill:#214b7e,stroke:#60a5fa,color:#fff
    style I fill:#f59e0b,stroke:#b45309,color:#fff
    
    style A1 fill:#064e3b,stroke:#a7f3d0,color:#fff
    style R1 fill:#4c0519,stroke:#fecdd3,color:#fff
    style N1 fill:#2563eb,stroke:#93c5fd,color:#fff
    style L1 fill:#171717,stroke:#3b82f6,color:#fff
    
    style B1 fill:#312e81,stroke:#818cf8,color:#fff
    style B2 fill:#064e3b,stroke:#34d399,color:#fff
    style B3 fill:#581c87,stroke:#c084fc,color:#fff
    style B4 fill:#991b1b,stroke:#fca5a5,color:#fff
    style B5 fill:#000000,stroke:#22c55e,color:#fff
```

### Context
In SAC78, the Dev Manager inspectability loop achieves simultaneous resolution. By separating `P1 (Inbox Packet Live Preview)` dynamically from `P2 (Run Artifact Live Preview)`, the GUI streams both the raw starting instructions explicitly launched towards the worker alongside the final report outcome dynamically rendered unconditionally side by side inside the same exact execution jump node.
