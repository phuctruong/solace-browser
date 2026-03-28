# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native department-memory reuse and callable-convention visibility

## Current Round

`SAC42` native department-memory reuse path and callable-convention visibility.

The Dev workspace now shows whether a specialist output entered department memory and what reusable object it became. The next step is to make that memory operational: one visible surface showing how the Dev Manager can see a live department-memory entry become callable, reusable, and promotable into the next directive or worker packet.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives become trustworthy outputs, see those outputs enter department memory, and see that department memory become callable for the next specialist task`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native department-memory reuse and callable-convention panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI9 — Conventions as the Core Product Object.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI14 — Convention Store as Persistent Intelligence.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI16 — Automatic Convention Distillation.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, and department-memory surfaces
- the workspace must show one direct reuse or callable-convention panel tied to a visible department-memory entry
- the surface must show at least one callable state, one limited state, and one blocked or revoked reuse state
- the surface must tie reuse state back to visible memory-entry context, specialist context, and directive or packet reuse context honestly
- if callable conventions are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: department memory must visibly feed the next managerial or specialist action rather than stopping at archival display
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether a memory entry is callable in the next directive or worker packet
- a reviewer still cannot tell whether the current reusable convention is live, limited, or blocked
- reuse state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making department memory materially reusable

## Required Deliverables

1. one visible department-memory reuse or callable-convention panel in the Dev workspace
2. one visible tie between callable state and memory-entry / specialist / directive context
3. one honest callable / limited / blocked summary
4. one honest reuse-basis or next-packet basis summary
5. one Prime Mermaid source artifact for department-memory reuse visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible department-memory reuse surface
Objective: make department memory callable instead of archival only.
Scope: show one visible surface of reusable memory objects feeding a next directive, next packet, or next specialist handoff directly in the workspace.
Done when: a reviewer can tell how the current department-memory entry would be reused without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie reuse state to memory-entry and directive context
Objective: stop treating reuse as detached theory.
Scope: each callable entry should reveal which memory object, which specialist context, and what next directive or packet basis is involved.
Done when: a reviewer can tell what each callable convention refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest reuse states
Objective: make department-memory reuse operationally truthful.
Scope: support at least one callable state, one limited state, and one blocked state with visible reasoning.
Done when: the workspace does not imply fake reuse certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one department-memory reuse Prime Mermaid artifact
Objective: capture the move from department-memory entry to callable department convention.
Scope: add one Prime Mermaid artifact for department-memory reuse visibility.
Done when: the reuse surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make department-memory reuse visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection
- one automated test or lightweight scripted verification for the reuse surface
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
- broad cloud sync, billing, `solaceagi` work
- unrelated Chromium platform changes
- rewriting the role stack instead of making department memory callable
