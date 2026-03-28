# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for visible worker detail and diagram-backed Dev context

## Current Round

SAW14 native worker-detail panel and Prime Mermaid diagram access.

The Dev workspace now has explicit, shareable inspection context. The next step is to make the current Solace worker and its governing diagrams visible in the workspace itself so a reviewer can understand who is acting, what role they hold, and what source diagrams define the current Dev flow without leaving Hub.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA expose their current worker identity, role detail, and governing Prime Mermaid diagrams directly inside the workspace`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Add a native worker-detail and diagram-access surface to the Dev workspace while preserving the current integrated role stack, run history, inspection context, and artifact inspection behavior.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdm0-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdd1-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdc2-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdq3-review-2026-03-27.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdx4-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdh5-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdr6-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sdi7-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sda8-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sav9-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sat10-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sap11-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sau12-review-2026-03-28.md`
- `/home/phuc/projects/solace-prime/reviews/solace-browser-sac13-review-2026-03-28.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-to-design-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/design-to-coder-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/coder-to-qa-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/role-stack.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-page-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/inspection-context-panel.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/solace-hub/src/hub-app.js`
- `/home/phuc/projects/solace-browser/solace-hub/src/index.html`

## Rules

- build on the current integrated Dev workspace, live role cards, run history, inspection context panel, and artifact preview surfaces
- the workspace must show the currently focused worker role and enough detail to tell what app is acting and where its current source artifacts live
- Prime Mermaid diagrams should be visible and reachable from inside the workspace, not hidden as repo-only knowledge
- do not invent worker state the runtime does not know about
- if a role or diagram set is missing, show that honestly in the workspace
- keep Prime Mermaid as the source-of-truth for worker-detail and diagram-access flow
- do not expand into cloud sync, billing, `solaceagi`, or unrelated browser platform work

## Hard Rejection Criteria

The round fails if any of these remain true:

- the workspace still lacks a native worker-detail surface
- a reviewer still cannot tell which worker app or role is currently in focus without reading repo files
- Prime Mermaid diagrams are still only discoverable through repo paths instead of the workspace
- the round only adds diagrams or links without making worker identity and diagram context more usable inside Hub

## Required Deliverables

You must produce all of these:

1. one visible worker-detail panel in the Dev workspace
2. one visible role/app identity path for the active or selected worker context
3. one native diagram-access path for relevant Prime Mermaid artifacts
4. one Prime Mermaid source artifact for worker-detail and diagram-access flow
5. one narrow smoke path
6. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Add a visible worker-detail panel
Objective: make the current worker identity explicit in the workspace.
Scope: show worker app id, role, basic live metadata, and relevant source artifact paths or counts in one native panel.
Done when: a reviewer can identify the current Solace worker context without reading repo files.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 2: Tie worker detail to the active Dev context
Objective: stop treating worker detail as disconnected from the current workspace state.
Scope: make the worker-detail surface follow the integrated Dev workspace context or selected role focus honestly.
Done when: a reviewer can tell which role/app is currently being inspected and why.
Evidence required: screenshots, routes exercised, and one short walkthrough.

### Ticket 3: Add native Prime Mermaid diagram access
Objective: make the governing diagrams visible from the product surface.
Scope: surface relevant role-stack, handoff, or page-map diagrams inside the Dev workspace via native links, embeds, or previews.
Done when: a reviewer can open the governing diagrams for the current Dev flow from inside the workspace.
Evidence required: screenshots, artifact paths, and one short walkthrough.

### Ticket 4: Add one worker-detail Prime Mermaid artifact
Objective: capture the move from implicit role knowledge to visible worker context.
Scope: add one Prime Mermaid artifact for worker-detail and diagram-access flow.
Done when: the worker-detail surface is represented as committed source truth.
Evidence required: artifact path and one short note on what it governs.

### Ticket 5: Add one narrow smoke path and one narrow test
Objective: make worker-detail and diagram access reviewable and repeatable.
Scope:
- one documented local smoke path from workspace load to worker-detail inspection to diagram access
- one automated test or lightweight scripted verification for the worker-detail surface
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
- rewriting the role stack instead of making worker identity and diagrams more visible
