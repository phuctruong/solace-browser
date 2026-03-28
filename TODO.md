# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for visible, shareable inspection context

## Current Round

SAC13 native inspection-context panel and copy-link affordance.

The Dev workspace now supports URL-backed deep-link inspection. The next step is to make that context visible and usable in the workspace itself: show the current inspection source and selected run explicitly, expose a copyable share link, and make the deep-link state legible without reading the browser address bar.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA can see, copy, and share the exact inspection context for the current selected run`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native inspection-context panel and copy-link affordance to the Dev workspace while keeping the current URL-backed and session-backed restore rules honest.`
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
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sau12-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/deep-link-inspection.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/selected-run-persistence.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/run-selection-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current URL-backed deep-link inspection and selected-run persistence surfaces
- the workspace must show the current inspection source and selected app/run explicitly
- a reviewer must be able to copy a concrete inspection link without reading the raw address bar
- keep precedence honest and visible: deep-link, restored session, or default fallback
- if the current inspection context is invalid or implicit, show that honestly in the panel
- keep Prime Mermaid as the source-of-truth for inspection-context panel flow
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still lacks a visible panel showing the current inspection context
- a reviewer still has to inspect the browser address bar to know or copy the current deep link
- the panel hides whether the current context came from deep-link, restored session, or fallback
- the round only adds diagrams without making inspection context more usable

## Required Deliverables

You must produce all of these:

1. one visible inspection-context panel in the workspace
2. one copy-link or equivalent explicit share affordance
3. one visible source indicator for current context (`deep-link`, `restored`, `selected`, or `fallback`)
4. one Prime Mermaid source artifact for inspection-context panel flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible inspection-context panel
Objective: make inspection context explicit inside the workspace.
Scope: show the current app/run, context source, and current deep-link state in one native panel.
Done when: a reviewer can see the active inspection context without reading the raw address bar.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Add a copy-link affordance
Objective: make the deep-link context shareable in practice.
Scope: add a copy-link button or equivalent affordance for the current inspection URL or route state.
Done when: a reviewer can copy a direct inspection link from inside the workspace.
Evidence required: screenshots, user-visible states, and one short walkthrough.

### Ticket 3: Surface source and fallback honestly
Objective: keep inspection provenance legible.
Scope: the panel should show whether the current context came from deep-link, restored session, latest fallback, or explicit selection.
Done when: a reviewer can tell how the current inspection context was established.
Evidence required: screenshots and one short walkthrough.

### Ticket 4: Add one inspection-context Prime Mermaid artifact
Objective: capture the move from raw URL support to usable workspace affordance.
Scope: add one Prime Mermaid artifact for the inspection-context panel and copy-link flow.
Done when: the inspection-context panel flow is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make inspection-context UX reviewable and repeatable.
Scope:
- one documented local smoke path from selecting a run to copying/opening the current inspection link
- one automated test or lightweight scripted verification for the panel and copy-link surface
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
- rewriting the role stack instead of making inspection context more usable
