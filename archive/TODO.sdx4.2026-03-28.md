# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for the first integrated Solace Dev role stack

## Current Round

SDX4 integrated Dev workspace and worker control.

The manager, design, coder, and QA role apps now exist and pass narrow contract checks. The next step is to stop treating them as separate card shells and make one real Dev workspace in Hub/dashboard where a human can inspect all four roles, inspect their inbox/outbox state, inspect diagrams and handoffs, and trigger the next worker action for `solace-browser` itself.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA operate on the same durable objects and can be inspected and driven from the browser itself`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `manager`
- `task_statement`: `Build the first integrated Dev workspace in Solace Hub for solace-browser itself, with visible manager/design/coder/qa role detail, shared project context, inbox/outbox visibility, and a minimal worker run/control path.`
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
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-source-map.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-to-design-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/design-to-coder-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/coder-to-qa-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-page-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-ui-state-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-component-state-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/design-handoff-flow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/coder-workflow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/coder-run-lifecycle.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/qa-workflow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/qa-signoff-release-gate.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-dev-manager/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-design/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-coder/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-qa/manifest.prime-mermaid.md`

## Rules

- build on the existing four role apps, do not replace them with a parallel abstraction
- the outcome must be one integrated Dev workspace, not four disconnected role cards
- make role detail visible in Hub or dashboard, not only in repo files
- keep Prime Mermaid as the source-of-truth for workspace and role-stack structure
- do not add new standalone JSON or YAML source contracts when Prime Mermaid can express the structure
- it is acceptable to keep JSON/YAML compatibility files only where runtime compatibility still requires them
- the shared project context must be `solace-browser` itself
- inbox, outbox, handoff, run, finding, and signoff visibility must be inspectable from the browser
- add a minimal worker control path even if execution is still local-first and partial
- do not expand into cloud sync, billing, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- there is still no single Dev workspace that surfaces manager, design, coder, and QA together
- a user cannot inspect the current project, current role, and current artifacts in one place
- inbox/outbox summaries are still hidden behind repo browsing only
- there is no visible role detail page or panel for at least the four active roles
- there is no visible worker run/control affordance for the role stack
- the dashboard cannot show the diagrams and current Dev role state for `solace-browser`
- the round only adds more docs without making the Hub/browser surface more usable

## Required Deliverables

You must produce all of these:

1. one integrated Dev workspace shell for the four active roles
2. one role roster or stack view showing manager, design, coder, and QA together
3. one role detail surface with inbox/outbox, handoff, artifact, and status visibility
4. one project detail surface for `solace-browser`
5. one minimal worker run/control path or action for the role stack
6. one Prime Mermaid source artifact for the integrated workspace and worker-control flow
7. one narrow smoke path
8. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Build one integrated Dev workspace shell
Objective: stop treating the role stack as separate round-by-round shells.
Scope: add one Dev workspace view in Hub/dashboard that shows the four roles together around the same active `solace-browser` project context.
Done when: a human can open one place in the browser and see the active role stack for `solace-browser`.
Evidence required: changed files, screenshots, and one short walkthrough.

### Ticket 2: Add the first role roster and role detail view
Objective: make each worker app inspectable from the browser.
Scope: expose manager, design, coder, and QA as first-class role entries with visible status, inbox summary, outbox summary, linked handoffs, and linked artifacts.
Done when: a reviewer can inspect each role without leaving the workspace or guessing hidden paths.
Evidence required: screenshots, artifact paths, and one short note on what each role detail view shows.

### Ticket 3: Add one project detail surface for `solace-browser`
Objective: anchor the role stack to a shared project object instead of free-floating role pages.
Scope: expose the current `solace-browser` project map, active diagrams, active role ownership, and linked role artifacts in one project-facing view.
Done when: the browser can show how the four roles relate to the current project.
Evidence required: screenshots and artifact paths.

### Ticket 4: Add a minimal worker run/control path
Objective: move toward the point where you can hit run on a Solace worker from Hub/dashboard.
Scope: add the minimum visible control path for the role stack, such as a run action, queue action, or launch action tied to a worker app and current project context.
Done when: a reviewer can see and exercise one clear worker control path without inventing undocumented steps.
Evidence required: exact route or action path, screenshots, sample payloads, and command output.

### Ticket 5: Add one integrated Prime Mermaid workspace/control artifact
Objective: make the combined workspace structure explicit.
Scope: add one Prime Mermaid artifact for the integrated Dev workspace and one Prime Mermaid artifact for the worker-control or run-request flow.
Done when: the integrated workspace is represented as committed source-of-truth diagrams instead of only UI code.
Evidence required: artifact paths and one short note on what each diagram governs.

### Ticket 6: Add one narrow smoke path and one narrow test
Objective: make the integrated workspace reviewable and repeatable.
Scope:
- one documented local smoke path from startup to Dev workspace to role detail to worker control
- one automated test or lightweight scripted verification for the integrated role stack
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/hub_control.rs`
- `solace-runtime/src/routes/backoffice.rs`
- `solace-runtime/src/routes/apps.rs`
- `solace-runtime/src/backoffice/schema.rs`
- `specs/solace-dev/`
- `data/apps/solace-dev-manager/`
- `data/apps/solace-design/`
- `data/apps/solace-coder/`
- `data/apps/solace-qa/`
- `tests/`
- `scripts/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- integrated workspace artifact paths
- role detail artifact paths
- sample payloads or records
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- adding new specialist roles beyond manager, design, coder, and QA
- broad cloud sync, billing, or `solaceagi` work
- unrelated Chromium platform changes
- deeper release automation beyond the first visible QA/signoff surface
- rewriting the four role apps instead of integrating them
