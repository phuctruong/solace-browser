# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound next-step inbox packet truth

## Current Round

`SAC77` native workflow-bound next-step inbox packet visibility.

`SAC76` made the workflow-bound result box able to launch the newly routed next specialist step through the real runtime run path and report the launched role, app, and run id.

The next blocker is worker truth. The manager can now route and launch from the same workflow box, but still cannot inspect the real worker packet or inbox basis for that newly launched next step from the same chain. That leaves the self-hosting loop strong on execution and weak on handoff truth.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to move a real workflow from request -> assignment -> worker inbox packet -> run -> evidence -> approval -> next routed assignment -> next launch inside Solace Hub using the existing runtime and Back Office objects.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one workflow-bound next-step inbox packet visibility block into the active workflow result area. Keep it tied to the selected request, source assignment, routed target assignment, launched role, and launched run.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-company.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI4 — AI Workers as Orchestrated Systems, Not Models.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/src/browser/inbox_outbox.py`
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
- worker inbox packet truth is still not visible from the same workflow chain

## Rules

- do not invent a second packet model
- use the existing Back Office assignments and real app inbox/outbox filesystem/runtime paths
- keep the visibility bound to the active workflow request/assignment/run result
- do not fake “worker packet visible” unless the result box can point to real inbox basis for the launched next step
- preserve `SAC66` through `SAC76`

## Hard Rejection Criteria

- the manager still cannot inspect the next-step worker packet from the workflow result area
- the packet display is detached from the active request/assignment/run context
- the panel shows generic role text instead of launched worker packet truth
- the result area claims packet truth without clearly stating which target role, assignment, or run it belongs to

## Required Deliverables

1. one visible workflow-bound next-step inbox packet block in the result area
2. one explicit link from request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet
3. one honest basis line describing whether the packet view is backed by exact launched assignment context or a weaker fallback
4. one Prime Mermaid artifact for request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add workflow-bound next-step packet view

Objective: make the launched next step inspectable as worker context, not just executable.

Scope:

- show the next-step worker packet or inbox basis from the workflow result area
- tie it to the launched target role and launched assignment

Done when: a reviewer can inspect the launched next-step worker packet truth without leaving the workflow result context.

### Ticket 2: Preserve honest packet context

Objective: keep the packet display truthful.

Scope:

- make clear which request, source assignment, target assignment, role, and run the packet belongs to
- make clear whether the packet view is exact launched assignment truth or weaker fallback

Done when: the packet display is useful without obscuring system truth.

## Suggested File Targets

- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample next-step packet basis
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole inbox model
- adding cloud sync or `solaceagi`
- unrelated dashboard polish
- fake workflow packet visibility without real assignment or app context
