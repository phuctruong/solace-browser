# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native specialist promotion-candidate and seal-readiness visibility

## Current Round

SAP39 native specialist promotion-candidate and seal-readiness visibility.

The Dev workspace now shows whether the current artifact bundle is trustworthy from a provenance and integrity perspective. The next step is to make that trust actionable: one visible promotion-candidate surface showing whether the current bundle is ready to be sealed, whether it is still provisional, and whether it is disqualified from promotion.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives enter specialist lanes, confirm inbox receipt, inspect execution evidence, inspect run artifacts, verify trust, and judge whether a specialist output is ready for promotion into department memory`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native specialist promotion-candidate and seal-readiness visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, governance summary, manager action queue, manager directive packet, delegation handoff, specialist acceptance, specialist readiness, specialist execution, specialist evidence, specialist artifact, and specialist provenance surfaces
- the workspace must show one specialist promotion-candidate / seal-readiness surface directly
- the surface must show at least one ready-to-seal state, one provisional state, and one disqualified state
- the surface must tie promotion state back to specialist, directive, active packet, and visible bundle trust context honestly
- if promotion values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: trustworthy artifacts must visibly become promotion candidates rather than stopping at integrity checks
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether the current output is ready for promotion
- a reviewer still cannot tell whether the current bundle is ready-to-seal, provisional, or disqualified
- promotion state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making specialist promotion readiness more operationally legible

## Required Deliverables

1. one visible specialist promotion-candidate / seal-readiness surface in the Dev workspace
2. one visible tie between promotion entries and specialist/directive/packet context
3. one honest ready-to-seal/provisional/disqualified summary
4. one honest promotion-basis or seal-readiness summary
5. one Prime Mermaid source artifact for specialist promotion visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible specialist promotion-candidate surface
Objective: make post-integrity promotion readiness first-class.
Scope: show one visible surface of specialist outputs becoming promotion candidates directly in the workspace.
Done when: a reviewer can tell whether a worker output is ready for sealing without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie promotion entries to specialist, directive, and packet context
Objective: stop treating promotion readiness as detached theory.
Scope: each entry should reveal which directive, which specialist, and what active packet or trusted bundle is involved.
Done when: a reviewer can tell what each promotion entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest promotion states
Objective: make specialist promotion visibility operationally truthful.
Scope: support at least one ready-to-seal state, one provisional state, and one disqualified state with visible reasoning.
Done when: the workspace does not imply fake promotion certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one specialist-promotion Prime Mermaid artifact
Objective: capture the move from specialist artifact provenance to visible promotion readiness.
Scope: add one Prime Mermaid artifact for specialist promotion visibility.
Done when: the promotion surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make specialist promotion visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to directive packet to handoff log to specialist acceptance to specialist readiness to specialist execution to specialist evidence to specialist artifact bundle to specialist provenance to specialist promotion inspection
- one automated test or lightweight scripted verification for the promotion surface
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
- rewriting the role stack instead of making specialist promotion visibility more visible
