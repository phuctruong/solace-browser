# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for launched-run result binding

## Current Round

`SAC70` native launched-run binding back into the selected workflow.

`SAC69` gave the manager an explicit execution launch from the selected routed assignment through the real runtime app/run route.

The next blocker is result binding. Launch now happens honestly, but the selected request/assignment workflow still needs one explicit visible “latest launched run for this selected workflow” binding so the manager can see that the launch returned into the same chain instead of merely firing a generic app run.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to launch a routed assignment and then immediately see that launched run come back into the selected request/assignment workflow context inside Hub.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Bind the launched run back into the selected request and active assignment context. Surface one honest latest-launch result line showing request, assignment, app, and run linkage.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Audit Ground Truth

- request creation is native
- request selection is native
- assignment routing is native
- execution launch is native
- the launched run is still not clearly bound back to the selected workflow as a first-class result object

## Rules

- do not invent a separate run-tracking model
- use the existing runtime run output and selection behavior
- keep the selected request / selected assignment / launched run linkage visible and honest
- preserve `SAC66` through `SAC69`

## Hard Rejection Criteria

- the manager still cannot tell which run belongs to the current selected workflow
- launched run context is still generic app/run output instead of workflow-bound output
- the round adds a label but not a real linkage between launch action and selected workflow

## Required Deliverables

1. one visible launched-run result surface tied to the selected request
2. one visible launched-run result surface tied to the active assignment
3. one honest basis line explaining how the run was bound
4. one Prime Mermaid artifact for request -> assignment -> launch -> run result
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Bind launch result to workflow context

Objective: make execution results belong to the selected workflow.

Scope:

- surface the latest launched run for the selected request/assignment
- show request ID, assignment ID, app ID, and run ID together

Done when: a reviewer can see that the launch returned into the same workflow chain.

### Ticket 2: Preserve honest runtime basis

Objective: keep the workflow truthful.

Scope:

- show the runtime route or runtime result basis honestly
- do not imply durable run linkage if it is only session-bound

Done when: the result surface is useful without overstating system truth.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample launch-result payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole run system
- cloud sync or `solaceagi`
- unrelated transparency panels
- generic polish without result linkage
