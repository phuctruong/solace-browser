# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native convention-release execution and rollout visibility

## Current Round

`SAC50` native convention-release execution and rollout visibility.

The Dev workspace now shows whether a convention lineage has manager signoff for release or promotion. The next step is to make that decision real in the system: one visible surface showing whether the approved lineage was actually executed into rollout, whether the rollout is live, staged, or aborted, and what release-execution basis produced that state.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see trustworthy convention lineages move from proof to trust to explicit signoff and then into real rollout or rejection`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native convention-release execution and rollout panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, convention effect visibility, convention proof visibility, convention trust visibility, convention release visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, memory-reuse, convention-invocation, convention-delivery, convention-activation, convention-effect, convention-proof, convention-trust, and convention-release surfaces
- the workspace must show one direct convention-rollout or release-execution panel tied to a visible release action
- the surface must show at least one live-rollout state, one staged-rollout state, and one aborted-rollout state
- the surface must tie rollout state back to visible release context, trust context, lineage context, and rollout basis honestly
- if rollout values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: manager signoff must become visible rollout or explicit non-rollout, not stop at action approval
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether an approved convention lineage actually rolled out
- a reviewer still cannot tell whether the current rollout verdict is live, staged, or aborted
- rollout state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making release execution materially inspectable

## Required Deliverables

1. one visible convention-rollout or release-execution panel in the Dev workspace
2. one visible tie between rollout state and release / trust / lineage / rollout context
3. one honest live / staged / aborted summary
4. one honest rollout-basis or release-execution basis summary
5. one Prime Mermaid source artifact for convention-rollout visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible convention-rollout surface
Objective: make signoff decisions operational.
Scope: show one visible surface of rollout or release execution attached to an approved or denied convention lineage directly in the workspace.
Done when: a reviewer can tell whether the current convention lineage actually rolled out without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie rollout state to release and lineage context
Objective: stop treating rollout as detached theory.
Scope: each rollout entry should reveal which release verdict, which convention lineage, and what rollout basis is involved.
Done when: a reviewer can tell what each rollout verdict refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest rollout states
Objective: make release execution operationally truthful.
Scope: support at least one live state, one staged state, and one aborted state with visible reasoning.
Done when: the workspace does not imply fake rollout certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one convention-rollout Prime Mermaid artifact
Objective: capture the move from manager signoff to actual rollout state.
Scope: add one Prime Mermaid artifact for convention-rollout visibility.
Done when: the rollout surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make convention-rollout state visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection to proof inspection to trust-decision inspection to release-action inspection to rollout inspection
- one automated test or lightweight scripted verification for the rollout surface
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
- rewriting the role stack instead of making rollout inspectable
