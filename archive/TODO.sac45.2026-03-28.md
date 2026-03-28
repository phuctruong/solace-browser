# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native convention-activation and target-execution visibility

## Current Round

`SAC45` native convention-activation and target-execution visibility.

The Dev workspace now shows whether an invoked convention reached the target packet. The next step is to make that delivery operationally real: one visible surface showing whether the target execution actually activated the delivered convention, whether it is actively constraining the next run, and whether activation is live, queued, or failed.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives become trustworthy outputs, see those outputs enter department memory, see that memory become callable, see exactly how it is invoked into the next packet, see whether the target received it, and see whether the target execution actually activated that convention`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native convention-activation and target-execution panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI10 — The Solace Execution Graph.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, memory-reuse, convention-invocation, and convention-delivery surfaces
- the workspace must show one direct convention-activation or target-execution panel tied to a visible delivered convention
- the surface must show at least one active state, one queued-activation state, and one failed-activation state
- the surface must tie activation state back to visible delivery context, target worker or packet context, and directive context honestly
- if activation values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: routed department memory must visibly constrain the next managed execution target rather than stop at delivery
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether a delivered convention actually activated the next execution target
- a reviewer still cannot tell whether the current activation is active, queued, or failed
- activation state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making target execution materially reviewable

## Required Deliverables

1. one visible convention-activation or target-execution panel in the Dev workspace
2. one visible tie between activation state and delivery / packet / directive context
3. one honest active / queued / failed summary
4. one honest activation-basis or execution-binding basis summary
5. one Prime Mermaid source artifact for convention-activation visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible convention-activation surface
Objective: make delivered department memory visibly active in the next execution target.
Scope: show one visible surface of a delivered convention becoming an active, queued, or failed constraint in a next directive, next packet, or next specialist run.
Done when: a reviewer can tell whether the current delivered convention actually activated without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie activation state to delivery and packet context
Objective: stop treating execution activation as detached theory.
Scope: each activation entry should reveal which delivered convention, which target worker or packet, and what directive basis is involved.
Done when: a reviewer can tell what each activation refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest activation states
Objective: make convention activation operationally truthful.
Scope: support at least one active state, one queued state, and one failed state with visible reasoning.
Done when: the workspace does not imply fake activation certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one convention-activation Prime Mermaid artifact
Objective: capture the move from convention delivery to target execution binding.
Scope: add one Prime Mermaid artifact for convention-activation visibility.
Done when: the activation surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make convention activation visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection
- one automated test or lightweight scripted verification for the activation surface
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
- rewriting the role stack instead of making convention activation reviewable
