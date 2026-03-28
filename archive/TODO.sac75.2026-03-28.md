# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound next-step routing

## Current Round

`SAC75` native workflow next-step routing from the active workflow result area.

`SAC74` made the workflow-bound result box able to approve or reject the active output using the real Back Office approvals path.

The next blocker is workflow continuity. The manager can now sign off from the result area, but still has to leave that same result context to advance the request into the next specialist lane. That keeps the self-hosting loop split across multiple surfaces.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to move a real workflow from request -> assignment -> run -> evidence -> approval -> next routed assignment inside Solace Hub using the existing Back Office objects.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one workflow-bound next-step routing action into the active workflow result area. Keep it tied to the selected request, assignment, run, and current approval state.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI4 — AI Workers as Orchestrated Systems, Not Models.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/data/apps/solace-dev-manager/manifest.yaml`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`

## Audit Ground Truth

- request creation is native
- request selection is native
- assignment routing is native
- execution launch is native
- launched run binding is native
- artifact and preview are visible
- approval/signoff state is visible
- approval/reject action is native
- advancing the same workflow to its next routed role is still split away from the result box

## Rules

- do not invent a second assignment model
- use the existing `assignments` Back Office objects
- keep the action bound to the active workflow request/assignment/run result
- do not fake “workflow advanced” unless a real assignment mutation happened
- preserve `SAC66` through `SAC74`

## Hard Rejection Criteria

- the manager still cannot route the next step from the active workflow result area
- the action is detached from the active request/assignment/run context
- the action mutates fake UI state without writing the real assignment path
- the result area claims advancement without clearly stating which role was activated

## Required Deliverables

1. one visible workflow-bound next-step routing control in the result area
2. one explicit link from request -> assignment -> run -> preview -> approval -> next-step route
3. one honest basis line describing whether the route created or updated assignment state
4. one Prime Mermaid artifact for request -> assignment -> run -> approval -> next-step route
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add workflow-bound next-step route

Objective: make the approved or rejected result actionable without leaving the workflow box.

Scope:

- allow one native route-to-role action from the workflow result area
- write through the existing assignments object model

Done when: a reviewer can move the active request into the next role without leaving the workflow result context.

### Ticket 2: Preserve honest workflow context

Objective: keep the routing action truthful.

Scope:

- make clear which request, assignment, and run the action applies to
- make clear which target role was activated
- make clear whether the assignment row was created or updated

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
- sample next-step routing payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole assignment model
- adding cloud sync or `solaceagi`
- unrelated dashboard polish
- fake workflow advancement without real Back Office mutation
