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

## 4. Screenshots and Evidence
Records produced across the flow documenting proof of functionality, validation, or issues.

- **Storage Location (Screenshots)**: Local `/tmp/` during processing, but ultimately transformed/embedded directly into `~/.solace/runtime/evidence.jsonl`.
- **Storage Location (Audit Trail)**: The global Geometric Law audit trail output (`~/projects/solace-cli/dragon/audit/evidence.jsonl`) and the local runtime trace (`~/.solace/runtime/evidence.jsonl`).
- **Format**: Base64 data chunks within JSONL structures.
