# Diagram 29: Sidebar Implementation Phases
# DNA: `implement(phase0→phase4) × test(probe) × ship(push)`
# Paper: 47 v8 | Auth: 65537

```mermaid
gantt
    title Sidebar Implementation Pipeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Phase 0: Spike
    Extension loads via --load-extension      :done, p0a, 2026-03-07, 1d
    35 static tests pass                       :done, p0b, 2026-03-07, 1d
    QA notebook 77 (143 probes)               :done, p0c, 2026-03-07, 1d

    section Phase 1: Sidebar Shell
    Load extension in solace_browser_server   :p1a, 2026-03-08, 2d
    Side panel opens on browser start         :p1b, after p1a, 1d
    4 tabs render (Now/Runs/Chat/More)        :p1c, after p1b, 1d
    WebSocket connects to localhost:8888      :p1d, after p1c, 1d
    API endpoints for sidebar                  :p1e, after p1d, 2d

    section Phase 2: Core Features
    App detection + badge                     :p2a, after p1e, 2d
    Recipe matching per URL                   :p2b, after p2a, 1d
    Run Now / approval flow                   :p2c, after p2b, 2d
    Evidence chain display                    :p2d, after p2c, 2d
    eSign on approval                         :p2e, after p2d, 1d

    section Phase 3: Enterprise
    BAT acceptance matrix                     :p3a, after p2e, 2d
    Multi-tab data comparison                 :p3b, after p3a, 2d
    Budget enforcement UI                     :p3c, after p3b, 1d
    Cloud twin status                         :p3d, after p3c, 1d

    section Phase 4: Kill Webapp
    Migrate remaining pages to sidebar        :p4a, after p3d, 3d
    Delete 15+ HTML pages                     :p4b, after p4a, 1d
    Port 8791 → 8888 complete                 :p4c, after p4b, 1d
```

## Implementation Priority
1. Get extension loading in solace_browser_server.py (the prerequisite for everything)
2. WebSocket connection (the communication backbone)
3. App detection + Run Now (the core value)
4. Evidence + eSign (the compliance moat)
5. Enterprise features (the revenue driver)
