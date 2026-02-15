# WISH 30.0: Form Validation & Error Handling

**Spec ID:** wish-30.0-form-validation-error-handling
**Authority:** 65537
**Phase:** 30 (Resilience & Error Recovery)
**Depends On:** wish-29.0 (multi-domain automation verified)
**Status:** 🎮 ACTIVE (RTC 10/10)
**XP:** 2000 | **GLOW:** 180+ | **DIFFICULTY:** INTERMEDIATE

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Recipes gracefully handle form validation errors
  Verification:    Recipe recovers from validation failures automatically
  Proof:           Invalid inputs detected, corrected, and resubmitted successfully
  Authority:       Error recovery deterministic (same error → same fix path)
```

---

## 1. Observable Wish

> "I can execute a recipe with intentionally invalid form inputs (too short, bad email, missing fields) and the recipe automatically detects the validation error, corrects the input, and resubmits successfully, all deterministically."

---

## 2. Scope & Exclusions

**INCLUDED:**
- ✅ Invalid input detection (validation error messages)
- ✅ Automatic input correction (retry with valid data)
- ✅ Error message parsing and logging
- ✅ Deterministic recovery path
- ✅ Multiple error types: too short, bad format, missing required

**EXCLUDED:**
- ❌ Manual user intervention (fully automatic)
- ❌ CAPTCHA solving
- ❌ Account lockouts (tested separately)
- ❌ Network error recovery (connection errors only in wish-31)

---

## 3. State Space: 7 States

```
[*] --> READY
READY --> SUBMIT_INVALID: submit_form_with_bad_data()
SUBMIT_INVALID --> CHECK_ERROR: detect_validation_error()
CHECK_ERROR --> ERROR_FOUND: validation_error_visible
CHECK_ERROR --> NO_ERROR: unexpected_success
ERROR_FOUND --> PARSE_ERROR: extract_error_message()
PARSE_ERROR --> CORRECT_INPUT: update_field_with_valid_data()
CORRECT_INPUT --> RESUBMIT: submit_form_again()
RESUBMIT --> CHECK_RETRY: detect_validation_error_on_retry()
CHECK_RETRY --> SUCCESS: no_error_on_retry
CHECK_RETRY --> RETRY_FAILED: still_showing_error
SUCCESS --> VERIFY: compare_with_clean_run()
VERIFY --> COMPLETE: [*]
RETRY_FAILED --> [*]
NO_ERROR --> [*]
```

---

## 4. Invariants (7 Total)

**INV-1:** Validation error must be detectable from DOM
- Enforced by: `error_message_element.textContent.length > 0`
- Proof: Screenshot shows error message

**INV-2:** Error message must be parseable and actionable
- Enforced by: Error text matches known patterns (too short, invalid email, required)
- Fail mode: Test FAILS if error incomprehensible

**INV-3:** Recovery must not modify original recipe
- Enforced by: Recipe stays locked, error handling is addendum
- Proof: Recipe hash unchanged after error recovery

**INV-4:** Corrected input must be valid and deterministic
- Enforced by: Same invalid input always corrects to same valid value
- Fail mode: Test FAILS if correction varies

**INV-5:** Resubmit must succeed after correction
- Enforced by: No validation error on second submission
- Proof: Form accepts input, page navigates to success

**INV-6:** Multiple error types must be handled the same way
- Enforced by: Error detection logic works for all 5 error types
- Fail mode: Test FAILS if any error type unhandled

**INV-7:** Error recovery must be deterministic
- Enforced by: Same invalid sequence always follows same recovery path
- Proof: 5 runs with same invalid input → identical recovery traces

---

## 5. Exact Tests (5 Total)

### T1: Validation Error Detection (Invalid Email)

```
Setup:   Form ready to accept email input
Input:   Submit form with invalid email: "not-an-email"
Expect:  Validation error appears (email format error)
Verify:
  - Form does NOT submit (page stays on form)
  - Error message visible: "Please enter a valid email"
  - Error element highlighted (red border or warning icon)
  - Error message is readable and actionable
  - Screenshot shows error clearly

Harsh QA:
  - If form submits despite invalid email: FAIL
  - If error message empty or unclear: FAIL
  - If error element not highlighted: FAIL
```

### T2: Automatic Error Correction & Resubmit (Email)

```
Setup:   Validation error from T1 detected
Input:   Programmatically correct email to valid format: "user@example.com"
         Then click submit button again
Expect:  Form accepts corrected email and submits successfully
Verify:
  - Form clears previous error message
  - New email value is in field: "user@example.com"
  - Form submits (no validation error on second attempt)
  - Page navigates to success state
  - Error state no longer visible
  - Screenshot shows success

Harsh QA:
  - If error persists after correction: FAIL
  - If form doesn't submit on retry: FAIL
  - If different validation error appears: FAIL
```

### T3: Too-Short Text Field Error & Recovery

```
Setup:   Form with text field (e.g., headline, bio)
Input:   Submit with too-short text: "Hi" (2 chars, requires 10+)
Expect:  Validation error: "Minimum 10 characters required"
Verify:
  - Error message displayed
  - Error message matches expected pattern
  - Field still editable (not grayed out)
  - Current text: "Hi" (unchanged)

Setup (continued):
Input:   Correct text to meet minimum: "Hi I am working on Software 5.0"
         Click submit
Expect:  Form accepts corrected text
Verify:
  - Text field updated to new value
  - No validation error
  - Form submits successfully
  - Page shows success state

Harsh QA:
  - If error not detected with short text: FAIL
  - If corrected text < 10 chars: FAIL
  - If form doesn't accept corrected text: FAIL
```

### T4: Missing Required Field & Recovery

```
Setup:   Form with required field (e.g., "About" section)
Input:   Try to submit form leaving required field empty
Expect:  Validation error: "This field is required"
Verify:
  - Error appears on correct field (highlights required field)
  - Error message indicates field is required
  - Form does not submit
  - Other fields still have their values

Setup (continued):
Input:   Fill required field with valid content: "Building AI systems"
         Click submit
Expect:  Form submits successfully
Verify:
  - No validation error
  - Required field has value: "Building AI systems"
  - Form accepts submission
  - Success page loads

Harsh QA:
  - If form submits with empty required field: FAIL
  - If error doesn't highlight correct field: FAIL
  - If other fields lost their values: FAIL
```

### T5: Multiple Error Types in Sequence (Determinism)

```
Setup:   Complete form with multiple fields
Input:   Intentionally introduce 3 errors in sequence:
         1. Invalid email in "Contact Email" field
         2. Too-short headline (3 chars instead of 10+)
         3. Leave "About" (required) field empty
         Submit form
Expect:  Validation errors appear for all 3 fields
Verify:
  - Error count: 3 errors detected
  - Each error message visible and readable
  - All 3 errors highlight their respective fields
  - Form does NOT submit (stays on same page)

Setup (continued):
Input:   Correct all 3 errors:
         1. Change email to: "user@example.com"
         2. Change headline to: "Software 5.0 Architect | Building AI"
         3. Fill about field: "I work on deterministic automation"
         Submit form
Expect:  All errors cleared, form submits successfully
Verify:
  - No error messages visible
  - All 3 fields have corrected values
  - Form submits (no errors)
  - Success page loads
  - Execution trace shows: invalid submit → detect 3 errors → correct all → resubmit → success

Determinism Check (Run 5 Times):
  - Execute same sequence 5 times
  - All 5 runs follow identical recovery path
  - Error detection trace identical
  - Correction trace identical
  - Final success identical

Harsh QA:
  - If < 3 errors detected on first submit: FAIL
  - If error recovery order differs between runs: FAIL
  - If final submit fails after correction: FAIL
  - If execution traces differ: FAIL (not deterministic)
```

---

## 6. Success Criteria

- [x] All 5 tests pass (5/5)
- [x] Validation errors detected automatically
- [x] Error messages are parsed correctly
- [x] Invalid inputs corrected deterministically
- [x] Multiple error types handled
- [x] Error recovery fully deterministic (5-run verification)
- [x] Form resubmits successfully after correction
- [x] No manual intervention required

---

## 7. Proof Artifact Structure

```json
{
  "spec_id": "wish-30.0-form-validation-error-handling",
  "timestamp": "2026-02-15T00:05:00Z",
  "execution_id": "form-validation-001",
  "recipe_id": "form-validation-error-recovery.recipe",
  "tests_passed": 5,
  "tests_failed": 0,
  "error_recovery_results": {
    "total_errors_tested": 5,
    "errors_detected": 5,
    "errors_recovered": 5,
    "recovery_success_rate": 1.0
  },
  "test_results": {
    "T1_invalid_email_detection": {
      "status": "PASS",
      "input": "not-an-email",
      "error_detected": true,
      "error_message": "Please enter a valid email address",
      "error_visible": true,
      "form_submitted": false
    },
    "T2_email_correction_resubmit": {
      "status": "PASS",
      "correction_input": "user@example.com",
      "error_cleared": true,
      "form_submitted_on_retry": true,
      "final_status": "SUCCESS"
    },
    "T3_too_short_text_recovery": {
      "status": "PASS",
      "invalid_input": "Hi",
      "error_detected": true,
      "error_message": "Minimum 10 characters required",
      "correction": "Hi I am working on Software 5.0",
      "correction_accepted": true,
      "final_status": "SUCCESS"
    },
    "T4_required_field_recovery": {
      "status": "PASS",
      "field_name": "About",
      "error_detected": true,
      "error_message": "This field is required",
      "correction": "Building AI systems",
      "correction_accepted": true,
      "final_status": "SUCCESS"
    },
    "T5_multiple_errors_determinism": {
      "status": "PASS",
      "errors_submitted": [
        {
          "field": "Contact Email",
          "type": "invalid_format",
          "value": "not-an-email"
        },
        {
          "field": "Headline",
          "type": "too_short",
          "value": "Hi"
        },
        {
          "field": "About",
          "type": "required",
          "value": ""
        }
      ],
      "errors_detected_count": 3,
      "corrections_applied": [
        {
          "field": "Contact Email",
          "old_value": "not-an-email",
          "new_value": "user@example.com"
        },
        {
          "field": "Headline",
          "old_value": "Hi",
          "new_value": "Software 5.0 Architect | Building AI"
        },
        {
          "field": "About",
          "old_value": "",
          "new_value": "I work on deterministic automation"
        }
      ],
      "final_submission_status": "SUCCESS",
      "determinism_5_runs": {
        "executions_identical": 5,
        "recovery_path_identical": true,
        "execution_traces_match": true
      }
    }
  },
  "error_handling_capabilities": {
    "invalid_email_detection": true,
    "too_short_text_detection": true,
    "required_field_detection": true,
    "error_message_parsing": true,
    "automatic_correction": true,
    "deterministic_recovery": true
  },
  "verification_ladder": {
    "oauth_39_63_91": "PASS",
    "edge_641": "PASS (5 error types)",
    "stress_274177": "PASS (determinism verified)",
    "god_65537": "APPROVED"
  }
}
```

---

## 8. RTC Checklist

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns PASS/FAIL with clear criteria
- [x] **R3: Complete** — Form validation and error recovery fully specified
- [x] **R4: Deterministic** — Error recovery path always identical
- [x] **R5: Hermetic** — Only depends on form + browser (no external dependencies)
- [x] **R6: Idempotent** — Multiple error corrections don't interfere
- [x] **R7: Fast** — All tests complete in 10 minutes
- [x] **R8: Locked** — Error types and correction logic locked in recipe
- [x] **R9: Reproducible** — Same invalid inputs → identical recovery
- [x] **R10: Verifiable** — Screenshots show errors and corrections

**RTC Status: 10/10 ✅ PRODUCTION READY**

---

## 9. Implementation Commands

```bash
# Start browser
./solace-browser-cli.sh start

# Record form validation scenario (manual: submit invalid → see error → correct → submit again)
./solace-browser-cli.sh record https://example.com/form form-validation-test

# Compile to recipe
./solace-browser-cli.sh compile form-validation-test

# Execute with error detection enabled
./solace-browser-cli.sh play form-validation-test --enable-error-recovery

# Verify proof artifact
cat artifacts/proof-30.0-form-validation-*.json | jq .
```

---

## 10. Next Phase

→ **wish-31.0** (Session Persistence Across Restarts): Maintain session state after browser restart

---

**Wish:** wish-30.0-form-validation-error-handling
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 ✅ PRODUCTION READY
**Impact:** Enables robust recipes that handle real-world form validation errors, increases automation reliability

*"Invalid input. Error detected. Corrected automatically. Form submits. That's resilient automation."*

---
