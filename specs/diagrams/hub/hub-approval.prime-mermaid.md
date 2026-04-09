<!-- BEFORE: 5/10 (generic risk tiers, no L1-L5 mapping, no preview card, no approval queue, no sidebar badge) -->
<!-- AFTER: 9/10 (L1-L5 approval tiers, preview with Prime Wiki snapshot, sidebar red badge, e-sign for L5, expiry) -->
<!-- Diagram: 20-approval-stepup-flow -->
# 20: Approval Queue + Step-Up Flow by LLM Level
# DNA: `approval = level(L1-L5) × preview(snapshot) × queue(sidebar_badge) × step_up(esign) → evidence`
# SHA-256: pending-rewrite
# Auth: 65537 | State: SEALED | Version: 2.0.0

## Approval Philosophy

Every LLM action has a cost and a risk. The approval flow scales with both.
L1-L2: fast and cheap, auto-approved with evidence.
L3-L4: meaningful cost, preview before execution.
L5: irreversible or expensive, e-sign required.

The approval queue appears in the Yinyang sidebar with a red badge count.
Users see what AI wants to do BEFORE it happens.

## Extends
- [STYLES.md](STYLES.md) -- base classDef conventions
- [hub-chat-fsm](hub-chat-fsm.prime-mermaid.md) -- parent diagram
- [hub-llm-routing](hub-llm-routing.prime-mermaid.md) -- level definitions

## Canonical Diagram

```mermaid
flowchart TD
    ACTION["Action Requested<br>(from app or chat)"] --> LEVEL{"LLM Level?"}

    LEVEL -->|L1 CPU| AUTO_L1["Auto-approved<br>$0 — no LLM call<br>Evidence: action logged"]
    LEVEL -->|L2 Fast| AUTO_L2["Auto-approved<br>3s countdown visible in sidebar<br>User can cancel during countdown<br>Evidence: action + cost logged"]
    LEVEL -->|L3 Standard| QUEUE_L3["Added to Approval Queue<br>Red badge incremented in sidebar"]
    LEVEL -->|L4 Advanced| QUEUE_L4["Added to Approval Queue<br>Red badge incremented + cost shown"]
    LEVEL -->|L5 Critical| QUEUE_L5["Added to Approval Queue<br>Red badge + WARNING label"]

    AUTO_L1 --> EXEC["Execute Action"]
    AUTO_L2 --> EXEC

    QUEUE_L3 --> PREVIEW_L3["Preview Card in Sidebar<br>Prime Wiki snapshot of plan<br>What AI wants to do + expected result"]
    QUEUE_L4 --> PREVIEW_L4["Preview Card in Sidebar<br>Snapshot + cost estimate<br>Estimated: $0.10—$0.50"]
    QUEUE_L5 --> PREVIEW_L5["Preview Card in Sidebar<br>Snapshot + cost + risk warning<br>IRREVERSIBLE ACTION label"]

    PREVIEW_L3 -->|"[Approve]"| EXEC
    PREVIEW_L3 -->|"[Reject]"| REJECT["Rejected<br>Evidence: rejection reason logged"]
    PREVIEW_L3 -->|"5 min timeout"| EXPIRE["Expired<br>Evidence: expiry logged"]

    PREVIEW_L4 -->|"[Approve]"| EXEC
    PREVIEW_L4 -->|"[Reject]"| REJECT
    PREVIEW_L4 -->|"5 min timeout"| EXPIRE

    PREVIEW_L5 -->|"[e-Sign]"| ESIGN["E-Sign Form<br>Full name typed<br>Reason field (required)<br>30-second cooldown timer<br>Hash of action shown"]
    PREVIEW_L5 -->|"[Reject]"| REJECT
    PREVIEW_L5 -->|"5 min timeout"| EXPIRE

    ESIGN -->|"signed after 30s"| EXEC
    ESIGN -->|"cancelled"| REJECT

    EXEC --> LOG["Evidence Recorded<br>approval_type + actor + timestamp<br>action_hash + result_hash<br>cost_actual + level"]
    REJECT --> LOG_REJECT["Evidence Recorded<br>rejection_reason + actor + timestamp<br>action_hash + level"]
    EXPIRE --> LOG_EXPIRE["Evidence Recorded<br>expiry_timestamp + action_hash + level"]

    LOG --> CHAIN["Hash-chain appended<br>Part 11 compliant"]
    LOG_REJECT --> CHAIN
    LOG_EXPIRE --> CHAIN

    subgraph SIDEBAR_QUEUE["Approval Queue in Yinyang Sidebar"]
        BADGE_COUNT["Red badge: 3 pending"]
        ITEM_1["L3 | gmail.com | draft reply | [Preview]"]
        ITEM_2["L4 | github.com | create PR | [Preview]"]
        ITEM_3["L5 | bank.com | transfer $500 | [e-Sign]"]
    end

    subgraph PREVIEW_EXPANDED["Preview Card (expanded in sidebar)"]
        SNAP_TITLE["Action: Draft reply to boss re: Q2 budget"]
        SNAP_WIKI["Prime Wiki snapshot of current page"]
        SNAP_PLAN["AI plan: Reply with budget summary from spreadsheet"]
        SNAP_COST["Estimated cost: $0.01 (L3 Sonnet)"]
        SNAP_BUTTONS["[Approve] [Reject] [View Full Page] [Screenshot]"]
    end

    QUEUE_L3 -.-> SIDEBAR_QUEUE
    QUEUE_L4 -.-> SIDEBAR_QUEUE
    QUEUE_L5 -.-> SIDEBAR_QUEUE
    ITEM_1 -.->|click Preview| PREVIEW_EXPANDED

    classDef auto fill:#e8f5e9,stroke:#2e7d32
    classDef preview fill:#fff9c4,stroke:#f9a825
    classDef esign fill:#ffcdd2,stroke:#c62828,stroke-width:3px
    classDef evidence fill:#e3f2fd,stroke:#1565c0
    classDef queue fill:#fce4ec,stroke:#c62828,stroke-width:2px

    class AUTO_L1,AUTO_L2 auto
    class QUEUE_L3,QUEUE_L4,PREVIEW_L3,PREVIEW_L4 preview
    class QUEUE_L5,PREVIEW_L5,ESIGN esign
    class LOG,LOG_REJECT,LOG_EXPIRE,CHAIN evidence
    class BADGE_COUNT,ITEM_1,ITEM_2,ITEM_3 queue
```

## Approval Levels Detail

```
L1 CPU ($0.00):
  Approval: AUTOMATIC — no user interaction
  UI: No notification. Action logged silently in events table.
  Evidence: { type: "auto_approved", level: "L1", cost: 0.00 }
  Example: Recipe replay, regex filter, template render

L2 Fast ($0.001):
  Approval: AUTOMATIC with 3-second countdown
  UI: Small countdown in sidebar brand section: "L2 running... 3... 2... 1..."
       User can click [Cancel] during countdown to abort.
  Evidence: { type: "auto_approved", level: "L2", cost: 0.001, countdown_completed: true }
  Example: Classify email, extract fields, short summary

L3 Standard ($0.01):
  Approval: PREVIEW REQUIRED — added to approval queue
  UI: Red badge appears on sidebar. Preview card shows:
       - Prime Wiki snapshot of current page context
       - What AI wants to do (one paragraph)
       - Expected output format
       - [Approve] [Reject] buttons
  Evidence: { type: "user_approved", level: "L3", cost: 0.01, approved_by: "user", timestamp: ... }
  Timeout: 5 minutes → auto-expire with evidence
  Example: Draft email, write summary, generate code

L4 Advanced ($0.10):
  Approval: PREVIEW + COST — added to approval queue
  UI: Same as L3 plus:
       - Cost estimate prominently displayed: "This will cost ~$0.10—$0.50"
       - Warning if approaching daily budget limit
  Evidence: { type: "user_approved", level: "L4", cost_estimated: 0.10, cost_actual: ..., approved_by: ... }
  Timeout: 5 minutes → auto-expire with evidence
  Example: Legal analysis, financial report, complex multi-step task

L5 Critical ($1.00):
  Approval: E-SIGN REQUIRED — added to approval queue with WARNING
  UI: Preview card plus:
       - "IRREVERSIBLE ACTION" warning label (red)
       - E-sign form: user must type full name
       - Reason field (required, min 10 characters)
       - 30-second cooldown timer (cannot sign before timer completes)
       - Hash of the action displayed (SHA-256 first 16 chars)
       - [Sign & Execute] button (enabled after 30s + name + reason)
  Evidence: {
    type: "esigned",
    level: "L5",
    signer_name: "Phuc Nguyen",
    reason: "Quarterly report needs to go out today",
    cooldown_seconds: 30,
    action_hash: "a4f2c7...",
    timestamp: "2026-03-15T14:32:00Z",
    cost_estimated: 1.00
  }
  Timeout: 5 minutes → auto-expire with evidence
  Example: Money transfer, account deletion, public post, team broadcast
```

## Preview Card Content

```
When user clicks [Preview] on an approval item:

Card expands in sidebar (takes ~60% of sidebar height):
┌──────────────────────────────────────┐
│ L3 Standard — gmail.com             │
│ App: inbox-triage                    │
│                                      │
│ Action: Draft reply to boss          │
│ Re: Q2 Budget Review                 │
│                                      │
│ What AI will do:                     │
│ Read the email about Q2 budget,      │
│ pull numbers from attached sheet,    │
│ draft a 3-paragraph reply with       │
│ key figures highlighted.             │
│                                      │
│ Page context (Prime Wiki snapshot):  │
│ ┌──────────────────────────────────┐ │
│ │ From: boss@company.com           │ │
│ │ Subject: Q2 Budget Review        │ │
│ │ "Please review and reply with    │ │
│ │  your department's numbers..."   │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Est. cost: $0.01                     │
│                                      │
│ [Approve] [Reject] [View Full] [SS] │
└──────────────────────────────────────┘

[View Full] → opens localhost:8888/apps/inbox-triage/runs/{id}
[SS] → captures screenshot on demand (not stored by default)
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-68 -->
| Node | Status | Evidence |
|------|--------|----------|
| ACTION | SEALED | Action request from app/chat |
| LEVEL | SEALED | Level classification L1-L5 |
| AUTO_L1 | SEALED | L1 auto-approve, $0, evidence logged |
| AUTO_L2 | SEALED | L2 auto-approve, 3s countdown, cancellable |
| QUEUE_L3 | SEALED | L3 added to approval queue |
| QUEUE_L4 | SEALED | L4 added to queue with cost |
| QUEUE_L5 | SEALED | L5 added to queue with WARNING |
| PREVIEW_L3 | SEALED | Preview card with snapshot |
| PREVIEW_L4 | SEALED | Preview + cost estimate |
| PREVIEW_L5 | SEALED | Preview + e-sign form |
| ESIGN | SEALED | E-sign: name + reason + 30s cooldown + hash |
| EXEC | SEALED | Execute action on approval |
| REJECT | SEALED | Rejection with evidence |
| EXPIRE | SEALED | 5-minute auto-expiry with evidence |
| LOG/CHAIN | SEALED | Evidence hash-chained, Part 11 compliant |
| SIDEBAR_QUEUE | SEALED | Red badge count in sidebar |
| PREVIEW_EXPANDED | SEALED | Expandable preview card |

## Related Papers
- [papers/hub-service-mesh-paper.md](../papers/hub-service-mesh-paper.md)

## Forbidden States
```
AUTO_APPROVE_L3_PLUS      → KILL (L3+ always needs user approval)
ESIGN_WITHOUT_COOLDOWN    → KILL (L5 requires 30-second wait)
APPROVE_WITHOUT_PREVIEW   → KILL (user must see what AI will do)
PREVIEW_WITHOUT_SNAPSHOT  → KILL (Prime Wiki snapshot required)
EXPIRED_WITHOUT_EVIDENCE  → KILL (expiry must be logged)
REJECT_WITHOUT_EVIDENCE   → KILL (rejection must be logged)
BUDGET_EXCEEDED_IN_QUEUE  → KILL (over-budget items blocked before queue)
PORT_9222                 → KILL
EXTENSION_API             → KILL
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
