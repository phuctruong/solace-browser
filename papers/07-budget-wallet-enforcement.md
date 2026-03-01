# Paper 07: Budget & Wallet Enforcement — Per-App Governance
**Date:** 2026-03-01 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser
**Cross-ref:** solaceagi/papers/04-wallet-budgets.md, 19-preview-mode-cooldown-signoff.md

---

## 1. Principle

Autonomy without budgets is fast failure. Budgets make agency safe, bounded, auditable.

## 2. Two Budget Planes

### Action Budgets (Non-Financial)
Controls WHAT actions and HOW MANY.
- Gmail: send ≤ 10/day, delete ≤ 3/day
- LinkedIn: post ≤ 1/day, comment ≤ 5/day
- Max recipients per email = 3
- Only email people in allowlist

### Spend Budgets (Financial)
Controls PAYMENTS and SPENDING authority.
- LLM cost per day ≤ $0.50
- Per-transaction max ≤ $200
- Daily cap ≤ $50
- Only use stripe payment rail

## 3. Budget Gates (Fail-Closed)

Every action passes through 5 gates. ANY failure = BLOCKED.

```
Gate B1 — Policy Present
  Scope requires policy → policy must exist
  → BLOCKED: BUDGET_POLICY_MISSING

Gate B2 — Limit Remaining
  Action count must not exceed remaining budget
  → BLOCKED: BUDGET_EXCEEDED

Gate B3 — Target Allowed
  Target must be on allowlist (recipient/merchant/domain)
  → BLOCKED: BUDGET_TARGET_NOT_ALLOWED

Gate B4 — Step-Up Required
  Rule requires re-consent → pause for step-up
  → STEP_UP_REQUIRED (no action occurs)

Gate B5 — Evidence Mode
  Policy requires evidence → runner must comply
  → BLOCKED: BUDGET_EVIDENCE_MODE_REQUIRED
```

## 4. Budget Resolution (Deterministic)

When global AND app-specific budgets exist:
- Caps: minimum wins (stricter wins)
- Allowlists: intersection wins (smaller set)
- Step-up: if ANY policy requires it → required
- Evidence: if ANY policy requires stronger → stronger

## 5. Per-App Budget (Example: Gmail)

```json
{
  "action_budgets": {
    "reads_per_run": 50,
    "drafts_per_run": 5,
    "sends_per_run": 0,
    "sends_per_day": 10,
    "deletes_per_run": 0,
    "deletes_per_day": 3,
    "archives_per_run": 50,
    "max_recipients_per_email": 3
  },
  "spend_budgets": {
    "llm_per_day_cents": 50,
    "llm_per_run_cents": 10
  },
  "policies": {
    "recipients_allowlist": "inbox/gmail-inbox-triage/policies/priority-contacts.csv",
    "step_up_required": ["gmail.send.email", "gmail.delete.email"],
    "evidence_mode": "SCREENSHOT"
  }
}
```

## 6. Budget Display (Read-Only in Browser)

```
┌──────────────────────────────────────┐
│  Gmail Inbox Triage                   │
│                                       │
│  Emails sent today: 12 / 50          │
│  LLM cost today: $0.08 / $0.50      │
│  Actions today: 34 / 200            │
│  ████████░░░░░░░░░░░░ 24%           │
│                                       │
│  [📁 Open in VS Code] [💬 Yinyang]   │
└──────────────────────────────────────┘
```

Change budgets via: VS Code (edit budget.json) or Yinyang ("set my email budget to 100/day").

## 7. Delegation Chains (MIN-Cap Rule)

When Agent A delegates to Agent B:
- cap_B = MIN(cap_A_remaining, cap_B_requested)
- scopes_B = INTERSECTION(scopes_A, scopes_B_requested)
- Prevents escalation by spawning sub-agents with bigger budgets

## 8. Forbidden States (Auto-Block)

| State | Meaning |
|-------|---------|
| FLOAT_IN_BUDGET | Monetary values must be integer cents |
| OVERCOMMITTED_ENVELOPE | Sub-agents sum > parent budget |
| DELEGATION_ESCALATION | Child cap > parent remaining |
| REVOKED_TOKEN_SPEND | Spending on revoked OAuth3 token |
| MISSING_EVIDENCE | Irreversible action without evidence capture |

## 9. Invariants

1. Any budget gate failure = BLOCKED (fail-closed, always)
2. Minimum wins for caps, intersection wins for allowlists
3. Step-up required for ALL irreversible actions
4. All monetary values in integer cents (floats forbidden)
5. Delegation cannot exceed parent authority (MIN-cap)
6. Budget changes via file edit only (VS Code or Yinyang)
