# Workflow

```mermaid
flowchart TD
    Request[Request] --> Map[Project map]
    Map --> Assign[Assignment]
    Assign --> Role[Next role inbox]
    Role --> Evidence[Artifacts and evidence]
    Evidence --> Approval[Approval]
```
