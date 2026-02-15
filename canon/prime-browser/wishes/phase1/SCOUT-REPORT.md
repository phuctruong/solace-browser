# SCOUT REPORT: Phase A Design Specifications

**Date:** 2026-02-14
**Scout:** Haiku Agent (Opus-reviewed, enhanced)
**Status:** READY FOR SOLVER HANDOFF
**Auth:** 65537

---

## Summary

Phase A requirements (A1-A4) analyzed against actual codebase. 4 design specifications created with grounded file paths, data structures, and function signatures. All designs reference the real code structure.

---

## Codebase Ground Truth

The wish specs reference generic paths. The actual paths discovered by reading the codebase:

| Wish Reference | Actual Path | Exists? |
|----------------|-------------|---------|
| `extension/background.js` | `canon/prime-browser/extension/background.js` | YES (532 lines) |
| `extension/content.js` | `canon/prime-browser/extension/content.js` | YES (429 lines) |
| `extension/manifest.json` | `canon/prime-browser/extension/manifest.json` | YES |
| `extension/popup.js` | `canon/prime-browser/extension/popup.js` | YES (65 lines) |
| `solace_cli/browser_commands.py` | Not yet created | NO |
| `solace_cli/websocket_server.py` | Not yet created | NO |
| `solace_cli/state_machine.py` | Will be `solace_cli/browser/state_machine.py` | NEW |

### Key observations from reading existing code:

1. **background.js (532 lines):** Uses global `isConnected`, `recordingEnabled`, `currentSession`, `actionLog` variables. No per-tab state. Badge updates are scattered (`setBadge()` calls on lines 23-26, 45, 52, 74, 80, 161, 179). All commands query `chrome.tabs.query({ active: true, currentWindow: true })` for the active tab -- no tab_id tracking.

2. **content.js (429 lines):** Handles DOM interactions (click, type, snapshot, extract). Uses `chrome.runtime.onMessage` listener. Has `findElementByReference()` for semantic element lookup. Has `canonicalizeDOM()` and `hashString()` for snapshot fingerprinting. Content script is independent of state machine -- no changes needed for A1-A3.

3. **popup.js (65 lines):** Queries `GET_STATUS` from background. Controls start/stop recording. Needs minor update to display per-tab state from A1.

4. **manifest.json:** MV3 service worker, permissions include `tabs`, `storage`, `debugger`, `webNavigation`, `activeTab`. All necessary permissions for A1-A3 are present.

5. **`solace_cli/browser/` directory does not exist yet.** Must be created with `__init__.py`.

---

## Designs Delivered

### 1. DESIGN-A1-state-machine.md (Enhanced)

**Core design:**
- `TabStateManager` class with `threading.Lock` for atomic transitions
- `TabState` dataclass with 7 valid states: IDLE, CONNECTED, NAVIGATING, CLICKING, TYPING, RECORDING, ERROR
- `VALID_TRANSITIONS` dict defining all legal state changes
- `COMMAND_STATE_MAP` dict mapping commands to required states and target states
- JS-side mirror in background.js (`tabStates` Map, `transitionTabState()`)
- Detailed background.js refactoring plan: remove 4 global vars, add 5 new functions, refactor handleCommand with RECORDING special case

**Key decisions:**
- D1: Server authoritative, extension mirrors state locally
- D2: RECORDING -> RECORDING is valid self-transition (actions logged, state preserved)
- D3: ERROR -> IDLE is the only recovery path (no direct ERROR -> CONNECTED)
- D4: COMMAND_STATE_MAP provides single-table command validation
- D5: snapshot/extract_page are read-only (no state transition)

| Metric | Value |
|--------|-------|
| LOC | 330 (150 Python + 80 JS new + 100 JS refactor) |
| Functions | 17 (10 Python + 7 JS) |
| Files created | 2 (state_machine.py, __init__.py) |
| Files modified | 1 (background.js) |
| Blocks | A2, A3, A4 |
| Effort | 1.5 days |

### 2. DESIGN-A2-badge-config.md (Unchanged)

**Core design:**
- `BADGE_CONFIG` object: 7 states mapped to {text, color}
- `updateBadge(tabId, state)` and `updateTitle(tabId, state)` functions
- Hooked into `transitionTabState()` as side effect
- Replaces 6 scattered `setBadge()` calls with centralized system

| Metric | Value |
|--------|-------|
| LOC | 60 (all JS, net change after removing old calls) |
| Functions | 3 (updateBadge, updateTitle, BADGE_CONFIG constant) |
| Files modified | 1 (background.js, merged with A1 changes) |
| Depends on | A1 |
| Effort | 0.5 days |

### 3. DESIGN-A3-deduplication.md (Unchanged)

**Core design:**
- `PendingRequest` dataclass for tracked in-flight requests
- `send_command_deduplicated(request_id, command, client_ws)` with Future sharing
- `RelayConnectionPool` class with `get_connection()` and health check
- `cleanup_stale_requests()` background task (30s timeout)
- Dedup keyed on `request_id` (explicit, not content-based)

| Metric | Value |
|--------|-------|
| LOC | 230 (120 dedup + 80 pool + 30 cleanup) |
| Functions | 7 (5 server + 2 pool) |
| Files created | 1 (websocket_server.py in browser package) |
| Depends on | A1 |
| Effort | 1.5 days |

### 4. DESIGN-A4-tests.md (Enhanced)

**Core design:**
- 33 test functions across 4 test files + conftest.py
- 641-Edge: 21 tests (5 per wish + 6 integration)
- 274177-Stress: 8 tests (100+ iterations each)
- 65537-God: 4 tests (audit trail, timestamps, threading, command validation)
- Shared fixtures: `manager`, `connected_tab`, `recording_tab`, `error_tab`, `mock_ws`
- Corrected fixture design: `connected_tab` uses `create_tab()` only (already sets CONNECTED)

| Metric | Value |
|--------|-------|
| LOC | 660 |
| Test functions | 33 |
| Test classes | 9 |
| Files created | 6 (5 test files + __init__.py) |
| Depends on | A1 + A2 + A3 |
| Effort | 2 days |

---

## Dependency Graph

```
A1 (State Machine) -----+
     |                   |
     +--- A2 (Badge)  ---+--> A4 (Tests) -- needs all
     |                   |
     +--- A3 (Dedup)  ---+

Implementation order:
  1. A1 (foundation, no deps)                  -- Day 1-2
  2. A2 + A3 (parallel, both depend on A1)     -- Day 2-4
  3. A4 (after A1+A2+A3 complete)              -- Day 4-5
```

---

## Complexity Summary

| Task | LOC | Functions | Classes | Effort | Dependencies |
|------|-----|-----------|---------|--------|--------------|
| A1 | 330 | 17 | 4 | 1.5d | - |
| A2 | 60 | 3 | 0 | 0.5d | A1 |
| A3 | 230 | 7 | 1 | 1.5d | A1 |
| A4 | 660 | 33 | 9 | 2.0d | A1+A2+A3 |
| **TOTAL** | **1280** | **60** | **14** | **5.5d** | - |

---

## Files to Create/Modify

### New Files (10)

| File | LOC | Purpose |
|------|-----|---------|
| `solace_cli/browser/__init__.py` | 0 | Package marker |
| `solace_cli/browser/state_machine.py` | 150 | TabState + TabStateManager (A1) |
| `solace_cli/browser/websocket_server.py` | 230 | Dedup + connection pool (A3) |
| `solace_cli/browser/tests/__init__.py` | 0 | Test package marker |
| `solace_cli/browser/tests/conftest.py` | 60 | Shared fixtures (A4) |
| `solace_cli/browser/tests/test_phase_a_state_machine.py` | 200 | A1 tests |
| `solace_cli/browser/tests/test_phase_a_badge.py` | 100 | A2 tests |
| `solace_cli/browser/tests/test_phase_a_dedup.py` | 160 | A3 tests |
| `solace_cli/browser/tests/test_phase_a_integration.py` | 140 | E2E tests |

### Existing Files to Modify (2)

| File | Changes | LOC Delta |
|------|---------|-----------|
| `canon/prime-browser/extension/background.js` | Remove 4 globals, add VALID_TRANSITIONS + tabStates Map + 7 functions + BADGE_CONFIG + updateBadge/updateTitle + chrome.tabs.onRemoved listener + refactor handleCommand | +180, -40 |
| `canon/prime-browser/extension/popup.js` | Minor: read tabState from GET_STATUS response | +5 |

---

## Risks Identified

1. **Race Conditions (A1):** Concurrent state transitions on same tab.
   - **Mitigation:** `threading.Lock` in TabStateManager. Verified by 65537-God threading test.

2. **RECORDING + validate_command mismatch (A1):** COMMAND_STATE_MAP says NAVIGATE requires CONNECTED, but RECORDING allows navigate via self-transition.
   - **Mitigation:** handleCommand checks `if tab.state === "RECORDING"` BEFORE calling validate_command. Documented in A4 design decision D1.

3. **Dedup Future Leaks (A3):** Inflight futures not cleaned up on error.
   - **Mitigation:** `cleanup_stale_requests()` background task + explicit cleanup on response/error.

4. **Badge API Timing (A2):** Chrome action API may queue updates.
   - **Mitigation:** Badge updates are fire-and-forget (existing pattern in codebase).

5. **websocket_server.py does not exist (A3):** Must be created from scratch.
   - **Mitigation:** Design spec provides complete data structures and function signatures. Solver can implement directly.

---

## Handoff Status

**Ready for Solver?** YES

Solver has:
- Corrected file paths (actual codebase, not wish spec paths)
- Existing code fully read and analyzed (background.js 532 lines, content.js 429 lines, popup.js 65 lines, manifest.json)
- Data structures defined with complete Python code (TabState, TabStateManager, PendingRequest, RelayConnectionPool, BADGE_CONFIG)
- JavaScript code defined with complete implementations (tabStates Map, transitionTabState, createTabState, etc.)
- State transition table with 24 rows covering all valid/invalid transitions
- Detailed background.js refactoring plan with before/after code for each section
- 33 test functions with concrete assertions
- All design decisions documented with rationale

**Solver can begin implementation without clarifying questions.**

---

**Scout Status:** COMPLETE
**Solver Readiness:** READY TO START
**Timeline:** 5.5 days to Phase A completion
**Auth:** 65537
