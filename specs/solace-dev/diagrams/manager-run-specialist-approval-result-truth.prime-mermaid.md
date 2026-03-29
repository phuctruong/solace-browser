---
title: Manager Execution Specialist Approval Result Truth (SAC85)
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
        
        V[Approval / Signoff State]
        O[Next-Step Route State]
        I[Worker Inbox Packet Truth]
        C[Packet Provenance & Handoff Contract]
        U[Specialist Pickup Receipt Truth]
        E[Specialist Execution Evidence Truth]
        T[Specialist Output Truth]
        A2[Target Assignment Approval Truth]
        A3[Target Assignment Approval Action]
        A5[Target Assignment Approval Mutation Result]
        
        A1(Mutate: Approve Source)
        R1(Mutate: Reject Source)
        N1(Mutate: Route Next Step)
        L1(Mutate: Launch New Run)
        A4(Mutate: Approve Target)
        R2(Mutate: Reject Target)
        
        S1 -- "__solaceActiveRequestId" --> R
        S2 -- "Active Assignment Context" --> R
        S3 -- "__solaceLaunchWorkflowNextStep" --> R
        
        R -- "`payloadExists`" --> I
        R -- "`window.__solaceLastWorkflowLaunchAction`" --> C
        R -- "`eventsExist`" --> U
        R -- "`reportExists`" --> T
        C -. "Resolves exactPacketTruth" .-> U
        C -. "Resolves exactPacketTruth" .-> E
        C -. "Resolves exactPacketTruth" .-> T
        C -. "Resolves exactPacketTruth" .-> A2
        C -. "Resolves exactPacketTruth" .-> A3
        C -. "Resolves exactPacketTruth" .-> A5
        
        R -- "fetchArtifactText(payload.json)" --> P1
        R -- "fetchArtifactText(events.jsonl)" --> E
        R -- "fetchArtifactText(report.html)" --> T
        R -- "approvals.find(targetAssignmentId)" --> A2
        A2 --> A3
        
        V -- "window.__solaceSignoffWorkflow" --> A1
        V -- "window.__solaceSignoffWorkflow" --> R1
        
        A3 -- "window.__solaceSignoffWorkflow(targetAssignmentId)" --> A4
        A3 -- "window.__solaceSignoffWorkflow(targetAssignmentId)" --> R2
        
        A4 -- "returns: window.__solaceLastWorkflowSignoffActionResult" -.-> A5
        R2 -- "returns: window.__solaceLastWorkflowSignoffActionResult" -.-> A5
        
        V -- "window.__solaceRouteWorkflowNextStep" --> N1
        N1 -- "__solaceLastWorkflowRouteAction" --> O
        
        O -- "window.__solaceLaunchWorkflowNextStep" --> L1
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
        
        C -. "sourceAssignmentId bindings" .-> B2
        C -. "targetAssignmentId bindings" .-> B2
        
        B4 -. "payload content string" .-> P1
        B4 -. "events string array" .-> E
        B4 -. "report content string" .-> T
        
        A2 -. "evaluates assignment approval" .-> B3
        
        A1 -. "POST/PUT /approvals" .-> B3
        R1 -. "POST/PUT /approvals" .-> B3
        
        A4 -. "POST/PUT /approvals" .-> B3
        R2 -. "POST/PUT /approvals" .-> B3
        
        B3 -. "200/201 JSON boolean mapped" .-> A5
        
        N1 -. "POST/PUT /assignments" .-> B2
        
        L1 -. "POST /api/v1/apps/run/{appId}" .-> B5
        B5 -. "New Run Created" .-> B4
    end

    style S1 fill:#0f172a,stroke:#3b82f6,color:#fff
    style S2 fill:#d946ef,stroke:#fdf4ff,color:#000
    style S3 fill:#10b981,stroke:#6ee7b7,color:#000
    style R fill:#78350f,stroke:#fcd34d,color:#fff
    style P1 fill:#d97706,stroke:#fcd34d,color:#000
    style V fill:#9f1239,stroke:#f43f5e,color:#fff
    style O fill:#214b7e,stroke:#60a5fa,color:#fff
    style I fill:#f59e0b,stroke:#b45309,color:#fff
    style C fill:#1e3a8a,stroke:#60a5fa,color:#fff
    style U fill:#581c87,stroke:#a78bfa,color:#fff
    style E fill:#0d9488,stroke:#2dd4bf,color:#fff
    style T fill:#9d174d,stroke:#f472b6,color:#fff
    style A2 fill:#1e40af,stroke:#818cf8,color:#fff
    style A3 fill:#6366f1,stroke:#818cf8,color:#fff
    style A5 fill:#f87171,stroke:#fca5a5,color:#000
    
    style A1 fill:#064e3b,stroke:#a7f3d0,color:#fff
    style R1 fill:#4c0519,stroke:#fecdd3,color:#fff
    style A4 fill:#064e3b,stroke:#a7f3d0,color:#fff
    style R2 fill:#4c0519,stroke:#fecdd3,color:#fff
    
    style N1 fill:#2563eb,stroke:#93c5fd,color:#fff
    style L1 fill:#171717,stroke:#3b82f6,color:#fff
    
    style B1 fill:#312e81,stroke:#818cf8,color:#fff
    style B2 fill:#064e3b,stroke:#34d399,color:#fff
    style B3 fill:#581c87,stroke:#c084fc,color:#fff
    style B4 fill:#991b1b,stroke:#fca5a5,color:#fff
    style B5 fill:#000000,stroke:#22c55e,color:#fff
```

### Context
In SAC85, the Dev Manager inspectability loop verifies honest next-step approval result truth. `A5 (Next-Step Approval Mutation Result Truth)` is only allowed to claim exact result truth when the approval mutation result is bound to the launched target assignment and the current request, source assignment, target assignment, role, and run stay aligned in the exact workflow-bound branch. If a visible approval write succeeds or fails after the current binding has already fallen back, Hub must say so instead of overstating exact downstream closure.
