<!-- Diagram: 24-cpu-swarm-node-architecture -->
---
target_schema: prime-mermaid-v1
confidence: verification_gated
author: Grace Hopper (QA Diagrammer constraints)
description: Formal state architecture of the SAM27 Human-in-the-Loop Promotion Decision pipeline. Maps candidate memory generated internally against Manager-driven validation gates.
context_paper: SI17 Human-in-the-Loop, SI18 Transparency as a Product Feature
---

# Structure: Worker Promotion Decision States

The system implements transparent human oversight (SI17/SI18), presenting the exact decision block bridging automated repeating signals into shared intelligent memory. 

```mermaid
stateDiagram-v2
    [*] --> DecisionEval: Manager Clicks Run Envelope (updatePromotionDecisionState)

    state DecisionEval {
        direction LR
        
        Inspect: Inspect Distillation Candidate
        Inspect --> APPROVED: Role = 'manager' (Authority matches System Target)
        Inspect --> PENDING_REVIEW: Role = 'coder' (Repetitive Execution without Approval)
        Inspect --> BLOCKED: Role = 'qa' | 'design' (No memory logic evaluated)
        Inspect --> UNKNOWN: Role = 'undefined' (Failsafe fallback)
        
        APPROVED --> GlobalStore: Promoted to all-access Convention Memory
        PENDING_REVIEW --> ReviewQueue: Locks candidate memory from Global use
        BLOCKED --> RejectAction: Returns memory constraints strictly to local context
        APPROVED --> PacketContext: Active Packet Context
        PENDING_REVIEW --> PacketContext
        BLOCKED --> PacketContext
    }
```

## State Dictionary
- `APPROVED`: The highest verification state where the human authority confirms the execution pattern successfully represents a durable memory component perfectly aligned to Solace goals.
- `PENDING_REVIEW`: Intelligent system correctly recognizes repetition, yet legally yields authority blocking full deployment until human sign-off verifies it limits unexpected side-effects.
- `BLOCKED`: Denied promotion path entirely.
- `UNKNOWN`: Fallback. Protects UI and data structure from hallucinatory logic.
