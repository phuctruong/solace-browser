# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound next-step specialist pickup truth

## Current Round

`SAC80` native workflow-bound next-step specialist pickup and acceptance truth.

`SAC79` made the workflow-bound result box able to show packet provenance and handoff truth for the launched next-step branch.

The next blocker is worker receipt. The manager can now inspect packet content and packet provenance, but still cannot see whether the launched specialist actually picked up and accepted that exact packet in the same workflow chain. That keeps the self-hosting loop strong on planning truth and weaker on specialist handoff truth.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to move a real workflow from request -> assignment -> worker inbox packet -> run -> evidence -> approval -> next routed assignment -> next launch -> next specialist pickup inside Solace Hub with packet content, packet provenance, and specialist receipt all inspectable in the same workflow surface.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one workflow-bound next-step specialist pickup and acceptance block into the active workflow result area. Keep it tied to the selected request, source assignment, target assignment, launched role, launched run, and launched packet provenance.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Communication Protocol

### LEK

Locate existing knowledge first.

- read the exact runtime-backed chain already in `hub-app.js`
- read the exact current route, launch, packet, preview, and provenance blocks
- read the prior round artifacts before editing

### LEAK

Use this execution loop:

1. `Locate` the real runtime/backoffice/app anchors
2. `Evaluate` what is already true vs what would still be dishonest
3. `Act` with the smallest critical-path mutation that increases durable system truth
4. `Knowledge-return` with changed files, exact commands, exact routes exercised, payload basis, and remaining risks

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
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/tests/test_manager_run_packet_provenance_truth.py`

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
- workflow-bound next-step packet preview is visible
- workflow-bound next-step packet provenance is visible
- specialist pickup and acceptance truth for that exact launched packet are still not visible in the same workflow box

## Rules

- do not invent a second pickup model
- use the existing request, assignment, run, and packet context already present in the workflow chain
- keep the pickup display bound to the active workflow request/assignment/run result
- do not fake “specialist accepted packet” unless the result box can clearly state the target role and exact launched branch context it belongs to
- preserve `SAC66` through `SAC79`

## Hard Rejection Criteria

- the manager still cannot inspect next-step specialist pickup or acceptance truth from the workflow result area
- the pickup view is detached from the launched target assignment or launched run
- the panel shows generic role prose instead of explicit packet receipt or acceptance truth
- the result area claims pickup truth without clearly stating which request, source assignment, target assignment, role, and run the acceptance belongs to

## Required Deliverables

1. one visible workflow-bound next-step specialist pickup or acceptance block in the result area
2. one explicit link from request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet preview -> next-step packet provenance -> next-step specialist pickup
3. one honest basis line describing whether the pickup view is exact launched-workflow truth or a weaker fallback
4. one Prime Mermaid artifact for request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet preview -> next-step packet provenance -> next-step specialist pickup
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add workflow-bound next-step specialist pickup truth

Objective: make the launched next-step packet traceable into actual specialist receipt, not just content and provenance.

Scope:

- show specialist pickup or acceptance state from the workflow result area
- tie it to the launched next-step role, assignment, packet preview, and packet provenance

Done when: a reviewer can see whether the exact launched next-step packet was actually picked up by the intended specialist without leaving the workflow result context.

### Ticket 2: Preserve honest pickup context

Objective: keep the pickup display truthful.

Scope:

- make clear which request, source assignment, target assignment, role, and run the pickup state belongs to
- make clear whether the pickup state is exact launched-workflow truth or weaker fallback

Done when: the pickup display is useful without obscuring system truth.

## Suggested File Targets

- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample next-step specialist pickup basis
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole inbox model
- adding cloud sync or `solaceagi`
- unrelated dashboard polish
- fake pickup truth without exact request/assignment/run packet relationship
