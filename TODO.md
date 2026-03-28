# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for native convention-effect and constrained-output visibility

## Current Round

`SAC46` native convention-effect and constrained-output visibility.

The Dev workspace now shows whether a delivered convention activated the target runtime. The next step is to make that activation materially inspectable: one visible surface showing whether the active convention is changing the target run output, what constrained artifact or log it produced, and whether the effect is visible, partial, or absent.

## Worker Inbox

- `northstar`: `Solace Browser is the visible operating environment for the Solace Dev department, where the Dev Manager can see directives become trustworthy outputs, see those outputs enter department memory, see that memory become callable, see exactly how it is invoked into the next packet, see whether the target received it, see whether the target execution activated it, and see what concrete constrained output that activation produced`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native convention-effect and constrained-output panel to the Dev workspace while preserving the current role stack, worker detail, diagram access, inbox/outbox visibility, assignment packet, execution mode/convention visibility, human gate visibility, proof visibility, execution graph visibility, convention-store visibility, drift/adaptive replay visibility, hybrid routing visibility, efficiency visibility, per-worker distillation visibility, department memory queue visibility, promotion decision packet visibility, promotion audit trail visibility, governance summary visibility, manager action queue visibility, manager directive packet visibility, delegation handoff visibility, specialist acceptance visibility, specialist readiness visibility, specialist execution visibility, specialist evidence visibility, specialist artifact visibility, specialist provenance visibility, specialist promotion visibility, specialist memory-admission visibility, department-memory entry visibility, department-memory reuse visibility, convention invocation visibility, convention delivery visibility, convention activation visibility, run history, inspection context, and artifact inspection behavior.`
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

- build on the current integrated Dev workspace and preserve all existing role, routing, drift, convention, proof, graph, efficiency, artifact, inspection, promotion, admission, memory-entry, memory-reuse, convention-invocation, convention-delivery, and convention-activation surfaces
- the workspace must show one direct convention-effect or constrained-output panel tied to a visible active convention
- the surface must show at least one visible-effect state, one partial-effect state, and one absent-effect state
- the surface must tie effect state back to visible activation context, target runtime context, and produced artifact or log context honestly
- if effect values are mocked or role-derived rather than runtime-native, show that honestly
- the panel must fit the Solace company model: active department memory must visibly change the next managed output rather than stop at activation
- keep the surface compatible with the current Prime Mermaid-first source model
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

- the manager still cannot see whether an active convention actually changed the target output
- a reviewer still cannot tell whether the current effect is visible, partial, or absent
- effect state is presented as fake certainty instead of visible grounded context
- the round only adds labels without making convention effects materially inspectable

## Required Deliverables

1. one visible convention-effect or constrained-output panel in the Dev workspace
2. one visible tie between effect state and activation / runtime / artifact context
3. one honest visible / partial / absent summary
4. one honest effect-basis or constrained-output basis summary
5. one Prime Mermaid source artifact for convention-effect visibility
6. one narrow smoke path
7. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible convention-effect surface
Objective: make active department memory visibly change output.
Scope: show one visible surface of an active convention producing a constrained artifact, log, or run output directly in the workspace.
Done when: a reviewer can tell what changed because of the active convention without leaving the workspace.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie effect state to activation and artifact context
Objective: stop treating constrained output as detached theory.
Scope: each effect entry should reveal which active convention, which target runtime, and what produced artifact or log basis is involved.
Done when: a reviewer can tell what each constrained output refers to and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Represent honest effect states
Objective: make convention effect operationally truthful.
Scope: support at least one visible-effect state, one partial-effect state, and one absent-effect state with visible reasoning.
Done when: the workspace does not imply fake effect certainty.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 4: Add one convention-effect Prime Mermaid artifact
Objective: capture the move from convention activation to constrained output.
Scope: add one Prime Mermaid artifact for convention-effect visibility.
Done when: the effect surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make convention effects visible, reviewable, and repeatable.
Scope:
- one documented local smoke path from workspace load to memory-entry inspection to callable-convention inspection to invocation inspection to delivery inspection to activation inspection to constrained-output inspection
- one automated test or lightweight scripted verification for the effect surface
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
- rewriting the role stack instead of making convention effects inspectable
