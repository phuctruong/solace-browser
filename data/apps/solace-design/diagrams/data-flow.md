# Data Flow

```mermaid
flowchart LR
    ManagerOutbox[Manager Outbox] --> DesignInbox[Design Inbox]
    DesignInbox --> SpecEngine[Spec Production]
    SpecEngine --> DesignOutbox[Design Outbox]
    DesignOutbox --> Backoffice[(Backoffice)]
    Backoffice --> ManagerReview[Manager Review]
```
