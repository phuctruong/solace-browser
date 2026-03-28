# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for explicit, shareable inspection context

## Current Round

SAU12 URL-backed selected-run context and deep-linkable inspection.

The Dev workspace can now persist the selected run across refresh or activation within the same session. The next step is to make that inspection context explicit and portable: the selected app/run should be reflected in the URL or equivalent visible route state so the workspace can be reopened or shared without depending only on hidden session state.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA can open a direct link to a specific inspected run and see the same inspection context restored honestly`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Make selected-run inspection context explicit and deep-linkable in the Dev workspace while keeping the current session persistence and honest fallback behavior intact.`
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
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sap11-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-selection-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/selected-run-persistence.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/artifact-preview-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current selected-run persistence, run-selection, and artifact-preview surfaces
- keep selected-run context honest and backed by real app/run ids
- reflect selected-run context in a visible route or URL state, not just hidden session storage
- if URL state and stored session state disagree, choose one explicit precedence rule and make it reviewable
- if URL state points to a missing run, show an honest fallback state
- keep Prime Mermaid as the source-of-truth for deep-link or route-backed inspection flow
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- a reviewer cannot open a link or route state that restores a specific selected run
- the workspace still depends only on hidden session state for inspection context
- URL or route state can point to a fake or missing run without an honest fallback
- precedence between URL state and session state is ambiguous
- the round only adds diagrams without making inspection context more explicit

## Required Deliverables

You must produce all of these:

1. one visible URL-backed or route-backed selected-run context path
2. one honest restore path from that context into native inspection and previews
3. one visible fallback state for invalid deep-link context
4. one Prime Mermaid source artifact for deep-link or route-backed inspection flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Make selected-run context explicit
Objective: stop hiding inspection context in session-only state.
Scope: reflect the selected app/run in URL or route state and keep it synchronized with the workspace selection.
Done when: a reviewer can see and copy a URL or route state representing the selected run.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Restore from explicit context
Objective: make explicit context operational, not cosmetic.
Scope: when the workspace opens with a valid selected-run URL or route state, restore inspection and previews from that context.
Done when: a reviewer can open the workspace directly into a specific selected run.
Evidence required: routes exercised, sample payloads, and screenshots.

### Ticket 3: Handle invalid explicit context honestly
Objective: avoid fake deep links.
Scope: if URL or route state points to a missing run, show a visible fallback and explain what happened.
Done when: invalid explicit context is visible and reviewable.
Evidence required: screenshots and one short walkthrough.

### Ticket 4: Add one deep-link inspection Prime Mermaid artifact
Objective: capture the move from hidden persistence to explicit route state.
Scope: add one Prime Mermaid artifact for URL-backed or route-backed inspection flow.
Done when: the explicit inspection-context flow is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make explicit inspection context reviewable and repeatable.
Scope:
- one documented local smoke path from selecting a run to reopening via URL or route state and seeing the same run restored
- one automated test or lightweight scripted verification for explicit selected-run context
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
- rewriting the role stack instead of making inspection context more explicit
