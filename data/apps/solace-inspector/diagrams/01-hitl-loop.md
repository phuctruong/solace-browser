# Diagram 01: HITL Loop — The Complete Evidence Chain
# Solace Inspector | Auth: 65537 | GLOW: L | Updated: 2026-03-03
# Committee: James Bach · Cem Kaner · Elisabeth Hendrickson · Kent Beck · Michael Bolton

## The Full Agent → Inspector → Human Loop

```mermaid
flowchart TD
    A([🤖 Agent drops\ntest-spec-*.json\ninto inbox/]) --> B

    subgraph Inspector["🔍 Solace Inspector Runner"]
        B[Poll inbox/\nfor new specs] --> C{mode?}
        C -->|web| D[Playwright:\nnavigate + ARIA\n+ screenshot]
        C -->|cli| E[subprocess:\nexecute command\n+ capture output]
        D --> F[Apply 18 heuristics\nARIA·SEO·BROKEN·UX\nSECURITY·API]
        E --> G[Assert checks:\nexit_code·stdout\n·stderr_empty]
        F --> H[Compute QA score\n100 - errors×15\n- warnings×5]
        G --> H
        H --> I[Build agent_analysis_request\npersona prompt + raw evidence\n💲$0.00 — no LLM call]
        I --> J[SHA-256 seal\n→ outbox/report-*.json]
    end

    J --> K([🤖 Agent reads report\napplies OWN model\nfills analysis_response\nproposes fixes])

    K --> L{qa_score?}
    L -->|100/100 ✅| M([✅ Green — spec\nsealed in vault\nno action needed])
    L -->|< 100 ⚠️| N([👤 Human reviews\nfix_proposals\nin dashboard])

    N --> O{Approve?}
    O -->|✅ Yes| P[Fix deployed\nHITL cycle complete]
    O -->|❌ No| Q[Agent refines\nfix proposal]
    Q --> N

    style Inspector fill:#1a1a2e,stroke:#4ecdc4,color:#fff
    style M fill:#1a472a,stroke:#52b788,color:#fff
    style P fill:#1a472a,stroke:#52b788,color:#fff
```

## Evidence Quality Gates

| Gate | Condition | Action |
|------|-----------|--------|
| **G1** | qa_score = 100 | Seal + done — no human needed |
| **G2** | qa_score 70–99 | Yellow belt — agent proposes fix, human reviews |
| **G3** | qa_score < 70 | Orange/White — critical finding, human must approve |
| **G4** | SHA-256 mismatch | Evidence tampered — reject, re-run spec |

## Key Architecture Decision: Agent-Native

```
WRONG MODEL (deprecated):
  Inspector → calls OpenRouter/Together.ai → LLM analyzes → result

CORRECT MODEL ($0.00):
  Inspector → collects raw evidence → builds prompt template
  Agent (Claude Code / Cursor / Codex) reads report
  Agent applies ITS OWN model (already running, zero extra cost)
  Persona = prompt template, not a separate API call
```
