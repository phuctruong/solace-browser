# Deep-Link Inspection Flow

Governs: how URL hash state (`#inspect=appId/runId`) provides explicit, shareable inspection context.

```mermaid
flowchart TD
    A[Dev tab activated] --> B[hydrateRunHistory]
    B --> C[render run history from API]
    C --> D{URL has #inspect=appId/runId?}
    
    D -->|Yes| E{Run exists in DOM?}
    E -->|Yes| F["restoreSelectedRun(source='deep-link')"]
    F --> G["badge: 'deep-link: app @ run_id'"]
    G --> H[inspection + previews]
    
    E -->|No| I[showInvalidDeepLinkFallback]
    I --> J["badge: 'deep link invalid'"]
    J --> K[clearInspectionHash]
    K --> L[fall through to latest]
    
    D -->|No| M{sessionStorage has selection?}
    M -->|Yes| N{Run exists?}
    N -->|Yes| O["restoreSelectedRun(source='restored')"]
    N -->|No| P[stale fallback]
    P --> L
    
    M -->|No| L
    L --> Q[select latest + saveSelectedRun + setInspectionHash]

    style I fill:#7f1d1d,color:#fca5a5
    style F fill:#064e3b,color:#6ee7b7
```

## Precedence Rule

```
1. URL hash (#inspect=appId/runId)  ← explicit, shareable
2. sessionStorage                   ← same-tab persistence
3. Latest run across all roles      ← default fallback
```
