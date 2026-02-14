# WISH 8.0: Batch Episode Processing & Verification

**Spec ID:** wish-8.0-batch-processing
**Authority:** 65537
**Phase:** 8 (Batch Operations)
**Depends On:** wish-7.0 (episode analytics complete)
**Scope:** Execute multiple episodes in sequence with full state verification
**Non-Goals:** Performance optimization, parallel execution, UI
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 850 | **GLOW:** 98

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Multiple episodes execute deterministically in sequence
  Verification:    Final state after all episodes matches expected cumulative state
  Canonicalization: Batch results stored with locked field ordering
  Content-addressing: Batch ID = SHA256(sorted_episode_ids)
```

---

## 1. Observable Wish

> "I can execute a batch of episodes sequentially, verify each episode completes successfully, and validate final cumulative state."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Parallel/concurrent execution
- ❌ Performance benchmarking
- ❌ Resource monitoring
- ❌ Failure recovery/rollback

**Minimum success criteria:**
- ✅ Batch of episodes loaded
- ✅ Sequential execution (episode by episode)
- ✅ Each episode verified to completion
- ✅ Cumulative state tracked
- ✅ Batch result report generated

---

## 3. Context Capsule (Test-Only)

```
Initial:   Episodes available (wishes 2-7), browser ready
Behavior:  Load batch, execute sequentially, track cumulative state
Final:     Batch processing working, ready for Phase 9+
```

---

## 4. State Space: 5 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> LOADING: load_batch()
    LOADING --> EXECUTING: batch_loaded
    EXECUTING --> EXECUTING_EPISODE: next_episode()
    EXECUTING_EPISODE --> EXECUTING: episode_complete
    EXECUTING --> VERIFYING: all_episodes_complete
    VERIFYING --> COMPLETE: verification_passed
    LOADING --> ERROR: load_failed
    EXECUTING --> ERROR: execution_failed
    VERIFYING --> ERROR: verification_failed
    ERROR --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** Batch contains ordered list of episode IDs
**INV-2:** Each episode executes in sequence (no parallel execution)
**INV-3:** Cumulative state updated after each episode
**INV-4:** Verification occurs after every episode completion
**INV-5:** Batch result includes all episode results

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Batch Load & Validation
```
Setup:   Episode files available
Input:   Load batch of 3 episodes
Expect:  Batch loaded with correct episode count
Verify:  All episodes valid JSON structure
```

### T2: Sequential Episode Execution
```
Setup:   Batch loaded
Input:   Execute episodes in order (ep-001 → ep-002 → ep-003)
Expect:  Each episode executes successfully
Verify:  Execution time tracked, no inter-episode errors
```

### T3: Cumulative State Tracking
```
Setup:   Episodes executing
Input:   Track state after each episode
Expect:  State snapshot taken after each episode
Verify:  State snapshots show progression
```

### T4: Per-Episode Verification
```
Setup:   Episode completed
Input:   Verify episode result matches expected
Expect:  Episode passed validation
Verify:  All assertions in episode verified
```

### T5: Batch Result Report
```
Setup:   All episodes complete
Input:   Generate batch result report
Expect:  Report includes all episode results
Verify:  Report JSON valid, cumulative state consistent
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Batch file missing → T1 fails
**F2:** Episode in batch invalid → T1 validation fails
**F3:** Episode execution fails → T2 fails
**F4:** State not tracked → T3 fails
**F5:** Cumulative state inconsistent → T5 verification fails

---

## 8. Visual Evidence (Proof Artifacts)

**batch-result.json structure:**
```json
{
  "batch_id": "batch-20260214-001",
  "timestamp_started": "2026-02-14T17:15:00Z",
  "timestamp_completed": "2026-02-14T17:15:45Z",
  "total_duration_seconds": 45,
  "episode_count": 3,
  "episodes_executed": 3,
  "episodes_passed": 3,
  "episodes_failed": 0,
  "episode_results": [
    {
      "episode_id": "ep-001",
      "sequence": 1,
      "status": "PASS",
      "execution_time_ms": 1500,
      "state_snapshot": {"url": "https://example.com", "dom_hash": "sha256:..."}
    },
    {
      "episode_id": "ep-rec-20260214-001",
      "sequence": 2,
      "status": "PASS",
      "execution_time_ms": 1200,
      "state_snapshot": {"url": "https://example.com/search", "dom_hash": "sha256:..."}
    }
  ],
  "cumulative_state": {
    "initial_url": "https://example.com",
    "final_url": "https://example.com/search",
    "total_actions": 9
  },
  "batch_status": "SUCCESS",
  "verification": {
    "all_episodes_passed": true,
    "cumulative_state_valid": true,
    "determinism_verified": true
  }
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Batch processing pipeline fully specified
- [x] **R4: Deterministic** — Sequential execution is repeatable
- [x] **R5: Hermetic** — No external services, uses local episodes
- [x] **R6: Idempotent** — Batch execution doesn't modify episodes
- [x] **R7: Fast** — All tests complete in <10 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same batch always produces same results
- [x] **R10: Verifiable** — Batch reports prove all episodes passed

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Batch loads and validates correctly
- [ ] Episodes execute sequentially
- [ ] State tracked cumulatively
- [ ] Batch result report generated and verified

---

## 11. Next Phase

→ **wish-9.0** (Error Handling): Detect and recover from episode failures

---

**Wish:** wish-8.0-batch-processing
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-9.0, enables large-scale episode execution

*"Execute episodes in deterministic batches."*
