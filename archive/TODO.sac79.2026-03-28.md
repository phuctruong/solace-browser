# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound next-step packet provenance and handoff truth

## Current Round

`SAC79` native workflow-bound next-step packet provenance and handoff truth.

`SAC78` made the workflow-bound result box able to preview the launched next-step `payload.json` inline and distinguish exact launched-run packet truth from weaker fallback.

The next blocker is provenance. The manager can now inspect the next-step packet body, but still cannot see the explicit source-to-target handoff contract for that packet in the same workflow chain. That means packet content is visible, but packet origin and packet ownership are still weaker than they need to be for a truly symmetric self-hosting loop.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to move a real workflow from request -> assignment -> worker inbox packet -> run -> evidence -> approval -> next routed assignment -> next launch inside Solace Hub, with packet content and packet provenance both inspectable in the same workflow surface.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one workflow-bound next-step packet provenance and handoff block into the active workflow result area. Keep it tied to the selected request, source assignment, target assignment, launched role, and launched run.`
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
- workflow-bound next-step packet preview is visible
- packet provenance and handoff truth are still not explicit in the same workflow box

## Rules

- do not invent a second handoff model
- use the existing request, assignment, run, and packet context already present in the workflow chain
- keep the provenance display bound to the active workflow request/assignment/run result
- do not fake “packet provenance” unless the result box can clearly state source assignment, target assignment, target role, and launched run relationship
- preserve `SAC66` through `SAC78`

## Hard Rejection Criteria

- the manager still cannot inspect next-step packet provenance from the workflow result area
- the provenance view is detached from the launched target assignment or launched run
- the panel shows generic role prose instead of explicit source-to-target handoff truth
- the result area claims provenance truth without clearly stating which request, source assignment, target assignment, role, and run the packet belongs to

## Required Deliverables

1. one visible workflow-bound next-step packet provenance block in the result area
2. one explicit link from request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet preview -> next-step packet provenance
3. one honest basis line describing whether the provenance view is exact launched-workflow truth or a weaker fallback
4. one Prime Mermaid artifact for request -> assignment -> approval -> next-step route -> next-step launch -> next-step packet preview -> next-step packet provenance
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add workflow-bound next-step packet provenance

Objective: make the launched next-step worker packet traceable as a real handoff, not just visible content.

Scope:

- show source assignment, target assignment, target role, and launched run relationship from the workflow result area
- tie it to the launched next-step packet preview

Done when: a reviewer can see where the launched next-step packet came from and who it belongs to without leaving the workflow result context.

### Ticket 2: Preserve honest provenance context

Objective: keep the provenance display truthful.

Scope:

- make clear which request, source assignment, target assignment, role, and run the provenance belongs to
- make clear whether the provenance is exact launched-workflow truth or weaker fallback

Done when: the provenance display is useful without obscuring system truth.

## Suggested File Targets

- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample next-step packet provenance basis
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole inbox model
- adding cloud sync or `solaceagi`
- unrelated dashboard polish
- fake provenance without exact request/assignment/run packet relationship
