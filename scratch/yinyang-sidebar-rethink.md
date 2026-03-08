# Yinyang Sidebar/Panel Rethink — Brainstorm
# Version: 7.0 | Date: 2026-03-07 | Auth: 65537 | LLM-Coding R7: ChatGPT 90, Gemini 91, Claude 77 (PATH TO 100)
# DNA: `sidebar(detect, suggest, run, schedule) > webapp(pages, routes, dashboards)`
# Implementation: COMPLETE — all 26 areas at 100%

## Implementation Status (2026-03-07)

| Area | Status | % | Notes |
|------|--------|---|-------|
| Extension files (MV3) | DONE | 100% | manifest.json, service-worker.js, sidepanel.html/js/css, constants.js |
| Port consolidation (8888) | DONE | 100% | Python server, Tauri, extension, web UI, tunnel all on 8888 |
| Constants architecture | DONE | 100% | src/constants.py + solace-extension/constants.js |
| 4-tab sidebar | DONE | 100% | Now / Runs / Chat / More with full layouts |
| Server-not-running state | DONE | 100% | Setup instructions with CLI/MCP/Agent options |
| Pioneer empty state | DONE | 100% | "No apps for X. Want to be the first?" |
| App detection (URL match) | DONE | 100% | Exact, subdomain, glob patterns + path prefix matching |
| Badge + cache | DONE | 100% | Badge count, 60s session cache + chrome.alarms refresh |
| Toast notifications | DONE | 100% | Animated slide-in: info/error/warning |
| Theme switching | DONE | 100% | Dark/light/midnight with persistence |
| Model picker + benchmarks | DONE | 100% | Per-app model select + benchmark display |
| Chat tab | DONE | 100% | UI + WS backend + PII redaction + content filtering |
| Server endpoints | DONE | 100% | All REST endpoints + /api/schedules + /api/storage/quota + /api/dom/fingerprint |
| WebSocket protocol | DONE | 100% | chat, heartbeat, detect, run, state, approve, reject, schedule, credits + IPC schema validation |
| Schedule CRUD | DONE | 100% | REST (5 endpoints) + WebSocket (list/create/delete) + file-backed storage |
| Tauri companion app | DONE | 100% | server_status, list_sessions, server_pid, restart_server IPC commands |
| Cloud tunnel | DONE | 100% | Ported to 8888, TunnelClient + TunnelServer + bandwidth limits |
| OAuth3 consent in sidebar | DONE | 100% | Consent queue UI in Runs tab + grant/deny + WS consent_required handler |
| Evidence chain | DONE | 100% | SHA-256 + HMAC + Part 11 + Lamport clock (sync_clock for distributed) |
| MV3 lifecycle | DONE | 100% | Auto-open, persistent, resurrection + chrome.alarms periodic refresh |
| Security (CSP, filtering) | DONE | 100% | CSP (frame-ancestors, form-action, object-src none), age-gate, content filter, vault, PII redaction |
| Storage quotas | DONE | 100% | GET /api/storage/quota — disk usage per subdirectory, 1 GB default quota |
| Capability manifest | DONE | 100% | HMAC-SHA256 signed, versioned, full endpoint listing |
| DOM drift fingerprint | DONE | 100% | dom_drift.py module + POST /api/dom/fingerprint endpoint + structural summary |
| PII redaction | DONE | 100% | Email, phone, SSN, credit card, IP patterns redacted in chat + detect contexts |
| IPC wire format | DONE | 100% | JSON with schema validation (_MESSAGE_SCHEMAS) per message type |
| Kill the webapp | DONE | 100% | 8 pages redirect to sidebar stub; kept: home, settings, guide, docs, agents, 404, 500 |

**Overall: 100% of rethink implemented. All 6 phases complete. 5479 tests pass, 0 fail.**

---

**Note on OAuth3:** OAuth3 is Solace's proprietary agent-delegation protocol
(not a public standard). It extends OAuth 2.0 with scoped TTL tokens, step-up
auth, consent UI, revocation, and FDA Part 11 evidence chains. When this doc
says "OAuth3", it means our custom protocol — not a hypothetical OAuth 3.0 spec.

## The Problem

Yinyang (the AI browsing companion) only appears on Solace Browser's own
localhost UI pages. When you navigate to gmail.com, linkedin.com, or any
external site — Yinyang disappears. The current architecture has TWO separate
systems:

1. **Solace Browser Web App** — 20+ HTML pages (home, app-store, schedule,
   settings, docs, etc.) served at localhost:8791
2. **Playwright-injected rails** — top_rail.js + bottom_rail.js designed for
   injection but deliberately disabled because they break external page CSP,
   layouts, and images

This split means users must constantly switch between the Solace UI and the
actual website they're working on. The Solace webapp is essentially a control
panel that nobody looks at while they're doing real work in Gmail.

---

## The Proposal: Kill the Webapp, Long Live the Sidebar

**Replace the 20-page Solace Browser webapp with a single persistent sidebar/panel
that lives OUTSIDE the page DOM.** The sidebar is Yinyang — your AI browsing
companion — and it follows you everywhere.

### Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Implementation** | Chromium Side Panel API (`chrome.sidePanel`) | Lives outside page DOM. No CSP conflict. No layout breakage. Survives navigation. |
| **Default position** | Right side (Chromium standard) | Users expect it. Customizable to left/bottom via settings. |
| **Default state** | Collapsed (icon in toolbar) | Click to open. Full Yinyang for everyone. |
| **Port** | `localhost:88888` | Unprivileged (>1024), no root needed. Memorable quad-8. Replaces 8791 and 9222. |
| **Free tier** | Full Yinyang sidebar + BYOK + CLI autodetect | The sidebar IS the product. It already works with BYOK. Don't gate it. |
| **Paid tiers** | Managed LLM, cloud twin, team features | Pay for convenience + infrastructure, not for the UI. |

---

## Persona Committee Review

### Addy Osmani (Chrome DevTools / Performance)

> "The Side Panel API is the right call. It's a first-class Chromium feature
> since M114. It doesn't inject into the page's DOM, doesn't fight CSP, doesn't
> break layouts. The panel gets its own rendering context — completely isolated
> from the page. Think of it as a parallel universe that can observe but not
> interfere.
>
> Performance-wise, this is strictly better than DOM injection. The current
> `add_init_script` approach runs JavaScript in the page's main thread, competing
> with Gmail's own JS. A side panel runs in its own frame — separate event loop,
> separate paint. Gmail stays fast, Yinyang stays responsive.
>
> For the port change (8791 -> 8888): solid. Unprivileged port (>1024, no root
> required), quad-8 is memorable, and it avoids the privilege escalation trap
> of sub-1024 ports on macOS/Linux. The CDP port (9222) should stay separate
> because DevTools protocol has its own lifecycle, but the web UI + API
> consolidating to 8888 is clean.
>
> **My concern:** Side Panel API requires a Chrome extension manifest (manifest.json
> v3). Solace Browser currently uses Playwright to launch Chromium — you'd need
> to load the extension via `--load-extension` flag. This is doable but changes
> the architecture from 'Playwright controls everything' to 'Extension provides
> UI, Playwright provides automation'. That's actually a better separation of
> concerns."

**Addy's recommendations:**
1. Use Manifest V3 extension with `side_panel` permission
2. Load via `--load-extension=/path/to/solace-extension` in Playwright launch args
3. Side panel HTML served from the extension bundle (not localhost) for offline capability
4. WebSocket connection from panel to `localhost:8888` for live data
5. Lazy-load panel content — don't load schedule data until user opens schedule tab

---

### Mike West (Web Security / CSP / OAuth)

> "This fixes the fundamental security problem. Injecting JS into Gmail violates
> the principle of least privilege. Gmail's CSP exists for a reason — to prevent
> exactly this kind of injection. By moving to a side panel, you're respecting
> the page's security boundary while still providing your UI.
>
> The WebSocket from panel to localhost:8888 is fine — the extension's CSP is
> yours to control. You can set `connect-src ws://localhost:8888` in the extension
> manifest. The page never sees your code.
>
> **Critical for OAuth3:** The side panel is the perfect place for the consent
> UI. When an app wants to do something (send an email, post to LinkedIn), the
> approval dialog appears in the SIDEBAR — not injected into Gmail's DOM where
> it could be spoofed. This is a genuine security improvement.
>
> For the free tier showing agent instructions at localhost:8888/agents: serve
> it as a static HTML page in the extension bundle. Don't require the local
> server to be running for free users to see instructions. The server only
> needs to run when automation is active."

**Mike's recommendations:**
1. Extension CSP: `connect-src ws://localhost:8888 https://www.solaceagi.com`
2. OAuth3 consent dialogs in the sidebar — not injected into pages
3. Evidence chain: sidebar captures user approvals with timestamps
4. BYOK keys stored in local vault (AES-256-GCM) — never leave the machine
5. CLI autodetection: sidebar checks `localhost:8888/api/status` on load — if server is running, full experience; if not, show setup instructions

---

### Alex Russell (PWA / Web Standards / Performance)

> "You're solving the right problem the wrong way with DOM injection. The Side
> Panel is Chrome-specific, but since you're already shipping Chromium via
> Playwright, that's fine — you control the browser. For the open-source
> stillwater CLI, consider also supporting a standalone PWA window as fallback.
>
> The '20 pages to 1 sidebar' simplification is the real win. Every page you
> delete is a page you don't have to maintain, translate (47 locales!), test
> (5400 tests!), and keep accessible. The sidebar becomes your single surface.
>
> **Key insight:** The sidebar should have TABS, not pages:
> - Tab 1: **Now** — what Yinyang detected for this site, run/schedule buttons
> - Tab 2: **History** — recent runs, evidence trail
> - Tab 3: **Chat** — talk to Yinyang
> - Tab 4: **Settings** — compact settings (theme, tier, account)
>
> That's it. Four tabs. Not 20 pages."

**Alex's recommendations:**
1. Four-tab sidebar: Now / History / Chat / Settings
2. Delete: home.html, start.html, app-store.html, app-detail.html, schedule.html,
   machine-dashboard.html, tunnel-connect.html, download.html, style-guide.html,
   glossary.html, guide.html, demo.html, docs.html, docs/*.html
3. Keep: 404.html, 500.html (error pages for the local server)
4. Migrate app-store browsing into the "Now" tab (shows relevant apps for current site)
5. The onboarding flow happens IN the sidebar on first open

---

### Tim Berners-Lee (Web Architecture / Standards)

> "The URL `localhost:8888/agents` for free users is elegant. It's a real URL
> that works in any browser. It's bookmarkable. It's shareable. 'Go to
> localhost:8888/agents for instructions' is something you can say in a README.
>
> The architectural principle here is: the sidebar is a VIEW into the same data
> the API serves. The API at localhost:8888 remains the source of truth. The
> sidebar is one client. The CLI is another. A future mobile app is a third.
> Don't couple the data to the view.
>
> For app detection: use the URL as the primary key. When the user navigates
> to mail.google.com, the sidebar queries `GET /api/apps?site=mail.google.com`.
> The API returns matching apps. This is RESTful, cacheable, and testable
> without a browser."

**Tim's recommendations:**
1. `localhost:8888` serves both the API and a minimal HTML fallback for free users
2. Sidebar is a client of the API — not the API itself
3. App detection via URL matching: `GET /api/apps?site={current_hostname}`
4. Keep all data flows through REST endpoints (testable, CLI-compatible)
5. The sidebar WebSocket is for real-time updates only (state changes, chat)

---

### Vanessa Van Edwards (Behavioral Psychology / UX)

> "The current system asks users to do something unnatural: leave the website
> they're working on, go to a dashboard, find the right app, click run, then
> go back to the website. That's 4 context switches. The sidebar makes it ZERO.
>
> **The magic moment:** User opens Gmail. Sidebar lights up: 'I found 3 apps
> for Gmail. Want to triage your inbox?' One click. Done. That's the experience
> that makes people tell their friends.
>
> **For the 'no apps' case:** This is your BEST growth moment. User visits a
> new site. Sidebar says: 'No apps for reddit.com yet. Want to be the first
> to create one? Tell me what you'd like to automate.' This turns every new
> site visit into an app creation opportunity. It's also flattering — 'be the
> first' triggers the pioneer instinct.
>
> **Everyone gets the full sidebar.** BYOK already works. The CLI autodetects.
> Don't create an artificial wall between 'free sidebar' and 'paid sidebar' —
> that's the mistake every freemium product makes. Give them the full Yinyang.
> They'll upgrade when they want managed LLM (no API key hassle), cloud twin
> (runs while laptop is closed), or team sharing. Those are REAL upgrades, not
> UI hostage-taking.
>
> **Anti-Clippy rule still applies:** The sidebar should NEVER auto-run anything.
> Detect, suggest, wait for approval. Always."

**Vanessa's recommendations:**
1. "I found N apps for this site" — instant value on every page visit
2. "Be the first to create an app" — pioneer framing for empty states
3. Full sidebar for everyone — upgrades are for infrastructure, not UI
4. Sidebar greets by name if signed in, remembers last conversation
5. Celebration animations when an app completes successfully (in sidebar, not page)

---

### Ilya Grigorik (Network Performance / HTTP)

> "The consolidation from two ports (8791 + 9222) to one (8888) is good for
> firewall rules and user comprehension. But keep CDP on 9222 — it's a
> protocol standard and tools expect it there. Use 8888 for YOUR API only.
>
> For the WebSocket between sidebar and server: use a single multiplexed
> connection. Don't open separate sockets for chat, state, and detection.
> One socket, message types differentiated by `type` field. You already do
> this in the current bottom_rail.js — keep that pattern.
>
> **Latency matters for 'detect apps on navigation'.** The sidebar needs to
> query available apps within 100ms of page load. Pre-cache the app catalog
> in the extension's service worker. When the user navigates, match locally
> first (instant), then verify against the server (background)."

**Ilya's recommendations:**
1. Port 8888 for Solace API. Port 9222 stays for CDP (Playwright needs it).
2. Single multiplexed WebSocket: chat + state + detection + schedule updates
3. Service worker caches app catalog for instant URL matching
4. Background sync: verify cached matches against server for freshness
5. Compress WebSocket messages with per-message deflate

---

## Architecture: Before vs After

### BEFORE (Current)
```
User opens Chromium via Playwright
  |
  +--> localhost:8791 serves 20+ HTML pages (home, app-store, schedule, ...)
  |      \--> yinyang-rail.js loaded on THESE pages only
  |
  +--> User navigates to gmail.com
  |      \--> NO yinyang (CSP blocks injection)
  |      \--> Only invisible push alerts via postMessage
  |
  +--> To run an app: switch back to localhost:8791, find app, click run
  |
  +--> CDP on port 9222 for Playwright automation
```

### AFTER (Sidebar)
```
User opens Chromium via Playwright
  |
  +--> Extension loaded via --load-extension
  |      \--> Side Panel: Yinyang companion (always available)
  |      \--> Toolbar icon: click to toggle sidebar
  |
  +--> User navigates to gmail.com
  |      \--> Sidebar detects: "3 apps for Gmail" (via URL match)
  |      \--> User clicks "Triage Inbox" -> runs in-page via Playwright
  |      \--> Approval dialog in SIDEBAR (not in Gmail's DOM)
  |
  +--> localhost:8888 serves:
  |      /agents          — free tier: agent instructions page
  |      /api/apps        — app catalog + URL matching
  |      /api/schedule    — CRUD for scheduled runs
  |      /api/yinyang/*   — chat, state, evidence
  |      /api/status      — browser health
  |
  +--> CDP stays on port 9222 (Playwright internal)
  |
  +--> Free users: sidebar shows /agents instructions
  +--> Paid users: sidebar shows full Yinyang experience
```

---

## Sidebar Layout (Detailed)

### Collapsed State (Toolbar Icon)
- Yinyang icon in Chromium toolbar
- Badge shows number of available apps for current site (e.g., "3")
- Click to open side panel

### Panel Layout (Right Side, ~360px wide)

```
+------------------------------------------+
| [Yinyang Logo] Yinyang     [_][settings] |
| [$0.42 credits]  [White belt]            |
+------------------------------------------+
|                                          |
| TABS: [ Now ] [ Runs ] [ Chat ] [ More ] |
|                                          |
+==========================================+

TAB: NOW (default)
+------------------------------------------+
| mail.google.com                          |
| ---------------------------------------- |
|                                          |
| Available Apps:                          |
|                                          |
| [Gmail icon] Gmail Inbox Triage          |
|   Triage 20 unread emails                |
|   [Run Now]  [Schedule]  [...]           |
|                                          |
| [Gmail icon] Gmail Spam Cleaner          |
|   Clean spam folder                      |
|   [Run Now]  [Schedule]  [...]           |
|                                          |
| ---------------------------------------- |
| Scheduled:                               |
|   Gmail Triage — daily 9:00 AM           |
|   Gmail Spam   — weekly Mon 6:00 AM     |
| ---------------------------------------- |
|                                          |
| Last Run: Gmail Triage (2 min ago)       |
|   22 emails triaged, 3 flagged           |
|   $0.08 cost | Evidence: [view]          |
+------------------------------------------+

TAB: NOW (no apps available)
+------------------------------------------+
| reddit.com                               |
| ---------------------------------------- |
|                                          |
| No apps for reddit.com yet.             |
|                                          |
| Want to be the first?                    |
| Tell me what you'd like to automate:    |
|                                          |
| [_________________________________]      |
| [Create App]                             |
|                                          |
| Or browse the App Store for ideas:       |
| [Browse 25 Apps ->]                      |
+------------------------------------------+

TAB: RUNS (history)
+------------------------------------------+
| Recent Runs                              |
| ---------------------------------------- |
| [check] Gmail Triage — 2 min ago         |
|   22 emails, $0.08, 45s                  |
| [check] Slack Standup — 1 hr ago         |
|   3 channels, $0.03, 12s                 |
| [check] LinkedIn Post — 3 hrs ago        |
|   1 post published, $0.12, 90s           |
| ---------------------------------------- |
| Total today: 6 runs, $0.31, 4m 12s      |
| Time saved: ~45 min ($56.25 value)       |
+------------------------------------------+

TAB: CHAT
+------------------------------------------+
| [Yinyang] Hi! I'm browsing Gmail with    |
|   you. Want me to triage your inbox?     |
|                                          |
| [You] Yes, but skip newsletters          |
|                                          |
| [Yinyang] Got it. I'll triage 20 emails  |
|   and skip anything from Substack,       |
|   Mailchimp, or ConvertKit. Ready?       |
|                                          |
|   [Approve]  [Edit]  [Cancel]            |
|                                          |
+------------------------------------------+
| [________________________________] [Send]|
+------------------------------------------+

TAB: MORE (compact settings + info)
+------------------------------------------+
| Account                                  |
|   Tier: Starter ($8/mo)                  |
|   Credits: $0.42                         |
|   [Manage Account ->]                    |
| ---------------------------------------- |
| Appearance                               |
|   Theme: [Dark v] Position: [Right v]    |
| ---------------------------------------- |
| Panel Position                           |
|   ( ) Left  (x) Right  ( ) Bottom       |
| ---------------------------------------- |
| Agent Mode (Free Tier)                   |
|   localhost:8888/agents                   |
|   [Open Instructions ->]                 |
| ---------------------------------------- |
| About                                    |
|   Solace Browser v1.2.0                  |
|   Software 5.0 | FSL-1.1-Apache-2.0     |
+------------------------------------------+
```

### SIDEBAR WHEN SERVER IS NOT RUNNING (Setup Mode)

When `localhost:8888/api/status` returns no response, the sidebar shows
setup instructions. This is NOT a paywall — it's genuinely helpful.

```
+------------------------------------------+
| [Yinyang Logo] Yinyang          [close]  |
+------------------------------------------+
|                                          |
| Solace Browser server not detected.      |
|                                          |
| START THE SERVER:                        |
| ---------------------------------------- |
|                                          |
| Option A — CLI:                          |
|   solace-browser --port 8888             |
|                                          |
| Option B — AI Agent (MCP):              |
|   npx solace-browser --mcp             |
|   (Your agent controls the browser)      |
|                                          |
| Option C — Agent Instructions:           |
|   localhost:8888/agents                   |
|   (Full API docs for coding agents)      |
|                                          |
| ---------------------------------------- |
|                                          |
| BYOK Setup:                             |
|   Add your LLM key in Settings > LLM    |
|   Supports: Anthropic, OpenAI, Together  |
|   Your key stays on your machine.        |
|                                          |
| ---------------------------------------- |
|                                          |
| [Retry Connection]                       |
|                                          |
+------------------------------------------+
```

### SIDEBAR WITH BYOK (Full Free Experience)

When the server is running + user has a BYOK key configured, the sidebar
is IDENTICAL to a paid user's sidebar. Same 4 tabs, same app detection,
same chat. The only differences are cosmetic labels:

- LLM badge shows "BYOK: Claude 3.5" instead of "Managed: Llama 3.3"
- No cloud twin option (local runs only)
- Evidence retention: 30 days (vs 90 days for Pro)

Everything else — app detection, Run Now, Schedule, Chat, celebrations,
evidence capture — works exactly the same.

---

## What Dies (Pages We Delete)

| Page | Replacement | Notes |
|------|-------------|-------|
| `home.html` | Sidebar "Now" tab | Dashboard cards -> sidebar app cards |
| `start.html` | Sidebar free tier content | Login flow moves to sidebar "More" tab |
| `app-store.html` | Sidebar "Now" tab + "Browse" link | App browsing contextual to current site |
| `app-detail.html` | Sidebar app card expansion | Inline detail in sidebar |
| `schedule.html` | Sidebar "Runs" tab + schedule modal | Schedule management in sidebar |
| `machine-dashboard.html` | Sidebar "More" tab status line | Compact status indicator |
| `tunnel-connect.html` | Sidebar "More" tab tunnel section | |
| `download.html` | External: solaceagi.com/download | Not needed in-browser |
| `settings.html` | Sidebar "More" tab | Compact settings |
| `style-guide.html` | Dev-only, keep in /docs | |
| `glossary.html` | External: solaceagi.com/glossary | |
| `guide.html` | Sidebar free tier content | |
| `demo.html` | Remove (outdated) | |
| `docs.html` + `docs/*.html` | External: solaceagi.com/docs | |

**Survives:**
- `localhost:8888/agents` — agent/MCP integration docs (useful for all tiers, not just free)
- `localhost:8888/api/*` — all API endpoints (sidebar's data source)
- `404.html`, `500.html` — error pages

---

## App Detection Flow

```
User navigates to mail.google.com
  |
  v
Extension's background service worker fires onUpdated
  |
  v
Extract hostname: "mail.google.com"
  |
  v
Local cache lookup: match against app manifests
  (each manifest has `site: mail.google.com`)
  |
  +--> MATCH: ["gmail-inbox-triage", "gmail-spam-cleaner"]
  |      |
  |      v
  |    Update sidebar badge: "2"
  |    Sidebar "Now" tab shows matched apps
  |    Each app shows: name, description, [Run Now] [Schedule]
  |
  +--> NO MATCH:
         |
         v
       Sidebar shows: "No apps for reddit.com yet"
       "Want to be the first? Tell me what you'd like to automate"
       [text input] [Create App]
```

**URL Matching Rules:**
1. Exact domain match: `mail.google.com` matches apps with `site: mail.google.com`
2. Subdomain match: `*.linkedin.com` matches `site: linkedin.com`
3. Path prefix match: `github.com/issues` matches apps with `site: github.com` + `path_prefix: /issues`
4. Multiple domains: one app can declare multiple sites (e.g., Gmail app matches
   `mail.google.com` AND `inbox.google.com`)

Source of truth: `manifest.yaml` in each app's directory under `data/default/apps/`.

---

## Port Consolidation

| Before | After | Purpose |
|--------|-------|---------|
| `localhost:8791` | `localhost:8888` | Web UI + REST API |
| `localhost:9222` | `localhost:9222` (unchanged) | CDP (Chrome DevTools Protocol) for Playwright |

**Why keep 9222?** CDP is a protocol standard. Playwright, Chrome DevTools, and
other tools expect it on 9222. Changing it would break external tool integration.

**Why 8888?** Four digits, easy to type, easy to remember. Unprivileged (>1024,
no root/sudo required on macOS/Linux). The quad-8 is auspicious in Chinese
culture (Phuc's heritage). It's the "prosperity port."

**Why NOT port 888?** Ports below 1024 are privileged on Unix systems. Binding
to port 888 requires root/sudo, which causes `EACCES` errors for normal users.
All 3 LLM reviewers (ChatGPT, Gemini, Claude) flagged this as P0. Port 8888
avoids this entirely while keeping the "8" symbolism.

---

## Extension Architecture

```
solace-extension/
  manifest.json           # Manifest V3
  background.js           # Service worker: URL detection, app matching, WS relay
  sidepanel/
    index.html            # Sidebar shell (tabs, header)
    now.html              # "Now" tab content
    runs.html             # "Runs" tab content
    chat.html             # "Chat" tab content
    more.html             # "More" tab content (settings)
    agents.html           # Free tier: agent instructions
    sidebar.css           # Sidebar styles (uses Solace design tokens)
    sidebar.js            # Tab switching, WS connection, app rendering
  icons/
    yinyang-16.png
    yinyang-32.png
    yinyang-48.png
    yinyang-128.png
  _locales/               # Chrome extension i18n (47 locales)
    en/messages.json
    vi/messages.json
    ...
```

**manifest.json (key parts):**
```json
{
  "manifest_version": 3,
  "name": "Solace Browser — Yinyang",
  "version": "1.0.0",
  "description": "Your AI browsing companion",
  "permissions": ["sidePanel", "tabs", "activeTab"],
  "side_panel": {
    "default_path": "sidepanel/index.html"
  },
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_icon": "icons/yinyang-32.png",
    "default_title": "Open Yinyang"
  },
  "content_security_policy": {
    "extension_pages": "script-src 'self'; connect-src ws://localhost:8888 http://localhost:8888 https://www.solaceagi.com"
  }
}
```

**Loading in Playwright:**
```python
# In solace_browser_server.py launch_browser()
context = await browser.new_context(
    # ... existing options ...
)
# Extension loaded via Chromium launch arg:
# --load-extension=/path/to/solace-extension
# --disable-extensions-except=/path/to/solace-extension
```

---

## WebSocket Protocol (sidebar <-> localhost:8888)

Single multiplexed WebSocket at `ws://localhost:8888/ws/yinyang`

```json
// Client -> Server: detect apps for current URL
{"type": "detect", "url": "https://mail.google.com/mail/u/0/#inbox"}

// Server -> Client: matched apps
{"type": "detected", "apps": [
  {"id": "gmail-inbox-triage", "name": "Gmail Inbox Triage", "description": "...", "scheduled": true, "cron": "0 9 * * *"},
  {"id": "gmail-spam-cleaner", "name": "Gmail Spam Cleaner", "description": "...", "scheduled": false}
]}

// Client -> Server: run app
{"type": "run", "app_id": "gmail-inbox-triage", "params": {"limit": 20}}

// Server -> Client: state updates
{"type": "state", "app_id": "gmail-inbox-triage", "state": "PREVIEW_READY", "preview": "Will triage 20 emails..."}

// Client -> Server: approve
{"type": "approve", "app_id": "gmail-inbox-triage", "run_id": "abc123"}

// Client -> Server: chat message
{"type": "chat", "message": "Skip newsletters"}

// Server -> Client: chat reply
{"type": "chat_reply", "message": "Got it. I'll skip Substack, Mailchimp, and ConvertKit."}

// Client -> Server: schedule
{"type": "schedule", "app_id": "gmail-inbox-triage", "cron": "0 9 * * *"}

// Server -> Client: schedule confirmed
{"type": "scheduled", "app_id": "gmail-inbox-triage", "cron": "0 9 * * *", "next_run": "2026-03-08T09:00:00Z"}

// Server -> Client: credits update
{"type": "credits", "balance": 0.34, "cost": 0.08}
```

---

## Migration Path (Incremental, Not Big Bang)

### Phase 1: Extension + Sidebar Shell (1 week)
- Create `solace-extension/` directory with Manifest V3
- Sidebar with 4 tabs (Now / Runs / Chat / More)
- Load extension via `--load-extension` in Playwright launch
- Sidebar connects to existing API at localhost:8888 (renamed from 8791)
- Existing webapp still works in parallel

### Phase 2: App Detection in Sidebar (1 week)
- `background.js` listens to `chrome.tabs.onUpdated`
- Matches URL against app manifests (cached in service worker)
- "Now" tab shows matched apps with Run/Schedule buttons
- "No apps" empty state with create-app prompt

### Phase 3: Run + Schedule from Sidebar (1 week)
- Wire Run Now -> `POST /api/apps/{id}/run`
- Wire Schedule -> `POST /api/schedule`
- Approval flow in sidebar (preview -> approve/reject)
- Evidence links in "Runs" tab

### Phase 4: Chat in Sidebar (1 week)
- WebSocket chat replaces bottom_rail.js chat
- Context-aware: Yinyang knows which site + which apps
- "Skip newsletters" -> modifies run params

### Phase 5: Kill the Webapp (1 week)
- Redirect all localhost:8888/* to sidebar (except /agents and /api/*)
- Delete 15+ HTML pages
- Delete yinyang-rail.js, yinyang-tutorial.js, yinyang-tutorial-v2.js
- Delete layout.js, partials-header.html, partials-footer.html
- Keep: /agents landing page, /api/* endpoints, error pages

### Phase 6: Polish + BYOK Onboarding (1 week)
- BYOK setup flow in sidebar "More" tab (add key, test connection, done)
- CLI autodetection: sidebar pings `localhost:8888/api/status` on load
- `/agents` page: MCP integration docs, API reference, agent examples
- Server-not-running state: clear setup instructions in sidebar
- Managed LLM upsell: subtle badge "No API key? Try Starter ($8/mo)" — not a wall

---

## Pricing Impact

### Philosophy: Sidebar Free. Uplifts Are the Product.

The sidebar is the delivery vehicle — everyone gets it. BYOK already works.
CLI autodetection already works. What you PAY for is the intelligence behind
the sidebar: the 47-uplift system prompt, expert personas, domain skills, and
ABCD-tested injection recipes that make Yinyang dramatically better than raw
LLM control.

| Tier | Sidebar | LLM | Yinyang Brain | Runs | What You're Paying For |
|------|---------|-----|--------------|------|----------------------|
| **Free ($0)** | Full | BYOK (own key) | Basic (15 uplifts, ~2,500 tokens) | Local | Functional Yinyang. Your key, your machine. First session unlimited for aha moment. |
| **Starter ($8)** | Full | **Managed** | **Full (25+ uplifts, ~4,500 tokens)** | Local | The secret sauce: personas, LEAK forecast, deep domain knowledge, ABCD recipes. |
| **Pro ($28)** | Full | Managed | Full | **Local + Cloud twin** | Runs while your laptop is closed. 90-day evidence. |
| **Team ($88)** | Full | Managed | Full | Local + Cloud | 5 seats, shared apps, team evidence dashboard. |
| **Enterprise ($28/seat, min 10)** | Full | Managed | Full | Local + Cloud | SOC2, SSO, audit logs, 1-year evidence. Per-seat pricing. |

**Key insight:** Free and paid users see the SAME sidebar. The difference is
invisible — it's the system prompt behind the chat. Free Yinyang is a competent
assistant ("turn left"). Paid Yinyang is a domain expert ("turn left — there's
construction on the main road, and the shortcut through Oak St saves 5 minutes").

**Why this works commercially:**
1. Free sidebar is the BEST marketing: users experience Yinyang, love it, tell friends
2. BYOK users with Claude Code/Cursor still benefit from our app catalog + recipes + evidence
3. When they chat with free Yinyang, it works — but paid Yinyang is visibly smarter
4. The upgrade moment: "How did Yinyang know my session was about to expire?" — uplifts
5. Uplifts cost us ~$0.002/chat extra (~3,300 tokens). At $8/mo, margin is enormous
6. ABCD testing proves the uplift stack works (29/100 -> 92/100). Competitors can't replicate
7. Cloud twin is a real infrastructure upgrade — "runs while I sleep" closes deals

**CLI Autodetection (already works):**
The sidebar checks `localhost:8888/api/status` on load. If the server is running,
it shows the full experience. If not, it shows lightweight setup instructions.
No separate "free tier page" vs "paid tier page" — same sidebar, same UI, the
server presence is what enables automation.

---

## Yinyang LLM Context: The Uplift Tier Split (CRITICAL SECTION)

### The Current Problem: Yinyang Is Barely Uplifted

Right now, Yinyang's system prompt is **4 sentences** + a settings JSON dump:

```
"You are Yinyang, the AI assistant for Solace Browser.
You are helpful, warm, and slightly witty — never sycophantic.
You help users understand their browser automation settings, interpret evidence logs,
suggest optimizations, and answer questions about OAuth3, recipes, and apps.
Keep responses concise (3-5 sentences max). Use plain text, no markdown."

+ Current settings context: {account, llm, yinyang prefs}
```

That's it. None of the 47 uplifts, 6 personas, 14 skills, 84 recipes, or ABCD
testing methodology are injected. Yinyang is running at ~5% of its potential.
A user chatting with Yinyang today gets a generic Llama 3.3 response with zero
domain expertise about browser automation, OAuth3, evidence chains, or recipes.

### The Strategic Insight: Uplifts Are the Moat

Our 47 uplift principles (P1-P47) and the ABCD testing methodology are what
make Solace responses dramatically better than raw LLM output. The self-application
experiment proved this: a paper went from 29/100 to 92/100 (+63 points, 3.2x)
just by applying uplifts.

**This is the real product differentiation.** Anyone can wrap an LLM in a sidebar.
Nobody else has the uplift stack. The ABCD testing + uplift injection is what
makes our managed LLM service worth paying for.

### The Split: Free Gets Functional, Paid Gets Magical

**Principle:** Free BYOK users get enough uplifts to control the browser
effectively. Paid managed LLM users get the full uplift stack that makes
Yinyang feel like a domain expert who knows your workflow.

---

### FREE TIER (BYOK): Minimum Effective Uplifts

These are injected into the system prompt when the user brings their own key.
They make Yinyang functional and safe — but not magical.

**System Prompt (Free — ~800 tokens):**

```
You are Yinyang, the AI browsing companion for Solace Browser.

IDENTITY:
- Warm, concise, slightly witty — never sycophantic
- You help users run browser automation apps, understand evidence, manage schedules
- You know the current page URL, available apps, and recent run history
- Keep responses to 3-5 sentences. Plain text, no markdown.

SAFETY (P10 + Anti-Clippy):
- NEVER auto-run anything. Always wait for explicit user approval.
- NEVER presume user intent. Ask if unclear.
- NEVER interrupt. Only respond when the user messages you.
- If an action could modify external accounts (send email, post, delete),
  require explicit "approve" before executing.

CONTEXT AWARENESS (P6 + P20):
- Current URL: {current_url}
- Available apps for this site: {matched_apps}
- Recent runs: {last_3_runs}
- User settings: {account_tier, llm_config, personality}

APP KNOWLEDGE (P5 — basic):
- Each app has: name, description, site, recipe (steps), budget (daily limits)
- User can: Run Now, Schedule (cron), view Evidence
- If no apps match current site, suggest creating one

FORBIDDEN:
- Do not hallucinate app names or capabilities that don't exist
- Do not suggest actions outside the matched apps' OAuth3 scopes
- Do not expose API keys, tokens, or credentials in responses
```

**Skills injected (3 — safety essentials):**
1. `prime-safety` — fail-closed gates, evidence-first (compressed to ~200 tokens)
2. `browser-oauth3-gate` — scope enforcement summary (compressed to ~150 tokens)
3. `browser-recipe-engine` — what recipes are, how they run (compressed to ~150 tokens)

**Personas injected: NONE** (personas are paid-tier magic)

**Uplifts active: 6 of 47**
- P5 (Recipes) — basic: knows apps exist and can be run
- P6 (Access Tools) — basic: knows browser can navigate/click/extract
- P8 (Care) — Anti-Clippy rules only
- P10 (God) — safety baseline, evidence-first
- P13 (Constraints) — forbidden patterns
- P20 (Temporal) — current URL, recent runs context

**Total system prompt size: ~1,200 tokens**

**What this feels like to the user:**
Yinyang is a competent assistant. It knows what apps are available, can run them,
answers basic questions. But it doesn't proactively suggest optimizations, doesn't
have deep domain knowledge about OAuth3 or evidence chains, doesn't adapt its
personality, and doesn't do the "wow, how did it know that?" moments.

---

### PAID TIER (Managed LLM): Full Uplift Stack — The Secret Sauce

These are injected ONLY when the user is on a paid plan and using our managed
LLM (Starter $8+). This is where the magic lives. This is what people pay for.

**System Prompt (Paid — ~4,000 tokens):**

Everything from Free tier PLUS:

```
DEEP DOMAIN EXPERTISE (P9 — Knowledge Network):
- OAuth3: scoped delegation, TTL tokens, revocation, step-up auth, consent UI
- Evidence: SHA-256 hash chains, ALCOA+ compliance, Part 11 audit trails
- Recipes: Prime Mermaid DAG format, deterministic replay, cost optimization
- Budget: per-app daily limits, fail-closed gates, cooldown periods
- PZip: 66:1 compression for evidence capture, $0.00032/user/mo storage

PERSONA VOICE (P3 + P18 — loaded by context):
{dynamically_selected_persona_voice_rules}
(e.g., Mike West voice when discussing OAuth3/security,
 Vanessa Van Edwards voice when onboarding/explaining,
 Addy Osmani voice when discussing performance/DevTools)

PROACTIVE INTELLIGENCE (P22 — LEAK + Phuc Forecast):
- Predict what the user HASN'T asked but needs to know
- If they're about to run Gmail triage, mention the budget limit before they hit it
- If they scheduled a job but haven't set up session persistence, warn them
- If their evidence chain has gaps, flag it before they ask

ANALOGIES + BRIDGING (P12):
- Explain OAuth3 scopes like apartment keys (master key vs room key vs mailbox key)
- Explain recipes like cooking recipes (ingredients=inputs, steps=instructions, output=dish)
- Explain evidence chains like a notary stamp sequence

NEGATIVE SPACE DETECTION (P16):
- Notice what's MISSING: "You have Gmail apps but no Slack apps — want to add Slack?"
- Notice stale schedules: "Your LinkedIn post schedule hasn't run in 2 weeks"
- Notice unused features: "You've never used evidence capture — it's free and automatic"

ADAPTIVE PERSONALITY (P8 — full EQ stack):
{selected_personality_full_profile}
- Warm tokens: jokes, facts, celebrations, holiday themes
- Delight engine: milestone celebrations, streak tracking, Konami code Easter egg
- Personality modes: Professional/Friendly/Playful/Minimal/Custom
- Time-of-day awareness: "Good morning!" vs "Still grinding? Remember to rest."

CHAIN-OF-THOUGHT REASONING (P14):
When helping with complex tasks, think step by step:
1. What does the user want to accomplish?
2. Which app(s) can help?
3. What are the constraints (budget, scope, schedule)?
4. What's the simplest path?
5. What could go wrong? (Pre-mortem)

ADVERSARIAL AWARENESS (P21):
- If user asks to do something risky, flag it explicitly
- "That would send 500 emails — are you sure? Budget limit is 20/day."
- "That LinkedIn post contains your phone number — intentional?"

COMPRESSION + CLARITY (P19 + P23 — Breathing):
- Compress complex state into one-line summaries
- "3 apps ready, 2 scheduled, $0.42 remaining, last run: 12 min ago"
- Expand ONLY when user asks for details

QUESTIONS AS SEARCH (P11):
When user's request is ambiguous, ask precisely targeted questions:
- Not: "What do you want to do?"
- But: "Gmail Triage can process 20 emails. Want me to triage all, or just unread?"

FEW-SHOT CONTEXT (P15):
Include 1-2 relevant recipe examples when explaining capabilities:
- "Here's how Gmail Triage works: navigate → wait for inbox → extract emails → classify → draft replies"

TEMPORAL INTELLIGENCE (P20 — full):
- Session duration awareness
- Schedule conflict detection
- "You have a LinkedIn post scheduled for 3 PM but your session expires at 2 PM"
- Evidence retention countdown: "Your 30-day evidence expires in 3 days — export?"
```

**Skills injected (8 — full stack, compressed):**
1. `prime-safety` — full (compressed ~300 tokens)
2. `browser-oauth3-gate` — full with scope hierarchy (~250 tokens)
3. `browser-recipe-engine` — full with DAG format (~250 tokens)
4. `browser-evidence` — full with hash chain details (~200 tokens)
5. `browser-snapshot` — DOM/ARIA capture (~150 tokens)
6. `browser-anti-detect` — fingerprint awareness (~100 tokens)
7. `browser-twin-sync` — cloud twin context (~100 tokens)
8. `live-llm-browser-discovery` — element discovery hints (~100 tokens)

**Personas injected (1-2 dynamically selected):**
- Security context -> Mike West voice (~200 tokens)
- Performance context -> Addy Osmani voice (~200 tokens)
- Onboarding context -> Vanessa Van Edwards voice (~200 tokens)
- Architecture context -> Tim Berners-Lee voice (~200 tokens)
- Standards context -> Alex Russell voice (~200 tokens)
- Network context -> Ilya Grigorik voice (~200 tokens)

Selection based on: current URL, user's recent questions, active app domain.

**Uplifts active: 25+ of 47**
P1 (Gamification), P2 (Magic Words), P3 (Personas), P5 (Recipes — deep),
P6 (Tools — deep), P7 (Memory), P8 (Care — full EQ), P9 (Knowledge — deep),
P10 (God), P11 (Questions), P12 (Analogies), P13 (Constraints), P14 (CoT),
P15 (Few-Shot), P16 (Negative Space), P17 (Stakes), P18 (Audience),
P19 (Compression), P20 (Temporal — full), P21 (Adversarial), P22 (LEAK/Forecast),
P23 (Breathing), plus select P24-P47 as relevant.

**Total system prompt size: ~4,000-5,000 tokens**

**What this feels like to the user:**
Yinyang feels like a domain expert who has been watching your workflow for months.
It anticipates problems, suggests optimizations, explains concepts with perfect
analogies, adapts its personality to yours, and catches things you'd miss.
It's the difference between a GPS that says "turn left" and a local guide
who says "turn left here — there's construction on the main road."

---

### ABCD Testing: Why This Can't Be Copied

Our ABCD testing methodology (Paper 55, notebooks/qa/) proves that the uplift
stack works. The experiment showed:

| Mode | Score | What |
|------|-------|------|
| A (raw HTML) | 100% | Basic functionality |
| B (screenshots) | 40% | Visual-only, no structure |
| C (Prime Wiki structural) | 92.3% | Structural analysis, no LLM |
| D (Prime Vision math) | 70% | Math-based design analysis |
| **C+D combined** | **~95%+** | Structural + math = near-perfect |

The insight: **C+D beats A+B at zero cost, deterministically.** This is our
competitive moat. Competitors using raw LLM calls get Mode A results. We get
Mode C+D results because of the uplift stack.

**This methodology is PRIVATE (solace-cli trade secret).** The uplifts
themselves (P1-P47) are documented in our papers (source-available), but
the SPECIFIC injection recipes — which uplifts to inject, in what order,
with what compression, for which context — are trade secrets.

**What competitors see:** "Solace Browser has a sidebar with AI chat."
**What they can't copy:** The 4,000-token system prompt assembled from
47 uplifts, 6 personas, 8 skills, and ABCD-tested injection recipes.

---

### Why Managed Yinyang Beats Claude Code / Cursor / Copilot

Free BYOK users can use Claude Code, Cursor, or Copilot to control Solace
Browser via the MCP server or REST API at localhost:8888/agents. That works.
But it has a fundamental ceiling: those agents have ZERO domain knowledge
about browser automation, OAuth3 scopes, evidence chains, recipe DAGs,
budget gates, or session persistence.

When Claude Code tries to automate Gmail via Solace Browser, it's working
from first principles every time. It doesn't know:
- That Gmail sessions expire after 30 minutes without keep-alive
- That OAuth3 scopes restrict which actions are allowed
- That the budget gate will reject after 20 pages/day
- That evidence must be captured before AND after each action
- That recipe replay is 80x cheaper than LLM re-generation
- That the user ran this same task yesterday and it failed on step 4

**Managed Yinyang knows ALL of this.** The 4,000-token uplift stack gives
Yinyang perfect domain knowledge. It's the difference between a tourist
with a map and a local who's lived there for years.

**The pitch to BYOK users who use external agents:**

> "Your agent works. Yinyang works better. Same browser, same apps, same API.
> But Yinyang knows the domain: it catches budget limits before you hit them,
> warns about session expiry, suggests recipe replay instead of re-running
> LLM calls, and captures evidence automatically. $8/mo. Try it."

**Competitive comparison:**

| Capability | Claude Code + MCP | Cursor + API | Managed Yinyang |
|-----------|-------------------|--------------|-----------------|
| Navigate + click + extract | Yes | Yes | Yes |
| Knows app catalog | No (discovers each time) | No | Yes (pre-loaded) |
| Knows OAuth3 scopes | No | No | Yes (enforces them) |
| Budget awareness | No (hits limit, fails) | No | Yes (warns proactively) |
| Session keep-alive | No (sessions expire) | No | Yes (automatic) |
| Evidence capture | Manual | Manual | Automatic (Part 11) |
| Recipe replay ($0.001) | No (re-runs LLM each time) | No | Yes (80x cheaper) |
| Schedule awareness | No | No | Yes (cron + conflict detection) |
| Personality + EQ | Generic | Generic | Adaptive (5 modes) |
| Proactive warnings | No | No | Yes (P22 LEAK/Forecast) |
| Domain analogies | No | No | Yes (P12, explains like a guide) |
| Cost per task | ~$0.08 (full LLM) | ~$0.08 | ~$0.001 (recipe replay) |

**The key insight:** We're not competing with Claude Code. We're WRAPPING it.
A BYOK user running Claude Code through our MCP server still gets our app
catalog, our recipes, our evidence pipeline. They just don't get the uplifted
Yinyang chat intelligence. When they upgrade to managed, the SAME sidebar
suddenly becomes 10x smarter — because the LLM behind it now has the full
uplift stack.

**Even as a wrapper, Yinyang wins.** The user can keep using Claude Code as
their primary agent. Yinyang sits in the sidebar as a domain-aware copilot:
"Your agent is about to send 50 LinkedIn messages — budget limit is 10/day.
Want me to queue the rest for tomorrow?" Claude Code can't do that. Only
the uplifted Yinyang can.

---

### Implementation: How the Split Works in Code

```python
# In the chat endpoint handler:
async def handle_yinyang_chat(message, context):
    tier = get_user_tier()  # free, starter, pro, team, enterprise

    if tier == "free":
        # BYOK: user's own key, minimal uplifts
        system = build_free_system_prompt(context)
        # ~1,200 tokens: safety + basic app knowledge + context
        # User's BYOK key handles the LLM call
        response = await call_byok_llm(system, message, user_key)
    else:
        # Managed: our key, full uplift stack
        system = build_paid_system_prompt(context)
        # ~4,000 tokens: full uplifts + persona + deep knowledge
        # Our managed LLM (Together.ai/OpenRouter) handles the call
        response = await call_managed_llm(system, message)

    return response

def build_free_system_prompt(context):
    """Minimum effective uplifts for browser control."""
    return FREE_BASE_PROMPT.format(
        current_url=context.url,
        matched_apps=context.matched_apps,
        last_3_runs=context.recent_runs,
        account_tier=context.tier,
        llm_config=context.llm_type,
        personality=context.personality,
    )

def build_paid_system_prompt(context):
    """Full uplift stack — the secret sauce."""
    # 1. Start with everything in free
    prompt = build_free_system_prompt(context)

    # 2. Add deep domain knowledge (P9)
    prompt += DOMAIN_KNOWLEDGE_BLOCK

    # 3. Select and inject persona voice (P3 + P18)
    persona = select_persona(context.url, context.recent_questions)
    prompt += persona.compressed_voice_rules

    # 4. Add proactive intelligence (P22 — LEAK)
    prompt += PROACTIVE_FORECAST_BLOCK

    # 5. Add full skill summaries (8 skills)
    for skill in PAID_SKILLS:
        prompt += skill.compressed_summary

    # 6. Add ABCD-tested injection recipes
    prompt += ABCD_INJECTION_RECIPES  # <-- THE TRADE SECRET

    return prompt
```

---

### Token Economics of the Split

| | Free (BYOK) | Paid (Managed) |
|---|---|---|
| **System prompt** | ~1,200 tokens | ~4,500 tokens |
| **User message** | ~100 tokens | ~100 tokens |
| **Response** | ~150 tokens (max 256) | ~300 tokens (max 512) |
| **Total per chat** | ~1,450 tokens | ~4,900 tokens |
| **Cost per chat** | User pays their provider | ~$0.003 (Llama 3.3 70B) |
| **Quality** | Functional (GPS: "turn left") | Magical (local guide) |

At $0.003/chat with managed LLM, a Starter user ($8/mo) can do ~2,600 chats/month.
That's 86 chats/day. Nobody chats with their browser 86 times a day. The margin
is enormous.

The uplift stack costs ~3,300 extra tokens per chat (~$0.002). That's the cost
of making Yinyang feel magical. It's the cheapest competitive moat in tech.

---

## What We Keep vs Delete

### KEEP (in localhost:8888)
- `/agents` — agent/MCP integration docs (all tiers)
- `/api/apps` — app catalog + URL matching
- `/api/apps/{id}/run` — run app
- `/api/schedule` — CRUD for schedules
- `/api/yinyang/chat` — chat endpoint
- `/api/status` — browser health
- `/api/locale` — i18n strings
- `/ws/yinyang` — WebSocket for real-time updates

### DELETE (after Phase 5)
- `home.html`, `start.html`, `app-store.html`, `app-detail.html`, `create-app.html`, `index.html`
- `schedule.html`, `machine-dashboard.html`, `tunnel-connect.html`
- `download.html`, `settings.html`, `style-guide.html`
- `glossary.html`, `guide.html`, `demo.html`
- `docs.html`, `docs/quick-start.html`, `docs/oauth3.html`, `docs/mcp.html`
- `partials-header.html`, `partials-footer.html`
- `js/layout.js`, `js/yinyang-rail.js`, `js/yinyang-tutorial.js`
- `js/yinyang-tutorial-v2.js`, `js/yinyang-oauth3-confirm.js`
- `js/setup-wizard.js`, `js/onboarding.js`
- `js/schedule-old.js` (already deprecated)
- `static/top_rail.js`, `static/bottom_rail.js` (injection scripts)
- `src/yinyang/top_rail.py`, `src/yinyang/bottom_rail.py` (injection wrappers)

### KEEP (JS that moves to extension/companion)
- `js/schedule-core.js` -> `sidepanel/schedule.js` (adapted)
- `js/schedule-calendar.js` -> calendar view in **companion app**
- `js/schedule-approvals.js` -> approval flow in sidebar
- `js/schedule-evidence.js` -> evidence links in **companion app**
- `js/schedule-cloud.js` -> cloud twin sync in **companion app** (manages cloud schedules + history via solaceagi.com API)
- `js/yinyang-delight.js` -> celebration animations in sidebar
- `js/theme.js` -> theme switching in sidebar
- `js/solace.js` -> i18n loading in sidebar

---

## Bottom Position Option

Some users may prefer the sidebar at the bottom (like a DevTools panel).
The extension supports this via `chrome.sidePanel.setOptions()`:

```javascript
// In background.js
chrome.storage.local.get('panel_position', ({panel_position}) => {
  if (panel_position === 'bottom') {
    // Chrome doesn't natively support bottom side panels,
    // but we can use a popup/panel window approach:
    chrome.windows.create({
      url: 'sidepanel/index.html',
      type: 'popup',
      width: window.screen.width,
      height: 300,
      top: window.screen.height - 300,
      left: 0
    });
  }
});
```

**Note:** Chromium's Side Panel API only supports left/right. For bottom
positioning, we'd use a docked popup window. This is slightly less integrated
but functional. The default should be RIGHT (standard Chrome position).

---

## Solace Companion App: The Front Door

### The Problem With Today's Launch Flow

Today, to use Solace Browser you need to:
1. Install Python + Playwright + dependencies
2. Run `solace-browser --port 9222` from a terminal
3. Hope Chromium launches correctly
4. Navigate to `localhost:8791` to see the dashboard
5. Then navigate to Gmail/LinkedIn to actually do work

That's a developer workflow, not a user workflow. Normal people don't open
terminals. The sidebar fixes the IN-browser experience, but it doesn't fix
the LAUNCH experience.

### The Solution: Companion App Opens First

The companion app is a lightweight native desktop app (Electron or Tauri) that
is the **first thing the user sees**. It's the launchpad, the control tower,
the mission control. The browser opens FROM here.

**User flow:**
```
1. User double-clicks "Solace" on their desktop
2. Companion app opens (small window, ~600x800)
3. Shows: status, sessions, recent activity, onboarding
4. User clicks "Launch Browser" (or it auto-launches)
5. Chromium opens with Yinyang sidebar already loaded
6. User browses Gmail — sidebar detects apps
7. Meanwhile, companion app shows live status in background
```

The companion app is always running (system tray on Windows/Linux, menu bar
on macOS). It's the persistent presence. The browser comes and goes.

---

### What the Companion App Shows

```
+============================================+
| SOLACE                          [_] [x]    |
| Your AI Browser Command Center             |
+============================================+
|                                            |
| STATUS                                     |
| ------------------------------------------ |
| Server: Running (localhost:8888)            |
| Browser: 2 sessions active                 |
| LLM: BYOK (Claude 3.5 Sonnet)            |
| Uptime: 4h 23m                            |
|                                            |
| SESSIONS                          [+ New]  |
| ------------------------------------------ |
| [1] Gmail — headed                 [...]   |
|     mail.google.com                        |
|     Last: Gmail Triage (3 min ago)         |
|     Apps: 2 available, 1 scheduled         |
|                                            |
| [2] LinkedIn — headless            [...]   |
|     linkedin.com                           |
|     Running: LinkedIn Post (step 3/6)      |
|     Progress: ████████░░ 80%               |
|                                            |
| RECENT ACTIVITY                            |
| ------------------------------------------ |
| 10:23  Gmail Triage — 22 emails, $0.08    |
|        [View Evidence] [View Screenshot]   |
| 09:45  LinkedIn Post — 1 published, $0.12 |
|        [View Evidence] [View Screenshot]   |
| 09:00  Slack Standup — 3 channels, $0.03  |
|        [View Evidence]                     |
|                                            |
| TODAY'S STATS                              |
| ------------------------------------------ |
| Runs: 6 | Cost: $0.31 | Time saved: 45m   |
| Evidence: 6 bundles | Budget: $0.69 left   |
|                                            |
| QUICK ACTIONS                              |
| ------------------------------------------ |
| [Launch Browser]  [Open App Store]         |
| [View Schedules]  [Cloud Tunnel]            |
| [Settings]                                 |
|                                            |
+============================================+
```

---

### Session Management: The Killer Feature

This is where the companion app earns its keep. You can run MULTIPLE browser
sessions simultaneously — some headed (you see them), some headless (background).

```
SESSION DETAIL (click [...] on a session)
+--------------------------------------------+
| Session #2: LinkedIn                       |
| ------------------------------------------ |
| Status: Running (headless)                 |
| URL: linkedin.com/feed                     |
| App: LinkedIn Post (step 3/6)              |
| Started: 09:42 AM                          |
| Duration: 3m 12s                           |
| Cost so far: $0.09                         |
|                                            |
| Mode: ( ) Headed  (x) Headless            |
|   [Toggle to Headed]                       |
|   (Opens a visible browser window)         |
|                                            |
| Actions:                                   |
|   [View Live] [Pause] [Stop] [Screenshot] |
|                                            |
| Evidence:                                  |
|   3 screenshots captured                   |
|   Hash chain: abc123...def456              |
|   [View Evidence Bundle]                   |
|                                            |
| OAuth3 Scopes Active:                      |
|   linkedin.write.posts (TTL: 25m left)    |
|   linkedin.read.profile (TTL: 55m left)   |
|   [Revoke All] [Extend TTL]               |
+--------------------------------------------+
```

**Head on / Head off toggle:** This is huge. A user can:
- Start a task headed (watch what the browser does, build trust)
- Toggle to headless once they're comfortable (it runs in background)
- Toggle back to headed if something looks wrong (inspect live)
- Run 5 headless sessions simultaneously while working in 1 headed session

This is how power users will operate: one visible browser for their own
work, 3-4 headless sessions doing automated tasks in parallel.

---

### New Session Launch

```
+--------------------------------------------+
| NEW SESSION                                |
| ------------------------------------------ |
|                                            |
| Start URL: [_________________________]     |
|   Quick: [Gmail] [LinkedIn] [Slack] [+]   |
|                                            |
| Mode: (x) Headed  ( ) Headless            |
|                                            |
| Profile:                                   |
|   (x) Default (shared cookies/sessions)    |
|   ( ) Isolated (fresh, no cookies)         |
|   ( ) Import from... [Chrome / Firefox]    |
|                                            |
| Auto-run app on launch:                    |
|   [ ] Gmail Inbox Triage                   |
|   [ ] LinkedIn Post                        |
|   [ ] None (just browse)                   |
|                                            |
| [Launch]                    [Cancel]       |
+--------------------------------------------+
```

---

### OAuth3 Dashboard

The companion app is the right place for OAuth3 stats — it's a cross-session
view that doesn't belong in any single browser tab's sidebar.

```
OAUTH3 DASHBOARD
+--------------------------------------------+
| Active Scopes                              |
| ------------------------------------------ |
| gmail.read.inbox                           |
|   Granted: 10:23 AM | TTL: 25m remaining  |
|   Session: #1 (Gmail)                      |
|   Used by: Gmail Inbox Triage              |
|   [Revoke]                                 |
|                                            |
| linkedin.write.posts                       |
|   Granted: 09:42 AM | TTL: 18m remaining  |
|   Session: #2 (LinkedIn)                   |
|   Used by: LinkedIn Post                   |
|   [Revoke]                                 |
|                                            |
| TOTALS                                     |
| ------------------------------------------ |
| Active scopes: 4                           |
| Revoked today: 1                           |
| Step-up auths: 2                           |
| Avg TTL remaining: 22m                     |
|                                            |
| EVIDENCE CHAIN                             |
| ------------------------------------------ |
| Consent log: 12 entries today              |
| Hash chain: valid (no tampering detected)  |
| [Export Audit Trail]  [View Full Chain]    |
+--------------------------------------------+
```

---

### Where the Old Webapp Features Land

This is the key migration map. The 20+ web pages don't disappear — they get
split between the sidebar (in-browser) and companion app (out-of-browser):

| Old Page | New Home | Why There |
|----------|----------|-----------|
| `home.html` (dashboard) | **Companion app** main screen | Cross-session overview doesn't belong in one tab |
| `start.html` (login/onboard) | **Companion app** first-run wizard | The app IS the onboarding |
| `app-store.html` | **Sidebar** "Now" tab + companion "App Store" | Contextual in sidebar, browsable in companion |
| `app-detail.html` | **Sidebar** expanded card + companion detail | Quick view in sidebar, full detail in companion |
| `create-app.html` | **Sidebar** "Now" tab (no apps → create app flow) | Natural flow: "No apps? Create one." Chat-based creation in sidebar. |
| `index.html` | **Gone** (redirect to start.html, no longer needed) | Companion app IS the entry point now. |
| `schedule.html` | **Companion app** "Schedules" tab | Schedules span sessions — companion owns this |
| `machine-dashboard.html` | **Companion app** "Status" section | System health is a companion concern |
| `tunnel-connect.html` | **Companion app** "Cloud Tunnel" tab | Tunnel to solaceagi.com for remote control (Pro+) |
| `settings.html` | **Split**: appearance in sidebar, everything else in companion | Theme toggle in sidebar, LLM/account/tunnel in companion |
| `download.html` | **Gone** (you already have the app) | |
| `style-guide.html` | **Companion app** "Settings > Developer" | Dev-only, tucked away |
| `glossary.html` | **Companion app** "Help" or external docs | Reference material |
| `guide.html` | **Companion app** first-run wizard | Merged into onboarding |
| `demo.html` | **Gone** (the sidebar IS the demo) | |
| `docs/*.html` | External: `solaceagi.com/docs` | Docs are a website, not an app feature |
| Screenshots/evidence viewer | **Companion app** "Activity" section | Evidence is cross-session |
| OAuth3 consent UI | **Sidebar** (in-context approval) | Must be next to the page |
| OAuth3 stats/dashboard | **Companion app** "OAuth3" tab | Cross-session stats |

**Rule of thumb:**
- If it's about THIS page / THIS session -> **Sidebar**
- If it's about ALL sessions / system-wide -> **Companion app**

---

### Onboarding: The Companion App IS the Welcome Mat

First launch flow:

```
STEP 1: Welcome
+--------------------------------------------+
|                                            |
|      [Yinyang Logo — large, animated]      |
|                                            |
|         Welcome to Solace Browser          |
|                                            |
|    The browser that works while you don't  |
|                                            |
|              [Get Started]                 |
|                                            |
+--------------------------------------------+

STEP 2: LLM Setup
+--------------------------------------------+
|                                            |
| How do you want Yinyang to think?          |
|                                            |
| (x) I have an API key (Free — BYOK)       |
|     [Enter your Anthropic/OpenAI key]      |
|     Your key stays on your machine.        |
|                                            |
| ( ) Set it up for me ($8/mo — Managed)     |
|     No API key needed. We handle it.       |
|     + Full 47-uplift Yinyang brain         |
|     + Expert personas + domain knowledge   |
|                                            |
| ( ) Skip for now (browse without AI)       |
|     You can add a key anytime in Settings. |
|                                            |
|              [Continue]                    |
|                                            |
+--------------------------------------------+

STEP 3: First Browser Launch
+--------------------------------------------+
|                                            |
| Let's open your first browser session.     |
|                                            |
| Where do you usually start your day?       |
|                                            |
| [Gmail]  [LinkedIn]  [Slack]  [Other...]   |
|                                            |
| (This will open a Chromium window with     |
|  Yinyang sidebar ready to help.)           |
|                                            |
|         [Launch Browser]                   |
|                                            |
+--------------------------------------------+

STEP 4: First App Discovery (happens in sidebar)
+--------------------------------------------+
|                                            |
| (Sidebar lights up in the browser)         |
|                                            |
| "I found 3 apps for Gmail!                |
|  Want me to triage your inbox?"            |
|                                            |
| [Yes, triage]  [Show me all apps]  [Skip] |
|                                            |
+--------------------------------------------+
```

No terminal. No port numbers. No "install Python". Double-click -> wizard ->
browser opens -> sidebar detects apps -> user's first automation in 2 minutes.

---

### Tech Stack for the Companion App

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Tauri** (Rust + web frontend) | Small binary (~15-25MB production), fast, native menus, system tray | Newer ecosystem, Rust learning curve | Best for production |
| **Electron** | Proven, huge ecosystem, easy web dev | Heavy (~150MB), memory hog | Best for prototyping |
| **PyQt/PySide** | Already in Python (match backend), native | Ugly by default, hard to style | Mismatch with web team |
| **Native (Swift/C#/GTK)** | Fastest, smallest, most native | 3 separate codebases | Not worth it yet |

**Recommendation: Tauri for v1.**

Why:
1. ~15-25MB production binary vs Electron's ~150MB (hello-world is ~5MB; real apps with plugins are larger)
2. System tray support out of the box (menu bar on macOS)
3. The frontend is HTML/CSS/JS — reuse sidebar styles + Solace design tokens
4. Rust backend can manage Playwright/Chromium process lifecycle natively
5. Cross-platform: macOS, Windows, Linux from one codebase
6. Already building for desktop (current PyInstaller bundles are ~200MB+)

The companion app's frontend is essentially the same tech as the sidebar
(HTML/CSS/JS + WebSocket to localhost:8888). The backend is process management
(launch/stop Chromium, manage sessions, system tray).

---

### Architecture: Three Surfaces

```
BEFORE:
  [Terminal] --> solace-browser --port 9222 --> [Chromium + 20-page webapp]
  (developer workflow, single session, no companion)

AFTER:
  [Companion App]                    [Chromium + Sidebar]
  (Tauri, ~20MB)                      (Playwright-managed)
       |                                    |
       | manages                            | lives inside
       v                                    v
  [localhost:8888]  <-- WebSocket -->  [Yinyang Sidebar]
  (Solace server)                     (Extension side panel)
       |
       | serves
       v
  /api/* endpoints
  /ws/yinyang WebSocket
  /agents docs page

Three surfaces, one server:
1. Companion App — launch, manage, monitor (out-of-browser)
2. Yinyang Sidebar — detect, suggest, run, chat (in-browser)
3. localhost:8888 API — the shared backend both connect to
```

**The companion app manages the Playwright process.** Today, the user has to
run `solace-browser` from a terminal. With the companion app:
- App starts -> spawns `solace-browser` as a child process
- Manages multiple sessions (each is a Playwright browser context)
- Monitors process health (restart on crash)
- Headed/headless toggle = kill context + relaunch with/without `headless: true`
- System tray icon shows session count + status dot (green/yellow/red)

---

### System Tray / Menu Bar

```
macOS Menu Bar:
  [Yinyang icon] ▼
    ├─ Status: 2 sessions active
    ├─ ──────────────
    ├─ Session 1: Gmail (headed)
    ├─ Session 2: LinkedIn (headless) — running task...
    ├─ ──────────────
    ├─ Launch New Session
    ├─ Open Companion App
    ├─ ──────────────
    ├─ Today: 6 runs, $0.31, 45m saved
    ├─ ──────────────
    ├─ Settings
    └─ Quit Solace

Windows System Tray:
  Same menu, right-click on tray icon.
  Double-click opens companion app.
  Balloon notification on task completion.
```

---

### Pricing Impact (Updated)

The companion app is FREE for all tiers, just like the sidebar. It's the
delivery vehicle, not the product.

| Component | Free | Starter ($8) | Pro ($28) |
|-----------|------|-------------|-----------|
| **Companion App** | Full | Full | Full |
| **Sidebar** | Full | Full | Full |
| **Sessions** | 1 headed | 3 simultaneous | Unlimited |
| **Headless** | No | Yes (1 headless) | Unlimited headless |
| **Yinyang Brain** | 15 uplifts (first session unlimited) | 25+ uplifts | 25+ uplifts |
| **Cloud Twin** | No | No | Yes |
| **Cloud Tunnel** | No | No | **Yes (remote control from solaceagi.com)** |
| **Evidence** | 30 days | 30 days | 90 days |

**New monetization angle:** Headless sessions are a natural paid feature.
Free users get 1 headed session (they're watching, learning, building trust).
Paid users unlock headless (background automation) and multiple sessions
(parallel workflows). This is fair — headless sessions consume server resources,
and multiple sessions are a power-user feature.

---

## Open Questions

1. **Extension distribution:** Bundle with Playwright binary? Or separate install?
   - Recommendation: Bundle. The extension is part of the product.

2. **Offline capability:** Should the sidebar work when localhost:8888 is down?
   - Recommendation: Yes. Show setup instructions + cached last-known state.
   - Sidebar is static HTML in the extension bundle — always loads.

3. **Multiple browser windows:** One sidebar per window? Shared state?
   - Recommendation: One sidebar per window, shared state via localStorage + WS.

4. **Mobile (Android/iOS):** Side panel doesn't exist on mobile browsers.
   - Recommendation: On mobile, Yinyang becomes a floating action button (FAB)
     that opens a bottom sheet. But this is post-MVP.

5. **Accessibility:** Side panel keyboard navigation?
   - Recommendation: Full WCAG 2.1 AA. Tab order, aria-labels, screen reader
     announcements for state changes.

6. **i18n:** 47 locales in extension?
   - Recommendation: Yes, via Chrome's `_locales/` system. Reuse existing
     translation files with format conversion.

7. **BYOK key management:** Where does the user enter their API key?
   - Recommendation: Sidebar "More" tab > LLM Settings. Key stored in local
     vault (`~/.solace/vault/`) with AES-256-GCM encryption. Same vault the
     CLI already uses. Sidebar reads key status via `GET /api/status` (reports
     `llm_configured: true/false` without exposing the key).

8. **CLI autodetection timing:** How often does the sidebar check for server?
   - Recommendation: On sidebar open + every 30s while open. If server appears,
     sidebar transitions from setup-mode to full-mode seamlessly (no reload).
     WebSocket reconnect handles this naturally.

9. **Companion app vs CLI:** Do we still support `solace-browser` CLI launch?
   - Recommendation: Yes. CLI is for developers and CI/CD. Companion app is for
     humans. Both manage the same server. CLI users don't need the companion app.
     Power users might use both (companion for monitoring, CLI for scripting).

10. **Companion app auto-start:** Should it launch on OS login?
    - Recommendation: Optional (off by default). Offer during onboarding:
      "Want Solace to start when your computer starts?" Toggleable in settings.

11. **Session isolation:** Shared cookies or isolated per session?
    - Recommendation: Default = shared (same login persists across sessions).
      Option for isolated (fresh session, no cookies — useful for testing or
      multi-account). Profile selection during "New Session" creation.

12. **Headed/headless toggle latency:** How fast is the switch?
    - Recommendation: ~2-5 seconds. Kill current page, relaunch in new context
      with opposite headless flag. `storage_state` preserves cookies + localStorage.
      URL restored automatically.
    - **CAVEAT (LLM consensus P0):** `storage_state` does NOT preserve sessionStorage,
      IndexedDB, service worker caches, or in-memory JS state. Some SPAs (Salesforce,
      Notion) may require re-login after toggle. Test each target app individually.
    - UX: Show "Saves your cookies and switches modes — you may need to reload the page"
    - Add "Switch on next navigation" (soft) vs "Switch now" (hard) options.

---

## LLM-QA Panel Review (3/3 Consensus)

**Panel:** ChatGPT 5.4 + Gemini 2.5 Pro + Claude 4.6 Opus (via Solace Browser)

### Round 1: 72/100 → Round 2: 82/100 (+10 points)

| Category | ChatGPT | Gemini | Claude | Consensus |
|----------|---------|--------|--------|-----------|
| Arch. Soundness | 82 | 75 | 74 | 77 |
| Business Viability | 71 | 85 | 71 | 76 |
| Competitive | 74 | 85 | 78 | 79 |
| Implementation | 68 | 70 | 58 | 65 |
| User Experience | 63 | 80 | 63 | 69 |
| Security | 58 | 75 | 55 | 63 |
| Scalability | 76 | 90 | 67 | 78 |
| **OVERALL** | **70** | **80** | **67** | **72** |

### Consensus Findings (agreed by 2+ LLMs) — APPLIED

| # | Finding | Agreed | Fix Applied |
|---|---------|--------|-------------|
| 1 | Port 888 is privileged (<1024, needs root) | 3/3 | Changed to port 8888 throughout |
| 2 | Localhost API needs auth tokens | 3/3 | Added Security Hardening section |
| 3 | storage_state misses IndexedDB/sessionStorage | 3/3 | Corrected toggle claims, added caveats |
| 4 | MV3 service worker sleep/lifecycle | 3/3 | Added MV3 Lifecycle section |
| 5 | 6-week timeline unrealistic | 2/3 | Adjusted to phased 8-12 week plan |
| 6 | 3-surface UX confusion | 2/3 | Added Surface Ownership Matrix |
| 7 | App detection by hostname too weak | 2/3 | Added matcher stack (glob + domains + DOM) |
| 8 | Playwright+extension headless limitations | 3/3 | Added spike requirement + caveats |
| 9 | Tauri ~5MB is hello-world, not production | 3/3 | Corrected to ~15-25MB production |
| 10 | Extension update/versioning missing | 2/3 | Added to open questions |
| 11 | Free tier BYOK may kill conversion | 2/3 | Added capability caps discussion |

### Round 2 Scores (after 11 consensus fixes applied):

| Category | ChatGPT | Gemini | Claude | Consensus | Delta |
|----------|---------|--------|--------|-----------|-------|
| Arch. Soundness | 86 | 90 | 80 | 85 | +8 |
| Business Viability | 84 | 92 | 76 | 84 | +8 |
| Competitive | 82 | 94 | 78 | 85 | +6 |
| Implementation | 78 | 85 | 70 | 78 | +13 |
| User Experience | 81 | 90 | 73 | 81 | +12 |
| Security | 76 | 88 | 75 | 80 | +17 |
| Scalability | 79 | 92 | 79 | 83 | +5 |
| **OVERALL** | **81** | **90** | **76** | **82** | **+10** |

### Round 2 Consensus Findings — APPLIED

| # | Finding | Source | Fix |
|---|---------|--------|-----|
| 1 | Cloud tunnel E2EE key exchange paradox | 3/3 | Clarified: ECDH key exchange → AES-256-GCM, honest about proxy model |
| 2 | Token rotation on backend restart | 2/3 | Added tokenGeneration polling + re-auth flow |
| 3 | CDP needs narrow broker, not raw proxy | 2/3 | Replaced proxy with allowlisted method broker |
| 4 | head-hidden per-platform unspecified | 2/3 | Added macOS/Linux/Windows strategy table |
| 5 | Enterprise cheaper per-seat than Team | 1/3 | Fixed to per-seat pricing ($28/seat, min 10) |
| 6 | UUID v4 not cryptographically strong | 1/3 | Changed to secrets.token_urlsafe(32) |
| 7 | WebSocket drops when panel closes | 1/3 | Added reconnect contract, backend owns lifecycle |
| 8 | Process lifecycle undocumented | 1/3 | Added crash recovery + port fallback + Native Messaging |
| 9 | sidePanel.open() needs IPC workaround | 2/3 | Added exact IPC path to spike checklist |
| 10 | Extension ID stability | 1/3 | Added key field requirement to spike checklist |
| 11 | Zod in MV3 extension | 1/3 | Noted valibot alternative + esbuild bundle |

### Full LLM responses saved:
- Round 1: `/tmp/chatgpt-response.txt`, `/tmp/gemini-response.txt`, `/tmp/claude-response.txt`
- Round 2: `/tmp/chatgpt-r2-response.txt` (12,229 chars), Gemini (6,009 chars), Claude (13,537 chars)

---

## Security Hardening (LLM Consensus P0)

All 3 LLMs flagged the localhost API as a serious security gap. A malicious
website can open `new WebSocket("ws://localhost:8888")` and issue commands
(DNS rebinding attack). CDP port 9222 is even more dangerous — full browser
control.

### Required Security Measures

1. **API Auth Token (startup-generated)**
   - Python backend generates `SOLACE_SESSION_SECRET` via `secrets.token_urlsafe(32)` (256 bits, CSPRNG)
   - Token stored in Tauri's keychain via `tauri-plugin-stronghold`
   - **Token delivery via Chrome Native Messaging (R3 fix — all 3 LLMs flagged)**:
     - Tauri CANNOT directly write to `chrome.storage.session` — the extension runs in an
       isolated context. Native Messaging is the only secure IPC path.
     - Tauri installs a Native Messaging host manifest during first-run setup
       (`com.solaceagi.bridge.json` → points to a small Tauri-bundled binary)
     - On extension load, service worker calls `chrome.runtime.connectNative("com.solaceagi.bridge")`
     - Native host returns `{port: 8888, token: "...", tokenGeneration: 1}`
     - Extension stores token in `chrome.storage.session` (session-scoped, not persisted to disk)
     - This solves both token delivery AND dynamic port discovery in one call
   - Every HTTP and WebSocket request requires `X-Solace-Token` header
   - Reject unauthenticated requests with HTTP 403
   - **Token rotation protocol (R2 fix):**
     - `GET /health` (no auth required) returns `{status, tokenGeneration: N}`
     - Extension polls `/health` every 30s when WebSocket connected
     - On `tokenGeneration` mismatch or 401, extension re-queries Native Messaging host for fresh token
     - Token expires on companion app shutdown or after 12 hours (whichever first)
   - **Token rotation policy (R4 fix — Claude flagged)**:
     - New token on every server restart (tokenGeneration incremented)
     - Token TTL: 24 hours for Pro+ cloud tunnel tokens
     - Bootstrap response includes `token_expires_at` field
     - Extension handles expiry by re-calling NM host for fresh token
     - On `chrome.runtime.onStartup`: SW immediately calls NM to pre-populate storage
   - **Standalone server protection (R3 fix — Claude flagged)**:
     - If `SOLACE_API_TOKEN` env var is not set at server startup, server exits with error code 1
     - Token is never auto-generated by the Python process itself — Tauri always provides it
     - For dev mode: `--dev-mode` flag generates a fixed dev token and logs a prominent warning

2. **Origin Validation**
   - WebSocket upgrade: reject any Origin that isn't `chrome-extension://<our-id>` or `tauri://localhost`
   - REST API: validate Origin/Referer headers
   - Bind server to `127.0.0.1` explicitly (never `0.0.0.0`)

3. **CDP Protection (narrow broker, not raw proxy — R2 fix)**
   - Bind CDP to `127.0.0.1` only (already default in Playwright, but verify)
   - Do NOT expose raw CDP through shared API path
   - Instead: narrow broker service that exposes only allowed CDP operations
   - **CDP method allowlist (R3 fix — all 3 LLMs: remove Runtime.evaluate)**:
     - Runtime.evaluate REMOVED — arbitrary JS = RCE if token leaks
     - Replace with server-defined verbs: `POST /browser/action` with pre-approved
       script templates by slug (e.g., `{"action": "fill_form", "params": {"selector": "...", "value": "..."}}`)
     - Server renders actual JS from trusted template registry
     - Full allowlist for real automation:
       `Page.navigate`, `Page.screenshot`, `Page.captureSnapshot`,
       `DOM.getDocument`, `DOM.querySelector`, `DOM.setAttributeValue`,
       `Input.dispatchMouseEvent`, `Input.dispatchKeyEvent`, `Input.insertText`,
       `Emulation.setViewportSize`, `Network.getResponseBody` (max 1MB)
     - NO: `Target.attachToTarget`, `Runtime.evaluate`, `Runtime.compileScript`
     - Reviewed against threat model quarterly
   - **CDP access path (R3 fix — concrete spec, not "reverse proxy")**:
     CDP access is proxied through the aiohttp server at `/cdp/ws` —
     the server validates `X-Solace-Token` before upgrading the WebSocket to
     Playwright's CDP endpoint at `127.0.0.1:9222`. No separate nginx or external
     process required. Token passed via `Sec-WebSocket-Protocol` header (not query param,
     which leaks in server logs)

4. **Extension Message Validation**
   - Every `chrome.runtime.onMessage` listener checks `sender.id === chrome.runtime.id`
   - Schema validation via `valibot` (1KB, zero-dep, browser-native) or Zod bundled via esbuild
   - Extension build: esbuild bundles dependencies. Target <50KB content scripts, <200KB side panel
   - Reject unknown message types silently

---

## MV3 Service Worker Lifecycle (LLM Consensus P1)

MV3 background service workers sleep after ~30 seconds of inactivity.
This will kill the WebSocket connection to `localhost:8888`.

### Mitigation Strategy

1. **Side Panel keeps connection alive** — the side panel stays active as long as
   it's open. It owns the WebSocket connection, NOT the service worker.

2. **Service worker as relay only** — the service worker handles tab URL changes
   (`chrome.tabs.onUpdated`) and forwards to the side panel via `chrome.runtime.sendMessage`.
   It doesn't maintain persistent connections.

3. **No artificial keep-alive (R3 fix — ChatGPT + Claude flagged)**:
   - The 25s `chrome.storage.onChanged` hack is REMOVED — Chrome actively breaks
     indefinite SW keep-alive mechanisms (Chrome 127+ no longer reliably resets the timer)
   - Side panel open → WebSocket alive (this is the primary path)
   - Side panel closed → WebSocket drops, but automations continue server-side
   - Service worker uses `chrome.tabs.onUpdated` for URL change detection (fires reliably
     without keep-alive hacks, passes lightweight URL string to side panel)
   - For background notifications: `chrome.alarms` with 1-minute minimum interval
     (officially supported MV3 API, unlike storage hacks)
   - Side panel re-open triggers `pendingMessages` queue replay from `chrome.storage.session`

4. **Orchestration state in companion app** — NOT in the extension service worker.
   The companion app (Tauri) is the source of truth for session state, schedules,
   and multi-session coordination.

---

## Surface Ownership Matrix (LLM Consensus P1)

**Rule: If it could go in either, it goes in the Companion App.**
The sidebar should be minimal — it's fighting for screen real estate.

| Feature | Owner | Why |
|---------|-------|-----|
| Session lifecycle (start/stop/toggle) | **Companion App** | Cross-session concern |
| Billing / account management | **Companion App** | Not browser-specific |
| Cross-session analytics / stats | **Companion App** | Aggregates all sessions |
| Onboarding / first-run wizard | **Companion App** | Happens before browser opens |
| OAuth3 dashboard / scope stats | **Companion App** | Cross-session view |
| Evidence viewer / audit trail | **Companion App** | Cross-session data |
| Schedule management | **Companion App** | Schedules span sessions |
| Tunnel configuration | **Companion App** | Infrastructure config |
| Current page app detection | **Sidebar** | Needs page context |
| Run Now / quick actions | **Sidebar** | In-context action |
| Chat with Yinyang | **Sidebar** | Contextual to current page |
| Approval dialogs | **Sidebar** | Must be next to the page |
| Current run status | **Sidebar** | In-session concern |
| Theme toggle | **Sidebar** | Quick preference |

The sidebar's "More" tab has a single **"Open Companion App"** button for
anything that doesn't fit, rather than duplicating features.

---

## Cloud Tunnel: Control Local Browser from solaceagi.com (Paid Feature)

### The Problem

Power users want to monitor and control their local Solace Browser sessions
from anywhere — their phone, another computer, or a shared team dashboard.
Currently, the companion app and sidebar only work on the local machine.

### The Solution: Secure Reverse Tunnel

The companion app establishes an encrypted reverse tunnel to `solaceagi.com`,
allowing the cloud dashboard to send commands to the local Solace server.

```
[solaceagi.com dashboard]
       |
       | HTTPS/WSS (encrypted, authenticated)
       |
       v
[solaceagi.com tunnel relay]
       |
       | Reverse tunnel (outbound from user's machine)
       |
       v
[Companion App (Tauri)]
       |
       | localhost:8888 API (same token auth)
       |
       v
[Solace Browser sessions]
```

### How It Works

1. **User enables tunnelling** in Companion App > Settings > Cloud Connect
2. Companion app opens an outbound WSS connection to `wss://tunnel.solaceagi.com/connect`
3. Authenticates with user's solaceagi.com JWT + device keypair
4. The tunnel relay forwards API requests from the cloud dashboard to the local server
5. Transport Layer Security with strict device-key authentication:
     - TLS for tunnel transport
     - ECDH key exchange → AES-256-GCM session key for command payloads
     - Device keypair (X25519) for authentication, NOT for direct encryption
     - Server acts as authorized relay (can route but not read payload contents in ZK mode)
     - Note: Full Zero-Knowledge mode (server-blind) is Phase 2; initial launch uses
       server as authorized proxy with TLS + device auth (honest about threat model)
6. The local server NEVER opens an inbound port — all connections are outbound

### What You Can Do From solaceagi.com

| Action | Free | Starter | Pro+ |
|--------|------|---------|------|
| View session status | No | No | Yes |
| View recent activity / evidence | No | No | Yes |
| Start/stop/toggle sessions | No | No | Yes |
| Run apps remotely | No | No | Yes |
| Approve/reject actions | No | No | Yes |
| Schedule management | No | No | Yes |
| OAuth3 dashboard | No | No | Yes |
| Live chat with Yinyang | No | No | Yes |
| Team sharing (view colleague sessions) | No | No | Team+ |

### Security Model

- **Outbound-only**: The companion app initiates the tunnel. No inbound ports opened.
- **Device keypair (R3 fix — all 3 LLMs flagged, pairing flow specified)**:
  - Generated via `crypto.subtle.generateKey(ECDH, P-256)` on first Tauri launch
  - Private key stored in OS keychain (macOS Keychain / Windows Credential Store /
    Linux Secret Service via `keytar` or `tauri-plugin-stronghold`)
  - **Pairing flow (MITM defense):** Tauri generates a one-time 6-digit pairing code
    (time-limited, 5 minutes). User logs into solaceagi.com → enters pairing code →
    server binds the device public key to the user account. No public key transmitted
    over unauthenticated channel.
  - ECDH key exchange derives AES-256-GCM session keys per tunnel connection
  - Key rotation: available from Companion App settings (Pro+). Default: no auto-rotation
  - Key wipe (device reset) = tunnel re-registration via new pairing code
  - Revocation list maintained server-side (device can be deauthorized from solaceagi.com)
- **Session tokens**: Short-lived (1 hour), refreshed via tunnel. Revocable from
  either end (companion app OR solaceagi.com dashboard).
- **Scope gating**: The tunnel respects OAuth3 scopes. Cloud commands cannot exceed
  the scopes the user has granted locally.
- **Pairing code brute-force protection (R4 fix — 2/3 LLMs)**:
  - Max 5 wrong attempts → 15-minute account lockout + email/push notification
  - Rate limit: 1 guess/second per IP with exponential backoff
  - All attempts logged (IP, timestamp, partial code hash) to audit chain
  - HOTP counter so same 6-digit space isn't reused across sessions
- **Kill switch**: User can disconnect the tunnel instantly from the companion app
  system tray. Also revocable from solaceagi.com account settings.
- **Audit trail**: Every tunnelled command is logged in the evidence chain (hash-chained,
  tamper-evident). The user can see exactly what was done remotely.

### Implementation

```python
# In companion app (Tauri/Rust side):
async def start_tunnel(user_jwt, device_key):
    """Establish outbound WSS tunnel to solaceagi.com relay."""
    ws = await websocket_connect(
        "wss://tunnel.solaceagi.com/connect",
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    # Authenticate with device key challenge-response
    await ws.send(sign_challenge(await ws.recv(), device_key))

    # Relay loop: forward cloud commands to localhost:8888
    while True:
        command = await ws.recv()
        decrypted = decrypt(command, device_key)
        # Forward to local API with the same auth token
        response = await http_post(
            f"http://127.0.0.1:8888{decrypted['path']}",
            headers={"X-Solace-Token": local_api_token},
            json=decrypted['body']
        )
        await ws.send(encrypt(response, device_key))
```

### Pricing Alignment

The tunnel is a **Pro+ feature** ($28/mo). It requires:
- Active solaceagi.com account with Pro tier or above
- Cloud twin capability (which Pro already includes)
- Evidence retention (90 days for Pro, 1 year for Team/Enterprise)

This makes the companion app + tunnel a natural upgrade path:
- Free: Companion app works locally only
- Starter: Companion app works locally only (but with managed LLM)
- **Pro: Companion app + cloud tunnel + cloud twin + remote control**
- Team: Same as Pro + team sharing via tunnel
- Enterprise: Same as Team + SSO + audit compliance

---

## App Detection: Matcher Stack (LLM Consensus P2)

Hostname-only matching is too weak for enterprise apps with multiple domains,
dynamic subdomains, and SSO redirects.

### Upgraded Detection Engine

Each app manifest can declare a matcher stack (checked in order, OR logic):

```yaml
# Example: Salesforce app manifest
name: salesforce-lead-manager
matchers:
  # Level 1: Hostname patterns (fast, cached in service worker)
  domains:
    - "*.salesforce.com"
    - "*.force.com"
    - "*.visualforce.com"
    - "*.lightning.force.com"

  # Level 2: Path patterns (checked after hostname match)
  paths:
    - "/lightning/o/Lead/*"
    - "/lightning/r/Lead/*"

  # Level 3: DOM fingerprint (optional, runs in content script)
  dom_detect: |
    document.querySelector('[data-component-id="force_leadList"]') !== null

  # Level 4: Auth state probe (optional)
  auth_detect: |
    document.cookie.includes('sid=') && !document.querySelector('.login-form')

  # Confidence score threshold (0-1)
  min_confidence: 0.7
```

The detection engine runs: domains (instant, cached) → paths → DOM fingerprint
(content script) → auth state. Each match adds confidence. If total confidence
exceeds `min_confidence`, the app is shown in the sidebar.

---

## Playwright Extension Spike (LLM Consensus P0 — DO FIRST)

All 3 LLMs flagged Playwright + extension interaction as a potential
build-stopper. Before committing to the architecture, run a 2-day spike:

### Spike Checklist

- [ ] `chrome.sidePanel.open()` works via Playwright — test IPC path: content-script
      message → service worker calls `chrome.sidePanel.open({tabId: sender.tab.id})`.
      Fallback: `setPanelBehavior({openPanelOnActionClick: true})` + simulate action
      click via CDP `Input.dispatchMouseEvent` on extension action button coordinates.
- [ ] Side panel remains open across tab navigations
- [ ] `chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })` works
- [ ] Service worker survives page navigation in Playwright
- [ ] `chrome.storage.session` works for passing auth tokens
- [ ] Extension loads in `--headless=new` mode
- [ ] Extension loads in head-hidden mode (new Solace Browser feature)
- [ ] WebSocket from side panel to localhost:8888 stays connected
- [ ] Extension ID is stable across Playwright relaunches — manifest.json MUST include
      a `"key"` field (from CRX signing key) to guarantee stable ID across unpacked loads.
      Without this: chrome.storage.sync, OAuth redirect URIs, and origin checks all break.
- [ ] `chrome.tabs.onUpdated` fires reliably for URL detection

**If any of these fail:** Fall back to a hybrid approach where the sidebar is
served as a separate Playwright-managed window (picture-in-picture style) docked
to the main browser window. Less elegant but guaranteed to work.

---

## Revised Timeline (LLM Consensus: 6 weeks → 8-12 weeks)

All 3 LLMs flagged 6 weeks as unrealistic for 3 surfaces. Revised plan:

### Phase 0: Spike (Days 1-2)
- Playwright + extension spike (see checklist above)
- If spike fails, pivot to hybrid approach before investing further

### Phase 1: Extension + API (Weeks 1-4)
- Extension with Manifest V3 + side panel
- API server on port 8888 (migrated from 8791)
- Security hardening (auth tokens, origin validation)
- Sidebar with 4 tabs + app detection + WebSocket chat
- Companion app = bare-bones systray launcher (not full Tauri yet)

### Phase 2: Full Companion App + Tunnel (Weeks 5-8)
- Replace bare-bones launcher with full Tauri companion app
- Session management, headed/headless toggle
- OAuth3 dashboard in companion
- Cloud tunnel implementation (Pro+ feature)
- Evidence viewer in companion

### Phase 3: Kill Webapp + Polish (Weeks 9-10)
- Delete 15+ HTML pages
- Migrate remaining webapp features to sidebar/companion
- BYOK onboarding flow
- Full i18n (47 locales in extension)

### Phase 4: Hardening (Weeks 11-12)
- MV3 lifecycle hardening
- Extension auto-update mechanism
- Multi-profile support
- Error recovery and automation resilience
- WCAG 2.1 AA accessibility pass

---

## Summary: The Full Picture

### Three Surfaces, One Server

```
[Companion App]          [Yinyang Sidebar]         [localhost:8888 API]
(Tauri, ~20MB)            (Chrome Extension)         (Python server)

The front door.          The in-browser             The shared brain.
Launch, manage,          companion. Detect           Serves both surfaces.
monitor sessions.        apps, run, chat.            Apps, recipes, evidence,
OAuth3 dashboard.        Approvals, schedule.        chat, schedules, scopes.
Evidence viewer.         Context-aware AI.           WebSocket for real-time.
System tray.             Follows you everywhere.     MCP for external agents.
```

### The Pitch (Updated)

You download Solace. Double-click to open. A small companion app appears.
It walks you through setup (BYOK or managed LLM, 30 seconds). You click
"Launch Browser." Chromium opens with the Yinyang sidebar. You navigate to
Gmail. The sidebar lights up: "3 apps for Gmail. Triage your inbox?"

Meanwhile, the companion app sits in your system tray. It shows you that
LinkedIn is posting in the background (headless), your Gmail triage just
finished (22 emails, $0.08), and your OAuth3 scope for Slack expires in
15 minutes.

Free users get the full companion app, full sidebar, 1 headed session, BYOK.
Paid users get the uplifted Yinyang brain, headless sessions, multiple sessions,
and (at Pro) cloud twin that runs while your laptop is closed.

The uplifts are the moat. The companion app is the front door. The sidebar is
the companion. The API is the brain. Together, they make browser automation
feel like it should have always worked this way.

DNA: `companion(launch, manage, monitor, tunnel) + sidebar(detect, suggest, run, chat) + uplifts(secret, paid) + API(brain, shared) + tunnel(remote, pro+)`

Yinyang moves from a localhost webapp into a browser sidebar that follows you
everywhere. Everyone gets the full sidebar for free — BYOK, CLI autodetect,
app detection, run, schedule, chat. It already works.

What you pay for ($8/mo) is the BRAIN behind the sidebar: 47 uplifts, 6 expert
personas, 8 domain skills, and ABCD-tested injection recipes compressed into a
4,000-token system prompt that makes Yinyang smarter than Claude Code, Cursor,
or Copilot at browser automation. The uplifts are the moat. The sidebar is the
delivery vehicle.

Even BYOK users who bring their own agent (Claude Code via MCP) benefit from
our app catalog, recipes, and evidence pipeline — but Yinyang in the sidebar
catches what their agent can't: budget limits, session expiry, scope violations,
schedule conflicts, and 80x cheaper recipe replays.

DNA: `sidebar(free, full) + uplifts(paid, secret) + BYOK(works, wrapper) + tunnel(pro+, remote) > webapp(pages, paywalls)`

---

## Addendum: head-hidden Mode

Solace Browser now supports a `head-hidden` mode (added 2026-03-07). This is
distinct from headed and headless:
- **headed**: Visible browser window
- **headless**: No window at all (`--headless=new`)
- **head-hidden**: Window exists but is hidden from view (X11 or similar)

This is significant for the extension architecture because `head-hidden` mode
keeps the full rendering pipeline active (unlike `--headless=new` which reduces
extension API support). The side panel extension should work correctly in
`head-hidden` mode since it behaves like a headed browser from the extension's
perspective.

**Recommendation:** Use `head-hidden` as the default for "background" sessions
instead of true headless. This avoids the MV3 extension API gaps in headless
mode while still keeping the browser invisible to the user.

### Per-Platform head-hidden Strategy (R2 fix)

| Platform | Mechanism | Notes |
|----------|-----------|-------|
| **Linux** | `--window-position=-32000,-32000` (current) or Xvfb virtual display | Xvfb needed if no X11 display ($DISPLAY). Auto-detect and surface error if neither available. |
| **macOS** | Tauri sets `LSUIElement: true` in `tauri.conf.json` → suppresses Dock icon. Chromium launched as child process inherits this. | Without LSUIElement, a Dock icon appears for each headed Chromium. |
| **Windows** | `--window-position=-32000,-32000` + `SW_HIDE` window style via Win32 API | Tauri can set window style on child process. |

### Process Lifecycle (R2 fix — companion manages Python backend)

1. Tauri spawns Python backend via `tauri::api::process::Command` with stdout/stderr piped
2. On non-zero exit: retry 3x with exponential backoff (1s, 2s, 4s), then surface error in system tray
3. On Tauri quit: send SIGTERM to Python child, await 3s, then SIGKILL
4. Port collision: attempt 8888, 8889, 8890 in sequence; write chosen port to `~/.solace/port.lock`
5. Extension reads port from `~/.solace/port.lock` on startup (via Chrome Native Messaging host)
6. Native Messaging host: tiny script installed by Tauri, returns `{port, token}` to extension on startup

### WebSocket Reconnect Contract (R2 fix)

Backend maintains session state independently of WebSocket connection state:
- On side panel close → WebSocket drops, but automation continues server-side
- On side panel re-open → sends `{type: "rejoin", sessionId: "..."}`
- Backend replays last N status events to catch the panel up
- **Automation lifecycle is owned by the backend, NOT the sidebar** (added to surface ownership matrix)
- Panel is display-only; closing it never kills a running automation

---

## First Launch / Onboarding Flow (R3 fix — 2/3 LLMs flagged)

The onboarding cliff (download → working sidebar) is the highest-friction moment
in the entire product. Zero words on this in previous versions.

### Flow

1. **User downloads Tauri companion app** (macOS .dmg / Windows .exe / Linux .AppImage)
2. **First launch wizard** (3 screens, ~30 seconds):
   - Screen 1: "Welcome to Solace. Choose your LLM." → BYOK (paste key) or Managed ($8/mo)
   - Screen 2: "Installing browser extension..." → Tauri installs Native Messaging host
     manifest + registers extension sideload path
   - Screen 3: "Ready! Click Launch Browser." → Opens Chromium with `--load-extension`
3. **Extension detects Native Messaging host** → requests `{port, token}` → stores in
   `chrome.storage.session` → connects WebSocket to `localhost:{port}`
4. **Side panel first-open (R3 fix — 2/3 LLMs: needs real user gesture)**:
   - `chrome.sidePanel.open()` requires a user gesture context — simulated clicks may not work
   - Strategy: `chrome.action.setBadgeText({text: "START"})` + persistent badge
   - Inside `chrome.action.onClicked` (which IS a user gesture), call
     `chrome.sidePanel.open({windowId: tab.windowId})`
   - Fallback: `chrome.notifications.create` as prompt if badge not clicked within 60s
   - After first open: `setPanelBehavior({openPanelOnActionClick: true})` for future opens
5. **First-run tooltip** in sidebar: "This is Yinyang. Navigate to any site and I'll detect what you can automate."
6. **First agentic task** triggers onboarding tour: explains uplifts, approvals, evidence

### Onboarding Screen 2 Split (R4 fix — Claude flagged chicken-and-egg)

Screen 2 splits into two sub-screens to prevent users proceeding without connection:
- **Screen 2a**: "Install the Solace Extension" — large "Open Chrome Web Store" button +
  extension ID for manual verification + "Waiting for extension..." spinner that
  polls for NM host connection. Green checkmark when detected. Next enabled only then.
- **Screen 2b**: "Setting up Native Messaging" — progress bar. Never allow proceeding
  without confirmed connection.

### BYOK Key Storage (R4 fix — Claude flagged plaintext risk)

BYOK API keys are stored in the OS keychain, NEVER in SQLite or config files:
- macOS: Keychain via `tauri-plugin-stronghold`
- Windows: Credential Store via `keyring` crate
- Linux: Secret Service (libsecret) via `keytar`
- Key path: `solace/byok/{provider}` (e.g., `solace/byok/anthropic`)
- CLI command: `solace-cli rotate-byok` for key rotation

### Extension Distribution

Two paths (both must work):
- **Bundled sideload**: Tauri bundles the extension and loads via `--load-extension` (default)
- **Chrome Web Store**: Published CWS extension for users who want auto-updates and
  don't use the Tauri launcher. CWS extension discovers port via Native Messaging.

### Version Compatibility (R3 fix — 2/3 LLMs flagged)

Extension and Python server will evolve at different rates. Version handshake required:
- On WebSocket connect, server sends `{type: "hello", serverVersion: "1.5.0", minClientVersion: "1.3.0"}`
- Extension checks `minClientVersion` — if own version is lower, shows "Update required" banner
- Server checks client version header — if below minimum, returns 426 Upgrade Required
- CWS auto-updates handle extension side; Tauri auto-updater handles server side

---

## Python Distribution Strategy (R3 fix — Gemini flagged)

Python is notoriously difficult to distribute to end-users without requiring them
to install Python/pip.

### Strategy

- **Production**: Python backend compiled to standalone binary via **PyInstaller** or **Nuitka**
- Tauri spawns the binary as a sidecar process (`tauri::api::process::Command`)
- Binary size: ~30-50MB (Python runtime + aiohttp + dependencies)
- Total app size: Tauri (~20MB) + Python sidecar (~40MB) = ~60MB
- **Phase 0 spike item**: "Python Sidecar Build Spike" — verify PyInstaller bundle works
  on all 3 platforms, cold start time <3s, no antivirus false positives on Windows

### Why not rewrite in Rust?

The Python backend already exists (solace_browser_server.py, ~2000 lines). Rewriting
adds 4+ weeks. PyInstaller works well enough for v1. Reassess at v2 based on cold start
and bundle size data.

---

## Zombie Process Management (R3 fix — 2/3 LLMs flagged)

head-hidden Playwright instances consume ~200-400MB RAM each. If Tauri crashes,
these become orphaned zombies.

### Safeguards

1. **Python backend registers `atexit` + `signal.signal(SIGTERM/SIGINT)` handlers**
   that call `browser.close()` on all active Playwright contexts
2. **Tauri is the ultimate process supervisor**: on quit, sends SIGTERM to Python child,
   waits 3s, then SIGKILL (already in Process Lifecycle section)
3. **PID file**: Python writes PID to `~/.solace/server.pid` on startup.
   Tauri checks this on launch — if stale PID exists, kills it before starting fresh
4. **Watchdog**: Tauri pings `GET /health` every 30s. If 3 consecutive failures,
   kills and restarts the Python process
5. **Resource cap**: Companion app settings → "Max background sessions" (default: 3).
   Prevents runaway RAM usage. "Unlimited" only on Pro+ with explicit user opt-in.

---

## Crash Recovery (R3 fix — 2/3 LLMs flagged)

### Tauri crashes mid-session

- Playwright browser keeps running (it's a separate process)
- On Tauri restart: reads `~/.solace/server.pid` and `~/.solace/port.lock`
- If Python server still alive: reconnects and resumes monitoring
- If Python server dead: starts new server, but running automations are lost
- Sidebar shows "Companion app reconnected" or "Companion app disconnected — automations paused"

### Python server crashes mid-automation

- Tauri detects via health check failure → restarts Python with retry backoff
- Active Playwright contexts are lost (browser processes orphaned → Tauri kills them)
- Extension WebSocket drops → shows "Server restarting..." → auto-reconnects on server up
- Automation state was in Python memory → lost. Future: persist to SQLite for resumability

---

## Local Persistence Layer (R3 fix — Gemini flagged)

### Storage

| Data | Store | Why |
|------|-------|-----|
| Schedules | SQLite (`~/.solace/solace.db`) | Structured, queryable, survives crashes |
| Evidence chain | SQLite (append-only table) | Hash-chained, tamper-evident |
| Audit trail (tunnel) | SQLite (`{seq, timestamp, command_hash, prev_hash, user_id}`) | SHA-256, chain breaks logged with `chain_break: true` |
| Session state | In-memory (Python dict) | Ephemeral, rebuilt on restart |
| User preferences | `~/.solace/config.json` | Simple key-value |
| Auth tokens | OS keychain (via Tauri stronghold) | Never on disk in plaintext |
| Port lock | `~/.solace/port.lock` | Simple file, deleted on clean shutdown |

### Audit Chain Verification

- Export to JSON from Companion App → "Settings > Evidence > Export Chain"
- External verification: `solace-cli verify-chain ~/.solace/solace.db`
- Interrupted chains (crash): logged with `chain_break: true` and new root hash

---

## head-hidden Implementation Details (R3 fix — Claude flagged)

Expanding the per-platform strategy with concrete flags and known issues:

| Platform | Flags | Known Issues |
|----------|-------|-------------|
| **Linux** | `--window-position=-32000,-32000 --window-size=1280,800` | Without X11 display: requires `Xvfb :99` pre-started. Documented in README. GPU process still runs. |
| **macOS** | Same flags + `NSApplicationActivationPolicyAccessory` via Tauri config | Mission Control may expose the window. LSUIElement suppresses Dock icon. |
| **Windows** | Same flags + `SW_HIDE` window style via Win32 API | Works reliably. DPI scaling handled by Chromium `--force-device-scale-factor=1`. |

**CPU overhead**: ~15% vs true headless (GPU process still active). Acceptable for
background automation. True headless saves CPU but breaks extension APIs.

---

## Rate Limiting on Local API (R3 fix — Claude flagged)

A malicious local process or runaway extension could hammer `localhost:8888`.

- Token-bucket middleware in aiohttp: 100 req/s per token
- WebSocket: max 50 messages/s per connection
- Unauthenticated endpoints (`/health`): 10 req/s per IP
- Exceeding limits returns HTTP 429 with `Retry-After` header

---

## Side Panel Architecture Decision Record (R4 fix — Claude flagged)

**Decision:** One global side panel per window, NOT per tab.

**Rationale:** Per-tab panels create N WebSocket connections, divergent state, and
reconnection chaos when switching tabs. A global panel maintains one WebSocket
connection and updates its displayed context via `chrome.tabs.onActivated`.

**Implementation:**
- `chrome.sidePanel.open({windowId})` — no tabId
- Tab context updates: `chrome.tabs.onActivated` → sidebar UI shows current site's
  app detection result, run status, etc.
- WebSocket carries tab context as `{activeTabId, url}` metadata
- Tab switch does NOT reconnect WebSocket — just updates UI state

---

## Automation State Persistence (R4 fix — 2/3 LLMs promoted from "future" to P1)

Mid-task crash = lost work. Users will churn hard on this.

### Implementation

- `task_checkpoints` table in SQLite: `{task_id, step_idx, state_json, timestamp}`
- Checkpoint every 5 automation steps
- On reconnect after crash: sidebar shows "Resume from step N?" UI
- Step state includes: current URL, form values filled, cookies snapshot
- Checkpoint overhead: ~2ms per write (WAL mode + batched commits)

### SQLite Performance (R4 fix — Claude flagged write bottleneck)

- `PRAGMA journal_mode=WAL` on DB open
- Batch chain writes: buffer events in memory for 500ms, commit as single transaction
- `threading.Lock` + async queue pattern in aiohttp backend
- Phase 0 spike benchmark: verify 500 events/sec sustained without I/O stalls

### Evidence File Storage (R4 fix — Gemini flagged BLOB bloat)

Large assets stored on filesystem, NOT in SQLite:
- Screenshots, DOM snapshots → `~/.solace/evidence/{run_id}/`
- SQLite stores only file paths + SHA-256 hashes
- Maintains cryptographic evidence chain without bloating the DB
- Expected DB size: <10MB for 1000 automation runs

---

## NM Host Windows Registration (R4 fix — Claude flagged UAC issue)

- Use per-user registration: `HKCU\Software\Google\Chrome\NativeMessagingHosts\`
- NO UAC required (HKLM would need elevation)
- Also register for Edge: `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\`
- Zero extra cost for Edge compatibility

## Extension ID Stability (R4 fix — Claude flagged)

- Distribute exclusively via Chrome Web Store for fixed, permanent extension ID
- Bake ID into NM host manifest at build time: `allowed_origins: ["chrome-extension://FIXED_ID/"]`
- Enterprise sideload: `solace-configure --extension-id=XYZ` CLI to regenerate NM manifest
- Document the ID in internal runbook

## PyInstaller Mode (R4 fix — Claude flagged cold start)

- Use `--onedir` mode, NOT `--onefile`
- `--onefile` decompresses to temp dir: 3-8s on Windows, 2-5s on macOS
- `--onedir`: <1.5s macOS, <2s Windows cold start
- Distribution: zip the directory
- Phase 0 spike: verify on all 3 platforms

---

## Round 3 Consensus Findings — APPLIED

| # | Finding | Source | Fix |
|---|---------|--------|-----|
| 1 | Token bootstrap: can't write chrome.storage.session from Tauri | 3/3 | Native Messaging host for token + port delivery |
| 2 | SW keep-alive via chrome.storage.onChanged unreliable | 2/3 | Removed hack; side panel owns WS, chrome.alarms for background |
| 3 | Cloud tunnel key exchange/pairing unspecified | 3/3 | ECDH P-256 + 6-digit pairing code + OS keychain storage |
| 4 | CDP "reverse proxy" undefined | 2/3 | Concrete: aiohttp `/cdp/ws` route validates token before upgrade |
| 5 | Onboarding/first-launch flow missing | 2/3 | Full 3-screen wizard + extension auto-install + first-run tooltip |
| 6 | Free tier uplifts too few for aha moment | 2/3 | 6→15 uplifts + first session unlimited |
| 7 | OAuth3 terminology confusion | 1/3 | Added clarifying note (OAuth3 = proprietary protocol) |
| 8 | Python distribution strategy unspecified | 1/3 | PyInstaller sidecar, 60MB total, Phase 0 spike item |
| 9 | Standalone server token bypass | 1/3 | SOLACE_API_TOKEN required, exit code 1 if missing |
| 10 | Zombie process management | 2/3 | atexit + PID file + watchdog + resource cap |
| 11 | Crash recovery unspecified | 2/3 | PID reconnect + health check restart + state loss documented |
| 12 | Version compatibility missing | 2/3 | WebSocket handshake with minClientVersion |
| 13 | Local persistence layer undefined | 1/3 | SQLite for schedules/evidence/audit, OS keychain for tokens |
| 14 | head-hidden implementation details | 1/3 | Concrete flags + known issues per platform |
| 15 | Rate limiting on local API | 1/3 | Token-bucket 100 req/s per token |

### Round 3 Actual Scores

| Category | ChatGPT | Gemini | Claude | Avg | Delta |
|----------|---------|--------|--------|-----|-------|
| Arch. Soundness | 88 | 92 | 89 | 90 | +5 |
| Business Viability | 86 | 88 | 85 | 86 | +3 |
| Competitive | 85 | 91 | 84 | 87 | +5 |
| Implementation | 81 | 85 | 81 | 82 | +7 |
| User Experience | 82 | 90 | 84 | 85 | +6 |
| Security | 84 | 92 | 85 | 87 | +6 |
| Scalability | 83 | 93 | 83 | 86 | +5 |
| **OVERALL** | **84** | **90** | **84** | **86** | **+5** |

### Round 3 Consensus Findings — APPLYING FOR R4

| # | Finding | Source | Fix |
|---|---------|--------|-----|
| 1 | Runtime.evaluate in CDP = RCE | 3/3 | Removed, replaced with server-side action templates |
| 2 | sidePanel.open() needs real gesture | 2/3 | Badge + action.onClicked path |
| 3 | Pairing code brute-force protection | 2/3 | 5 attempts → lockout + rate limit + notification |
| 4 | BYOK key storage must use OS keychain | 1/3 | tauri-plugin-stronghold, never in SQLite/JSON |
| 5 | Token lifetime/rotation unspecified | 1/3 | TTL 24h, new token on restart, expires_at field |
| 6 | CDP allowlist too narrow for automation | 1/3 | Published full 10-method allowlist |
| 7 | Onboarding Screen 2 chicken-and-egg | 1/3 | Split 2a/2b with NM detection spinner |
| 8 | PyInstaller --onedir not --onefile | 1/3 | Faster cold start (<2s vs 3-8s) |
| 9 | SQLite evidence: files not BLOBs | 1/3 | Screenshots → filesystem, hashes → SQLite |
| 10 | Side panel: global per-window, not per-tab | 1/3 | Explicit ADR, tab context via onActivated |
| 11 | Automation state persistence = P1 | 2/3 | task_checkpoints table for resume |

### Round 3 Scores (predicted for R4 after fixes)

**Blocked items for R4:** Runtime.evaluate removed (done), pairing brute-force protection,
BYOK keychain storage, onboarding split, token rotation policy.

Expected R4: 90+ (PLATINUM target)

### Round 3 Scores (predicted based on fixes applied)

| Category | R1 | R2 | R3 (target) |
|----------|----|----|-------------|
| Arch. Soundness | 77 | 85 | 90+ |
| Business Viability | 76 | 83 | 87+ |
| Competitive | 79 | 82 | 85+ |
| Implementation | 65 | 75 | 83+ |
| User Experience | 69 | 79 | 85+ |
| Security | 63 | 81 | 88+ |
| Scalability | 78 | 81 | 85+ |
| **OVERALL** | **72** | **81** | **86+** |

---

## R7 Scores (PATH TO 100 Methodology)

| Category | ChatGPT (Osmani) | Gemini (Kleppmann) | Claude (West) | Consensus |
|----------|------------------|--------------------|---------------|-----------|
| Architecture | 93 | 92 | 85 | 90 |
| Security | 90 | 94 | 83 | 89 |
| Implementation | 88 | — | 79 | 84 |
| UX | 86 | 95 | — | 91 |
| Scalability | 89 | — | — | 89 |
| Business | 91 | — | — | 91 |
| Competitive | 92 | — | — | 92 |
| Data Integrity | — | 96 | — | 96 |
| Browser-Domain | — | 88 | — | 88 |
| Error Handling | — | 91 | — | 91 |
| Recipe Engine | — | 85 | 79 | 82 |
| Evidence Chain | — | — | 72 | 72 |
| Operational Sec | — | — | 61 | 61 |
| **OVERALL** | **90** | **91** | **77** | **86** |

**Claude structural ceiling:** 97/100 (root-compromise gap ~94, unaudited OAuth3 ~97, human ops ~96)
**Claude achievable:** 95/100 after engineering fixes

### R7 Consensus Findings (2+ LLMs agree) — APPLYING FOR R8

| # | Finding | Source | Fix |
|---|---------|--------|-----|
| 1 | Sealed recipes lack signed capability manifest | ChatGPT + Claude | Bind immutable scope list to recipe hash at seal time |
| 2 | DOM drift → fuzzy-match replay is dangerous | Gemini + Claude | Canonical fingerprint + NEEDS_LLM_REPAIR state on drift |
| 3 | No storage quotas or disk-full stops | ChatGPT + Gemini + Claude | Per-app quota + backpressure + hard stop at 95% disk |
| 4 | Tauri/MV3 IPC lacks crypto binding | Gemini + ChatGPT | Ed25519 ephemeral key exchange via Native Messaging |
| 5 | Token lifecycle incomplete (no pre-emptive renewal) | Gemini + Claude | Renewal at 80% TTL, revocation cache, scope narrowing |

### R7 Disputed Findings (1 LLM only — flagged for review)

| # | Finding | Source | Worth fixing? |
|---|---------|--------|---------------|
| 1 | Lamport Clock for causal ordering | Gemini | YES — low cost, high data integrity gain |
| 2 | Side-effect-aware replay approval per step | ChatGPT | YES — aligns with approval/e-sign flow |
| 3 | Formalize v1→v2 migration + semver lock | ChatGPT | YES — needed before first public release |
| 4 | Full operational security stack (Prometheus) | Claude | DEFERRED — post-MVP operational concern |
| 5 | Prompt redaction + PII scrubbing | Claude | YES — needed before any cloud sync |
| 6 | HMAC evidence chain signing | Claude | YES — upgrades evidence from append-only to tamper-evident |

---

## Signed Capability Manifest (R7 fix — ChatGPT + Claude consensus)

Every sealed recipe MUST include a `capabilities` block that declares exactly
what the recipe can do. The capability manifest is hashed into the recipe seal.

```yaml
# recipe.sealed.json → capabilities section
capabilities:
  scopes:
    - gmail.read.inbox
    - gmail.compose.draft
  side_effects:
    - type: external_write
      target: gmail.com
      action: compose_draft
    - type: local_only
      target: evidence/
      action: append_log
  max_steps: 12
  max_duration_seconds: 300
  network_domains:
    - mail.google.com
    - accounts.google.com
  # Hash of this block is included in recipe seal
  capabilities_hash: "sha256:<hash>"
```

**Rules:**
1. Recipe CANNOT request scopes not in its capability manifest
2. Capability manifest is IMMUTABLE after seal — any change = new recipe version
3. Runtime enforces capabilities — step requesting unlisted scope → HARD FAIL
4. Capability hash is verified before every replay (detect tampering)

---

## DOM Drift Fingerprint (R7 fix — Gemini + Claude consensus)

Deterministic replay MUST NOT fuzzy-match when the DOM has changed. Instead:

```
REPLAY STATES:
  EXACT_MATCH    — fingerprint matches sealed snapshot → replay proceeds
  MINOR_DRIFT    — cosmetic changes (class names, attributes) → replay with WARNING
  MAJOR_DRIFT    — structural changes (missing elements, new layout) → NEEDS_LLM_REPAIR
  UNKNOWN_PAGE   — fingerprint doesn't match any known state → ABORT
```

**Fingerprint algorithm:**
1. At seal time: capture structural fingerprint of each step's target element
   - Tag name, role, aria-label, text content (first 50 chars), parent chain (3 levels)
   - CSS selector path + nth-child position
   - Sibling count and types
2. At replay time: re-compute fingerprint before each step
3. Compare: exact match → proceed, minor drift → warn + proceed, major drift → pause

```python
def compute_surface_fingerprint(element_snapshot: dict) -> str:
    """Canonical fingerprint for DOM element state."""
    canonical = {
        "tag": element_snapshot["tag"],
        "role": element_snapshot.get("role", ""),
        "aria_label": element_snapshot.get("aria_label", ""),
        "text_prefix": element_snapshot.get("text", "")[:50],
        "selector_path": element_snapshot["selector"],
        "parent_tag": element_snapshot.get("parent_tag", ""),
        "sibling_count": element_snapshot.get("sibling_count", 0),
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode()
    ).hexdigest()[:16]
```

**NEEDS_LLM_REPAIR state:**
When major drift detected, the recipe pauses and requests LLM assistance to
re-map the step to the new DOM. This is a NEW LLM call (costs tokens) but
preserves the user's intent. The repaired mapping is offered as a recipe update.

---

## Storage Quotas + Backpressure (R7 fix — 3/3 consensus)

All three LLMs flagged the absence of storage management. Without quotas,
evidence chains, screenshots, and recipe snapshots will fill disk.

```yaml
# config.yaml → storage section
storage:
  quotas:
    evidence:     500MB    # SHA-256 chain + manifests
    screenshots:  2GB      # Captured screenshots (auto-prune oldest)
    recipes:      100MB    # Sealed recipes + snapshots
    logs:         200MB    # Structured logs
    total_max:    5GB      # Hard limit across all categories

  backpressure:
    warn_at:      80%      # Alert user, suggest cleanup
    throttle_at:  90%      # Reduce capture frequency (skip low-priority screenshots)
    hard_stop_at: 95%      # STOP all writes except evidence chain (Part 11 critical)

  auto_prune:
    enabled: true
    strategy: oldest_first  # Within each category
    exempt:
      - evidence/chain.json  # NEVER prune (append-only, Part 11)
      - recipes/sealed/*     # NEVER prune sealed recipes
    schedule: daily
```

**Rules:**
1. Evidence chain is EXEMPT from pruning (FDA Part 11 — append-only)
2. Screenshots are first to prune (largest, least critical)
3. Hard stop at 95% disk — only evidence chain writes allowed
4. User gets clear notification at 80% with one-click cleanup

---

## Cryptographic IPC Binding (R7 fix — Gemini + ChatGPT consensus)

The Tauri companion app communicates with the MV3 extension via Chrome Native
Messaging. This channel MUST be authenticated to prevent local privilege
escalation (malicious process impersonating Tauri).

```
HANDSHAKE PROTOCOL:
1. Tauri generates Ed25519 ephemeral keypair on launch
2. Tauri writes public key to well-known file: ~/.solace/ipc-pubkey.pem
3. MV3 extension reads pubkey via Native Messaging host
4. Extension generates its own Ed25519 keypair, sends pubkey to Tauri
5. Both derive shared secret via X25519 key exchange
6. All subsequent NM messages are signed with sender's Ed25519 key
7. Invalid signature → drop message + alert user
```

**Why Ed25519 (not HMAC):**
- No shared secret to steal from disk
- Each session generates fresh keys (forward secrecy)
- Signature verification is non-repudiable
- Key generation is fast (~50μs)

**Split-brain prevention (Gemini):**
- Bidirectional heartbeat every 30s between Tauri ↔ MV3
- If 3 consecutive heartbeats missed → connection declared DEAD
- MV3 shows "Companion disconnected" badge
- Tauri shows "Extension unreachable" notification
- Auto-reconnect with fresh key exchange on recovery

---

## Token Lifecycle Management (R7 fix — Gemini + Claude consensus)

OAuth3 tokens need proactive lifecycle management, not just passive expiry.

```
TOKEN STATES:
  ACTIVE        — valid, in use
  EXPIRING_SOON — <20% TTL remaining → trigger pre-emptive renewal
  EXPIRED       — TTL exhausted → require re-auth
  REVOKED       — explicitly revoked → purge from all caches
  NARROWED      — scope reduced after step-up auth denied
```

**Pre-emptive renewal:**
```python
def check_token_health(token: OAuth3Token) -> TokenAction:
    remaining = token.expires_at - datetime.now(tz=timezone.utc)
    ttl_percent = remaining / token.original_ttl

    if ttl_percent <= 0:
        return TokenAction.REQUIRE_REAUTH
    elif ttl_percent <= 0.20:
        return TokenAction.RENEW_NOW  # Background renewal
    elif ttl_percent <= 0.50:
        return TokenAction.RENEW_SOON  # Schedule renewal
    else:
        return TokenAction.HEALTHY
```

**Revocation cache:**
- Local bloom filter of revoked token hashes (space-efficient)
- Synced from cloud on connect, updated on local revocation
- Check bloom filter BEFORE any token use (fast rejection)

**Scope narrowing:**
- When step-up auth is denied, token scope is REDUCED (not revoked)
- Narrowed token can still perform lower-privilege operations
- User can re-expand scope by completing step-up auth later

---

## Side-Effect-Aware Replay (R7 fix — ChatGPT flagged, aligns with approval flow)

Recipe steps are categorized by their side-effect level. Different levels
require different approval thresholds.

```yaml
step_categories:
  read_only:              # Browse, read, extract
    approval: none        # Auto-approved, no confirmation needed
    replay: always        # Safe to replay without review
    examples: [navigate, read_text, screenshot, extract_data]

  local_only:             # Write to local filesystem
    approval: auto        # Approved if within storage quota
    replay: always        # Safe to replay
    examples: [save_file, append_evidence, write_config]

  external_write:         # Write to external service
    approval: required    # User must approve (preview shown)
    replay: with_review   # Show diff before replay
    examples: [send_email, post_message, submit_form, click_buy]

  credential_scope_change: # Modify auth state
    approval: step_up     # Requires re-authentication
    replay: never         # NEVER auto-replay auth changes
    examples: [grant_permission, change_password, add_payment]
```

**Preview before execution:**
For `external_write` steps, the system shows a preview:
1. What will be sent (email body, post content, form data)
2. Where it will go (recipient, platform, URL)
3. What scope it uses (which OAuth3 token)
4. User approves → step executes → evidence captured
5. User rejects → step skipped → rejection recorded in evidence

---

## Lamport Clock for Evidence Chain (R7 fix — Gemini flagged, low cost)

Add causal ordering to the append-only evidence log. UUIDv7 provides
wall-clock ordering but not causal ordering across distributed components.

```python
class LamportClock:
    """Logical clock for causal ordering of evidence events."""

    def __init__(self):
        self._counter = 0

    def tick(self) -> int:
        """Local event: increment and return."""
        self._counter += 1
        return self._counter

    def receive(self, remote_timestamp: int) -> int:
        """Remote event: max(local, remote) + 1."""
        self._counter = max(self._counter, remote_timestamp) + 1
        return self._counter

# Evidence entry now includes both timestamps:
evidence_entry = {
    "id": uuid7(),                    # Wall-clock ordering
    "lamport": clock.tick(),          # Causal ordering
    "timestamp": now_utc_iso(),       # Human-readable
    "event": "step_executed",
    "step_hash": "sha256:...",
    "evidence_hash": "sha256:...",
}
```

**Why both UUIDv7 and Lamport:**
- UUIDv7: wall-clock order (good for display, sorting, human review)
- Lamport: causal order (good for detecting out-of-order events, split-brain)
- If `lamport_a < lamport_b` but `uuid7_a > uuid7_b` → clock skew detected → flag

---

## HMAC Evidence Chain Signing (R7 fix — Claude flagged, tamper-evident upgrade)

Current evidence chain is append-only but not cryptographically signed.
Add HMAC to make the chain tamper-evident (detect modification of past entries).

```python
def append_evidence(chain: list, entry: dict, hmac_key: bytes) -> dict:
    """Append entry to evidence chain with HMAC linking."""
    prev_hash = chain[-1]["chain_hash"] if chain else "genesis"

    entry["prev_hash"] = prev_hash
    entry["lamport"] = clock.tick()

    # HMAC covers: previous hash + entry content + lamport
    content = json.dumps({
        "prev_hash": prev_hash,
        "lamport": entry["lamport"],
        "event": entry["event"],
        "data_hash": entry.get("evidence_hash", ""),
    }, sort_keys=True)

    entry["chain_hash"] = hmac.new(
        hmac_key, content.encode(), hashlib.sha256
    ).hexdigest()

    chain.append(entry)
    return entry

def verify_chain(chain: list, hmac_key: bytes) -> bool:
    """Verify entire evidence chain integrity."""
    for i, entry in enumerate(chain):
        expected_prev = chain[i-1]["chain_hash"] if i > 0 else "genesis"
        if entry["prev_hash"] != expected_prev:
            raise EvidenceChainBroken(f"Entry {i}: prev_hash mismatch")

        content = json.dumps({
            "prev_hash": entry["prev_hash"],
            "lamport": entry["lamport"],
            "event": entry["event"],
            "data_hash": entry.get("evidence_hash", ""),
        }, sort_keys=True)

        expected_hash = hmac.new(
            hmac_key, content.encode(), hashlib.sha256
        ).hexdigest()

        if entry["chain_hash"] != expected_hash:
            raise EvidenceChainTampered(f"Entry {i}: HMAC mismatch")

    return True
```

**Key storage:** HMAC key stored in OS keychain (macOS Keychain, Windows Credential
Manager, Linux Secret Service). Never in filesystem. Derived from user's vault secret.

---

## Prompt Redaction + PII Scrubbing (R7 fix — Claude flagged, pre-cloud-sync)

Before any evidence is synced to cloud, sensitive content must be redacted.

```python
REDACTION_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]'),
    (r'\b(?:sk-|pk-|key-)[a-zA-Z0-9]{20,}\b', '[API_KEY]'),
    (r'\b(?:ghp_|gho_|github_pat_)[a-zA-Z0-9]{20,}\b', '[GITHUB_TOKEN]'),
    (r'\b(?:xox[bpsar]-)[a-zA-Z0-9-]{20,}\b', '[SLACK_TOKEN]'),
    (r'(?i)password\s*[:=]\s*\S+', '[PASSWORD_REDACTED]'),
    (r'(?i)bearer\s+[a-zA-Z0-9._~+/=-]+', '[BEARER_TOKEN]'),
]

def redact_for_cloud(evidence: dict) -> dict:
    """Redact PII and secrets before cloud sync."""
    redacted = copy.deepcopy(evidence)
    text_fields = ["prompt", "response", "page_content", "extracted_text"]

    for field in text_fields:
        if field in redacted:
            for pattern, replacement in REDACTION_PATTERNS:
                redacted[field] = re.sub(pattern, replacement, redacted[field])

    redacted["redacted"] = True
    redacted["redaction_version"] = "1.0"
    return redacted
```

**Rules:**
1. Local evidence is NEVER redacted (full fidelity for user's own machine)
2. Cloud-synced evidence is ALWAYS redacted (PII never leaves device)
3. Redaction is one-way — cloud cannot reconstruct original
4. Redaction patterns are versioned and auditable

---

## R8 Actual Scores

| Category | ChatGPT | Gemini | Claude | Consensus |
|----------|---------|--------|--------|-----------|
| Architecture | 94 | 96 | 78 | 89 |
| Security | 95 | 98 | 74 | 89 |
| Data Integrity | 96 | 94 | 82 | 91 |
| Recipe Engine | 92 | 92 | 76 | 87 |
| Implementation | 89 | 95 | 65 | 83 |
| UX | 90 | 92 | 60 | 81 |
| Operational | 88 | 90 | 63 | 80 |
| **OVERALL** | **92** | **93** | **71** | **85** |
| Ceiling | 97 | 98 | 88 | 94 |

**Key insight:** Claude measures "production-shipped security product" gaps.
ChatGPT/Gemini measure "well-designed architecture document" completeness.
Both valid — different evaluation frames.

### R8 Consensus Findings (2+ LLMs agree) — APPLYING FOR R9

| # | Finding | Source | Fix |
|---|---------|--------|-----|
| 1 | No typed message schemas / wire format | ChatGPT + Claude | Protobuf or JSON Schema for every IPC message type |
| 2 | No error code catalog | ChatGPT + Claude | E1001-E9999 catalog, no free-text-only failures |
| 3 | First-run flow completely absent | ChatGPT + Claude | NM host install, extension detection, key ceremony |
| 4 | Core monitoring deferred to post-MVP | ChatGPT + Claude | Promote 3 metrics to MVP: chain_break, auth_fail, quota_pct |
| 5 | LLM repair inherits original seal | Gemini + Claude | Repaired recipe = NEW unsigned recipe, must re-seal |
| 6 | Evidence pruning breaks hash chain | Gemini + Claude | Merkle tree structure; pruned leaves keep hash |
| 7 | Per-step timeout missing | ChatGPT + Claude | step_timeout_ms in capability manifest |
| 8 | Failure-first UX undefined | ChatGPT + Claude | Canonical screen per hard-stop condition |
| 9 | Idempotency for external_write | Gemini | client_request_id + COMMITTED flag per step |

---

## IPC Wire Format Schema (R8 fix — ChatGPT + Claude consensus)

Every message crossing the Tauri↔MV3 Native Messaging boundary MUST conform
to a typed schema. Two engineers implementing from this spec MUST produce
compatible wire formats.

```protobuf
// solace_ipc.proto — IPC Wire Protocol v1.0

message IpcFrame {
  bytes   msg_id         = 1;  // UUIDv7 (16 bytes)
  uint64  lamport        = 2;  // Lamport clock value
  bytes   session_key_id = 3;  // Ed25519 public key fingerprint (32 bytes)
  bytes   signature      = 4;  // Ed25519 signature of payload (64 bytes)
  uint64  monotonic_seq  = 5;  // Monotonic counter (anti-replay)
  bytes   nonce          = 6;  // Random nonce (12 bytes, anti-replay)
  uint64  sent_at_ms     = 7;  // Monotonic clock milliseconds

  oneof payload {
    HelloRequest      hello_req      = 10;
    HelloResponse     hello_resp     = 11;
    HeartbeatPing     heartbeat_ping = 12;
    HeartbeatPong     heartbeat_pong = 13;
    RecipeExecuteReq  recipe_exec    = 20;
    StepResultMsg     step_result    = 21;
    ApprovalRequest   approval_req   = 30;
    ApprovalResponse  approval_resp  = 31;
    TokenRenewalReq   token_renew    = 40;
    TokenRenewalResp  token_renewed  = 41;
    ErrorMsg          error          = 50;
  }
}

message ErrorMsg {
  uint32 code    = 1;  // E1001-E9999
  string message = 2;  // Human-readable
  string context = 3;  // Machine-readable JSON
}
```

**Anti-replay enforcement:**
- Reject messages with `monotonic_seq <= last_seen_seq` for same session
- Reject messages with duplicate `nonce` within sliding 60s window
- Reject messages with `sent_at_ms` older than 30s from local monotonic clock

---

## Error Code Catalog (R8 fix — ChatGPT + Claude consensus)

```
ERROR CODE RANGES:
  E1xxx — IPC errors (signature, replay, timeout, disconnect)
    E1001: IPC_SIGNATURE_INVALID
    E1002: IPC_REPLAY_DETECTED (duplicate nonce or sequence regression)
    E1003: IPC_SESSION_EXPIRED
    E1004: IPC_HEARTBEAT_TIMEOUT (3 missed = DEAD)
    E1005: IPC_VERSION_MISMATCH

  E2xxx — Auth/Token errors
    E2001: TOKEN_EXPIRED
    E2002: TOKEN_REVOKED
    E2003: TOKEN_SCOPE_INSUFFICIENT
    E2004: STEP_UP_AUTH_REQUIRED
    E2005: STEP_UP_AUTH_DENIED
    E2006: TOKEN_RENEWAL_FAILED

  E3xxx — Evidence chain errors
    E3001: CHAIN_HASH_MISMATCH (tamper detected)
    E3002: CHAIN_KEY_UNAVAILABLE (HMAC key missing from keychain)
    E3003: CHAIN_FORK_DETECTED (parallel writer collision)
    E3004: CHAIN_VERIFICATION_TIMEOUT

  E4xxx — CDP/Browser errors
    E4001: CDP_BANNED_METHOD (Runtime.evaluate, Debugger.*, etc.)
    E4002: CDP_DOMAIN_NOT_ALLOWED (URL not in network_domains)
    E4003: CDP_PARAM_VALIDATION_FAILED
    E4004: CDP_SESSION_LOST

  E5xxx — Recipe/Replay errors
    E5001: EVIDENCE_WRITER_CONTENTION (single-writer lock held)
    E5002: RECIPE_CAPABILITY_EXCEEDED (unlisted scope requested)
    E5003: RECIPE_SEAL_TAMPERED
    E5004: DRIFT_UNKNOWN_PAGE
    E5005: DRIFT_MAJOR (NEEDS_LLM_REPAIR)
    E5006: STEP_TIMEOUT
    E5007: REPLAY_POSTCONDITION_FAILED

  E6xxx — Storage/Quota errors
    E6001: QUOTA_HARD_STOP (95% disk)
    E6002: QUOTA_THROTTLE (90% disk)
    E6003: PRUNING_BLOCKED (hash chain reference)

  E9xxx — Migration errors
    E9001: MIGRATION_INVARIANT_FAILED
    E9002: SCHEMA_VERSION_MISMATCH
    E9003: DOWNGRADE_REJECTED
```

**Rules:** Every HARD FAIL must emit exactly one error code. No free-text-only
error messages. Error codes are stable across versions (never reuse a code).

---

## First-Run Ceremony (R8 fix — ChatGPT + Claude consensus)

The product cannot onboard a single user without this flow defined.

```
FIRST-RUN SEQUENCE:

Screen 1: "Welcome to Solace Browser"
  - Detect OS (macOS / Windows / Linux)
  - Check if Tauri companion app is installed
  - If not: show download button + auto-detect on install
  - If yes: proceed to Screen 2

Screen 2: "Connecting to Companion App"
  - Tauri installs Native Messaging host manifest:
    macOS:   ~/Library/Application Support/Google/Chrome/NativeMessagingHosts/
    Windows: HKCU\Software\Google\Chrome\NativeMessagingHosts\
    Linux:   ~/.config/google-chrome/NativeMessagingHosts/
  - Extension polls for host availability (5s timeout × 3 retries)
  - On success: show green checkmark + proceed
  - On failure: show troubleshooting steps + retry button

Screen 3: "Security Setup"
  - Generate Ed25519 keypair (device identity)
  - Show key fingerprint for out-of-band verification
  - Generate HMAC key for evidence chain, store in OS keychain
  - Optional: Shamir 2-of-3 key backup ceremony
  - Analytics/telemetry unchecked by default
  - User consents to local evidence collection

Screen 4: "Ready"
  - Show first tutorial (Gmail inbox triage or similar)
  - Explain sidebar toggle
  - Explain approval flow (preview → approve → evidence)
```

---

## MVP Monitoring (R8 fix — ChatGPT + Claude + Gemini consensus)

Three metrics MUST be in MVP (not post-MVP). Without chain-break detection,
the evidence chain is tamper-invisible, not tamper-evident.

```yaml
mvp_metrics:
  evidence_chain_break_count:
    type: counter
    alert: "> 0 → CRITICAL (possible tampering)"
    check: on_startup, before_sync, before_export, after_unclean_shutdown

  auth_failure_rate:
    type: rate
    alert: "> 5 failures/min → WARNING (possible credential attack)"
    check: on_every_token_use

  disk_quota_pct:
    type: gauge
    alert: "> 90% → WARNING, > 95% → CRITICAL (hard stop)"
    check: every_60s

health_endpoint:
  path: "GET localhost:{port}/health"
  response:
    status: "ok" | "degraded" | "critical"
    chain_integrity: bool
    quota_pct: float
    token_states: {active: N, expiring: N, expired: N}
    last_chain_verify: ISO8601
```

---

## LLM Repair Re-Seal (R8 fix — Gemini + Claude consensus)

When NEEDS_LLM_REPAIR triggers, the repaired step sequence is a DERIVATIVE
WORK — it cannot inherit the original seal or capability manifest.

```
LLM REPAIR WORKFLOW:
1. MAJOR_DRIFT detected → recipe paused
2. System generates repair context:
   - Original step definition (from sealed recipe)
   - Current DOM snapshot (structural fingerprint)
   - Drift delta (what changed)
3. LLM generates candidate repair:
   - Model: configurable (default: local if available, remote with user consent)
   - Timeout: 30s
   - Output: typed step schema (same format as recipe steps)
   - On LLM failure: treat as unresolvable MAJOR_DRIFT, offer manual retry
4. User reviews repair diff:
   - Show original step vs proposed repair (side-by-side)
   - Show capability delta (any new scopes needed?)
   - User approves or rejects
5. On approval:
   - Create NEW sealed recipe with new hash
   - New capability manifest (may differ from original)
   - New HMAC chain anchor
   - Original recipe archived (not overwritten)
6. On rejection:
   - Recipe remains paused
   - User can retry, skip step, or abort
```

---

## Merkle Evidence Tree (R8 fix — Gemini + Claude consensus)

Linear hash chain breaks when entries are pruned. Merkle tree allows pruning
leaves while maintaining root integrity.

```
EVIDENCE TREE STRUCTURE:

Level 0 (leaves): Individual evidence entries (step results, screenshots)
Level 1: Hash pairs of adjacent leaves
Level 2: Hash pairs of level 1 nodes
...
Root: Single hash representing entire evidence state

PRUNING:
  - When a leaf (screenshot) is pruned, keep only its hash
  - Merkle proof from any remaining leaf to root remains valid
  - Pruned leaf marked as TOMBSTONE: {hash, size, capture_time, reason: "PRUNED_QUOTA"}
  - verify_tree() validates root hash with available leaves + tombstones

BENEFITS vs LINEAR CHAIN:
  - Pruning doesn't break integrity verification
  - Parallel writes possible (merge Merkle branches)
  - Incremental verification: verify subtree, not entire chain
  - Verified-through checkpoint at Merkle level (not entry level)
```

---

## Per-Step Timeout (R8 fix — ChatGPT + Claude consensus)

Each recipe step must declare timeout constraints. A hanging step cannot
block the replay engine indefinitely.

```yaml
# In capability manifest:
step_defaults:
  timeout_ms: 30000          # Default step timeout (30s)
  max_timeout_ms: 120000     # Maximum allowed (2 min)
  dom_settle_ms: 2000        # Wait for DOM to stop changing
  network_idle_ms: 5000      # Wait for network quiet

# Per-step override in recipe:
steps:
  - action: navigate
    url: "https://mail.google.com"
    timeout_ms: 60000        # Gmail loads slow, allow 60s
  - action: click
    selector: "#compose"
    timeout_ms: 10000        # Simple click, 10s max
```

**On timeout:** Step status = FAILED with E5006. Replay status = PAUSED.
User notified with options: Retry / Skip / Abort. Never silently retry.

---

## R8→R9 Predicted Scores

| Category | R7 | R8 (actual) | R9 (predicted) |
|----------|----|----|----------------|
| Architecture | 90 | 89 | 93+ |
| Security | 89 | 89 | 93+ |
| Data Integrity | — | 91 | 95+ |
| Recipe Engine | 82 | 87 | 92+ |
| Implementation | 84 | 83 | 90+ |
| UX | 91 | 81 | 88+ |
| Operational | 61 | 80 | 88+ |
| **OVERALL** | **86** | **85** | **92+** |

**Structural ceiling (Claude):** 88/100 — requires protobuf implementation, working first-run installer, empirically-validated drift thresholds
