# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for the first live Solace Dev role stack

## Current Round

SDH5 live workspace hydration and run feedback.

The integrated Dev workspace now exists and the four roles are visible together in Hub/dashboard. The next step is to stop relying on mostly static role text and make the workspace load live state from the runtime and Back Office: role metadata, project context, handoff counts, latest run/report state, and visible run feedback after a worker action.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA operate on the same durable objects and the browser can show live worker state, not just static scaffolding`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `manager`
- `task_statement`: `Hydrate the integrated Dev workspace with live runtime/backoffice state for solace-browser itself, and make worker runs return visible feedback and linked artifacts in the browser.`
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
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-source-map.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-to-design-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/design-to-coder-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/coder-to-qa-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/integrated-dev-workspace.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/worker-control-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-dev-manager/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-design/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-coder/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-qa/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the existing integrated workspace; do not replace it with a second shell
- make the role cards and project surface load live state from runtime or Back Office where possible
- keep Prime Mermaid as the source-of-truth for live workspace and run-feedback structure
- do not add new standalone JSON or YAML source contracts when Prime Mermaid can express the structure
- it is acceptable to keep JSON transport at API boundaries and compatibility files where runtime still needs them
- the shared project context remains `solace-browser`
- do not fake run state; if a run cannot be shown yet, show the honest boundary and current payload/result
- worker-control feedback must be visible in the browser after an action, not just in terminal output
- do not expand into cloud sync, billing, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the integrated workspace is still mostly static text rather than runtime/backoffice-backed state
- the role cards cannot show any live metadata, counts, or recent role state
- worker control still returns only a blind fire-and-forget action with no visible feedback path
- there is no visible last-run, last-report, or last-action surface for the role stack
- the browser still cannot show live role and project context for `solace-browser`
- the round only adds more diagrams without making the workspace more truthful

## Required Deliverables

You must produce all of these:

1. one live workspace hydration path in Hub for the integrated role stack
2. one live role detail surface showing at least some runtime or backoffice-backed state
3. one visible run-feedback surface after worker control actions
4. one project context surface with live links or live counts
5. one Prime Mermaid source artifact for live workspace hydration or run-feedback flow
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Hydrate the integrated role stack
Objective: replace static-only role summaries with live state.
Scope: load role metadata, role counts, or recent state from runtime/backoffice APIs into the integrated workspace for manager, design, coder, and QA.
Done when: a reviewer can see that the workspace is reading some real state instead of only hardcoded copy.
Evidence required: changed files, routes exercised, screenshots, and one short walkthrough.

### Ticket 2: Add one live role detail surface
Objective: make at least one level of role detail data-backed.
Scope: add live role detail for the four active roles, such as latest run/report path, table counts, or current inbox/outbox summary derived from runtime/backoffice state.
Done when: a reviewer can inspect role detail that is not just static prose.
Evidence required: screenshots, sample payloads, and artifact paths.

### Ticket 3: Add visible run feedback
Objective: make worker control actions useful in-browser.
Scope: after clicking a run control, show visible response state such as returned report path, latest run id, latest event link, or structured error feedback.
Done when: a reviewer can trigger a worker action and understand what happened without opening devtools.
Evidence required: exact route exercised, screenshots, sample response payloads, and command output.

### Ticket 4: Add live project context
Objective: make the project-facing surface more truthful.
Scope: show live project-facing data for `solace-browser`, such as linked backoffice counts, current role ownership markers, or latest artifact/run references.
Done when: the project header or detail area reflects live project state rather than only static labels.
Evidence required: screenshots and routes exercised.

### Ticket 5: Add one Prime Mermaid live-state artifact
Objective: capture the new hydration or feedback flow as source truth.
Scope: add one Prime Mermaid artifact for live workspace hydration and one Prime Mermaid artifact for run-feedback or last-run visibility.
Done when: the move from static shell to live workspace is represented in committed source artifacts.
Evidence required: artifact paths and one short note on what each diagram governs.

### Ticket 6: Add one narrow smoke path and one narrow test
Objective: make the live workspace reviewable and repeatable.
Scope:
- one documented local smoke path from startup to integrated workspace to worker control to visible run feedback
- one automated test or lightweight scripted verification for the live workspace surface
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/apps.rs`
- `solace-runtime/src/routes/backoffice.rs`
- `solace-runtime/src/routes/hub_control.rs`
- `solace-runtime/src/backoffice/schema.rs`
- `specs/solace-dev/`
- `tests/`
- `scripts/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- live workspace artifact paths
- sample response payloads
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- adding new specialist roles beyond manager, design, coder, and QA
- broad cloud sync, billing, or `solaceagi` work
- unrelated Chromium platform changes
- rewriting the role stack instead of hydrating it
