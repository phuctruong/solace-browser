# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native post-release health and rollback visibility

## Current Round

`SAC51` native post-release health and rollback visibility.

The Dev workspace now shows whether a convention lineage actually rolled out. The next step is to make rollout accountable after deployment: one visible surface showing whether the rollout remains healthy, degraded, or rolled back, and what post-release evidence or rollback basis produced that state.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see trustworthy convention lineages move from proof to trust to signoff to rollout, and can then see whether the rollout stayed healthy, degraded, or rolled back`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native post-release health and rollback panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, convention effect visibility, convention proof visibility, convention trust visibility, convention release visibility, convention rollout visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, memory-reuse, convention-invocation, convention-delivery, convention-activation, convention-effect, convention-proof, convention-trust, convention-release, and convention-rollout surfaces
- the workspace must show one direct post-release health or rollback panel tied to a visible rollout state
- the surface must show at least one healthy state, one degraded state, and one rolled-back state
- the surface must tie post-release state back to visible rollout context, lineage context, and health or rollback basis honestly
- if health values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: rollout must be visibly accountable after execution, not stop at deployment status
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether a rolled-out convention lineage stayed healthy or was rolled back
- a reviewer still cannot tell whether the current post-release verdict is healthy, degraded, or rolled back
- post-release state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making rollout accountability materially inspectable

## Required Deliverables

1. one visible post-release health or rollback panel in the Dev workspace
2. one visible tie between post-release state and rollout / lineage / health context
3. one honest healthy / degraded / rolled-back summary
4. one honest health-basis or rollback-basis summary
5. one Prime Mermaid source artifact for post-release visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible post-release health surface
Objective: make rollout accountability visible.
Scope: show one visible surface of health or rollback state attached to a rolled-out convention lineage directly in the workspace.
Done when: a reviewer can tell whether the current rollout remained healthy without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie post-release state to rollout and lineage context
Objective: stop treating rollback or health as detached theory.
Scope: each post-release entry should reveal which rollout lineage and what health or rollback basis is involved.
Done when: a reviewer can tell what each post-release verdict refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest post-release states
Objective: make rollout accountability operationally truthful.
Scope: support at least one healthy state, one degraded state, and one rolled-back state with visible reasoning.
Done when: the workspace does not imply fake rollout health certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one post-release Prime Mermaid artifact
Objective: capture the move from rollout state to post-release accountability.
Scope: add one Prime Mermaid artifact for post-release visibility.
Done when: the post-release surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make post-release state visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection to proof inspection to trust-decision inspection to release-action inspection to rollout inspection to post-release inspection
- one automated test or lightweight scripted verification for the post-release surface
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
- rewriting the role stack instead of making rollout accountability inspectable
