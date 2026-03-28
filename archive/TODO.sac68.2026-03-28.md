# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native assignment routing on selected requests

## Current Round

`SAC68` native manager assignment routing and explicit role activation.

`SAC67` made the manager able to create and select a real `solace-browser` request in Hub. That removed the hidden seed dependency for request creation.

The next blocker is that role routing is still too implicit. New requests are still hard-wired into an immediate `coder` assignment instead of being managed as an explicit routing decision by the Dev Manager. The next round must make assignment routing visible and intentional for the selected request.

## Worker Inbox

- `northstar`: `The Dev Manager must be able to route a selected self-hosting request into the correct specialist lane from Hub itself, and that routing decision must become the visible basis for downstream worker context.`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native assignment-routing surface for the selected request. The manager must be able to choose a target role and create or activate the corresponding assignment through the existing Back Office objects.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/ROADMAP.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI5 — Solace Hub as Mission Control.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-dev-manager/manifest.yaml`
- `/home/phuc/projects/solace-browser/solace-runtime/src/routes/backoffice.rs`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Audit Ground Truth

- request creation is now native in Hub
- selected request state now exists
- downstream worker context can now follow a selected request
- assignment routing is still not a first-class manager decision
- the manager still cannot explicitly choose `design`, `coder`, or `qa` for the selected request inside Hub

## Rules

- do not revert to implicit hard-coded routing
- use the existing `assignments` Back Office table
- keep `SAC66` and `SAC67` runtime-backed flow intact
- make explicit what assignment is active for the selected request
- preserve honesty about any fallback behavior

## Hard Rejection Criteria

- routing is still hard-coded only to `coder`
- the manager still cannot explicitly assign a selected request to a role in Hub
- selected request does not drive the visible active assignment
- the round adds only labels without changing the actual request -> assignment truth path

## Required Deliverables

1. one native assignment-routing control for the selected request
2. one visible selected-role / active-assignment state
3. one visible link from routing decision -> assignment context
4. one Prime Mermaid artifact for request-to-assignment routing
5. one narrow smoke path
6. one narrow automated test

## Current Tickets

### Ticket 1: Add assignment routing control

Objective: make specialist routing a manager action, not a hidden default.

Scope:

- add one visible control for the selected request
- allow explicit assignment to at least `design`, `coder`, or `qa`
- create or activate the relevant assignment record in Back Office

Done when: the manager can route the selected request intentionally from Hub.

### Ticket 2: Surface the active routed assignment

Objective: make downstream role context honest.

Scope:

- show which role is currently routed for the selected request
- ensure assignment context panels follow that routed assignment

Done when: the active assignment is clearly tied to the selected request and chosen role.

### Ticket 3: Preserve the runtime-backed chain

Objective: keep the request -> assignment -> artifact/approval chain coherent.

Scope:

- do not break `SAC66` workflow binding
- do not break `SAC67` request creation/selection

Done when: routing strengthens the durable chain instead of bypassing it.

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
- sample assignment payload
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- full workflow redesign
- cloud sync or `solaceagi`
- another unrelated transparency panel
- generic polish without manager-driven routing truth
