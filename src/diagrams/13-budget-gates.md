# Diagram 13: Budget Gates — Fail-Closed Enforcement
**Date:** 2026-03-01 | **Auth:** 65537
**Cross-ref:** Paper 07 (Budget), solaceagi/papers/04-wallet-budgets.md

---

## Gate Sequence

```mermaid
flowchart TD
    ACTION["Agent wants to\nperform action"] --> B1

    B1{"Gate B1\nPolicy Present?"} -->|No| BLOCK1["BLOCKED:\nBUDGET_POLICY_MISSING"]
    B1 -->|Yes| B2

    B2{"Gate B2\nLimit Remaining?"} -->|No| BLOCK2["BLOCKED:\nBUDGET_EXCEEDED"]
    B2 -->|Yes| B3

    B3{"Gate B3\nTarget Allowed?"} -->|No| BLOCK3["BLOCKED:\nBUDGET_TARGET_NOT_ALLOWED"]
    B3 -->|Yes| B4

    B4{"Gate B4\nStep-Up Required?"} -->|Yes| STEPUP["STEP_UP_REQUIRED\n(pause for consent)"]
    B4 -->|No| B5

    STEPUP -->|Approved| B5
    STEPUP -->|Denied/Timeout| BLOCK4["BLOCKED:\nSTEP_UP_DENIED"]

    B5{"Gate B5\nEvidence Mode Met?"} -->|No| BLOCK5["BLOCKED:\nBUDGET_EVIDENCE_MODE_REQUIRED"]
    B5 -->|Yes| PASS["✓ ACTION ALLOWED\nProceed to execution"]

    style B1 fill:#222,color:#fff
    style B2 fill:#222,color:#fff
    style B3 fill:#222,color:#fff
    style B4 fill:#222,color:#fff
    style B5 fill:#222,color:#fff
    style BLOCK1 fill:#FF6B6B,color:#fff
    style BLOCK2 fill:#FF6B6B,color:#fff
    style BLOCK3 fill:#FF6B6B,color:#fff
    style BLOCK4 fill:#FF6B6B,color:#fff
    style BLOCK5 fill:#FF6B6B,color:#fff
    style STEPUP fill:#FFD700,color:#000
    style PASS fill:#2d7a2d,color:#fff
```

## Resolution Rules

```mermaid
graph LR
    G["Global Budget\nsend ≤ 20/day"] --> R["Resolution\nMIN(global, app)"]
    A["App Budget\nsend ≤ 10/day"] --> R
    R --> E["Effective\nsend ≤ 10/day"]

    G2["Global Allowlist\n[a.com, b.com, c.com]"] --> R2["Resolution\nINTERSECTION"]
    A2["App Allowlist\n[b.com, c.com, d.com]"] --> R2
    R2 --> E2["Effective\n[b.com, c.com]"]

    style R fill:#222,color:#fff
    style R2 fill:#222,color:#fff
```

- Caps: minimum wins (stricter)
- Allowlists: intersection wins (smaller)
- Step-up: if ANY requires → required
- Evidence: if ANY requires stronger → stronger

## Invariants

1. ANY gate failure = BLOCKED (no fallback, no degrade)
2. Step-up timeout = DENY (not proceed)
3. Budget resolution is deterministic (MIN + INTERSECTION)
4. All monetary values in integer cents (floats = forbidden state)
5. Delegation: child can never exceed parent (MIN-cap rule)
