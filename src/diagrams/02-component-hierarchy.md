# Component Hierarchy

```mermaid
flowchart TD
    APP[Browser App Shell]
    APP --> HOME[Homepage App Grid]
    APP --> AUTH[Auth and session manager]
    APP --> RUNNER[Recipe runner]
    APP --> APPROVAL[Approval modal]
    APP --> HISTORY[Run history and vault viewer]

    RUNNER --> WS[Webservice client layer]
    WS --> API[/api/v1/browser/*]
    WS --> FILES[/api/v1/fs/*]
    WS --> EVIDENCE[/api/v1/evidence/*]

    RUNNER --> INBOX[Inbox config loader]
```

## Notes
- No chat component in runtime path.
- Recipe runner is deterministic and driven by app specs.
