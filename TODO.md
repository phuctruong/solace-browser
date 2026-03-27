# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for the Solace Design role after the manager-first substrate

## Current Round

SDD1 design-first role setup.

The manager-first round is good enough to build on. The next step is to make `solace-design` real so the manager can hand work to a design worker with explicit page/state truth for `solace-browser` itself.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA operate on the same durable objects`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `design`
- `task_statement`: `Build the first Solace Design role app and workspace flow for solace-browser itself, using Prime Mermaid as the source of truth for pages, states, and design handoff artifacts.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-cli/specs/hub/prime-wiki/solace-hub.prime-wiki.md`
- `/home/phuc/projects/solace-cli/specs/browser/prime-wiki/solace-browser.prime-wiki.md`
- `/home/phuc/projects/solace-cli/specs/hub/diagrams/hub-dashboard-pages.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-source-map.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/dev-role-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/project-mappings/solace-browser.prime-mermaid.md`

## Rules

- build on the existing manager-first workspace, not beside it
- do not start coder or QA implementation in this round
- `solace-design` must be a real worker app with inbox/outbox structure
- Prime Mermaid is the source of truth for page maps, state maps, component-state maps, and handoff artifacts
- avoid new standalone JSON/YAML system definitions when Prime Mermaid can express the contract
- if YAML/JSON compatibility files are still required, keep the Prime Mermaid file as the source contract
- design must operate on `solace-browser` itself first
- make the manager-to-design handoff visible in Hub or Back Office, not hidden in prose only
- keep the round local-first, inspectable, and evidence-first

## Hard Rejection Criteria

The round fails if any of these remain true:

- there is no `solace-design` worker app with a real inbox/outbox contract
- there is no committed Prime Mermaid page/state truth for the `solace-browser` manager workspace
- there is no explicit manager-to-design handoff artifact or object path
- design artifacts still live mainly in prose with no committed diagram set
- the Hub surface still cannot point to design-state artifacts for `solace-browser`
- the round expands into coder or QA implementation instead of perfecting the design role

## Required Deliverables

You must produce all of these:

1. one `solace-design` worker app under `data/apps/`
2. one Prime Mermaid design source set for `solace-browser`
3. one explicit manager-to-design handoff contract
4. one initial design workspace shell or visible design view in Hub
5. one durable object path for design artifacts or design state
6. one storage note showing where design artifacts now live
7. one narrow smoke path
8. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Create the `solace-design` worker app
Objective: make the design role a real worker app rather than an idea.
Scope: add `data/apps/solace-design/` with inbox, outbox, diagrams, Prime Mermaid source contract, and compatibility files only where still required.
Done when: the app satisfies the current inbox/outbox contract and clearly declares the design role.
Evidence required: changed files, app paths, and one short summary of the inbox/outbox layout.

### Ticket 2: Add the first design diagram set
Objective: create design truth for `solace-browser` itself.
Scope: add at least:
- one page map
- one UI state map
- one component-state or panel-state map
- one design handoff flow
Done when: the manager can point to committed Prime Mermaid design artifacts as the source of truth for the browser workspace.
Evidence required: artifact paths and one short note on what each diagram governs.

### Ticket 3: Add the manager-to-design handoff contract
Objective: make design assignment explicit and durable.
Scope: define what the manager passes to design for a `solace-browser` task: request, project map, page scope, state scope, constraints, and expected artifacts.
Done when: there is one committed handoff artifact or object contract that a reviewer can inspect.
Evidence required: artifact path and one sample payload or record.

### Ticket 4: Add the first design workspace view
Objective: expose design as a visible role in the Dev workspace.
Scope: add one initial design-facing view in Hub or the Dev workspace that points to page/state artifacts for `solace-browser`.
Done when: a human can open the Hub and inspect current design truth for the active project.
Evidence required: changed files, screenshots, and one short walkthrough.

### Ticket 5: Add durable design-state storage
Objective: stop design truth from living only in files or chat.
Scope: add the minimum Back Office object path or schema needed for design artifacts, design states, or handoff records.
Done when: the design role can point to durable shared state rather than only repo-local diagrams.
Evidence required: changed files, API paths exercised, and one sample record or payload.

### Ticket 6: Add one storage note
Objective: keep the next roles from re-deciding where design truth lives.
Scope: update or add one artifact that explains where:
- design source diagrams
- design handoff artifacts
- design worker app state
- design evidence
live now.
Done when: coder and QA can inherit the storage model directly.
Evidence required: artifact path and one short summary.

### Ticket 7: Add one narrow smoke path and one narrow test
Objective: make the round reviewable and repeatable.
Scope:
- one documented local smoke path from startup to manager workspace to design artifact inspection
- one automated test or lightweight scripted verification for the design role flow
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/backoffice.rs`
- `solace-runtime/src/backoffice/schema.rs`
- `solace-runtime/src/routes/apps.rs`
- `specs/solace-dev/`
- `data/apps/solace-design/`
- `tests/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact APIs exercised
- design artifact paths
- handoff artifact path
- sample records or payloads
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- coder implementation
- QA implementation
- broad cloud sync or billing work
- unrelated Chromium platform changes
- redesigning the manager round instead of building on it
