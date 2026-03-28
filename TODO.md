# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for one runtime-backed Solace Dev workflow

## Current Round

`SAC66` native Back Office request/assignment/run truth for one self-hosting Dev loop.

The workspace now exposes many useful panels, but the audit shows the real gap clearly: too much of the Dev Manager and specialist flow is still `role-derived` in [hub-app.js](/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js) instead of being hydrated from the real Back Office and app-run substrate that already exists in:

- `solace-runtime/src/backoffice/schema.rs`
- `solace-runtime/src/routes/backoffice.rs`
- `solace-runtime/src/routes/apps.rs`
- `data/apps/solace-dev-manager/manifest.yaml`
- `data/apps/solace-design/manifest.yaml`
- `data/apps/solace-coder/manifest.yaml`
- `data/apps/solace-qa/manifest.yaml`

This round is a deliberate pivot away from adding another isolated visibility panel. The goal is to make one real Solace Dev workflow exist end to end for `solace-browser` itself.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, and it must be able to use one real Back Office request -> assignment -> worker inbox -> run -> evidence -> approval/release path to improve Solace Browser itself.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Bind one self-hosting Solace Dev workflow to the real Back Office and runtime. Use durable request/assignment/run objects instead of another role-derived panel.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI6 — Solace Browser as Execution & Proof Layer.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI9 — Conventions as the Core Product Object.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-browser/solace-runtime/src/backoffice/schema.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/apps.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Audit Ground Truth

The current audit says:

- Back Office already exists.
- Worker app manifests already exist.
- Run history, events, and artifact serving already exist.
- The Dev workspace is stronger on transparency than on durable system truth.
- Many later surfaces explicitly admit they are `role-derived mocks`.

This round must reduce that gap materially.

## Rules

- do not add another isolated “state panel” as the main deliverable
- bind the visible Dev workspace to real Back Office records and real app-run paths
- use one real `solace-browser` request as the canonical proof path
- preserve the current integrated workspace and existing review surfaces
- if anything remains mocked, say so in the UI and in the evidence return
- prefer wiring existing runtime/backoffice routes over inventing parallel state
- do not expand into `solaceagi`, billing, cloud sync, or unrelated browser platform work

## Hard Rejection Criteria

- the result still centers on a new mock panel instead of one durable workflow
- the Dev Manager still cannot see a real request/assignment/run path for `solace-browser`
- the worker inbox/outbox view is still detached from Back Office request/assignment truth
- no real run/evidence path is shown for the selected request
- the implementation invents a second object model instead of using the existing Back Office/runtime

## Required Deliverables

1. one real Back Office request object for `solace-browser`
2. one real manager assignment object linked to that request
3. one visible worker inbox packet derived from that assignment
4. one visible run/evidence binding for that assignment
5. one visible human review or approval state linked to the same object chain
6. one Prime Mermaid artifact describing this runtime-backed flow
7. one narrow smoke path
8. one narrow automated test

## Current Tickets

### Ticket 1: Define the runtime-backed object chain

Objective: stop the workspace from floating above the system truth.

Scope:

- choose or create the minimum durable objects needed for one self-hosting loop:
  - `request`
  - `assignment`
  - `run`
  - `approval` or `release_decision`
- use the existing Back Office manifest/runtime rather than parallel ad hoc JSON

Done when: one reviewer can trace a single `solace-browser` improvement request through these objects.

### Ticket 2: Hydrate manager view from Back Office truth

Objective: make the Dev Manager operate on durable records.

Scope:

- surface the chosen request and assignment in the workspace
- show IDs, titles, status, linked worker, and linked run honestly
- make it obvious what is runtime-backed vs still derived

Done when: the manager panel is grounded in real records, not just role-derived text.

### Ticket 3: Bind worker inbox/outbox to the same chain

Objective: make worker operation visible as part of the same workflow.

Scope:

- show the selected worker packet as derived from the selected assignment
- show the run/evidence/artifact path tied to that packet
- show at least one concrete linkage between assignment and outbox/run result

Done when: the inbox/outbox view is clearly part of the same durable object chain.

### Ticket 4: Add one Prime Mermaid flow artifact

Objective: record the runtime-backed self-hosting loop as source truth.

Scope:

- add one Prime Mermaid artifact for:
  - request
  - assignment
  - worker packet
  - run
  - evidence
  - approval/release decision

Done when: the flow is committed as source truth and matches the real implementation.

### Ticket 5: Add one smoke path and one narrow test

Objective: make the new binding reviewable and repeatable.

Scope:

- one smoke path from workspace load to request selection to assignment inspection to worker packet inspection to run/evidence inspection
- one automated test asserting that the workspace is reading the runtime-backed chain rather than only role-derived mocks

Done when: a reviewer can prove the path without guessing.

## Suggested File Targets

- `solace-runtime/src/routes/backoffice.rs`
- `solace-runtime/src/routes/apps.rs`
- `data/apps/solace-dev-manager/manifest.yaml`
- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `specs/solace-dev/`
- `tests/`
- `scripts/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample request/assignment/run payloads
- artifact/report paths
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- adding another long post-release surface chain
- building cloud sync or `solaceagi`
- rewriting the entire runtime
- generic UI polish without durable workflow improvement
