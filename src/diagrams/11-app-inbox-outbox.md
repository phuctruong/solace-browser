# Diagram 11: App Inbox/Outbox — Universal Folder Contract
**Date:** 2026-03-01 | **Auth:** 65537
**Cross-ref:** Paper 02 (App Standard), solaceagi/papers/13-agent-inbox-outbox.md

---

## Data Flow

```mermaid
flowchart TD
    subgraph "User Controls (Inbox)"
        PROMPTS["prompts/\nTriage rules, tone, style"]
        TEMPLATES["templates/\nEmail, post, report templates"]
        ASSETS["assets/\nSignatures, PDFs, images"]
        POLICIES["policies/\nAllowlists, blocklists, rules"]
        DATASETS["datasets/\nCRM, contacts, projects"]
    end

    subgraph "App Execution"
        RECIPE["Recipe\n(sealed, versioned)"]
        BUDGET["Budget Gates\n(fail-closed)"]
        LLM["LLM Preview\n(called ONCE)"]
        CPU["CPU Execute\n(deterministic replay)"]
    end

    subgraph "AI Produces (Outbox)"
        PREVIEWS["previews/\nActions awaiting approval"]
        DRAFTS["drafts/\nWork products"]
        REPORTS["reports/\nSummaries, digests"]
        SUGGESTIONS["suggestions/\nRecommendations"]
        RUNS["runs/{run-id}/\nmanifest + evidence"]
    end

    subgraph "User Decision"
        APPROVE["✓ Approve"]
        EDIT["✏️ Edit"]
        REJECT["✗ Reject"]
    end

    PROMPTS --> RECIPE
    TEMPLATES --> RECIPE
    ASSETS --> RECIPE
    POLICIES --> BUDGET
    DATASETS --> RECIPE

    RECIPE --> BUDGET
    BUDGET -->|PASS| LLM
    BUDGET -->|BLOCK| BLOCKED["BLOCKED\n(fail-closed)"]
    LLM --> PREVIEWS

    PREVIEWS --> APPROVE
    PREVIEWS --> EDIT
    PREVIEWS --> REJECT
    EDIT --> PREVIEWS

    APPROVE --> CPU
    CPU --> DRAFTS
    CPU --> REPORTS
    CPU --> SUGGESTIONS
    CPU --> RUNS

    style PROMPTS fill:#2d7a2d,color:#fff
    style TEMPLATES fill:#2d7a2d,color:#fff
    style ASSETS fill:#2d7a2d,color:#fff
    style POLICIES fill:#222,color:#fff
    style DATASETS fill:#2d7a2d,color:#fff
    style BUDGET fill:#222,color:#fff
    style LLM fill:#1a5cb5,color:#fff
    style CPU fill:#2d7a2d,color:#fff
    style BLOCKED fill:#FF6B6B,color:#fff
    style APPROVE fill:#2d7a2d,color:#fff
```

## Folder Contract

```
~/.solace/
  inbox/{app-id}/           ← User teaches AI (read-only for AI)
    prompts/                ← Custom instructions
    templates/              ← Reusable templates
    assets/                 ← Files for AI to use
    policies/               ← Hard rules
    datasets/               ← Reference data

  outbox/{app-id}/          ← AI shows work (append-only)
    previews/               ← Awaiting approval
    drafts/                 ← Work products
    reports/                ← Analyses
    suggestions/            ← Recommendations
    runs/{run-id}/          ← Evidence bundles

  apps/{app-id}/            ← App config
    manifest.yaml           ← Metadata + scopes
    recipe.json             ← Steps
    budget.json             ← Limits
    stats.json              ← Auto-generated
```

## Invariants

1. AI reads inbox, NEVER writes to it
2. AI writes outbox, append-only
3. Every run produces manifest.json with hashes
4. Inbox changes hot-reload into next run
5. Budget gates are fail-closed (any failure = BLOCKED)
6. Two mutation paths: VS Code (file edit) or Yinyang (AI edits file)
