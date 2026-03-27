# Data Flow

```mermaid
flowchart LR
    Hub --> Backoffice
    Backoffice --> WorkerInbox
    WorkerInbox --> WorkerOutbox
    WorkerOutbox --> Evidence
    Evidence --> Hub
```
