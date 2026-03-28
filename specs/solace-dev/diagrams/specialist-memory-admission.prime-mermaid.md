<!-- Diagram: 24-cpu-swarm-node-architecture -->
---
target_schema: prime-mermaid-v1
confidence: verification_gated
author: Grace Hopper (QA Diagrammer)
description: Formal topology governing the final admission of promotion-ready artifacts into department memory targets (Queued / Admitted / Rejected).
context_paper: SI21 — The Solace Intelligence System
---

# Structure: Specialist Memory Admission

Makes intelligence system retention *transparent*. This graph ensures that even if a bundle is promotion-ready, its actual write into the department memory queue and file system is explicitly tracked and verified.

```mermaid
stateDiagram-v2
    [*] --> AdmissionGate: Request Memory Admission (updateSpecialistMemoryAdmission)

    state AdmissionGate {
        direction LR

        PromotionReady: Promotion Candidate (SAP39)
        PromotionReady --> AssessAdmission

        AssessAdmission --> Admitted : SI17 Gate open, fs write successful
        AssessAdmission --> Queued   : Provisional or awaiting allocation
        AssessAdmission --> Rejected : Disqualified or write failed

        Admitted --> AdmissionRecord
        Queued   --> AdmissionRecord
        Rejected --> AdmissionRecord

        note right of AdmissionRecord: ALCOA+ = btoa(status + bundleId + targetMemory)
    }

    AdmissionGate --> [*]: Terminate Pipeline
```

## State Dictionary
- `AssessAdmission`: Evaluates if candidate cleared the SI17 seal gate.
- `Admitted`: Target memory address generated; artifacts persisted to tree.
- `Queued`: Awaiting final checks or manager gate approval.
- `Rejected`: Disqualified candidate blocked from writing to memory.
- `AdmissionRecord`: Final ALCOA+ ledger stamp for the pipeline sequence.
