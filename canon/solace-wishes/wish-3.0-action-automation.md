# WISH 3.0: Action Automation & Episode Playback

**Spec ID:** wish-3.0-action-automation
**Authority:** 65537
**Phase:** 3 (Automation & Control)
**Depends On:** wish-2.0 (episode recording infrastructure complete)
**Scope:** Implement deterministic playback of recorded episodes - execute action sequences in browser
**Non-Goals:** ML training (Phase 8+), cross-browser (Phase 10+), real-time optimization
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 600 | **GLOW:** 90

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Action sequence executes deterministically, browser state matches expected
  Verification:    Each action produces observable side effect, post-action state validated
  Canonicalization: Action playback is idempotent (replay = first run)
  Content-addressing: Execution trace SHA256 matches expected trace hash
```

---

## 1. Observable Wish

> "I can load a recorded episode, execute its action sequence deterministically, and verify that the browser state after playback matches the recorded post-state."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ ML-based action inference (Phase 8+)
- ❌ Cross-browser playback (Phase 10+)
- ❌ Performance optimization
- ❌ Error recovery/fallback paths

**Minimum success criteria:**
- ✅ Episode loaded from JSON
- ✅ Action executor implemented (click, type, navigate, scroll)
- ✅ Each action produces expected side effect
- ✅ Post-action state snapshot matches expected
- ✅ Execution trace generated and verified

---

## 3. Context Capsule (Test-Only)

```
Initial:   Episode recording verified (wish-2.0), sample episodes available
Behavior:  Load episode, execute actions, verify final state
Final:     Episode playback working deterministically, ready for Phase 4 integration
```

---

## 4. State Space: 5 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> LOADING_EPISODE: start()
    LOADING_EPISODE --> EXECUTING_ACTIONS: episode loaded
    EXECUTING_ACTIONS --> VALIDATING_STATE: all actions done
    VALIDATING_STATE --> SUCCESS: state matches expected
    LOADING_EPISODE --> ERROR: episode invalid
    EXECUTING_ACTIONS --> ERROR: action failed
    VALIDATING_STATE --> ERROR: state mismatch
    ERROR --> [*]
    SUCCESS --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** Action executor has methods for all action types: click, type, navigate, scroll, wait, screenshot
**INV-2:** Each action execution records pre/post state
**INV-3:** Execution trace is ordered list of {action, result, state_before, state_after}
**INV-4:** Final state hash matches expected post-episode state
**INV-5:** Execution is deterministic (same input, same trace every time)

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Load Episode from JSON
```
Setup:   Episode file exists at artifacts/episodes/episode-001.json
Input:   Load episode into memory
Expect:  Episode object has all required fields
Verify:  state_snapshot and actions array accessible
```

### T2: Execute Single Click Action
```
Setup:   Episode loaded, action executor initialized
Input:   Execute action: {type: "click", target: "button.submit", timestamp: 100}
Expect:  Action completes without error
Verify:  Execution trace records action, pre/post states
```

### T3: Execute Type Action (Input Text)
```
Setup:   Click action complete
Input:   Execute action: {type: "type", target: "input.search", value: "solace", timestamp: 200}
Expect:  Text input field receives value
Verify:  Trace shows value set in element state
```

### T4: Execute Navigate Action
```
Setup:   Type action complete
Input:   Execute action: {type: "navigate", value: "https://example.com/search", timestamp: 300}
Expect:  Navigation happens, URL changes
Verify:  Trace shows new URL in state_snapshot
```

### T5: Validate Final State & Generate Trace
```
Setup:   All actions executed
Input:   Compare final state_snapshot to expected post-state
Expect:  State hash matches episode's expected end state
Verify:  Execution trace generated with SHA256 checksum
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Episode file missing → Loading fails → T1 fails
**F2:** Invalid action type → Action executor doesn't handle it → T2 fails
**F3:** Target selector not found → Action can't find element → T2/T3 fail
**F4:** Navigation fails (network error) → State mismatch → T4 fails
**F5:** Post-state doesn't match → Execution wasn't deterministic → T5 fails

---

## 8. Visual Evidence (Proof Artifacts)

**execution-trace.json structure:**
```json
{
  "episode_id": "ep-001",
  "execution_id": "exec-20260214-001",
  "timestamp_started": "2026-02-14T16:55:00Z",
  "timestamp_completed": "2026-02-14T16:55:03Z",
  "total_duration_ms": 3000,
  "actions_executed": 3,
  "actions_passed": 3,
  "actions_failed": 0,
  "action_traces": [
    {
      "action_id": 0,
      "action_type": "click",
      "target": "button.submit",
      "status": "SUCCESS",
      "pre_state_snapshot": {"url": "...", "dom_hash": "..."},
      "post_state_snapshot": {"url": "...", "dom_hash": "..."},
      "execution_time_ms": 150
    }
  ],
  "final_state_snapshot": {"url": "...", "dom_hash": "..."},
  "final_state_matches_expected": true,
  "execution_trace_hash": "sha256:...",
  "determinism_verified": true
}
```

**proof.json structure:**
```json
{
  "spec_id": "wish-3.0-action-automation",
  "timestamp": "2026-02-14T16:55:00Z",
  "authority": "65537",
  "tests": [
    {
      "test_id": "T1",
      "name": "Load Episode",
      "status": "PASS"
    }
  ],
  "execution_summary": {
    "episodes_executed": 1,
    "total_actions": 3,
    "actions_passed": 3,
    "actions_failed": 0,
    "determinism_verified": true
  }
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Action executor and validation logic fully defined
- [x] **R4: Deterministic** — No network calls, state deterministic
- [x] **R5: Hermetic** — Tests work with mock/fixture data
- [x] **R6: Idempotent** — Can replay same episode multiple times
- [x] **R7: Fast** — All tests complete in <10 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same episode always produces same trace
- [x] **R10: Verifiable** — Artifacts prove execution and determinism

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Action executor implements all 6 action types
- [ ] Execution traces generated with full state snapshots
- [ ] Final state validation passes
- [ ] Determinism verified (replay produces identical trace)

---

## 11. Next Phase

→ **wish-4.0** (State Machine): Implement state transitions and validation

---

**Wish:** wish-3.0-action-automation
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-4.0, enables automated episode playback

*"Execute episodes deterministically."*
