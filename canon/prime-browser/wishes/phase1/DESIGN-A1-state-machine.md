# DESIGN-A1: Per-Tab State Machine

**Status:** Design Complete - Ready for Solver
**Auth:** 65537
**Date:** 2026-02-14

---

## Architecture Overview

The state machine is a shared module used by both the Python server side (`solace_cli/`) and the JavaScript extension side (`extension/background.js`). Each side maintains its own per-tab state map. The Python side is the source of truth for validation; the extension side mirrors state for badge updates and local guard logic.

```
                    ┌─────────────────────────────────────────────────────┐
                    │              extension/background.js                │
                    │                                                     │
                    │   ┌───────────────────────────────────────────┐     │
                    │   │       tabStates: Map<tabId, TabStateObj>   │     │
                    │   │                                           │     │
                    │   │   tab_1: { state: CONNECTED, ... }        │     │
                    │   │   tab_2: { state: RECORDING, ... }        │     │
                    │   │   tab_3: { state: NAVIGATING, ... }       │     │
                    │   └───────────────────┬───────────────────────┘     │
                    │                       │                             │
                    │         ┌─────────────┼─────────────┐              │
                    │         v             v             v              │
                    │   transitionTab  handleCommand  getTabState        │
                    │   State()        ()             ()                 │
                    │         │             │             │              │
                    │         v             v             v              │
                    │   auditLog Map  validated      GET_STATUS          │
                    │                 dispatch                           │
                    └──────────────────────┼─────────────────────────────┘
                                           │ WebSocket
                                           v
                    ┌─────────────────────────────────────────────────────┐
                    │     solace_cli/browser/state_machine.py (NEW)       │
                    │                                                     │
                    │   TabState (dataclass)                              │
                    │   TabStateManager (thread-safe manager)             │
                    │     .create_tab(tab_id)                             │
                    │     .transition(tab_id, new_state, reason)          │
                    │     .get_tab(tab_id)                                │
                    │     .remove_tab(tab_id)                             │
                    │     .get_audit_log(tab_id)                          │
                    │   InvalidTransitionError                            │
                    └─────────────────────────────────────────────────────┘
```

---

## Data Structures

### 1. TabState (Python - new file: `solace_cli/browser/state_machine.py`)

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
import threading

VALID_STATES = frozenset({
    "IDLE", "CONNECTED", "NAVIGATING", "CLICKING",
    "TYPING", "RECORDING", "ERROR"
})

VALID_TRANSITIONS = {
    "IDLE":       ["CONNECTED"],
    "CONNECTED":  ["NAVIGATING", "CLICKING", "TYPING", "RECORDING", "ERROR"],
    "NAVIGATING": ["CONNECTED", "ERROR"],
    "CLICKING":   ["CONNECTED", "ERROR"],
    "TYPING":     ["CONNECTED", "ERROR"],
    "RECORDING":  ["RECORDING", "CONNECTED", "ERROR"],
    "ERROR":      ["IDLE"],
}

# Maps command types to allowed source states and in-progress target state
COMMAND_STATE_MAP = {
    "NAVIGATE":        {"required": {"CONNECTED"},            "target": "NAVIGATING"},
    "CLICK":           {"required": {"CONNECTED"},            "target": "CLICKING"},
    "TYPE":            {"required": {"CONNECTED"},            "target": "TYPING"},
    "START_RECORDING": {"required": {"CONNECTED"},            "target": "RECORDING"},
    "STOP_RECORDING":  {"required": {"RECORDING"},            "target": "CONNECTED"},
    "SNAPSHOT":        {"required": {"CONNECTED", "RECORDING"}, "target": None},
    "EXTRACT_PAGE":    {"required": {"CONNECTED", "RECORDING"}, "target": None},
    "EXECUTE_SCRIPT":  {"required": {"CONNECTED"},            "target": None},
    "PING":            {"required": None,                     "target": None},
}


@dataclass
class AuditEntry:
    tab_id: int
    from_state: str
    to_state: str
    reason: str
    timestamp: str


@dataclass
class TabState:
    tab_id: int
    state: str = "IDLE"
    current_action: Optional[Dict] = None
    recording_session: Optional[str] = None
    last_error: Optional[str] = None
    timestamp: str = ""
    metadata: Dict = field(default_factory=dict)


class InvalidTransitionError(Exception):
    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        msg = f"Invalid transition: {from_state} -> {to_state}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class InvalidCommandError(Exception):
    def __init__(self, command: str, current_state: str):
        self.command = command
        self.current_state = current_state
        super().__init__(f"Command '{command}' not allowed in state '{current_state}'")


class TabStateManager:
    """Thread-safe per-tab state manager."""

    def __init__(self):
        self._tabs: Dict[int, TabState] = {}
        self._audit_log: Dict[int, List[AuditEntry]] = {}
        self._lock = threading.Lock()

    def create_tab(self, tab_id: int) -> TabState:
        """Create new tab state (IDLE -> CONNECTED). Raises if already exists."""
        with self._lock:
            if tab_id in self._tabs:
                raise InvalidTransitionError("CONNECTED", "CONNECTED", "already attached")
            tab = TabState(
                tab_id=tab_id,
                state="CONNECTED",
                timestamp=datetime.utcnow().isoformat(),
            )
            self._tabs[tab_id] = tab
            self._append_audit(tab_id, "IDLE", "CONNECTED", "extension attached")
            return tab

    def get_tab(self, tab_id: int) -> Optional[TabState]:
        """Query current state for a tab."""
        return self._tabs.get(tab_id)

    def get_all_tabs(self) -> Dict[int, TabState]:
        """Snapshot of all tab states."""
        return dict(self._tabs)

    def transition(self, tab_id: int, new_state: str, reason: str = "") -> TabState:
        """Atomic validated transition. Raises InvalidTransitionError on failure."""
        with self._lock:
            tab = self._tabs.get(tab_id)
            if tab is None:
                raise InvalidTransitionError("NO_TAB", new_state, f"tab {tab_id} not found")

            allowed = VALID_TRANSITIONS.get(tab.state, [])
            if new_state not in allowed:
                raise InvalidTransitionError(tab.state, new_state, reason)

            old_state = tab.state
            tab.state = new_state
            tab.timestamp = datetime.utcnow().isoformat()

            if new_state in ("CONNECTED", "ERROR", "IDLE"):
                tab.current_action = None
            if new_state == "ERROR":
                tab.last_error = reason

            self._append_audit(tab_id, old_state, new_state, reason)
            return tab

    def validate_command(self, tab_id: int, command_type: str) -> None:
        """Check if command is allowed in current tab state. Raises InvalidCommandError."""
        mapping = COMMAND_STATE_MAP.get(command_type)
        if mapping is None:
            return  # unknown commands pass through
        required = mapping["required"]
        if required is None:
            return  # always allowed (e.g., PING)
        tab = self.get_tab(tab_id)
        if tab is None:
            raise InvalidCommandError(command_type, "NO_TAB")
        if tab.state not in required:
            raise InvalidCommandError(command_type, tab.state)

    def remove_tab(self, tab_id: int) -> Optional[TabState]:
        """Remove tab state on tab close. Returns removed TabState or None."""
        with self._lock:
            tab = self._tabs.pop(tab_id, None)
            if tab:
                self._append_audit(tab_id, tab.state, "CLOSED", "tab closed")
            return tab

    def get_audit_log(self, tab_id: int) -> List[AuditEntry]:
        """Return audit trail for a tab."""
        return list(self._audit_log.get(tab_id, []))

    def reset(self) -> None:
        """Clear all state. Testing only."""
        with self._lock:
            self._tabs.clear()
            self._audit_log.clear()

    def _append_audit(self, tab_id: int, from_state: str, to_state: str, reason: str):
        if tab_id not in self._audit_log:
            self._audit_log[tab_id] = []
        self._audit_log[tab_id].append(AuditEntry(
            tab_id=tab_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
        ))
```

### 2. Per-Tab State Map (JavaScript - in `extension/background.js`)

```javascript
// --- Constants ---
const VALID_TRANSITIONS = {
  IDLE:       ["CONNECTED"],
  CONNECTED:  ["NAVIGATING", "CLICKING", "TYPING", "RECORDING", "ERROR"],
  NAVIGATING: ["CONNECTED", "ERROR"],
  CLICKING:   ["CONNECTED", "ERROR"],
  TYPING:     ["CONNECTED", "ERROR"],
  RECORDING:  ["RECORDING", "CONNECTED", "ERROR"],
  ERROR:      ["IDLE"],
};

// --- Per-tab state ---
const tabStates = new Map();   // Map<tabId, TabStateObj>
const auditLog  = new Map();   // Map<tabId, AuditEntry[]>

/**
 * @typedef {Object} TabStateObj
 * @property {number} tabId
 * @property {string} state
 * @property {Object|null} currentAction
 * @property {string|null} recordingSession
 * @property {string|null} lastError
 * @property {string} timestamp
 * @property {Object} metadata
 */

function createTabState(tabId) {
  if (tabStates.has(tabId)) {
    throw new Error(`Tab ${tabId} already has state`);
  }
  const now = new Date().toISOString();
  const state = {
    tabId,
    state: "CONNECTED",
    currentAction: null,
    recordingSession: null,
    lastError: null,
    timestamp: now,
    metadata: {},
  };
  tabStates.set(tabId, state);
  appendAudit(tabId, "IDLE", "CONNECTED", "extension attached");
  return state;
}

function transitionTabState(tabId, newState, reason = "") {
  const tab = tabStates.get(tabId);
  if (!tab) {
    throw new Error(`No state for tab ${tabId}`);
  }
  const allowed = VALID_TRANSITIONS[tab.state] || [];
  if (!allowed.includes(newState)) {
    throw new Error(`Invalid transition: ${tab.state} -> ${newState} (${reason})`);
  }
  const oldState = tab.state;
  tab.state = newState;
  tab.timestamp = new Date().toISOString();
  if (newState === "ERROR") tab.lastError = reason;
  if (["CONNECTED", "ERROR", "IDLE"].includes(newState)) tab.currentAction = null;
  appendAudit(tabId, oldState, newState, reason);
  // A2 hook: updateBadge(tabId, newState); updateTitle(tabId, newState);
  return tab;
}

function getTabState(tabId) {
  return tabStates.get(tabId) || null;
}

function removeTabState(tabId) {
  const tab = tabStates.get(tabId);
  if (tab) {
    appendAudit(tabId, tab.state, "CLOSED", "tab closed");
    tabStates.delete(tabId);
  }
  return tab;
}

function appendAudit(tabId, fromState, toState, reason) {
  if (!auditLog.has(tabId)) auditLog.set(tabId, []);
  auditLog.get(tabId).push({
    tabId, fromState, toState, reason,
    timestamp: new Date().toISOString(),
  });
}
```

---

## Key Design Decisions

### D1: Python `TabStateManager` uses `threading.Lock` for atomicity
- The websocket server runs in asyncio, but concurrent tab operations from different clients could race
- A simple Lock around `_tabs` dict access prevents race conditions
- Alternative considered: asyncio.Lock -- but threading.Lock is safer if any sync code paths exist

### D2: Extension mirrors state but server is authoritative
- The extension tracks `tabStates` locally for instant badge updates (no round-trip)
- The server's `TabStateManager` is the source of truth
- If they diverge, the server wins (extension re-syncs on next command response)

### D3: RECORDING state allows sub-actions (navigate, click, type) without leaving RECORDING
- RECORDING -> RECORDING is a valid self-transition
- The `current_action` field tracks what sub-action is in progress
- This matches the wish spec: "navigate() during RECORDING stays RECORDING, logs action"

### D4: ERROR -> IDLE is the only recovery path
- No direct ERROR -> CONNECTED
- Forces explicit recovery step (detach + reattach)
- Matches the wish spec: "ERROR state requires explicit recovery"

### D5: `snapshot()` and `extract_page()` do NOT change state
- These are read-only queries, always valid from CONNECTED or RECORDING
- Implemented as state-preserving operations (no transition needed)
- COMMAND_STATE_MAP has `target: None` for these

### D6: COMMAND_STATE_MAP provides validation without coupling
- Maps each command type to its required source states and target state
- Solver can use this table directly: `validate_command()` is a single dict lookup
- Adding new commands means adding one entry to the map

---

## State Transition Table (Complete)

| From State | To State | Trigger | Valid? |
|-----------|----------|---------|--------|
| IDLE | CONNECTED | attach_extension() | YES |
| IDLE | NAVIGATING | navigate() | NO |
| IDLE | ERROR | any error | NO |
| CONNECTED | NAVIGATING | navigate() | YES |
| CONNECTED | CLICKING | click() | YES |
| CONNECTED | TYPING | type() | YES |
| CONNECTED | RECORDING | start_recording() | YES |
| CONNECTED | CONNECTED | snapshot() | YES (no transition, read-only) |
| CONNECTED | ERROR | command failure | YES |
| NAVIGATING | CONNECTED | page load complete | YES |
| NAVIGATING | ERROR | timeout/failure | YES |
| NAVIGATING | CLICKING | click() during nav | NO |
| NAVIGATING | NAVIGATING | navigate() during nav | NO |
| CLICKING | CONNECTED | click complete | YES |
| CLICKING | ERROR | element not found | YES |
| CLICKING | CLICKING | click() during click | NO |
| TYPING | CONNECTED | type complete | YES |
| TYPING | ERROR | field not found | YES |
| TYPING | TYPING | type() during type | NO |
| RECORDING | RECORDING | navigate/click/type | YES (stay, log action) |
| RECORDING | CONNECTED | stop_recording() | YES |
| RECORDING | ERROR | failure | YES |
| ERROR | IDLE | manual recovery | YES |
| ERROR | CONNECTED | auto-reconnect | NO (must go through IDLE) |

---

## Integration Points

### File: `solace_cli/browser/state_machine.py` (NEW)
- `TabState` dataclass
- `AuditEntry` dataclass
- `InvalidTransitionError` exception
- `InvalidCommandError` exception
- `TabStateManager` class with `create_tab`, `get_tab`, `get_all_tabs`, `transition`, `validate_command`, `remove_tab`, `get_audit_log`, `reset`
- `VALID_TRANSITIONS` dict
- `COMMAND_STATE_MAP` dict
- `VALID_STATES` frozenset

### File: `solace_cli/browser/__init__.py` (NEW - empty)
- Package marker for `solace_cli.browser`

### File: `solace_cli/browser/websocket_server.py` (MODIFY - via A3)
- Import `TabStateManager` from state_machine
- Instantiate global `tab_manager = TabStateManager()`
- In `handle_client_command()`: call `tab_manager.validate_command()` before forwarding
- In `handle_extension_response()`: call `tab_manager.transition()` on completion/error
- On extension disconnect: iterate tabs and mark as IDLE

### File: `canon/prime-browser/extension/background.js` (MODIFY)
- Replace global `isConnected`, `recordingEnabled`, `currentSession` with `tabStates` Map
- Add `VALID_TRANSITIONS`, `createTabState()`, `transitionTabState()`, `getTabState()`, `removeTabState()`, `appendAudit()`
- Refactor `handleCommand()` to validate state before dispatch and transition after
- Add `chrome.tabs.onRemoved` listener for cleanup
- Update `GET_STATUS` handler to return per-tab state
- Handle RECORDING special case: sub-actions stay in RECORDING

#### Detailed background.js Refactoring Plan

**Remove these globals:**
```javascript
// DELETE these lines:
let isConnected = false;
let recordingEnabled = false;
let currentSession = null;
let actionLog = [];
```

**Replace with per-tab state (via tabStates Map, see data structures above).**

**Refactor handleCommand():**

```javascript
async function handleCommand(msg) {
  const { type, payload = {}, request_id, tab_id } = msg;

  // Resolve tab: explicit tab_id or active tab
  let resolvedTabId = tab_id;
  if (!resolvedTabId) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    resolvedTabId = tab?.id;
  }
  if (!resolvedTabId) {
    sendMessage({ type: "ERROR", error: "No tab available", request_id });
    return;
  }

  // Ensure tab state exists (auto-create on first command)
  if (!getTabState(resolvedTabId) && type !== "PING") {
    createTabState(resolvedTabId);
  }

  const tabState = getTabState(resolvedTabId);

  try {
    switch (type) {
      case "PING":
        sendMessage({ type: "PONG", request_id, timestamp: new Date().toISOString() });
        break;

      case "NAVIGATE":
        if (tabState.state === "RECORDING") {
          await navigateTo(payload.url, request_id, resolvedTabId);
          logAction(resolvedTabId, "navigate", { url: payload.url });
        } else {
          transitionTabState(resolvedTabId, "NAVIGATING", "navigate() called");
          await navigateTo(payload.url, request_id, resolvedTabId);
          transitionTabState(resolvedTabId, "CONNECTED", "page load complete");
        }
        break;

      case "CLICK":
        if (tabState.state === "RECORDING") {
          await clickElement(payload, request_id, resolvedTabId);
          logAction(resolvedTabId, "click", payload);
        } else {
          transitionTabState(resolvedTabId, "CLICKING", "click() called");
          await clickElement(payload, request_id, resolvedTabId);
          transitionTabState(resolvedTabId, "CONNECTED", "click complete");
        }
        break;

      case "TYPE":
        if (tabState.state === "RECORDING") {
          await typeText(payload, request_id, resolvedTabId);
          logAction(resolvedTabId, "type", payload);
        } else {
          transitionTabState(resolvedTabId, "TYPING", "type() called");
          await typeText(payload, request_id, resolvedTabId);
          transitionTabState(resolvedTabId, "CONNECTED", "type complete");
        }
        break;

      case "START_RECORDING":
        transitionTabState(resolvedTabId, "RECORDING", "start recording");
        startRecording(payload, request_id, resolvedTabId);
        break;

      case "STOP_RECORDING":
        stopRecording(request_id, resolvedTabId);
        transitionTabState(resolvedTabId, "CONNECTED", "stop recording");
        break;

      case "SNAPSHOT":
        await takeSnapshot(payload, request_id, resolvedTabId);
        break;

      case "EXTRACT_PAGE":
        await extractPageData(payload, request_id, resolvedTabId);
        break;

      case "EXECUTE_SCRIPT":
        await executeScript(payload.script, request_id, resolvedTabId);
        break;

      default:
        console.warn("[Solace] Unknown command:", type);
    }
  } catch (error) {
    console.error("[Solace] Command error:", error);
    // Transition to ERROR if valid
    try {
      transitionTabState(resolvedTabId, "ERROR", error.message);
    } catch (_) { /* already in ERROR or IDLE */ }
    sendMessage({ type: "ERROR", error: error.message, command: type, request_id });
  }
}
```

**Refactor navigateTo, clickElement, typeText:**
- Add `tabId` parameter (use instead of querying active tab each time)
- Change `chrome.tabs.query` to `chrome.tabs.get(tabId)` for targeted tab
- Remove global `isConnected` checks (state machine handles this)

**Add chrome.tabs.onRemoved listener:**
```javascript
chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
  const tab = removeTabState(tabId);
  if (tab && tab.state === "RECORDING") {
    stopRecording(null, tabId);
  }
  console.log(`[Solace] Tab ${tabId} closed, state cleaned up`);
});
```

**Refactor logAction to be per-tab:**
```javascript
// Per-tab action logs (replaces global actionLog)
const tabActionLogs = new Map();  // Map<tabId, action[]>

function logAction(tabId, type, data) {
  const tab = getTabState(tabId);
  if (tab && tab.state === "RECORDING") {
    if (!tabActionLogs.has(tabId)) tabActionLogs.set(tabId, []);
    tabActionLogs.get(tabId).push({
      type, data, timestamp: new Date().toISOString()
    });
  }
}
```

**Update GET_STATUS handler:**
```javascript
if (request.type === "GET_STATUS") {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tabId = tabs[0]?.id;
    const tabState = tabId ? getTabState(tabId) : null;
    sendResponse({
      isConnected: ws && ws.readyState === WebSocket.OPEN,
      tabState: tabState,
      recordingEnabled: tabState?.state === "RECORDING",
      currentSession: tabState?.recordingSession,
      serverUrl: DEFAULT_WS_URL,
    });
  });
  return true;  // async response
}
```

---

## Function Inventory

### Python (`solace_cli/browser/state_machine.py`) -- 10 items

| Item | Type | Purpose |
|------|------|---------|
| `VALID_STATES` | frozenset | Enumeration of valid state strings |
| `VALID_TRANSITIONS` | dict | State -> list of valid target states |
| `COMMAND_STATE_MAP` | dict | Command type -> {required states, target state} |
| `TabState` | dataclass | Per-tab state data |
| `AuditEntry` | dataclass | Transition log entry |
| `InvalidTransitionError` | exception | Raised on invalid transition |
| `InvalidCommandError` | exception | Raised on invalid command for current state |
| `TabStateManager.create_tab` | method | Create new tab (IDLE -> CONNECTED) |
| `TabStateManager.transition` | method | Atomic validated transition |
| `TabStateManager.validate_command` | method | Check command allowed in current state |
| `TabStateManager.get_tab` | method | Query current state |
| `TabStateManager.get_all_tabs` | method | Snapshot of all tab states |
| `TabStateManager.remove_tab` | method | Cleanup on tab close |
| `TabStateManager.get_audit_log` | method | Return transition history |
| `TabStateManager.reset` | method | Clear all state (testing) |

### JavaScript (`extension/background.js`) -- 7 items

| Item | Type | Purpose |
|------|------|---------|
| `VALID_TRANSITIONS` | const object | State -> valid targets |
| `tabStates` | Map | Per-tab state storage |
| `auditLog` | Map | Per-tab audit trail |
| `createTabState(tabId)` | function | Initialize per-tab state |
| `transitionTabState(tabId, state, reason)` | function | Atomic transition with validation |
| `getTabState(tabId)` | function | Read state for tab |
| `removeTabState(tabId)` | function | Clean up on tab close |
| `appendAudit(tabId, from, to, reason)` | function | Log transition |
| `logAction(tabId, type, data)` | function | Per-tab action logging during recording |

---

## Dependencies

### Blocks (what depends on A1)

| Wish | Reason |
|------|--------|
| **A2** | Badge updates hook into `transitionTabState()` callback |
| **A3** | Server-side validation uses `TabStateManager.validate_command()` |
| **A4** | All tests depend on state machine being functional |

### Depends On

None. A1 is the foundation.

---

## Complexity Estimate

| Metric | Value |
|--------|-------|
| LOC (Python: state_machine.py) | 150 |
| LOC (JavaScript: new functions in background.js) | 80 |
| LOC (JavaScript: refactoring existing background.js) | 100 |
| Total LOC | 330 |
| Dataclasses/Classes | 4 (TabState, AuditEntry, TabStateManager, InvalidTransitionError) |
| Python functions/methods | 10 |
| JavaScript functions | 7 |
| Files created | 2 (state_machine.py, __init__.py) |
| Files modified | 1 (background.js) |
| Effort | 1.5 days |

---

## 641-Edge Test Cases

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| TAB1 | IDLE -> CONNECTED via `create_tab()` | TabState created, state = "CONNECTED", audit log has 1 entry |
| TAB2 | Double attach same tab (call `create_tab()` twice) | `InvalidTransitionError` raised |
| TAB3 | NAVIGATING -> CLICKING (call transition during nav) | `InvalidTransitionError` raised |
| TAB4 | RECORDING persists across navigate, click, type | State stays "RECORDING", actions logged in actionLog |
| TAB5 | ERROR -> recovery: only IDLE allowed, then CONNECTED | ERROR -> CONNECTED raises; ERROR -> IDLE succeeds |

---

## Solver Handoff Checklist

- [ ] Create `solace_cli/browser/__init__.py` (empty package marker)
- [ ] Create `solace_cli/browser/state_machine.py` with all data structures and TabStateManager
- [ ] Add `VALID_TRANSITIONS`, `COMMAND_STATE_MAP`, `VALID_STATES` constants
- [ ] Implement `TabStateManager` with thread-safe locking
- [ ] Refactor `background.js`: remove global vars (`isConnected`, `recordingEnabled`, `currentSession`, `actionLog`)
- [ ] Add `VALID_TRANSITIONS`, `tabStates`, `auditLog`, `tabActionLogs` to background.js
- [ ] Add `createTabState()`, `transitionTabState()`, `getTabState()`, `removeTabState()`, `appendAudit()`, `logAction()` to background.js
- [ ] Refactor `handleCommand()` to validate state and transition before/after each command
- [ ] Handle RECORDING special case: sub-actions stay in RECORDING
- [ ] Add `tabId` parameter to `navigateTo()`, `clickElement()`, `typeText()`
- [ ] Add `chrome.tabs.onRemoved` listener for cleanup
- [ ] Update `GET_STATUS` handler to return per-tab state
- [ ] Verify thread safety via `_lock` in Python module
- [ ] Run 641-edge tests (TAB1-TAB5)

---

**Auth:** 65537
**Verification:** 641 -> 274177 -> 65537
**Status:** DESIGN COMPLETE
