# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for the Solace Coder role after manager and design

## Current Round

SDC2 coder-first role setup.

The manager-first and design-first rounds are good enough to build on. The next step is to make `solace-coder` real so the manager can route implementation work that is bounded by the project map and the design artifacts already committed for `solace-browser`.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA operate on the same durable objects`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `coder`
- `task_statement`: `Build the first Solace Coder role app and workspace flow for solace-browser itself, using the existing manager and design artifacts as the bounded implementation input.`
- `scope_change_policy`: `FAIL_AND_NEW_TASK`

## Read This First

Before coding, read and align to:

- `/home/phuc/projects/solace-prime/NORTHSTAR.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-workspace.md`
- `/home/phuc/projects/solace-prime/specs/solace-dev-role-architecture.md`
- `/home/phuc/projects/solace-prime/specs/prime-mermaid-substrate.md`
- `/home/phuc/projects/solace-prime/specs/solace-worker-inbox-contract.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-source-map.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/storage-model.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/manager-to-design-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/dev-role-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-page-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-ui-state-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-component-state-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-dev-manager/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-design/manifest.prime-mermaid.md`

## Rules

- build on the existing manager and design substrates, not beside them
- do not start QA implementation in this round
- `solace-coder` must be a real worker app with inbox/outbox structure
- coder inputs must be bounded by manager assignment plus design artifacts
- Prime Mermaid is the source of truth for coder workflow contracts, implementation handoff diagrams, and code-run lifecycle diagrams
- avoid new standalone JSON/YAML system definitions when Prime Mermaid can express the contract
- if YAML/JSON compatibility files are still required, keep the Prime Mermaid file as the source contract
- make the manager/design-to-coder handoff visible in Hub or Back Office, not hidden in prose only
- make code artifacts explicit: changed files, diff summaries, test output, run status, and evidence
- keep the round local-first, inspectable, and evidence-first

## Hard Rejection Criteria

The round fails if any of these remain true:

- there is no `solace-coder` worker app with a real inbox/outbox contract
- there is no explicit handoff contract from manager/design to coder
- there is no durable object path for code runs or implementation artifacts
- the Hub surface cannot point to coder artifacts for `solace-browser`
- coder work is not visibly bounded by the design artifacts from `SDD1`
- the round expands into QA implementation instead of perfecting the coder role

## Required Deliverables

You must produce all of these:

1. one `solace-coder` worker app under `data/apps/`
2. one Prime Mermaid coder workflow and handoff source set
3. one explicit manager/design-to-coder handoff contract
4. one initial coder workspace shell or visible coder view in Hub
5. one durable object path for code runs, code artifacts, or implementation reviews
6. one storage note showing where coder artifacts now live
7. one narrow smoke path
8. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Create the `solace-coder` worker app
Objective: make the coder role a real worker app rather than an idea.
Scope: add `data/apps/solace-coder/` with inbox, outbox, diagrams, Prime Mermaid source contract, and compatibility files only where still required.
Done when: the app satisfies the current inbox/outbox contract and clearly declares the coder role.
Evidence required: changed files, app paths, and one short summary of the inbox/outbox layout.

### Ticket 2: Add the first coder diagram set
Objective: create coder truth for `solace-browser` itself.
Scope: add at least:
- one coder workflow diagram
- one implementation handoff flow
- one code-run lifecycle diagram
- one artifact flow diagram
Done when: the manager can point to committed Prime Mermaid coder artifacts as the source of truth for the implementation role.
Evidence required: artifact paths and one short note on what each diagram governs.

### Ticket 3: Add the manager/design-to-coder handoff contract
Objective: make implementation assignment explicit and durable.
Scope: define what manager and design pass to coder for a `solace-browser` task: request, assignment, page scope, state scope, constraints, expected files or areas, and expected artifacts.
Done when: there is one committed handoff artifact or object contract that a reviewer can inspect.
Evidence required: artifact path and one sample payload or record.

### Ticket 4: Add the first coder workspace view
Objective: expose coder as a visible role in the Dev workspace.
Scope: add one initial coder-facing view in Hub or the Dev workspace that points to runs, artifacts, diff summaries, and implementation inputs for `solace-browser`.
Done when: a human can open the Hub and inspect current coder truth for the active project.
Evidence required: changed files, screenshots, and one short walkthrough.

### Ticket 5: Add durable coder-state storage
Objective: stop implementation truth from living only in git diff or chat.
Scope: add the minimum Back Office object path or schema needed for code runs, implementation artifacts, or coder reviews.
Done when: the coder role can point to durable shared state rather than only repo-local artifacts.
Evidence required: changed files, API paths exercised, and one sample record or payload.

### Ticket 6: Add one storage note
Objective: keep the next role from re-deciding where coder truth lives.
Scope: update or add one artifact that explains where:
- coder source diagrams
- coder handoff artifacts
- coder worker app state
- code-run artifacts and evidence
live now.
Done when: QA can inherit the storage model directly.
Evidence required: artifact path and one short summary.

### Ticket 7: Add one narrow smoke path and one narrow test
Objective: make the round reviewable and repeatable.
Scope:
- one documented local smoke path from startup to manager workspace to coder artifact inspection
- one automated test or lightweight scripted verification for the coder role flow
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/backoffice.rs`
- `solace-runtime/src/backoffice/schema.rs`
- `solace-runtime/src/routes/apps.rs`
- `specs/solace-dev/`
- `data/apps/solace-coder/`
- `tests/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact APIs exercised
- coder artifact paths
- handoff artifact path
- sample records or payloads
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- QA implementation
- broad cloud sync or billing work
- unrelated Chromium platform changes
- redesigning manager or design rounds instead of building on them
