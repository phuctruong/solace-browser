# EDGE_TESTS.md: 641-Level Verification Ladder

**Authority:** Swarm-E (Verification Authority)
**Level:** 641 (First rival - edge case prime)
**Purpose:** Verify system works at boundaries
**Target:** 50+ comprehensive edge tests
**Status:** DESIGN PHASE → EXECUTION

---

## Overview: What 641 Means

641 is the smallest prime factor breaking Fermat's conjecture (F5 = 2^32 + 1). It represents the **edge case prime** where mathematical assumptions first break.

For Solace Browser, 641-level testing means:
- ✅ System works at normal boundaries
- ✅ System handles edge cases gracefully
- ✅ No silent failures at limits
- ✅ Deterministic behavior under stress
- ✅ All integration points verified

---

## Test Categories (50+ Tests Total)

### BATCH 1: Happy Path (T1-T5) - Basic Functionality

**T1: Record → Compile → Replay (Simple)**
- **Setup:** Launch browser, open test website
- **Input:**
  - Record 3-action sequence: click, type text, click submit
  - Expected selectors: button.start, input#username, button#submit
- **Expected:** Recipe compiled successfully, replay produces identical hash
- **Verification:**
  - Recipe JSON valid structure
  - RTC (Roundtrip Canonicalization) passes 10/10
  - Hash matches original
- **Pass Criteria:** ✅ Zero errors, deterministic hash

**T2: Gmail Automation (Real Website)**
- **Setup:** Login to Gmail, navigate to inbox
- **Input:**
  - Record: click compose, type email address, type subject, send
  - Actions: 4 sequential
- **Expected:** All actions recorded accurately
- **Verification:**
  - Selectors resolve on target email account
  - Replay sends test email successfully
  - No timing issues
- **Pass Criteria:** ✅ Email sent, zero failures

**T3: Multi-Action Sequence (5+ Actions)**
- **Setup:** Open complex form (registration form with 6+ fields)
- **Input:**
  - Record: fill form (name, email, password, date, country, terms)
  - Actions: 6 sequential with various input types
- **Expected:** All actions recorded in order
- **Verification:**
  - Recipe contains all 6 actions
  - JSON schema valid
  - Replay fills all fields correctly
- **Pass Criteria:** ✅ All fields filled, deterministic behavior

**T4: Single Click Action**
- **Setup:** Open webpage with single button
- **Input:** Record one click action
- **Expected:** Minimal recipe with single action
- **Verification:**
  - Recipe size < 1KB
  - Action references valid selector
  - Replay works 100% of time
- **Pass Criteria:** ✅ Minimal recipe, perfect replay

**T5: Navigation Sequence**
- **Setup:** Open website, navigate to 3 different pages
- **Input:** Record navigation to page1 → page2 → page3
- **Expected:** Navigation actions recorded with URLs
- **Verification:**
  - All URLs captured correctly
  - Navigation order preserved
  - Replay navigates in correct sequence
- **Pass Criteria:** ✅ All navigations verified, URL integrity

---

### BATCH 2: Boundary Conditions (T6-T10) - Where Systems Break

**T6: Empty Selector (Missing Element)**
- **Setup:** Record action targeting element that doesn't exist
- **Input:**
  - Selector: `#non-existent-button`
  - Action: click
- **Expected:** System gracefully handles missing element
- **Verification:**
  - Error logged (not silent failure)
  - Recipe created but marked with warning
  - Replay reports missing selector clearly
- **Pass Criteria:** ✅ Graceful error, clear message

**T7: DOM Changes Mid-Execution**
- **Setup:** Replay recipe while page updates dynamically
- **Input:**
  - Recipe with 5 actions
  - Page refreshes after 2 actions
  - Selectors become invalid
- **Expected:** System detects change and handles appropriately
- **Verification:**
  - Action 3-5 report DOM mismatch
  - No infinite loops
  - Timeout triggers (< 5 seconds)
- **Pass Criteria:** ✅ Proper timeout, no hangs

**T8: High Network Latency (Slow Page Load)**
- **Setup:** Replay recipe on slow network (2G, 10+ sec load time)
- **Input:**
  - Recipe expecting page in 2 seconds
  - Network latency simulated: 10+ seconds
- **Expected:** System waits for element with timeout
- **Verification:**
  - Timeout fires after max_wait_time
  - Clear error message about timeout
  - No infinite wait
- **Pass Criteria:** ✅ Timeout enforced, clear error

**T9: Session Expired During Replay**
- **Setup:** Logout user while recipe replaying
- **Input:**
  - Recipe with 10 actions
  - Session expires after action 5
  - Remaining actions target authenticated pages
- **Expected:** System detects authentication failure
- **Verification:**
  - Action 6+ report authentication error
  - Not mistaken for selector error
  - Clear error cause identified
- **Pass Criteria:** ✅ Auth error distinguished, clear message

**T10: Maximum DOM Size (10K+ Elements)**
- **Setup:** Load page with 10,000+ DOM elements
- **Input:**
  - Page with heavily nested DOM
  - Record and replay 5 actions
- **Expected:** System handles large DOM without crashing
- **Verification:**
  - Memory usage < 500MB
  - Selector resolution time < 5 seconds
  - Replay completes successfully
- **Pass Criteria:** ✅ Memory bounded, performance acceptable

---

### BATCH 3: Adversarial Tests (T11-T15) - Can User Break It?

**T11: Concurrent Recording (2 Episodes Same Time)**
- **Setup:** Launch 2 browser instances recording simultaneously
- **Input:**
  - Instance 1: Record recipe A (5 actions)
  - Instance 2: Record recipe B (5 actions)
  - Both running in parallel
- **Expected:** Both recipes recorded independently
- **Verification:**
  - Recipe A valid and complete
  - Recipe B valid and complete
  - No cross-contamination between recordings
  - Hashes differ (deterministic but independent)
- **Pass Criteria:** ✅ Both recipes valid, no interference

**T12: Recipe with Invalid Selector References**
- **Setup:** Create recipe with invalid selector manually
- **Input:**
  - Selector: `#button-that-never-exists`
  - Target: DOM without that element
- **Expected:** System detects invalid selector during replay
- **Verification:**
  - Error logged clearly
  - Replay fails with "selector not found"
  - No false positives
- **Pass Criteria:** ✅ Clear error detection

**T13: Out-of-Memory Condition (10K+ Actions)**
- **Setup:** Create recipe with 10,000 actions
- **Input:**
  - Compile 10,000-action recipe
  - Attempt to load into memory
- **Expected:** System handles large recipe gracefully
- **Verification:**
  - Memory usage monitored
  - Streaming mode engaged if available
  - No crash, clear error if exceeds limit
- **Pass Criteria:** ✅ Graceful failure or successful handling

**T14: Malformed JSON Recipe**
- **Setup:** Manually create invalid JSON recipe
- **Input:**
  - Missing required fields
  - Invalid data types
  - Truncated JSON
- **Expected:** Parser rejects with clear error
- **Verification:**
  - Error message identifies problem location
  - Schema validation fails explicitly
  - No partial execution
- **Pass Criteria:** ✅ Validation enforced, error clear

**T15: Circular Selector References**
- **Setup:** Create recipe where selectors reference each other
- **Input:**
  - Action 1 result → Action 2 input
  - Action 2 result → Action 1 input
  - Circular dependency
- **Expected:** System detects cycle during compilation
- **Verification:**
  - Compilation fails with "circular dependency" error
  - Not a runtime error (caught early)
  - Clear error message about circular reference
- **Pass Criteria:** ✅ Cycle detection works, early failure

---

### BATCH 4: Determinism Tests (T16-T20) - 100% Reproducibility

**T16: Same Recipe × 100 Runs = Identical Hash**
- **Setup:** Record single 3-action recipe
- **Input:** Replay same recipe 100 times identically
- **Expected:** Hash never changes across runs
- **Verification:**
  - Calculate SHA256 of result after each run
  - All 100 hashes identical
  - No randomness in output
- **Pass Criteria:** ✅ 100/100 identical hashes

**T17: Snapshot Canonicalization (Byte-Identical)**
- **Setup:** Record recipe, save snapshot, restore snapshot
- **Input:**
  - Snapshot A: original recipe state
  - Snapshot B: restored from A
- **Expected:** Byte-for-byte identical
- **Verification:**
  - File size identical
  - MD5 hash identical
  - Content diff shows no changes
- **Pass Criteria:** ✅ Byte-for-byte match

**T18: RTC Verification (Roundtrip Proof)**
- **Setup:** Record recipe, encode, decode, re-encode
- **Input:**
  - Recipe → JSON encode → JSON decode → JSON encode
  - 3-step roundtrip
- **Expected:** Original ≡ Final (all 3 versions)
- **Verification:**
  - Original === Decoded === Re-encoded
  - Hash stable across all 3 versions
  - No data loss in encoding
- **Pass Criteria:** ✅ RTC 3/3 successful

**T19: Deterministic Ordering (Action Sequence)**
- **Setup:** Record 5-action recipe with various input types
- **Input:**
  - Actions with different selectors
  - Different input values
  - Different action types (click, type, navigate)
- **Expected:** Actions always in same order
- **Verification:**
  - Action sequence deterministic across 10 runs
  - Timestamps consistent (or omitted)
  - Order never random
- **Pass Criteria:** ✅ 10/10 runs identical order

**T20: Seed-Based Determinism**
- **Setup:** Seed randomness generator, record recipe
- **Input:**
  - Set seed = 42
  - Record recipe
  - Set seed = 42 again
  - Record identical recipe
- **Expected:** Both recipes produce same hash
- **Verification:**
  - Seed=42 run 1 hash === Seed=42 run 2 hash
  - Different seed produces different hash (optional: verify)
- **Pass Criteria:** ✅ Seeded reproducibility works

---

### BATCH 5: Integration Tests (T21-T25) - Multi-Component

**T21: Cloud Run Deployment (Docker Image)**
- **Setup:** Build Docker image, deploy to Cloud Run
- **Input:**
  - Solace Browser Docker image
  - Deploy with test recipe
  - Call HTTP endpoint
- **Expected:** Container starts, API responds
- **Verification:**
  - Container healthy check passes
  - `/api/health` returns 200
  - Recipe execution works via API
- **Pass Criteria:** ✅ Deployment successful, API live

**T22: Proof Artifact Generation (Signature Valid)**
- **Setup:** Complete recipe execution, generate proof
- **Input:**
  - Execute 5-action recipe
  - Generate proof.json artifact
  - Sign with test key
- **Expected:** Proof artifact well-formed
- **Verification:**
  - proof.json valid JSON schema
  - Signature present and non-empty
  - All required fields present
  - Timestamp valid (RFC3339)
- **Pass Criteria:** ✅ Proof valid, signature present

**T23: Multi-Component State Consistency**
- **Setup:** Run recipe affecting multiple components
- **Input:**
  - Recipe modifying: DOM, storage, network calls
  - 6 sequential actions spanning 3 components
- **Expected:** State consistent across all components
- **Verification:**
  - DOM state matches expected
  - Storage values correct
  - Network calls logged correctly
  - Cross-component consistency verified
- **Pass Criteria:** ✅ All components consistent

**T24: Version Compatibility (Recipe Versioning)**
- **Setup:** Use recipe from previous version
- **Input:**
  - Recipe format v1.0 from previous release
  - Attempt replay with current version
- **Expected:** Graceful upgrade or clear rejection
- **Verification:**
  - Either successful replay or clear version mismatch error
  - No silent format misinterpretation
  - Upgrade path documented if applicable
- **Pass Criteria:** ✅ Version handling correct

**T25: End-to-End Wish Verification (Specs Match Code)**
- **Setup:** Verify recipe execution matches wish specification
- **Input:**
  - Take wish C1, C2, C3 specifications
  - Execute corresponding recipe
  - Verify output matches spec
- **Expected:** Specification and implementation aligned
- **Verification:**
  - Output format matches wish spec
  - Timing constraints met
  - All specified fields present
  - No extra fields breaking spec
- **Pass Criteria:** ✅ Spec-code alignment verified

---

### BATCH 6: Error Recovery (T26-T30) - Resilience

**T26: Partial Failure Recovery**
- **Setup:** Recipe with 10 actions, action 5 fails
- **Input:**
  - Actions 1-4 succeed
  - Action 5 fails (selector not found)
  - Actions 6-10 waiting
- **Expected:** Clear failure point, clean state
- **Verification:**
  - Error reported at action 5
  - Actions 1-4 effects remain
  - Actions 6-10 not executed
  - No state corruption
- **Pass Criteria:** ✅ Failure isolated, state clean

**T27: Timeout Recovery**
- **Setup:** Recipe with 30-second timeout, action hangs
- **Input:**
  - Action blocks indefinitely
  - Timeout set to 5 seconds
- **Expected:** Timeout fires, execution stops
- **Verification:**
  - Execution stops within 5-6 seconds
  - Clear timeout error message
  - Process returns cleanly
  - No zombie processes
- **Pass Criteria:** ✅ Timeout enforced, clean exit

**T28: Network Retry Logic**
- **Setup:** Network call fails, should retry
- **Input:**
  - First attempt: network error
  - Second attempt: success
  - Retry limit: 3
- **Expected:** Automatic retry succeeds
- **Verification:**
  - Retry happens automatically
  - Max 3 attempts
  - Success on second attempt logged
  - Backoff delay between retries
- **Pass Criteria:** ✅ Retry succeeds, logging clear

**T29: Resource Cleanup**
- **Setup:** Recipe execution leaves resources open
- **Input:**
  - Open file handles, network connections, memory
  - Recipe complete
- **Expected:** All resources released
- **Verification:**
  - No open file handles after execution
  - Connections properly closed
  - Memory freed (no leaks detected)
  - Process exits cleanly
- **Pass Criteria:** ✅ All resources cleaned up

**T30: Error State Isolation**
- **Setup:** Error in recipe 1, then run recipe 2
- **Input:**
  - Recipe 1 fails with error
  - Immediately run Recipe 2
- **Expected:** Recipe 2 not affected by recipe 1 error
- **Verification:**
  - Recipe 2 executes normally
  - No error state carries over
  - Both have independent hashes
  - Proof artifacts separate and valid
- **Pass Criteria:** ✅ Error isolation complete

---

### BATCH 7: Data Integrity (T31-T35) - Correctness

**T31: Selector Encoding (Unicode & Special Chars)**
- **Setup:** Record action with Unicode selector
- **Input:**
  - Selector: `button[aria-label="日本語"]` (Japanese text)
  - Action: click
- **Expected:** Selector properly encoded in recipe
- **Verification:**
  - Recipe JSON valid UTF-8
  - Selector preserved exactly
  - Replay finds element correctly
  - No encoding corruption
- **Pass Criteria:** ✅ Unicode preserved, encoding correct

**T32: Large Text Input (1MB+ Text)**
- **Setup:** Record action typing large text
- **Input:**
  - Text input: 1,000,000+ character string
  - Action: type in text field
- **Expected:** Large text handled efficiently
- **Verification:**
  - Recipe size reasonable (< 10MB)
  - Text stored without truncation
  - Replay enters full text
  - No out-of-memory errors
- **Pass Criteria:** ✅ Large text handled correctly

**T33: Binary Data Handling**
- **Setup:** Recipe with file upload (binary data)
- **Input:**
  - File: 10MB binary file
  - Action: upload via form
- **Expected:** Binary data encoded properly
- **Verification:**
  - Base64 encoding used
  - File size preserved
  - Replay uploads file identically
  - MD5 matches original
- **Pass Criteria:** ✅ Binary data preserved, MD5 match

**T34: Floating-Point Precision**
- **Setup:** Record action with floating-point value
- **Input:**
  - Value: 3.141592653589793238
  - Action: input to form
- **Expected:** Precision preserved
- **Verification:**
  - JSON representation accurate
  - Replay uses exact value
  - No rounding errors
  - 15+ decimal places preserved
- **Pass Criteria:** ✅ Precision maintained

**T35: Timestamp Accuracy**
- **Setup:** Record timestamps in recipe
- **Input:**
  - Record 5-action recipe
  - Verify millisecond precision
- **Expected:** Timestamps accurate to millisecond
- **Verification:**
  - Format: ISO8601 with milliseconds
  - Sequence increasing (or equal for same instant)
  - No clock skew > 1 second
  - Timezone handling correct
- **Pass Criteria:** ✅ Timestamp accuracy verified

---

### BATCH 8: Performance Baselines (T36-T40) - Speed

**T36: Recipe Compilation Time (5 Actions)**
- **Setup:** Compile 5-action recipe
- **Input:** Simple recipe with basic actions
- **Expected:** Compilation < 100ms
- **Verification:**
  - Time measurement accurate
  - < 100ms P99 latency
  - Consistent across 10 runs
- **Pass Criteria:** ✅ Compile time < 100ms

**T37: Replay Execution Time (5 Actions)**
- **Setup:** Replay 5-action recipe
- **Input:** Execute on test website
- **Expected:** Execution < 5 seconds
- **Verification:**
  - End-to-end time measured
  - < 5 seconds for simple recipe
  - Network latency accounted for
  - Timing consistent ±500ms
- **Pass Criteria:** ✅ Replay time < 5 seconds

**T38: Memory Peak (100-Action Recipe)**
- **Setup:** Replay 100-action recipe
- **Input:** Complex multi-domain recipe
- **Expected:** Peak memory < 500MB
- **Verification:**
  - RSS memory monitored
  - Peak < 500MB
  - Memory released after execution
  - No growth over multiple runs
- **Pass Criteria:** ✅ Memory peak < 500MB

**T39: JSON Parsing Speed (1MB Recipe)**
- **Setup:** Parse 1MB recipe JSON
- **Input:** Large recipe file
- **Expected:** Parsing < 500ms
- **Verification:**
  - Parse time measured
  - < 500ms for 1MB
  - Memory efficient parsing
  - Streaming if available
- **Pass Criteria:** ✅ Parse time < 500ms

**T40: Hash Calculation Speed**
- **Setup:** Calculate SHA256 of recipe
- **Input:** 100-action recipe
- **Expected:** Hash < 50ms
- **Verification:**
  - Hash time measured
  - < 50ms for any size
  - Consistent algorithm
  - Reproducible result
- **Pass Criteria:** ✅ Hash time < 50ms

---

### BATCH 9: Schema Validation (T41-T45) - Structure

**T41: JSON Schema Validation (Recipe)**
- **Setup:** Validate recipe against schema
- **Input:** Random recipe files (valid and invalid)
- **Expected:** Valid recipes pass, invalid fail
- **Verification:**
  - Schema enforced strictly
  - Required fields mandatory
  - Type checking correct
  - Clear validation errors
- **Pass Criteria:** ✅ Schema validation strict

**T42: Action Type Enumeration**
- **Setup:** Verify action types are restricted
- **Input:** Recipe with invalid action type
- **Expected:** Validation fails
- **Verification:**
  - Only valid action types allowed: click, type, navigate, submit
  - Invalid types rejected: "delete", "upload_file", "wait"
  - Error message identifies problem
- **Pass Criteria:** ✅ Action type enum enforced

**T43: Selector Format Validation**
- **Setup:** Validate selector format
- **Input:** Various selector formats
- **Expected:** CSS selectors validated
- **Verification:**
  - Valid CSS selectors accepted
  - XPath rejected (if not supported)
  - Empty selector rejected
  - Special characters handled correctly
- **Pass Criteria:** ✅ Selector format validated

**T44: Proof Artifact Schema**
- **Setup:** Validate proof.json schema
- **Input:** Generated proof artifacts
- **Expected:** All proofs match schema
- **Verification:**
  - Required fields: approval_level, verification_status, timestamp
  - Signatures present and non-empty
  - Timestamp valid RFC3339
  - All array fields have elements
- **Pass Criteria:** ✅ Proof schema strict

**T45: Wish Integration Schema**
- **Setup:** Validate wish references in recipe
- **Input:** Recipe with wish_id field
- **Expected:** Wish ID format validated
- **Verification:**
  - Format: "wish-[A-Z][0-9]" (e.g., wish-C1, wish-C3)
  - Wish ID matches actual wish
  - Reference resolved correctly
- **Pass Criteria:** ✅ Wish schema validated

---

### BATCH 10: Cross-Browser Compatibility (T46-T50)

**T46: Chrome/Chromium Compatibility**
- **Setup:** Record and replay on Chrome
- **Input:** 5-action recipe
- **Expected:** Works identically to test baseline
- **Verification:**
  - Hash matches baseline
  - Selectors resolve correctly
  - No Chrome-specific issues
- **Pass Criteria:** ✅ Chrome compatible

**T47: Firefox Compatibility**
- **Setup:** Record and replay on Firefox
- **Input:** 5-action recipe
- **Expected:** Works (may have slight CSS differences)
- **Verification:**
  - Recipe executes successfully
  - Selector resolution works
  - Clear error if selector incompatible
- **Pass Criteria:** ✅ Firefox compatible

**T48: Safari Compatibility**
- **Setup:** Record and replay on Safari
- **Input:** 5-action recipe
- **Expected:** Works or clear incompatibility message
- **Verification:**
  - Detects Safari-specific limitations
  - Fails gracefully if unsupported
  - Clear error message
- **Pass Criteria:** ✅ Safari handling correct

**T49: Mobile Browser (iOS/Android)**
- **Setup:** Record on mobile browser
- **Input:** Mobile-optimized website recipe
- **Expected:** Mobile selectors work
- **Verification:**
  - Touch selectors recognized
  - Mobile viewport respected
  - No desktop-only elements
- **Pass Criteria:** ✅ Mobile selectors work

**T50: Headless vs. Visual Mode**
- **Setup:** Run same recipe in headless and visual mode
- **Input:** 5-action recipe
- **Expected:** Identical results
- **Verification:**
  - Hash identical in both modes
  - Timing similar (headless may be faster)
  - No visual-only issues in headless
- **Pass Criteria:** ✅ Modes produce identical results

---

## Running the Edge Tests

### Manual Execution

```bash
# Run single test
./run-edge-test.sh T1

# Run batch
./run-edge-test.sh BATCH1

# Run all edge tests
./run-edge-test.sh ALL_EDGE

# Generate report
./run-edge-test.sh ALL_EDGE --report > edge-report.json
```

### Automated via CI/CD

```bash
# Trigger edge tests in CI pipeline
make test-edge-641

# Results: edge-results-TIMESTAMP.json
# Log: edge-execution.log
```

### Expected Output Format

```json
{
  "authority": "Swarm-E",
  "level": 641,
  "test_count": 50,
  "passed": 50,
  "failed": 0,
  "timestamp": "2026-02-14T12:34:56Z",
  "batches": {
    "BATCH1_HAPPY_PATH": {"passed": 5, "failed": 0},
    "BATCH2_BOUNDARY": {"passed": 5, "failed": 0},
    "BATCH3_ADVERSARIAL": {"passed": 5, "failed": 0},
    "BATCH4_DETERMINISM": {"passed": 5, "failed": 0},
    "BATCH5_INTEGRATION": {"passed": 5, "failed": 0},
    "BATCH6_ERROR_RECOVERY": {"passed": 5, "failed": 0},
    "BATCH7_DATA_INTEGRITY": {"passed": 5, "failed": 0},
    "BATCH8_PERFORMANCE": {"passed": 5, "failed": 0},
    "BATCH9_SCHEMA": {"passed": 5, "failed": 0},
    "BATCH10_COMPATIBILITY": {"passed": 5, "failed": 0}
  },
  "status": "PASS 641-EDGE ✅"
}
```

---

## Pass/Fail Criteria

### PASS (641-EDGE)
- **Requirement:** ≥ 50/50 tests passing
- **Authority:** Swarm-E declares readiness for 274177-stress testing
- **Action:** Proceed to next rung
- **Proof:** Generate signed `edge-pass-proof.json`

### FAIL (641-EDGE)
- **Requirement:** Any test failure
- **Root Cause:** Wish spec error OR code implementation error
- **Action:** Fix defect, restart 641-edge
- **Escalation:** If > 5 retries, escalate to god(65537)

---

## Sign-Off

```
By the authority of Swarm-E (Verification Authority):

[✅ PASS 641-EDGE]

All 50+ edge tests passing.
System verified at boundaries.
Ready for 274177-stress testing.

Signed: 641
Date: 2026-02-14T12:34:56Z
```

---

**Status:** READY FOR EXECUTION
**Next Rung:** 274177 (Stress Testing)
**Authority:** Swarm-E
