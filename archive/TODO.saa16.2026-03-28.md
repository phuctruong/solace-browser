# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native worker assignment packet visibility

## Current Round

SAA16 native worker assignment packet and scope-lock visibility.

The Dev workspace now shows worker identity, diagrams, and inbox/outbox structure. The next step is to make the active worker assignment itself visible: a reviewer should be able to see the current task statement, assignment packet, scope lock, and expected evidence contract directly inside the workspace instead of inferring it from static role templates.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose the active assignment packet, scope lock, and evidence contract directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native worker assignment packet surface to the Dev workspace while preserving the current role stack, worker detail, inbox/outbox visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sai15-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace, worker detail, diagram access, inbox/outbox visibility, run history, inspection context, and artifact preview surfaces
- the workspace must show the active assignment packet for the current worker context
- the assignment surface must include task statement, scope lock, and expected evidence contract
- do not invent live assignment state the repo or runtime does not know about
- if the current assignment packet is missing or only partially known, show that honestly
- keep Prime Mermaid and worker inbox contract artifacts visible as governing sources
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still does not show the active assignment packet directly
- a reviewer still cannot see the task statement or scope lock for the active worker from inside Hub
- the workspace still hides the expected evidence contract for the active worker
- the round only adds diagrams or static labels without making assignment state more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible worker assignment packet panel or section in the Dev workspace
2. one visible task statement and scope-lock surface for the active worker context
3. one visible expected evidence contract surface for the active worker context
4. one Prime Mermaid source artifact for worker assignment packet visibility
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible assignment packet surface
Objective: make the active worker assignment explicit.
Scope: show the current worker’s task statement, role, and assignment context in one native surface.
Done when: a reviewer can see what the current worker is supposed to do from inside the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Add scope lock and evidence contract visibility
Objective: make review criteria explicit before execution.
Scope: show scope lock, expected evidence outputs, or equivalent contract fields for the active worker.
Done when: a reviewer can tell what the worker is allowed to change and what evidence it must return.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Tie assignment packet to active worker context
Objective: stop treating task definition as detached from the selected role/run.
Scope: the assignment packet should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which worker’s assignment packet is being inspected and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one worker assignment Prime Mermaid artifact
Objective: capture the move from implicit tasking to visible assignment state.
Scope: add one Prime Mermaid artifact for worker assignment packet visibility.
Done when: the assignment packet surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make assignment packet visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to assignment packet inspection
- one automated test or lightweight scripted verification for the worker assignment surface
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
- rewriting the role stack instead of making assignment state more visible
