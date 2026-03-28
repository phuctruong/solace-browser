# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native specialist intake readiness and execution-start visibility

## Current Round

SAR34 native specialist intake readiness and execution-start visibility.

The Dev workspace now shows whether a selected specialist received and accepted the handoff. The next step is to make that acceptance operationally meaningful: one visible intake-readiness surface showing whether the specialist is actually ready to execute, whether the accepted packet cleared intake constraints, and whether execution is queued, ready, or blocked.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives enter specialist lanes, confirm inbox receipt, and know whether the specialist is actually ready to execute the work`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native specialist intake readiness and execution-start visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, governance summary, manager action queue, manager directive packet, delegation handoff, and specialist acceptance surfaces
- the workspace must show one specialist intake-readiness / execution-start surface directly
- the surface must show at least one queued execution, one ready execution, and one blocked execution state
- the surface must tie readiness state back to specialist, directive, accepted packet, and intake constraints honestly
- if readiness values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: accepted work must visibly move toward specialist execution rather than stopping at inbox receipt
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether accepted work is actually ready to execute
- a reviewer still cannot tell whether execution is queued, ready, or blocked
- readiness state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making specialist execution readiness more operationally legible

## Required Deliverables

1. one visible specialist intake-readiness / execution-start surface in the Dev workspace
2. one visible tie between readiness entries and specialist/directive/packet context
3. one honest queued/ready/blocked execution summary
4. one honest intake-constraint or execution-basis summary
5. one Prime Mermaid source artifact for specialist readiness visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible specialist readiness surface
Objective: make post-acceptance execution readiness first-class.
Scope: show one visible surface of accepted manager directives clearing specialist intake directly in the workspace.
Done when: a reviewer can tell whether a worker is actually ready to execute the accepted handoff without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie readiness entries to specialist, directive, and packet context
Objective: stop treating readiness as detached theory.
Scope: each entry should reveal which directive, which specialist, and what accepted packet or intake target is involved.
Done when: a reviewer can tell what each readiness entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest execution readiness states
Objective: make specialist intake visibility operationally truthful.
Scope: support at least one queued execution, one ready execution, and one blocked execution with visible reasoning.
Done when: the workspace does not imply fake readiness certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one specialist-readiness Prime Mermaid artifact
Objective: capture the move from specialist acceptance to execution readiness.
Scope: add one Prime Mermaid artifact for specialist readiness visibility.
Done when: the readiness surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make specialist readiness visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to directive packet to handoff log to specialist acceptance to specialist readiness inspection
- one automated test or lightweight scripted verification for the readiness surface
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
- rewriting the role stack instead of making specialist readiness more visible
