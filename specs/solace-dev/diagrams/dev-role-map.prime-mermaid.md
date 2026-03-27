# Dev Role Map

```mermaid
graph TD
    classDef manager fill:#d946ef,stroke:#701a75,color:#fff
    classDef design fill:#3b82f6,stroke:#1e3a8a,color:#fff
    classDef coder fill:#10b981,stroke:#064e3b,color:#fff
    classDef qa fill:#f59e0b,stroke:#78350f,color:#fff
    classDef object fill:#1f2937,stroke:#9ca3af,color:#fff

    Manager[Solace Dev Manager]::manager
    Design[Solace Design]::design
    Coder[Solace Coder]::coder
    QA[Solace QA]::qa

    Projects[(Projects)]::object
    Requests[(Requests)]::object
    Assignments[(Assignments)]::object

    Manager -->|creates/triage| Requests
    Manager -->|maps scope to| Projects
    Manager -->|routes to roles via| Assignments

    Assignments -->|Design spec creation| Design
    Assignments -->|Implementation| Coder
    Assignments -->|Replay adversarial validation| QA

    Design -.->|reads| Projects
    Coder -.->|reads| Projects
    QA -.->|reads| Projects
```
