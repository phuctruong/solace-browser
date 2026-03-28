# Inspection-Context Panel Flow

Governs: how the workspace renders the current inspection context with source provenance and copy-link affordance.

```mermaid
flowchart TD
    A[Context change triggered] --> B{Source type?}
    
    B -->|User click| C["__solaceSelectRun → source='selected'"]
    B -->|Hash restore| D["restoreSelectedRun → source='deep-link'"]
    B -->|Session restore| E["restoreSelectedRun → source='restored'"]
    B -->|No stored + latest| F["default hydration → source='selected'"]
    B -->|Stale fallback| G["default hydration → source='fallback'"]
    
    C & D & E & F & G --> H[updateInspectionContext]
    H --> I[render source pill with color]
    H --> J[render app/run code badge]
    H --> K[render deep-link input + copy button]
    
    K --> L{User clicks copy?}
    L -->|Yes| M[__solaceCopyInspectionLink]
    M --> N{navigator.clipboard?}
    N -->|Yes| O[writeText → "✓ copied"]
    N -->|No| P[execCommand fallback → "✓ copied"]

    style C fill:#312e81,color:#a5b4fc
    style D fill:#1e3a5f,color:#7dd3fc
    style E fill:#064e3b,color:#6ee7b7
    style G fill:#78350f,color:#fcd34d
```
