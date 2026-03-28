# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native convention-release action and manager signoff visibility

## Current Round

`SAC49` native convention-release action and manager signoff visibility.

The Dev workspace now shows whether a convention lineage is trusted or blocked for continued use. The next step is to make that decision operational: one visible surface showing whether a trusted lineage has an actual release or promotion action pending, approved, or denied by the Dev Manager, and what signoff basis produced that action.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives become trustworthy outputs, see those outputs enter department memory, see that memory become callable and operational, and see whether the resulting convention lineage is actually approved, denied, or waiting on release action`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native convention-release action and manager signoff panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, convention effect visibility, convention proof visibility, convention trust visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, memory-reuse, convention-invocation, convention-delivery, convention-activation, convention-effect, convention-proof, and convention-trust surfaces
- the workspace must show one direct convention-release or manager-signoff panel tied to a visible trust decision
- the surface must show at least one approved state, one pending-signoff state, and one denied state
- the surface must tie action state back to visible trust context, proof context, lineage context, and manager signoff basis honestly
- if action values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: trust decisions must become explicit manager actions, not stop at status display
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether a trusted convention lineage is actually approved, pending, or denied for release or promotion
- a reviewer still cannot tell whether the current action verdict is approved, pending, or denied
- action state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making manager signoff materially inspectable

## Required Deliverables

1. one visible convention-release or manager-signoff panel in the Dev workspace
2. one visible tie between action state and trust / proof / lineage / signoff context
3. one honest approved / pending / denied summary
4. one honest signoff-basis or release-action basis summary
5. one Prime Mermaid source artifact for convention-release visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible convention-release surface
Objective: make trust decisions actionable.
Scope: show one visible surface of manager release or promotion action attached to a trusted or blocked convention lineage directly in the workspace.
Done when: a reviewer can tell what action is pending or approved for the current convention lineage without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie action state to trust and signoff context
Objective: stop treating release decisions as detached theory.
Scope: each action entry should reveal which trust verdict, which lineage, and what signoff basis is involved.
Done when: a reviewer can tell what each action verdict refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest action states
Objective: make release action operationally truthful.
Scope: support at least one approved state, one pending state, and one denied state with visible reasoning.
Done when: the workspace does not imply fake action certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one convention-release Prime Mermaid artifact
Objective: capture the move from trust verdict to explicit manager action.
Scope: add one Prime Mermaid artifact for convention-release visibility.
Done when: the release-action surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make convention-release action visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection to proof inspection to trust-decision inspection to release-action inspection
- one automated test or lightweight scripted verification for the release-action surface
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
- rewriting the role stack instead of making manager signoff inspectable
