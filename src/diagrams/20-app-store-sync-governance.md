# 20 — App Store Sync Governance

```mermaid
flowchart TD
    A[App manifests in data/default/apps] --> B[sync_app_store_catalog.py]
    B --> C[official-store.json in git]
    C --> D[GET /api/apps and /api/apps/{appId}]
    D --> E[Website App Store]
    D --> F[Browser App Store]

    G[User proposal form] --> H[POST /api/app-store/proposals]
    H --> I{Backend}
    I -->|local dev| J[proposed-apps-dev.jsonl]
    I -->|production| K[Firestore app_store_proposals]
    J --> L[Human triage]
    K --> L
    L --> M[Accepted app implementation]
    M --> A
```

## Notes
- Official catalog is git-backed and reviewable.
- Proposals are queue-only and never auto-promote into official catalog.
- Local development uses file backend; production uses Firestore backend.
- Browser and website app stores consume the same API-backed catalog source.

