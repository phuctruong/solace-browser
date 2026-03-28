# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native specialist execution evidence and output-log visibility

## Current Round

SAE36 native specialist execution evidence and output-log visibility.

The Dev workspace now shows whether specialist work actually started running and emitted a first output signal. The next step is to make that execution auditable: one visible execution-evidence surface showing the current output log or evidence stream, whether evidence is flowing, and whether the run is streaming, stalled, or terminated.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives enter specialist lanes, confirm inbox receipt, confirm execution readiness, confirm activity start, and inspect the first visible execution evidence`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native specialist execution evidence and output-log visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, governance summary, manager action queue, manager directive packet, delegation handoff, specialist acceptance, specialist readiness, and specialist execution surfaces
- the workspace must show one specialist execution-evidence / output-log surface directly
- the surface must show at least one streaming evidence state, one stalled evidence state, and one terminated evidence state
- the surface must tie evidence state back to specialist, directive, active packet, and visible output or log context honestly
- if evidence values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: running work must visibly produce inspectable evidence rather than stopping at a status label
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether execution is producing visible evidence
- a reviewer still cannot tell whether evidence is streaming, stalled, or terminated
- evidence state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making specialist execution evidence more operationally legible

## Required Deliverables

1. one visible specialist execution-evidence / output-log surface in the Dev workspace
2. one visible tie between evidence entries and specialist/directive/packet context
3. one honest streaming/stalled/terminated evidence summary
4. one honest output-log or evidence-basis summary
5. one Prime Mermaid source artifact for specialist execution evidence visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible specialist execution-evidence surface
Objective: make post-start execution evidence first-class.
Scope: show one visible surface of running specialist work producing observable output directly in the workspace.
Done when: a reviewer can tell whether a worker is actually emitting evidence without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie evidence entries to specialist, directive, and packet context
Objective: stop treating execution evidence as detached theory.
Scope: each entry should reveal which directive, which specialist, and what active packet or output log is involved.
Done when: a reviewer can tell what each evidence entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest execution evidence states
Objective: make specialist execution evidence visibility operationally truthful.
Scope: support at least one streaming evidence state, one stalled evidence state, and one terminated evidence state with visible reasoning.
Done when: the workspace does not imply fake evidence certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one specialist-execution-evidence Prime Mermaid artifact
Objective: capture the move from specialist execution activity to visible execution evidence.
Scope: add one Prime Mermaid artifact for specialist execution evidence visibility.
Done when: the evidence surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make specialist execution evidence visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to directive packet to handoff log to specialist acceptance to specialist readiness to specialist execution to specialist evidence inspection
- one automated test or lightweight scripted verification for the evidence surface
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
- rewriting the role stack instead of making specialist execution evidence more visible
