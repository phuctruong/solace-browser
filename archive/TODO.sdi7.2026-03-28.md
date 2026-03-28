# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for durable Solace Dev run history

## Current Round

SDI7 hydrated last-known run state and run-history inspection.

The workspace can now show live role counts and inspect a run after you click a worker action in the current session. The next step is to make run inspection durable and recoverable: when the Dev workspace loads, it should be able to show the latest known run/report/event state for the active role stack even before a new click happens.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA have durable, inspectable run history and last-known run state in the browser itself`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `manager`
- `task_statement`: `Hydrate the Dev workspace with durable last-known run state and a first real run-history inspection path for the active Solace worker stack.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdm0-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdd1-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdc2-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdq3-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdx4-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdh5-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdr6-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/live-workspace-hydration.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-feedback-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-inspection-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/files.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/app_engine/runner.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current live workspace and run inspection surface
- the outcome must make run state durable and re-hydratable, not just prettier after a click
- use real runtime or filesystem-backed run/report/event data
- do not invent fake last-run ids, fake history entries, or fake artifact state
- if runtime support is missing, add the minimum honest support needed
- keep Prime Mermaid as the source-of-truth for run-history and last-known-state flow
- do not expand into cloud sync, billing, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still loses useful run inspection state on reload
- a user still cannot see a last-known run/report/event surface until after triggering a new run
- there is no first run-history path for the active role stack
- the browser still cannot show a durable path from role -> latest known run -> report or events
- the round only adds more diagrams without making run state more durable

## Required Deliverables

You must produce all of these:

1. one hydrated last-known run surface in the Dev workspace
2. one run-history or recent-runs inspection path
3. one visible durable path from role to latest report or event state
4. one Prime Mermaid source artifact for run-history or last-known-state flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Hydrate last-known run state
Objective: make the workspace useful even before a new run is clicked.
Scope: load the latest known run/report/event state for at least the active role stack from real runtime or filesystem-backed data.
Done when: a reviewer can open the workspace and see real last-known run state without first triggering a new run.
Evidence required: screenshots, routes exercised, and sample payloads.

### Ticket 2: Add one run-history path
Objective: move beyond one ephemeral last-run badge.
Scope: expose one recent-runs list, recent-run selector, or recent-run inspection path tied to the active role stack.
Done when: a reviewer can inspect more than the single current action result.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Add durable report/event inspection
Objective: make the latest run truly recoverable.
Scope: expose a durable path from role to latest report or event surface, even after reload.
Done when: a reviewer can navigate from the workspace to a real last-known report or event inspection path without clicking run first.
Evidence required: screenshots, sample response payloads, and artifact/report paths.

### Ticket 4: Add one Prime Mermaid durable-state artifact
Objective: capture the move from immediate feedback to durable run state.
Scope: add one Prime Mermaid artifact for last-known run hydration and one for recent-run inspection if needed.
Done when: the durable run-state flow is represented as committed source truth.
Evidence required: artifact paths and one short note on what each diagram governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make the durable run-state surface reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to last-known run inspection
- one automated test or lightweight scripted verification for durable run-state hydration
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/apps.rs`
- `solace-runtime/src/routes/files.rs`
- `solace-runtime/src/app_engine/runner.rs`
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
- rewriting the role stack instead of making run state durable
