# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native drift detection and adaptive replay visibility

## Current Round

SAD22 native drift detection and adaptive replay visibility.

The Dev workspace now shows worker identity, diagrams, inbox/outbox structure, assignment packet, execution mode/convention state, human gate state, proof state, execution graph state, and convention-store state. The next step is to surface drift and replay adaptation: what changed, when replay is safe, when replay is blocked by drift, and what fallback path the system is using.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose drift detection and adaptive replay state directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native drift detection and adaptive replay visibility surface to the Dev workspace while preserving the current role stack, worker detail, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, run history, inspection context, and artifact inspection behavior.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI11 — Discover vs Replay Modes.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI12 — Drift Detection and Adaptive Replay.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdm0-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdd1-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdc2-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdq3-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdx4-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdh5-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdr6-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdi7-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sda8-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sav9-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sat10-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sap11-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sau12-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sac13-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-saw14-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sai15-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-saa16-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sam17-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sah18-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sat19-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sag20-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sac21-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, run history, inspection context, and artifact preview surfaces
- the workspace must show drift detection or replay safety state for the active worker/run
- the workspace must show at least one visible adaptive replay outcome, such as `safe_replay`, `drift_detected`, `fallback_to_discover`, or an honest equivalent
- do not invent drift signals the repo/runtime does not know about
- if replay safety is role-derived rather than runtime-native, show that honestly
- keep the drift/adaptive replay surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still does not show drift or replay-safety state directly
- a reviewer still cannot tell whether replay is safe for the active worker/run
- drift state is presented as fake certainty instead of visible grounded context
- the round only adds diagrams or labels without making adaptive replay more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible drift/adaptive replay surface in the Dev workspace
2. one visible tie between drift/replay state and the active worker/run context
3. one honest representation of replay-safe, drifted, and fallback states
4. one Prime Mermaid source artifact for drift/adaptive replay visibility
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible drift/adaptive replay surface
Objective: make replay safety first-class.
Scope: show whether the active worker/run is replay-safe, drifted, or falling back to discover mode.
Done when: a reviewer can tell replay safety from inside the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie drift/replay state to active worker/run context
Objective: stop treating adaptive replay as detached theory.
Scope: the drift surface should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which worker/run the drift state belongs to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest drift states
Objective: make replay safety operationally truthful.
Scope: support at least a visible replay-safe state, a drift-detected state, and one fallback/discover state.
Done when: the workspace does not imply fake replay safety.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one drift/adaptive replay Prime Mermaid artifact
Objective: capture the move from implicit drift handling to visible workspace state.
Scope: add one Prime Mermaid artifact for drift/adaptive replay visibility.
Done when: the drift surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make drift/adaptive replay visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to drift/replay inspection
- one automated test or lightweight scripted verification for the drift surface
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `specs/solace-dev/`
- `tests/`
- `scripts/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample response payloads
- artifact/report paths
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- adding new specialist roles beyond manager, design, coder, and QA
- broad cloud sync, billing, or `solaceagi` work
- unrelated Chromium platform changes
- rewriting the role stack instead of making drift and adaptive replay more visible
