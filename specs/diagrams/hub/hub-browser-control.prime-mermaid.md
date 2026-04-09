<!-- Diagram: hub-browser-control -->
# hub-browser-control: Hub Browser Control — Navigate, Click, Fill, Screenshot
# DNA: `control = navigate(url) + click(selector) + fill(selector,value) + screenshot + evaluate(js) + act(action)`
# Auth: 65537 | State: SEALED | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-runtime](hub-runtime.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TD
    AGENT[AI Agent / CLI / MCP] --> RUNTIME[Runtime :8888]
    
    subgraph NAVIGATE[Navigation]
        RUNTIME --> NAV[POST /api/navigate<br>go to URL]
        RUNTIME --> NAV_BG[POST /api/navigate/background<br>background load]
    end
    
    subgraph INTERACT[Interaction]
        RUNTIME --> CLICK[POST /api/click<br>click element by selector]
        RUNTIME --> FILL[POST /api/fill<br>type into input field]
        RUNTIME --> UPLOAD[POST /api/upload<br>file upload]
        RUNTIME --> ACT[POST /api/act<br>high-level action]
    end
    
    subgraph CAPTURE[Capture]
        RUNTIME --> SCREENSHOT[POST /api/screenshot<br>full page or element]
        RUNTIME --> SCREENSHOT_BG[POST /api/screenshot-bg<br>background capture]
        RUNTIME --> DOM_SNAP[GET /api/dom-snapshot<br>full DOM tree]
        RUNTIME --> ARIA_SNAP[GET /api/aria-snapshot<br>accessibility tree]
        RUNTIME --> PAGE_SNAP[GET /api/page-snapshot<br>Prime Wiki snapshot]
        RUNTIME --> DOM_FP[POST /api/dom/fingerprint<br>page structure hash]
    end
    
    subgraph EVALUATE[Evaluate]
        RUNTIME --> EVAL[POST /api/evaluate<br>run JavaScript in page]
        RUNTIME --> PAGE_EVAL[POST /api/pages/{id}/evaluate<br>run JS in specific tab]
    end
    
    subgraph RISK[Risk Management]
        RUNTIME --> ESCALATE[POST /api/escalate<br>risk tier upgrade]
        RUNTIME --> ESTIMATE[POST /api/estimate<br>cost estimation]
    end
    
    CAPTURE --> EVIDENCE[Evidence Chain<br>every capture hashed]
    INTERACT --> EVIDENCE
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-67 -->
| Node | Status | Evidence |
|------|--------|----------|
| NAV | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| NAV_BG | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| CLICK | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| FILL | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| UPLOAD | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| ACT | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| SCREENSHOT | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| SCREENSHOT_BG | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| DOM_SNAP | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| ARIA_SNAP | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| PAGE_SNAP | SEALED | implemented + tested |
| DOM_FP | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| EVAL | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| PAGE_EVAL | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| ESCALATE | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| ESTIMATE | SEALED | spec only — from original solace_browser_server.py (152 handlers) |
| EVIDENCE | SEALED | implemented + tested |


## Related Papers
- [papers/hub-sidebar-paper.md](../papers/hub-sidebar-paper.md)
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
