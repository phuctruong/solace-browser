# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native transparency and proof visibility

## Current Round

SAT19 native transparency and proof visibility.

The Dev workspace now shows worker identity, diagrams, inbox/outbox structure, assignment packet, execution mode/convention state, and the human gate. The next step is to make transparency itself first-class: what proof surfaces exist for the active worker/run, what evidence is visible in Hub, what remains unproven, and how a reviewer can inspect proof status without leaving the workspace.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose proof, evidence, and transparency state directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native transparency and proof visibility surface to the Dev workspace while preserving the current role stack, worker detail, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
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
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, run history, inspection context, and artifact preview surfaces
- the workspace must show the proof/transparency state for the active worker/run
- the workspace must show what evidence is visible, what proof artifacts are available, and what remains missing or unproven
- do not invent proof or evidence the repo/runtime does not know about
- if proof status is partial or unknown, show that honestly
- keep the transparency/proof surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still does not show proof or transparency state directly
- a reviewer still cannot tell what evidence exists for the active worker/run
- proof state is presented as fake certainty instead of visible grounded context
- the round only adds diagrams or labels without making reviewability more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible transparency/proof surface in the Dev workspace
2. one visible tie between proof state and the active worker/run context
3. one honest representation of `proven`, `partial`, `missing`, or similarly grounded proof states
4. one Prime Mermaid source artifact for transparency/proof visibility
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible transparency/proof surface
Objective: make evidence review first-class.
Scope: show proof state, visible evidence surfaces, and missing proof directly inside the workspace.
Done when: a reviewer can tell the proof state from inside the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie proof state to active worker/run context
Objective: stop treating transparency as detached theory.
Scope: the transparency/proof surface should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which worker/run the proof state belongs to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest proof states
Objective: make proof visibility operationally truthful.
Scope: support at least a visible `proven`, `partial`, and `missing` or equivalent grounded state model.
Done when: the workspace does not imply fake proof completeness.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one transparency/proof Prime Mermaid artifact
Objective: capture the move from implicit traceability to visible workspace state.
Scope: add one Prime Mermaid artifact for transparency/proof visibility.
Done when: the proof surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make transparency/proof visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to proof/transparency inspection
- one automated test or lightweight scripted verification for the proof/transparency surface
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
- rewriting the role stack instead of making proof/transparency more visible
