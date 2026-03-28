# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for durable selected-run inspection

## Current Round

SAP11 durable selected-run state and workspace rehydration.

The Dev workspace can now select recent runs and switch native inspection and preview surfaces across them. The next step is to make that selected-run state durable: the workspace should preserve the selected run across refresh or activation and rehydrate the same inspection context honestly instead of snapping back to an implicit default.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA can reopen the workspace and keep inspecting the same selected run and its artifacts`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Make selected-run state durable and rehydratable inside the Dev workspace while keeping the current run-selection and artifact-preview flows honest.`
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
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sat10-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-selection-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/artifact-preview-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/durable-run-state.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/files.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current run-selection, artifact-preview, and durable-run-state surfaces
- keep selected-run state honest and backed by real app/run ids
- if the saved selected run no longer exists, fall back visibly and honestly
- do not invent fake persisted run state
- keep Prime Mermaid as the source-of-truth for selected-run persistence and rehydration flow
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- a reviewer cannot refresh or reactivate the workspace and keep the previously selected run
- the workspace silently falls back to another run without telling the user
- the browser invents fake persisted selection state
- the round only adds diagrams without making selected-run state more durable

## Required Deliverables

You must produce all of these:

1. one durable selected-run state path
2. one honest rehydration path on workspace load or activation
3. one visible fallback state when a stored selection is invalid or missing
4. one Prime Mermaid source artifact for selected-run persistence flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Persist selected-run state
Objective: make run selection survive beyond the immediate click.
Scope: store the selected app/run pair in one honest local workspace state path and use it on reload or activation.
Done when: a reviewer can select a run, reload or reactivate, and see the same selected run restored.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Rehydrate inspection and previews from stored selection
Objective: make durable selection useful, not cosmetic.
Scope: when stored selection is valid, restore the run-inspection and artifact-preview surfaces from that selection instead of defaulting to the newest run.
Done when: a reviewer sees the same inspection context after reload.
Evidence required: routes exercised, sample payloads, and screenshots.

### Ticket 3: Handle invalid stored selection honestly
Objective: avoid fake or stale persisted state.
Scope: if a stored selected run is missing, clear or replace it visibly and explain the fallback in the workspace.
Done when: a reviewer can see the invalid-selection fallback state and the workspace still behaves coherently.
Evidence required: screenshots and one short walkthrough.

### Ticket 4: Add one selected-run persistence Prime Mermaid artifact
Objective: capture the move from ephemeral selection to durable workspace context.
Scope: add one Prime Mermaid artifact for selected-run persistence or rehydration flow.
Done when: the persistence flow is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make durable selected-run state reviewable and repeatable.
Scope:
- one documented local smoke path from selecting a run to refreshing or reactivating and seeing the same run restored
- one automated test or lightweight scripted verification for selected-run persistence
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/apps.rs`
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
- rewriting the role stack instead of making selected-run state durable
