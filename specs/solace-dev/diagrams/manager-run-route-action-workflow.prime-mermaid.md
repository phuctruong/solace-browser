---
title: Manager Execution Route Action Workflow (SAC75)
type: prime-mermaid
---

```mermaid
graph TD
    subgraph `solace-hub` (Dev Workspace)
        S1[Manager Action: Select Request]
        S2[Manager Action: Route Target Role]
        S3[Manager Action: Launch Routed Flow]
        
        R[Active Workflow Result Binding]
        P[Run Artifact Live Preview]
        V[Approval / Signoff State]
        
        A1(Mutate: Approve)
        R1(Mutate: Reject)
        
        N1(Mutate: Route Next Step)
        
        S1 -- "__solaceActiveRequestId" --> R
        S2 -- "Active Assignment Context" --> R
        S3 -- "__solaceLaunchRoutedFlow" --> R
        
        R -- "Runtime Fetch" --> P
        R -- "Runtime Fetch" --> V
        
        V -- "window.__solaceSignoffWorkflow" --> A1
        V -- "window.__solaceSignoffWorkflow" --> R1
        
        V -- "window.__solaceRouteWorkflowNextStep" --> N1
    end

    subgraph `solace-runtime` (Back Office)
        B1[requests table]
        B2[assignments table]
        B3[approvals table]
        B4[apps/runs/ artifacts]
        
        R -. "Verify __solaceActiveRequestId" .-> B1
        R -. "Verify Selected Run match" .-> B2
        R -. "Verify Assignment Signoff" .-> B3
        
        B4 -. "fetchArtifactText payload" .-> P
        
        A1 -. "POST/PUT /approvals" .-> B3
        R1 -. "POST/PUT /approvals" .-> B3
        
        N1 -. "POST/PUT /assignments" .-> B2
    end

    style S1 fill:#0f172a,stroke:#3b82f6,color:#fff
    style S2 fill:#d946ef,stroke:#fdf4ff,color:#000
    style S3 fill:#10b981,stroke:#6ee7b7,color:#000
    style R fill:#78350f,stroke:#fcd34d,color:#fff
    style P fill:#047857,stroke:#34d399,color:#fff
    style V fill:#9f1239,stroke:#f43f5e,color:#fff
    style A1 fill:#064e3b,stroke:#a7f3d0,color:#fff
    style R1 fill:#4c0519,stroke:#fecdd3,color:#fff
    style N1 fill:#2563eb,stroke:#93c5fd,color:#fff
    
    style B1 fill:#312e81,stroke:#818cf8,color:#fff
    style B2 fill:#064e3b,stroke:#34d399,color:#fff
    style B3 fill:#581c87,stroke:#c084fc,color:#fff
    style B4 fill:#991b1b,stroke:#fca5a5,color:#fff
```

### Context
In SAC75, the continuous execution boundary loop is completely closed. The pipeline maps `N1 (Route Next Step)` directly out of `V (Approval/Signoff State)`, feeding back into the `B2 (Assignments)` Back Office table dynamically over runtime HTTP traces seamlessly inline inside the visual inspector loop.

### Truth Binding
By natively bridging the explicit `button` actions bound inside the `hydrateActiveWorkflowResult` panel immediately firing `__solaceRouteWorkflowNextStep(activeAssignmentId, 'qa')`, the system enforces a strict pipeline closure tying human-in-the-loop approvals definitively to the explicit next jump assignment, proving continuity all the way down the pipe without breaking context layout.
