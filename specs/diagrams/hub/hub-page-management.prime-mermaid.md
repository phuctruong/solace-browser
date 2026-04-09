<!-- Diagram: hub-page-management -->
# hub-page-management: Hub Multi-Tab Page Management
# DNA: `pages = new(url) + list + navigate(id,url) + evaluate(id,js) + close(id)`
# Auth: 65537 | State: SEALED | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-browser-control](hub-browser-control.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TD
    RUNTIME[Runtime :8888] --> PAGES[Page Manager<br>multi-tab control]
    
    PAGES --> NEW[POST /api/pages/new<br>open new tab]
    PAGES --> LIST[GET /api/pages<br>list open tabs]
    PAGES --> PAGE_NAV[POST /api/pages/{id}/navigate<br>navigate specific tab]
    PAGES --> PAGE_EVAL[POST /api/pages/{id}/evaluate<br>run JS in tab]
    PAGES --> PAGE_CLOSE[DELETE /api/pages/{id}<br>close tab]
    
    NEW --> SESSION[Session Tracking<br>session_id per tab]
    SESSION --> DEDUP[Dedup Guard<br>3-layer protection]
    SESSION --> EVIDENCE[Evidence<br>every action logged]
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-67 -->
| Node | Status | Evidence |
|------|--------|----------|
| PAGES | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| NEW | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| LIST | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| PAGE_NAV | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| PAGE_EVAL | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| PAGE_CLOSE | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| SESSION | SEALED | implemented + tested |
| DEDUP | SEALED | implemented + tested |
| EVIDENCE | SEALED | implemented + tested |


## Related Papers
- [papers/hub-three-realms-paper.md](../papers/hub-three-realms-paper.md)

## Forbidden States
```
PORT_9222              → KILL (use runtime at :8888)
DIRECT_CDP             → KILL (all control via runtime API)
CLICK_WITHOUT_EVIDENCE → KILL (every action produces evidence)
NAVIGATE_WITHOUT_GATE  → KILL (budget + scope check before action)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
