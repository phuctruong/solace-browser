# Storage and Mapping Artifact

**Objective**: Define explicitly where versioned diagrams, role app state, shared backoffice state, and evidence screenshots live across the repository and user filesystem.

## 1. Versioned Diagrams and Mappings

These files define the fundamental topology and logic of the system. They are the primary source of truth.

- **Storage Location**: `solace-browser/specs/solace-dev/diagrams/*.prime-mermaid.md` and `solace-browser/specs/solace-dev/project-mappings/*.prime-mermaid.md`
- **Format**: `.prime-mermaid.md` (Markdown with embedded `mermaid` graph blocks)
- **Managed By**: Dev Manager (creation/scope) and Source Control (Git).
- **Consumption**: Parsed via `view_file` or static text inspection before coding/design starts.

## 2. Role App Operational State

Worker app boundaries, prompts, and temporary derived states.

- **Storage Location**: `solace-browser/data/apps/<role_id>/`
- **Examples**:
  - Manager source: `data/apps/solace-dev-manager/manifest.prime-mermaid.md`
  - Manager compatibility: `data/apps/solace-dev-manager/manifest.yaml`
  - Design: `data/apps/solace-design/`
  - Coder: `data/apps/solace-coder/`
  - QA: `data/apps/solace-qa/`
- **Contents**: Prime Mermaid source contracts, compatibility manifests, recipe templates, static prompts, and config settings.
- **Rule**: Prime Mermaid stays primary; YAML/JSON are compatibility artifacts until the runtime finishes the migration.

## 3. Shared Backoffice State

Durable operational memory encompassing requests, assignments, project scope boundaries, and approval state.

- **Storage Location (Disk)**: Local SQLite database via `solace-runtime` DB mappings (`~/.solace/data/backoffice-<app_id>.db` or equivalent paths mapped by `solace_home()`).
- **REST Endpoints**: `/api/v1/backoffice/solace-dev-manager/<table_name>`
- **Schema Source**: `data/apps/solace-dev-manager/manifest.prime-mermaid.md`
- **Compatibility Input**: `data/apps/solace-dev-manager/manifest.yaml`
- **Tables Used**: `projects`, `requests`, `assignments`, `artifacts`, `approvals`, `releases`.

## 4. Design Role Artifacts

Design-specific state produced by the `solace-design` worker app.

- **Design Source Diagrams**: `solace-browser/specs/solace-dev/diagrams/browser-*.prime-mermaid.md` and `design-handoff-flow.prime-mermaid.md`
- **Design Worker App State**: `solace-browser/data/apps/solace-design/` (manifest, inbox/outbox, diagrams, recipe)
- **Design Handoff Records**: Durable backoffice objects in `design_handoffs` table under `solace-dev-manager` — REST endpoint: `/api/v1/backoffice/solace-dev-manager/design_handoffs`
- **Design Specs**: Durable backoffice objects in `design_specs` table under `solace-design` — REST endpoint: `/api/v1/backoffice/solace-design/design_specs`
- **Design Reviews**: Durable backoffice objects in `design_reviews` table under `solace-design` — REST endpoint: `/api/v1/backoffice/solace-design/design_reviews`
- **Handoff Contract**: `solace-browser/specs/solace-dev/manager-to-design-handoff.md`
- **Managed By**: Manager (handoff creation), Design (spec production), Source Control (Git for diagrams).

## 5. Coder Role Artifacts

Coder-specific state produced by the `solace-coder` worker app.

- **Coder Source Diagrams**: `solace-browser/specs/solace-dev/diagrams/coder-*.prime-mermaid.md`
- **Coder Worker App State**: `solace-browser/data/apps/solace-coder/` (manifest, inbox/outbox, diagrams, recipe)
- **Coder Handoff Records**: Durable backoffice objects in `coder_handoffs` table under `solace-dev-manager` — REST endpoint: `/api/v1/backoffice/solace-dev-manager/coder_handoffs`
- **Code Runs**: Durable backoffice objects in `code_runs` table under `solace-coder` — REST endpoint: `/api/v1/backoffice/solace-coder/code_runs`
- **Code Artifacts**: Durable backoffice objects in `code_artifacts` table under `solace-coder` — REST endpoint: `/api/v1/backoffice/solace-coder/code_artifacts`
- **Code Reviews**: Durable backoffice objects in `coder_reviews` table under `solace-coder` — REST endpoint: `/api/v1/backoffice/solace-coder/coder_reviews`
- **Handoff Contract**: `solace-browser/specs/solace-dev/design-to-coder-handoff.md`
- **Managed By**: Manager (handoff creation), Design (spec input), Coder (run production), Source Control (Git for diagrams).

## 6. QA Role Artifacts

QA-specific state produced by the `solace-qa` worker app.

- **QA Source Diagrams**: `solace-browser/specs/solace-dev/diagrams/qa-*.prime-mermaid.md`
- **QA Worker App State**: `solace-browser/data/apps/solace-qa/` (manifest, inbox/outbox, diagrams, recipe)
- **QA Handoff Records**: Durable backoffice objects in `qa_handoffs` table under `solace-dev-manager` — REST endpoint: `/api/v1/backoffice/solace-dev-manager/qa_handoffs`
- **QA Runs**: Durable backoffice objects in `qa_runs` table under `solace-qa` — REST endpoint: `/api/v1/backoffice/solace-qa/qa_runs`
- **QA Findings**: Durable backoffice objects in `qa_findings` table under `solace-qa` — REST endpoint: `/api/v1/backoffice/solace-qa/qa_findings`
- **QA Signoffs**: Durable backoffice objects in `qa_signoffs` table under `solace-qa` — REST endpoint: `/api/v1/backoffice/solace-qa/qa_signoffs`
- **Handoff Contract**: `solace-browser/specs/solace-dev/coder-to-qa-handoff.md`
- **Managed By**: Manager (handoff creation), Coder (run input), QA (validation/signoff production), Source Control (Git for diagrams).

## 7. Screenshots and Evidence
Records produced across the flow documenting proof of functionality, validation, or issues.

- **Storage Location (Screenshots)**: Local `/tmp/` during processing, but ultimately transformed/embedded directly into `~/.solace/runtime/evidence.jsonl`.
- **Storage Location (Audit Trail)**: The global Geometric Law audit trail output (`~/projects/solace-cli/dragon/audit/evidence.jsonl`) and the local runtime trace (`~/.solace/runtime/evidence.jsonl`).
- **Format**: Base64 data chunks within JSONL structures.
