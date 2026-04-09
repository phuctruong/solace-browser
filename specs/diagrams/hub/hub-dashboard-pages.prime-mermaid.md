<!-- Diagram: hub-dashboard-pages -->
# Hub Dashboard Pages — Complete Information Architecture (GLOW 568)
## DNA: `pages = dashboard(overview+workers+apps+backoffice+trust+platform) + domains(hierarchy) + features(flat) + store(marketplace)`
## Auth: 65537 | Committee: Norman · Rams · Hickey · Gregg

```mermaid
flowchart TB
    ROOT[localhost:8888] --> DASH[/dashboard<br>6 tabs: Overview | Workers | Apps | Backoffice | Trust | Platform]
    ROOT --> DOMAINS[/domains<br>Domain list with app counts]
    DOMAINS --> DD[/domains/:domain<br>Apps + Events + Tab + Config]
    DD --> APP[/apps/:app_id<br>Manifest + Runs + Events + Evidence]
    APP --> RUN[/apps/:app_id/runs/:id<br>Event log + chain + report]

    DASH --> DASH_OV[/dashboard#overview<br>Today view + launch + pending + recent events]
    DASH --> DASH_WK[/dashboard#workers<br>AI worker roster + hire + schedules + runs]
    DASH --> DASH_AP[/dashboard#apps<br>Installed apps + domains + recipes + app store]
    DASH --> DASH_BO[/dashboard#backoffice<br>CRM + Messages + Tasks + Docs + Email + Support + Invoicing]
    DASH --> DASH_TR[/dashboard#trust<br>Approvals + evidence + QA + wiki]
    DASH --> DASH_PL[/dashboard#platform<br>LLMs + CLI agents + OAuth3 + budget + settings]

    DASH_BO --> BO[/backoffice<br>Workspace switcher for business apps]
    BO --> BO_APP[/backoffice/:app_id<br>Backoffice workspace]

    ROOT --> STORE[/appstore<br>Installed + Available + Custom]
    ROOT --> LLMS[/llms<br>Agents + BYOK + Managed + Models]
    ROOT --> EVIDENCE[/evidence<br>Hash chain + Part 11 + Export]
    ROOT --> BUDGET[/budget<br>Daily + Monthly + Per-app]
    ROOT --> RECIPES[/recipes<br>Library + History + Create]
    ROOT --> OAUTH3[/oauth3<br>Tokens + Register + Revoke]
    ROOT --> ESIGN[/esign<br>Approvals + Tunnel + History]
    ROOT --> WIKI[/wiki-hub<br>Snapshots + Codecs + Domains]
    ROOT --> SETTINGS[/settings<br>Theme + Cloud + Tunnel + Export]
    ROOT --> SIDEBAR[/sidebar<br>Yinyang in-browser panel]
    ROOT --> STYLE[/styleguide<br>Design system reference]

    classDef home fill:#22c55e,color:#fff
    classDef feature fill:#3b82f6,color:#fff
    classDef hierarchy fill:#f59e0b,color:#111
    classDef meta fill:#6b7280,color:#fff
    class DASH home
    class DASH_OV,DASH_WK,DASH_AP,DASH_BO,DASH_TR,DASH_PL home
    class STORE,LLMS,EVIDENCE,BUDGET,RECIPES,OAUTH3,ESIGN,WIKI,SETTINGS feature
    class DOMAINS,DD,APP,RUN,BO,BO_APP hierarchy
    class SIDEBAR,STYLE meta
```

## PM Status
<!-- Updated: 2026-03-16 | Session: P-70 | GLOW 568 -->
| Page | Status | Evidence |
|------|--------|----------|
| /dashboard | SEALED | 6 tabs: Overview + Workers + Apps + Backoffice + Trust + Platform |
| /dashboard#overview | SEALED | Today view + quick launch + pending approvals + recent events |
| /dashboard#workers | SEALED | Worker roster + hire flow + schedules + recent runs |
| /dashboard#apps | SEALED | Domains + installed apps + recipes + app store shortcuts |
| /dashboard#backoffice | SEALED | Workspace switcher for CRM/messages/tasks/docs/email/support/invoicing |
| /dashboard#trust | SEALED | Signoff + evidence + QA + Prime Wiki trust surfaces |
| /dashboard#platform | SEALED | LLMs + CLI agents + OAuth3 + budget + settings status |
| /domains | SEALED | Domain list with app counts + icons |
| /domains/:domain | SEALED | 4 tabs: Apps + Events + Tab Status + Config |
| /apps/:app_id | SEALED | 4 tabs: Overview + Runs + Evidence + Settings |
| /apps/:app_id/runs/:id | SEALED | Event log + chain badge + report link |
| /backoffice | SEALED | Workspace switcher for all backoffice apps |
| /backoffice/:app_id | SEALED | Generic backoffice app shell powered by schema |
| /appstore | SEALED | 63 installed apps + store link + custom guide |
| /llms | SEALED | Agent detection + BYOK + managed + L1-L5 |
| /budget | SEALED | Daily/monthly bars + fail-closed policy |
| /recipes | SEALED | Library with hit rate + zero-cost explanation |
| /oauth3 | SEALED | Token table + register + revoke |
| /esign | SEALED | Approval queue + tunnel consent + history |
| /wiki-hub | SEALED | Snapshot stats + Stillwater codecs |
| /settings | SEALED | Theme + cloud + tunnel + platform + export |
| /evidence | SEALED | Hash chain + Part 11 + ALCOA |
| /sidebar | SEALED | 4-state gate + chat + domains + events |
| /styleguide | SEALED | Full design system reference |

## Score: 24/24 SEALED (100%) — DASHBOARD IA UPDATED FOR BACKOFFICE + AI WORKERS + TRUST

## Forbidden States
```
PAGE_WITHOUT_DIAGRAM_TAG    → KILL (every page must map to a diagram node)
HARDCODED_ROUTES            → KILL (all routes defined in diagram — single source of truth)
PAGE_WITHOUT_EVIDENCE       → KILL (navigation produces hash-chained evidence)
DUPLICATE_PAGE_PATH         → KILL (each route unique — no aliases or redirects)
ORPHAN_PAGE_NO_NAV          → KILL (every page reachable from dashboard or sidebar)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
