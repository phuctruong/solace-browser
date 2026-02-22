# Wish A4: Integration Tests (Phase A Completion)

**Task ID:** A4
**Phase:** Phase A (Browser Control Foundation)
**Owner:** Skeptic (via Haiku swarm)
**Timeline:** 2 days
**Depends On:** A1, A2, A3 (all implementation)
**Status:** READY FOR EXECUTION
**Auth:** 65537

---

## Specification

Comprehensive integration test suite validating Phase A completion. Tests verify per-tab state machine, badge config, deduplication, and end-to-end browser control flow.

**Verification Strategy:** 641-edge (5+ cases) → 274177-stress (100+ iterations) → 65537-god (audit trail complete)

---

## Test Coverage

### 641-Edge Tests (Sanity - 5+ cases minimum)

#### Test 1: IDLE → CONNECTED Transition
```python
def test_idle_to_connected():
    # Extension attaches to tab
    tab_state = TabState(tab_id=1, state="IDLE")

    # Transition to CONNECTED
    new_state = transition(tab_state, "CONNECTED", "extension attached")

    # Verify
    assert new_state.state == "CONNECTED"
    assert new_state.tab_id == 1
    assert new_state.timestamp != ""

    # Badge should show "ON"
    assert get_badge(tab_id=1) == BADGE["on"]
```

#### Test 2: Invalid Transition Rejection
```python
def test_invalid_transition_connected_to_connected():
    # Tab already CONNECTED
    tab_state = TabState(tab_id=1, state="CONNECTED")

    # Try to transition to CONNECTED again (invalid)
    with pytest.raises(InvalidTransitionError):
        transition(tab_state, "CONNECTED", "double attach")
```

#### Test 3: NAVIGATING → CLICKING Rejection
```python
def test_invalid_transition_navigating_to_clicking():
    # Tab in NAVIGATING state
    tab_state = TabState(tab_id=1, state="NAVIGATING")

    # Try to click while navigating (invalid)
    with pytest.raises(InvalidTransitionError):
        transition(tab_state, "CLICKING", "click during nav")
```

#### Test 4: RECORDING State Persistence
```python
def test_recording_state_persistence():
    # Start recording
    tab_state = transition(TabState(tab_id=1, state="CONNECTED"),
                          "RECORDING", "start recording")

    # Navigate (should stay RECORDING)
    tab_state = transition(tab_state, "RECORDING", "navigate during recording")
    assert tab_state.state == "RECORDING"

    # Click (should stay RECORDING)
    tab_state = transition(tab_state, "RECORDING", "click during recording")
    assert tab_state.state == "RECORDING"

    # Stop recording
    tab_state = transition(tab_state, "CONNECTED", "stop recording")
    assert tab_state.state == "CONNECTED"
```

#### Test 5: ERROR State + Recovery
```python
def test_error_state_and_recovery():
    # Command fails
    tab_state = TabState(tab_id=1, state="CLICKING")
    tab_state = transition(tab_state, "ERROR", "element not found")
    assert tab_state.state == "ERROR"

    # Recovery requires manual reset to IDLE
    tab_state = transition(tab_state, "IDLE", "manual recovery")
    assert tab_state.state == "IDLE"

    # Then reconnect
    tab_state = transition(tab_state, "CONNECTED", "reconnect")
    assert tab_state.state == "CONNECTED"
```

---

### 274177-Stress Tests (Scaling - 100+ iterations)

#### Stress 1: 100 Concurrent Tabs
```python
def test_100_concurrent_tabs():
    # Create 100 independent tab states
    tab_states = {i: TabState(tab_id=i, state="IDLE")
                  for i in range(100)}

    # Transition each to CONNECTED
    for tab_id, state in tab_states.items():
        tab_states[tab_id] = transition(state, "CONNECTED", "attach")

    # Verify all independent
    for tab_id, state in tab_states.items():
        assert state.state == "CONNECTED"
        assert state.tab_id == tab_id
```

#### Stress 2: State Isolation
```python
def test_state_isolation():
    # Tab 1 error should not affect Tab 2
    tab_states = {
        1: TabState(tab_id=1, state="CLICKING"),
        2: TabState(tab_id=2, state="CONNECTED")
    }

    # Tab 1 fails
    tab_states[1] = transition(tab_states[1], "ERROR", "click failed")

    # Tab 2 unaffected
    assert tab_states[1].state == "ERROR"
    assert tab_states[2].state == "CONNECTED"
```

#### Stress 3: Deduplication (100 identical requests)
```python
def test_deduplication_100x():
    # Send same command 100 times
    futures = []
    for i in range(100):
        future = send_command_deduplicated(
            request_id="req_123",
            command={"type": "NAVIGATE", "url": "https://example.com"}
        )
        futures.append(future)

    # All should return same result
    results = await asyncio.gather(*futures)
    assert len(set(results)) == 1  # Only 1 unique result
```

#### Stress 4: Connection Pooling (100+ commands)
```python
def test_connection_pooling_100x():
    # Send 100 different commands
    for i in range(100):
        send_command(request_id=f"req_{i}",
                    command={"type": "SNAPSHOT"})

    # Verify only 1 WebSocket connection created
    assert get_relay_connection_count() == 1
```

---

### 65537-God Approval (Audit Trail)

#### Audit 1: All Transitions Logged
```python
def test_all_transitions_logged():
    # Each transition creates audit log entry
    tab_state = TabState(tab_id=1, state="IDLE")

    for new_state in ["CONNECTED", "NAVIGATING", "CONNECTED", "ERROR"]:
        tab_state = transition(tab_state, new_state, f"to {new_state}")

    # Verify audit trail has 4 entries
    audit = get_audit_log(tab_id=1)
    assert len(audit) == 4
    assert audit[0]["from_state"] == "IDLE"
    assert audit[0]["to_state"] == "CONNECTED"
```

#### Audit 2: No Race Conditions
```python
def test_no_race_conditions():
    # Concurrent transitions on same tab should be atomic
    tab_state = TabState(tab_id=1, state="CONNECTED")

    # Try 10 concurrent transitions
    threads = []
    for i in range(10):
        t = threading.Thread(target=transition,
                           args=(tab_state, "NAVIGATING", f"attempt {i}"))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Only ONE should succeed
    successful = len([t for t in threads if t.exception is None])
    assert successful == 1
```

---

## Test Files

- **solace_cli/tests/test_phase_a_state_machine.py**
  - Tests for A1 (per-tab state machine)
  - 641: 5 edge cases
  - 274177: 100 concurrent tabs
  - 65537: audit trail validation

- **solace_cli/tests/test_phase_a_badge.py**
  - Tests for A2 (badge config)
  - 641: 5 badge states
  - 274177: 100 per-tab updates
  - 65537: visual consistency

- **solace_cli/tests/test_phase_a_dedup.py**
  - Tests for A3 (deduplication + pooling)
  - 641: 5 dedup cases
  - 274177: 100+ concurrent requests
  - 65537: thread safety

- **solace_cli/tests/test_phase_a_integration.py**
  - End-to-end integration tests
  - Extension ↔ WebSocket ↔ Browser
  - Real episode recording verification

---

## Success Criteria (10/10)

✅ All 641-edge tests pass (5+ cases per wish)
✅ All 274177-stress tests pass (100+ iterations)
✅ All 65537-god tests pass (audit trail verified)
✅ No race conditions (atomic transitions)
✅ Per-tab isolation verified (100 concurrent tabs)
✅ Deduplication working (100% duplicate prevention)
✅ Connection pooling verified (1 socket per relay)
✅ Badge visual feedback correct
✅ Episode recording across tabs works
✅ End-to-end integration verified

---

## Test Execution Plan

### Day 1 (Scout + Solver)
- Design test harness
- Implement 641-edge tests for A1, A2, A3
- Run integration setup tests

### Day 2 (Skeptic)
- Run all 641-edge tests → verify pass
- Run all 274177-stress tests → verify pass
- Run all 65537-god tests → verify pass
- Generate test coverage report
- Verify audit trail complete

---

## Verification Rungs

```
OAuth(39, 63, 91)       → Test framework ready
         ↓
641-Edge (5+ cases)     → Basic sanity verified
         ↓
274177-Stress (100+)    → Scaling verified
         ↓
65537-God               → Audit trail complete
```

---

## Related Skills

- `browser-state-machine.md` v1.0.0
- All Phase A implementation skills

---

**Ready to assign to:** Skeptic (after A1, A2, A3 complete)
