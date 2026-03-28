# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native human approval and intervention visibility

## Current Round

SAH18 native human-in-the-loop visibility.

The Dev workspace now shows worker identity, diagrams, inbox/outbox structure, assignment packet, and execution mode/convention state. The next step is to make the human first-class in the same workspace: who must approve, what is blocked pending human review, what the current intervention state is, and how the reviewer can see the human gate without leaving the workspace.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose the human approval and intervention gate directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native human approval and intervention visibility surface to the Dev workspace while preserving the current role stack, worker detail, inbox/outbox visibility, assignment packet, execution mode/convention visibility, run history, inspection context, and artifact inspection behavior.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI4 — AI Workers as Orchestrated Systems, Not Models.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
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
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, run history, inspection context, and artifact preview surfaces
- the workspace must show human approval or intervention status for the active worker context
- the workspace must show whether the current worker/run is waiting on human approval, already approved, or not yet at a human gate
- the workspace must show the human gate using visible grounded context from the current role/run state; do not invent approvals the repo/runtime does not know about
- if the human gate is only partially known, show that honestly
- keep the approval/intervention surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still does not show human approval/intervention state directly
- a reviewer still cannot tell whether the active worker/run is blocked on human input
- human gate state is presented as fake certainty instead of visible grounded context
- the round only adds diagrams or labels without making human review more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible human approval/intervention surface in the Dev workspace
2. one visible tie between approval/intervention state and the active worker/run context
3. one honest blocked / approved / not-at-gate representation
4. one Prime Mermaid source artifact for human approval/intervention visibility
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible human approval/intervention surface
Objective: make the human gate first-class.
Scope: show whether the active worker/run is waiting on human approval, already approved, needs intervention, or is not yet at a human gate.
Done when: a reviewer can tell the human gate state from inside the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie approval/intervention to active worker/run context
Objective: stop treating the human gate as detached theory.
Scope: the approval/intervention surface should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which worker/run is blocked, approved, or still autonomous and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest human gate states
Objective: make review status operationally truthful.
Scope: support at least `awaiting_human`, `approved`, `intervention_required`, and one honest fallback like `not_yet_at_gate` or `unknown`.
Done when: the workspace does not imply fake approval state.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one human-gate Prime Mermaid artifact
Objective: capture the move from implicit human review to visible workspace state.
Scope: add one Prime Mermaid artifact for human approval/intervention visibility.
Done when: the human gate surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make human gate visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to human approval/intervention inspection
- one automated test or lightweight scripted verification for the approval/intervention surface
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
- rewriting the role stack instead of making the human gate more visible
