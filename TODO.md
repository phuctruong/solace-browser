# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound approval/signoff context

## Current Round

`SAC73` native workflow-bound approval/signoff result.

`SAC72` made the manager able to inspect a compact workflow-bound payload/report preview inside the active workflow result box.

The next blocker is decision context. The manager can now see what the workflow-bound run produced, but the same result box still needs one explicit approval/signoff surface so the manager can see whether the workflow output is pending review, approved, or rejected in the same context.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to see the active workflow run, preview its output, and see the current approval or signoff state for that same workflow result without leaving the workflow surface.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Bind one approval/signoff surface into the workflow result box using the existing Back Office approval objects. Keep the linkage honest if it is session-bound or assignment-derived rather than fully durable.`
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
- workflow-bound artifact and preview surfaces are now visible
- approval/signoff still lives outside the same workflow-bound result area

## Rules

- do not invent a second approval model
- use the existing Back Office approval objects
- keep the approval/signoff surface tied to the workflow-bound request/assignment/run result
- preserve `SAC66` through `SAC72`

## Hard Rejection Criteria

- the manager still cannot see approval/signoff state from the workflow result area
- approval/signoff state is detached from the active workflow result
- the round adds generic review labels without using the existing approval objects

## Required Deliverables

1. one visible workflow-bound approval/signoff surface
2. one visible link from request -> assignment -> run -> preview -> approval/signoff
3. one honest basis line describing whether the approval/signoff linkage is session-bound or durable
4. one Prime Mermaid artifact for request -> assignment -> run -> preview -> approval/signoff
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Surface workflow-bound approval/signoff

Objective: make the workflow result decision-ready.

Scope:

- show one approval or signoff state for the active workflow result
- keep it tied to the selected request and assignment

Done when: a reviewer can tell whether the current workflow result is pending, approved, or rejected.

### Ticket 2: Preserve honest binding semantics

Objective: keep the review surface truthful.

Scope:

- say whether the approval/signoff state is directly durable or inferred from the active assignment path
- do not overstate the persistence model

Done when: the workflow result area is more useful without exaggerating system truth.

## Suggested File Targets

- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample approval/signoff payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole approval system
- cloud sync or `solaceagi`
- unrelated transparency panels
- generic polish without workflow-bound approval truth
