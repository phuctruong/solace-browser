# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native workflow approval action

## Current Round

`SAC74` native workflow approval/reject action.

`SAC73` made the workflow-bound result box show the current approval/signoff state for the active request/assignment/run output.

The next blocker is actionability. The manager can now see approval state, but the same workflow box still needs one explicit approval/reject action so the manager can move the workflow forward without leaving the result context.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to see the active workflow result and directly approve or reject it from the same workflow-bound result area using the existing Back Office approval objects.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one native workflow-bound approval action into the result box using the existing approvals table. Keep the action honest and tied to the selected request, assignment, and run context.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`

## Audit Ground Truth

- request creation is native
- request selection is native
- assignment routing is native
- execution launch is native
- launched run binding is native
- artifact and preview are visible
- approval/signoff state is visible
- approval/reject action is still missing from the workflow result area

## Rules

- do not invent a second approval path
- use the existing approvals Back Office objects
- keep the action bound to the active workflow request/assignment/run result
- preserve `SAC66` through `SAC73`

## Hard Rejection Criteria

- the manager still cannot approve or reject from the workflow result area
- the action is detached from the active workflow context
- the round adds fake buttons without writing the real approval object path

## Required Deliverables

1. one visible workflow-bound approve/reject control
2. one visible link from request -> assignment -> run -> preview -> approval action
3. one honest basis line describing whether the approval action is updating or creating approval state
4. one Prime Mermaid artifact for request -> assignment -> run -> preview -> approval action
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add workflow-bound approval action

Objective: make the result box actionable.

Scope:

- allow one native approve or reject action from the result area
- write through the existing approvals object model

Done when: a reviewer can change approval state without leaving the workflow result area.

### Ticket 2: Preserve honest context

Objective: keep the action truthful.

Scope:

- make clear which request, assignment, and run the action applies to
- make clear whether the approval row was created or updated

Done when: the action is useful without obscuring system truth.

## Suggested File Targets

- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample approval action payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole approval model
- cloud sync or `solaceagi`
- unrelated transparency panels
- generic polish without workflow-bound approval action truth
