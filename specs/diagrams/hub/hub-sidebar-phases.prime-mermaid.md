<!-- Diagram: 10-sidebar-implementation-phases -->
# 10: Diagram 29: Sidebar Implementation Phases
# DNA: `phases = P0(tests) → P1(shell) → P2(features) → P3(enterprise) → P4(kill webapp)`
# SHA-256: cb20a8c254261cf250adde71d461c947f2be58dec1acd47b9c0fa3d4cbe1fe87
# Auth: 65537 | State: SEALED | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions

## Canonical Diagram

```mermaid
gantt
    title Sidebar Implementation Pipeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Phase 0: Spike
    Rust runtime (solace-runtime) E2E test pass           :done, p0a, 2026-03-07, 1d
    35 static tests pass                       :done, p0b, 2026-03-07, 1d
    QA notebook 77 (143 probes)               :done, p0c, 2026-03-07, 1d

    section Phase 1: Sidebar Shell
    Build native C++ WebUI sidebar into Chromium   :p1a, 2026-03-08, 7d
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
    Port 8791  to  8888 complete                 :p4c, after p4b, 1d
```

## PM Status
<!-- Updated: 2026-03-14 | Session: P-67 -->
No flowchart nodes — Gantt chart covers implementation phases.
Overall: N/A


## Related Papers
- [papers/hub-sidebar-paper.md](../papers/hub-sidebar-paper.md)

## Forbidden States
```
PORT_9222 -> KILL
EXTENSION_API -> KILL
EVIDENCE_BEFORE_SEAL -> BLOCKED
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```

## LEAK Interactions
- Calls: backoffice-messages, evidence chain
- Orchestrates with: other Solace apps via API
- Pattern: input → process → output → evidence
