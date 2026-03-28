# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native specialist artifact provenance and bundle-integrity visibility

## Current Round

SAV38 native specialist artifact provenance and bundle-integrity visibility.

The Dev workspace now shows the current artifact bundle and run outputs for specialist work. The next step is to make those bundles trustworthy: one visible provenance and integrity surface showing where the bundle came from, whether the artifact set is complete, and whether integrity is verified, partial, or invalid.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives enter specialist lanes, confirm inbox receipt, confirm execution readiness, inspect execution evidence, inspect run artifacts, and judge whether the current artifact bundle is trustworthy`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native specialist artifact provenance and bundle-integrity visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, governance summary, manager action queue, manager directive packet, delegation handoff, specialist acceptance, specialist readiness, specialist execution, specialist evidence, and specialist artifact surfaces
- the workspace must show one specialist artifact-provenance / bundle-integrity surface directly
- the surface must show at least one verified bundle state, one partial bundle state, and one invalid bundle state
- the surface must tie integrity state back to specialist, directive, active packet, and visible bundle provenance honestly
- if provenance values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: inspectable artifacts must visibly carry trust and integrity context rather than stopping at file names
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether the current artifact bundle is trustworthy
- a reviewer still cannot tell whether the current bundle is verified, partial, or invalid
- provenance state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making specialist artifact trust more operationally legible

## Required Deliverables

1. one visible specialist artifact-provenance / bundle-integrity surface in the Dev workspace
2. one visible tie between provenance entries and specialist/directive/packet context
3. one honest verified/partial/invalid bundle summary
4. one honest provenance or integrity-basis summary
5. one Prime Mermaid source artifact for specialist artifact provenance visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible specialist artifact-provenance surface
Objective: make post-artifact trust first-class.
Scope: show one visible surface of specialist run outputs carrying bundle provenance and integrity state directly in the workspace.
Done when: a reviewer can tell whether a worker’s artifact bundle is trustworthy without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie provenance entries to specialist, directive, and packet context
Objective: stop treating bundle trust as detached theory.
Scope: each entry should reveal which directive, which specialist, and what active packet or bundle provenance is involved.
Done when: a reviewer can tell what each provenance entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest bundle-integrity states
Objective: make specialist artifact-trust visibility operationally truthful.
Scope: support at least one verified bundle state, one partial bundle state, and one invalid bundle state with visible reasoning.
Done when: the workspace does not imply fake integrity certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one specialist-provenance Prime Mermaid artifact
Objective: capture the move from specialist artifact output to visible bundle trust and integrity.
Scope: add one Prime Mermaid artifact for specialist artifact provenance visibility.
Done when: the provenance surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make specialist artifact provenance visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to directive packet to handoff log to specialist acceptance to specialist readiness to specialist execution to specialist evidence to specialist artifact bundle to specialist provenance inspection
- one automated test or lightweight scripted verification for the provenance surface
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
- rewriting the role stack instead of making specialist artifact provenance more visible
