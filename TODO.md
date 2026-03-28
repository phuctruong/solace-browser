# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native post-release return-to-service verification visibility

## Current Round

`SAC57` native post-release return-to-service verification visibility.

The Dev workspace now shows whether quarantine cleared, recovery was authorized, or re-entry stayed blocked. The next step is to make restored service trustworthy: one visible surface showing whether authorized recovery actually returned the system to service, remained provisional, or failed re-entry verification.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see trustworthy convention lineages move from proof to trust to signoff to rollout, then see the incident path, remediation path, closure path, escalation path, control path, recovery path, and whether restored systems honestly returned to service or failed re-entry verification`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native post-release return-to-service verification panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, convention effect visibility, convention proof visibility, convention trust visibility, convention release visibility, convention rollout visibility, post-release health visibility, post-release incident visibility, post-release closure visibility, post-release escalation visibility, post-release quarantine visibility, post-release recovery visibility, run history, inspection context, and artifact inspection behavior.`
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
- the workspace must show one direct post-release return-to-service verification panel tied to a visible recovery or re-entry state
- the surface must show at least one returned-to-service state, one provisional-service state, and one re-entry-failed state
- the surface must tie service verification back to visible recovery, quarantine, escalation, and operational basis honestly
- if return-to-service values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: cleared recovery must eventually produce an explicit service-verification decision, not stop at permission language
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether authorized recovery actually returned the system to service
- a reviewer still cannot tell whether the current service state is returned-to-service, provisional-service, or re-entry-failed
- return-to-service state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making post-release service restoration materially governable

## Required Deliverables

1. one visible post-release return-to-service verification panel in the Dev workspace
2. one visible tie between service state and recovery / quarantine / escalation context
3. one honest returned-to-service / provisional-service / re-entry-failed summary
4. one honest service-verification basis summary
5. one Prime Mermaid source artifact for post-release return-to-service verification visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible return-to-service surface
Objective: make post-recovery outcomes governable.
Scope: show one visible surface of service verification state attached to an authorized or staged recovery lineage directly in the workspace.
Done when: a reviewer can tell whether the system truly returned to service without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie service state to recovery and control context
Objective: stop treating restored service as detached theory.
Scope: each service entry should reveal which recovery lineage, which control path, and what operational basis is involved.
Done when: a reviewer can tell what each service verdict refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest return-to-service states
Objective: make post-release service restoration operationally truthful.
Scope: support at least one returned-to-service state, one provisional-service state, and one re-entry-failed state with visible reasoning.
Done when: the workspace does not imply fake service certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one post-release return-to-service Prime Mermaid artifact
Objective: capture the move from recovery authorization to actual service restoration.
Scope: add one Prime Mermaid artifact for post-release return-to-service verification visibility.
Done when: the service-verification surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make post-release return-to-service visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection to proof inspection to trust-decision inspection to release-action inspection to rollout inspection to post-release inspection to remediation inspection to remediation-verification inspection to escalation inspection to control inspection to recovery inspection to service-verification inspection
- one automated test or lightweight scripted verification for the return-to-service verification surface
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
- rewriting the role stack instead of making post-release service restoration governable
