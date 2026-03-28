# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native department memory queue and promotion review visibility

## Current Round

SAQ26 native department memory queue and manager promotion review.

The Dev workspace now shows per-worker convention distillation and promotion state. The next step is to make that useful for the Solace Dev Manager as a department operator: one visible queue where promoted, pending, and blocked convention candidates across specialists can be reviewed as department memory, not just as isolated worker state.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can review and promote specialist output into durable department memory`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native department memory queue and promotion review surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI14 — Convention Store as Persistent Intelligence.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI16 — Automatic Convention Distillation.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, and per-worker distillation surfaces
- the workspace must show one manager-facing department memory queue directly
- the queue must show at least promoted, pending, and blocked candidate states across specialists
- the queue must show why an item is promotable or blocked
- if queue values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: manager sees department memory formation across specialists
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the manager still cannot see convention promotion state across specialists in one queue
- a reviewer still cannot tell why a department-memory candidate is promoted, pending, or blocked
- queue state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making department memory review more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible department memory queue in the Dev workspace
2. one visible tie between queue items and specialist/worker context
3. one honest promoted/pending/blocked queue summary
4. one honest promotion-review basis or evidence basis summary
5. one Prime Mermaid source artifact for department memory queue visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible department memory queue
Objective: make manager review of specialist memory formation first-class.
Scope: show promoted, pending, and blocked convention candidates in one manager-facing queue.
Done when: a reviewer can tell what the Dev Manager would review without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie queue items to specialist context
Objective: stop treating department memory as detached theory.
Scope: queue items should reveal which specialist/worker generated the candidate and which run or pattern it came from.
Done when: a reviewer can tell which role produced the item and why it is in the queue.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest review states
Objective: make queue visibility operationally truthful.
Scope: support at least one promoted item, one pending item, and one blocked or unknown item with visible reasoning.
Done when: the workspace does not imply fake promotion certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one department memory queue Prime Mermaid artifact
Objective: capture the move from per-worker distillation to manager-visible department review.
Scope: add one Prime Mermaid artifact for department memory queue visibility.
Done when: the queue is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make department memory review visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to manager-facing queue inspection
- one automated test or lightweight scripted verification for the queue surface
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
- rewriting the role stack instead of making department memory review more visible
