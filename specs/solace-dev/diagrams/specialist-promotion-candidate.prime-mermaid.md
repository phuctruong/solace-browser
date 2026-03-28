<!-- Diagram: 24-cpu-swarm-node-architecture -->
---
target_schema: prime-mermaid-v1
confidence: verification_gated
author: Grace Hopper (QA Diagrammer)
description: Formal topology governing the transition from verified artifact provenance (SAV38) to actionable promotion candidacy (Ready-to-Seal / Provisional / Disqualified).
context_paper: SI17 — Human-in-the-Loop as a First-Class System Component
---

# Structure: Specialist Promotion Candidate

Makes bundle trust *actionable*. This graph ensures that once integrity is verified, the workspace explicitly decides whether the run output is ready to enter department memory — and shows the exact gate or blocker preventing it if not.

```mermaid
stateDiagram-v2
    [*] --> PromotionGate: Evaluate bundle trust (updateSpecialistPromotionCandidate)

    state PromotionGate {
        direction LR

        ProvenanceVerdict: Bundle Integrity Verdict (SAV38)
        ProvenanceVerdict --> AssessReadiness

        AssessReadiness --> ReadyToSeal   : All checks passed, no blockers
        AssessReadiness --> Provisional   : Checks incomplete — run still active
        AssessReadiness --> Disqualified  : One or more integrity failures

        ReadyToSeal  --> SealGate: Human gate (SI17) — manager approval required
        Provisional  --> SealGate: Pending file completion before gate
        Disqualified --> SealGate: Re-run required — gate closed

        note right of SealGate: ALCOA+ = btoa(status + bundleId + basis)
    }
```

## State Dictionary
- `AssessReadiness`: Combines provenance verdict with run completion state.
- `Ready-to-Seal`: All files present and hash-matched; bundle awaits human approval.
- `Provisional`: Provenance partially complete; run still producing outputs.
- `Disqualified`: Hash mismatch or missing file detected; cannot be promoted.
- `SealGate`: The SI17 human-in-the-loop checkpoint before committing to department memory.
