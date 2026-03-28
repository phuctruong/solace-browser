# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native department governance summary and approval pressure visibility

## Current Round

SAG29 native department governance summary and approval pressure visibility.

The Dev workspace now shows a promotion audit trail and approval log. The next step is to help the Solace Dev Manager operate the department at a glance: one visible governance summary showing how many promotion decisions are approved, pending, or blocked, where approval pressure is accumulating, and which specialist lanes are creating the most governance load.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see both individual decisions and aggregate governance pressure across the department`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native department governance summary and approval pressure surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, promotion decision packet, and promotion audit trail surfaces
- the workspace must show one aggregate governance summary directly
- the summary must show at least approved, pending, and blocked counts across the department
- the summary must show one visible notion of approval pressure or governance load by role or lane
- if summary values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: Dev Manager sees department-level governance state, not just isolated events
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the manager still cannot see aggregate governance state across the department
- a reviewer still cannot tell where approval pressure is accumulating
- governance summary is presented as fake certainty instead of visible grounded context
- the round only adds labels without making department governance more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible governance summary in the Dev workspace
2. one visible tie between summary metrics and specialist or lane context
3. one honest approved/pending/blocked aggregate summary
4. one honest approval-pressure or governance-load summary
5. one Prime Mermaid source artifact for governance-summary visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible governance summary
Objective: make department-level governance first-class.
Scope: show one aggregate summary of promotion governance directly in the workspace.
Done when: a reviewer can tell the department’s approval state without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie metrics to specialist context
Objective: stop treating governance summary as detached theory.
Scope: the summary should reveal which specialist lanes are contributing to approval pressure or completed promotion flow.
Done when: a reviewer can tell where the governance load is coming from and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest governance states
Objective: make governance visibility operationally truthful.
Scope: support at least approved, pending, and blocked aggregate state plus one honest pressure or backlog indicator.
Done when: the workspace does not imply fake governance certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one governance-summary Prime Mermaid artifact
Objective: capture the move from audit entries to manager-level governance state.
Scope: add one Prime Mermaid artifact for governance-summary visibility.
Done when: the summary is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make governance summary visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to audit trail to governance summary inspection
- one automated test or lightweight scripted verification for the summary surface
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
- rewriting the role stack instead of making governance summary more visible
