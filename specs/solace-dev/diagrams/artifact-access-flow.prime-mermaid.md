# First-Class Artifact Access Flow

Governs: how the Dev workspace accesses run artifacts through first-class API routes.

```mermaid
sequenceDiagram
    participant U as Hub UI
    participant JS as hub-app.js
    participant RT as solace-runtime

    Note over U: Inspection panel rendered (from hydration or post-run)
    
    alt Open report
        U->>RT: GET /api/v1/apps/:app_id/runs/:run_id/artifact/report.html
        RT->>RT: whitelist check (report.html ✓)
        RT->>RT: read outbox/runs/:run_id/report.html
        RT-->>U: text/html; charset=utf-8
    end
    
    alt Open payload
        U->>RT: GET /api/v1/apps/:app_id/runs/:run_id/artifact/payload.json
        RT-->>U: application/json
    end
    
    alt Open stillwater
        U->>RT: GET /api/v1/apps/:app_id/runs/:run_id/artifact/stillwater.json
        RT-->>U: application/json (or 404 if not present)
    end
    
    alt Open events file
        U->>RT: GET /api/v1/apps/:app_id/runs/:run_id/artifact/events.jsonl
        RT-->>U: application/x-ndjson
    end
    
    alt Open events API
        U->>RT: GET /api/v1/apps/:app_id/runs/:run_id/events
        RT-->>U: {events, count, chain_valid}
    end

    Note over RT: Allowed artifacts whitelist:
    Note over RT: report.html, payload.json, stillwater.json,
    Note over RT: ripple.json, events.jsonl, stdout.txt,
    Note over RT: stderr.txt, evidence.json
```
