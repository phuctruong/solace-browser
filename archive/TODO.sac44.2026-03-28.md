# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native convention-delivery receipt and packet-binding visibility

## Current Round

`SAC44` native convention-delivery receipt and packet-binding visibility.

The Dev workspace now shows whether a callable convention was routed into the next directive or packet. The next step is to make that routing verifiable: one visible surface showing whether the target worker or packet actually received the invoked convention, how it was bound, and whether delivery is acknowledged, pending, or rejected.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives become trustworthy outputs, see those outputs enter department memory, see that memory become callable, see exactly how it is invoked into the next packet, and see whether the target packet or worker actually received that convention`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native convention-delivery receipt and packet-binding panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, run history, inspection context, and artifact inspection behavior.`
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
- `/home/phuc/projects/solace-prime/canon/hub/SI10 — The Solace Execution Graph.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI14 — Convention Store as Persistent Intelligence.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI17 — Human-in-the-Loop as a First-Class System Component.md`
- `/home/phuc/projects/solace-prime/canon/hub/SI21 — The Solace Intelligence System.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, memory-reuse, and convention-invocation surfaces
- the workspace must show one direct convention-delivery or packet-binding panel tied to a visible invoked convention
- the surface must show at least one acknowledged state, one pending-delivery state, and one rejected or failed-binding state
- the surface must tie delivery state back to visible convention-invocation context, target worker or packet context, and directive context honestly
- if delivery values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: routed department memory must visibly arrive at the next managed execution target rather than stop at invocation
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether an invoked convention was actually received by the next packet or worker
- a reviewer still cannot tell whether the current convention delivery is acknowledged, pending, or rejected
- delivery state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making convention delivery materially reviewable

## Required Deliverables

1. one visible convention-delivery or packet-binding panel in the Dev workspace
2. one visible tie between delivery state and invocation / packet / directive context
3. one honest acknowledged / pending / rejected summary
4. one honest delivery-basis or packet-binding basis summary
5. one Prime Mermaid source artifact for convention-delivery visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible convention-delivery surface
Objective: make invoked department memory verifiably received.
Scope: show one visible surface of an invoked convention arriving at a next directive, next packet, or next specialist target directly in the workspace.
Done when: a reviewer can tell whether the current invoked convention actually reached its target without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie delivery state to invocation and packet context
Objective: stop treating delivery as detached theory.
Scope: each delivery entry should reveal which invoked convention, which target worker or packet, and what directive basis is involved.
Done when: a reviewer can tell what each delivery refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest delivery states
Objective: make convention delivery operationally truthful.
Scope: support at least one acknowledged state, one pending state, and one rejected state with visible reasoning.
Done when: the workspace does not imply fake delivery certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one convention-delivery Prime Mermaid artifact
Objective: capture the move from convention invocation to target packet receipt.
Scope: add one Prime Mermaid artifact for convention-delivery visibility.
Done when: the delivery surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make convention delivery visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection
- one automated test or lightweight scripted verification for the delivery surface
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
- rewriting the role stack instead of making convention delivery reviewable
