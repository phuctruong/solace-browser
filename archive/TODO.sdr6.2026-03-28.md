# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for live Solace Dev run inspection

## Current Round

SDR6 run records and artifact inspection.

The integrated Dev workspace is now live enough to show runtime/backoffice-backed counts and visible run feedback. The next step is to make worker execution inspectable: last run record, last report path, event link, and artifact visibility for the active role stack, so a human can move from “I clicked run” to “I can inspect what happened” without leaving the workspace.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA can be run and their latest runs, reports, events, and artifacts can be inspected from the browser itself`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `qa`
- `task_statement`: `Add the first real run-record and artifact inspection surfaces to the live Dev workspace for solace-browser itself.`
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
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-source-map.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/integrated-dev-workspace.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/live-workspace-hydration.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-feedback-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/app_engine/runner.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current live workspace; do not replace it with another shell
- the outcome must make worker execution more inspectable, not merely more decorative
- use real runtime or filesystem-backed run/report data where possible
- do not invent fake run ids, fake report links, or fake event paths
- if a runtime gap prevents a full run-record view, expose the honest boundary and add the minimum runtime support needed
- keep Prime Mermaid as the source-of-truth for run-record and artifact-inspection flow
- do not expand into cloud sync, billing, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- a user still cannot inspect a real last run/report/event surface from the workspace
- worker run feedback still stops at a generic success/failure pill
- there is no visible artifact inspection path for the active role stack
- the browser cannot show a real path from role -> run -> report or role -> run -> events
- the round only adds more diagrams without making worker execution more inspectable

## Required Deliverables

You must produce all of these:

1. one visible last-run inspection surface in the Dev workspace
2. one visible report or artifact inspection path in the Dev workspace
3. one visible event or run-detail path for worker execution
4. one Prime Mermaid source artifact for run-record or artifact-inspection flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add last-run inspection
Objective: make the latest worker execution inspectable.
Scope: show the latest run state in the Dev workspace with at least app id, status, and a real report path or run id.
Done when: a reviewer can see a real last-run surface after a worker action.
Evidence required: screenshots, routes exercised, and sample payloads.

### Ticket 2: Add report or artifact inspection
Objective: move from run status to inspectable output.
Scope: add a visible path to open the latest report, artifact, or run output for the current worker stack.
Done when: a reviewer can navigate from the workspace to a real artifact or report path without guessing hidden filesystem locations.
Evidence required: screenshots, artifact paths, and sample response payloads.

### Ticket 3: Add event or run-detail visibility
Objective: make worker execution traceable.
Scope: expose one run-detail or events path in the workspace, using existing runtime APIs or the minimum new support required.
Done when: a reviewer can inspect more than just success/failure text.
Evidence required: routes exercised, screenshots, and one short walkthrough.

### Ticket 4: Add one Prime Mermaid inspection artifact
Objective: capture the move from live status to inspectable execution.
Scope: add one Prime Mermaid artifact for run-record inspection and one for artifact/report inspection if needed.
Done when: the execution-inspection path is represented as committed source truth.
Evidence required: artifact paths and one short note on what each diagram governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make the inspection surface reviewable and repeatable.
Scope:
- one documented local smoke path from workspace to worker run to last-run/report inspection
- one automated test or lightweight scripted verification for the new inspection surface
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/apps.rs`
- `solace-runtime/src/app_engine/runner.rs`
- `solace-runtime/src/routes/files.rs`
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
- rewriting the role stack instead of making execution more inspectable
