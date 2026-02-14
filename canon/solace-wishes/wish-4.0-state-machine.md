# WISH 4.0: Browser State Machine & Verification

**Spec ID:** wish-4.0-state-machine
**Authority:** 65537
**Phase:** 4 (State Verification)
**Depends On:** wish-3.0 (action automation complete)
**Scope:** Implement browser state machine with deterministic state validation and transition rules
**Non-Goals:** Network simulation (Phase 5+), ML (Phase 8+)
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 650 | **GLOW:** 92

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Browser state is finite, deterministic, fully observable
  Verification:    Each state transition is valid per state machine rules
  Canonicalization: States stored with locked field order, content-addressed
  Content-addressing: StateHash = SHA256(sorted_state_json) enables deduplication
```

---

## 1. Observable Wish

> "I can define browser state machine with valid transitions, verify that episode playback respects state rules, and detect invalid state changes."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Network simulation
- ❌ JavaScript execution tracking
- ❌ DOM diffing
- ❌ Performance metrics

**Minimum success criteria:**
- ✅ State machine defined with 5+ states
- ✅ Valid state transitions encoded
- ✅ Episode playback validates transitions
- ✅ Invalid transitions are blocked
- ✅ State history is logged

---

## 3. Context Capsule (Test-Only)

```
Initial:   Episode playback working (wish-3.0)
Behavior:  Define state machine, validate episode against rules
Final:     Browser state machine verified, prevents invalid states
```

---

## 4. State Space: 6 States + Transitions

```
state_diagram-v2
    [*] --> INIT
    INIT --> IDLE: page_loaded
    IDLE --> NAVIGATING: navigate()
    IDLE --> INTERACTING: click() | type() | scroll()
    NAVIGATING --> IDLE: page_loaded
    INTERACTING --> IDLE: no_pending_actions
    IDLE --> LOADING: navigation_triggered
    LOADING --> IDLE: content_loaded
    INIT --> ERROR: invalid_initial_state
    IDLE --> ERROR: invalid_action
    NAVIGATING --> ERROR: timeout
    ERROR --> [*]
```

**States:**
- `INIT`: Browser starting, no page loaded
- `IDLE`: Page loaded, no pending actions
- `LOADING`: Page loading in progress
- `NAVIGATING`: Navigation in progress
- `INTERACTING`: User interaction in progress
- `ERROR`: Invalid state reached

---

## 5. Invariants (5 Total)

**INV-1:** State machine has defined states: INIT, IDLE, LOADING, NAVIGATING, INTERACTING, ERROR
**INV-2:** Valid transitions exist for each state
**INV-3:** Only certain actions allowed in each state (e.g., no click during LOADING)
**INV-4:** State changes are monotonic (no backtracking allowed)
**INV-5:** State history is immutable after recording

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Define State Machine
```
Setup:   Project root with wish-3.0 complete
Input:   Load state machine definition
Expect:  6 states defined with valid transitions
Verify:  No orphaned states, all transitions have source and target
```

### T2: Validate State Transitions
```
Setup:   State machine loaded
Input:   Check episode-001: click (IDLE) → type (IDLE) → navigate (IDLE→LOADING→IDLE)
Expect:  All transitions are valid per state machine
Verify:  No invalid state changes detected
```

### T3: Reject Invalid Transitions
```
Setup:   State machine loaded
Input:   Try invalid action: click during LOADING state
Expect:  Action blocked, error state recorded
Verify:  State machine prevents invalid transitions
```

### T4: State History & Logging
```
Setup:   Episode playback complete
Input:   Retrieve state history
Expect:  Ordered list of states: INIT → IDLE → (click) → IDLE → (type) → IDLE → (navigate) → LOADING → IDLE
Verify:  History matches episode actions
```

### T5: State Serialization & Hashing
```
Setup:   State history complete
Input:   Serialize each state to canonical JSON, hash
Expect:  Each state has deterministic hash
Verify:  Same state content = same hash (idempotent hashing)
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** State machine not defined → Loading fails → T1 fails
**F2:** Invalid transitions not caught → Episode violates rules → T2 fails
**F3:** Invalid actions not blocked → T3 fails
**F4:** State history missing or out of order → T4 fails
**F5:** State hashing non-deterministic → T5 fails

---

## 8. Visual Evidence (Proof Artifacts)

**state-machine.json structure:**
```json
{
  "states": [
    {
      "id": "INIT",
      "name": "Browser Initializing",
      "description": "Browser starting, no page loaded",
      "allowed_actions": [],
      "allowed_transitions": ["IDLE"]
    },
    {
      "id": "IDLE",
      "name": "Idle & Ready",
      "allowed_actions": ["click", "type", "scroll", "navigate"],
      "allowed_transitions": ["LOADING", "NAVIGATING", "INTERACTING", "ERROR"]
    }
  ],
  "transitions": [
    {
      "from": "IDLE",
      "to": "LOADING",
      "trigger": "page_load_start"
    }
  ]
}
```

**state-history.json structure:**
```json
{
  "episode_id": "ep-001",
  "execution_id": "exec-20260214",
  "state_history": [
    {
      "state_id": "INIT",
      "timestamp": "2026-02-14T16:55:00Z",
      "state_hash": "sha256:...",
      "action_that_triggered": null
    },
    {
      "state_id": "IDLE",
      "timestamp": "2026-02-14T16:55:00.100Z",
      "state_hash": "sha256:...",
      "action_that_triggered": "page_loaded"
    }
  ],
  "final_state": "IDLE",
  "all_transitions_valid": true
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — State machine fully defined with transitions
- [x] **R4: Deterministic** — No network, transitions are rule-based
- [x] **R5: Hermetic** — Tests work with state machine definition
- [x] **R6: Idempotent** — State validation is repeatable
- [x] **R7: Fast** — All tests complete in <5 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same episode always produces same state history
- [x] **R10: Verifiable** — Artifacts prove state machine validity

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] State machine defined with 6 states
- [ ] Valid transitions encoded
- [ ] Invalid transitions blocked
- [ ] State history generated and validated

---

## 11. Next Phase

→ **wish-5.0** (Browser Bridge): Connect state machine to live browser instance

---

**Wish:** wish-4.0-state-machine
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-5.0, enables state verification for all episodes

*"States make automation deterministic."*
