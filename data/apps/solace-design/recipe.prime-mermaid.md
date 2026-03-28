# Solace Design Recipe

```mermaid
flowchart TD
    A[Receive assignment from manager inbox] --> B[Load project page map]
    B --> C[Produce page/state/component specs]
    C --> D[Write draft design spec]
    D --> E[Submit for manager review]
    E --> F[Emit approved artifacts to outbox]
```
