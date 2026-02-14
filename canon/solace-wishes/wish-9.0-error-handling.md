# WISH 9.0: Error Handling & Recovery

**Spec ID:** wish-9.0-error-handling
**Authority:** 65537
**Phase:** 9 (Error Management)
**Depends On:** wish-8.0 (batch processing complete)
**Scope:** Detect, classify, and recover from episode execution errors
**Non-Goals:** Automatic failure fixes, ML-based recovery (Phase 12+), performance tuning
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 900 | **GLOW:** 99

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Errors are classifiable into recovery strategies
  Verification:    Each error type has defined recovery action
  Canonicalization: Error reports stored in canonical JSON format
  Content-addressing: Error ID = SHA256(error_type + context)
```

---

## 1. Observable Wish

> "I can detect episode execution errors, classify them by type, execute recovery strategies, and log complete error context for analysis."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Automatic bug fixes
- ❌ ML-based error prediction (Phase 12+)
- ❌ Real-time error prevention
- ❌ User notification/alerting

**Minimum success criteria:**
- ✅ Error detection (action fails, state mismatch, timeout)
- ✅ Error classification (3+ error types)
- ✅ Recovery strategy execution (retry, skip, abort)
- ✅ Error context logging (full state, action, result)
- ✅ Error report generation

---

## 3. Context Capsule (Test-Only)

```
Initial:   Episodes executing (wish-8.0), errors may occur
Behavior:  Detect errors, classify, execute recovery, log context
Final:     Error handling working, batch execution resilient
```

---

## 4. State Space: 6 States

```
state_diagram-v2
    [*] --> EXECUTING
    EXECUTING --> ERROR_DETECTED: error_thrown
    ERROR_DETECTED --> ERROR_CLASSIFIED: classification_complete
    ERROR_CLASSIFIED --> RECOVERING: recovery_strategy_selected
    RECOVERING --> RECOVERED: recovery_successful
    RECOVERING --> FAILED: recovery_failed
    RECOVERED --> EXECUTING: continue_next_action
    FAILED --> ABORTED: max_retries_exceeded
    EXECUTING --> COMPLETED: all_actions_done
    ABORTED --> [*]
    COMPLETED --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** All errors caught and classified (no unhandled exceptions)
**INV-2:** Error types: ActionFailed, StateMismatch, Timeout, ElementNotFound
**INV-3:** Recovery strategies: Retry, Skip, Abort
**INV-4:** Error report includes: type, context, timestamp, recovery action, outcome
**INV-5:** All errors logged deterministically (same error → same log entry)

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Error Detection Works
```
Setup:   Episode executing with invalid action
Input:   Execute action that will fail (click non-existent element)
Expect:  Error caught and reported
Verify:  Error message captured, execution pauses
```

### T2: Error Classification
```
Setup:   Error detected
Input:   Classify error type (ActionFailed, StateMismatch, etc.)
Expect:  Error type correctly identified
Verify:  Classification matches error pattern
```

### T3: Recovery Strategy Execution
```
Setup:   Error classified
Input:   Execute recovery strategy (Retry, Skip, Abort)
Expect:  Recovery action executes without error
Verify:  State consistent after recovery
```

### T4: Error Context Logging
```
Setup:   Error and recovery complete
Input:   Generate error log entry
Expect:  Log contains: error, action, state, recovery, outcome
Verify:  All fields present and consistent
```

### T5: Error Report Generation
```
Setup:   Multiple errors logged during batch execution
Input:   Generate comprehensive error report
Expect:  Report lists all errors with context
Verify:  Error count matches, all details present
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Error not caught → T1 fails, unhandled exception
**F2:** Error type misclassified → T2 fails, wrong recovery
**F3:** Recovery fails → T3 fails, execution stuck
**F4:** Error context missing → T4 fails, incomplete log
**F5:** Error count inconsistent → T5 fails, report incomplete

---

## 8. Visual Evidence (Proof Artifacts)

**error-report.json structure:**
```json
{
  "report_id": "err-report-20260214-001",
  "timestamp": "2026-02-14T17:20:00Z",
  "batch_id": "batch-20260214-001",
  "total_errors": 2,
  "errors_by_type": {
    "ActionFailed": 1,
    "StateMismatch": 1
  },
  "errors": [
    {
      "error_id": "err-20260214-001",
      "timestamp": "2026-02-14T17:20:15Z",
      "error_type": "ActionFailed",
      "episode_id": "ep-001",
      "action_sequence": 3,
      "action": {
        "type": "click",
        "target": "button.submit",
        "value": null
      },
      "error_message": "Element button.submit not found in DOM",
      "pre_state": {
        "url": "https://example.com",
        "dom_hash": "sha256:..."
      },
      "recovery_strategy": "Retry",
      "retry_attempt": 1,
      "recovery_successful": true,
      "post_recovery_state": {
        "url": "https://example.com",
        "dom_hash": "sha256:..."
      }
    }
  ],
  "recovery_statistics": {
    "total_recoveries": 2,
    "successful_recoveries": 2,
    "failed_recoveries": 0,
    "recovery_success_rate": 1.0
  },
  "summary": {
    "batch_resilience": "good",
    "execution_continued_after_error": true,
    "batch_completion_despite_errors": true
  }
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Error handling pipeline fully specified
- [x] **R4: Deterministic** — Error classification is repeatable
- [x] **R5: Hermetic** — No external services, uses local episodes
- [x] **R6: Idempotent** — Error handling doesn't modify episodes
- [x] **R7: Fast** — All tests complete in <10 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same error always produces same recovery
- [x] **R10: Verifiable** — Error reports prove all errors handled

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Error detection working for all error types
- [ ] Error classification accurate
- [ ] Recovery strategies execute successfully
- [ ] Error report complete and accurate

---

## 11. Next Phase

→ **wish-10.0** (Performance Metrics): Measure and optimize execution performance

---

**Wish:** wish-9.0-error-handling
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-10.0, makes batch execution resilient to failures

*"Handle errors, continue execution."*
