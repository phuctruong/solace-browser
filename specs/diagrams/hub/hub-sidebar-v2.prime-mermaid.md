<!-- Diagram: 08b-sidebar-v2-two-modes -->
# 08b: Yinyang Sidebar v2 — Two-Mode Worker Theater
# DNA: `sidebar = idle(minimal) | worker_running(timeline) | domain_detected(apps); browser = stage, sidebar = narrator`
# Auth: 65537 | State: PENDING | Version: 2.0.0

## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-sidebar-gate](hub-sidebar-gate.prime-mermaid.md) — auth gate (upstream)
- [hub-runtime](hub-runtime.prime-mermaid.md) — parent diagram

## Design Principle

The browser is the stage. AI workers are the actors. The sidebar narrates.
The user watches their AI team work — the wow moment is autonomous browser control
with a live timeline explaining every step.

## Canonical Diagram

```mermaid
stateDiagram-v2
    [*] --> AUTH_GATE

    AUTH_GATE --> LOGGED_OUT: unregistered
    AUTH_GATE --> IDLE: byok | paid | no_llm

    state LOGGED_OUT {
        [*] --> SHOW_DOMAIN_TEASER: domain detected
        [*] --> SHOW_VALUE_PROP: no domain match
        note right of SHOW_DOMAIN_TEASER
            "3 AI workers for gmail.com — sign in to activate"
            Shows value WITHOUT access. Proves DOM awareness.
        end note
        note right of SHOW_VALUE_PROP
            Solace logo + "Your AI team works while you browse"
            Sign in CTA. Minimal. Intriguing.
        end note
    }

    state IDLE {
        [*] --> MINIMAL_STATUS
        MINIMAL_STATUS --> DOMAIN_DETECTED: URL matches installed app domain
        MINIMAL_STATUS --> WORKER_RUNNING: POST /api/v1/apps/run/{id}
        DOMAIN_DETECTED --> WORKER_RUNNING: user clicks [Run Now]
        DOMAIN_DETECTED --> MINIMAL_STATUS: user navigates away
        note right of MINIMAL_STATUS
            Logo + "2 workers scheduled, 0 running"
            Last 3 completed sessions (compact)
            "Set up workers → Dashboard" CTA if new user
        end note
    }

    state DOMAIN_DETECTED {
        [*] --> SHOW_DOMAIN_BAR
        SHOW_DOMAIN_BAR --> SHOW_DOMAIN_APPS
        note right of SHOW_DOMAIN_BAR
            Domain icon + name + "3 apps available" pill
            Sidebar header shifts color to domain brand tint
        end note
        note right of SHOW_DOMAIN_APPS
            App cards with: name, description, schedule, last run
            [Run Now] button per app
            [View Last Run →] link per app
        end note
    }

    state WORKER_RUNNING {
        [*] --> WORKING
        WORKING --> APPROVAL_NEEDED: L3+ action
        APPROVAL_NEEDED --> WORKING: user approves
        APPROVAL_NEEDED --> CANCELLED: user rejects
        WORKING --> DONE: all steps complete
        WORKING --> ERROR: step fails
        WORKING --> CANCELLED: user clicks [Stop]
        DONE --> CELEBRATE
        CELEBRATE --> IDLE: after 30s or user navigates
        ERROR --> IDLE: user dismisses
        CANCELLED --> IDLE: immediate
        note right of WORKING
            Visual: breathing glow border + worker accent color
            Worker name + domain + pulsing "Working..." pill
            Live timeline: timestamped step entries
            Progress: "Step 3 of 7"
            [Stop] button always visible
        end note
        note right of APPROVAL_NEEDED
            Timeline pauses. Breathing changes to "waiting" pulse.
            Highlighted card: action + preview + cost estimate
            [Approve] [Reject] buttons
            L5: [e-Sign] with name + reason + 30s countdown
        end note
        note right of CELEBRATE
            Green flash. Breathing stops.
            "Done! Processed 47 emails in 2m 14s"
            [View Work Session →] opens /apps/{id}/runs/{run-id}
        end note
    }
```

## The Three Sidebar States

### 1. IDLE (default — minimal)
- Solace logo
- Status line: "{n} workers scheduled, {n} running"
- Last 3 completed work sessions (one-line each: worker name + time + result)
- If no workers configured: "Set up your first AI worker → Dashboard"

### 2. DOMAIN_DETECTED (passive — context-aware)
- Domain icon + name at top (visual state change — domain brand tint)
- "{n} apps available" pill
- App cards with [Run Now] + schedule info + last run
- Activated by URL match against installed app domains

### 3. WORKER_RUNNING (active — live theater)
- Full sidebar takeover with breathing glow border
- Worker identity bar: name + icon + domain + "Working..." pill
- Live timeline: timestamped entries for each agent step
- Progress indicator
- [Stop] button
- Approval interrupts inline
- Celebration on completion with [View Work Session →]

## Logged-Out Experience
- Domain-aware teaser: "3 AI workers for {domain} — sign in to activate"
- Generic: "Your AI team works while you browse" + sign in CTA
- Proves DOM superpow without granting access

## Free vs Paid (NO sidebar layout difference)
- Free (BYOK): Workers use user's API key. Cost shown in timeline.
- Starter ($8): Managed LLM. "Powered by Managed LLM" in timeline.
- Pro ($28): + Cloud sync badge on timeline entries.

## PM Status
<!-- Updated: 2026-03-22 | Session: P-75 | GLOW 741-758 -->
| Node | Status | Evidence |
|------|--------|----------|
| AUTH_GATE | SEALED | Rust compute_sidebar_state() — verified P-68, P-75 |
| LOGGED_OUT | SEALED | sidepanel.html: yy-logged-out div with logo, tagline, sign-in CTA. Verified via screenshot P-75. |
| SHOW_DOMAIN_TEASER | SEALED | sidepanel.js: showTeaser() shows "{n} AI workers for {domain}" with icon. |
| SHOW_VALUE_PROP | SEALED | "Your AI team works while you browse" + How Yinyang Works 3-step guide. |
| IDLE | SEALED | sidepanel.html/js: yy-idle div with status line, How Yinyang Works, Today's Schedule, Open Dashboard. Screenshots verified. |
| MINIMAL_STATUS | SEALED | "{n} workers scheduled, 0 running" + clickable → dashboard. Schedule shows past (green "ran") + now marker + upcoming. |
| DOMAIN_DETECTED | SEALED | C++ SolaceTabUrlReporter writes URL file, runtime reads via /api/v1/browser/current-url, sidebar polls every 2s. Gmail/GitHub/Claude/LinkedIn icons + app cards + FOR THIS PAGE badges verified. |
| WORKER_RUNNING | GOOD | sidepanel.html/js: yy-worker div with breathing glow CSS, timeline, stop button, approval area. Worker timeline + done celebration built. Not yet tested with live long-running worker. |
| WORKING | GOOD | Timeline entries via addTimelineEntry(). WebSocket handler for worker_step events. Not yet tested end-to-end with live WebSocket. |
| APPROVAL_NEEDED | GOOD | showApproval() renders inline card with Approve/Reject buttons. Shell class changes to yy-shell--approval. Not tested with real L3+ approval. |
| DONE | GOOD | workerDone() shows celebration card with summary + stats + elapsed time. yy-shell--done CSS class. Not tested with real worker completion. |
| CELEBRATE | GOOD | yy-celebrate div with checkmark icon, summary, stats, "View Work Session" link. 30s auto-return to idle. Link uses navigateMain(). |

## Forbidden States
```
SIDEBAR_AS_DASHBOARD     → KILL (dashboard is at :8888/dashboard)
DOMAIN_NAV_ACCORDION     → KILL (belongs in dashboard, not sidebar)
FULL_EVENT_FEED          → KILL (belongs in dashboard)
WORKER_LIST_IN_SIDEBAR   → KILL (belongs in dashboard)
LANGUAGE_SWITCHER        → KILL (belongs in settings)
ENGINE_CHOOSER           → KILL (belongs at /llms)
XDOTOOL_NAVIGATION       → KILL (use Chromium IPC or C++ APIs, never xdotool)
PKILL_BROWSER            → KILL (navigate never kills browser — destroys sessions)
CHAT_WITHOUT_WORKER      → PENDING (chat is Phase 2 — after worker theater works)
```

## Covered Files
```
html:
  - solace-browser/solace-hub/src/sidepanel.html
  - solace-browser/source/src/chrome/browser/resources/solace/sidepanel.html
js:
  - solace-browser/solace-hub/src/sidepanel.js
css:
  - solace-browser/solace-hub/src/sidepanel.css
rust:
  - solace-browser/solace-runtime/src/routes/sidebar.rs
  - solace-browser/solace-runtime/src/routes/files.rs (sidebar_page)
api:
  - GET /api/v1/sidebar/state
  - GET /api/v1/domains/{domain}/status
  - GET /api/v1/apps/run/{id} (trigger worker)
  - WS /ws/yinyang (live timeline events)
```

## Implementation Phases
- **P0**: Rewrite sidebar HTML — 3 states (idle, domain, worker running)
- **P1**: Wire domain detection (URL monitor → domain match → state change)
- **P2**: Wire worker timeline (WebSocket → live step entries)
- **P3**: Approval interrupts inline
- **P4**: Celebration + work session link
- **P5**: Chat integration (talk to AI about current page)

## Verification
```
ASSERT: Sidebar has exactly 3 states (idle, domain_detected, worker_running)
ASSERT: No domain accordion/navigation in sidebar
ASSERT: No event feed in sidebar (belongs in dashboard)
ASSERT: Worker running state shows live timeline
ASSERT: Domain detected state shows app cards with [Run Now]
ASSERT: Logged-out state shows domain-aware teaser
```
