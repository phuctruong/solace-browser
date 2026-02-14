# WISH 21.0: LinkedIn Profile Automation (Real Browser Testing)

**Spec ID:** wish-21.0-linkedin-automation-real
**Authority:** 65537
**Phase:** 21 (Real-World Browser Automation)
**Depends On:** wish-20.0 (integration testing complete)
**Scope:** Automate LinkedIn profile updates using real browser control via CDP
**Non-Goals:** API-based LinkedIn integration, bot detection evasion beyond browser realism
**Status:** 🎮 ACTIVE (Ready for Harsh QA)
**XP:** 2000 | **GLOW:** 150+ | **DIFFICULTY:** PRODUCTION-GRADE

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    LinkedIn profile automation is reproducible via real browser
  Verification:    Profile changes verifiable via screenshot comparison
  Canonicalization: Episode stored as deterministic recipe (locked)
  Content-addressing: Recipe ID = SHA256(linkedin_actions_sequence)
```

---

## 1. Observable Wish

> "I can automate LinkedIn profile updates using real browser control (CDP), record the interaction as a deterministic episode, and replay it infinitely with proof artifacts showing all changes."

---

## 2. Scope Exclusions & Harsh QA Rules

**NOT included:**
- ❌ Defeating LinkedIn bot detection (scope for wish-22.0)
- ❌ Multi-account automation (single profile only)
- ❌ Campaign analytics/reporting (that's later)

**Harsh QA Rules (NON-NEGOTIABLE):**
- ✅ Browser MUST actually pop open (not mock)
- ✅ User MUST see real LinkedIn.com load in browser
- ✅ Profile MUST change in real LinkedIn (verifiable)
- ✅ Screenshots MUST show real changes
- ✅ NO Mocking: If browser unavailable, test FAILS
- ✅ All proofs must show REAL execution timestamps

---

## 3. Context Capsule (Test-Only)

```
Initial:   Compiled Solace Browser available, accessible via CDP
Behavior:  Start browser → Navigate LinkedIn → Login → Update profile → Save
Final:     Profile updated, screenshots prove changes, deterministic recipe created
```

---

## 4. State Space: 7 States (Real Browser Control)

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> BROWSER_STARTING: start_browser()
    BROWSER_STARTING --> CDP_CONNECTED: detect_browser_via_cdp()
    CDP_CONNECTED --> RECORDING: navigate_to_linkedin()
    RECORDING --> NAVIGATING: click_edit_profile()
    NAVIGATING --> UPDATING: fill_headline_text()
    UPDATING --> SAVING: click_save_button()
    SAVING --> VERIFYING: screenshot_proof()
    VERIFYING --> LOCKED_RECIPE: compile_episode_to_recipe()
    LOCKED_RECIPE --> COMPLETE: generate_proof_artifacts()
    BROWSER_STARTING --> ERROR: cdp_connection_failed
    ERROR --> [*]
    COMPLETE --> [*]
```

---

## 5. Invariants (6 Total - LOCKED FOR PRODUCTION)

**INV-1:** Browser process MUST be running and accessible via CDP
- Enforced by: `curl -s http://localhost:9222/json` returns 200
- Fail mode: Test FAILS (no mock fallback)

**INV-2:** LinkedIn.com MUST actually load in real browser
- Enforced by: Page snapshot contains LinkedIn DOM
- Proof: Screenshot shows linkedin.com in address bar

**INV-3:** Profile changes MUST be visible in before/after screenshots
- Enforced by: Pixel comparison shows headline field changed
- Proof: Visual regression test passes

**INV-4:** Recipe MUST be locked and immutable after compilation
- Enforced by: `"locked": true` in recipe JSON
- Fail mode: Recipe cannot be modified

**INV-5:** All timestamps must be deterministic
- Enforced by: No random UUIDs or millisecond variance
- Proof: Same recipe executed twice has identical screenshots

**INV-6:** No mocking allowed in any test
- Enforced by: Tests abort if browser not available
- Fail mode: HARSH FAILURE (no graceful degradation)

---

## 6. Exact Tests (HARSH QA - Setup/Input/Expect/Verify)

### T1: Browser Launch & CDP Connection
```
Setup:   Solace Browser compiled and available
Input:   Start browser with remote-debugging-port=9222
Expect:  Process spawned, CDP port responds to /json
Verify:
  - Process ID exists (ps aux | grep chrome)
  - curl http://localhost:9222/json returns browser info
  - Browser window visible on screen (harsh check)
  - Status: Browser info contains "Chrome" or "Chromium"
Harsh QA:
  - If browser doesn't start → TEST FAILS (no mock)
  - If CDP unresponsive → TEST FAILS immediately
  - 30-second timeout max (abort if slower)
```

### T2: Navigate to LinkedIn.com
```
Setup:   Browser running, CDP connected
Input:   Send CDP navigate command to https://linkedin.com
Expect:  Page loads, DOM becomes accessible
Verify:
  - Page title contains "LinkedIn"
  - Snapshot shows linkedin.com in URL
  - DOM contains LinkedIn logo element
  - Page load time < 15 seconds
Harsh QA:
  - Screenshot must show REAL LinkedIn site (not error page)
  - Network requests logged (verify real HTTP calls)
  - If LinkedIn returns 403/429 → TEST FAILS (we're blocked)
```

### T3: User Login Authentication
```
Setup:   LinkedIn page loaded
Input:   Enter email and password via CDP keyboard events
Expect:  2FA challenge appears (or login success)
Verify:
  - POST request sent to LinkedIn login endpoint
  - Session cookie captured
  - Page navigates to profile or 2FA screen
Harsh QA:
  - Credentials MUST come from environment or .env
  - NO hardcoded passwords in test
  - If 2FA required → test records code entry point (manual step)
  - If login fails → comprehensive error log with LinkedIn response
```

### T4: Navigate to Edit Profile
```
Setup:   User logged into LinkedIn
Input:   Click "Edit" button on profile
Expect:  Edit profile form opens
Verify:
  - Form contains headline, about, project fields
  - All fields are editable (not grayed out)
  - Page title shows "Edit Profile"
Harsh QA:
  - Screenshot shows edit form (visual verification)
  - No JavaScript errors in console
  - All expected fields present and interactive
```

### T5: Update Profile Content
```
Setup:   Edit profile form open and ready
Input:   Fill headline, about section, add projects
        Headline: "Software 5.0 Architect | 65537 Authority | Building Verified AI OS in Public"
        About: [200-300 word text from linkedin-suggestions.md]
        Projects: STILLWATER, SOLACEAGI, PZIP, PHUCNET, IF
Expect:  All fields filled without errors
Verify:
  - Headline field shows new text (visual check)
  - About section contains all 300 words (text verification)
  - 5 projects listed with links
  - Form does NOT show validation errors
Harsh QA:
  - Character count validation (about must be 200-300 chars)
  - All project links MUST be valid URLs
  - No broken formatting (test for HTML injection)
  - Screenshot shows filled form before save
```

### T6: Save Profile & Verify
```
Setup:   All profile fields filled correctly
Input:   Click "Save Changes" button
Expect:  Page confirms save, profile page refreshes
Verify:
  - Success message appears ("Profile updated")
  - Page navigates back to profile view
  - Profile shows NEW headline (not old one)
  - All changes persist (reload page, verify again)
Harsh QA:
  - Before/after screenshot comparison (headline changed)
  - Pixel diff shows text changed in DOM
  - Verify profile is publicly accessible (LinkedIn API check)
  - Check that changes visible in different browser (proves real save)
```

### T7: Episode Recording & Compilation
```
Setup:   All LinkedIn actions completed successfully
Input:   Compile recorded episode to locked recipe
Expect:  Recipe file created with "locked": true
Verify:
  - Recipe JSON valid and contains all 6 actions
  - Recipe hash matches episode hash
  - Recipe file immutable (chmod 444)
  - Proof artifact generated with execution trace
Harsh QA:
  - File permissions verify recipe is locked (not writable)
  - Hash verification ensures no tampering
  - Execution trace shows exact CDP timestamps
```

### T8: Determinism Test (Replay)
```
Setup:   Locked recipe ready, profile reset to original state
Input:   Play recipe 2 times sequentially on same browser
Expect:  Both executions make identical changes
Verify:
  - Screenshot 1 == Screenshot 2 (pixel-perfect)
  - Both proof.json files have identical SHA256
  - Profile shows SAME headline in both runs
  - Same exact timeline of operations
Harsh QA:
  - Determinism rate MUST be 100% (no variance allowed)
  - Any pixel diff → TEST FAILS
  - Hash comparison is byte-level (not approximate)
```

---

## 7. Forecasted Failures (Harsh Mode)

**F1: Browser Not Compiled** (Probability: 60%)
- **Symptom:** solace-browser binary not found
- **Impact:** ALL TESTS FAIL immediately (no mock mode)
- **Mitigation:** Wish depends on wish-1.0 (Chromium compilation) being complete
- **Recovery:** User must compile Solace Browser first

**F2: LinkedIn Account Blocking** (Probability: 25%)
- **Symptom:** HTTP 429 (too many requests) or 403 (forbidden)
- **Impact:** T3-T6 tests fail due to rate limiting
- **Mitigation:** Use high-quality Solace Browser binary (real Chromium, not flagged)
- **Recovery:** Wait 24 hours, test with different account

**F3: 2FA Required** (Probability: 40%)
- **Symptom:** LinkedIn requests 2FA code
- **Impact:** T3 test requires manual code entry (not automated)
- **Mitigation:** Disable 2FA on test account OR implement code injection
- **Recovery:** Manual step or use accounts without 2FA

**F4: DOM Changes on LinkedIn** (Probability: 15%)
- **Symptom:** Edit button selector no longer works (LinkedIn updated UI)
- **Impact:** T4-T5 tests fail to find edit form
- **Mitigation:** Use semantic selectors (role, aria-label) not CSS classes
- **Recovery:** Update recipe with new selectors

**F5: Network Timeouts** (Probability: 20%)
- **Symptom:** LinkedIn takes >20 seconds to load, test timeout
- **Impact:** T2 test fails, page load incomplete
- **Mitigation:** Increase timeout, verify network quality
- **Recovery:** Run test again, or test during off-peak hours

---

## 8. Visual Evidence (Proof Artifacts)

**proof-21.0.json structure:**
```json
{
  "proof_id": "proof-linkedin-automation-2026-02-14-001",
  "timestamp": "2026-02-14T23:30:45Z",
  "episode_id": "linkedin-profile-update",
  "recipe_id": "linkedin-profile-update.recipe",
  "control_mode": "REAL_BROWSER_CDP",
  "tests_passed": 8,
  "tests_failed": 0,
  "execution_timeline": {
    "browser_launch_time": "2026-02-14T23:20:00Z",
    "cdp_connection_time": "2026-02-14T23:20:03Z",
    "linkedin_load_time": "2026-02-14T23:20:15Z",
    "profile_update_time": "2026-02-14T23:25:30Z",
    "profile_save_time": "2026-02-14T23:26:00Z",
    "total_duration_seconds": 600
  },
  "test_results": {
    "T1_browser_launch": "PASS",
    "T2_navigate_linkedin": "PASS",
    "T3_login": "PASS",
    "T4_edit_profile": "PASS",
    "T5_update_content": "PASS",
    "T6_save_profile": "PASS",
    "T7_compilation": "PASS",
    "T8_determinism": "PASS"
  },
  "screenshots": {
    "before_edit": "screenshot-before-edit.png",
    "form_filled": "screenshot-form-filled.png",
    "after_save": "screenshot-after-save.png",
    "proof_of_change": "screenshot-headline-changed.png"
  },
  "verification": {
    "profile_changes_visible": true,
    "screenshots_taken": 4,
    "determinism_verified": true,
    "recipe_locked": true,
    "all_tests_real_browser": true,
    "no_mocking": true
  },
  "linkedin_changes": {
    "headline": {
      "before": "[Original headline]",
      "after": "Software 5.0 Architect | 65537 Authority | Building Verified AI OS in Public",
      "verified": true
    },
    "about_section": {
      "before_length": 150,
      "after_length": 287,
      "verified": true,
      "contains_software_5_0": true
    },
    "projects_added": 5,
    "projects_list": ["STILLWATER", "SOLACEAGI", "PZIP", "PHUCNET", "IF"]
  },
  "harsh_qa_results": {
    "browser_process_alive": true,
    "cdp_responsive": true,
    "linkedin_real_not_mock": true,
    "no_timeouts": true,
    "no_rate_limiting": true,
    "network_calls_real": 127,
    "determinism_score": 1.0
  }
}
```

---

## 9. RTC Checklist (Ready To Compile - PRODUCTION GRADE)

- [x] **R1: Readable** — All 8 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL) in harsh mode
- [x] **R3: Complete** — LinkedIn automation pipeline fully specified
- [x] **R4: Deterministic** — Same recipe produces identical profile changes
- [x] **R5: Hermetic** — Only depends on compiled Solace Browser + LinkedIn
- [x] **R6: Idempotent** — Profile updates don't interfere with each other
- [x] **R7: Fast** — All tests complete in <15 minutes
- [x] **R8: Locked** — Setup/Expect/Verify phrases word-for-word, no deviation
- [x] **R9: Reproducible** — Same episode → same LinkedIn profile changes
- [x] **R10: Verifiable** — Screenshots + proofs prove all changes

**RTC Status: 10/10 ✅ PRODUCTION READY (HARSH QA MODE)**

---

## 10. Success Criteria (UNCOMPROMISING)

- [ ] All 8 tests pass (8/8) with REAL BROWSER
- [ ] Browser actually pops open (not mocked)
- [ ] LinkedIn.com loads in real browser
- [ ] Profile headline visibly changes
- [ ] Profile about section updates with full 300-word text
- [ ] 5 projects added with valid links
- [ ] Screenshots prove all changes
- [ ] Recipe locked and immutable
- [ ] Replay is 100% deterministic
- [ ] Zero mocking, zero fallbacks

---

## 11. Implementation: Using solace-browser-cli.sh v2.0

```bash
# Step 1: Start browser (pops open)
./solace-browser-cli.sh start

# Step 2: Record LinkedIn update episode
./solace-browser-cli.sh record https://linkedin.com linkedin-update

# Step 3: Manual interactions (in browser window)
# - Navigate to linkedin.com/me
# - Click "Edit profile"
# - Update headline, about, projects
# - Click "Save"

# Step 4: Compile to recipe
./solace-browser-cli.sh compile linkedin-update

# Step 5: Execute recipe (deterministic replay)
./solace-browser-cli.sh play linkedin-update

# Step 6: Verify proof artifacts
cat artifacts/proof-linkedin-update-*.json | jq .
```

---

## 12. Harsh QA Report Template

```
HARSH QA REPORT - WISH 21.0
Generated: $(date)

BROWSER CONTROL:
  ✓ Solace Browser started: YES
  ✓ CDP port responsive: 9222
  ✓ Browser version: Chromium 120.0.6099.129

LINKEDIN AUTOMATION:
  ✓ LinkedIn.com loaded: YES (real site, not mock)
  ✓ User authenticated: YES
  ✓ Edit profile opened: YES
  ✓ Profile changes visible: YES
  ✓ Changes saved: YES

SCREENSHOT VERIFICATION:
  ✓ Before/after comparison: DIFFERENT (title changed)
  ✓ Pixel diff > 5%: YES (confirms real change)
  ✓ Text comparison: MATCH (headline updated)

DETERMINISM VERIFICATION:
  ✓ Replay 1 screenshot hash: abc123def456
  ✓ Replay 2 screenshot hash: abc123def456
  ✓ DETERMINISM: 100% VERIFIED

HARSH PENALTIES:
  ✗ Any mock mode usage: -1000 points
  ✗ No browser popup: -500 points
  ✗ LinkedIn not real: -500 points
  ✗ Mocking allowed: DISQUALIFIED

FINAL SCORE: 10/10 (PRODUCTION READY)
```

---

## 13. Next Phase

→ **wish-22.0** (LinkedIn Campaign Automation): Execute 3-month content calendar with batch posting

---

**Wish:** wish-21.0-linkedin-automation-real
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 ✅ HARSH QA READY
**Impact:** Proves Solace Browser real-world capability, unblocks content automation

*"Real browser, real automation, real profile changes. No mocks. No excuses. Just determinism at scale."*

---

**CRITICAL CONSTRAINT:** This wish will ONLY PASS if browser is actually compiled and accessible via CDP. There is NO mock fallback. If Solace Browser is not compiled, this wish will FAIL all 8 tests. This is by design - we test reality, not fantasies.
