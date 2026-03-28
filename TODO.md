# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for first-class Solace Dev artifacts

## Current Round

SDA8 first-class run artifact routes and workspace-native detail.

The Dev workspace now has durable last-known run state and basic run history. The next step is to stop depending on partial secondary inspection paths and make the most important run artifacts first-class: report HTML, payload, stillwater/ripple when present, events, and a stronger workspace-native detail surface for the latest known run.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA have first-class, inspectable run artifacts and detail surfaces in the browser itself`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add first-class run artifact access and a stronger workspace-native run detail surface for the active Solace worker stack.`
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
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-inspection-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/durable-run-state.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/files.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/app_engine/runner.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current durable run-state and inspection surfaces
- the outcome must make artifacts and run detail more first-class, not just add more link text
- use real runtime or filesystem-backed run/report/artifact data
- do not invent fake payload, stillwater, ripple, or events routes
- if runtime support is missing, add the minimum honest support needed
- keep Prime Mermaid as the source-of-truth for artifact-access and run-detail flow
- do not expand into cloud sync, billing, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still cannot access first-class artifact routes for the latest run
- a user still has to guess where payload/report/stillwater data lives
- the browser still lacks a stronger workspace-native run detail surface
- the round only adds more diagrams without making run artifacts more accessible

## Required Deliverables

You must produce all of these:

1. one stronger workspace-native run detail surface
2. one first-class artifact access path for the latest run
3. one real route or file-serving path for at least the most important missing artifact surfaces
4. one Prime Mermaid source artifact for artifact-access or run-detail flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add stronger run detail in the workspace
Objective: make run inspection useful without leaving the Dev workspace immediately.
Scope: add a stronger native detail surface for the latest run, including richer event/report metadata and artifact visibility.
Done when: a reviewer can inspect the latest run in-browser with more than pills and basic links.
Evidence required: screenshots, routes exercised, and sample payloads.

### Ticket 2: Add first-class artifact access
Objective: stop relying on partial or implied artifact paths.
Scope: expose first-class access for the most important run artifacts, such as report HTML, payload, and stillwater/ripple when present, through honest runtime-backed routes or file-serving paths.
Done when: a reviewer can open the latest run artifacts from the browser without guessing hidden filesystem locations.
Evidence required: routes exercised, artifact paths, and screenshots.

### Ticket 3: Add one artifact-access Prime Mermaid artifact
Objective: capture the move from basic run inspection to first-class artifact access.
Scope: add one Prime Mermaid artifact for artifact access and one for stronger run detail if needed.
Done when: the artifact-access path is represented as committed source truth.
Evidence required: artifact paths and one short note on what each diagram governs.

### Ticket 4: Add one narrow smoke path and one narrow test
Objective: make the new artifact surface reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to latest run detail to artifact access
- one automated test or lightweight scripted verification for the new artifact-access surface
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
- rewriting the role stack instead of making artifacts first-class
