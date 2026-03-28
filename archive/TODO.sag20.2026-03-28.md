# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native execution-graph visibility

## Current Round

SAG20 native execution-graph visibility.

The Dev workspace now shows worker identity, diagrams, inbox/outbox structure, assignment packet, execution mode/convention state, human gate state, and proof state. The next step is to surface the execution graph itself: what nodes the current worker/run is traversing, what stage is active, and how the graph structure connects planning, execution, validation, and evidence.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose the active execution graph directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native execution-graph visibility surface to the Dev workspace while preserving the current role stack, worker detail, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, run history, inspection context, and artifact inspection behavior.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI10 — The Solace Execution Graph.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
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
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, run history, inspection context, and artifact preview surfaces
- the workspace must show the execution graph state for the active worker/run
- the workspace must show at least the active node or stage, the graph path shape, and how execution, validation, and evidence relate
- do not invent runtime graph semantics the repo/runtime does not know about
- if graph state is partial or role-derived rather than runtime-native, show that honestly
- keep the graph surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still does not show execution graph structure directly
- a reviewer still cannot tell how the current worker/run maps to a graph or staged flow
- graph state is presented as fake certainty instead of visible grounded context
- the round only adds diagrams or labels without making the orchestration path more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible execution-graph surface in the Dev workspace
2. one visible tie between graph state and the active worker/run context
3. one honest representation of active stage/node/path state
4. one Prime Mermaid source artifact for execution-graph visibility
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible execution-graph surface
Objective: make orchestration structure first-class.
Scope: show the graph or staged path for the active worker/run directly in the workspace.
Done when: a reviewer can tell the orchestration path from inside the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie graph state to active worker/run context
Objective: stop treating graph structure as detached theory.
Scope: the graph surface should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which worker/run the graph belongs to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest graph state
Objective: make orchestration visibility operationally truthful.
Scope: support at least a visible active stage/node plus one honest partial/unknown state if the graph is not fully runtime-native yet.
Done when: the workspace does not imply fake graph certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one execution-graph Prime Mermaid artifact
Objective: capture the move from implicit orchestration to visible workspace state.
Scope: add one Prime Mermaid artifact for execution-graph visibility.
Done when: the graph surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make graph visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to execution-graph inspection
- one automated test or lightweight scripted verification for the graph surface
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
- rewriting the role stack instead of making execution-graph state more visible
