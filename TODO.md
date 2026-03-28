# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound next-step launch

## Current Round

`SAC76` native workflow next-step launch from the active workflow result area.

`SAC75` made the workflow-bound result box able to route the next specialist lane through the real Back Office assignments path and report whether that route created or updated assignment state.

The next blocker is continuity. The manager can now approve and route from the same workflow box, but still has to leave that result context to launch the newly routed next step. That breaks the self-hosting loop one step too early.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to move a real workflow from request -> assignment -> run -> evidence -> approval -> next routed assignment -> next launch inside Solace Hub using the existing runtime and Back Office objects.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one workflow-bound launch-next-step action into the active workflow result area. Keep it tied to the selected request, assignment, routed target role, and current workflow-bound route state.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI4 — AI Workers as Orchestrated Systems, Not Models.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
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
- approval/reject action is native
- workflow-bound next-step routing is native
- launching the newly routed next step is still split away from the workflow result box

## Rules

- do not invent a second launch path
- use the existing runtime run route and existing assignments Back Office objects
- keep the action bound to the active workflow request/assignment/run result
- do not fake “next step launched” unless a real runtime run mutation happened
- preserve `SAC66` through `SAC75`

## Hard Rejection Criteria

- the manager still cannot launch the routed next step from the active workflow result area
- the launch action is detached from the active request/assignment/run context
- the action mutates fake UI state without hitting the real runtime run path
- the result area claims next-step launch without clearly stating which role/app was launched

## Required Deliverables

1. one visible workflow-bound launch-next-step control in the result area
2. one explicit link from request -> assignment -> run -> preview -> approval -> next-step route -> next-step launch
3. one honest basis line describing whether the launch used workflow-bound routed assignment state or a weaker fallback
4. one Prime Mermaid artifact for request -> assignment -> run -> approval -> next-step route -> next-step launch
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add workflow-bound next-step launch

Objective: make the routed next step executable without leaving the workflow box.

Scope:

- allow one native next-step launch action from the workflow result area
- use the existing runtime run route against the routed target role

Done when: a reviewer can route and then launch the next specialist step from the same workflow result context.

### Ticket 2: Preserve honest workflow launch context

Objective: keep the launch action truthful.

Scope:

- make clear which request, assignment, run, and target role the action applies to
- make clear whether the launch used the workflow-bound route state or a weaker fallback

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
- sample next-step launch payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole run model
- adding cloud sync or `solaceagi`
- unrelated dashboard polish
- fake workflow advancement without real runtime launch mutation
