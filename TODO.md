# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for workflow-bound payload/report preview

## Current Round

`SAC72` native workflow-bound payload/report preview.

`SAC71` made the workflow-bound launched run show its first artifact and event links. That means the manager can now see that the active workflow produced concrete outputs.

The next blocker is readability inside Hub. The manager still has to leave the workflow box to inspect the most important outputs. The next round must surface one compact preview of the workflow-bound run payload/report inside the same workflow result context.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to see the active workflow run, its first artifact links, and a compact preview of what that run produced without leaving the workflow surface.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Bind one compact payload/report preview into the workflow-bound run result panel using the existing artifact routes. Keep the preview honest if the linkage is only session-bound.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Audit Ground Truth

- request creation is native
- request selection is native
- assignment routing is native
- execution launch is native
- launched run binding is native
- workflow-bound artifact/evidence links are now visible
- payload/report content still requires leaving the workflow panel

## Rules

- do not invent a second preview system
- use the existing artifact routes already used elsewhere in Hub
- keep the preview bound to the selected request / assignment / launched run context
- preserve `SAC66` through `SAC71`

## Hard Rejection Criteria

- the manager still cannot preview what the workflow-bound run produced from the workflow result area
- the preview is detached from the selected workflow result
- the round adds generic preview UI without proving it is using the workflow-bound run

## Required Deliverables

1. one visible compact payload/report preview tied to the workflow-bound run
2. one visible link from request -> assignment -> run -> preview
3. one honest basis line describing whether the preview is session-bound or durable
4. one Prime Mermaid artifact for request -> assignment -> run -> preview
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Surface compact workflow-bound preview

Objective: make the workflow result immediately useful.

Scope:

- show one compact payload or report preview in the workflow result box
- keep it tied to the workflow-bound run, not generic selected run state

Done when: a reviewer can inspect the first useful output without leaving the workflow result area.

### Ticket 2: Preserve honest binding semantics

Objective: keep the preview truthful.

Scope:

- say whether the preview comes from workflow launch binding or weaker fallback state
- do not imply durability if it is only session-backed

Done when: the preview is helpful without overstating system truth.

## Suggested File Targets

- `solace-hub/src/hub-app.js`
- `solace-hub/src/index.html`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample preview payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole preview system
- cloud sync or `solaceagi`
- unrelated transparency panels
- generic polish without workflow-bound preview truth
