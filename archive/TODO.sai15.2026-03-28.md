# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native worker inbox/outbox visibility

## Current Round

SAI15 native worker inbox/outbox visibility.

The Dev workspace now shows worker identity and governing diagrams. The next step is to make the worker contract operationally legible: a reviewer should be able to see the current role’s inbox inputs, scope-defining source artifacts, and outbox result surfaces directly inside the workspace instead of inferring them only from run history.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose their current inbox inputs, outbox outputs, and governing source artifacts directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native worker inbox/outbox surface to the Dev workspace while preserving the current role stack, run history, inspection context, worker detail, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sac13-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-saw14-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-to-design-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/design-to-coder-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/coder-to-qa-handoff.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace, inspection context, worker detail, diagram access, run history, and artifact preview surfaces
- the workspace must show the current role’s inbox sources and current outbox/result surface explicitly
- do not invent inbox state the runtime or repo contract does not know about
- if a role has no current inbox or outbox detail, show that honestly in the workspace
- keep Prime Mermaid and role handoff docs visible as inbox-governing source artifacts
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still does not expose worker inbox inputs directly
- the workspace still does not expose worker outbox/result state directly
- a reviewer still has to infer inbox/outbox from repo files or raw run artifacts alone
- the round only adds diagrams or static text without making the worker contract more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible worker inbox panel or section in the Dev workspace
2. one visible worker outbox panel or section in the Dev workspace
3. one explicit tie between active worker context and the inbox/outbox surface
4. one Prime Mermaid source artifact for worker inbox/outbox visibility
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible inbox surface
Objective: make worker inputs and governing sources explicit.
Scope: show the current role’s inbox inputs such as handoff source, relevant source artifacts, or contract anchors in one native surface.
Done when: a reviewer can see what the current worker is operating from without reading repo files.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Add a visible outbox surface
Objective: make worker outputs explicit.
Scope: show the current role’s outbox/result surface such as latest run, artifact summary, or current review surface in one native panel.
Done when: a reviewer can see what the current worker has produced from inside the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Tie inbox/outbox to active worker context
Objective: stop treating worker contract state as disconnected from the selected role/run.
Scope: the inbox/outbox surface should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which role’s inbox/outbox is being inspected and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one worker inbox/outbox Prime Mermaid artifact
Objective: capture the move from implicit worker contract state to visible workspace contract state.
Scope: add one Prime Mermaid artifact for worker inbox/outbox visibility flow.
Done when: the worker inbox/outbox surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make worker inbox/outbox visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to inbox/outbox inspection
- one automated test or lightweight scripted verification for the worker inbox/outbox surface
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
- rewriting the role stack instead of making worker inbox/outbox state more visible
