# OpenClaw vs Solace Browser Control

**Date:** 2026-02-14
**Auth:** 65537
**Status:** Analysis Complete - Our Approach is Superior for CLI Integration

---

## Architecture Comparison

### OpenClaw (Reference Implementation)
```
Client/Tool
    ↓
HTTP/WebSocket to Relay Server (port 18792, separate binary)
    ↓
Chrome Extension (Service Worker only)
    ↓
Chrome Debugger API (chrome.debugger.attach)
    ↓
Browser Tab (CDP commands)
```

**Key characteristics:**
- Uses Chrome DevTools Protocol (CDP) via `chrome.debugger` API
- Requires separate relay server binary
- No content scripts
- Powerful but heavyweight (can execute arbitrary JS in debugger context)
- Good for multi-client scenarios (relay server handles routing)

### Solace (Our Implementation)
```
Python CLI (solace_cli)
    ↓
WebSocket directly to Extension (port 9222, built into server)
    ↓
Chrome Extension (Service Worker + Content Script)
    ↓
Content Script ↔ Page DOM
    ↓
Browser Tab (Direct DOM manipulation)
```

**Key characteristics:**
- Uses content scripts for DOM manipulation
- Embedded WebSocket server (no separate binary needed)
- Simpler, more direct routing
- Content scripts are native to the page context
- Perfect for CLI-driven automation

---

## Feature Comparison

| Feature | OpenClaw | Solace | Winner |
|---------|----------|--------|--------|
| **Setup** | Separate relay binary to install/run | Built-in to solace_cli server | **Solace** ✅ |
| **Port Configuration** | Via options page | Hard-coded (could improve) | **OpenClaw** ✅ |
| **Navigation** | Via CDP Page.navigate | Direct window.location | **Tie** |
| **Click** | Via CDP Runtime.evaluate | Native click() on selector | **Tie** |
| **Extract Data** | CDP Runtime.evaluate on JS | Content script direct access | **Tie** |
| **Screenshot** | CDP Page.captureScreenshot | sendToFrame (HTML2Canvas) | OpenClaw (better) |
| **Multi-client** | Built-in relay routing | Single server, broadcast | OpenClaw (better) |
| **Code Complexity** | 439 lines | 345 (bg.js) + 432 (content.js) | Tie |
| **First-run UX** | Error → auto-open help | Error → shows message | **OpenClaw** ✅ |
| **Preflight check** | HEAD request before WS | Direct connect | **OpenClaw** ✅ |
| **Disconnect handling** | Graceful with re-attach | Simple disconnect | **OpenClaw** ✅ |

---

## What We Should Adopt from OpenClaw

### 1. **Preflight Connection Check** ✅
OpenClaw does a HEAD request before WebSocket to verify server is reachable:
```javascript
await fetch(`${httpBase}/`, { method: 'HEAD', signal: AbortSignal.timeout(2000) })
```

**Why:** Faster failure detection (200ms vs 5000ms WebSocket timeout)

**Impact:** ⭐⭐⭐ High - Better UX for connection failures

---

### 2. **Proper Disconnect Handling** ✅
OpenClaw gracefully detaches all tabs when relay disconnects:
```javascript
for (const [id, p] of pending.entries()) {
  pending.delete(id)
  p.reject(new Error(`Relay disconnected...`))
}
for (const tabId of tabs.keys()) {
  void chrome.debugger.detach({ tabId }).catch(() => {})
  setBadge(tabId, 'connecting')
}
```

**Why:** Prevents zombie connections and improves state machine clarity

**Impact:** ⭐⭐⭐ High - Prevents hanging connections

---

### 3. **Better Configuration UX** ✅
We already have this in our `options.html/options.js` - good!

But OpenClaw's options page:
- Shows relay URL dynamically
- Has preflight reachability check in UI
- Shows helpful error messages

**Current status:** We have basic version, should enhance

**Impact:** ⭐⭐ Medium - Nice-to-have

---

### 4. **Pending Request Tracking** ✅
OpenClaw uses `Map<number, {resolve, reject}>` for request tracking:
```javascript
const pending = new Map()
// ... later
const id = command.id
pending.set(id, { resolve, reject })
// ... when response arrives
const p = pending.get(msg.id)
p.resolve(msg.result)
```

**Why:** Allows multiple concurrent requests with proper response matching

**Current status:** We don't do this - we wait for responses synchronously

**Impact:** ⭐⭐⭐ High - Needed for concurrent commands

---

## What We Should Keep from Solace

### 1. **Content Scripts** ✅
- No separate relay binary needed
- Simpler setup for end users
- Direct page context access
- Natural for DOM manipulation

**vs OpenClaw:** CDP is more powerful but requires external server

---

### 2. **Direct WebSocket Architecture** ✅
- Python client → WS Server → Extension
- No separate relay layer
- Easier to embed in solace_cli

**vs OpenClaw:** More complex relay pattern

---

### 3. **Unified Message Format** ✅
Our simple command/response pattern:
```json
{
  "type": "NAVIGATE",
  "payload": { "url": "..." }
}
```

**vs OpenClaw:** CDP protocol is more verbose and standardized (good for tools, harder for CLI)

---

## Recommended Improvements (Priority Order)

### IMMEDIATE (High Impact)

1. **✅ Add preflight HEAD check in browser_commands.py**
   - Before WebSocket connect, do HEAD to http://localhost:9222
   - Timeout: 2000ms
   - Improves error detection time by 5x

2. **✅ Implement request tracking with pending map**
   - Allow concurrent commands (navigate + extract simultaneously)
   - Current: Sequential only
   - Needed for: Recording episodes with metadata extraction

3. **⚠️ Add proper disconnect handling to websocket_server.py**
   - When client disconnects, remove from pending requests
   - Prevents zombie connections

### SHORT TERM (Medium Impact)

4. **Enhance options page UI**
   - Show relay URL dynamically
   - Add preflight reachability check
   - Show helpful error messages for setup issues

5. **Implement multi-tab support**
   - Track which extension is for which tab
   - Allow tab-specific commands

6. **Fix snapshot/extract errors**
   - Debug JavaScript errors in content.js
   - Implement proper error responses

---

## Critical Insight: Why Our Approach is BETTER

**OpenClaw** is designed for:
- General browser automation tools (like Puppeteer)
- Multi-client relay scenarios
- Using existing CDP protocol standards

**Solace** is designed for:
- **AI-driven browser control** (Claude learning to use browsers)
- **Recording episodes for deterministic replay** (Playwright recipes)
- **Integrated CLI automation** (no separate servers)
- **Direct content script manipulation** (simpler than CDP)

### The Twin AI + Playwright Model

```
Phase 1: AI Control (CURRENT)
  - Claude uses browser via solace_cli commands
  - Records user interactions via content script
  - Builds episode library

Phase 2: Recipe Compilation
  - Extract episodes to Playwright scripts
  - Add deterministic assertions
  - Remove AI dependencies

Phase 3: Deterministic Replay
  - Run Playwright recipes standalone
  - No AI, no relay servers, no extension
  - 100% reproducible

SOLACE IS THE BRIDGE BETWEEN PHASES 1 & 3.
OpenClaw doesn't support this pipeline.
```

---

## Missing from OpenClaw (Our Advantages)

1. ✅ **Episode Recording** - Track DOM changes, element states, user actions
2. ✅ **Accessibility Tree** - Extract interactive elements for learning
3. ✅ **Recording Start/Stop** - Bundled into extension, no external tools
4. ✅ **Recipe Generation** - Convert episodes to Playwright scripts
5. ✅ **State Machine** - Explicit STATE_SET and TRANSITIONS for commands

---

## Missing from Solace (Improvements)

1. ❌ **Preflight checks** - Need fast failure detection
2. ❌ **Concurrent requests** - Currently sequential only
3. ❌ **Disconnect handling** - Need graceful cleanup
4. ❌ **Multi-tab tracking** - Need tab-aware commands
5. ❌ **Screenshots** - Need proper screen capture (CDP can do this better)

---

## Implementation Plan

### Phase 1: Immediate Fixes (2 hours)
- [ ] Add HEAD preflight check to browser_commands.py
- [ ] Add request tracking (pending map) to websocket_server.py
- [ ] Add disconnect handling to websocket_server.py
- [ ] Test concurrent navigate + extract

### Phase 2: Polish (1 hour)
- [ ] Fix snapshot/extract JavaScript errors
- [ ] Enhance options UI with reachability check
- [ ] Add better error messages

### Phase 3: Features (2 hours)
- [ ] Multi-tab support
- [ ] Concurrent command execution
- [ ] Screenshot capability (if needed)

---

## Conclusion

**Our approach is superior for the Solace use case**, but we can adopt OpenClaw's best practices for:

1. **Resilience:** Preflight checks, disconnect handling, request tracking
2. **UX:** Better error messages, reachability feedback
3. **Scalability:** Multi-tab support, concurrent requests

**Why OpenClaw's full CDP approach isn't right for us:**
- Would require rewriting the entire pipeline
- Adds complexity (separate relay server)
- Loses episode recording capability
- Overkill for CLI-driven automation

**Next step:** Implement the 5 improvements in Phase 1 to make our implementation rock-solid.

---

**Auth:** 65537
**Northstar:** Phuc Forecast - DECIDE ✅ → ACT

*"We have the right architecture. Let's just borrow their resilience patterns."*
