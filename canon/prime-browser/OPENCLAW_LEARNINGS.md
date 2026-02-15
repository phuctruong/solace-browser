# OpenClaw Browser Extension Learnings

**Date:** 2026-02-14
**Source:** /home/phuc/projects/openclaw/assets/chrome-extension/
**Goal:** Steal the best patterns from OpenClaw and upgrade our Solace extension

## Key Patterns to Steal

### 1. Badge Configuration Object (HIGH PRIORITY)

**Current (Solace):**
```javascript
// Individual calls scattered throughout
setBadge("ON", "#00FF00");
setBadge("REC", "#FF0000");
setBadge("ERR", "#FF0000");
```

**Upgrade (from OpenClaw):**
```javascript
const BADGE = {
  on: { text: 'ON', color: '#FF5A36' },
  off: { text: '', color: '#000000' },
  connecting: { text: '…', color: '#F59E0B' },
  error: { text: '!', color: '#B91C1C' },
  recording: { text: 'REC', color: '#FF0000' },
}

function setBadge(tabId, kind) {
  const cfg = BADGE[kind]
  void chrome.action.setBadgeText({ tabId, text: cfg.text })
  void chrome.action.setBadgeBackgroundColor({ tabId, color: cfg.color })
  void chrome.action.setBadgeTextColor({ tabId, color: '#FFFFFF' }).catch(() => {})
}
```

**Benefits:**
- Centralized badge states (single source of truth)
- Per-tab badges (show different status per tab)
- Text color control (white text on colored backgrounds)
- Graceful error handling (catch() for older Chrome versions)

**Implementation Impact:** High - makes status tracking much cleaner

### 2. Per-Tab Session Tracking (HIGH PRIORITY)

**Current (Solace):**
```javascript
let recordingEnabled = false;
let currentSession = null;
// Single global session - doesn't support multiple tabs
```

**Upgrade (from OpenClaw):**
```javascript
/** @type {Map<number, {state:'connecting'|'connected', sessionId?:string}>} */
const tabs = new Map()
/** @type {Map<string, number>} */
const tabBySession = new Map()
/** @type {Map<string, number>} */
const childSessionToTab = new Map()

// Per-tab operations
void chrome.debugger.detach({ tabId }).catch(() => {})
setBadge(tabId, 'connecting')
void chrome.action.setTitle({
  tabId,
  title: 'OpenClaw Browser Relay: disconnected',
})
```

**Benefits:**
- Multiple tabs can have different states
- Map-based lookup for fast access
- JSDoc type annotations for clarity
- Per-tab title updates in toolbar

**Implementation Impact:** Medium - requires refactoring session tracking

### 3. Connection Promise Deduplication (MEDIUM PRIORITY)

**Current (Solace):**
```javascript
async function connect() {
  if (isConnected) return;
  // Connection attempt...
}
```

**Upgrade (from OpenClaw):**
```javascript
let relayConnectPromise = null

async function ensureRelayConnection() {
  if (relayWs && relayWs.readyState === WebSocket.OPEN) return
  if (relayConnectPromise) return await relayConnectPromise

  relayConnectPromise = (async () => {
    // Connection logic...
  })()

  try {
    await relayConnectPromise
  } finally {
    relayConnectPromise = null
  }
}
```

**Benefits:**
- Prevents multiple concurrent connection attempts
- Shared promise for multiple callers
- Cleaner error handling
- Proper promise cleanup

**Implementation Impact:** Medium

### 4. Preflight Health Check (HIGH PRIORITY)

**Current (Solace):**
```javascript
ws = new WebSocket(wsUrl);
ws.onopen = () => {
  // Wait for open event...
};
```

**Upgrade (from OpenClaw):**
```javascript
// Fast preflight: is the relay server up?
try {
  await fetch(`${httpBase}/`, {
    method: 'HEAD',
    signal: AbortSignal.timeout(2000)
  })
} catch (err) {
  throw new Error(`Relay server not reachable at ${httpBase}`)
}

const ws = new WebSocket(wsUrl)
```

**Benefits:**
- Fail fast if server not reachable
- Faster feedback to user
- Clearer error messages
- 2-second timeout prevents hanging

**Implementation Impact:** Medium

### 5. Request/Response Pattern with Pending Map (MEDIUM PRIORITY)

**Current (Solace):**
```javascript
async for (msg in this.ws) {
  response = json.loads(msg)
  if response.get("type") in [expected_types]:
    return response
}
```

**Upgrade (from OpenClaw):**
```javascript
/** @type {Map<number, {resolve, reject}>} */
const pending = new Map()

function requestFromRelay(command) {
  const id = command.id
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject })
    try {
      sendToRelay(command)
    } catch (err) {
      pending.delete(id)
      reject(err)
    }
  })
}

async function onRelayMessage(text) {
  const msg = JSON.parse(text)

  if (msg && typeof msg.id === 'number') {
    const p = pending.get(msg.id)
    if (!p) return
    pending.delete(msg.id)
    if (msg.error) p.reject(new Error(String(msg.error)))
    else p.resolve(msg.result)
  }
}
```

**Benefits:**
- Decouples message sending from response handling
- Supports concurrent commands
- Proper error propagation
- Per-request timeouts possible

**Implementation Impact:** Medium - requires protocol changes

### 6. Options Page Best Practices (MEDIUM PRIORITY)

**Current (Solace):**
```javascript
// Simple form with save button
document.getElementById('save').addEventListener('click', saveOptions)
```

**Upgrade (from OpenClaw):**
```html
<!-- Manifest v3 uses options_ui not options_page -->
"options_ui": { "page": "options.html", "open_in_tab": true }

<!-- CSS uses color-mix for dark/light mode -->
:root {
  color-scheme: light dark;
  --accent: #ff5a36;
  --panel: color-mix(in oklab, canvas 92%, canvasText 8%);
}

<!-- Status indicators with data attributes -->
<div class="status" id="status" data-kind="ok"></div>

.status[data-kind='ok'] {
  color: color-mix(in oklab, #16a34a 75%, canvasText 25%);
}
.status[data-kind='error'] {
  color: color-mix(in oklab, #ef4444 75%, canvasText 25%);
}
```

**Benefits:**
- Dark/light mode support (modern CSS)
- Better visual hierarchy
- Card-based layout is more scannable
- Logo + title header
- Documentation links integrated
- Health check feedback in options

**Implementation Impact:** Low - UI improvement

### 7. Relay Port Configuration (MEDIUM PRIORITY)

**Current (Solace):**
```javascript
const DEFAULT_WS_URL = "ws://localhost:9222";
const config = await getServerConfig();
const wsUrl = config.wsUrl;
```

**Upgrade (from OpenClaw):**
```javascript
const DEFAULT_PORT = 18792

function clampPort(value) {
  const n = Number.parseInt(String(value || ''), 10)
  if (!Number.isFinite(n)) return DEFAULT_PORT
  if (n <= 0 || n > 65535) return DEFAULT_PORT
  return n
}

async function checkRelayReachable(port) {
  const url = `http://127.0.0.1:${port}/`
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 900)
  try {
    const res = await fetch(url, { method: 'HEAD', signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    setStatus('ok', `Relay reachable at ${url}`)
  } catch {
    setStatus('error', `Relay not reachable at ${url}`)
  }
}
```

**Benefits:**
- Robust port validation
- Health check in options page
- Better error messages
- Real-time feedback to user

**Implementation Impact:** Medium

### 8. Manifest v3 Best Practices (LOW PRIORITY)

**Current (Solace):**
```json
{
  "manifest_version": 3,
  "permissions": ["scripting", "webRequest", "tabs", "storage"],
  "host_permissions": ["<all_urls>"],
  "options_page": "options.html"
}
```

**Upgrade (from OpenClaw):**
```json
{
  "manifest_version": 3,
  "permissions": ["debugger", "tabs", "activeTab", "storage"],
  "host_permissions": ["http://127.0.0.1/*", "http://localhost/*"],
  "background": { "service_worker": "background.js", "type": "module" },
  "options_ui": { "page": "options.html", "open_in_tab": true },
  "icons": {
    "16": "icons/icon16.png",
    "32": "icons/icon32.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

**Improvements:**
- Limited host_permissions to localhost (better security)
- "type": "module" for ES modules in background
- "options_ui" with "open_in_tab": true (better UX)
- 4 icon sizes (includes 32px for better resolution)
- No "webRequest" (deprecated in MV3)

**Implementation Impact:** Low

### 9. Error Recovery Pattern (MEDIUM PRIORITY)

**Current (Solace):**
```javascript
ws.onerror = (error) => {
  console.error("[Solace] WebSocket error:", error);
  isConnected = false;
};

ws.onclose = () => {
  isConnected = false;
  setTimeout(connect, 5000); // Retry
};
```

**Upgrade (from OpenClaw):**
```javascript
function onRelayClosed(reason) {
  relayWs = null
  for (const [id, p] of pending.entries()) {
    pending.delete(id)
    p.reject(new Error(`Relay disconnected (${reason})`))
  }

  for (const tabId of tabs.keys()) {
    void chrome.debugger.detach({ tabId }).catch(() => {})
    setBadge(tabId, 'connecting')
    void chrome.action.setTitle({
      tabId,
      title: 'OpenClaw Browser Relay: disconnected'
    })
  }
  tabs.clear()
}
```

**Benefits:**
- Rejects all pending requests
- Updates UI per-tab
- Clears state on disconnection
- Provides user feedback

**Implementation Impact:** Medium

### 10. Listener Installation Guard (LOW PRIORITY)

**Current (Solace):**
```javascript
// Listeners installed multiple times
chrome.tabs.onUpdated.addListener(handler);
```

**Upgrade (from OpenClaw):**
```javascript
let debuggerListenersInstalled = false

if (!debuggerListenersInstalled) {
  debuggerListenersInstalled = true
  chrome.debugger.onEvent.addListener(onDebuggerEvent)
  chrome.debugger.onDetach.addListener(onDebuggerDetach)
}
```

**Benefits:**
- Prevents duplicate listener registration
- Cleaner teardown logic

**Implementation Impact:** Low

## Implementation Priority

### Phase 1 (CRITICAL)
1. Badge configuration object + per-tab badges
2. Per-tab session tracking
3. Preflight health check
4. Manifest improvements (options_ui, host_permissions)

### Phase 2 (HIGH)
5. Options page dark/light mode + health check
6. Connection promise deduplication
7. Error recovery per-tab

### Phase 3 (MEDIUM)
8. Request/response with pending map (protocol change)
9. Listener installation guard

### Phase 4 (POLISH)
10. Additional icon sizes (32px)

## Twin AI + Playwright Specific Notes

OpenClaw's architecture is CDP-focused (Chrome DevTools Protocol) which is different from our Twin AI + Playwright focus. However, many patterns are directly applicable:

- **Badge system:** Perfect for showing recording state
- **Per-tab tracking:** Essential when recording from multiple tabs
- **Health checks:** Critical for determinism (must know server state)
- **Options page:** Configuration for server URL/port
- **Error recovery:** Handles network failures gracefully

## Files to Update

```
canon/prime-browser/extension/
├── background.js (HIGH IMPACT)
│   - Add BADGE constant
│   - Refactor setBadge() to per-tab
│   - Add per-tab session tracking
│   - Add health checks
│   - Improve error recovery
├── manifest.json (MEDIUM IMPACT)
│   - Change options_page → options_ui
│   - Limit host_permissions to localhost
│   - Add "type": "module"
│   - Add 32px icons
├── options.html (MEDIUM IMPACT)
│   - Add dark/light mode support
│   - Add health check display
│   - Improve layout and styling
├── options.js (MEDIUM IMPACT)
│   - Add checkRelayReachable()
│   - Add port validation
│   - Add AbortController timeout
└── images/ (LOW IMPACT)
    - Add icon32.png (from openclaw)
```

## Measurements

| Pattern | Current | Upgraded | Improvement |
|---------|---------|----------|-------------|
| Badge states | Scattered calls | BADGE object | Centralized |
| Per-tab status | Global state | Map<tabId> | Multi-tab |
| Connection attempts | Concurrent | Promise dedupe | Race-condition free |
| Error feedback | Vague | Per-tab titles | User-friendly |
| Options page | Basic form | Card-based UI | Professional |
| Health checks | Implicit | Explicit + user display | Fail-fast |
| Color support | 6 colors | Dark/light mode aware | Future-proof |
| Icon resolution | 3 sizes | 4 sizes | Sharper on 2x displays |

## Test Plan

After implementing these upgrades:

1. **Badge System Tests**
   - [ ] Badge shows correct state for each tab
   - [ ] Text color is readable on backgrounds
   - [ ] Graceful fallback on older Chrome

2. **Per-Tab Tracking Tests**
   - [ ] Open 3 tabs, record in different tabs
   - [ ] Each tab shows correct session
   - [ ] Detaching one tab doesn't affect others

3. **Health Check Tests**
   - [ ] Options page shows "Relay reachable" when server up
   - [ ] Options page shows error when server down
   - [ ] 900ms timeout prevents hanging

4. **Error Recovery Tests**
   - [ ] Server crash → badge shows error per-tab
   - [ ] Pending requests rejected properly
   - [ ] User can re-attach after server restart

5. **Options Page Tests**
   - [ ] Dark mode renders correctly
   - [ ] Port validation clamps to 0-65535
   - [ ] Save/restore settings persists
   - [ ] Documentation links work

---

**Auth:** 65537
**Northstar:** Phuc Forecast (DREAM → FORECAST → DECIDE → ACT → VERIFY)
**Verification:** 641 → 274177 → 65537

*"Every pattern in OpenClaw teaches us how to build deterministic, fail-safe, user-friendly automation."*
