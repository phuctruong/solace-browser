# Paper 02: App Inbox/Outbox Standard — Universal Convention
**Date:** 2026-03-01 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser, solace-cli, solaceagi
**Cross-ref:** solaceagi/papers/13-agent-inbox-outbox.md (original spec)

---

## 1. The Universal App Contract

Every Solace app follows the same filesystem convention. This is the "filesystem API" for Software 5.0.

```
EVERY APP = manifest.yaml + inbox/ + outbox/ + recipe.json + budget.json
```

### 1.1 App Directory

```
~/.solace/apps/{app-id}/
  manifest.yaml          ← metadata, scopes, category, risk tier
  recipe.json            ← steps the AI executes (sealed, versioned)
  budget.json            ← action + spend limits (user-editable)
  stats.json             ← auto-generated run stats (read-only)
```

### 1.2 Inbox Directory

```
~/.solace/inbox/{app-id}/
  prompts/               ← custom instructions for app behavior
  templates/             ← reusable templates the AI fills in
  assets/                ← files the AI uses in outputs (signatures, PDFs, images)
  policies/              ← rules: allowlists, blocklists, compliance
  datasets/              ← reference data: CRM exports, contact lists
```

### 1.3 Outbox Directory

```
~/.solace/outbox/{app-id}/
  previews/              ← AI-generated previews awaiting approval
  drafts/                ← draft outputs (emails, posts, reports)
  reports/               ← completed summaries, digests, analyses
  suggestions/           ← AI recommendations for user review
  runs/                  ← per-run evidence bundles
    {run-id}/
      manifest.json      ← inputs, outputs, hashes
      evidence.pzip      ← hash-chained evidence
```

## 2. Inbox Rules (User → AI)

- Agents may ONLY read from `inbox/` + granted OAuth3 scopes
- Agents NEVER write to inbox (that's user-controlled space)
- Agents NEVER modify user files
- `vault/` is off-limits unless explicitly authorized
- Inbox changes hot-reload into next run (no restart needed)

### Inbox Types

| Type | Purpose | Example |
|------|---------|---------|
| `prompts/` | How the app should behave | "Always star emails from boss" |
| `templates/` | Reusable fill-in templates | Email reply template with {{name}} |
| `assets/` | Files to attach or embed | signature.html, product-sheet.pdf |
| `policies/` | Hard rules the AI must follow | priority-contacts.csv, forbidden-topics.md |
| `datasets/` | Reference data to consult | CRM export, project list |

## 3. Outbox Rules (AI → User)

- Agents write ONLY to `outbox/` (and `evidence/` if enabled)
- Outbox is append-only by default
- Every output has a manifest.json with: run_id, inputs, outputs, hashes
- Outputs are verifiable, replayable, searchable
- Never overwrite user files unless recipe explicitly permits + OAuth3 scope allows + step-up approved

### Outbox Types

| Type | Purpose | Example |
|------|---------|---------|
| `previews/` | Actions the AI wants to take (needs approval) | "Send 3 emails — approve?" |
| `drafts/` | Work products for user review | Email draft, post draft |
| `reports/` | Completed analyses and summaries | Daily digest, weekly report |
| `suggestions/` | Recommendations for user action | "Whitelist john@acme.com?" |
| `runs/` | Evidence bundles per execution | manifest + evidence chain |

## 4. Run Manifest (Every Execution)

```json
{
  "run_id": "run_550e8400",
  "created_at": "2026-03-01T14:12:00Z",
  "app_id": "gmail-inbox-triage",
  "level": "L2",
  "inputs": [
    "inbox/gmail-inbox-triage/prompts/triage-rules.md",
    "inbox/gmail-inbox-triage/policies/priority-contacts.csv"
  ],
  "outputs": [
    "outbox/gmail-inbox-triage/reports/2026-03-01_daily_digest.md"
  ],
  "evidence": [
    "outbox/gmail-inbox-triage/runs/run_550e8400/evidence.pzip"
  ],
  "hashes": {
    "output_sha256": "sha256:...",
    "evidence_sha256": "sha256:..."
  },
  "budget_consumed": {
    "reads": 42,
    "drafts": 3,
    "llm_cost_cents": 8
  }
}
```

## 5. Base App Manifest (Convention)

```yaml
type: solace_app_spec
app_id: "{category}-{name}"
spec_version: 1.0.0
rung_target: 641

# REQUIRED
category: "{communications|productivity|sales|marketing|engineering|finance|social|ecommerce}"
risk_tier: "{low|medium|high}"
site: "{domain}"
requires_login: true

# Scopes
default_scopes: [...]
optional_scopes: [...]  # STEP-UP REQUIRED

# Storage contract
storage:
  inbox_dir: "inbox/{app-id}"
  outbox_dir: "outbox/{app-id}"
  cache_dir: "cache/{app-id}"

# Budget enforcement
action_budgets:
  "{action}_per_run": N
  "{action}_per_day": N

# Scheduling
scheduling:
  default_interval: "{Nm|Nh|daily|weekly}"
  retry_policy: "exponential_backoff"
  max_retries: 2

# Evidence
evidence_mode: "SCREENSHOT"
```

## 6. Safety Classes

| Class | Risk | Cooldown | Step-Up | Examples |
|-------|------|----------|---------|----------|
| A (Read) | Low | 0s | No | Read inbox, scan feed, extract metrics |
| B (Visible) | Medium | 5-15s | Optional | Post, send message, create draft |
| C (Irreversible) | High | 15-30s | Required + reason | Send email, delete, refund |

## 7. Customization: Two Paths, Same File

**Power user:** Open in VS Code → edit inbox files directly
**Normal user:** Talk to Yinyang → AI edits inbox files
**Result:** Same file, same hot-reload, same next run

## 8. App Categories (10 categories, 30+ planned apps)

| Category | Flagship | Free | Domain |
|----------|----------|------|--------|
| Communications | Gmail Inbox Triage | Yes | mail.google.com |
| Productivity | Morning Brief | Yes | mail + calendar.google.com |
| Sales | LinkedIn Outreach | No | linkedin.com |
| Marketing | Reddit Scanner | No | reddit.com |
| Engineering | GitHub Issue Triage | No | github.com |
| E-commerce | Amazon Price Monitor | No | amazon.com |
| Finance | Expense Scanner | No | bank portals |
| Social | WhatsApp Organizer | No | web.whatsapp.com |

## 9. Invariants

1. Inbox is user-controlled. AI reads, never writes.
2. Outbox is append-only. AI writes, user reviews.
3. Every run produces a manifest with hashes.
4. Budget gates are fail-closed. Any failure = BLOCKED.
5. Step-up required for all irreversible actions.
6. File is single source of truth. Hot-reload on change.
7. Customization = files, not forms.
