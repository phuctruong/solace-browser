# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for runtime-backed request creation and active workflow selection

## Current Round

`SAC67` native manager request creation and request-selection truth.

`SAC66` was the first real pivot away from pure role-derived visibility. The Hub now reads a real Back Office request/assignment/artifact/approval chain for one workflow.

That is progress, but it is still not self-hosting enough because the workflow currently depends on an external seed script. The next step is to let the Dev Manager create and select the active `solace-browser` request directly in Hub, then drive the rest of the runtime-backed workflow from that selected request.

## Worker Inbox

- `northstar`: `Solace Browser must let the Dev Manager initiate and inspect one real self-hosting request in the browser itself, not only through external seeding scripts.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add one native manager request-creation and request-selection path in Hub, backed by the existing Back Office objects, and use that selected request as the visible basis for assignment and worker workflow context.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/data/apps/solace-dev-manager/manifest.yaml`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Audit Ground Truth

- Back Office objects now exist and are being read for one workflow.
- The current runtime-backed path still depends on `scripts/seed-saz66-runtime-binding.sh`.
- The manager still cannot create the canonical request directly inside the Hub workspace.
- Active workflow selection is still too implicit and too dependent on role/run context.

## Rules

- do not revert to a new mock panel
- use the existing `projects`, `requests`, `assignments`, `artifacts`, and `approvals` Back Office objects
- keep the manager flow honest about what is runtime-backed and what is still fallback
- preserve the current integrated workspace and `SAC66` binding
- do not introduce a second parallel request model

## Hard Rejection Criteria

- the manager still cannot create one real `solace-browser` request from Hub
- the visible active workflow is still determined only by fallback role/run context
- request selection does not visibly drive assignment and worker context
- the result depends entirely on an external seed script again

## Required Deliverables

1. one native Hub request-creation path for `solace-browser`
2. one visible active-request selection surface
3. one visible link from selected request -> assignment context
4. one visible link from selected request -> worker inbox/outbox context
5. one Prime Mermaid artifact for request creation and selection
6. one narrow smoke path
7. one narrow automated test

## Current Tickets

### Ticket 1: Add native request creation

Objective: make the manager able to start the self-hosting loop inside Hub.

Scope:

- create one narrow UI path that creates a `requests` record in `solace-dev-manager`
- tie it to the `solace-browser` project
- keep the interaction minimal and reviewable

Done when: a reviewer can create a real `solace-browser` request from the Hub workspace.

### Ticket 2: Add active request selection

Objective: make the workflow basis explicit.

Scope:

- show a visible selected request in the manager workspace
- make selected request context flow into assignment and worker panels
- keep fallback mode explicit if no request is selected

Done when: a reviewer can tell which request the current workflow is about.

### Ticket 3: Preserve runtime-backed linkage

Objective: keep `SAC66` intact while making it manager-driven.

Scope:

- ensure assignment, artifact, and approval reads still work
- ensure selected request drives the same durable chain

Done when: the new manager path strengthens the existing runtime-backed chain instead of bypassing it.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/backoffice.rs`
- `tests/`
- `scripts/`
- `specs/solace-dev/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample created request payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- broad workflow redesign
- cloud sync or `solaceagi`
- another long post-release panel chain
- generic polish without manager-driven runtime truth
