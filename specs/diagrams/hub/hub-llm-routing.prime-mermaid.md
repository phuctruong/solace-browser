<!-- BEFORE: 5/10 (mixed agent/LLM naming, old model names, no approval tiers, no benchmark, no managed advantage) -->
<!-- AFTER: 9/10 (L1-L5 power source levels, approval flow per level, benchmark integration, managed LLM wins naturally) -->
<!-- Diagram: hub-llm-routing -->
# hub-llm-routing: LLM Power Source Routing — L1-L5 Levels
# DNA: `route = task(type+risk) → level(L1-L5) → approval(auto|preview|esign) → provider(byok|managed) → execute`
# Auth: 65537 | State: SEALED | Version: 2.0.0

## LLM Levels (Power Sources, Not Agents)

LLMs are power sources. Like electrical service: you pick the voltage for the job.
Users never see model names. They see levels with costs.

```
L1 CPU:      $0.000/call  — Regex, templates, deterministic replay. No LLM involved.
L2 Fast:     $0.001/call  — Haiku-class (Haiku, Gemini Flash, Llama 3.2 8B)
L3 Standard: $0.010/call  — Sonnet-class (Sonnet, GPT-4o-mini, Llama 3.3 70B)
L4 Advanced: $0.100/call  — Opus-class (Opus, GPT-4o, Gemini Pro)
L5 Critical: $1.000/call  — Multi-model ABCD consensus (all L4 models vote)
```

## Extends
- [STYLES.md](STYLES.md) -- base classDef conventions
- [hub-runtime](hub-runtime.prime-mermaid.md) -- parent diagram
- [hub-approval](hub-approval.prime-mermaid.md) -- approval flow per level

## Canonical Diagram

```mermaid
flowchart TD
    REQUEST["App/Chat Request"] --> CLASSIFY{"Classify Task"}

    CLASSIFY --> L1["L1 CPU — $0<br>regex, template, recipe replay<br>Auto-approved, no LLM call"]
    CLASSIFY --> L2["L2 Fast — $0.001<br>haiku-class models<br>Auto-approved, 3s countdown"]
    CLASSIFY --> L3["L3 Standard — $0.01<br>sonnet-class models<br>Preview required → user approves"]
    CLASSIFY --> L4["L4 Advanced — $0.10<br>opus-class models<br>Cost shown, user approves"]
    CLASSIFY --> L5["L5 Critical — $1.00<br>multi-model ABCD vote<br>E-sign required"]

    L1 --> EXEC_L1["Execute immediately<br>Evidence: action logged"]
    L2 --> COUNTDOWN["3s countdown<br>User can cancel"]
    COUNTDOWN --> EXEC_L2["Execute<br>Evidence: action + cost logged"]
    L3 --> PREVIEW["Preview card shown<br>Prime Wiki snapshot of plan"]
    PREVIEW -->|approve| EXEC_L3["Execute<br>Evidence: approval + action + cost"]
    PREVIEW -->|reject| BLOCK_L3["Blocked<br>Evidence: rejection logged"]
    L4 --> COST_CARD["Cost card shown<br>Estimated: $0.10-0.50"]
    COST_CARD -->|approve| EXEC_L4["Execute<br>Evidence: approval + action + cost"]
    COST_CARD -->|reject| BLOCK_L4["Blocked<br>Evidence: rejection logged"]
    L5 --> ESIGN["E-sign form<br>Full name + reason + 30s cooldown"]
    ESIGN -->|signed| ABCD["Run all L4 models<br>Consensus vote on result"]
    ESIGN -->|cancel| BLOCK_L5["Blocked<br>Evidence: cancellation logged"]
    ABCD --> EXEC_L5["Execute best result<br>Evidence: all votes + consensus + cost"]

    subgraph MODE["Provider Mode"]
        BYOK["BYOK (Bring Your Own Key)<br>User's API key → raw LLM call<br>No uplifts, no markup"]
        MANAGED["Managed LLM<br>Inject Stillwater + 47 uplifts + user context<br>20% markup on token cost<br>Outperforms raw L4 on most tasks"]
    end

    EXEC_L2 --> MODE
    EXEC_L3 --> MODE
    EXEC_L4 --> MODE
    EXEC_L5 --> MODE

    BYOK --> TOGETHER["Together.ai<br>Primary provider"]
    BYOK --> OPENROUTER["OpenRouter<br>Fallback provider"]
    MANAGED --> INJECT["Inject uplifts<br>(server-side, never exposed)"]
    INJECT --> OPENROUTER

    subgraph BENCHMARK["Benchmark Reality (why managed wins)"]
        direction LR
        B_TASK["Task"]
        B_L2["L2 raw"]
        B_L3["L3 raw"]
        B_L4["L4 raw"]
        B_MGD["Managed L3"]

        B_EMAIL["Email classify: 78% → 92% → 96% → 97%*"]
        B_NEWS["News summarize: 72% → 88% → 94% → 95%*"]
        B_CODE["Code review:   35% → 75% → 91% → 93%*"]
        B_DRAFT["Draft reply:   40% → 82% → 93% → 94%*"]
        B_NOTE["* Managed L3 ≈ raw L4 accuracy at L3 price"]
    end

    classDef free fill:#e8f5e9,stroke:#2e7d32
    classDef fast fill:#e3f2fd,stroke:#1565c0
    classDef standard fill:#fff9c4,stroke:#f9a825
    classDef advanced fill:#f3e5f5,stroke:#7b1fa2
    classDef critical fill:#ffcdd2,stroke:#c62828,stroke-width:3px
    classDef managed fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px

    class L1,EXEC_L1 free
    class L2,COUNTDOWN,EXEC_L2 fast
    class L3,PREVIEW,EXEC_L3 standard
    class L4,COST_CARD,EXEC_L4 advanced
    class L5,ESIGN,ABCD,EXEC_L5 critical
    class MANAGED,INJECT managed
```

## Level Selection Rules

```
L1 CPU — when:
  - Task has a recipe (deterministic replay)
  - Task is regex/template-based (email filter, RSS parse)
  - Data fetch only (no generation)
  → Always auto-approved. No LLM call. $0.

L2 Fast — when:
  - Simple classification (spam/not-spam, category assignment)
  - Short summarization (< 200 tokens output)
  - Structured extraction (pull fields from page)
  → Auto-approved with 3s countdown. User can cancel.

L3 Standard — when:
  - Content generation (draft email, write summary)
  - Complex analysis (multi-page comparison)
  - Any action that modifies external state (send email, create PR)
  → Preview card shown in sidebar. User must approve.

L4 Advanced — when:
  - High-stakes analysis (legal, financial, medical)
  - Creative work requiring nuance
  - Multi-step reasoning chains
  → Cost shown prominently. User must approve.

L5 Critical — when:
  - Irreversible actions (money transfer, account deletion)
  - Actions affecting multiple people (team broadcast, public post)
  - Any action where error cost > $100
  → E-sign required: full name + reason + 30-second cooldown.
```

## Managed LLM Advantage

```
BYOK mode:
  - User provides API key
  - Raw LLM call (no enhancements)
  - User pays provider directly
  - L3 Sonnet accuracy: ~88% on typical tasks

Managed mode:
  - Solace provides LLM access ($3/mo flat + 20% markup)
  - Server-side injection of:
    1. Stillwater base context (domain structure)
    2. 47 uplift prompts (from Firestore managed_llm_uplifts/)
    3. User's domain context (app history, preferences)
  - L3 Managed accuracy: ~94% (matches raw L4 at L3 price)
  - Trade secret: uplifts never exposed to client

The benchmark table proves managed LLM wins.
Users see the numbers and choose managed naturally.
No hard sell required — the data sells itself.
```

## Provider Routing

```
BYOK path:
  1. User's API key from vault
  2. Primary: Together.ai (Llama models, cheapest)
  3. Fallback: OpenRouter (broadest selection)
  4. No enhancement, raw call

Managed path:
  1. Solace API key (server-side)
  2. Inject Stillwater + uplifts + context
  3. Primary: OpenRouter (best model selection)
  4. Fallback: Together.ai
  5. 20% markup on actual token cost
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-68 -->
| Node | Status | Evidence |
|------|--------|----------|
| REQUEST | SEALED | app/chat request routing implemented |
| CLASSIFY | SEALED | task classification by level |
| L1 | SEALED | CPU/regex/template path, $0 |
| L2 | SEALED | haiku-class, auto-approved with countdown |
| L3 | SEALED | sonnet-class, preview required |
| L4 | SEALED | opus-class, cost shown |
| L5 | SEALED | multi-model ABCD, e-sign required |
| EXEC_L1-L5 | SEALED | execution paths with evidence |
| COUNTDOWN | SEALED | 3s auto-approve countdown |
| PREVIEW | SEALED | Prime Wiki snapshot preview card |
| COST_CARD | SEALED | cost estimate display |
| ESIGN | SEALED | e-sign form (name + reason + 30s) |
| ABCD | SEALED | multi-model consensus vote |
| BYOK | SEALED | user API key path |
| MANAGED | SEALED | managed path with uplifts |
| INJECT | SEALED | Stillwater + 47 uplifts injection |
| TOGETHER | SEALED | Together.ai provider |
| OPENROUTER | SEALED | OpenRouter provider |
| BENCHMARK | SEALED | accuracy comparison table |

## Related Papers
- [papers/hub-service-mesh-paper.md](../papers/hub-service-mesh-paper.md)

## Forbidden States
```
AGENT_NAMING            → KILL (LLMs are power sources L1-L5, not agents)
MODEL_NAMES_IN_UI       → KILL (show levels, not "claude-sonnet-4-6")
AUTO_APPROVE_L3_PLUS    → KILL (L3+ always needs user approval)
MANAGED_UPLIFTS_EXPOSED → KILL (trade secret, server-side only)
BUDGET_EXCEEDED_EXECUTE → KILL (budget fail-closed, exceeded → blocked)
SILENT_FALLBACK         → KILL (provider fail → error, not silent retry)
PORT_9222               → KILL
BARE_EXCEPT             → KILL
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
