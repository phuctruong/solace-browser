# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native convention-proof linkage and evidence-verdict visibility

## Current Round

`SAC47` native convention-proof linkage and evidence-verdict visibility.

The Dev workspace now shows whether an active convention changed the target output. The next step is to make that change auditable: one visible surface showing what proof or evidence verdict confirms the constrained output, whether the proof is verified, partial, or missing, and how that verdict ties back to the convention lineage.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives become trustworthy outputs, see those outputs enter department memory, see that memory become callable, see exactly how it is invoked into the next packet, see whether the target received it, see whether the target execution activated it, see what constrained output it produced, and see the proof verdict that confirms or rejects that constrained output`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native convention-proof linkage and evidence-verdict panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, convention effect visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI19 — Measuring Solace System Efficiency.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, memory-reuse, convention-invocation, convention-delivery, convention-activation, and convention-effect surfaces
- the workspace must show one direct convention-proof or evidence-verdict panel tied to a visible constrained output
- the surface must show at least one verified-proof state, one partial-proof state, and one missing-proof state
- the surface must tie proof state back to visible effect context, target runtime context, artifact context, and convention lineage honestly
- if proof values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: active department memory must visibly produce governed evidence, not just changed output
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether a constrained output is actually verified by visible evidence
- a reviewer still cannot tell whether the current proof verdict is verified, partial, or missing
- proof state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making convention evidence materially auditable

## Required Deliverables

1. one visible convention-proof or evidence-verdict panel in the Dev workspace
2. one visible tie between proof state and effect / runtime / artifact / convention context
3. one honest verified / partial / missing summary
4. one honest proof-basis or evidence-verdict basis summary
5. one Prime Mermaid source artifact for convention-proof visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible convention-proof surface
Objective: make constrained outputs visibly auditable.
Scope: show one visible surface of proof or evidence verdict attached to a constrained artifact, log, or run output directly in the workspace.
Done when: a reviewer can tell how the current constrained output was verified without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie proof state to effect and artifact context
Objective: stop treating evidence verdicts as detached theory.
Scope: each proof entry should reveal which active convention, which runtime, which produced artifact, and what evidence verdict basis is involved.
Done when: a reviewer can tell what each proof verdict refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest proof states
Objective: make convention evidence operationally truthful.
Scope: support at least one verified state, one partial state, and one missing state with visible reasoning.
Done when: the workspace does not imply fake proof certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one convention-proof Prime Mermaid artifact
Objective: capture the move from constrained output to governed evidence verdict.
Scope: add one Prime Mermaid artifact for convention-proof visibility.
Done when: the proof surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make convention proof visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection to proof inspection
- one automated test or lightweight scripted verification for the proof surface
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
- rewriting the role stack instead of making convention evidence auditable
