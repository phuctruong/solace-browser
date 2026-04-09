<!-- Diagram: hub-dashboard -->
# hub-dashboard: Hub Dashboard — GATE + LAUNCHER (5 Tabs)
# DNA: `hub = gate(LLM) → launch(browser) → monitor(sessions+events) → consent(remote) → settings(version+auth)`
# Auth: 65537 | State: SEALED | Version: 2.1.0

## Architecture Decision (P-71, 65537 expert consensus 9.1/10)
Hub = GATE + LAUNCHER. NOT a duplicate dashboard.
- Hub is the CONTROL PLANE (start, stop, consent, settings)
- Dashboard at localhost:8888 is the DATA PLANE (apps, domains, evidence, runs)
- Knuth: "Duplication = bugs." Ive: "Tray ≠ desk." Vogels: "Never mix control and data planes."

## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-runtime](hub-runtime.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TB
    HUB[Solace Hub<br>Tauri Desktop App<br>5 tabs | GATE not dashboard]

    HUB --> TRAY[System Tray<br>Open Solace Hub | Status | Quit]

    subgraph TABS[Hub Tabs — Control Plane Only]
        TAB_OVERVIEW[Overview<br>LLM gate + Launch Browser + Status]
        TAB_SESSIONS[Sessions<br>See/kill browser sessions]
        TAB_EVENTS[Events<br>Quick feed last 20]
        TAB_REMOTE[Remote<br>Consent form + audit trail]
        TAB_SETTINGS[Settings<br>Version + Auth + LLM + Auto-update]
    end

    HUB --> TAB_OVERVIEW
    HUB --> TAB_SESSIONS
    HUB --> TAB_EVENTS
    HUB --> TAB_REMOTE
    HUB --> TAB_SETTINGS

    HUB --> NAV_LOCAL[Link: Local Dashboard<br>localhost:8888/dashboard]
    HUB --> NAV_CLOUD[Link: Cloud Dashboard<br>solaceagi.com/dashboard]

    subgraph AUTH[Auth States]
        LOGGED_OUT[Not Connected<br>Sign In button visible<br>LLM gate blocks launch]
        LOGGED_IN[Connected<br>Green pill + email<br>Launch enabled]
    end

    classDef gate fill:#e8f5e9,stroke:#2e7d32,color:#111;
    classDef data fill:#e3f2fd,stroke:#1565c0,color:#111;
    classDef nav fill:#fff9c4,stroke:#f9a825,color:#111;
    class TAB_OVERVIEW,TAB_SESSIONS,TAB_EVENTS,TAB_REMOTE,TAB_SETTINGS gate;
    class NAV_LOCAL,NAV_CLOUD nav;
```

## PM Status
<!-- Updated: 2026-03-18 | Session: P-71 | GLOW 602 -->
| Node | Status | Evidence |
|------|--------|----------|
| TAB_OVERVIEW | SEALED | LLM gate (3 sources) + Launch Browser + system status dots |
| TAB_SESSIONS | SEALED | Session table with kill + single/multi mode |
| TAB_EVENTS | SEALED | DataTable events feed, auto-refresh |
| TAB_REMOTE | SEALED | Consent toggle + disconnect + audit trail (GLOW 602) |
| TAB_SETTINGS | SEALED | Version + auto-update + auth + LLM + data dirs (GLOW 602) |
| TRAY | SEALED | Open Solace Hub + Status + Quit (GLOW 592) |
| NAV_LOCAL | SEALED | Green dragon button → localhost:8888/dashboard |
| NAV_CLOUD | SEALED | Blue cloud button → solaceagi.com/dashboard |
| AUTH_LOGGED_OUT | SEALED | "Sign in" button + LLM gate blocks launch |
| AUTH_LOGGED_IN | SEALED | Green "Connected" pill + email (GLOW 602) |
| AUTO_UPDATE | SEALED | Checks GCS hourly, version in settings (GLOW 601) |


## Related Papers
- [papers/hub-three-realms-paper.md](../papers/hub-three-realms-paper.md)

## Forbidden States
```
PORT_9222             → KILL
COMPANION_APP_NAMING  → KILL (use "Solace Hub")
BARE_EXCEPT           → KILL
SILENT_FALLBACK       → KILL
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
