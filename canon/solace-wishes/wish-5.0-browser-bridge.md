# WISH 5.0: Browser Bridge & Live Integration

**Spec ID:** wish-5.0-browser-bridge
**Authority:** 65537
**Phase:** 5 (Live Browser Integration)
**Depends On:** wish-4.0 (state machine verified)
**Scope:** Implement bridge layer to connect episode automation to live browser instance
**Non-Goals:** Performance optimization, cross-browser (Phase 10+), ML (Phase 8+)
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 700 | **GLOW:** 95

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Browser bridge translates actions to browser API calls, reads state back
  Verification:    Each action produces observable side effect in browser
  Canonicalization: Browser state captured as canonical JSON snapshot
  Content-addressing: Browser screenshots hashed for frame deduplication
```

---

## 1. Observable Wish

> "I can connect the automation engine to a live browser instance, execute episodes, and capture real browser state back to episodes."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Chromium compilation (wish-1.1)
- ❌ Performance optimization
- ❌ Cross-browser support (Phase 10+)
- ❌ JS execution analysis

**Minimum success criteria:**
- ✅ Browser interface defined
- ✅ Mock browser instance created
- ✅ Action translation working (click → browser API)
- ✅ State capture working (screenshot → episode state)
- ✅ Round-trip test: episode → browser → capture → verify

---

## 3. Context Capsule (Test-Only)

```
Initial:   State machine verified (wish-4.0), episode format locked
Behavior:  Define browser interface, implement mock browser, execute episode
Final:     Browser bridge working, ready for Phase 6 optimization
```

---

## 4. State Space: 5 States

```
state_diagram-v2
    [*] --> DISCONNECTED
    DISCONNECTED --> CONNECTING: connect()
    CONNECTING --> CONNECTED: browser_ready
    CONNECTED --> EXECUTING: execute_action()
    EXECUTING --> CONNECTED: action_complete
    CONNECTED --> CAPTURING: capture_state()
    CAPTURING --> CONNECTED: state_captured
    CONNECTED --> DISCONNECTING: disconnect()
    DISCONNECTING --> DISCONNECTED: closed
    CONNECTING --> ERROR: timeout
    EXECUTING --> ERROR: action_failed
    CAPTURING --> ERROR: capture_failed
    ERROR --> DISCONNECTED: cleanup
    ERROR --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** Browser interface has methods: connect(), disconnect(), execute_action(), capture_state()
**INV-2:** Each action execution updates internal browser state
**INV-3:** State capture produces valid JSON snapshot with URL, DOM hash, DOM tree
**INV-4:** Screenshot data is hashed and stored for frame deduplication
**INV-5:** All browser state changes are reversible (can replay from any point)

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Browser Interface Defined
```
Setup:   Project root with wish-4.0 complete
Input:   Load browser interface definition
Expect:  Interface has required methods and properties
Verify:  All action types can be executed
```

### T2: Mock Browser Instance Created
```
Setup:   Browser interface loaded
Input:   Create mock browser with simulated DOM
Expect:  Browser instance created and ready
Verify:  Browser has URL, DOM tree, event handlers
```

### T3: Action Execution (Translation)
```
Setup:   Mock browser ready
Input:   Execute action: click on button.submit
Expect:  Browser receives click event, updates state
Verify:  Event handler called, DOM state changed
```

### T4: State Capture (Snapshot)
```
Setup:   Action executed, browser state changed
Input:   Capture current browser state
Expect:  Snapshot generated with URL, DOM hash, screenshot
Verify:  Snapshot is valid JSON, contains all required fields
```

### T5: Round-Trip Test (Episode → Browser → Capture → Verify)
```
Setup:   Full system: episode, browser, bridge
Input:   Load episode-001, execute all actions, capture final state
Expect:  Final state matches expected post-state
Verify:  Episode replay is deterministic, state matches
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Browser interface not defined → T1 fails
**F2:** Mock browser not initialized → T2 fails
**F3:** Action translation broken → T3 fails
**F4:** State capture missing fields → T4 fails
**F5:** Round-trip state mismatch → T5 fails (non-deterministic)

---

## 8. Visual Evidence (Proof Artifacts)

**browser-interface.json structure:**
```json
{
  "interface": {
    "methods": [
      {
        "name": "connect",
        "params": ["url"],
        "returns": "browser_handle"
      },
      {
        "name": "execute_action",
        "params": ["action_type", "target", "value"],
        "returns": "execution_result"
      },
      {
        "name": "capture_state",
        "params": [],
        "returns": "state_snapshot"
      },
      {
        "name": "disconnect",
        "params": [],
        "returns": "void"
      }
    ]
  }
}
```

**state_snapshot.json structure:**
```json
{
  "timestamp": "2026-02-14T17:00:00Z",
  "url": "https://example.com",
  "title": "Example Domain",
  "dom_hash": "sha256:...",
  "dom_tree": {
    "root": "html",
    "children": [
      {"tag": "head", "children": []},
      {"tag": "body", "children": []}
    ]
  },
  "screenshot_hash": "sha256:...",
  "active_element": "button.submit"
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Browser interface fully specified
- [x] **R4: Deterministic** — Mock browser has repeatable behavior
- [x] **R5: Hermetic** — No external browser needed (uses mock)
- [x] **R6: Idempotent** — Tests don't modify permanent state
- [x] **R7: Fast** — All tests complete in <10 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same episode always produces same browser state
- [x] **R10: Verifiable** — Artifacts prove round-trip execution works

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Browser interface defined with all methods
- [ ] Mock browser instance working
- [ ] Action execution and state capture both working
- [ ] Round-trip episode execution verified

---

## 11. Next Phase

→ **wish-6.0** (Episode Recorder): Record live browser interactions into episodes

---

**Wish:** wish-5.0-browser-bridge
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-6.0, enables live browser automation

*"Bridge episodes to browser instances."*
