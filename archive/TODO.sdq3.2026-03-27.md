# TODO

Repo: `solace-browser`
Role: Solace Hub + Browser workspace for the Solace QA role after manager, design, and coder

## Current Round

SDQ3 QA-first role setup.

The manager, design, and coder rounds are good enough to build on. The next step is to make `solace-qa` real so the manager can route adversarial validation work over the same durable request, design, and code-run objects already created for `solace-browser`.

## Worker Inbox

- `northstar`: `Solace Browser is the visible Hub + Dev workspace where manager, design, coder, and QA operate on the same durable objects`
- `worker_mode`: `external_coding_agent`
- `worker_role`: `qa`
- `task_statement`: `Build the first Solace QA role app and workspace flow for solace-browser itself, using the existing manager, design, and coder artifacts as the bounded validation input.`
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
- `/home/phuc/projects/solace-browser/specs/solace-dev/design-to-coder-handoff.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-page-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-ui-state-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/browser-component-state-map.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/coder-workflow.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/specs/solace-dev/diagrams/coder-run-lifecycle.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-dev-manager/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-design/manifest.prime-mermaid.md`
- `/home/phuc/projects/solace-browser/data/apps/solace-coder/manifest.prime-mermaid.md`

## Rules

- build on the existing manager, design, and coder substrates, not beside them
- do not skip adversarial review and signoff state
- `solace-qa` must be a real worker app with inbox/outbox structure
- QA inputs must be bounded by manager assignment plus design artifacts plus coder run artifacts
- Prime Mermaid is the source of truth for QA workflow contracts, evidence flow, signoff flow, and release-gate diagrams
- avoid new standalone JSON/YAML system definitions when Prime Mermaid can express the contract
- if YAML/JSON compatibility files are still required, keep the Prime Mermaid file as the source contract
- make the manager/coder-to-QA handoff visible in Hub or Back Office, not hidden in prose only
- make QA artifacts explicit: verdict, findings, screenshots, assertions, regressions, approvals, and release gate state
- keep the round local-first, inspectable, and evidence-first

## Hard Rejection Criteria

The round fails if any of these remain true:

- there is no `solace-qa` worker app with a real inbox/outbox contract
- there is no explicit handoff contract from manager/coder to QA
- there is no durable object path for QA runs, findings, or signoffs
- the Hub surface cannot point to QA artifacts for `solace-browser`
- QA work is not visibly bounded by the design and coder artifacts from earlier rounds
- the round expands into broader release automation instead of perfecting the QA role

## Required Deliverables

You must produce all of these:

1. one `solace-qa` worker app under `data/apps/`
2. one Prime Mermaid QA workflow and evidence/signoff source set
3. one explicit manager/coder-to-QA handoff contract
4. one initial QA workspace shell or visible QA view in Hub
5. one durable object path for QA runs, findings, reviews, or signoffs
6. one storage note showing where QA artifacts now live
7. one narrow smoke path
8. one narrow automated test or scripted verification

## Current Tickets

### Ticket 1: Create the `solace-qa` worker app
Objective: make the QA role a real worker app rather than an idea.
Scope: add `data/apps/solace-qa/` with inbox, outbox, diagrams, Prime Mermaid source contract, and compatibility files only where still required.
Done when: the app satisfies the current inbox/outbox contract and clearly declares the QA role.
Evidence required: changed files, app paths, and one short summary of the inbox/outbox layout.

### Ticket 2: Add the first QA diagram set
Objective: create QA truth for `solace-browser` itself.
Scope: add at least:
- one QA workflow diagram
- one evidence flow diagram
- one signoff/release-gate diagram
- one regression/failure routing diagram
Done when: the manager can point to committed Prime Mermaid QA artifacts as the source of truth for the validation role.
Evidence required: artifact paths and one short note on what each diagram governs.

### Ticket 3: Add the manager/coder-to-QA handoff contract
Objective: make QA assignment explicit and durable.
Scope: define what manager and coder pass to QA for a `solace-browser` task: request, assignment, design refs, code-run refs, evidence refs, assertions, and expected outputs.
Done when: there is one committed handoff artifact or object contract that a reviewer can inspect.
Evidence required: artifact path and one sample payload or record.

### Ticket 4: Add the first QA workspace view
Objective: expose QA as a visible role in the Dev workspace.
Scope: add one initial QA-facing view in Hub or the Dev workspace that points to findings, signoffs, and validation artifacts for `solace-browser`.
Done when: a human can open the Hub and inspect current QA truth for the active project.
Evidence required: changed files, screenshots, and one short walkthrough.

### Ticket 5: Add durable QA-state storage
Objective: stop validation truth from living only in test output or chat.
Scope: add the minimum Back Office object path or schema needed for QA runs, findings, signoffs, or release-gate records.
Done when: the QA role can point to durable shared state rather than only repo-local artifacts.
Evidence required: changed files, API paths exercised, and one sample record or payload.

### Ticket 6: Add one storage note
Objective: complete the role stack storage model.
Scope: update or add one artifact that explains where:
- QA source diagrams
- QA handoff artifacts
- QA worker app state
- QA findings, signoffs, and evidence
live now.
Done when: the first four-role Dev stack has a stable storage model.
Evidence required: artifact path and one short summary.

### Ticket 7: Add one narrow smoke path and one narrow test
Objective: make the round reviewable and repeatable.
Scope:
- one documented local smoke path from startup to manager workspace to QA artifact inspection
- one automated test or lightweight scripted verification for the QA role flow
Done when: a reviewer can run the commands without guessing hidden steps.
Evidence required: exact commands, exact output, screenshot paths, and remaining risks.

## Suggested File Targets

- `solace-hub/src/index.html`
- `solace-hub/src/hub-app.js`
- `solace-runtime/src/routes/backoffice.rs`
- `solace-runtime/src/backoffice/schema.rs`
- `solace-runtime/src/routes/apps.rs`
- `specs/solace-dev/`
- `data/apps/solace-qa/`
- `tests/`

## Evidence Return Format

- changed files
- exact test/check command output
- exact APIs exercised
- QA artifact paths
- handoff artifact path
- sample records or payloads
- screenshot paths
- local smoke path
- remaining risks

## Out Of Scope

- broader release automation beyond the first QA role substrate
- broad cloud sync or billing work
- unrelated Chromium platform changes
- redesigning earlier role rounds instead of building on them
