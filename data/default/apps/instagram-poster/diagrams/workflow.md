# Workflow — Instagram Poster

```mermaid
flowchart TD
    TRIGGER[Trigger] --> PREVIEW[Preview once]
    PREVIEW --> APPROVAL[Approve or reject]
    APPROVAL --> EXECUTE[Deterministic replay]
    EXECUTE --> OUTBOX[outbox/reports/]
```
