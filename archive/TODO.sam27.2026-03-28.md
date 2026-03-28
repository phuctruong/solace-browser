# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native promotion decision packet and manager approval visibility

## Current Round

SAM27 native promotion decision packet and manager approval visibility.

The Dev workspace now shows a manager-facing department memory queue across specialists. The next step is to let the Solace Dev Manager inspect one promotion candidate as a reviewable decision packet: what candidate is under review, what evidence backs it, which role produced it, and what approval or block basis governs the promotion outcome.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can review, approve, block, and promote specialist output into durable department memory`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native promotion decision packet and manager approval visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI16 — Automatic Convention Distillation.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI18 — Transparency as a Product Feature.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, and department memory queue surfaces
- the workspace must show one manager-facing promotion decision packet directly
- the packet must show at least one candidate, one evidence basis, one approval basis, and one promoted/pending/blocked outcome
- the packet must tie the decision back to role, run, and candidate context honestly
- if packet values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: manager approves or blocks department memory formation from specialist output
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the manager still cannot inspect one promotion candidate as a reviewable packet
- a reviewer still cannot tell why a candidate is approved, pending, or blocked
- approval state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making promotion review more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible promotion decision packet in the Dev workspace
2. one visible tie between the packet and role/run/candidate context
3. one honest approved/pending/blocked decision summary
4. one honest approval basis or evidence basis summary
5. one Prime Mermaid source artifact for promotion decision visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible promotion decision packet
Objective: make manager review of one candidate first-class.
Scope: show one reviewable promotion packet for the active candidate directly in the workspace.
Done when: a reviewer can tell what the Dev Manager is deciding without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie the packet to role/run/candidate context
Objective: stop treating promotion review as detached theory.
Scope: the packet should reveal which specialist produced the candidate and which run or pattern it came from.
Done when: a reviewer can tell which role/run/candidate the decision belongs to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest decision states
Objective: make promotion review operationally truthful.
Scope: support at least one approved or promoted decision, one pending review decision, and one blocked or unknown decision with visible reasoning.
Done when: the workspace does not imply fake decision certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one promotion decision Prime Mermaid artifact
Objective: capture the move from department queue review to one explicit manager decision packet.
Scope: add one Prime Mermaid artifact for promotion decision visibility.
Done when: the packet is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make manager decision review visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to department queue to promotion packet inspection
- one automated test or lightweight scripted verification for the decision packet surface
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
- rewriting the role stack instead of making promotion decision review more visible
