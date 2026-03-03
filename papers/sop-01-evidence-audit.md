# SOP-01: Evidence Capture and Audit Trail Management
# Version: 1.0 | Effective: 2026-03-03 | Prepared by: Solace AGI
# Cross-ref: Paper 40 (21 CFR Part 11), Paper 06 (ALCOA+), Paper 07 (Budget Gates)

---

## Purpose

Define the standard procedure for capturing, sealing, verifying, and
archiving agent action evidence in Solace Browser to satisfy FDA 21 CFR
Part 11 requirements for electronic records and electronic signatures.

---

## Scope

This SOP applies to all Solace Browser sessions where:

- The user has an active OAuth3 session (logged in)
- Evidence mode is set to `data` or `visual` (not `off`)
- The user clicks APPROVE before any agent action executes

Guest sessions (not logged in) and evidence mode `off` are out of scope
for Part 11 compliance.

---

## Definitions

| Term | Definition |
|------|-----------|
| **Run** | One complete execution of a recipe from approval to completion |
| **run_id** | Unique identifier for a run (format: `{app_id}-{YYYYMMDD}-{HHMMSS}`) |
| **Evidence bundle** | All files produced for a single run (manifest, actions, approval, snapshots) |
| **Seal** | Application of `chmod 444` to all evidence files; makes them immutable |
| **Hash chain** | Append-only SHA-256 linked list; each entry references the previous entry's hash |
| **bundle.sha256** | SHA-256 hash of all files in an evidence bundle |
| **Electronic signature** | `approval.json` containing signer identity, timestamp, and meaning |
| **APPROVE** | Explicit user action that triggers execution and creates the approval record |

---

## Procedure

### Step 1: Pre-Run Validation

**Before the recipe engine starts, the system automatically verifies:**

- [ ] Active OAuth3 token (`sw_sk_` bearer) present and not expired
- [ ] Token scope matches recipe requirements (e.g., `gmail.read.inbox`)
- [ ] Budget available (credits > estimated run cost)
- [ ] Device ID matches token binding
- [ ] Evidence mode is not `off` (if Part 11 compliance is required)

**If any check fails:** The run is blocked. A clear error message is shown.
No evidence is created for a blocked run.

**Manual verification (for QA or audit purposes):**

```bash
# Verify token status
python3 -m solace_browser.auth --check-token

# Expected output:
# Token: tok_abc123
# User: phuc@solaceagi.com (usr_phuc_001)
# Device: macbook-pro-phuc-001
# Expires: 2026-04-03T00:00:00Z (valid)
# Scopes: gmail.read.inbox, gmail.draft.create
# Budget remaining: $4.88
```

---

### Step 2: Approval Gate

**The approval gate is a hard block. No execution without it.**

The system presents a preview to the user showing:

```
Recipe: Gmail Inbox Triage
Steps to be executed:
  1. Navigate to Gmail inbox
  2. Read top 10 unread emails
  3. Draft 3 suggested replies (no send)
  4. Generate summary report

Scopes requested: gmail.read.inbox, gmail.draft.create
Estimated cost: $0.001 (1,247 tokens)
Estimated time: 18 seconds

[ APPROVE ]  [ REJECT ]
```

**When user clicks APPROVE:**

1. `approval.json` is written immediately with:
   - `signer.user_id` (from active token)
   - `signer.full_name` (from Firebase auth profile)
   - `approved_at` (system timestamp, UTC)
   - `meaning` ("I approve this agent action on my behalf")
   - `method` ("explicit_button_click")
   - `preview_hash` (SHA-256 of the preview content shown)
   - `steps_reviewed` (the exact steps shown in the preview)

2. `approval.json` is sealed immediately (`chmod 444`).

3. Execution begins only after `approval.json` is written and sealed.

**If user clicks REJECT:**

1. No evidence files are created.
2. The `run_id` is discarded.
3. No audit chain entry is written.

**Anti-Clippy rule:** The system never auto-approves, never pre-approves,
never assumes. Every run requires a fresh explicit APPROVE click.

---

### Step 3: Evidence Capture

**During execution, the system captures:**

For every agent action:

```
action = {
  seq:           monotonically increasing integer
  ts:            ISO 8601 timestamp (UTC, millisecond precision)
  who:           user_id + device_id
  action_type:   navigate | click | type | read | submit | wait
  url:           current page URL
  what:          human-readable description of action
  why:           recipe step reference + user approval reference
  snapshot_hash: SHA-256 of current page state (Prime Mermaid snapshot)
  prev_hash:     SHA-256 of previous action entry
}
```

**Invariants (enforced by the engine, not by configuration):**

- LLM is called exactly once (at preview). Never during execution.
- Evidence is captured at event time. Never reconstructed afterward.
- Sequence numbers never repeat and never skip within a run.
- Timestamp delta between consecutive actions is always > 0.

**Evidence files written during execution:**

```
~/.solace/evidence/{run_id}/
  manifest.json           Written at run start; updated at completion
  actions.json            Appended after each action
  before_snapshot.html    Written before first action (PZip compressed)
```

---

### Step 4: Sealing (chmod 444)

**When the run completes (all steps executed or error encountered):**

1. Final snapshot captured: `after_snapshot.html` written (PZip compressed)

2. `actions.json` is closed and finalized

3. `bundle.sha256` is computed:

```bash
# Computed over all files in the run_id directory
sha256sum ~/.solace/evidence/{run_id}/* > bundle.sha256
# Plus a BUNDLE line: sha256 of all individual sha256 values concatenated
```

4. All files are sealed:

```bash
chmod 444 ~/.solace/evidence/{run_id}/*
# Applies to: manifest.json, actions.json, approval.json,
#             before_snapshot.html, after_snapshot.html,
#             screenshots/*.png, bundle.sha256
```

5. The bundle hash is appended to `~/.solace/audit_chain.jsonl`:

```json
{
  "seq": 1043,
  "ts": "2026-03-03T14:30:41.000Z",
  "run_id": "gmail-inbox-triage-20260303-143019",
  "bundle_hash": "sha256:BUNDLE_HASH",
  "prev_hash": "sha256:PREV_BUNDLE_HASH",
  "chain_hash": "sha256:SHA256(bundle_hash + prev_hash)"
}
```

**After this point, no file in the run directory can be modified by any
process. The evidence is final.**

---

### Step 5: Hash Chain Verification

**After sealing, the system automatically verifies the chain:**

```bash
python3 -m solace_browser.audit --verify-last
# Expected: Chain intact. Entry 1043 verified. prev_hash matches entry 1042.
```

**If chain verification fails:**

1. Alert is displayed to the user: "Chain integrity error. Contact support."
2. No further runs are allowed until the issue is resolved.
3. Do NOT attempt to repair the chain manually.
4. Document the error in the deviation log.
5. Contact Solace AGI support with the chain_report.json.

---

### Step 6: Archive

**After sealing and verification, the run is available in the evidence store:**

```
Local:  ~/.solace/evidence/{run_id}/   (always available)
Cloud:  solaceagi.com evidence vault   (if cloud sync is enabled)
```

**Cloud sync (optional, requires Dragon or Enterprise tier):**

```bash
# Manual sync
python3 -m solace_browser.sync --run-id {run_id}

# Automatic sync (every 30 minutes if enabled in settings)
# Encrypted with AES-256-GCM before transmission
# Solace AGI servers cannot read the content
```

**Retention:**

| Tier | Local Retention | Cloud Retention |
|------|----------------|----------------|
| Free | Forever (local disk) | None |
| Dragon ($8/mo) | Forever | 30 days |
| Enterprise ($99/mo) | Forever | 365 days |

Evidence is never deleted by the system. The user may delete local files
manually. Cloud evidence follows the retention tier schedule.

---

## Verification

### Routine Verification (after each run)

The system displays in the evidence viewer:

```
Run: gmail-inbox-triage-20260303-143019
Status: SEALED
Actions: 7
Duration: 22 seconds
Bundle hash: sha256:f2ca1bb6c7...
Chain entry: #1043
Chain status: INTACT
Approved by: Phuc Truong at 2026-03-03 14:30:19 UTC
```

### Monthly Chain Verification

See SOP-02 (in Paper 40: Validation Protocol) for the monthly chain
verification procedure.

### Pre-Submission Verification

Before any regulatory submission, run:

```bash
python3 -m solace_browser.audit --verify-chain --full
python3 -m solace_browser.audit --export \
  --date-range "YYYY-MM-DD:YYYY-MM-DD" \
  --output pre_submission_audit.zip \
  --include-chain-proof
python3 -m solace_browser.audit --verify-export pre_submission_audit.zip
```

All three commands must complete without errors before submission.

---

## Non-Conformance

### What Constitutes Non-Conformance

| Finding | Severity | Required Action |
|---------|----------|----------------|
| Chain break detected | CRITICAL | Stop all runs. Document. Contact support. CAPA. |
| Run completed without approval.json | CRITICAL | Investigate immediately. This should be impossible. |
| bundle.sha256 does not match re-computation | HIGH | Quarantine the run. Document. Contact support. |
| Timestamp delta < 0 (out-of-order) | HIGH | Investigate. May indicate clock tampering. |
| chmod 444 not applied after seal | MEDIUM | Apply manually. Document. Review seal code. |
| Cloud sync failed | LOW | Retry. If persistent, document and notify admin. |

### Non-Conformance Documentation Template

```
Date: YYYY-MM-DD
Run ID: (if applicable)
Finding: (description)
Severity: CRITICAL / HIGH / MEDIUM / LOW
Detected by: (user / system / auditor)
Immediate action taken:
Root cause (if known):
CAPA reference: (if applicable)
Closed by: (name + date)
```

Non-conformance records are themselves Part 11 records. They must be
dated, signed, and retained with the same rigor as evidence bundles.

---

## Related Documents

| Document | Location |
|---------|---------|
| Paper 40: Part 11 Compliance + Self-Certification | `papers/40-part11-compliance-selfcert.md` |
| Paper 06: ALCOA+ Compliance Detail | `papers/06-part11-evidence-browser.md` |
| Paper 07: Budget Wallet Enforcement | `papers/07-budget-wallet-enforcement.md` |
| Diagram 40: Evidence Chain FSM | `data/default/diagrams/40-part11-evidence-chain.md` |
| ALCOA+ Mapping Diagram | `data/default/diagrams/part11-alcoa-mapping.md` |

---

## Version History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-03-03 | Solace AGI | Initial release |

---

## Signatures

This SOP is effective as of the date above and supersedes all previous
informal procedures for evidence capture.

```
Prepared by:  Solace AGI Development Team
Reviewed by:  [Quality Owner — to be designated by regulated user's organization]
Approved by:  [Responsible Person — 21 CFR §11.50]
Date:         2026-03-03
SOP ID:       SOP-01
Version:      1.0
```

Regulated users operating under GxP, HIPAA, or similar frameworks should
have this SOP reviewed and co-signed by their Quality Management System
owner before use in regulated activities. The SOP as written is the vendor's
declaration of the system's designed behavior. The responsible person at the
regulated organization is accountable for qualification and validation in
their specific context.
