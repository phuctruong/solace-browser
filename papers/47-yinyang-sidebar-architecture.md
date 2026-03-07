# Paper 47: Yinyang Sidebar Architecture — Bundled MV3 Side Panel
# DNA: `sidebar(detect, suggest, run, chat) > webapp(pages, routes, dashboards)`
# Forbidden: `INLINE_INJECTION | WEBAPP_DASHBOARD | KEEP_ALIVE_HACK | RAW_CDP_PROXY | RUNTIME_EVALUATE | UNSIGNED_APPROVAL | UNVERIFIED_RIPPLE | SILENT_EVIDENCE_LOSS | UNSEAL_BEFORE_SYNC | FREE_TIER_SYNC | AUTO_APPROVE | POINT_SOLUTION_THINKING`
**Date:** 2026-03-07 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser
**Supersedes:** Paper 04 (yinyang-dual-rail-browser)
**Cross-ref:** Paper 48 (companion-app), Paper 49 (cloud-tunnel-security), Paper 50 (uplift-tier-system), Paper 05 (pzip-capture), Paper 06 (part11-evidence), Paper 07 (budget-enforcement), Paper 08 (cross-app-delight), Paper 40 (part11-selfcert)
**LLM Consensus:** R1-R8 across ChatGPT + Gemini + Claude (8 rounds, 72 -> 86 -> 90+)

---

## 1. The Problem

Yinyang only appears on Solace Browser's localhost pages. When the user navigates to gmail.com, linkedin.com, or any external site, Yinyang disappears. The current dual-rail injection (Paper 04) breaks external page CSP, layouts, and images.

**Current state:**
- 20+ HTML pages served at localhost:8791 (control panel nobody looks at)
- `page.add_init_script()` injection deliberately disabled on external sites
- Users must context-switch between Solace UI and their actual work
- Two separate ports: 8791 (web UI) + 9222 (CDP)

## 2. The Solution: Kill the Webapp, Long Live the Sidebar

Replace the 20-page webapp with a single persistent sidebar using Chromium's Side Panel API (`chrome.sidePanel`). The sidebar is a **bundled component** of Solace Browser — not a standalone Chrome Web Store extension. When Solace Browser launches Chromium via Playwright, it automatically loads the sidebar via `--load-extension`. The user never installs anything; they launch Solace Browser and the sidebar is just there.

The sidebar lives OUTSIDE the page DOM — no CSP conflict, no layout breakage, survives navigation.

### Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Implementation | Bundled MV3 Side Panel (loaded via --load-extension) | Part of Solace Browser, not a store extension. Outside page DOM, no CSP conflict |
| Default position | Right side (Chromium standard) | Users expect it, customizable |
| Default state | Collapsed (toolbar icon) | Click to open |
| Port | `localhost:8888` | Unprivileged (>1024), memorable quad-8, replaces 8791 |
| Free tier | Full sidebar + BYOK + CLI autodetect | The sidebar IS the product |
| Paid tier | Managed LLM brain (47 uplifts) | Pay for intelligence, not UI |

### Architecture: Three Surfaces, One Server

```
[Companion App]          [Yinyang Sidebar]         [localhost:8888 API]
(Tauri, ~20MB)           (Chrome Extension)         (Python server)

The front door.          The in-browser             The shared brain.
Launch, manage,          companion. Detect           Serves both surfaces.
monitor sessions.        apps, run, chat.            Apps, recipes, evidence,
OAuth3 dashboard.        Approvals, schedule.        chat, schedules, scopes.
System tray.             Follows you everywhere.     WebSocket for real-time.
```

## 3. Sidebar Layout

### Four Tabs (Not 20 Pages)

| Tab | Purpose | Content |
|-----|---------|---------|
| Now | What Yinyang sees for THIS page | Current URL, matched apps, Run/Schedule buttons, last run |
| Runs | History + approvals | Recent runs, evidence links, approval queue |
| Chat | Talk to Yinyang | Context-aware chat, approval dialogs, suggestions |
| More | Settings + info | Theme, account, links, compact status |

### Surface Ownership Matrix

| Feature | Owner | Why |
|---------|-------|-----|
| Current page app detection | Sidebar | Needs page context |
| Run Now / quick actions | Sidebar | In-context action |
| Chat with Yinyang | Sidebar | Contextual to page |
| Approval dialogs | Sidebar | Must be next to page |
| Session lifecycle | Companion App | Cross-session |
| Billing / account | Companion App | Not browser-specific |
| Evidence viewer | Companion App | Cross-session data |
| Schedule management | Companion App | Spans sessions |

**Rule:** If it could go in either, it goes in the Companion App.

## 4. Bundled Sidebar Component

The sidebar is implemented as an MV3 extension bundle inside the Solace Browser repo. It is NOT a standalone extension — Solace Browser loads it automatically on launch via `--load-extension` and `--disable-extensions-except`.

```
solace-extension/            # Bundled sidebar (loaded automatically by Solace Browser)
  manifest.json              # Manifest V3 with sidePanel permission
  service-worker.js          # URL detection, app matching, tab events
  sidepanel.html             # 4-tab sidebar shell
  sidepanel.js               # Tab switching, WS, app rendering, chat
  sidepanel.css              # Design tokens (--yy-* variables)
  icons/
    icon-16.png              # Real yinyang logos (from web/images/yinyang/)
    icon-48.png
    icon-128.png
```

### MV3 Manifest (Key Parts)

```json
{
  "manifest_version": 3,
  "name": "Solace Browser -- Yinyang",
  "version": "0.1.0",
  "permissions": ["sidePanel", "tabs", "storage", "activeTab"],
  "side_panel": { "default_path": "sidepanel.html" },
  "background": { "service_worker": "service-worker.js" },
  "action": { "default_title": "Open Yinyang" },
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'none'; base-uri 'none';"
  }
}
```

### Loading in Solace Browser

Solace Browser's Playwright launcher automatically includes the sidebar:

```python
# In solace_browser_server.py launch args:
# --load-extension=/path/to/solace-extension
# --disable-extensions-except=/path/to/solace-extension
# User never sees this — sidebar appears automatically when browser starts.
```

## 5. App Detection Flow

```
User navigates to mail.google.com
  -> Extension service worker fires chrome.tabs.onUpdated
  -> Extract hostname, match against app manifests (cached)
  -> MATCH: Update badge count, sidebar shows matched apps
  -> NO MATCH: "No apps for this site. Want to create one?"
```

### Matcher Stack (LLM Consensus P2)

```yaml
matchers:
  domains: ["*.salesforce.com", "*.force.com"]   # Level 1: hostname (instant)
  paths: ["/lightning/o/Lead/*"]                   # Level 2: path pattern
  dom_detect: "querySelector('[data-component]')"  # Level 3: DOM fingerprint
  min_confidence: 0.7
```

## 6. WebSocket Protocol

Single multiplexed WebSocket at `ws://localhost:8888/ws/yinyang`:

| Direction | Type | Purpose |
|-----------|------|---------|
| C->S | detect | Match apps for current URL |
| S->C | detected | Return matched apps |
| C->S | run | Start app execution |
| S->C | state | State updates (preview_ready, running, done) |
| C->S | approve/reject | User approval decision |
| C->S | chat | Chat message |
| S->C | chat_reply | Yinyang response |
| C->S | schedule | Create/update schedule |
| S->C | credits | Balance update |
| S->C | evidence_sealed | Evidence chain sealed for run |
| S->C | evidence_synced | Evidence synced to cloud (paid) |
| S->C | esign_created | eSignature generated on approval |
| S->C | ripple_verified | PZip capture verified (100% RTC) |
| S->C | budget_warning | Budget gate triggered (B1-B5) |
| S->C | twin_status | Cloud twin state change |

## 7. Security Hardening (3/3 LLM Consensus)

### API Auth Token
- `secrets.token_urlsafe(32)` generated on startup
- Delivered to extension via Chrome Native Messaging
- Every HTTP/WS request requires `X-Solace-Token` header
- Token rotation on server restart (tokenGeneration field)

### Origin Validation
- WebSocket: reject Origin != `chrome-extension://<our-id>` or `tauri://localhost`
- REST: validate Origin/Referer
- Bind to `127.0.0.1` only (never `0.0.0.0`)

### CDP Protection (Narrow Broker)
- Runtime.evaluate BANNED (RCE risk)
- Allowlist: Page.navigate, Page.screenshot, DOM.querySelector, Input.dispatch*
- Access via `/cdp/ws` with token validation before upgrade

### Extension Message Validation
- `sender.id === chrome.runtime.id` check on all messages
- Schema validation via valibot (1KB, zero-dep)

## 8. MV3 Service Worker Lifecycle

MV3 service workers sleep after ~30s inactivity. Mitigation:

1. **Side panel owns WebSocket** (stays alive while panel is open)
2. **Service worker is relay only** (forwards tab URL changes to panel)
3. **No keep-alive hacks** (Chrome 127+ breaks them)
4. **chrome.alarms** for background notifications (1-min minimum, official API)
5. **Backend owns automation lifecycle** (closing panel never kills a task)

## 9. Port Consolidation

| Before | After | Purpose |
|--------|-------|---------|
| localhost:8791 | localhost:8888 | Web UI + REST API |
| localhost:9222 | localhost:9222 (unchanged) | CDP (Playwright) |

## 10. Sidebar Intelligence: Prime Wiki + PZip Capture

The sidebar's "Now" tab doubles as a capture interface for the community knowledge system.

### Page Extraction Pipeline (Paper 05)

```
User navigates to docs.python.org
  -> Service worker fires tabs.onUpdated
  -> Side panel triggers PZip capture (if enabled)
  -> Capture: DOM snapshot -> headings + body + meta + code blocks
  -> Compress: PZip (target 66:1 GAR) or gzip fallback (2.7:1)
  -> Verify: sha256(decompress(compressed)) == sha256(original)  [100% RTC]
  -> Store: .ripple.pz (compressed) + .ripple.json (manifest) + .structure.json (sitemap)
```

### What Sidebar Shows

| Element | Location | Content |
|---------|----------|---------|
| Capture status | "Now" tab header | "Capturing..." / "Verified" / "Error" |
| Compression ratio | "Now" tab | "2.7:1 (1.2 KB from 3.3 KB)" |
| Extract button | "Now" tab | "Extract to Community" -> POST /api/v1/prime-wiki/push |
| Mermaid diagrams | "Now" tab | Rendered Mermaid from captured pages |
| Community search | "More" tab | Search Prime Wiki snapshots |

### Community Browsing

- **Free tier:** Extract pages, contribute to community DB, pull others' snapshots
- **Paid tier:** All free features + cloud sync of local ripple database
- **Push:** Sidebar -> PZip compress -> POST to Firestore (doc_id = sha256(url))
- **Pull:** Search -> GET /api/v1/prime-wiki/pull?url_hash=X -> decompress -> render
- **Offline codebooks:** Bundle snapshots for offline study (Tower 29, Floor 7)

### Forbidden States

- `UNVERIFIED_RIPPLE` — Never display a snapshot without 100% RTC verification
- `ZLIB_FALLBACK` — PZip is the only compression method (Fallback Ban)
- `ANONYMOUS_PUSH` — Community contributions require authenticated user

## 11. Evidence Chain Display (FDA Part 11)

The sidebar is the primary witness for Part 11 compliance (Paper 06, Paper 40).

### Evidence in Sidebar

| Tab | Evidence Feature |
|-----|-----------------|
| Runs | Seal status per run: "pending" / "preview_ready" / "approved" / "sealed" |
| Runs | Click "View Evidence" -> hash chain viewer (entry N -> N-1 -> root) |
| Runs | Screenshot timeline (before/after each action) |
| Chat | Approval decisions are Part 11 logged with timestamp |
| More | Evidence export button (ZIP with verification script) |

### Hash Chain in Sidebar

```
Each evidence entry = {
  hash: sha256(payload + prev_hash + timestamp),
  prev_hash: link to previous entry,
  timestamp: UTC ISO-8601,
  action_type: "screenshot" | "approval" | "execution" | "seal",
  payload: action-specific data
}
```

- Chain is append-only, written per-step (not at end of run)
- Two streams share one run_id: evidence_chain.jsonl + oauth3_audit.jsonl
- Sidebar validates chain integrity on evidence viewer open
- Tamper detected -> red alert in sidebar header

### eSign from Sidebar (Paper 40)

When a logged-in user clicks "Approve" in the sidebar:

```
eSignature = sha256(user_id + timestamp_utc + meaning + record_hash)
  meaning: "reviewed" | "approved" | "authored" | "responsible" (Part 11 §11.50)
  Non-transferable: signature bound to user identity (Part 11 §11.70)
```

- **Logged-in users:** All approvals generate Part 11 compliant e-signatures
- **Guest users:** Actions logged but unsigned (audit trail only)
- Signature visible in evidence viewer with signer name, time, meaning
- Export package includes verification script (Python/sha256sum, no Solace install needed)

### Forbidden States

- `UNSIGNED_APPROVAL` — Logged-in users MUST generate e-signature on approve
- `RETROACTIVE_EVIDENCE` — Evidence captured at event time, never after
- `SEAL_BEFORE_COMPLETE` — Evidence seal is the final step per run
- `SILENT_EVIDENCE_LOSS` — Sync failure -> show error, retry (never drop)

## 12. Budget Enforcement in Sidebar (Paper 07)

Budget gates are fail-closed. The sidebar makes budget state visible.

### Budget Indicators

| Indicator | Location | Trigger |
|-----------|----------|---------|
| Credit balance | Header bar | Always visible ($0.42 remaining) |
| Action budget | "Now" tab per app | "3/10 sends used today" progress bar |
| Cost estimate | Run confirmation | "This will cost ~$0.08" before approval |
| Budget warning | Modal overlay | "Budget exceeded — blocked" (B1-B5 gate fail) |
| Daily spending | "Runs" tab footer | "$0.31 today | $56.25 value saved" |

### Gate Sequence (Paper 07)

```
B1: Is user authenticated?  -> BLOCKED if no
B2: Is app within scope?    -> BLOCKED if no
B3: Is action budget OK?    -> BLOCKED if exceeded
B4: Is financial budget OK? -> BLOCKED if exceeded
B5: Is step-up needed?      -> STEP_UP prompt if high-risk
```

All gates fail-closed. Sidebar shows which gate blocked and why.

## 13. Cloud Twin Status in Sidebar (Paper 49)

Paid users can monitor their cloud twin browser from the local sidebar.

### Twin Status Display

| Element | Location | Content |
|---------|----------|---------|
| Twin indicator | Header | Cloud icon: "Twin active" / "Twin idle" / "No twin" |
| Twin runs | "Runs" tab | Cloud-executed runs marked with cloud icon |
| Evidence sync | "Runs" tab | "Synced" / "Syncing..." / "Local only" per run |
| Start twin | "More" tab | "Start Cloud Twin" button (Pro+ users) |

### Sync for Paid Users

- **Free ($0) + Starter ($8/mo):** All data stays local, full functionality, no cloud sync
- **Pro ($28/mo):** Evidence + chat history + settings synced to solaceagi.com
- **Team ($88/mo):** + shared workspace, team evidence, shared schedules
- **Enterprise ($188/mo):** + SSO, unlimited retention, SOC2 audit export

### Sync Mechanism

```
Evidence bundles encrypted with AES-256-GCM (user's OAuth3-derived key)
  -> POST /api/v1/browser/evidence/sync (callback from Cloud Run Job)
  -> Sidebar shows sync status: "local" | "syncing" | "synced" | "error"
  -> Error: retry on next session (never silently drop data)
```

### What Syncs

| Data | Free + Starter | Pro+ |
|------|----------------|------|
| Evidence chains | Local only | Cloud + local |
| Chat history | Local only | Cloud + local |
| Settings/theme | Local only | Cloud + local |
| Schedule configs | Local only | Cloud + local |
| Prime Wiki ripples | Community push only | + personal backup |
| Recipes | Local only | Cloud catalog |

### Forbidden States

- `UNSEAL_BEFORE_SYNC` — Local seal must complete before cloud sync starts
- `UNENCRYPTED_SYNC` — All evidence encrypted before transmission
- `FREE_TIER_SYNC` — Free users never sync to cloud (explicit design choice)

## 14. Cross-App Orchestration (Paper 08)

The sidebar enables multi-app workflow visibility.

| Feature | Sidebar Tab | Description |
|---------|------------|-------------|
| Partner apps | "Now" tab | Suggested chain workflows for current app |
| Cross-app queue | "Runs" tab | Approval requests from partner apps |
| Delight engine | All tabs | Celebrations on milestones (Paper 08) |

### Anti-Clippy (Absolute Rule)

The sidebar NEVER auto-runs anything. Detect, suggest, wait for explicit approval.
- No auto-approve path (timeout = deny, Paper 07)
- No auto-run on page navigation
- No auto-schedule without user action

## 15. Competitive Position (Cross-Checked March 2026)

| Feature | Solace Sidebar | OpenAI Operator | Google Mariner | Anthropic Cowork | Browser-Use | Bardeen |
|---------|---------------|-----------------|----------------|-----------------|-------------|---------|
| Execution | Local-first | Cloud-only | Cloud-only | Local VM | SDK/headless | Extension |
| Sidebar | MV3 Side Panel | No sidebar | No sidebar | No sidebar | No sidebar | Injected overlay |
| OAuth delegation | OAuth3 (scoped, TTL, revocable) | None | UI-level consent | Folder sandbox | None | None |
| Evidence trail | SHA-256 hash chain (Part 11) | Org audit logs only | Timestamps + DOM | None | None | None |
| Deterministic replay | Yes (recipe system) | No (re-runs LLM) | Partial (Teach & Repeat) | No | No | Partial |
| Cost per replay | $0.001 (80x cheaper) | ~$0.08 (full LLM) | Unknown | ~$0.08 | ~$0.08 | Credit-based |
| eSign | SHA-256 Part 11 compliant | No | No | No | No | No |
| Community browsing | Prime Wiki (free) | No | No | No | No | No |
| Pricing | $0-188/mo | $20-200/mo | $250/mo | $20-200/mo | Free/paid | $0-50/mo |
| Distribution | Bundled in Solace Browser | Cloud-only | Cloud-only | Desktop app | SDK | Chrome Web Store |

### Key Differentiators (No Competitor Has)

1. **Hash-chained evidence** — tamper-evident, FDA Part 11 ready
2. **Deterministic recipe replay** — LLM called once at preview, $0.001 on replay
3. **OAuth3 scoped delegation** — TTL, revocation, step-up auth
4. **Community browsing** — Prime Wiki + PZip compression
5. **eSign from sidebar** — Part 11 §11.50/§11.70 compliant signatures

### Unfair Advantages of Owning the Browser

Building our own browser (Playwright + Chromium) instead of distributing a Chrome Web Store extension gives us capabilities no extension-only product can match:

| Advantage | What It Enables | Extension Can't |
|-----------|----------------|-----------------|
| **CDP 4-Plane Control** | Full DOM, Network, Input, Runtime access via CDP | Extensions limited to content scripts + messaging |
| **Bundled sidebar** | Sidebar loads automatically, no install friction | Users must find/install/trust from Web Store |
| **Anti-detect profiles** | Canvas, WebGL, timezone, font fingerprint spoofing | Extensions can't override browser fingerprints |
| **Session persistence** | Full browser profile (cookies, localStorage, sessions) across restarts | Extension can't control browser profile |
| **Headless/cloud twin** | Same browser runs headless in Cloud Run Jobs | Extensions can't run headless |
| **Controlled Chromium version** | Pin exact version, test against it, avoid breakage | At mercy of Chrome auto-updates |
| **Evidence capture** | Full page screenshots, network HAR, DOM snapshots via CDP | Extensions have limited capture APIs |
| **Recipe execution** | Playwright drives browser deterministically (click, type, navigate) | Content scripts can't reliably drive other origins |
| **Native Messaging bridge** | Direct IPC to local Solace CLI (OAuth3 vault, evidence store) | Requires separate native messaging host install |
| **OAuth3 consent flow** | Sidebar approval UI + CDP execution = atomic consent-then-act | Extension popup closes on navigation |
| **Multi-tab orchestration** | Playwright opens/controls multiple tabs programmatically | Extensions can only observe tabs, not drive them |
| **Network interception** | CDP Network domain: intercept, modify, block requests | Extensions use webRequest (being deprecated in MV3) |
| **PZip capture pipeline** | Full DOM extraction via CDP + PZip compression + hash verification | Extensions limited to content script DOM access |
| **Update channel** | Self-managed updates (git pull, Tauri auto-update) | Chrome Web Store review (3-7 days) |

**Bottom line:** A Chrome Web Store extension is a guest in someone else's house. Solace Browser owns the house — the sidebar, the automation engine, the evidence system, the profiles, and the update schedule are all ours.

### Known Limitation

- Panel width not programmatically controllable (~320px min, ~400px default)
- Sidebar requires Chromium-based engine (Solace Browser uses Playwright + Chromium, so this is always satisfied)
- If users try to load the extension in other browsers (Arc, Brave), sidePanel support varies — but Solace Browser controls the exact Chromium version

## 16. Browser-Native Features (Only Possible Because We Own the Browser)

These features leverage Solace Browser's full CDP + Playwright control — impossible in a Chrome Web Store extension.

### 16a. Inbox/Outbox Workflow Bus

Every automation follows: detect → preview → approve → execute → seal. The sidebar makes this visible.

| Element | Tab | Description |
|---------|-----|-------------|
| Inbox queue | Runs | Pending approvals, suggested actions, partner app requests |
| Outbox status | Runs | Approved actions being executed, with live progress |
| Preview pane | Now | LLM-generated preview of what will happen (shown once, sealed) |
| Outbox history | Runs | Completed actions with evidence links |

**Why browser-native:** Inbox/outbox requires CDP to intercept network responses, capture screenshots mid-flow, and drive execution deterministically. Extensions can't do this.

### 16b. OAuth3 Vault Dashboard

The sidebar's "More" tab shows OAuth3 token status.

| Element | Description |
|---------|-------------|
| Active scopes | Which apps have active OAuth3 tokens (e.g., "Gmail: send, read — expires 2h") |
| Revoke button | One-click revocation per app/scope |
| Step-up indicator | "High-risk action requires re-authentication" |
| Token health | Green/yellow/red per token (valid/expiring/expired) |
| Consent log | Recent consent decisions with timestamps |

**Why browser-native:** The OAuth3 vault lives in Solace CLI's local encrypted store. Native Messaging bridge gives direct IPC — no cloud round-trip.

### 16c. Recipe Library + Replay Status

| Element | Tab | Description |
|---------|-----|-------------|
| Available recipes | Now | Recipes matching current page (from `data/default/recipes/`) |
| Recipe preview | Now | "This recipe will: 1. Open compose 2. Fill subject 3. ..." |
| Replay indicator | Runs | "Replay: $0.001" vs "New: ~$0.08" cost badge |
| Recipe editor | More | Edit recipe steps (power users) |

**Why browser-native:** Recipe replay uses Playwright to drive actions deterministically — click coordinates, type text, wait for selectors. Extensions can't do this cross-origin.

### 16d. Schedule Management

| Element | Tab | Description |
|---------|-----|-------------|
| Active schedules | More | List of cron schedules with next-run time |
| Quick schedule | Now | "Run this daily at 9am" button per matched app |
| Schedule history | Runs | Past scheduled runs with evidence |
| Cloud schedule | More | "Run in cloud twin" toggle (Pro+ only) |

**Why browser-native:** Cloud schedules use the same Playwright automation in a Cloud Run Job. Extension-based scheduling would require a separate server anyway.

### 16e. Anti-Detect Profile Selector

| Element | Tab | Description |
|---------|-----|-------------|
| Profile badge | Header | Current anti-detect profile name |
| Profile switcher | More | Switch fingerprint profile (canvas, WebGL, timezone, fonts) |
| Profile per app | Now | "Use 'Marketing' profile for LinkedIn" |

**Why browser-native:** Anti-detect requires overriding browser-level APIs (canvas.toDataURL, navigator.webdriver, WebGL renderer). Only possible with CDP or Playwright launch args.

### 16f. Network Monitor + HAR Capture

| Element | Tab | Description |
|---------|-----|-------------|
| Request count | Now tab footer | "47 requests, 2.1 MB transferred" |
| Failed requests | Now | Red badge on network errors |
| HAR export | More | Export full network trace for debugging |
| API call log | Runs | Which API calls the recipe made during execution |

**Why browser-native:** CDP Network domain provides full request/response interception. Extensions' webRequest API is being gutted in MV3 (declarativeNetRequest is the replacement, far less capable).

### 16g. Tutorial + Fun Pack

| Element | Tab | Description |
|---------|-----|-------------|
| Getting started | Chat | Interactive tutorial (Yinyang walks through first automation) |
| Fun pack | More | Mini-games, achievements, celebration animations (Paper 08 delight) |
| Tip of the day | Chat | Contextual tips based on current page |
| Belt progress | More | Gamification progress bar (White → Black belt) |

## 17. Migration Path

| Phase | Scope | Duration |
|-------|-------|----------|
| 0: Spike | Playwright + MV3 extension feasibility | Days 1-2 |
| 1: Extension + API | Side panel + port 8888 + security | Weeks 1-4 |
| 2: Companion + Tunnel | Tauri app + session mgmt + cloud tunnel | Weeks 5-8 |
| 3: Kill Webapp | Delete 15+ HTML pages, migrate features | Weeks 9-10 |
| 4: Hardening | a11y, i18n, error recovery, auto-update | Weeks 11-12 |

## 18. What Dies

| Page | Replacement |
|------|-------------|
| home.html | Sidebar "Now" tab |
| app-store.html | Sidebar "Now" + "Browse" link |
| schedule.html | Companion app "Schedules" |
| settings.html | Split: theme in sidebar, rest in companion |
| 10+ more pages | See full migration map in scratch/yinyang-sidebar-rethink.md |

**Survives:** `/agents` docs page, `/api/*` endpoints, error pages (404, 500)

## 19. Spike Checklist (Phase 0)

- [ ] Sidebar appears automatically when Solace Browser starts (--load-extension)
- [ ] chrome.sidePanel.open() works via Playwright
- [ ] Side panel remains open across tab navigations
- [ ] Service worker survives page navigation
- [ ] chrome.storage.session works for auth tokens
- [ ] Sidebar works in --headless=new mode
- [ ] Sidebar works in head-hidden mode
- [ ] WebSocket from panel to localhost:8888 stays connected
- [ ] Extension ID stable across relaunches (key field in manifest)
- [ ] chrome.tabs.onUpdated fires reliably

---

## Interaction Patterns

| Actor | Action | Sidebar Response |
|-------|--------|-----------------|
| User navigates to Gmail | Service worker detects URL | "Now" tab shows 3 Gmail apps |
| User clicks "Run Now" | POST /api/apps/{id}/run | Switch to Runs tab, show progress |
| App needs approval | Server sends approval_request | Show approve/reject in Runs tab |
| User sends chat | WebSocket chat message | Yinyang responds with context |
| Server offline | Health check fails | Show setup instructions |
| No apps match | Empty state | "Be the first to create an app" |

---

## 20. The AI-Agent Browser: Killer Features That Define a New Category

Solace Browser isn't a browser with AI bolted on. It's a browser **built for AI agents from day one**. Every architectural decision — CDP control, sidebar, evidence, recipes — exists because AI agents need capabilities that no general-purpose browser provides.

### The 15 Killer Features

| # | Feature | What It Does | Why No Other Browser Has It |
|---|---------|-------------|---------------------------|
| K1 | **Deterministic Replay** | Record once, replay forever at $0.001/run (vs $0.08 with LLM). Playwright drives exact clicks/types/waits. | General browsers don't record action sequences. Extensions can't drive cross-origin. |
| K2 | **Evidence-First Execution** | Every agent action generates SHA-256 hash-chained proof: screenshots, DOM snapshots, network traces. FDA Part 11 ready. | No browser treats evidence as a first-class concern. Audit logs are afterthoughts. |
| K3 | **Consent Before Action** | OAuth3 scoped delegation: "Gmail: send emails to contacts, max 10/day, expires in 2 hours." Agent can't exceed scope. | Other browsers give AI all-or-nothing access. No granular delegation protocol. |
| K4 | **Sidebar Copilot** | Yinyang lives in the sidebar (MV3 Side Panel), sees what you see, suggests actions, never auto-runs. | Cloud browsers have no local UI. Extension browsers can't drive automation. |
| K5 | **Anti-Detect Profiles** | AI agents need multiple identities (marketing profile, research profile). Canvas, WebGL, timezone, font fingerprinting — all spoofable per session. | General browsers fight fingerprint spoofing. AI-agent browsers need it. |
| K6 | **Cloud Twin** | Same browser, same recipes, running headless in Cloud Run Jobs. $0.032 per 10-min recipe. Runs while you sleep. | No competitor offers local + cloud parity with the same automation engine. |
| K7 | **Recipe Marketplace** | Community-contributed automation recipes. Install "LinkedIn connection request" recipe, customize, run. Hit rate improves over time. | No browser has a recipe ecosystem. Bardeen has workflows but no replay economics. |
| K8 | **Budget Gates** | 5-level fail-closed budget enforcement (auth → scope → action → financial → step-up). Agent literally cannot overspend. | No browser has budget enforcement. Operator/Mariner have no spending controls. |
| K9 | **eSign on Approval** | When you approve an agent action, a Part 11 compliant e-signature is generated. Non-repudiable. Legally binding in regulated industries. | No browser generates legally compliant e-signatures on agent approvals. |
| K10 | **PZip Page Intelligence** | Every page you visit gets structurally extracted (headings, links, code blocks, meta) and compressed 66:1. Your agent learns from your browsing. | No browser extracts structured knowledge from browsing. History is just URLs. |
| K11 | **Community Knowledge** | Prime Wiki: community-contributed page extractions. "What does this API doc say?" → instant answer from someone who already visited. | No browser has a community knowledge graph built from browsing. |
| K12 | **Multi-Tab Orchestration** | Agent opens 5 tabs, fills a form in tab 1 using data from tab 3, approves in tab 5. Playwright coordinates all tabs programmatically. | Extensions can observe tabs but can't drive them. Cloud browsers drive one tab. |
| K13 | **Network-Aware Agents** | CDP Network domain: agent sees all HTTP requests/responses, can intercept, modify, or block. Full HAR capture for debugging. | MV3 killed webRequest. Cloud browsers don't expose network layer to agents. |
| K14 | **Inbox/Outbox Workflow** | Every automation follows: detect → preview → approve → execute → seal. Visible in sidebar. Nothing happens without explicit human consent. | Other agent browsers auto-execute. Solace makes the human the final authority. |
| K15 | **47 Expert Personas** | Agent adapts communication style: marketing persona for LinkedIn, technical persona for GitHub, empathetic persona for support. STORY-47 prime. | No browser integrates persona switching into the agent framework. |

### The Moat: Why This Can't Be Copied Easily

```
MOAT = Evidence(hash-chain) × Consent(OAuth3) × Economics(recipe-replay) × Community(Prime Wiki)

Evidence: Requires architectural commitment from day 1 (can't bolt on later)
Consent:  Token-revenue vendors (OpenAI, Anthropic) can't implement OAuth3
          — it reduces token usage, cannibalizing their revenue
Replay:   LLM vendors want you to call the LLM every time ($0.08)
          — recipe replay at $0.001 is against their business model
Community: Network effects compound — more users → more recipes → more knowledge
```

### Feature Implementation Priority

| Phase | Features | Status |
|-------|----------|--------|
| Phase 0 (Spike) | K4 (Sidebar), K14 (Inbox/Outbox) | Scaffold done |
| Phase 1 | K1 (Replay), K2 (Evidence), K3 (Consent), K8 (Budget) | Architected |
| Phase 2 | K5 (Anti-Detect), K6 (Cloud Twin), K12 (Multi-Tab), K13 (Network) | Infra ready |
| Phase 3 | K7 (Marketplace), K10 (PZip), K11 (Community), K15 (Personas) | Papers done |
| Phase 4 | K9 (eSign) | Part 11 framework ready |

---

## 21. Enterprise Customer Scenarios: Why They Must Buy

### 21a. SAP Data Migration — The VP of IT's Nightmare

**Customer profile:** Enterprise VP of IT running SAP S/4HANA migration ($2M-50M project, 6-18 months, 100+ stakeholders). The migration involves extracting data from legacy ECC, transforming it, loading into S/4HANA, and getting business sign-off that everything works.

**Market context (2026):** SAP migrations are a **$50B+ industry event**. ECC end-of-support hits 2027. 73% of projects exceed budget (avg 23% overrun). 68% take longer than planned. Testing alone is 25-30% of total project cost. Consulting fees rising 30-50% as deadline approaches. Current tools (SAP LTMC, Tricentis Tosca at $100K+/yr, Panaya, manual Excel) handle either migration OR testing OR compliance — **none handle all three**.

**The pain (what keeps them up at night):**

| Pain Point | Current Reality | Cost |
|-----------|----------------|------|
| Manual data validation | Consultants click through 500+ SAP transactions to verify migrated data matches source | $200-400/hr × weeks |
| Business Acceptance Testing (BAT) | Business users manually run test scripts, screenshot results, paste into Word docs | 2-4 weeks per cycle |
| Sign-off chaos | Approval chain: Data Owner → Business Process Owner → IT → Compliance → Project Manager → Steering Committee. Tracked in email. | Missed approvals delay go-live by weeks |
| Regulatory evidence | Pharma/medical: FDA 21 CFR Part 11 requires every validation step to have signed, timestamped, tamper-evident evidence | $500K+ for GxP validation consultant |
| Regression testing | After each data load, re-run ALL validation scripts. Any change means re-test everything | 3-5 test cycles per migration |
| Cutover window | 48-72 hours to migrate, validate, and go-live. Every minute of delay costs the business | $100K+/hour of downtime for large enterprises |
| Audit trail gaps | Auditors ask "who validated this data, when, and what did they see?" — teams scramble to reconstruct evidence | Audit findings → delayed go-live |

**What Solace Browser does for them (the "shut up and take my money" features):**

| Feature | Solace Capability | SAP Migration Impact |
|---------|------------------|---------------------|
| **BAT Automation** | Record a validation script once (navigate SAP Fiori, check field values, compare to source). Replay deterministically across 500 transactions. | 2-4 weeks → 2-4 hours |
| **Business eSign-Off** | When business user approves a validation result, generate Part 11 compliant e-signature: `sha256(user + timestamp + "approved" + evidence_hash)`. Non-repudiable. | Kill the Word doc/email chain. Auditor-ready instantly. |
| **Hash-Chained Evidence** | Every validation step: screenshot + DOM snapshot + network trace + timestamp → SHA-256 hash chain. Tamper-evident. Append-only. | FDA/GxP compliance built-in. No $500K consultant. |
| **Migration Validation Recipes** | Recipe library for common SAP checks: "Verify vendor master data migrated correctly" → recipe checks 50 fields across 1000 vendors | Community recipes reduce consultant dependency |
| **Multi-Tab Comparison** | Open legacy SAP in tab 1, S/4HANA in tab 2. Agent compares field-by-field, screenshots differences, generates deviation report. | Automated data comparison with evidence |
| **Cutover Dashboard** | Sidebar shows: "472/500 transactions validated, 28 remaining, ETA: 45 min, 3 deviations found" | Real-time cutover visibility |
| **Approval Workflow** | Sidebar: "Data Owner: Approved ✓ | Process Owner: Pending | IT: Waiting | Compliance: —" | Kill the email chain. Everyone sees status. |
| **Regression Replay** | Data changed? Re-run ALL 500 validation recipes. Same evidence, same sign-offs, $0.001/replay. | 3 days of regression → 3 hours |
| **Audit Export** | One-click ZIP: all evidence + hash chains + e-signatures + verification script. Hand to auditor. | Audit prep: days → minutes |

**SAP-Specific Killer Features (not in K1-K15):**

| # | Feature | Description |
|---|---------|-------------|
| E1 | **BAT Acceptance Matrix** | Configurable approval matrix: which roles must sign off on which data objects. Maps to SAP org structure. |
| E2 | **Data Comparison Engine** | Multi-tab CDP: read fields from legacy (tab 1) and target (tab 2), flag mismatches automatically |
| E3 | **Cutover Runbook Automation** | Sequential recipe execution with gates: "Don't proceed to step 5 until step 4 is signed off" |
| E4 | **GxP Validation Protocol** | IQ/OQ/PQ templates as recipes: Installation Qualification, Operational Qualification, Performance Qualification |
| E5 | **Deviation Tracking** | When validation finds a mismatch: auto-create deviation record, assign to data steward, track to resolution |
| E6 | **Regulatory Report Generator** | Auto-generate FDA 21 CFR Part 11 compliance report from evidence chains |

**Pricing for SAP customers:**
- Enterprise tier ($188/mo per seat) × 20 validation team seats = $3,760/mo
- vs. $200-400/hr consultant × 160 hours/month = $32,000-64,000/mo
- vs. Tricentis Tosca: $100K+/year for test automation alone
- **ROI: 10-17x cost reduction** — this sells itself

### 21b. Sales Team — Crushing Microsoft Copilot for Sales

**Customer profile:** Gatan VP of Sales, mid-market company ($50M-500M revenue), 20-100 sales reps, currently using Salesforce/HubSpot CRM + considering Microsoft Copilot for Sales ($50/user/mo).

**Market context (2026):** Mid-market AI tool spend grew 58% YoY. Average sales team pays $6,400-16,700/user/year across 5+ tools (data + engagement + intelligence + forecasting + CRM). Microsoft slashed internal Copilot sales targets by up to 50% due to underwhelming adoption. 87% of enterprises using AI sales tools still missed 2025 revenue targets. The U.S. House of Representatives banned Copilot for congressional staff over security concerns.

**The competition:**

| Product | Price | Strengths | Fatal Weakness |
|---------|-------|-----------|---------------|
| Microsoft Copilot for Sales | $50/user/mo ($20 add-on) | Outlook/Teams integration, CRM sync, meeting summaries | Adoption failing (targets slashed 50%). Can't control browser. Can't automate LinkedIn. "Clippy 2.0" perception. Locked in Microsoft ecosystem. |
| Gong | $250-400/user/mo + $50K platform | Best-in-class call intelligence, AI coaching, deal forecasting | Passive intelligence only (tells you what happened, doesn't act). No outbound. No LinkedIn. Extremely expensive. |
| Outreach | $100/user/mo | Multi-step email/call sequences, conversation intelligence (Kaia), AI Agents (Amplify) | No native contact database. No browser automation. Sequences are template-driven. Complex setup. |
| Apollo | $49-119/user/mo | 265M+ contact database, generous free tier, Chrome extension | LinkedIn tasks are MANUAL (no true automation). Confusing credit system ($0.20/overage). Phone accuracy issues. |
| Salesloft/Clari | $100-150/user/mo (merged Dec 2025) | Revenue forecasting (RevDB), pipeline inspection, cadences | Quote-based pricing creates friction. Intelligence-heavy but action-light. No prospecting database. |
| 6sense | $60K-300K/year | Best intent data, ABM, identifies anonymous visitors | Pipeline creation only (not execution). Extremely expensive. No CRM auto-fill. No email. No execution. |

**Why they all lose to Solace Browser:**

Every sales tool above operates in ONE channel (email OR calls OR data). None of them can actually DO things across channels. A VP of Sales doesn't want a tool that tells them what to do — they want a tool that DOES it with their approval.

**Solace Browser Sales Agent — What Gatan Would Kill For:**

| # | Feature | What It Does | Why Copilot Can't |
|---|---------|-------------|-------------------|
| S1 | **LinkedIn Prospecting Autopilot** | Browse LinkedIn, identify ICP matches, send personalized connection requests (20/day, budget-gated). Evidence trail of every action. | Copilot can't control LinkedIn. Period. |
| S2 | **CRM Auto-Fill from Browser** | Rep visits prospect's website → agent extracts: company size, tech stack, recent news, key contacts → pushes to CRM opportunity. Zero typing. | Copilot needs manual CRM entry or basic web scraping |
| S3 | **Meeting Prep Package** | Before a call: agent visits prospect's LinkedIn, website, news, competitors. Builds a 1-page briefing in sidebar. Takes 30 seconds, not 30 minutes. | Copilot summarizes past interactions but doesn't research prospects |
| S4 | **Follow-Up Sequence Engine** | After a meeting: agent drafts follow-up email (context-aware from meeting notes + prospect research), schedules send, tracks opens. Deterministic replay for similar deals. | Copilot drafts emails but can't execute multi-step sequences across LinkedIn + email + CRM |
| S5 | **Competitive Intel Crawler** | Agent monitors competitor websites, pricing pages, job postings. Alerts: "Competitor X just raised prices 15%" or "Competitor Y is hiring 20 SDRs — they're scaling outbound." | Copilot has zero competitive intelligence |
| S6 | **Pipeline Reality Check** | Agent visits each deal's contact on LinkedIn weekly. Flags: "Champion changed jobs" / "Company announced layoffs" / "New decision-maker appeared." Updates CRM automatically. | Copilot relies on stale CRM data |
| S7 | **Multi-Channel Cadence** | Day 1: LinkedIn view profile → Day 2: Connection request → Day 3: InMail → Day 5: Email → Day 8: Follow-up. All automated, all budget-gated, all with evidence. | No tool does cross-channel cadences with browser automation |
| S8 | **Deal Room Evidence** | Every prospect interaction captured: emails sent, LinkedIn messages, meeting recordings, CRM updates. Hash-chained. Shareable with VP for deal review. | Copilot has conversation history but no tamper-evident evidence chain |
| S9 | **Territory Intelligence** | Agent maps your territory: visits 500 company websites, extracts tech stack, employee count, recent funding. Builds scored prospect list overnight via cloud twin. | No sales tool does automated territory research at scale |
| S10 | **Persona-Aware Communication** | Agent uses "Marketing" persona for CMOs, "Technical" persona for CTOs, "Executive" persona for CEOs. Tone, vocabulary, and pitch automatically adjusted. | Copilot has one voice. One size fits all. |

**The knockout punch vs. Microsoft Copilot for Sales:**

```
Microsoft Copilot: "Here's a suggested email draft based on your meeting notes."
Solace Browser:    "I researched the prospect, drafted the email, scheduled the follow-up
                    sequence, updated the CRM, and found 3 similar companies in the territory.
                    Approve all 5 actions? [Approve] [Review Each]"
```

**Copilot is a copilot. Solace is the pilot (with your permission).**

**Pricing for Sales teams (the drug dealer ladder):**
- Free ($0/mo BYOK) — reps get full sidebar, unlimited recipes, unlimited LinkedIn. They bring own API key.
- Pro ($28/mo per seat) × 50 reps = $1,400/mo — the real conversion, unlimited recipes
- vs. Microsoft Copilot ($50/user/mo) × 50 reps = $2,500/mo
- vs. Gong ($250/user/mo) × 50 reps = $12,500/mo + $50K platform fee
- vs. Average sales stack: $6,400-16,700/user/year across 5+ tools
- **Starter is 84% cheaper than Copilot. Pro is 44% cheaper. AND it does 10x more.**

### 21c. Business Acceptance eSign-Off Framework (E1)

Both SAP and Sales customers need the same core capability: **structured business sign-offs with evidence.**

```
Business Acceptance eSign-Off = {
  acceptance_matrix: {
    data_object: "Vendor Master",           # What's being validated
    approvers: [
      { role: "Data Owner",     required: true,  order: 1 },
      { role: "Process Owner",  required: true,  order: 2 },
      { role: "IT Lead",        required: true,  order: 3 },
      { role: "Compliance",     required: true,  order: 4, condition: "if_regulated" },
      { role: "Project Sponsor", required: true, order: 5 }
    ],
    evidence_required: ["screenshots", "field_comparison", "deviation_report"],
    expiry: "72h"  # Re-approval needed if evidence changes
  },

  esign: {
    signature: sha256(user_id + role + timestamp_utc + meaning + evidence_bundle_hash),
    meaning: "business_accepted" | "conditionally_accepted" | "rejected",
    binding: "Part 11 §11.50 compliant — non-transferable, timestamped, meaning-attached",
    condition: "vendor_count < 50 exceptions documented in deviation_log"
  },

  evidence_bundle: {
    hash_chain: "append-only, SHA-256 linked",
    screenshots: "per-step, timestamped",
    field_comparisons: "source vs target, deviations highlighted",
    network_traces: "HAR capture for API calls",
    verification_script: "standalone Python script, no Solace install needed"
  }
}
```

**Why this is a game-changer:**
- SAP migration: Replace weeks of Word docs and email chains with tamper-evident digital sign-offs
- Sales: VP can approve/reject AI-generated outreach sequences with evidence of what was sent
- Compliance: Auditor opens evidence bundle → everything they need in one ZIP
- Legal: e-signatures are Part 11 compliant — legally binding in regulated industries

### 21d. AI Email — Crushing Shortwave, Superhuman, and Spark

**The competition:**

| Product | Price | Strengths | Fatal Weakness |
|---------|-------|-----------|---------------|
| Shortwave | $25/user/mo | AI triage, auto-labels, smart replies, "ask AI about emails" | Locked inside email. Can't check LinkedIn. Can't update CRM. Can't browse. |
| Superhuman | $30/user/mo | Speed, split inbox, follow-up reminders, AI drafts | No automation. Beautiful but manual. $30 for what amounts to a fast email client. |
| Spark AI | $8/user/mo | AI writing, smart inbox, team collaboration | No evidence trail. No approval flow. Basic AI writing. |
| Gmail Gemini | $20/user/mo | Google integration, "help me write", smart compose | Can't leave Gmail. No multi-site workflows. No recipes. |

**Why Solace Browser destroys email AI tools:**

Email AI tools are trapped inside the inbox. They can draft a reply, but they can't:
- Check the sender's LinkedIn to see if they changed jobs
- Look up the sender's company on Crunchbase before replying
- Pull data from Salesforce to personalize the response
- Schedule a follow-up across email + LinkedIn + CRM
- Generate evidence of what was sent and why

| # | Feature | What It Does | Why Email Tools Can't |
|---|---------|-------------|----------------------|
| M1 | **Context-Aware Reply** | Before drafting, agent checks sender's LinkedIn, company website, CRM record, past interactions. Reply is informed by full context, not just email thread. | Email tools only see the inbox |
| M2 | **Multi-Channel Follow-Up** | Reply to email → schedule LinkedIn message 3 days later → update CRM note → calendar reminder. One approval, four actions. | Email tools can only send email |
| M3 | **Evidence-Chained Responses** | Every email sent has SHA-256 evidence: who approved, what context was used, which recipe generated it. Audit-ready. | Email tools have no evidence chain |
| M4 | **Inbox Zero Autopilot** | Agent triages inbox using recipes: auto-categorize, auto-reply to routine, flag urgent, summarize newsletters. All with approval gates. | Shortwave has AI triage but no automation execution |
| M5 | **Template Recipe Library** | Community recipes: "respond to sales outreach" / "follow up on invoice" / "decline meeting politely." Replay at $0.001. | Email tools regenerate from LLM every time ($0.08) |
| M6 | **Attachment Intelligence** | Agent opens attached PDF/spreadsheet, extracts key data, summarizes in sidebar, suggests action. | Email tools can't parse attachments with agent intelligence |

### 21e. AI Marketing / Content / PR — The Content Factory

**The competition:**

| Product | Price | Strengths | Fatal Weakness |
|---------|-------|-----------|---------------|
| Jasper AI | $49-125/mo | Brand voice, campaigns, templates | Generates content but can't publish, distribute, or measure |
| Copy.ai | $36-186/mo | Workflows, content generation at scale | No browser — can't post to LinkedIn, Medium, Substack, Twitter |
| Surfer SEO | $89-219/mo | SEO optimization, SERP analysis | Only content optimization. Can't write, publish, or promote |
| HubSpot Content | $800+/mo | Full marketing stack, workflows | Insanely expensive. Locked into HubSpot ecosystem |
| Buffer/Hootsuite | $6-120/mo | Social scheduling, analytics | No content creation. No AI. Just scheduling. |

**Solace Browser Content & PR Agent:**

| # | Feature | What It Does | Why Content Tools Can't |
|---|---------|-------------|------------------------|
| C1 | **Write → Publish → Promote Pipeline** | Generate blog post → publish to Substack → share on LinkedIn → tweet thread → cross-post to Medium. One recipe, one approval, five platforms. | Content tools generate. They don't publish or promote. |
| C2 | **SEO Research + Content** | Agent crawls top 10 SERP results for target keyword, extracts structure/word count/headings, generates optimized content that beats them. | SEO tools analyze but don't create. Content tools create but don't analyze. |
| C3 | **PR Outreach Autopilot** | Agent finds relevant journalists on Twitter/LinkedIn, personalizes pitch based on their recent articles, sends via email. Budget-gated: max 20 pitches/day. | No PR tool combines journalist research + personalized outreach + budget control |
| C4 | **Content Calendar Automation** | Schedule content across platforms: Monday blog, Tuesday LinkedIn, Wednesday newsletter, Thursday Twitter thread. Recipes replay weekly. | Buffer schedules but doesn't create. Jasper creates but doesn't schedule. |
| C5 | **Competitive Content Monitor** | Agent crawls competitor blogs weekly. Alerts: "Competitor published article on topic X — here's a counter-angle." Suggests response content. | No content tool monitors competitors AND generates counter-content |
| C6 | **Multi-Platform Analytics** | Agent visits Google Analytics, LinkedIn Analytics, Substack dashboard, Twitter Analytics. Builds unified dashboard in sidebar. One view, all platforms. | Analytics tools are siloed per platform |
| C7 | **Brand Voice Recipes** | Record how you write on each platform. Agent replays your voice. LinkedIn: professional. Twitter: casual. Blog: technical. Each is a recipe. | Content tools have "brand voice" but can't replay deterministically |

### 21f. Market Category Summary — One Browser, Every AI Vertical

```
SOLACE BROWSER = AI-Agent Browser that replaces:
  ├── Email AI:     Shortwave ($25) + Superhuman ($30) + Spark ($8)
  ├── Sales AI:     Copilot for Sales ($50) + Gong ($100) + Outreach ($100)
  ├── Content AI:   Jasper ($49) + Copy.ai ($36) + Buffer ($6)
  ├── Enterprise:   SAP validation consultants ($200-400/hr)
  └── Browser AI:   Operator ($20) + Mariner ($250) + Cowork ($20)

TOTAL ADDRESSABLE TOOL SPEND per user: $200-500/mo across 3-5 separate tools
SOLACE BROWSER PRICE: $8/mo (Starter) or $28/mo (Pro) or $88/mo (Team)

The arbitrage: one AI-agent browser replaces 5+ point solutions.
Each tool only sees one channel. Solace sees ALL channels because it IS the browser.
```

---

## 22. The Free Tier Drug Ring: GTM Strategy

> "The first hit is free. The second hit is free. By the third hit, they can't imagine life without it." — Rory Sutherland (applied to value perception)

> "Build a value ladder. Free is the bottom rung. By the time they reach the top, they're not buying a tool — they're buying their transformed identity." — Russell Brunson

### The Addiction Model: What's Free, What's Paid

The free tier must be so good that users feel PAIN when they hit the wall. Not fake pain (arbitrary limits). Real pain (they've automated 5 things and now they need the 6th that requires cloud/team/evidence).

| Feature | Free ($0, local BYOK) | Starter ($8/mo) | Pro ($28/mo) | Team ($88/mo) | Enterprise ($188/mo) |
|---------|----------------------|----------------|-------------|---------------|---------------------|
| **Sidebar** | Full sidebar, all 4 tabs | Same | Same | Same | Same |
| **Apps** | All 18 apps, unlimited | Same | Same | Same | Same |
| **Recipes** | Unlimited (local, BYOK) | Same + managed LLM | Same | Shared team recipes | Custom enterprise recipes |
| **LLM** | BYOK only (bring your own key) | Managed LLM (no API key needed) | Managed LLM included | Same | Same + dedicated capacity |
| **Replay** | Unlimited (local, $0 with BYOK) | Same | Same | Same | Same |
| **LinkedIn** | Unlimited (local) | Same | Same | Team coordination | Multi-profile |
| **Email** | Unlimited (local) | Same | Same | Team templates | Compliance workflows |
| **CRM auto-fill** | Full (local) | Same | Same | Team sync | API integration |
| **Evidence** | Full local, unlimited retention | Same | Cloud sync, 90-day | 1-year + team sharing | Unlimited + SOC2 export |
| **Cloud Twin** | Not available | Not available | 10 hours/mo | 40 hours/mo | Unlimited |
| **eSign** | Local-only signatures | Same | Cloud-synced signatures | Team signatures + matrix | Full Part 11 compliance |
| **Anti-detect** | Unlimited profiles (local) | Same | Same | Same | Same |
| **Content publishing** | Full (local) | Same | Same | Calendar + team | Brand voice library |
| **Prime Wiki** | Read + contribute | Same | Same | Team knowledge base | Private wiki |
| **SAP/Enterprise** | Full local validation | Same | Same | Team validation | BAT + GxP + runbook + audit export |
| **What you're paying for** | Nothing — it's your machine, your key | No API key hassle | Cloud: twin + sync + backup | Collaboration: team + sharing | Compliance: SOC2 + Part 11 + audit |

**The philosophy:** Free is FULLY FUNCTIONAL on your local machine with your own API key. We never cripple local features. You pay for three things:
1. **Starter ($8):** Convenience — managed LLM so you don't need to get/manage an API key
2. **Pro ($28):** Cloud — twin browser runs while you sleep, evidence syncs, backup
3. **Team ($88):** Collaboration — shared recipes, team evidence, coordinated workflows
4. **Enterprise ($188):** Compliance — SOC2 export, Part 11 audit packages, GxP protocols

### The 5-Step Addiction Ladder (Russell Brunson Value Ladder)

```
Step 1: FREE — "Try the sidebar" (the first taste)
  Hook: Install Solace Browser. Sidebar appears. Navigate to LinkedIn.
  Yinyang says: "I see 3 automations for LinkedIn. Want to try one?"
  User runs "discover posts" recipe. FREE. Takes 30 seconds.
  Dopamine hit: "Holy shit, it just did in 30 seconds what takes me 15 minutes."

Step 2: FREE — "Do it again" (building the habit)
  User comes back next day. Runs "LinkedIn react to posts" recipe. FREE.
  Then "Gmail send follow-up" recipe. FREE.
  Then "Google search competitor" recipe. FREE.
  By day 3, they've used 4 recipes and saved 2 hours. They're hooked.

Step 3: FRICTION WALL — "I hate managing API keys" (the convenience pain)
  Free does EVERYTHING locally. No limits. But user needs an Anthropic/OpenAI key.
  Getting a key = sign up, add billing, copy key, paste into settings.
  Some users love BYOK (power users, devs). Most users HATE it.
  "Why can't it just work?" → That's the Starter hook.

Step 4: STARTER ($8/mo) — "Just $8, no more API key BS" (the micro-commitment)
  Same unlimited local features. But now: managed LLM — zero key management.
  $8 is under the "ask my manager" threshold. Expense it on a personal card.
  This is the CRACK STEP — remove friction, not features. Now they're paying.
  User thinks: "I was paying $20/mo for my own Anthropic key anyway."

Step 5: PRO ($28/mo) — "Run it while I sleep" (the cloud conversion)
  Everything from Starter PLUS: Cloud Twin (10 hrs/mo), evidence cloud sync, backup.
  "I set up a LinkedIn cadence last night. Woke up to 12 new connections."
  The cloud twin is the killer — it turns a tool into an employee.
  ROI: $28/mo for a 24/7 assistant. They'll never cancel.

Step 6: TEAM/ENTERPRISE — "My whole team needs this" (the expansion)
  VP sees one rep's 10x productivity. Asks: "Can the whole team use this?"
  Team tier: shared recipes, team evidence, coordinated cadences.
  Enterprise: SAP validation, Part 11 compliance, BAT automation.
  $188/mo × 50 seats = $9,400/mo replacing $50,000+/mo of tools.
```

### The Rory Sutherland Perception Hacks

> "The problem with logic is that it kills magic. And magic is what makes people buy."

| Hack | Implementation | Psychological Effect |
|------|---------------|---------------------|
| **Show time saved** | Sidebar footer: "You saved 47 minutes today" | Loss aversion — they can't go back to manual |
| **Show money saved** | "This recipe costs $0.001. Copilot would charge $0.08." | Anchoring against expensive competitors |
| **Celebrate streaks** | "7-day streak! 🔥 You've saved 5.2 hours this week" | Commitment escalation — breaking streak feels like loss |
| **Show the cloud upgrade** | "Cloud Twin available — run this recipe while you sleep ($28/mo)" | FOMO — they did it manually, the cloud could do it for them |
| **Social proof counter** | "1,247 users ran this recipe today" | Bandwagon + validation |
| **Persona flattery** | "You're in the top 10% of LinkedIn power users" (based on recipe usage) | Identity reinforcement — they become "a Solace user" |
| **Value framing** | "Your Solace Browser is worth $347/mo in tool replacement" | Reframe $28 as 92% discount on equivalent tools |

### The 7 Free Apps That Create Addiction

These must be genuinely useful on free tier — no sandbagging:

| # | App | Why It's Addictive (fully free, BYOK) | What Cloud Adds (Pro $28) |
|---|-----|--------------------------------------|--------------------------|
| 1 | **LinkedIn Discover** | See trending posts in your niche, auto-react, unlimited | Cloud Twin runs overnight, finds prospects while you sleep |
| 2 | **Gmail Smart Reply** | Context-aware replies using your contacts' LinkedIn data | Cloud sync: reply evidence accessible from any device |
| 3 | **Google Search Deep** | Agent searches, summarizes top 10 results, extracts insights | Cloud Twin: scheduled daily competitive research |
| 4 | **HackerNews Scanner** | Find trending tech discussions, auto-upvote your interests | Cloud Twin: morning digest of overnight trending posts |
| 5 | **Reddit Monitor** | Track subreddits, get summaries, draft comments | Cloud Twin: 24/7 subreddit monitoring |
| 6 | **Competitor Watch** | Monitor competitor websites for changes, unlimited | Cloud Twin: hourly checks, alert on pricing/feature changes |
| 7 | **Meeting Prep** | Agent builds 1-page brief from public sources | Team: shared meeting briefs, CRM data integrated |

### Why Enterprises Will Think This Is the Next Internet

> "The internet made information free. Solace Browser makes ACTION free."

| Era | What Changed | Who Won |
|-----|-------------|---------|
| 1995: Web browser | Information became accessible | Netscape, then Google |
| 2007: Smartphone | Information became mobile | Apple, Google |
| 2023: ChatGPT | Information became conversational | OpenAI |
| **2026: AI-Agent Browser** | **Action became automated** | **Solace Browser** |

The enterprise pitch is not "buy our tool." It's: **"Your employees spend 60% of their time doing things a browser agent could do. That's not a productivity problem — it's a structural problem. And it has a structural solution."**

SAP VP of IT hears: "Your $50M migration project has $15M of manual testing that an agent browser can do for $45K/year."

Gatan VP of Sales hears: "Your 50 reps spend 75% of their time NOT selling. Give them a browser agent and watch close rates double."

CMO hears: "Your content team publishes on 5 platforms manually. One recipe publishes everywhere simultaneously."

**The hook is the same every time: "Let me show you 30 seconds of magic." After that, they sell themselves.**

---

## 22b. Model Marketplace: Pick Your Brain, See The Price

> "Transparency creates trust. Trust creates lock-in that no competitor can break." — Rory Sutherland

### The Killer Insight: Let Users Choose Their LLM Per App

Every app in the sidebar shows a **model picker**. The user can choose from any LLM available on their machine or through our managed service:

```
┌─────────────────────────────────────────────────┐
│ Gmail Smart Reply                                │
│ ─────────────────────────────────────────────── │
│ Model:  [▼ Claude 4 Sonnet (local BYOK)     ]  │
│                                                  │
│ Price Comparison (this recipe):                  │
│ ┌───────────────────────────────────────────┐   │
│ │ Model              │ Est. Cost │ Quality  │   │
│ │ ────────────────── │ ──────── │ ──────── │   │
│ │ Claude 4 Sonnet    │ $0.003   │ ★★★★★   │   │
│ │ Gemini 2.5 Flash   │ $0.001   │ ★★★★☆   │   │
│ │ GPT-4o             │ $0.005   │ ★★★★☆   │   │
│ │ Llama 3.3 70B      │ $0.0006  │ ★★★☆☆   │   │
│ │ Solace Managed ✦   │ $0.002   │ ★★★★★+  │   │
│ │   (auto-uplifted)  │          │          │   │
│ └───────────────────────────────────────────┘   │
│                                                  │
│ ✦ Solace Managed includes automatic uplift:      │
│   inbox injection, persona routing, evidence     │
│   chain — our trade secret, your better results. │
│                                                  │
│ [Run Now]  [Schedule]  [View Benchmark]          │
└─────────────────────────────────────────────────┘
```

### Model Sources (Auto-Detected)

| Source | Detection | Available To |
|--------|-----------|-------------|
| **Anthropic API (BYOK)** | `ANTHROPIC_API_KEY` env var | Free tier |
| **OpenAI API (BYOK)** | `OPENAI_API_KEY` env var | Free tier |
| **Google AI (BYOK)** | `GOOGLE_API_KEY` / `gcloud auth` | Free tier |
| **Claude Code CLI** | `which claude` → detect installed | Free tier |
| **Gemini CLI** | `which gemini` → detect installed | Free tier |
| **Codex CLI** | `which codex` → detect installed | Free tier |
| **Antigravity** | `which antigravity` → detect installed | Free tier |
| **Ollama (local)** | `curl localhost:11434/api/tags` | Free tier |
| **Solace Managed** | Starter+ tier (Together.ai/OpenRouter) | $8+/mo |

### Transparent Benchmarks: Let Data Sell For Us

Every recipe has **real benchmark data** from Solace Inspector runs. No marketing fluff — real numbers:

```yaml
# data/default/apps/gmail-inbox-triage/benchmarks.yaml
recipe_id: gmail-inbox-triage
last_updated: 2026-03-07
sample_size: 1247  # real runs across all users (anonymized)
benchmarks:
  claude_4_sonnet:
    avg_cost: 0.0031
    avg_latency_ms: 2400
    quality_score: 94.2    # from /solace-inspector probes
    success_rate: 0.97
    evidence_completeness: 1.0
  gemini_2_5_flash:
    avg_cost: 0.0008
    avg_latency_ms: 1200
    quality_score: 87.1
    success_rate: 0.94
    evidence_completeness: 1.0
  gpt_4o:
    avg_cost: 0.0052
    avg_latency_ms: 3100
    quality_score: 91.8
    success_rate: 0.96
    evidence_completeness: 1.0
  llama_3_3_70b:
    avg_cost: 0.0006
    avg_latency_ms: 4200
    quality_score: 78.3
    success_rate: 0.89
    evidence_completeness: 0.95
  solace_managed:
    avg_cost: 0.0022
    avg_latency_ms: 2600
    quality_score: 97.8    # uplift adds +3-6 points
    success_rate: 0.99
    evidence_completeness: 1.0
    uplift_delta: "+3.6 vs same base model"
```

**How benchmarks are collected:**
1. `/solace-inspector` runs probes on every recipe execution (deterministic, CPU-only)
2. Quality scores measure: output accuracy, evidence completeness, format compliance, safety
3. Aggregated anonymously — no user data, just model × recipe × score
4. Published in the app's `benchmarks.yaml` — fully transparent, anyone can verify
5. Solace Managed's uplift delta is measurable: same base model, with vs without inbox injection

### The Auto-Uplift Trade Secret

When a user pays for Solace Managed ($8+/mo), every LLM call gets **automatic inbox injection** — our trade secret powered by 47 uplift principles (P1-P47) that produce a measurable **3.2x quality improvement**.

**Proven uplift data (from our own self-application experiment — Paper 13):**
- Before uplift: 29/100 quality score
- After uplift: 92/100 quality score
- Delta: **+63 points (3.2x, or +217%)**
- At 33 active principles: multiplicative effect = 1.1^33 = **23.2x theoretical ceiling**
- Individual principles contribute +3 to +9 points each (specific contributions = trade secret)

```
USER (BYOK, free):
  prompt = user's raw prompt
  → model response (baseline quality: ~30/100 on complex tasks)

USER (Solace Managed, $8+/mo):
  prompt = user's raw prompt
  + AUTO-INJECTED: [proprietary uplift stack — trade secret]
    What we reveal: "47 principles, 3.2x measured improvement"
    What we DON'T reveal: which principles, in what order,
      with what weights, using what prompt templates,
      and how they interact multiplicatively.
  → model response (uplifted quality: ~92/100 on same tasks, 3.2x better)
```

**The math is real and verifiable:**
- `/solace-inspector` probes measure before/after on identical tasks
- Self-application experiment: 29 → 92 across 10 quality dimensions (internal report)
- Multiplicative, not additive: miss one principle = lower ceiling, add one = compound gain

**Why this is safe:**
- Users CAN add their own inbox content (prompts, templates, policies, datasets)
- Users CANNOT see the auto-injected uplift stack (our trade secret)
- The uplift is MEASURABLE — Inspector probes show the quality delta
- Competitors can't copy it — they'd need our full uplift stack, persona system, Inspector probes, and recipe-specific tuning
- The 3.2x result is public. HOW we achieve it is not. The interaction effects between principles are the real secret.

**The sales pitch writes itself:**
- Show the benchmark: "Claude 4 Sonnet scores 29/100 raw on this task. With Solace Managed, it scores 92/100. Same model, same price, 3.2x better."
- Show the price: "BYOK costs you $0.003/run but you manage your own key. Managed costs $0.002/run (we negotiate volume) and scores 3.2x higher."
- Let the customer decide. No lock-in. No hidden fees. Pure transparency. The data sells itself.

### Trade Secret Boundary (What We Reveal vs. What We Don't)

| Public (safe to show) | Private (trade secret) |
|----------------------|----------------------|
| "3.2x quality improvement" (the result) | Which 47 principles, in what order |
| "47 uplift principles" (the count) | The prompt templates for each principle |
| Benchmark scores per model | The interaction weights between principles |
| Price per run | The persona routing algorithm |
| "Auto-uplifted" label | The specific inbox injection content |
| Inspector probe methodology (deterministic) | The probe-to-uplift feedback loop |
| Users can add their own inbox content | Our auto-injected inbox content |
| Before/after quality scores | The 10 quality dimensions and their formulas |

**Rule:** The sidebar shows RESULTS (benchmarks, scores, prices). It NEVER shows the uplift prompt content. The `/api/models` endpoint returns quality scores. It NEVER returns the injection payload. Users who select "Solace Managed" see better results — they don't need to know why.

### The Model Marketplace Revenue Model

```
Revenue streams from model marketplace:
1. Managed LLM markup (20% on token cost)     — Starter+ users
2. Volume discount pass-through                — we negotiate better rates
3. Uplift premium (quality justifies price)    — measurable via Inspector
4. Benchmark advertising (optional)            — model providers pay to be listed
5. Enterprise model routing                    — route to cheapest model that meets quality threshold

Cost to us:
- Inspector runs: $0 (CPU-only, deterministic)
- Benchmark collection: $0 (piggybacks on real usage)
- Uplift injection: $0 (prompt prepend, no extra API call)
- Model detection: $0 (local CLI detection)
```

### Why Users Trust Transparent Benchmarks

| Traditional AI Tool | Solace Browser |
|--------------------|-|
| "Our AI is better" (trust us) | Inspector probes prove it (verify yourself) |
| Hidden model behind API | You pick the model, see the price |
| Vendor lock-in to their model | Switch models per app, per run |
| Marketing benchmarks (cherry-picked) | Real benchmarks from real runs (anonymized) |
| No way to compare | Side-by-side comparison in the sidebar |

**The psychology:** When you show transparent pricing and let users choose, they trust you MORE and buy your managed service ANYWAY — because the data shows it's better value. This is the opposite of every SaaS company that hides pricing. Transparency is our competitive moat.

### 22c. Why Flat Pricing Beats Value-Based Pricing (Persona Panel: 5/5 Unanimous)

> "The moment you tie savings to price, the relationship becomes transactional instead of partnership." — Vanessa Van Edwards

**Question asked:** Should we charge based on what we save the customer (value-based) or flat 20% markup on LLM tokens?

**Persona panel result (5/5 FLAT):**

| Persona | Verdict | Key Argument |
|---------|---------|-------------|
| **Rory Sutherland** | FLAT | "Math kills magic. Variable pricing triggers loss aversion every time." |
| **Russell Brunson** | FLAT | "Flat pricing at all tiers, value-based REPORTING at Enterprise." |
| **Seth Godin** | FLAT | "Variable pricing erodes trust. 'How do I know you're calculating savings correctly?'" |
| **Vanessa Van Edwards** | FLAT | "Variable triggers uncertainty, suspicion, cognitive load. Flat triggers control." |
| **Jony Ive** | FLAT | "The most elegant pricing is invisible pricing. One number. Zero decisions." |

**The winning formula:**

```
PRICING:  Flat tiers ($0 / $8 / $28 / $88 / $188) — never changes based on usage
MARKUP:   Flat 20% on managed LLM tokens — predictable, invisible, builds trust
DISPLAY:  Show savings in sidebar footer: "You saved $347 this month"
ENTERPRISE: ROI dashboard for CFO justification: "Team ROI: $47K/quarter"
RENEWAL:  Savings counter sells the renewal — CFO sees $47K savings, $188/mo cost, obviously renews
```

**Why NOT value-based:**
1. **Trust erosion** — "How do you calculate my savings?" creates suspicion
2. **Cognitive load** — user must understand the formula before buying
3. **Unpredictable bills** — variable pricing triggers loss aversion every invoice
4. **Comparison shopping** — flat prices are easy to compare with competitors
5. **Self-serve friction** — value-based requires sales conversations

**The Rory Sutherland insight:** Show savings as MARKETING, not as BILLING. "You saved $47 this month" is a dopamine notification. "$47 × 20% = $9.40 charge" is an anxiety trigger. Same data, opposite emotional response.

**Implementation in sidebar:**

```
┌─────────────────────────────────────────┐
│ ☯ Yinyang                          [●]  │
│ ─────────────────────────────────────── │
│ [Now] [Runs] [Chat] [More]              │
│                                          │
│ ┌─────────────────────────────────────┐ │
│ │ Today's Savings                     │ │
│ │ ⏱ 47 min saved  |  💰 $12.30 saved │ │
│ │ 🔥 7-day streak                     │ │
│ └─────────────────────────────────────┘ │
│                                          │
│ Your plan: Starter ($8/mo)              │
│ This month's LLM usage: $2.40           │
│ vs. equivalent raw API: $14.70          │
│ You're saving 84% with recipes + uplift │
└─────────────────────────────────────────┘
```

The savings counter is the most addictive feature we build. It's free. It costs us nothing. And it makes every renewal a no-brainer.

---

## 23. Regulated Industry Scenarios — The Compliance Moat

Every regulated industry has the same core problem: **humans do repetitive browser-based work, but regulators demand evidence that the work was done correctly, by the right person, at the right time.** Solace Browser is the only tool that solves BOTH problems simultaneously: automate the work AND generate the compliance evidence.

### 23a. CEO / C-Suite Perspective

**What the CEO cares about:** Risk, liability, audit readiness, cost reduction, competitive advantage.

| CEO Question | Solace Browser Answer |
|-------------|----------------------|
| "Can this get us in trouble with regulators?" | Every action has SHA-256 hash-chained evidence. Part 11 compliant e-signatures. Tamper-evident. The tool GENERATES compliance, not risk. |
| "What happens if the AI makes a mistake?" | Nothing happens without human approval. Inbox/outbox model: preview → approve → execute. Budget gates prevent overspend. Timeout = deny. |
| "How do I explain this to the board?" | "We deployed an AI browser that reduced manual testing by 90% while improving audit readiness. ROI: 10-17x. Evidence trail exceeds what we had before." |
| "What's our liability exposure?" | Lower than status quo. Manual processes have human error, lost evidence, missed sign-offs. Solace Browser eliminates all three. |
| "Is our data safe?" | Local-first: data never leaves your machine unless you explicitly sync to cloud. BYOK: your LLM keys, your data. No telemetry. |

### 23b. Clinical Research / Pharma (FDA 21 CFR Part 11)

**The regulatory reality:** Every clinical trial generates thousands of electronic records. FDA requires:
- Audit trails independent of operators (§11.10(e))
- Electronic signatures legally equivalent to handwritten (§11.100)
- System validation with IQ/OQ/PQ documentation
- Data integrity: ALCOA+ (Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available)

| # | Feature | Clinical Research Use Case |
|---|---------|--------------------------|
| R1 | **EDC Validation Recipes** | Record validation of electronic data capture systems (Medidata Rave, Veeva Vault). Replay across 200 CRF pages. |
| R2 | **ALCOA+ Evidence Chain** | Every browser action generates ALCOA+ compliant evidence: who (user_id), what (action), when (UTC timestamp), how (recipe), why (approval meaning) |
| R3 | **CSV/CSA Validation Packages** | Auto-generate Computer System Validation or Computer Software Assurance documentation from evidence chains |
| R4 | **21 CFR Part 11 Audit Export** | One-click export: all evidence + signatures + chain verification. Hand to FDA inspector. |
| R5 | **Multi-Sig Approval Matrix** | Clinical: Investigator → Monitor → Sponsor → QA. Each signs with Part 11 compliant e-signature. |
| R6 | **Deviation Auto-Creation** | When validation finds unexpected data: auto-create CAPA-linked deviation record with evidence |
| R7 | **Audit Trail Viewer** | Sidebar shows full audit trail per record: every view, edit, approval, with timestamps and user IDs |

**Pharma pitch:** "Your CRAs spend 40% of their time on documentation. Solace Browser does the documentation automatically while they do the science."

### 23c. Finance / Banking (SOX, SEC, FINRA)

**The regulatory reality:** Sarbanes-Oxley (SOX) Section 404 requires internal controls documentation. SEC/FINRA require trade surveillance and communications monitoring. Banks need evidence of every process that touches financial data.

| # | Feature | Finance Use Case |
|---|---------|-----------------|
| F1 | **SOX Control Testing** | Record testing of internal controls (access reviews, segregation of duties, reconciliation). Replay quarterly. Evidence-chained. |
| F2 | **Trade Surveillance Recipes** | Agent monitors trading platforms for suspicious patterns. Screenshots evidence. Flags for compliance review. |
| F3 | **Communications Monitoring** | Agent reviews email/LinkedIn for compliance violations (promissory language, unapproved claims). Evidence-chained findings. |
| F4 | **Reconciliation Automation** | Agent opens two financial systems, compares balances field-by-field, generates variance report with screenshots. |
| F5 | **Regulatory Filing Automation** | Agent navigates SEC EDGAR / FINRA Gateway, fills required fields from internal data, captures submission evidence. |
| F6 | **Audit Committee Package** | Auto-compile: control test results + exception reports + remediation evidence + sign-offs → board-ready package. |

**Finance pitch:** "Your SOX testing costs $2M/year in external audit fees. Automate 60% of control tests and cut that to $800K — with better evidence."

### 23d. Healthcare (HIPAA, HITECH)

**The regulatory reality:** HIPAA requires access controls, audit trails, and breach notification for any system touching PHI (Protected Health Information). HITECH adds breach penalties up to $1.5M per violation category.

| # | Feature | Healthcare Use Case |
|---|---------|--------------------|
| H1 | **EHR Workflow Automation** | Agent navigates Epic/Cerner, completes repetitive data entry (patient intake, lab orders, referrals). Evidence-chained. |
| H2 | **Access Audit Recipes** | Quarterly access review: agent checks user accounts across 10+ systems, flags orphaned accounts, captures evidence. |
| H3 | **PHI-Safe Local Execution** | All processing on local machine. PHI never leaves the browser. No cloud sync for healthcare data. HIPAA-safe by architecture. |
| H4 | **Breach Investigation Evidence** | If breach occurs: agent generates complete access log, screenshots of affected systems, timeline of events. |
| H5 | **Prior Authorization Automation** | Agent navigates payer portals, submits prior auth requests, captures confirmation. Saves 45 min per auth (avg). |

**Healthcare pitch:** "Your nurses spend 2 hours/day on EHR data entry. Give them a browser agent that does it in 10 minutes — with HIPAA-compliant evidence that it was done correctly."

### 23e. Government / Military (FedRAMP, ITAR, CMMC)

**The regulatory reality:** Government agencies require FedRAMP authorization for cloud services. Military requires ITAR compliance for defense data. CMMC (Cybersecurity Maturity Model Certification) is mandatory for DoD contractors.

| # | Feature | Government Use Case |
|---|---------|--------------------|
| G1 | **Air-Gapped Local Mode** | Solace Browser runs 100% locally. No internet required. No telemetry. No cloud. Perfect for classified networks. |
| G2 | **CMMC Evidence Generation** | Agent tests security controls per CMMC Level 2/3 requirements. Generates assessment evidence automatically. |
| G3 | **FOIA Response Automation** | Agent searches internal systems for responsive documents. Captures evidence of search methodology. Redacts PII. |
| G4 | **Procurement Automation** | Agent navigates SAM.gov, GSA Advantage, agency portals. Compares bids. Evidence-chained procurement decisions. |
| G5 | **Continuous Monitoring** | Agent runs security checks on schedules: verify patches, check configurations, test access controls. Nightly via cloud twin. |
| G6 | **Supply Chain Risk Assessment** | Agent researches vendors: check OFAC lists, beneficial ownership, cybersecurity posture. Evidence-chained due diligence. |

**Government pitch:** "Your analysts spend 60% of their time on compliance documentation. The browser agent does the documentation while they do the analysis. And it runs air-gapped — no data ever leaves your network."

### 23f. Manager / Department Head Perspective

**What middle management cares about:** Headcount efficiency, team productivity, proving ROI to leadership, reducing overtime.

| Manager Pain | Solace Browser Solution |
|-------------|----------------------|
| "My team is drowning in manual work" | Recipes automate 60-80% of repetitive browser tasks |
| "I can't justify another headcount" | One browser agent = 0.5 FTE of automated work at $28/mo |
| "How do I prove my team's output?" | Evidence dashboard: tasks completed, time saved, cost avoided |
| "What if someone on my team messes up?" | Approval workflow: every action previewed and approved before execution |
| "IT won't approve another tool" | Free tier: runs locally, no IT approval needed. BYOK, no data leaves network |
| "My team uses 8 different tools" | Solace Browser replaces 5+ point solutions from one sidebar |

### 23g. The Compliance Moat — Why Regulated Industries Lock In

```
COMPLIANCE MOAT = Evidence(hash-chain, Part 11) × Approval(matrix, eSign) × Audit(export, verify) × Local(HIPAA, ITAR, air-gap)

Once a regulated company adopts Solace Browser:
1. Their compliance evidence is IN Solace Browser's hash chains
2. Their audit packages REFERENCE Solace Browser's exports
3. Their SOPs are WRITTEN around Solace Browser's approval workflows
4. Their auditors EXPECT the Solace Browser evidence format

Switching cost = re-creating years of compliance evidence in a new format.
This is the deepest moat in enterprise software: compliance lock-in.
Not vendor lock-in (we're source-available). Compliance lock-in (their evidence depends on our format).
```

### Industry Feature Summary

| Feature ID | Industry | Description |
|-----------|----------|-------------|
| R1-R7 | Pharma/Clinical | EDC validation, ALCOA+, CSV/CSA, Part 11, multi-sig, CAPA, audit trail |
| F1-F6 | Finance | SOX testing, trade surveillance, comms monitoring, reconciliation, regulatory filing |
| H1-H5 | Healthcare | EHR automation, access audits, PHI-safe local, breach investigation, prior auth |
| G1-G6 | Government | Air-gapped, CMMC, FOIA, procurement, continuous monitoring, supply chain |
| E1-E6 | SAP/Enterprise | BAT, data comparison, cutover, GxP, deviation tracking, regulatory reports |
| S1-S10 | Sales | LinkedIn, CRM, meeting prep, cadence, competitive intel, territory, persona |
| M1-M6 | Email | Context reply, multi-channel, evidence-chained, inbox zero, templates, attachments |
| C1-C7 | Content/PR | Publish pipeline, SEO, PR outreach, calendar, competitive monitor, analytics, brand voice |

**Total enterprise features: 57** (R7 + F6 + H5 + G6 + E6 + S10 + M6 + C7 + K15 = 68 including killer features)

### 23h. The Global User Who Doesn't Speak English

**The reality:** 75% of the world doesn't speak English as a first language. Most enterprise software is English-first with bolted-on translations. Solace Browser is different: 47 languages from day one (STORY-47 prime), with the sidebar, recipes, personas, and evidence all localized.

| # | Feature | Global User Impact |
|---|---------|-------------------|
| I1 | **47-Language Sidebar** | Every UI element, tab label, button, and error message in the user's language. Not Google Translate — hand-curated locale files. |
| I2 | **Localized Recipes** | Recipe descriptions, step labels, and confirmation messages in the user's language. A Japanese user sees Japanese throughout. |
| I3 | **Persona Language Matching** | Yinyang chat responds in the user's language. The 47 expert personas adapt tone and vocabulary per locale. |
| I4 | **RTL Support** | Arabic, Hebrew, Farsi: full right-to-left layout in sidebar. Not mirrored — properly designed. |
| I5 | **Local-First for Data Sovereignty** | Data stays on the user's machine in their country. No forced cloud sync to US servers. GDPR/LGPD/PIPL compliant by architecture. |
| I6 | **Multi-Language Evidence** | Evidence exports include locale metadata. Auditors in Germany see German labels. Auditors in Japan see Japanese. |
| I7 | **Zero CDN Translation** | All 47 locale files bundled locally. No runtime fetch. Works offline. No dependency on translation API availability. |

**The global pitch:** "Solace Browser speaks your language — literally. 47 languages, fully localized, data stays in your country."

### 23i. European Regulators (GDPR, EU AI Act, eIDAS, NIS2)

**The regulatory reality:** Europe has the world's strictest digital regulations. Any AI tool used by EU companies must comply with GDPR (data protection), the EU AI Act (AI transparency), eIDAS (electronic signatures), and NIS2 (cybersecurity).

| Regulation | Requirement | Solace Browser Compliance |
|-----------|-------------|--------------------------|
| **GDPR** | Data minimization, right to erasure, DPA, cross-border transfer restrictions | Local-first: data never leaves user's machine. No telemetry. Right to erasure = delete local evidence files. No cross-border transfer needed. |
| **EU AI Act (2026)** | AI systems must be transparent, explainable, human-in-the-loop for high-risk | Human-in-the-loop by design (inbox/outbox, preview→approve→execute). Full evidence trail = explainability. Recipe source code = transparency. |
| **eIDAS 2.0** | Electronic signatures must meet EU standards (Simple/Advanced/Qualified) | SHA-256 e-signatures meet Advanced Electronic Signature (AES) requirements. Qualified signatures via integration with EU trust services (future). |
| **NIS2** | Cybersecurity obligations for essential/important entities | Air-gapped local mode. No forced cloud. Security-by-design: CSP, origin validation, no eval(). Evidence of security controls. |
| **Schrems II** | EU personal data cannot be transferred to US without adequate safeguards | Local-first solves this entirely. Free/Starter tier: zero data leaves EU. Pro+ cloud sync: EU-hosted option planned. |
| **DORA** | Digital Operational Resilience Act (financial sector, Jan 2025) | Evidence-chained testing of digital systems. Automated ICT risk management documentation. |

**European enterprise features:**

| # | Feature | EU Compliance Impact |
|---|---------|---------------------|
| EU1 | **GDPR Data Map** | Agent crawls internal systems, maps where personal data lives, generates Article 30 Record of Processing Activities |
| EU2 | **DPIA Automation** | Data Protection Impact Assessment: agent runs through DPIA template, captures evidence per processing activity |
| EU3 | **Cookie Consent Audit** | Agent visits your websites, checks cookie banners for GDPR compliance, screenshots non-compliant pages |
| EU4 | **Right to Erasure Verification** | When a user requests data deletion: agent verifies deletion across all systems, captures evidence of erasure |
| EU5 | **AI Act Transparency Report** | Auto-generate EU AI Act transparency documentation: system purpose, training data summary, human oversight mechanisms |
| EU6 | **eIDAS Signature Integration** | E-signatures compatible with EU trust services. Evidence exports include eIDAS-compliant signature metadata. |
| EU7 | **NIS2 Incident Response** | Agent automates incident response documentation: timeline, impact assessment, notification evidence (72-hour GDPR breach notification) |

**European pitch:** "American AI tools send your data to US clouds and pray for adequacy decisions. Solace Browser runs on your machine, in your country, under your control. GDPR-compliant by architecture, not by policy."

### 23j. The Compliance Feature Matrix Across All Regions

| Capability | US (FDA/SOX/HIPAA) | EU (GDPR/AI Act/eIDAS) | APAC (PIPL/PDPA) | Global |
|-----------|-------------------|----------------------|------------------|--------|
| Local-first execution | Part 11, HIPAA | GDPR Art. 44-49 | PIPL cross-border | Data sovereignty |
| Hash-chained evidence | Part 11 §11.10(e) | eIDAS AES | — | Tamper-evident |
| e-Signatures | Part 11 §11.50/11.70 | eIDAS Art. 25-34 | — | Legally binding |
| Human-in-the-loop | Part 11 (human review) | AI Act Art. 14 | — | Consent-first |
| Audit export | SOX 404, FDA | GDPR Art. 30 | PDPA audit | One-click |
| Air-gapped mode | ITAR, FedRAMP | NIS2 | Government | Classified networks |
| 47 languages | — | EU multilingual | APAC languages | Global workforce |
| Right to erasure | — | GDPR Art. 17 | PIPL Art. 47 | Delete local files |

---

*Paper 47 v8 | Auth: 65537 | Supersedes Paper 04 | AI-Agent Browser — Full Vertical + Global + Compliance Architecture*
