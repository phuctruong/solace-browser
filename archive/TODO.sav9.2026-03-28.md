# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native Solace Dev artifact inspection

## Current Round

SAV9 workspace-native artifact previews and latest artifact hydration.

The Dev workspace now has honest first-class artifact routes for the latest run. The next step is to stop treating artifact inspection as mostly a set of outbound links and make the workspace itself useful: preview the most important latest-run artifacts inline, keep the route-backed links, and make the artifact state visible on workspace load.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA can inspect the latest run and its core artifacts directly inside the browser`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add workspace-native preview for the latest run artifacts while keeping the new route-backed artifact access honest and durable.`
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
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-inspection-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/durable-run-state.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/artifact-access-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/files.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/app_engine/runner.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current live workspace, durable run-state, and first-class artifact routes
- keep the current artifact routes real and runtime-backed
- the outcome must make latest-run artifacts more usable inside the workspace, not just add more outbound links
- preview only what the runtime can honestly provide
- if an artifact is missing, show a clear missing state rather than inventing synthetic content
- keep Prime Mermaid as the source-of-truth for artifact-preview flow
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still cannot preview any latest-run artifacts inline
- a reviewer still has to leave the workspace immediately to inspect the core latest-run artifacts
- the browser invents fake preview content instead of loading honest route-backed content
- the latest-run artifact panel does not survive workspace load and hydration
- the round only adds diagrams without making inspection more native

## Required Deliverables

You must produce all of these:

1. one workspace-native preview surface for the latest run
2. one honest preview path for at least two core artifacts
3. one visible missing-state treatment for absent artifacts
4. one Prime Mermaid source artifact for artifact-preview flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a native latest-run artifact panel
Objective: make the Dev workspace itself useful for artifact inspection.
Scope: add a latest-run artifact panel that renders inline in the workspace and is fed by the current run-history and artifact-route substrate.
Done when: a reviewer can open the workspace and see a real latest-run artifact panel without triggering a new run first.
Evidence required: screenshots, routes exercised, and sample payloads.

### Ticket 2: Preview at least two honest artifacts inline
Objective: reduce dependence on external tabs for the most important artifacts.
Scope: render at least two honest inline previews from route-backed content, such as report summary, payload preview, stillwater preview, event tail, stdout tail, or evidence summary.
Done when: a reviewer can inspect at least two latest-run artifact types inline in the workspace.
Evidence required: routes exercised, sample payloads, and screenshots.

### Ticket 3: Handle missing artifacts honestly
Objective: avoid fake preview content.
Scope: if an artifact is absent, show a visible missing-state message in the workspace instead of blank space or invented content.
Done when: missing artifact state is visible and reviewable.
Evidence required: screenshots and one short walkthrough.

### Ticket 4: Add one artifact-preview Prime Mermaid artifact
Objective: capture the move from route access to native preview.
Scope: add one Prime Mermaid artifact for latest-run artifact-preview flow.
Done when: the preview flow is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make native preview reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to latest-run artifact preview
- one automated test or lightweight scripted verification for the preview surface
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
- rewriting the role stack instead of making artifact inspection more native
