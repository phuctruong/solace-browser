# WISH 14.0: Form Filling & Submission

**Spec ID:** wish-14.0-form-filling
**Authority:** 65537
**Phase:** 14 (Form Automation)
**Depends On:** wish-13.0 (element visibility complete)
**Scope:** Fill multi-field forms, validate inputs, submit safely
**Non-Goals:** File uploads, CAPTCHA solving, password managers
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 1050 | **GLOW:** 110+

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Form submission is deterministically reproducible
  Verification:    Each field filled and submitted identically
  Canonicalization: Form data stored as canonical JSON
  Content-addressing: Form ID = SHA256(form_fields + values_hash)
```

---

## 1. Observable Wish

> "I can fill multi-field forms with typed data, select dropdown options, handle checkboxes/radio buttons, validate input, and submit forms deterministically."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ File uploads
- ❌ CAPTCHA solving
- ❌ Password manager integration
- ❌ Multi-step form wizards (Phase 15+)

**Minimum success criteria:**
- ✅ Fill text inputs (name, email, etc.)
- ✅ Select dropdown options
- ✅ Check/uncheck checkboxes
- ✅ Select radio buttons
- ✅ Validate form before submission
- ✅ Submit form successfully

---

## 3. Context Capsule (Test-Only)

```
Initial:   Visibility detection active (wish-13.0)
Behavior:  Fill form fields, validate, submit
Final:     Form automation complete, safe submissions guaranteed
```

---

## 4. State Space: 5 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> DETECTING_FORM: form_found
    DETECTING_FORM --> FILLING: fill_form()
    FILLING --> VALIDATING: all_fields_filled
    VALIDATING --> SUBMITTING: validation_passed
    SUBMITTING --> COMPLETE: form_submitted
    VALIDATING --> ERROR: validation_failed
    SUBMITTING --> ERROR: submission_failed
    ERROR --> [*]
    COMPLETE --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** All form fields detected and filled correctly
**INV-2:** Field values match input data (no truncation/corruption)
**INV-3:** Validation passes before submission
**INV-4:** Form submission successful (200/201 response)
**INV-5:** Form data deterministically reproducible

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Form Detection
```
Setup:   Page with form element loaded
Input:   Scan DOM for form elements
Expect:  Form detected with 5+ fields identified
Verify:  Form has name, email, message, checkbox, select fields
```

### T2: Text Input Filling
```
Setup:   Form detected, text fields identified
Input:   Fill text inputs with data
Expect:  All text fields filled without errors
Verify:  Field values match input data exactly
```

### T3: Select & Checkbox Handling
```
Setup:   Text fields filled
Input:   Select dropdown option, check checkbox
Expect:  Dropdown selected, checkbox marked
Verify:  Select shows correct value, checkbox state verified
```

### T4: Form Validation
```
Setup:   All fields filled
Input:   Validate form before submission
Expect:  Validation checks pass (no empty required fields)
Verify:  Validation report shows 0 errors
```

### T5: Form Submission
```
Setup:   Form validated successfully
Input:   Submit form via button click or enter key
Expect:  Form submitted, success response received
Verify:  Submission confirmed, response status 200+
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Form not found → T1 fails, no form detected
**F2:** Text input fails → T2 fails, values not entered
**F3:** Select/checkbox fails → T3 fails, options not selected
**F4:** Validation fails → T4 fails, required fields empty
**F5:** Submission fails → T5 fails, form not submitted

---

## 8. Visual Evidence (Proof Artifacts)

**form-detection.json structure:**
```json
{
  "form_id": "form-20260214-001",
  "timestamp": "2026-02-14T18:00:00Z",
  "form_selector": "form#contact-form",
  "form_name": "contact_form",
  "form_method": "POST",
  "form_action": "/submit",
  "fields": [
    {
      "field_id": "f-001",
      "name": "name",
      "type": "text",
      "required": true,
      "visible": true
    }
  ],
  "total_fields": 5,
  "submittable": true
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Form automation pipeline fully specified
- [x] **R4: Deterministic** — Form filling reproducible
- [x] **R5: Hermetic** — No external form services
- [x] **R6: Idempotent** — Form filling doesn't modify page state permanently
- [x] **R7: Fast** — All tests complete in <15 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases word-for-word
- [x] **R9: Reproducible** — Same form → same filling behavior
- [x] **R10: Verifiable** — Form submission reports prove all steps

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Form detection accurate
- [ ] Text inputs filled correctly
- [ ] Select/checkbox handling works
- [ ] Validation successful
- [ ] Form submission verified

---

## 11. Next Phase

→ **wish-15.0** (Multi-Tab Navigation): Handle complex workflows across tabs

---

**Wish:** wish-14.0-form-filling
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-15.0, enables form-based automation

*"Fill the form. Submit with confidence."*
