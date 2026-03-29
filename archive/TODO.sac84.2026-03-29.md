# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound next-step approval action truth

## Current Round

`SAC84` native workflow-bound next-step approval action truth.

`SAC83` made the workflow result box able to show whether the launched next-step specialist branch is pending, approved, or rejected on the exact launched branch or whether Hub has fallen back to weaker visibility.

The next blocker is action truth. The manager can now inspect request truth, assignment truth, run truth, packet truth, provenance truth, pickup truth, execution evidence truth, output truth, and approval truth, but still cannot approve or reject that same next-step branch from the same workflow box.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to move a real workflow from request -> assignment -> worker inbox packet -> run -> evidence -> approval -> next routed assignment -> next launch -> next specialist pickup -> next specialist execution evidence -> next specialist output -> next specialist approval truth -> next specialist approval action inside Solace Hub with each step inspectable and mutable from one honest workflow surface.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one workflow-bound next-step approval action block into the active workflow result area. Keep it tied to the selected request, source assignment, target assignment, launched role, launched run, packet provenance, pickup truth, execution evidence truth, output truth, and approval truth already present in the chain.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Communication Protocol

### LEK

Locate existing knowledge first.

- read the exact runtime-backed chain already in `hub-app.js`
- read the current route, launch, packet, preview, provenance, pickup, execution evidence, output, and approval blocks
- read the prior round artifacts before editing

### LEAK

Use this execution loop:

1. `Locate` the real runtime/backoffice/app anchors
2. `Evaluate` what is already true vs what would still be dishonest
3. `Act` with the smallest critical-path mutation that increases durable system truth
4. `Knowledge-return` with changed files, exact commands, exact routes exercised, payload basis, evidence basis, output basis, approval basis, action basis, and remaining risks

### LEC

Maintain one local evidence chain for every new claim:

- runtime route or durable object anchor
- Hub wiring
- narrow test
- smoke path
- Prime Mermaid artifact

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-company.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI4 — AI Workers as Orchestrated Systems, Not Models.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/tests/test_manager_run_specialist_approval_truth.py`

## Audit Ground Truth

- request creation is native
- request selection is native
- assignment routing is native
- execution launch is native
- launched run binding is native
- artifact and preview are visible
- approval/signoff state is visible for the current branch
- approval/reject action is native for the current branch
- workflow-bound next-step routing is native
- workflow-bound next-step launch is native
- workflow-bound next-step packet existence is visible
- workflow-bound next-step packet preview is visible
- workflow-bound next-step packet provenance is visible
- workflow-bound next-step specialist pickup truth is visible
- workflow-bound next-step specialist execution evidence truth is visible
- workflow-bound next-step specialist output truth is visible
- workflow-bound next-step specialist approval truth is visible
- next-step approval action for that exact launched branch is still not available in the same workflow box

## Rules

- do not invent a second approval action model
- use the existing request, assignment, run, packet, provenance, pickup, execution evidence, output, and approval context already present in the workflow chain
- keep the approval action bound to the active workflow request/assignment/run result
- do not fake “specialist branch approved or rejected” unless the result box can clearly state the target role and exact launched branch context it belongs to
- preserve `SAC66` through `SAC83`

## Hard Rejection Criteria

- the manager still cannot approve or reject next-step branch truth from the workflow result area
- the action view is detached from the launched target assignment or launched run
- the panel shows generic role prose instead of explicit action truth
- the result area claims approval action truth without clearly stating which request, source assignment, target assignment, role, and run the action belongs to

## Required Deliverables

1. one visible workflow-bound next-step approval action block in the result area
2. one explicit link from request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet preview -> next-step packet provenance -> next-step specialist pickup -> next-step specialist execution evidence -> next-step specialist output -> next-step specialist approval truth -> next-step specialist approval action
3. one honest basis line describing whether the approval action view is exact launched-workflow truth or a weaker fallback
4. one Prime Mermaid artifact for request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet preview -> next-step packet provenance -> next-step specialist pickup -> next-step specialist execution evidence -> next-step specialist output -> next-step specialist approval truth -> next-step specialist approval action
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add workflow-bound next-step approval action truth

Objective: make the launched next-step branch mutable through real approval action, not just inspectable approval state.

Scope:

- show next-step approval action from the workflow result area
- tie it to the launched next-step role, assignment, run, packet preview, packet provenance, pickup truth, execution evidence truth, output truth, and approval truth

Done when: a reviewer can approve or reject the exact launched next-step branch without leaving the workflow result context.

### Ticket 2: Preserve honest approval action context

Objective: keep the action display truthful.

Scope:

- make clear which request, source assignment, target assignment, role, and run the approval action belongs to
- make clear whether the action state is exact launched-workflow truth or weaker fallback

Done when: the action display is useful without obscuring system truth.

## Suggested File Targets

- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample next-step specialist approval action basis
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole inbox model
- adding cloud sync or `solaceagi`
- unrelated dashboard polish
- fake approval action truth without exact request/assignment/run packet relationship
