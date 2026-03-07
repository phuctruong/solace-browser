# Diagram 26: Business Acceptance eSign-Off Flow
# DNA: `validate(data) → approve(matrix) → esign(part11) → seal(evidence) → export(audit)`
# Paper: 47 (Section 21c) | Auth: 65537

```mermaid
flowchart TD
    subgraph VALIDATION["Validation Phase"]
        V1[Agent runs validation recipe]
        V2[Compare source vs target data]
        V3[Capture evidence: screenshots + DOM + HAR]
        V4[Generate deviation report]
        V1 --> V2 --> V3 --> V4
    end

    subgraph APPROVAL["Approval Matrix (E1)"]
        A1{Data Owner}
        A2{Process Owner}
        A3{IT Lead}
        A4{Compliance}
        A5{Project Sponsor}
        V4 --> A1
        A1 -->|approved| A2
        A1 -->|rejected| FIX[Fix & Re-validate]
        A2 -->|approved| A3
        A2 -->|rejected| FIX
        A3 -->|approved| A4
        A3 -->|rejected| FIX
        A4 -->|approved| A5
        A4 -->|rejected| FIX
        A5 -->|approved| SEAL
        A5 -->|rejected| FIX
        FIX --> V1
    end

    subgraph ESIGN["eSign Generation"]
        SEAL[Seal Evidence Bundle]
        SIG["sha256(user + role + timestamp + meaning + evidence_hash)"]
        SEAL --> SIG
    end

    subgraph EVIDENCE["Evidence Chain"]
        SIG --> HC[Hash Chain Entry]
        HC --> PREV[Link to Previous Entry]
        PREV --> BUNDLE[Evidence Bundle ZIP]
        BUNDLE --> VERIFY[Standalone Verification Script]
    end

    subgraph EXPORT["Audit Export"]
        VERIFY --> AUDITOR[Hand to Auditor]
        VERIFY --> REGULATOR[Submit to FDA/SOX]
    end

    style VALIDATION fill:#1a1a2e,stroke:#6C5CE7,color:#fff
    style APPROVAL fill:#16213e,stroke:#6C5CE7,color:#fff
    style ESIGN fill:#0f3460,stroke:#6C5CE7,color:#fff
    style EVIDENCE fill:#1a1a2e,stroke:#00b894,color:#fff
    style EXPORT fill:#16213e,stroke:#00b894,color:#fff
```

## Interaction Notes
- Each approval node shows in sidebar "Runs" tab with role-specific buttons
- Rejected items loop back to validation with deviation record
- eSign is Part 11 §11.50 compliant: non-transferable, timestamped, meaning-attached
- Evidence bundle is self-verifying (includes Python verification script)
