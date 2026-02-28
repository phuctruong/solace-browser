# TODO — Solace Browser (Browser Vertex — Yinyang Sprint)

**Project:** solace-browser — Headless Chromium + CDP + React frontend
**Stack:** Python 3.10 (Playwright, aiohttp), React/TypeScript (Vite), PyInstaller
**Tests:** `cd /home/phuc/projects/solace-browser && python -m pytest tests/ -x -q`
**Binary:** `python -m PyInstaller solace-browser.spec --clean --noconfirm`
**Current Sprint:** Yinyang Chat Rail — browser integration via Playwright injection + CDP
**Paper:** `solaceagi/papers/22-yinyang-chat-rail-proposal.md`

---

## Previous Sprint Status: ALL 6 TASKS DONE (2026-02-28)

All tasks at Rung 641:
- TASK-001: Sync client integrated into startup (heartbeat + background loop)
- TASK-002: CI pipeline for macOS/Windows/Linux binaries (GitHub Actions)
- TASK-003: Evidence auto-upload after Part 11 seal
- TASK-004: --version flag added
- TASK-005: 3 new recipes (Slack, GitHub, Notion)
- TASK-006: competitive_features null guards on all call sites

---

## PHASE 1: PLAYWRIGHT INJECTION (Top + Bottom Rails)

### TASK-001: Implement top status rail via Playwright injection

**Status:** READY
**Priority:** P0
**Rung Target:** 641
**Diagram:** `solace-cli/src/diagrams/13-yinyang-fsm.md` (when created)
**Files:** `src/yinyang/top_rail.py` (new), `src/yinyang/top_rail.js` (new)

Inject a compact, always-visible status rail below the address bar on every automated page.

**Implementation (Tier 1: Playwright `add_init_script()`):**
```python
# In browser automation, inject on every page:
await page.add_init_script(TOP_RAIL_JS)  # Survives same-context navigations
```

**Top rail content (one line, compact):**
```
[Yinyang avatar] | [Mode badge] | [Current step text] | [Step X of Y] | [State] | [Actions: Review | Pause | Stop]
```

**States to display (from FSM diagram 13):**
- IDLE: grey, "Ready"
- LISTENING: blue, "Listening..."
- PROCESSING: blue pulse, "Processing..."
- EXECUTING: green, "Step X of Y"
- WAITING FOR APPROVAL: orange flash, "Approval required"
- BLOCKED: red, "Blocked: [reason]"
- DONE: green, "Complete"
- ERROR: red, "Error: [message]"

**Requirements:**
1. Fixed position, top 0, full width, 32px height, z-index max
2. Push page content down with `document.body.style.marginTop`
3. Dark theme matching solaceagi design tokens (`#0a0e27` bg, `#f4f7fb` text)
4. State updates via `page.evaluate()` from Python
5. Action buttons (Review/Pause/Stop) send events back to Python via `window.__solaceAction`
6. Survives navigation within same browser context

**Acceptance:**
- Rail visible on every automated page
- All 8 FSM states render correctly with colors
- Action buttons functional
- Does not break page layout
- Tests: `pytest tests/test_yinyang_top_rail.py` passes

---

### TASK-002: Implement bottom chat rail via Playwright injection

**Status:** READY
**Priority:** P0
**Rung Target:** 641
**Diagram:** `solace-cli/src/diagrams/15-yinyang-data-flow.md` (when created)
**Files:** `src/yinyang/bottom_rail.py` (new), `src/yinyang/bottom_rail.js` (new)
**Dependencies:** TASK-001 (shares injection infrastructure)

Inject an expandable chat rail at the bottom of every automated page.

**Bottom rail layout:**
- **Collapsed (default):** 36px bar, "Solace Assistant", expand chevron
- **Expanded:** 300px, two columns:
  - Left: chat transcript + composer input
  - Right: recipe step accumulation (max 12 steps)

**Requirements:**
1. Fixed position, bottom 0, full width, expandable
2. Collapse/expand toggle via click on header
3. Chat messages sent via `window.__solaceSendMessage(text)` → Python picks up
4. Python pushes responses via `page.evaluate("window.__solaceReceiveMessage(msg)")`
5. Recipe steps synced between rail and Python
6. Session state persisted in `window.__solaceYinyangState`
7. Port existing patterns from `semantic-rungs.js`:
   - Page context collection (actions, fields, headings)
   - Action chips (Summarize, Suggest Click, Suggest Fields, Build Recipe)
   - Message rendering (user/assistant, timestamps)
   - Step rendering (toggle done/undone, max 12)

**Acceptance:**
- Rail collapses/expands smoothly
- Chat messages round-trip to Python and back
- Recipe steps accumulate and persist
- Page context sent to Python on each message
- Tests: `pytest tests/test_yinyang_bottom_rail.py` passes

---

### TASK-003: Implement CDP DOM highlighting

**Status:** READY
**Priority:** P0
**Rung Target:** 641
**Files:** `src/yinyang/highlighter.py` (new)

Use Chrome DevTools Protocol `Overlay.highlightNode` for native element targeting. This is the same technique Chrome DevTools uses — compositor-level, immune to CSP, handles scrolling.

**Implementation:**
```python
async def highlight_element(page, selector, label="TARGET"):
    cdp = await page.context.new_cdp_session(page)
    await cdp.send("Overlay.enable")
    doc = await cdp.send("DOM.getDocument")
    result = await cdp.send("DOM.querySelector", {
        "nodeId": doc["root"]["nodeId"],
        "selector": selector
    })
    await cdp.send("Overlay.highlightNode", {
        "nodeId": result["nodeId"],
        "highlightConfig": {
            "showInfo": True,
            "contentColor": {"r": 0, "g": 255, "b": 136, "a": 0.3},
            "borderColor": {"r": 0, "g": 255, "b": 136, "a": 0.9},
        }
    })

async def clear_highlights(cdp):
    await cdp.send("Overlay.hideHighlight")
```

**Requirements:**
1. Highlight any element by CSS selector
2. Custom colors matching Solace brand (green for targets, purple for suggestions)
3. Optional label badge above highlighted element
4. Auto-clear after 3 seconds (configurable)
5. Re-apply after page interactions (CDP overlays are transient)
6. Also inject a JS-based highlight fallback via `add_init_script()` for pages where CDP doesn't render (e.g., PDF viewers)

**Acceptance:**
- CDP highlighting works on standard web pages
- JS fallback works when CDP overlay doesn't render
- Highlights clear automatically
- Tests: `pytest tests/test_yinyang_highlighter.py` passes

---

## PHASE 2: STATE BRIDGE

### TASK-004: Bridge Yinyang to existing tab state machine

**Status:** READY
**Priority:** P1
**Rung Target:** 641
**Files:** `src/yinyang/state_bridge.py` (new), `src/solace/phase4/state_machine.py` (read)
**Dependencies:** TASK-001

Connect the top rail to the existing tab state machine so the rail reflects real browser state.

**Mapping (tab states → Yinyang top rail display):**
```
Tab: IDLE       → Rail: "Ready"          (grey)
Tab: CONNECTED  → Rail: "Connected"      (blue)
Tab: NAVIGATING → Rail: "Navigating..."  (blue pulse)
Tab: CLICKING   → Rail: "Clicking [target]" (green)
Tab: TYPING     → Rail: "Typing in [field]" (green)
Tab: RECORDING  → Rail: "Recording..."   (green)
Tab: ERROR      → Rail: "Error: [msg]"   (red)
```

**Requirements:**
1. Subscribe to tab state machine transitions
2. On each transition, update top rail via `page.evaluate()`
3. Bidirectional: top rail "Stop" button → triggers state machine STOP
4. Multiple tabs: rail shows active tab's state only

**Acceptance:**
- Tab state changes reflected in top rail within 100ms
- Stop button halts automation
- Works with recipe execution flow
- Tests: `pytest tests/test_yinyang_state_bridge.py` passes

---

### TASK-005: WebSocket bridge between injected JS and Python

**Status:** READY
**Priority:** P1
**Rung Target:** 641
**Files:** `src/yinyang/ws_bridge.py` (new)
**Dependencies:** TASK-001, TASK-002

Create a local WebSocket server in aiohttp that bridges the injected JS rails to the Python automation engine.

**Architecture:**
```
Injected JS (top rail + bottom rail)
  ↕ WebSocket (ws://localhost:{port}/ws/yinyang)
Python aiohttp server
  ↕ HTTP/WebSocket
solaceagi.com backend (for LLM routing + persistence)
```

**Message protocol (local WebSocket):**
```
JS → Python:
  { "type": "user_message", "content": "...", "page_context": {...} }
  { "type": "action", "action": "stop" | "pause" | "approve" | "reject" }
  { "type": "recipe_step", "text": "...", "source": "chat" }

Python → JS:
  { "type": "state_update", "state": "executing", "step": 3, "total": 5 }
  { "type": "assistant_message", "content": "..." }
  { "type": "highlight", "selector": "button#submit", "label": "CLICKING" }
  { "type": "recipe_update", "steps": [...] }
```

**Requirements:**
1. aiohttp WebSocket route at `/ws/yinyang`
2. Injected JS connects on bootstrap, reconnects on navigation
3. Python routes user messages to solaceagi.com chat API (or local LLM)
4. State updates pushed to JS on every tab state transition
5. Highlight commands trigger both CDP overlay + JS fallback

**Acceptance:**
- JS connects, sends message, receives response
- State updates flow in real-time
- Reconnection after navigation
- Tests: `pytest tests/test_yinyang_ws_bridge.py` passes

---

## PHASE 3: TESTS + PROMOTION

### TASK-006: Yinyang integration tests

**Status:** READY
**Priority:** P1
**Rung Target:** 641
**Files:** `tests/test_yinyang_integration.py` (new)
**Dependencies:** TASK-001 through TASK-005

End-to-end tests for the full Yinyang rail system.

**Test plan (15+ tests):**

1. **Top rail (4 tests):**
   - Rail appears on page load
   - State updates render correct text + color
   - Stop button sends action event
   - Rail survives page navigation

2. **Bottom rail (4 tests):**
   - Rail collapses/expands
   - Send message → receive response
   - Recipe step accumulates
   - Page context collected and sent

3. **CDP highlighting (3 tests):**
   - Highlight element by selector
   - Clear highlights
   - Auto-clear after timeout

4. **State bridge (2 tests):**
   - Tab state change → rail update
   - Rail action → state machine command

5. **WebSocket bridge (2 tests):**
   - Full message round-trip (JS → Python → API → Python → JS)
   - Reconnection after navigation

**Acceptance:**
- 15+ tests all pass
- `pytest tests/test_yinyang*.py -v` → all green
- No flaky tests

---

### TASK-007: Rung 274177 — Yinyang replay stability

**Status:** BLOCKED (by TASK-006)
**Priority:** P1
**Rung Target:** 274177
**Dependencies:** TASK-006

Run full test suite 3 times. All runs identical.

**Acceptance:**
- 3 consecutive identical test runs
- Zero flaky tests
- All Yinyang tests included in the run

---

## Execution Order

```
PHASE 1 — PLAYWRIGHT INJECTION (parallel where possible):
  TASK-001: Top status rail (Playwright add_init_script)
  TASK-002: Bottom chat rail (Playwright add_init_script)
  TASK-003: CDP DOM highlighting (Overlay.highlightNode)

PHASE 2 — STATE BRIDGE (sequential):
  TASK-004: Bridge to tab state machine
  TASK-005: WebSocket bridge (JS ↔ Python ↔ Cloud)

PHASE 3 — TESTS + PROMOTION:
  TASK-006: Integration tests (15+)
  TASK-007: 3x replay for rung 274177
```

---

**Total:** 7 tasks. Injection first (3 parallel), then bridge (2 sequential), then test + promote.
**Previous sprint:** 6/6 tasks done at Rung 641. All sync, binary, evidence, recipe work complete.
**Target:** Full Yinyang dual-rail in browser via Playwright injection + CDP.
