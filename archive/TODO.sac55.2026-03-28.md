# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native post-release quarantine and override visibility

## Current Round

`SAC55` native post-release quarantine and override visibility.

The Dev workspace now shows whether failed closure reopened the incident, escalated it, or kept it under observation. The next step is to make severe escalation operationally governable: one visible surface showing whether the system imposed quarantine, required manual override, or allowed constrained continuation.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see trustworthy convention lineages move from proof to trust to signoff to rollout, then see the incident path, remediation path, closure path, escalation path, and whether severe escalation caused honest quarantine or override control`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native post-release quarantine and override panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, convention effect visibility, convention proof visibility, convention trust visibility, convention release visibility, convention rollout visibility, post-release health visibility, post-release incident visibility, post-release closure visibility, post-release escalation visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, memory-reuse, convention-invocation, convention-delivery, convention-activation, convention-effect, convention-proof, convention-trust, convention-release, convention-rollout, post-release health, and post-release incident surfaces
- the workspace must show one direct post-release quarantine or override panel tied to a visible escalated or reopened state
- the surface must show at least one quarantined state, one manual-override-required state, and one constrained-continuation state
- the surface must tie quarantine or override back to visible escalation, closure, remediation, and operational basis honestly
- if quarantine values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: severe escalation must become an explicit control path, not disappear into generic alert noise
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether severe escalation forced quarantine or override
- a reviewer still cannot tell whether the current control state is quarantined, manual-override-required, or constrained-continuation
- quarantine or override state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making severe post-release escalation materially controllable

## Required Deliverables

1. one visible post-release quarantine or override panel in the Dev workspace
2. one visible tie between control state and escalation / closure / remediation context
3. one honest quarantined / manual-override-required / constrained-continuation summary
4. one honest quarantine-basis or override-basis summary
5. one Prime Mermaid source artifact for post-release quarantine and override visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible quarantine and override surface
Objective: make severe escalation outcomes governable.
Scope: show one visible surface of quarantine or override state attached to an escalated or reopened lineage directly in the workspace.
Done when: a reviewer can tell whether the system imposed quarantine or demanded override without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie control state to escalation and remediation context
Objective: stop treating quarantine as detached theory.
Scope: each quarantine or override entry should reveal which escalation lineage, which failed closure path, and what operational basis is involved.
Done when: a reviewer can tell what each control verdict refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest quarantine and override states
Objective: make post-release control operationally truthful.
Scope: support at least one quarantined state, one manual-override-required state, and one constrained-continuation state with visible reasoning.
Done when: the workspace does not imply fake control certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one post-release quarantine Prime Mermaid artifact
Objective: capture the move from escalation to explicit control.
Scope: add one Prime Mermaid artifact for post-release quarantine and override visibility.
Done when: the control surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make post-release quarantine or override visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection to proof inspection to trust-decision inspection to release-action inspection to rollout inspection to post-release inspection to remediation inspection to remediation-verification inspection to escalation inspection to control inspection
- one automated test or lightweight scripted verification for the quarantine and override surface
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
- rewriting the role stack instead of making severe escalation controllable
