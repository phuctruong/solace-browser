<!-- Diagram: 24-cpu-swarm-node-architecture -->
---
target_schema: prime-mermaid-v1
confidence: verification_gated
author: Grace Hopper (QA Diagrammer constraints)
description: Formal topology detailing the triage of governance load into explicit, actionable Human-in-the-Loop workflows. Prioritization mapping strictly ties candidate evaluation needs against bounded managerial capacity.
context_paper: SI17 Human-in-the-Loop
---

# Structure: Manager Action Queue

Transitioning from O(1) departmental load constraints (SAG29 Governance Summary) into explicit iteration operations. The pipeline determines exact next steps (Immediate, Pending, Blocked) mapped directly against executable role signatures enforcing ALCOA records globally per ticket.

```mermaid
stateDiagram-v2
    [*] --> TriagePipeline: Extract Pending Load

    state TriagePipeline {
        direction LR
        
        GovernanceLoad: Department Debt Array
        GovernanceLoad --> ImmedQueue: Target Hit Validation Bound (e.g. 5x repetitive successes)
        GovernanceLoad --> PendQueue: Sub-threshold repetition or architecture drift detected
        GovernanceLoad --> BlockedQueue: Dependent nodes are explicitly active (Not Ready)

        ImmedQueue --> HITL_Action: Review Promotion
        PendQueue --> HITL_Action: Investigate Lane Bottleneck
        BlockedQueue --> TerminalNode: Awaiting Run Sequences
        
        HITL_Action --> ALCOARecord: btoa(candidate+priority+role)
    }
```

## State Dictionary
- `ImmedQueue`: Highest ranking logic trace. Requires human signoff immediately to persist globally.
- `PendQueue`: Human oversight requested to address structural blockages inside specialist limits.
- `BlockedQueue`: Unresolved node cascades preventing safe Human Action.
- `HITL_Action`: Directed procedural command (e.g., 'Review Promotion', 'Investigate Bottleneck').
- `ALCOARecord`: The Phuc Forecast cryptographically stamped audit requirement.
