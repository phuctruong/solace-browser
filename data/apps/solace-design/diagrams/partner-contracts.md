# Partner Contracts

```mermaid
graph TD
    Manager[Manager] -->|assigns design tasks| Design[Design]
    Design -->|emits specs to| Backoffice[(Backoffice)]
    Design -->|handoff artifacts to| Coder[Coder]
    Manager -->|reviews| Design
```
