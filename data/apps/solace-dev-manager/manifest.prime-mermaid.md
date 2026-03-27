# App: Solace Dev Manager

# DNA: `Manager-first Solace Dev worker app that routes requests, assignments, approvals, and release state over durable Back Office objects.`

## Identity

- **ID**: solace-dev-manager
- **Version**: 1.0.0
- **Domain**: localhost
- **Category**: backoffice
- **Type**: worker-app
- **Visibility**: local-first

## Role Contract

```mermaid
graph TD
    Manager[solace-dev-manager]
    Projects[(projects)]
    Requests[(requests)]
    Assignments[(assignments)]
    Approvals[(approvals)]
    Releases[(releases)]

    Manager --> Projects
    Manager --> Requests
    Manager --> Assignments
    Manager --> Approvals
    Manager --> Releases
```

## Backoffice Contract

```mermaid
erDiagram
    PROJECTS ||--o{ REQUESTS : contains
    REQUESTS ||--o{ ASSIGNMENTS : spawns
    ASSIGNMENTS ||--o{ APPROVALS : requires
    ASSIGNMENTS ||--o{ ARTIFACTS : emits
    PROJECTS ||--o{ RELEASES : ships
```

## Compatibility

- `manifest.yaml` remains the runtime compatibility manifest.
- This Prime Mermaid file is the source of truth for the manager app contract.
