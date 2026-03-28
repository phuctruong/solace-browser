# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native execution mode and convention visibility

## Current Round

SAM17 native execution mode and convention visibility.

The Dev workspace now shows worker identity, diagrams, inbox/outbox structure, and assignment packets. The next step is to show whether the active worker is in discover or replay mode and what convention or reusable program object governs the current run, so the workspace makes mode and reuse visible instead of leaving them implicit.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose the active execution mode and governing convention object directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native execution mode and convention visibility surface to the Dev workspace while preserving the current role stack, worker detail, inbox/outbox visibility, assignment packet, run history, inspection context, and artifact inspection behavior.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI9 — Conventions as the Core Product Object.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI10 — The Solace Execution Graph.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI11 — Discover vs Replay Modes.md`
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
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace, worker detail, diagram access, inbox/outbox visibility, assignment packet, run history, inspection context, and artifact preview surfaces
- the workspace must show discover vs replay mode for the active worker context
- the workspace must show one visible convention or reusable program object for the active worker context
- do not invent live mode or convention state the repo/runtime does not know about
- if the current mode or convention is only partially known, show that honestly
- keep convention visibility compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still does not show discover vs replay mode directly
- a reviewer still cannot see which convention or reusable program object governs the active worker
- mode or convention state is presented as fake certainty instead of visible grounded context
- the round only adds diagrams or labels without making execution mode and reuse more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible execution mode surface in the Dev workspace
2. one visible convention or reusable program object surface in the Dev workspace
3. one explicit tie between mode/convention visibility and the active worker context
4. one Prime Mermaid source artifact for execution mode and convention visibility
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible execution mode surface
Objective: make discover vs replay mode explicit.
Scope: show whether the active worker is operating in discover mode, replay mode, or an honest partial/unknown state.
Done when: a reviewer can tell the active execution mode from inside the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Add a visible convention surface
Objective: make reuse visible.
Scope: show the current convention, reusable program object, or governing reusable artifact for the active worker.
Done when: a reviewer can tell what reusable structure the current worker is following.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Tie mode/convention to active worker context
Objective: stop treating execution mode and reuse as detached theory.
Scope: the mode/convention surface should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which worker’s mode/convention is being inspected and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one mode/convention Prime Mermaid artifact
Objective: capture the move from implicit execution semantics to visible workspace state.
Scope: add one Prime Mermaid artifact for execution mode and convention visibility.
Done when: the mode/convention surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make mode/convention visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to mode/convention inspection
- one automated test or lightweight scripted verification for the mode/convention surface
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
- rewriting the role stack instead of making execution mode and conventions more visible
