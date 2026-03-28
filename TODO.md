# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native delegation handoff log and specialist dispatch visibility

## Current Round

SAH32 native delegation handoff log and specialist dispatch visibility.

The Dev workspace now shows one bounded manager directive packet. The next step is to make that directive operational: one visible handoff log showing which specialist or lane the directive was dispatched to, what handoff payload or target it carries, and whether the delegation is pending, accepted, or blocked.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see not just directives, but the actual handoff path into specialist execution`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native delegation handoff log and specialist dispatch visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, run history, inspection context, and artifact inspection behavior.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-company.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, governance summary, manager action queue, and manager directive packet surfaces
- the workspace must show one delegation handoff log directly
- the handoff log must show at least one target specialist or lane, one dispatch payload or target, and one pending/accepted/blocked dispatch state
- the log must tie dispatch state back to directive and specialist context honestly
- if dispatch values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: Dev Manager directives must visibly enter specialist lanes
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see where a directive was dispatched
- a reviewer still cannot tell whether a specialist handoff is pending, accepted, or blocked
- handoff state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making specialist dispatch more operationally legible

## Required Deliverables

1. one visible delegation handoff log in the Dev workspace
2. one visible tie between handoff entries and directive/specialist context
3. one honest pending/accepted/blocked dispatch summary
4. one honest handoff-payload or dispatch-basis summary
5. one Prime Mermaid source artifact for delegation-handoff visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible delegation handoff log
Objective: make specialist dispatch first-class.
Scope: show one visible log of manager directives entering specialist lanes directly in the workspace.
Done when: a reviewer can tell where a directive is going without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie handoff entries to directive and specialist context
Objective: stop treating dispatch as detached theory.
Scope: each entry should reveal which directive, which specialist/lane, and what payload or target is involved.
Done when: a reviewer can tell what each dispatch entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest handoff states
Objective: make specialist dispatch visibility operationally truthful.
Scope: support at least one pending dispatch, one accepted dispatch, and one blocked or deferred dispatch with visible reasoning.
Done when: the workspace does not imply fake delegation certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one delegation-handoff Prime Mermaid artifact
Objective: capture the move from manager directive to specialist dispatch.
Scope: add one Prime Mermaid artifact for delegation-handoff visibility.
Done when: the handoff log is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make delegation handoff visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to directive packet to handoff-log inspection
- one automated test or lightweight scripted verification for the handoff surface
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `specs/solace-dev/`
- `tests/`
- `scripts/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact routes or APIs exercised
- sample response payloads
- artifact/report paths
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- adding new specialist roles beyond manager, design, coder, and QA
- broad cloud sync, billing, or `solaceagi` work
- unrelated Chromium platform changes
- rewriting the role stack instead of making delegation handoff more visible
