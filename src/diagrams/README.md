# solace-browser Diagram Index

**Sources:** 20 files (19 active + 1 deprecated), ~37 KB
**Purpose:** Mermaid diagrams for solace-browser runtime: auth, recipe execution, evidence, approval, session management, customization, 4-plane architecture, capture pipeline, app inbox/outbox, Yinyang dual rail, budget gates, and competitive position. Aligned to deterministic, fail-closed, consent-native execution.

---

## File Index

| File | Purpose |
|------|---------|
| `01-auth-flow.md` | Firebase login → sw_sk_ key issuance → vault storage → LLM mode selection → app grid unlock → OAuth3 scope gate per action |
| `01-authentication-flow.md` | **DEPRECATED** — replaced by `01-auth-flow.md` |
| `02-component-hierarchy.md` | Browser app shell components: auth manager, recipe runner, approval modal, history viewer; API layers (/browser/*, /fs/*, /evidence/*) |
| `03-recipe-execution.md` | Recipe execution state machine (APPROVAL → PRECHECK → LOAD_INPUTS → EXECUTE_STEPS → EVIDENCE_SEAL → COST → COMPLETE); deterministic step replay |
| `04-evidence-collection.md` | Per-step event write → screenshot/DOM capture → hash chain (evidence_chain.jsonl + oauth3_audit.jsonl) → seal bundle → vault upload |
| `05-customization-flow.md` | Inbox file load → validate overrides → merge with app defaults → execute recipe → write outbox + evidence |
| `06-session-management.md` | Browser session lifecycle: OAuth3 token bind → revocation check → scoped actions → keepalive → release |
| `07-approval-stepup-flow.md` | Risk tier → standard approval or step-up → 30s approval modal → execute or fail-closed → write approval record + evidence |
| `08-4-plane-architecture.md` | Four independent planes: Capture (always-on), Control (OAuth3), Execution (recipes), Evidence (hash-chain) |
| `09-oauth3-auth-proxy.md` | 3-layer defense: port 9222 auth proxy, port 9225 hidden Chrome, session token exchange |
| `10-capture-pipeline.md` | page.on('load') → DOM snapshot → Prime Mermaid → PZip 100% RTC verification → ripple storage |
| `11-app-inbox-outbox.md` | Universal folder contract: user inbox (prompts, templates, assets, policies) → AI outbox (previews, drafts, reports, suggestions) |
| `12-yinyang-dual-rail.md` | Top rail (32px status) + bottom rail (36-300px chat): integration with app lifecycle and approval flow |
| `13-budget-gates.md` | B1-B5 fail-closed budget gate sequence with MIN-cap resolution and delegation chains |
| `14-preview-approve-execute.md` | Full app lifecycle: trigger → budget → LLM preview → approve → seal → cooldown → CPU execute → evidence |
| `15-competitive-position.md` | 8 structural advantages vs 19 competitors, feature matrix, pricing, no-API exclusives |
| `16-cross-app-orchestration.md` | Cross-app message flow, partner discovery, orchestrator pattern, B6 budget gate, required app directory structure |
| `17-yinyang-delight-pipeline.md` | Warm token → delight effect pipeline, Yinyang universal interface, plugin architecture, alert queue |
| `18-app-ecosystem-day-one.md` | 18 day-one apps (10 standard + 5 no-API + 3 orchestrators), safety tiers, cross-app partner map |
| `19-browser-release-loop.md` | Compile -> upload -> download -> head-on smoke -> production API matrix with fail gates and metrics writeback |

---

## Color Legend

solace-browser diagrams use Mermaid defaults (no custom classDef) — no explicit color coding conventions beyond Mermaid's default node styling.

---

## Runtime Control API

The active browser webservice is `solace_browser_server.py`. Snapshot and control consumers should use `/api/status`, `/api/navigate`, `/api/snapshot`, `/api/evaluate`, `/api/aria-snapshot`, `/api/dom-snapshot`, and `/api/page-snapshot`.

## Architecture Rules Reflected in Diagrams

- **Yinyang dual rail for chat + status** — top rail = status (32px), bottom rail = chat (36-300px); Yinyang can trigger apps but PREVIEW_READY → APPROVED always requires explicit user click (see 12)
- **No triple-twin orchestration** — solace-browser does not run the triple-twin; that lives in stillwater/cli
- **No runtime self-learning mutation** — CPU learner does not run in browser; recipes are static graphs
- **Inbox-driven customization before execution** — overrides are validated and merged before any step runs (see 05)
- **OAuth3 gate before every sensitive operation** — scope check is a hard gate, not advisory (see 01, 06)
- **Approval is precondition, not afterthought** — approval modal fires before execution, timeout defaults to deny (see 07)
- **Evidence is parallel to execution, not post-hoc** — hash chain written per step, not at end (see 04)
- **Fail-closed everywhere** — OAuth3 denied, timeout, validation failure, revocation all route to blocked/stopped (see 01, 05, 06, 07)

---

## Key Mermaid: Auth + Recipe Execution Flow

```mermaid
flowchart TD
    V[Visit solace-browser] --> F[Firebase auth]
    F --> K[Server issues sw_sk_ key]
    K --> E[Store encrypted in ~/.solace/vault.enc]
    E --> L[LLM mode: BYOK or Managed]
    L --> GRID[Unlock app grid]

    GRID --> REQ[Run request]
    REQ --> GATE[OAuth3 scope gate]
    GATE -->|pass| APPROVAL[Approval modal 30s]
    GATE -->|fail| BLOCKED_A[Blocked fail-closed]

    APPROVAL -->|approve| RECIPE[Recipe execution]
    APPROVAL -->|deny/timeout| BLOCKED_B[Blocked fail-closed]

    RECIPE --> STEPS[LOAD_INPUTS → EXECUTE_STEPS\ndeterministic step replay]
    STEPS --> EVIDENCE[EVIDENCE_SEAL\nhash chain + manifest]
    EVIDENCE --> UPLOAD[Vault upload]
```

---

## Key Mermaid: Evidence Hash Chain (04)

```mermaid
flowchart TD
    START[Run started] --> EVT[Per-step event write]
    EVT --> ART[Capture screenshot + DOM text]
    ART --> HASH[Compute hash + link prev_hash]
    HASH --> CHAIN[evidence_chain.jsonl]
    EVT --> AUDIT[oauth3_audit.jsonl]
    CHAIN --> SEAL[Seal bundle + manifest digest]
    AUDIT --> SEAL
    SEAL --> UPLOAD[Vault upload]
```

Note: Audit stream and evidence stream are separate JSONL files sharing the same `run_id`. The hash chain is validated on evidence retrieval.

---

## Key Mermaid: Approval + Step-Up (07)

```mermaid
flowchart TD
    REQ[Action requested] --> RISK{Risk tier}
    RISK -->|low| AUTO[Standard approval path]
    RISK -->|medium/high| STEPUP[Step-up required]

    AUTO --> MODAL[Approval modal 30s]
    STEPUP --> MODAL

    MODAL -->|approve| EXEC[Execute action]
    MODAL -->|deny/timeout| BLOCK[Blocked fail-closed]

    EXEC --> LOG[Write approval record + audit logs]
    LOG --> EVID[Capture evidence artifacts]
```

High-risk scopes (send, delete, financial) always require step-up regardless of prior approval history.
