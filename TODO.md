# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native department-memory entry and convention-surface visibility

## Current Round

SAC41 native department-memory entry and convention-surface visibility.

The Dev workspace now shows whether a promotion-ready specialist output has actually requested or entered department memory. The next step is to make that admission tangible: one visible memory-entry surface showing the concrete department-memory record or convention entry that was created, whether it is draft, live, or revoked, and what reusable object it now exposes to the department.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives become trustworthy outputs, see those outputs enter department memory, and inspect the actual reusable memory objects that result`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native department-memory entry and convention-surface visibility panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, governance summary, manager action queue, manager directive packet, delegation handoff, specialist acceptance, specialist readiness, specialist execution, specialist evidence, specialist artifact, specialist provenance, specialist promotion, and specialist memory-admission surfaces
- the workspace must show one department-memory entry / convention-surface panel directly
- the surface must show at least one draft memory-entry state, one live memory-entry state, and one revoked memory-entry state
- the surface must tie memory-entry state back to specialist, directive, active packet, and visible admission context honestly
- if memory-entry values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: admitted outputs must visibly become reusable department memory objects rather than stopping at admission status
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see what concrete memory object was created from an admitted output
- a reviewer still cannot tell whether the current memory entry is draft, live, or revoked
- memory-entry state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making department memory materially inspectable

## Required Deliverables

1. one visible department-memory entry / convention-surface panel in the Dev workspace
2. one visible tie between memory entries and specialist/directive/packet context
3. one honest draft/live/revoked summary
4. one honest memory-object or convention-basis summary
5. one Prime Mermaid source artifact for department-memory entry visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible department-memory entry surface
Objective: make post-admission memory objects first-class.
Scope: show one visible surface of admitted specialist outputs becoming reusable department-memory records directly in the workspace.
Done when: a reviewer can tell what memory object was created without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie memory entries to specialist, directive, and packet context
Objective: stop treating department memory as detached theory.
Scope: each entry should reveal which directive, which specialist, and what active packet or admitted output is involved.
Done when: a reviewer can tell what each memory entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest memory-entry states
Objective: make department-memory visibility operationally truthful.
Scope: support at least one draft entry, one live entry, and one revoked entry with visible reasoning.
Done when: the workspace does not imply fake memory certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one department-memory Prime Mermaid artifact
Objective: capture the move from specialist memory admission to visible reusable department-memory objects.
Scope: add one Prime Mermaid artifact for department-memory entry visibility.
Done when: the memory-entry surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make department-memory visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to directive packet to handoff log to specialist acceptance to specialist readiness to specialist execution to specialist evidence to specialist artifact bundle to specialist provenance to specialist promotion to specialist memory-admission to department-memory entry inspection
- one automated test or lightweight scripted verification for the memory-entry surface
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
- rewriting the role stack instead of making department-memory visibility more visible
