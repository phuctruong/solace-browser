# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native post-release sustained-service verification visibility

## Current Round

`SAC58` native post-release sustained-service verification visibility.

The Dev workspace now shows whether authorized recovery actually returned the system to service, remained provisional, or failed re-entry verification. The next step is to make restored service trustworthy over time: one visible surface showing whether returned service stayed stable, entered regression watch, or relapsed after re-entry.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see trustworthy convention lineages move from proof to trust to signoff to rollout, then see the incident path, remediation path, closure path, escalation path, control path, recovery path, return-to-service path, and whether restored systems honestly stayed stable or relapsed after re-entry`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native post-release sustained-service verification panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, convention effect visibility, convention proof visibility, convention trust visibility, convention release visibility, convention rollout visibility, post-release health visibility, post-release incident visibility, post-release closure visibility, post-release escalation visibility, post-release quarantine visibility, post-release recovery visibility, post-release return visibility, run history, inspection context, and artifact inspection behavior.`
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
- the workspace must show one direct post-release sustained-service verification panel tied to a visible return-to-service or provisional-service state
- the surface must show at least one stable-service state, one regression-watch state, and one relapse-detected state
- the surface must tie sustained-service verification back to visible return-to-service, recovery, and operational basis honestly
- if sustained-service values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: restored service must eventually produce an explicit stability decision, not stop at re-entry authorization
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether restored service stayed stable after re-entry
- a reviewer still cannot tell whether the current sustained-service state is stable-service, regression-watch, or relapse-detected
- sustained-service state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making post-release service stability materially governable

## Required Deliverables

1. one visible post-release sustained-service verification panel in the Dev workspace
2. one visible tie between stability state and return-to-service / recovery context
3. one honest stable-service / regression-watch / relapse-detected summary
4. one honest sustained-service basis summary
5. one Prime Mermaid source artifact for post-release sustained-service verification visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible sustained-service surface
Objective: make post-reentry outcomes governable.
Scope: show one visible surface of stability verification state attached to a returned or provisional service lineage directly in the workspace.
Done when: a reviewer can tell whether the system truly stayed healthy after return without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie stability state to return and recovery context
Objective: stop treating sustained service as detached theory.
Scope: each stability entry should reveal which return lineage, which recovery path, and what operational basis is involved.
Done when: a reviewer can tell what each stability verdict refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest sustained-service states
Objective: make post-release service stability operationally truthful.
Scope: support at least one stable-service state, one regression-watch state, and one relapse-detected state with visible reasoning.
Done when: the workspace does not imply fake stability certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one post-release sustained-service Prime Mermaid artifact
Objective: capture the move from return-to-service to measured stability.
Scope: add one Prime Mermaid artifact for post-release sustained-service verification visibility.
Done when: the stability surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make post-release sustained-service visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection to proof inspection to trust-decision inspection to release-action inspection to rollout inspection to post-release inspection to remediation inspection to remediation-verification inspection to escalation inspection to control inspection to recovery inspection to service-verification inspection to stability inspection
- one automated test or lightweight scripted verification for the sustained-service verification surface
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
- rewriting the role stack instead of making post-release service stability governable
