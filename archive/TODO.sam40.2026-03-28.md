# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native specialist seal-action request and department-memory admission visibility

## Current Round

SAM40 native specialist seal-action request and department-memory admission visibility.

The Dev workspace now shows whether a specialist output is ready to be sealed and promoted. The next step is to make that promotion operational: one visible seal-action surface showing whether the current promotion candidate has actually requested admission into department memory, whether the request is queued, admitted, or rejected, and what exact memory target it is aiming for.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives enter specialist lanes, inspect trustworthy outputs, judge promotion readiness, and see whether a specialist output is actually entering department memory`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native specialist seal-action request and department-memory admission visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, governance summary, manager action queue, manager directive packet, delegation handoff, specialist acceptance, specialist readiness, specialist execution, specialist evidence, specialist artifact, specialist provenance, and specialist promotion surfaces
- the workspace must show one specialist seal-action / department-memory admission surface directly
- the surface must show at least one queued admission state, one admitted state, and one rejected state
- the surface must tie admission state back to specialist, directive, active packet, and visible promotion-candidate context honestly
- if admission values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: promotion-ready outputs must visibly request or enter department memory rather than stopping at readiness
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether a promotion-ready output is actually requesting admission into department memory
- a reviewer still cannot tell whether the current candidate is queued, admitted, or rejected
- admission state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making specialist memory admission more operationally legible

## Required Deliverables

1. one visible specialist seal-action / department-memory admission surface in the Dev workspace
2. one visible tie between admission entries and specialist/directive/packet context
3. one honest queued/admitted/rejected summary
4. one honest admission-basis or memory-target summary
5. one Prime Mermaid source artifact for specialist memory-admission visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible specialist memory-admission surface
Objective: make post-promotion memory admission first-class.
Scope: show one visible surface of specialist promotion candidates requesting or entering department memory directly in the workspace.
Done when: a reviewer can tell whether a worker output is actually entering memory without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie admission entries to specialist, directive, and packet context
Objective: stop treating memory admission as detached theory.
Scope: each entry should reveal which directive, which specialist, and what active packet or promotion candidate is involved.
Done when: a reviewer can tell what each admission entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest admission states
Objective: make specialist memory-admission visibility operationally truthful.
Scope: support at least one queued admission state, one admitted state, and one rejected state with visible reasoning.
Done when: the workspace does not imply fake admission certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one specialist-memory-admission Prime Mermaid artifact
Objective: capture the move from promotion readiness to visible department-memory admission.
Scope: add one Prime Mermaid artifact for specialist memory-admission visibility.
Done when: the admission surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make specialist memory-admission visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to directive packet to handoff log to specialist acceptance to specialist readiness to specialist execution to specialist evidence to specialist artifact bundle to specialist provenance to specialist promotion to specialist memory-admission inspection
- one automated test or lightweight scripted verification for the admission surface
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
- rewriting the role stack instead of making specialist memory-admission visibility more visible
