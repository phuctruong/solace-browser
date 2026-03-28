# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native Solace Dev run-by-run artifact inspection

## Current Round

SAT10 workspace-native run selection and artifact switching.

The Dev workspace now previews the latest run artifacts inline. The next step is to make artifact inspection stronger across recent runs: selecting a recent run should update the native inspection and preview surfaces inside the workspace instead of leaving the browser trapped in one latest-run view.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA can select a recent run and inspect its core artifacts directly inside the browser`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Make the Dev workspace support native run selection and artifact switching across recent runs while keeping the current latest-run preview path honest and durable.`
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
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdi7-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sda8-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sav9-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-inspection-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/durable-run-state.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/artifact-access-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/artifact-preview-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/files.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/app_engine/runner.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current live workspace, durable run-state, artifact routes, and inline preview panel
- keep the current artifact routes real and runtime-backed
- selecting a run must update native inspection and preview surfaces inside the workspace
- do not invent fake historical artifact state
- if a historical run lacks an artifact, show an honest missing state
- keep Prime Mermaid as the source-of-truth for run-selection and artifact-switching flow
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- recent-run selection does not update the inspection and preview surfaces inside the workspace
- the workspace still only meaningfully supports the single latest-run preview path
- the browser invents fake historical artifact content
- historical missing artifacts are not clearly represented
- the round only adds diagrams without making run-by-run inspection more native

## Required Deliverables

You must produce all of these:

1. one visible run-selection path from run history into native inspection and preview
2. one honest in-workspace artifact-switching path across selected runs
3. one visible missing-state treatment for historical missing artifacts
4. one Prime Mermaid source artifact for run-selection or artifact-switching flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Make recent-run selection drive the workspace
Objective: stop treating run history as a mostly separate list.
Scope: selecting a recent run should update the native run-inspection and artifact-preview surfaces in the workspace.
Done when: a reviewer can choose a recent run and see the workspace update without leaving the page.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Support artifact switching across selected runs
Objective: make the preview system useful beyond the single latest run.
Scope: the preview system should load route-backed artifacts for the selected run and keep the current latest-run behavior intact.
Done when: a reviewer can inspect artifacts for more than one run from the workspace.
Evidence required: routes exercised, sample payloads, and screenshots.

### Ticket 3: Handle historical missing artifacts honestly
Objective: avoid fake historical previews.
Scope: if a selected run does not contain an artifact, show a visible missing-state message inside the workspace.
Done when: missing historical artifact state is visible and reviewable.
Evidence required: screenshots and one short walkthrough.

### Ticket 4: Add one run-selection Prime Mermaid artifact
Objective: capture the move from latest-run preview to run-by-run inspection.
Scope: add one Prime Mermaid artifact for run-selection or artifact-switching flow.
Done when: the run-selection flow is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make run-by-run preview reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to historical run selection to native preview update
- one automated test or lightweight scripted verification for the run-selection surface
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
- rewriting the role stack instead of making run-by-run inspection more native
