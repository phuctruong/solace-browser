# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native convention distillation and promotion visibility

## Current Round

SAX25 native convention distillation visibility and promotion flow.

The Dev workspace now shows worker identity, diagrams, inbox/outbox structure, assignment packet, execution mode/convention state, human gate state, proof state, execution graph state, convention-store state, drift/adaptive replay state, hybrid routing state, and efficiency metrics. The next step is to show how Solace Dev turns repeated work into promoted department memory: what convention is emerging, what evidence supports it, and whether the manager can safely promote it into reusable operational intelligence.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where Solace Dev Manager can see specialist output become department-level convention memory and promotion candidates`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native convention distillation and promotion visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, and inspection surfaces
- the workspace must show convention distillation state for the active worker/run directly
- the workspace must show at least one promotion candidate, one promotion basis, and one honest promoted/not-promoted state
- if distillation values are role-derived or mocked rather than runtime-native, show that honestly
- the panel must fit the Solace company model: manager sees specialist output become department memory
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still cannot show whether repeated worker output is becoming a convention candidate
- a reviewer still cannot tell why a convention is promoted, blocked, or pending
- convention promotion is presented as fake certainty instead of visible grounded context
- the round only adds labels without making distillation and promotion more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible convention distillation surface in the Dev workspace
2. one visible tie between distillation state and the active worker/run context
3. one honest promotion candidate or promotion status summary
4. one honest promotion basis or evidence basis summary
5. one Prime Mermaid source artifact for convention distillation visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible convention distillation surface
Objective: make promotion from repeated work first-class.
Scope: show convention candidate and promotion state for the active worker/run directly in the workspace.
Done when: a reviewer can tell whether the current worker/run is generating reusable department memory.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie distillation state to active worker/run context
Objective: stop treating convention promotion as detached theory.
Scope: the distillation surface should follow the active worker detail or selected run context honestly.
Done when: a reviewer can tell which worker/run the promotion state belongs to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest promotion states
Objective: make distillation visibility operationally truthful.
Scope: support at least one visible candidate/pending state, one promoted or replayable state, and one blocked/unknown/fallback state.
Done when: the workspace does not imply fake convention certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one convention distillation Prime Mermaid artifact
Objective: capture the move from repeated role output to reusable department memory.
Scope: add one Prime Mermaid artifact for convention distillation visibility.
Done when: the distillation surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make convention distillation visibility reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker detail to convention promotion inspection
- one automated test or lightweight scripted verification for the distillation surface
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
- rewriting the role stack instead of making convention promotion more visible
