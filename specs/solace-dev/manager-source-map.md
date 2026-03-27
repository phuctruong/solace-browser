# Solace Dev Manager Source-Canon Map

**Objective**: Map the Solace Dev role architecture onto the current Hub/Browser canon and live `solace-browser` code.

## Reused Hub/Browser Canon

The following existing components are reused directly to support the Dev Manager workspace instead of building greenfield:

1. **Hub UI Shell** (`solace-hub/src/index.html`): The main visual interface for the Dev Manager, utilizing the existing standard dark mode, tabbed panel structure, and Back Office connectivity.
2. **Backoffice App Substrate** (`solace-runtime/src/routes/backoffice.rs` & `solace-runtime/src/backoffice/schema.rs`): Used to define and expose the durable object model (`projects`, `requests`, `assignments`, etc.) via `data/apps/solace-dev-manager/manifest.yaml`.
3. **Prime Mermaid Substrate**: Used systematically to encode system architecture, role flows, and workflow diagrams. Replaces ad-hoc JSON/YAML where a visual topological model natively fulfills the contract.
4. **App Directory Convention** (`~/.solace/apps/localhost/`, `data/apps/`, and `data/default/apps/`): Reused to host the manager's compatibility manifest plus Prime Mermaid source contract.

## Target Concepts from Role Architecture

These new concepts are actively implemented by the first Dev Manager Round:

- **Requests & Assignments**: Mapped to native SQLite records via the backoffice REST APIs `POST /api/v1/backoffice/solace-dev-manager/requests`.
- **Project Scope Map**: Represented by explicit Prime Mermaid diagrams containing target pages and backend route boundaries (`solace-browser.prime-mermaid.md`).
- **Diagram-Driven Flow**: Replacing unmanaged plaintext specs with versioned mermaid files stored in `specs/solace-dev/diagrams/`.
- **Evidence Bundles**: Native recording via `crate::evidence::record_event` tied to actor IDs ("system" or "manager") when project states change.

## Solace Dev Manager Implementation Map

- **Manager Tab**: Handled entirely inside `solace-hub/src/index.html` under the single-page application framework.
- **REST APIs**: `GET/POST /api/v1/backoffice/solace-dev-manager/projects`
- **Schema Source**: `data/apps/solace-dev-manager/manifest.prime-mermaid.md`
- **Compatibility Schema**: `data/apps/solace-dev-manager/manifest.yaml`
- **First Supported Project**: `solace-browser`
