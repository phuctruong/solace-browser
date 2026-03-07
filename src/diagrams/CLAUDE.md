# CLAUDE.md — solace-browser Diagram Specification

**Scope:** All diagrams in `src/diagrams/` for the solace-browser project.
**Rule:** Diagrams describe the browser's runtime behavior — local execution, not cloud orchestration. If a feature belongs to stillwater/cli or solaceagi.com backend, it does not appear in these diagrams.

---

## Files and Purpose

| File | What It Specifies |
|------|-------------------|
| `01-auth-flow.md` | Full auth precondition chain: Firebase → sw_sk_ → vault → LLM mode → app grid → OAuth3 gate |
| `02-component-hierarchy.md` | Static component tree: app shell → runner/auth/approval/history; API client layers |
| `03-recipe-execution.md` | Recipe state machine + deterministic input-merge → step-replay → evidence-seal flow |
| `04-evidence-collection.md` | Per-step hash chain construction; two streams (evidence + audit) sharing run_id |
| `05-customization-flow.md` | Inbox → validate → merge → execute → outbox pattern |
| `06-session-management.md` | Browser session lifecycle bound to OAuth3 token; immediate stop on revocation |
| `07-approval-stepup-flow.md` | Risk tier classification → modal (30s timeout defaults to deny) → evidence write |
| `08-4-plane-architecture.md` | Four independent planes: Capture, Control, Execution, Evidence |
| `09-oauth3-auth-proxy.md` | 3-layer defense: port 9222 auth proxy → hidden Chrome port 9225 |
| `10-capture-pipeline.md` | page.on('load') → DOM snapshot → Prime Mermaid → PZip 100% RTC |
| `11-app-inbox-outbox.md` | Universal folder contract: inbox (user teaches) → outbox (AI shows work) |
| `12-yinyang-dual-rail.md` | Top rail (32px status) + bottom rail (36-300px chat) [SUPERSEDED by D23] |
| `13-budget-gates.md` | B1-B5 fail-closed budget gate sequence with MIN-cap resolution |
| `14-preview-approve-execute.md` | Full app lifecycle: intent → budget → preview → approve → seal → execute → evidence |
| `15-competitive-position.md` | 8 structural advantages vs 19 competitors, feature matrix |
| `23-three-surface-architecture.md` | Companion + Sidebar + API: 3 surfaces, port map, before/after (Paper 47) |
| `24-sidebar-tab-flow.md` | Tab state machine, app detection sequence, run flow (Paper 47) |
| `25-ipc-native-messaging.md` | Token bootstrap, security boundaries, process lifecycle (Paper 47, 48) |

---

## Key Invariants

### Auth invariants
1. **Auth is the precondition for all app execution** — no recipe runs without a valid sw_sk_ key stored in `~/.solace/vault.enc`.
2. **Token revocation is enforced at gate time, not lazily** — the OAuth3 scope gate checks revocation status before every run, not once at session start.
3. **sw_sk_ key is shown to user exactly once** — at issuance. It is then stored encrypted (AES-256-GCM) in `~/.solace/vault.enc`. Never shown again.
4. **LLM mode selection (BYOK or Managed) happens after auth** — no LLM calls before the user has authenticated and chosen a mode.

### Recipe execution invariants
5. **No dynamic regeneration of the workflow graph during a run** — the step graph is fixed at recipe load time. Steps cannot add or remove other steps mid-execution.
6. **Step transitions must be reproducible from recipe + inputs alone** — deterministic replay is a hard requirement, not a goal.
7. **APPROVAL state is always first** — no recipe reaches PRECHECK without explicit user approval. Timeout defaults to DENY, not PROCEED.
8. **Evidence seal happens before cost reporting** — EVIDENCE_SEAL precedes COST in the state machine. Never reversed.

### Evidence invariants
9. **Hash chain is written per-step, not at end of run** — each step writes an event, captures artifacts, and links `prev_hash` before proceeding to the next step.
10. **Two separate evidence streams share one run_id** — `evidence_chain.jsonl` (action artifacts) and `oauth3_audit.jsonl` (scope decisions) are written separately and validated together at seal time.
11. **Hash chain is validated on evidence retrieval** — a broken chain is surfaced to the user, not silently accepted.

### Session invariants
12. **Session is bound to an OAuth3 token** — browser session operations are blocked immediately when the token is revoked or expired.
13. **Session lifecycle emits audit events for start, stop, and failure** — no silent session termination.
14. **Scoped actions are restricted to allowed domains declared in the token** — the session cannot act outside its declared scope.

### Customization invariants
15. **Overrides are validated before merge, not after** — if `inbox/` overrides fail validation, execution is blocked with an explanation. The fail-closed path is explicit.
16. **App defaults are never silently overwritten** — merge produces a resolved config; the user's overrides layer on top of, but do not erase, app defaults.
17. **Power users can supply diagram overrides in `inbox/diagrams/`** — these override the app's default FSM for the customized run only.

### Approval invariants
18. **Timeout defaults to deny** — a 30-second approval window that expires with no user action is treated identically to an explicit denial.
19. **High-risk scopes always require step-up** — send, delete, and financial scopes require step-up authentication regardless of session state or prior approvals.
20. **Approval record is written before evidence artifacts** — the LOG node precedes the EVID node in the approval flow. The approval decision is always the first evidence item for an action.

---

## Forbidden Paths (Cannot Appear in Any Diagram)

1. **Recipe execution without prior approval** — no path from LOAD_INPUTS that bypasses APPROVAL.
2. **Step execution after OAuth3 revocation** — if revocation is detected mid-session, the current operation completes (if already started) but no new steps begin.
3. **Evidence seal before all steps complete** — EVIDENCE_SEAL is the final step; it cannot appear earlier in the state machine.
4. **Inbox overrides bypassing validation** — no path from "user edits inbox files" directly to "execute recipe" without validation.
5. **Approval timeout proceeding** — timeout is not a third option between approve and deny; it is equivalent to deny.
6. **Yinyang auto-approving actions** — Yinyang chat can suggest and preview, but PREVIEW_READY → APPROVED always requires explicit user click. No auto-approve path.
7. **Self-learning/mutation during execution** — no diagram should show the browser modifying its own recipes, CPU nodes, or skill files during a run.

---

## OAuth3 Scope Gate Rules (from 01-auth-flow.md)

```
Every app run:
  1. OAuth3 scope gate checks before recipe execution
  2. Scope must match the action type (read/write/admin)
  3. Token revocation check is synchronous (not cached)
  4. Gate fail → BLOCKED (fail-closed), never degrade to lower scope

Step-up required for:
  - medium/high risk tier actions (07-approval-stepup-flow.md)
  - send, delete, financial scope operations
  - Any action that modifies persistent state outside the browser session

Step-up NOT required for:
  - Read-only browsing
  - Artifact capture (screenshots, DOM text)
  - Evidence writing (local only, no external mutation)
```

---

## Four-Plane Invariants (Diagrams 08-15)

21. **ALL PZip computation is client-side** — zero cloud compute for capture, compression, or verification.
22. **100% RTC must pass before ripple is stored** — sha256(reconstructed) == sha256(original).
23. **Port 9222 is auth proxy, port 9225 is hidden Chrome** — no raw CDP access without valid Bearer token.
24. **Inbox is user-controlled, outbox is AI-controlled** — AI reads inbox, writes outbox, never crosses.
25. **Top rail = status only, bottom rail = chat + approval** — never mixed. Two surfaces, two jobs.
26. **Budget gates are fail-closed** — B1-B5 sequential check, any failure = BLOCKED.
27. **Web-native: no vendor API keys** — browser operates web versions of all services directly.
28. **Stillwater versions never deleted** — Part 11 requires preserving all previous states.

---

## Deployment Context (What These Diagrams Cover)

These diagrams cover the **local execution layer** only:

```
solace-browser (local, these diagrams)
  ├── Auth: Firebase → sw_sk_ key → vault
  ├── Recipe runner: deterministic, inbox-driven
  ├── Evidence: per-step hash chain, two streams
  ├── Approval: risk-tier modal, fail-closed
  └── Session: OAuth3 token bound, revocable

NOT covered here (see stillwater/data/default/diagrams/):
  - Triple-twin orchestration (stillwater/cli)
  - Rung validation (stillwater store)
  - LLM provider routing (llm_client.py)
  - OAuth3 token issuance (OAuth3 Authority service)
  - Cloud vault sync (solaceagi.com backend)
```
