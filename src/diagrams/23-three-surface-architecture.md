# Diagram 23: Three-Surface Architecture
# DNA: `companion(desktop) + sidebar(browser) + api(brain) = three_surfaces_one_server`
**Paper:** 47 (yinyang-sidebar-architecture) | **Auth:** 65537

---

## System Overview

```mermaid
graph TB
    subgraph Desktop ["Companion App (Tauri ~20MB)"]
        CA_MAIN[Main Window<br/>Sessions / Status / OAuth3]
        CA_TRAY[System Tray<br/>Quick Actions / Notifications]
        CA_WIZARD[First-Run Wizard<br/>3 screens / 30s]
    end

    subgraph Browser ["Chromium (Playwright-managed)"]
        SW[Service Worker<br/>URL detection / Tab events]
        SP[Side Panel<br/>4 tabs: Now / Runs / Chat / More]
        PAGE[Web Page<br/>gmail.com / linkedin.com / etc]
    end

    subgraph Server ["localhost:8888 (Python)"]
        API[REST API<br/>/api/apps /api/schedule /api/status]
        WS[WebSocket<br/>ws://localhost:8888/ws/yinyang]
        CDP_BROKER[CDP Broker<br/>Allowlisted methods only]
        RECIPES[Recipe Engine<br/>Sealed recipes / Evidence]
    end

    subgraph Storage ["~/.solace/"]
        DB[(SQLite<br/>schedules / evidence)]
        VAULT[OS Keychain<br/>tokens / BYOK keys]
        CONFIG[config.json<br/>preferences]
    end

    CA_MAIN -->|manages| Server
    CA_MAIN -->|spawns| Browser
    CA_TRAY -->|quick actions| CA_MAIN

    SW -->|URL match| SP
    SP -->|WebSocket| WS
    SP -->|HTTP| API

    API -->|recipes| RECIPES
    API -->|evidence| DB
    CDP_BROKER -->|automation| PAGE

    Server -->|read/write| Storage
    CA_MAIN -->|keychain| VAULT

    style Desktop fill:#1a1a2e,stroke:#6C5CE7,color:#e0e0e0
    style Browser fill:#0f0f23,stroke:#6C5CE7,color:#e0e0e0
    style Server fill:#252540,stroke:#2ecc71,color:#e0e0e0
    style Storage fill:#252540,stroke:#f1c40f,color:#e0e0e0
```

## Port Map

```mermaid
graph LR
    subgraph Ports
        P8888["localhost:8888<br/>Solace API + WebSocket"]
        P9222["localhost:9222<br/>CDP (Playwright internal)"]
    end

    COMPANION[Companion App] -->|HTTP/WS| P8888
    SIDEBAR[Sidebar Panel] -->|HTTP/WS| P8888
    CLI[CLI / MCP Agents] -->|HTTP| P8888
    PLAYWRIGHT[Playwright] -->|CDP| P9222
    P8888 -->|broker| P9222

    style P8888 fill:#2ecc71,stroke:#2ecc71,color:#000
    style P9222 fill:#e74c3c,stroke:#e74c3c,color:#fff
```

## Before vs After

```mermaid
graph LR
    subgraph Before ["BEFORE (Current)"]
        B_TERM[Terminal] -->|"solace-browser"| B_SERVER["8791 + 9222"]
        B_SERVER -->|"20+ HTML pages"| B_WEBAPP[Localhost Webapp]
        B_WEBAPP -.->|"no yinyang"| B_GMAIL[Gmail]
    end

    subgraph After ["AFTER (Sidebar)"]
        A_APP[Companion App] -->|spawns| A_SERVER["8888 + 9222"]
        A_SERVER -->|WebSocket| A_SIDEBAR[Sidebar Panel]
        A_SIDEBAR -->|"follows everywhere"| A_GMAIL[Gmail]
        A_APP -->|"system tray"| A_TRAY[Tray]
    end

    style Before fill:#e74c3c,stroke:#e74c3c,color:#fff
    style After fill:#2ecc71,stroke:#2ecc71,color:#fff
```
