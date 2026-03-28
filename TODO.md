# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native manager action queue and next-decision visibility

## Current Round

SAA30 native manager action queue and next-decision visibility.

The Dev workspace now shows an aggregate governance summary and approval pressure. The next step is to turn that summary into action: one visible manager action queue showing which promotion or governance decisions need attention next, why they are prioritized, and what the next bounded action is for the Solace Dev Manager.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see both governance state and the next bounded actions required to operate the department`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native manager action queue and next-decision surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, promotion audit trail, and governance summary surfaces
- the workspace must show one manager action queue directly
- the action queue must show at least one next decision, one priority reason, and one bounded next action
- the queue must tie actions back to specialist or candidate context honestly
- if action values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: Dev Manager sees not just state, but the next actionable governance steps
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the manager still cannot see the next bounded governance actions required
- a reviewer still cannot tell why one action is prioritized over another
- action queue state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making manager action more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible manager action queue in the Dev workspace
2. one visible tie between action items and specialist/candidate context
3. one honest next-decision or next-action summary
4. one honest priority or urgency basis summary
5. one Prime Mermaid source artifact for manager-action visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible manager action queue
Objective: make next-step governance first-class.
Scope: show one visible queue of the next manager decisions or bounded actions directly in the workspace.
Done when: a reviewer can tell what the Dev Manager should do next without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie action items to specialist/candidate context
Objective: stop treating next actions as detached theory.
Scope: queue items should reveal which role, candidate, or governance lane they belong to.
Done when: a reviewer can tell what each action item refers to and why it exists.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest action and priority states
Objective: make manager action visibility operationally truthful.
Scope: support at least one immediate action, one pending queue item, and one lower-priority or blocked item with visible reasoning.
Done when: the workspace does not imply fake managerial certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one manager-action Prime Mermaid artifact
Objective: capture the move from governance state to actionable manager workflow.
Scope: add one Prime Mermaid artifact for manager-action visibility.
Done when: the action queue is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make manager action visibility visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to governance summary to action-queue inspection
- one automated test or lightweight scripted verification for the action-queue surface
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
- broad cloud sync, billing, or `solaceagi` work
- unrelated Chromium platform changes
- rewriting the role stack instead of making manager action visibility more visible
