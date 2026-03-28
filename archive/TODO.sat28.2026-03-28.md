# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native promotion audit trail and approval log visibility

## Current Round

SAT28 native promotion audit trail and approval log visibility.

The Dev workspace now shows one manager-facing promotion decision packet. The next step is to make that decision durable and reviewable over time: one visible audit trail showing which promotion decisions were approved, blocked, or left pending, why they changed, and how the Dev Manager can inspect approval history instead of only the current packet.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can review durable approval history for department memory promotion`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native promotion audit trail and approval log visibility surface to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, per-worker distillation, department memory queue, and promotion decision packet surfaces
- the workspace must show one durable promotion audit trail or approval log directly
- the audit trail must show at least approved, pending, and blocked review entries over time
- the audit trail must show why an entry changed state
- if audit values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: manager review becomes durable department memory governance
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the manager still cannot inspect durable approval history for promotion decisions
- a reviewer still cannot tell why a decision entry is approved, pending, or blocked
- approval history is presented as fake certainty instead of visible grounded context
- the round only adds labels without making approval history more operationally legible

## Required Deliverables

You must produce all of these:

1. one visible promotion audit trail or approval log in the Dev workspace
2. one visible tie between log entries and role/run/candidate context
3. one honest approved/pending/blocked audit summary
4. one honest state-change or approval-basis summary
5. one Prime Mermaid source artifact for approval-log visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible promotion audit trail
Objective: make approval history first-class.
Scope: show a durable promotion audit trail directly in the workspace.
Done when: a reviewer can inspect recent promotion decisions without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie log entries to role/run/candidate context
Objective: stop treating approval history as detached theory.
Scope: each entry should reveal which specialist produced the candidate and which run or pattern it came from.
Done when: a reviewer can tell what each decision entry refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest audit states
Objective: make approval history operationally truthful.
Scope: support at least one approved entry, one pending entry, and one blocked or rejected entry with visible reasoning.
Done when: the workspace does not imply fake approval certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one approval-log Prime Mermaid artifact
Objective: capture the move from one decision packet to durable department approval history.
Scope: add one Prime Mermaid artifact for promotion audit visibility.
Done when: the audit trail is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make approval history visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to promotion packet to audit-trail inspection
- one automated test or lightweight scripted verification for the audit surface
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
- rewriting the role stack instead of making approval history more visible
