# Wish A1: Per-Tab State Machine Implementation

**Task ID:** A1
**Phase:** Phase A (Browser Control Foundation)
**Owner:** Solver (via Haiku swarm)
**Timeline:** 2 days
**Status:** READY FOR EXECUTION
**Auth:** 65537

---

## Specification

Implement deterministic per-tab state machine for browser sessions. Each tab tracks its own independent session state with atomic transitions.

**Skill Reference:** `canon/prime-browser/skills/browser-state-machine.md` v1.0.0

---

## Requirements

### Data Structure

```python
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class TabState:
    tab_id: int
    state: str  # IDLE, CONNECTED, NAVIGATING, CLICKING, TYPING, RECORDING, ERROR
    current_action: Optional[Dict]
    recording_session: Optional[str]
    last_error: Optional[str]
    timestamp: str
    metadata: Dict

# Global state
tab_sessions: Dict[int, TabState] = {}
```

### State Diagram

```
IDLE ──attach──> CONNECTED ──record──> RECORDING ──stop──> CONNECTED
                    │
                    ├──navigate──> NAVIGATING ──load──> CONNECTED
                    ├──click────> CLICKING ──complete──> CONNECTED
                    ├──type─────> TYPING ──complete──> CONNECTED
                    │
                    └──ERROR (any failure)
```

### Integration Points

1. **extension/background.js**
   - `onExtensionAttach(tabId)` → Create TabState, set CONNECTED
   - `onTabClose(tabId)` → Save episode (if RECORDING), delete TabState
   - `dispatch_command(tabId, command)` → Validate state, transition, execute

2. **solace_cli/browser_commands.py**
   - `validate_state(tab_id, required_state)` → Check if allowed
   - `transition_state(tab_id, new_state, reason)` → Atomic update
   - `get_tab_state(tab_id)` → Query current state

3. **solace_cli/websocket_server.py**
   - State validation before command dispatch
   - Reject invalid transitions with typed error

---

## Success Criteria (641-Edge)

✅ **TAB1:** IDLE → CONNECTED succeeds
- Extension attaches to tab → TabState created with CONNECTED state

✅ **TAB2:** CONNECTED → CONNECTED fails (invalid transition)
- Attempting to attach twice returns error

✅ **TAB3:** NAVIGATING → CLICKING fails (invalid transition)
- Cannot click while navigating

✅ **TAB4:** RECORDING state persists across multiple actions
- navigate() during RECORDING → stays RECORDING, logs action
- click() during RECORDING → stays RECORDING, logs action
- stop_recording() → CONNECTED

✅ **TAB5:** ERROR state requires explicit recovery
- Any failure → ERROR state
- Manual recovery needed (admin action to reset)

---

## Implementation Checklist

- [ ] Define TabState dataclass in `solace_cli/state_machine.py`
- [ ] Implement `transition(tab_state, new_state, reason)` function
- [ ] Implement `validate_transition(from_state, to_state)` validation
- [ ] Add per-tab state tracking to `websocket_server.py`
- [ ] Update `extension/background.js` to manage per-tab state
- [ ] Add state logging to audit trail
- [ ] Test IDLE→CONNECTED flow
- [ ] Test invalid transition rejection
- [ ] Test RECORDING state persistence
- [ ] Test ERROR state + recovery

---

## Acceptance Criteria

✅ Per-tab state machine running atomically (no race conditions)
✅ Invalid transitions rejected with typed error messages
✅ All state changes logged to audit trail (timestamp, reason)
✅ State isolation verified (tab 1 state ≠ tab 2 state)
✅ 641-edge tests pass (all 5 cases)
✅ 274177-stress tests pass (100+ concurrent tabs)

---

## Related Skills

- `browser-state-machine.md` v1.0.0 (specification)
- `browser-selector-resolution.md` v1.0.0 (for command validation)

---

**Ready to assign to:** Scout (design), Solver (implementation)
