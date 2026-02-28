# TASK-002 Test Recovery

```mermaid
flowchart TD
    A[pytest tests/test_distribution.py tests/test_stillwater_qa.py] --> B{Failure class}
    B -->|Distribution assets missing| C[Restore VERSION + build scripts + installer page]
    B -->|Stillwater server unavailable| D[Mark UI/API suites server_required]
    C --> E[Re-run distribution tests]
    D --> F[Re-run Stillwater tests]
    E --> G{Green?}
    F --> G
    G -->|yes| H[Run full pytest tests/]
    G -->|no| I[Adjust implementation, not the contract]
    I --> A
```

States:
- Distribution path fails closed until required artifacts exist.
- Stillwater path skips with an explicit reason when the external server is unavailable.
- Full-suite verification is required before marking TASK-002 complete.
