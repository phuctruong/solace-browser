# Solace Browser Project Map

```mermaid
graph TD
    classDef core fill:#4f46e5,stroke:#312e81,color:#fff
    classDef frontend fill:#06b6d4,stroke:#164e63,color:#fff
    classDef backend fill:#ea580c,stroke:#7c2d12,color:#fff
    classDef evidence fill:#10b981,stroke:#064e3b,color:#fff

    SolaceBrowser[Solace Browser Project Map]::core

    subgraph Hub UI Boundaries
        HubShell[Solace Hub Shell Index]:::frontend
        HubAppJS[Hub Application JS]:::frontend
        DevWorkspace[Dev Workspace Panel]:::frontend
    end

    subgraph Runtime Routing Boundaries
        HubControl[Hub Control API]:::backend
        BackofficeREST[Backoffice CRUD API]:::backend
        AppsREST[Apps Engine API]:::backend
    end

    subgraph Backoffice Schemas
        ManagerManifest[Solace Dev Manager manifest.yaml]:::backend
    end

    subgraph Evidence & Part 11
        EvidenceRecorder[Evidence Event Recorder]:::evidence
        EvidenceLog[runtime/evidence.jsonl]:::evidence
    end

    SolaceBrowser --> HubShell
    HubShell --> HubAppJS
    HubShell --> DevWorkspace

    SolaceBrowser --> HubControl
    SolaceBrowser --> BackofficeREST
    SolaceBrowser --> AppsREST

    BackofficeREST --> ManagerManifest

    SolaceBrowser --> EvidenceRecorder
    HubControl -.-> EvidenceRecorder
    BackofficeREST -.-> EvidenceRecorder
    EvidenceRecorder --> EvidenceLog
```
