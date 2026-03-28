# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound next-step inbox packet preview

## Current Round

`SAC78` native workflow-bound next-step inbox packet preview.

`SAC77` made the workflow-bound result box able to show whether the launched next-step assignment produced a real `payload.json` packet and tied that visibility to the launched role, assignment, and run.

The next blocker is inspectability. The manager can now see that the next-step packet exists, but still has to leave the workflow result context to inspect the packet body. That keeps worker truth one click away from the self-hosting loop instead of fully inside it.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to move a real workflow from request -> assignment -> worker inbox packet -> run -> evidence -> approval -> next routed assignment -> next launch inside Solace Hub, with the worker packet itself inspectable in the same workflow surface.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one workflow-bound next-step inbox packet preview block into the active workflow result area. Keep it tied to the selected request, source assignment, target assignment, launched role, and launched run.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-company.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI4 — AI Workers as Orchestrated Systems, Not Models.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
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
- workflow-bound next-step launch is native
- workflow-bound next-step packet existence is visible
- workflow-bound next-step packet body is still not previewable in the same workflow box

## Rules

- do not invent a second packet artifact path
- use the existing runtime artifact route for `payload.json`
- keep the preview bound to the active workflow request/assignment/run result
- do not fake “packet preview” unless the result box shows real packet content or an honest missing state for the exact launched run
- preserve `SAC66` through `SAC77`

## Hard Rejection Criteria

- the manager still cannot preview the next-step worker packet from the workflow result area
- the preview is detached from the launched target assignment or launched run
- the panel shows generic placeholder text instead of real packet content or honest missing state
- the result area claims packet preview truth without clearly stating which launched role, assignment, or run it belongs to

## Required Deliverables

1. one visible workflow-bound next-step inbox packet preview block in the result area
2. one explicit link from request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet preview
3. one honest basis line describing whether the packet preview is exact launched-run packet truth or a weaker fallback
4. one Prime Mermaid artifact for request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet preview
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add workflow-bound next-step packet preview

Objective: make the launched next-step worker packet inspectable without leaving the workflow box.

Scope:

- preview the launched next-step `payload.json` from the workflow result area
- tie it to the launched target role, launched assignment, and launched run

Done when: a reviewer can inspect the launched next-step worker packet body without leaving the workflow result context.

### Ticket 2: Preserve honest packet-preview context

Objective: keep the packet preview truthful.

Scope:

- make clear which request, source assignment, target assignment, role, and run the packet preview belongs to
- make clear whether the preview is exact launched-run packet truth or weaker fallback

Done when: the packet preview is useful without obscuring system truth.

## Suggested File Targets

- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample next-step packet preview basis
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole inbox model
- adding cloud sync or `solaceagi`
- unrelated dashboard polish
- fake packet preview without exact launched-run artifact truth
