# Paper 47: Yinyang Sidebar Architecture — Bundled MV3 Side Panel
# DNA: `sidebar(detect, suggest, run, chat) > webapp(pages, routes, dashboards)`
# Forbidden: `INLINE_INJECTION | WEBAPP_DASHBOARD | KEEP_ALIVE_HACK | RAW_CDP_PROXY | RUNTIME_EVALUATE | UNSIGNED_APPROVAL | UNVERIFIED_RIPPLE | SILENT_EVIDENCE_LOSS | UNSEAL_BEFORE_SYNC | FREE_TIER_SYNC | AUTO_APPROVE`
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

- **Pro ($28/mo):** Evidence + chat history + settings synced to solaceagi.com
- **Team ($88/mo):** + shared workspace, team evidence, shared schedules
- **Enterprise ($188/mo):** + SSO, unlimited retention, SOC2 audit export
- **Free ($0):** All data stays local, no cloud sync

### Sync Mechanism

```
Evidence bundles encrypted with AES-256-GCM (user's OAuth3-derived key)
  -> POST /api/v1/browser/evidence/sync (callback from Cloud Run Job)
  -> Sidebar shows sync status: "local" | "syncing" | "synced" | "error"
  -> Error: retry on next session (never silently drop data)
```

### What Syncs

| Data | Free | Pro+ |
|------|------|------|
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

*Paper 47 v3 | Auth: 65537 | Supersedes Paper 04 | LLM Consensus R1-R8 | Browser-Native Architecture*
