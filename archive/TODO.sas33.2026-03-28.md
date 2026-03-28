# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native specialist acceptance state and inbox-delivery visibility

## Current Round

SAS33 native specialist acceptance state and inbox-delivery visibility.

The Dev workspace now shows one bounded delegation handoff log. The next step is to make that handoff operationally credible: one visible acceptance surface showing whether the selected specialist actually accepted the directive, whether the handoff reached the worker inbox, and whether delivery is pending, confirmed, or rejected.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives enter specialist lanes and confirm whether the specialist actually received and accepted the work`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native specialist acceptance state and inbox-delivery visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, governance summary, manager action queue, manager directive packet, and delegation handoff surfaces
- the workspace must show one specialist acceptance/inbox-delivery surface directly
- the surface must show at least one pending delivery, one confirmed acceptance, and one rejected or unavailable delivery state
- the surface must tie delivery state back to specialist, directive, inbox target, and handoff context honestly
- if acceptance values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: Dev Manager directives must not stop at dispatch; specialist receipt and acceptance must be visible
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether a specialist actually received the handoff
- a reviewer still cannot tell whether inbox delivery is pending, confirmed, or rejected
- delivery state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making specialist acceptance more operationally legible

## Required Deliverables

1. one visible specialist acceptance / inbox-delivery surface in the Dev workspace
2. one visible tie between acceptance entries and specialist/directive/inbox context
3. one honest pending/confirmed/rejected delivery summary
4. one honest inbox-target or delivery-basis summary
5. one Prime Mermaid source artifact for specialist acceptance visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible specialist acceptance surface
Objective: make inbox delivery first-class.
Scope: show one visible surface of manager directives reaching specialist inboxes directly in the workspace.
Done when: a reviewer can tell whether a worker actually received the handoff without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie acceptance entries to specialist, directive, and inbox context
Objective: stop treating delivery as detached theory.
Scope: each entry should reveal which directive, which specialist, and what inbox target or worker surface is involved.
Done when: a reviewer can tell what each acceptance entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest delivery states
Objective: make specialist receipt visibility operationally truthful.
Scope: support at least one pending delivery, one confirmed acceptance, and one rejected or unavailable delivery with visible reasoning.
Done when: the workspace does not imply fake acceptance certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one specialist-acceptance Prime Mermaid artifact
Objective: capture the move from delegation handoff to specialist inbox delivery.
Scope: add one Prime Mermaid artifact for specialist acceptance visibility.
Done when: the acceptance surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make specialist acceptance visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to directive packet to handoff log to specialist acceptance inspection
- one automated test or lightweight scripted verification for the acceptance surface
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
- rewriting the role stack instead of making specialist acceptance more visible
