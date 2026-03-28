# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native efficiency metrics and replay-rate visibility

## Current Round

SAE24 native efficiency metrics and replay-rate dashboard.

The Dev workspace now shows worker identity, diagrams, inbox/outbox structure, assignment packet, execution mode/convention state, human gate state, proof state, execution graph state, convention-store state, drift/adaptive replay state, and hybrid routing state. The next step is to surface efficiency: whether the current system is replay-heavy or discover-heavy, what it costs, what it saves, and whether route selection is actually improving the system.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose measurable replay, reuse, route, cost, and latency behavior directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native efficiency metrics and replay-rate surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, run history, inspection context, and artifact inspection behavior.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI11 — Discover vs Replay Modes.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI13 — Hybrid Routing: Local Models + External APIs.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI19 — Measuring Solace System Efficiency.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, artifact, and inspection surfaces
- the workspace must show efficiency state for the active worker/run directly
- the workspace must show at least replay rate, route class, and one cost or latency summary
- if efficiency values are role-derived or mocked rather than runtime-native, show that honestly
- the panel must distinguish replay/reuse from discover/external work
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still cannot show whether the current worker/run is replay-heavy or discover-heavy
- a reviewer still cannot tell whether routing is saving or spending system cost
- efficiency state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making replay/cost/latency more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible efficiency surface in the Dev workspace
2. one visible tie between efficiency state and the active worker/run context
3. one honest replay-rate or replay-vs-discover summary
4. one honest route-cost or latency summary
5. one Prime Mermaid source artifact for efficiency visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible efficiency surface
Objective: make replay/cost/latency first-class.
Scope: show efficiency state for the active worker/run directly in the workspace.
Done when: a reviewer can tell the current worker/run efficiency state without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie efficiency state to active worker/run context
Objective: stop treating metrics as detached theory.
Scope: the efficiency surface should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which worker/run the efficiency state belongs to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest replay and route economics
Objective: make efficiency visibility operationally truthful.
Scope: support at least visible replay/reuse percentage or replay-vs-discover state, plus one route-cost or latency indicator and one honest unknown/fallback state.
Done when: the workspace does not imply fake efficiency certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one efficiency Prime Mermaid artifact
Objective: capture the move from implicit economics to visible workspace state.
Scope: add one Prime Mermaid artifact for efficiency visibility.
Done when: the efficiency surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make efficiency visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to efficiency inspection
- one automated test or lightweight scripted verification for the efficiency surface
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
- rewriting the role stack instead of making efficiency more visible
