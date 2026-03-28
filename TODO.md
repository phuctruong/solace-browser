# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native convention invocation and next-packet reuse visibility

## Current Round

`SAC43` native convention invocation and next-packet reuse visibility.

The Dev workspace now shows whether department memory became callable. The next step is to make that callable memory operationally routed: one visible surface showing how a callable convention is actually invoked into the next directive, next worker packet, or next specialist run.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives become trustworthy outputs, see those outputs enter department memory, see that memory become callable, and see exactly how that callable convention enters the next packet or run`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native convention invocation and next-packet reuse panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI10 — The Solace Execution Graph.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI14 — Convention Store as Persistent Intelligence.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, and memory-reuse surfaces
- the workspace must show one direct convention-invocation or next-packet reuse panel tied to a visible callable department-memory entry
- the surface must show at least one invoked state, one queued state, and one blocked invocation state
- the surface must tie invocation state back to visible memory-entry context, callable convention context, specialist context, and directive or packet context honestly
- if convention invocation values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: department memory must visibly feed the next managed action, not stop at “callable”
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether a callable convention was actually routed into the next directive or worker packet
- a reviewer still cannot tell whether the current convention is invoked, queued, or blocked
- invocation state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making callable department memory materially routed

## Required Deliverables

1. one visible convention-invocation or next-packet reuse panel in the Dev workspace
2. one visible tie between invocation state and memory-entry / callable-convention / directive context
3. one honest invoked / queued / blocked summary
4. one honest invocation-basis or next-packet basis summary
5. one Prime Mermaid source artifact for convention invocation visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible convention-invocation surface
Objective: make callable department memory operationally routed.
Scope: show one visible surface of callable memory objects feeding a next directive, next packet, or next specialist run directly in the workspace.
Done when: a reviewer can tell how the current callable convention is actually routed without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie invocation state to memory-entry and directive context
Objective: stop treating invocation as detached theory.
Scope: each invocation entry should reveal which memory object, which callable convention, and what next directive or packet basis is involved.
Done when: a reviewer can tell what each invocation refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest invocation states
Objective: make convention invocation operationally truthful.
Scope: support at least one invoked state, one queued state, and one blocked state with visible reasoning.
Done when: the workspace does not imply fake invocation certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one convention-invocation Prime Mermaid artifact
Objective: capture the move from callable department memory to routed next-packet convention use.
Scope: add one Prime Mermaid artifact for convention invocation visibility.
Done when: the invocation surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make convention invocation visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection
- one automated test or lightweight scripted verification for the invocation surface
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
- rewriting the role stack instead of making department memory operationally routed
