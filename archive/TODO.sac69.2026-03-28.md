# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native assignment execution launch

## Current Round

`SAC69` native run launch from the selected routed assignment.

`SAC68` made assignment routing a real manager action. The manager can now choose `design`, `coder`, or `qa` for the selected request and write that routing decision into Back Office honestly.

The next blocker is execution. The selected request and routed assignment still do not give the manager one explicit “run this assignment now” path in Hub. The next round must make the selected request + selected role produce one explicit run-launch action tied to the existing app/run routes.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to move a selected self-hosting request from request truth into assignment truth and then into one explicit execution launch from Hub itself.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native run-launch surface for the selected routed assignment. The manager must be able to launch the corresponding role app using the existing runtime app/run routes and keep that launch visibly tied to the selected request and routed assignment.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Audit Ground Truth

- request creation is native in Hub
- selected request state is native in Hub
- assignment routing is now a native manager action
- execution launch is still implicit and detached from the selected request/assignment chain
- the manager still cannot explicitly launch the routed specialist lane from the same workflow surface

## Rules

- do not bypass the selected request / selected assignment path
- use the existing app run route instead of inventing a parallel execution API
- keep the route from selected request -> assignment -> run honest and visible
- preserve `SAC66`, `SAC67`, and `SAC68`

## Hard Rejection Criteria

- the manager still cannot launch the routed assignment from Hub
- run launch is still detached from the selected request and selected assignment
- the round adds a button without clearly tying it to the existing runtime app/run path
- the result reintroduces mock execution state instead of using the actual runtime route

## Required Deliverables

1. one native run-launch control for the selected routed assignment
2. one visible link from selected request -> routed role -> launched run
3. one honest basis line showing which runtime route was used
4. one Prime Mermaid artifact for request-to-assignment-to-run launch
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add explicit run launch

Objective: make execution a manager-visible action.

Scope:

- add one control that launches the selected routed role
- bind it to the existing runtime app/run route
- prevent launch when there is no selected request or no routed assignment

Done when: the manager can explicitly launch one routed role from Hub.

### Ticket 2: Surface launch context honestly

Objective: stop execution from looking detached.

Scope:

- show selected request
- show active routed assignment
- show launched role/app target
- show which runtime route is being used

Done when: a reviewer can tell exactly what the launch action is about.

### Ticket 3: Preserve the durable chain

Objective: keep the workflow coherent.

Scope:

- do not break request creation
- do not break request selection
- do not break assignment routing
- keep downstream worker panels compatible with the launched role

Done when: launch strengthens the request -> assignment -> run chain.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/apps.rs`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample launch payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- workflow redesign beyond launch
- cloud sync or `solaceagi`
- unrelated transparency panels
- generic polish without execution truth
