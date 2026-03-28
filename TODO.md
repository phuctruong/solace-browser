# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native post-release recovery authorization and re-entry visibility

## Current Round

`SAC56` native post-release recovery authorization and re-entry visibility.

The Dev workspace now shows whether severe escalation imposed quarantine, required override, or allowed constrained continuation. The next step is to make recovery operationally governable: one visible surface showing whether quarantine cleared, recovery was authorized, or re-entry stayed blocked.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see trustworthy convention lineages move from proof to trust to signoff to rollout, then see the incident path, remediation path, closure path, escalation path, control path, and whether quarantined systems honestly cleared for recovery or remained blocked`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native post-release recovery authorization and re-entry panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, convention effect visibility, convention proof visibility, convention trust visibility, convention release visibility, convention rollout visibility, post-release health visibility, post-release incident visibility, post-release closure visibility, post-release escalation visibility, post-release quarantine visibility, run history, inspection context, and artifact inspection behavior.`
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
- the workspace must show one direct post-release recovery authorization or re-entry panel tied to a visible quarantine or override state
- the surface must show at least one recovery-authorized state, one re-entry-blocked state, and one staged-recovery state
- the surface must tie recovery or re-entry back to visible quarantine, escalation, closure, and operational basis honestly
- if recovery values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: severe control must eventually produce an explicit recovery or block decision, not remain a dead-end state
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether quarantine cleared for recovery or re-entry
- a reviewer still cannot tell whether the current recovery state is recovery-authorized, re-entry-blocked, or staged-recovery
- recovery or re-entry state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making post-release recovery materially governable

## Required Deliverables

1. one visible post-release recovery authorization or re-entry panel in the Dev workspace
2. one visible tie between recovery state and quarantine / escalation / closure context
3. one honest recovery-authorized / re-entry-blocked / staged-recovery summary
4. one honest recovery-basis or re-entry-basis summary
5. one Prime Mermaid source artifact for post-release recovery authorization visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible recovery authorization surface
Objective: make post-quarantine outcomes governable.
Scope: show one visible surface of recovery or re-entry state attached to a quarantined or override-bound lineage directly in the workspace.
Done when: a reviewer can tell whether the system cleared recovery without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie recovery state to control and escalation context
Objective: stop treating re-entry as detached theory.
Scope: each recovery or re-entry entry should reveal which control lineage, which escalation path, and what operational basis is involved.
Done when: a reviewer can tell what each recovery verdict refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest recovery authorization states
Objective: make post-release recovery operationally truthful.
Scope: support at least one recovery-authorized state, one re-entry-blocked state, and one staged-recovery state with visible reasoning.
Done when: the workspace does not imply fake recovery certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one post-release recovery authorization Prime Mermaid artifact
Objective: capture the move from quarantine to explicit re-entry control.
Scope: add one Prime Mermaid artifact for post-release recovery authorization visibility.
Done when: the recovery surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make post-release recovery or re-entry visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection to proof inspection to trust-decision inspection to release-action inspection to rollout inspection to post-release inspection to remediation inspection to remediation-verification inspection to escalation inspection to control inspection to recovery inspection
- one automated test or lightweight scripted verification for the recovery authorization surface
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
- rewriting the role stack instead of making post-release recovery governable
