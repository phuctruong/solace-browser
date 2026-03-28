# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for launched-run artifact/evidence linkage

## Current Round

`SAC71` native launched-run artifact and evidence linkage.

`SAC70` made the launched run come back into the selected request/assignment workflow context. That closed the gap between launch and workflow visibility.

The next blocker is evidence truth. The manager can now see which run belongs to the active workflow, but the workflow result still needs one explicit artifact/evidence binding so the manager can see what that run produced without relying on generic run browsing.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to see the launched run as part of the active workflow and see the first artifact/evidence output of that same run in the same workflow context.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Bind the launched run result to one visible artifact/evidence surface for the selected request and assignment. Use the existing artifact/report/event paths and keep the binding honest if it is only session-bound.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
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
- launched run binding is now visible
- first artifact/evidence for the launched run is still not clearly surfaced in the same workflow result box

## Rules

- do not invent a separate artifact model
- use existing runtime artifact/report/event paths
- keep the selected request / assignment / launched run / artifact chain honest
- preserve `SAC66` through `SAC70`

## Hard Rejection Criteria

- the manager still cannot tell what the launched run produced
- artifact/evidence view is still detached from the active workflow result
- the round adds a label without binding to real artifact/report/event paths

## Required Deliverables

1. one visible launched-run artifact/evidence surface tied to the selected workflow
2. one visible link from request -> assignment -> run -> artifact/evidence
3. one honest basis line describing whether the linkage is session-bound or durable
4. one Prime Mermaid artifact for request -> assignment -> run -> artifact
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Surface first artifact/evidence for the launched run

Objective: make the workflow result useful.

Scope:

- show one artifact/report/event result for the launched run
- keep it tied to the selected request and assignment

Done when: a reviewer can see what the active workflow run produced.

### Ticket 2: Preserve honest binding semantics

Objective: keep the workflow truthful.

Scope:

- say whether the artifact/evidence linkage is session-bound or durable
- avoid overstating runtime truth if only the run binding is session-backed

Done when: the surface is useful without exaggerating persistence.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample artifact/evidence payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- redesigning the whole artifact system
- cloud sync or `solaceagi`
- unrelated transparency panels
- generic polish without artifact linkage
