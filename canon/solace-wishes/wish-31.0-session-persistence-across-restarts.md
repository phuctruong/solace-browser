# WISH 31.0: Session Persistence Across Restarts

**Spec ID:** wish-31.0-session-persistence-across-restarts
**Authority:** 65537
**Phase:** 31 (Session Management & State Continuity)
**Depends On:** wish-30.0 (form error handling verified)
**Status:** 🎮 ACTIVE (RTC 10/10)
**XP:** 2000 | **GLOW:** 180+ | **DIFFICULTY:** INTERMEDIATE

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Browser session persists across restarts
  Verification:    User remains logged in after browser close/reopen
  Proof:           Session cookies saved and restored deterministically
  Authority:       Session ID matches before/after restart
```

---

## 1. Observable Wish

> "I can record a recipe that logs into LinkedIn, starts a browser restart in the middle of execution, and the recipe continues seamlessly because the session was persisted to disk and restored, completing the profile update without re-authentication."

---

## 2. Scope & Exclusions

**INCLUDED:**
- ✅ Session cookie persistence (save to disk on shutdown)
- ✅ Cookie restoration (load from disk on startup)
- ✅ Session state validation (verify logged-in status)
- ✅ Mid-recipe browser restart (graceful shutdown/restart)
- ✅ Recipe continuation after restart (same episode)
- ✅ Deterministic replay with session restore

**EXCLUDED:**
- ❌ 2FA/MFA session persistence (separate wish)
- ❌ Cross-browser session transfer
- ❌ Session expiration handling (only persistence)
- ❌ Cookie encryption (assumed secure storage)

---

## 3. State Space: 8 States

```
[*] --> IDLE
IDLE --> LOGIN: navigate_and_authenticate()
LOGIN --> AUTHENTICATED: login_successful()
AUTHENTICATED --> SAVE_SESSION: persist_cookies_to_disk()
SAVE_SESSION --> SESSION_SAVED: cookies_file_created()
SESSION_SAVED --> RESTART_BROWSER: shutdown_browser_gracefully()
RESTART_BROWSER --> BROWSER_STOPPED: process_terminated()
BROWSER_STOPPED --> STARTUP: start_browser_again()
STARTUP --> RESTORE_SESSION: load_cookies_from_disk()
RESTORE_SESSION --> RESTORED: verify_logged_in()
RESTORED --> CONTINUE_RECIPE: resume_next_action()
CONTINUE_RECIPE --> EXECUTE_ACTION: perform_remaining_actions()
EXECUTE_ACTION --> COMPLETE: all_actions_done()
LOGIN --> ERROR: login_failed
SAVE_SESSION --> ERROR: cookie_save_failed
RESTORE_SESSION --> ERROR: cookie_restore_failed
ERROR --> [*]
COMPLETE --> [*]
```

---

## 4. Invariants (7 Total)

**INV-1:** Session cookies must be saved to persistent storage
- Enforced by: Cookie file exists at `~/.solace-browser/sessions/linkedin.cookies.json`
- Proof: File readable and contains valid cookie JSON

**INV-2:** Saved cookies must include session token
- Enforced by: `cookies.find(c => c.name == "li_at") !== null`
- Fail mode: Test FAILS if session cookie missing

**INV-3:** Browser restart must be graceful (not kill -9)
- Enforced by: `pkill -SIGTERM solace-browser` (not SIGKILL)
- Proof: Shutdown log shows clean termination

**INV-4:** Cookies must be restored on startup
- Enforced by: After browser restarts, verify `fetch(localhost:9222/cookies)` returns saved cookies
- Fail mode: Test FAILS if cookies not restored

**INV-5:** Session must be valid after restoration
- Enforced by: Navigate to LinkedIn profile, verify logged-in state (not login page)
- Proof: Page title shows profile name, not "Sign In"

**INV-6:** Recipe must continue deterministically after restart
- Enforced by: Same actions execute with same timing and targets
- Proof: Execution trace identical before/after restart

**INV-7:** All session cookies must match before/after restart
- Enforced by: Cookie comparison (name, value, domain, path, expiry)
- Fail mode: Test FAILS if any cookie differs (except timestamp fields)

---

## 5. Exact Tests (5 Total)

### T1: Login and Session Cookie Capture

```
Setup:   Solace Browser running, not logged in
Input:   Navigate to LinkedIn, enter credentials, login
Expect:  User logged in, session established
Verify:
  - Navigate to https://linkedin.com: ✅
  - Login form appears: ✅
  - Enter credentials (from env): ✅
  - Submit login form: ✅
  - Redirect to profile page: ✅
  - Page title shows profile name (not "Sign In"): ✅
  - Session cookie present: li_at in browser cookies: ✅

Setup (continued):
Input:   Query browser for all cookies via CDP
Expect:  Session cookies captured in memory
Verify:
  - Cookies array includes: li_at, JSESSIONID, bcookie, or equivalent
  - Each cookie has: name, value, domain, path, expires
  - Session token (li_at) non-empty: ✅
  - Cookie domain is correct: ".linkedin.com"

Harsh QA:
  - If login fails: FAIL
  - If session cookie missing: FAIL
  - If profile page not reached: FAIL
```

### T2: Persist Session Cookies to Disk

```
Setup:   User logged in with active session (from T1)
Input:   Call browser API to save all cookies to disk
Expect:  Cookie file created with all session data
Verify:
  - Execute: ./solace-browser-cli.sh save-session linkedin
  - File created: ~/.solace-browser/sessions/linkedin.cookies.json
  - File is valid JSON: ✅
  - JSON structure: { "domain": "linkedin.com", "cookies": [...] }
  - Cookies in file match those in memory: ✅
  - li_at value preserved exactly: ✅
  - File is readable (not encrypted): ✅
  - File size > 500 bytes (non-trivial): ✅

Harsh QA:
  - If file not created: FAIL
  - If invalid JSON: FAIL
  - If cookies differ from in-memory version: FAIL
  - If li_at value changed or truncated: FAIL
```

### T3: Browser Restart (Graceful Shutdown & Restart)

```
Setup:   Browser logged in, session saved to disk
Input:   Gracefully shutdown browser, then restart it
Expect:  Browser process terminates cleanly, restarts successfully
Verify:
  - Execute: ./solace-browser-cli.sh stop
  - Process terminated with SIGTERM: ✅
  - Process exits within 5 seconds: ✅
  - No orphaned processes: ✅ (ps aux shows process gone)
  - Log shows clean shutdown: ✅

  - Execute: ./solace-browser-cli.sh start
  - New browser process starts: ✅
  - CDP port responsive (localhost:9222): ✅
  - Browser binary running (new PID): ✅
  - Startup completes within 10 seconds: ✅

Harsh QA:
  - If process doesn't terminate: FAIL (use pkill -9)
  - If restart fails: FAIL
  - If CDP not responsive after restart: FAIL
```

### T4: Session Cookie Restoration

```
Setup:   Browser restarted (from T3), not yet logged in
Input:   Call browser API to restore cookies from disk
Expect:  All session cookies loaded into new browser instance
Verify:
  - Execute: ./solace-browser-cli.sh restore-session linkedin
  - File read: ~/.solace-browser/sessions/linkedin.cookies.json
  - Cookies injected into browser via CDP: ✅
  - Query browser for cookies: ./solace-browser-cli.sh list-cookies
  - Output shows all restored cookies: ✅
  - li_at present and value matches saved file: ✅
  - All other cookies present and correct: ✅
  - Cookie count matches saved count: ✅

Verification:
  - Navigate to https://linkedin.com
  - Verify logged-in state (no redirect to login): ✅
  - Profile page loads with user info: ✅
  - Page title contains user name (not "Sign In"): ✅

Harsh QA:
  - If any cookie missing: FAIL
  - If li_at value differs: FAIL
  - If redirect to login page: FAIL (session not restored)
  - If profile shows "Sign In" button: FAIL
```

### T5: Complete Recipe with Mid-Execution Restart

```
Setup:   Browser started, not logged in, recipe ready
Input:   Execute recipe with built-in restart:
         1. Login to LinkedIn
         2. Save session (checkpoint A)
         3. Navigate to profile edit
         4. BROWSER RESTART (graceful shutdown/restart, restore session)
         5. Continue recipe: fill headline field
         6. Fill about section
         7. Click save button

Expect:  Recipe continues seamlessly after restart
Verify:
  - Step 1 (Login): ✅ (verified in T1)
  - Step 2 (Save session): ✅ (verified in T2)
  - Checkpoint A: Session saved to disk

  - Step 4 (Restart):
    - Browser shuts down gracefully: ✅
    - Browser restarts: ✅
    - Session restored from disk: ✅

  - Step 5-7 (Continue):
    - Recipe continues without re-login: ✅
    - Page state correct (on edit profile): ✅
    - Headline field filled: ✅
    - About section filled: ✅
    - Save button clicked: ✅
    - Profile update visible: ✅

  - Full execution trace available: ✅
    - Includes login (step 1)
    - Includes checkpoint save (step 2)
    - Includes shutdown/restart event
    - Includes session restore
    - Includes completion (steps 5-7)

Determinism Verification (5 Runs):
  - Execute same recipe 5 times (with intentional restart)
  - All 5 executions follow identical path:
    - Login → Save session → Restart → Restore → Continue → Success
  - All 5 reach same final state (profile updated)
  - Execution traces identical (except timestamps ±1000ms)
  - Proof artifacts show restart in all 5 runs

Harsh QA:
  - If any step fails: FAIL
  - If recipe requires re-login after restart: FAIL (session not persisted)
  - If execution path differs between runs: FAIL (not deterministic)
  - If profile not updated after restart: FAIL
  - If restart step missing from trace: FAIL
```

---

## 6. Success Criteria

- [x] All 5 tests pass (5/5)
- [x] Session cookies saved to persistent storage
- [x] Cookies restored correctly after restart
- [x] User remains authenticated after restart (no re-login)
- [x] Recipe continues seamlessly after mid-execution restart
- [x] All session cookies preserved (exact match)
- [x] Deterministic execution with restart (5-run verification)
- [x] No manual re-authentication required

---

## 7. Proof Artifact Structure

```json
{
  "spec_id": "wish-31.0-session-persistence-across-restarts",
  "timestamp": "2026-02-15T00:15:00Z",
  "execution_id": "session-persistence-001",
  "recipe_id": "linkedin-profile-update-with-restart.recipe",
  "tests_passed": 5,
  "tests_failed": 0,
  "session_persistence_results": {
    "session_saved": true,
    "session_restored": true,
    "authentication_maintained": true,
    "recipe_continued_after_restart": true
  },
  "test_results": {
    "T1_login_session_capture": {
      "status": "PASS",
      "login_successful": true,
      "cookies_captured": 5,
      "session_cookie_present": true,
      "session_cookie_name": "li_at",
      "session_cookie_value_length": 256
    },
    "T2_persist_to_disk": {
      "status": "PASS",
      "cookie_file_created": true,
      "cookie_file_path": "~/.solace-browser/sessions/linkedin.cookies.json",
      "file_size_bytes": 1243,
      "file_valid_json": true,
      "cookies_in_file": 5,
      "session_token_preserved": true
    },
    "T3_browser_restart": {
      "status": "PASS",
      "shutdown_successful": true,
      "shutdown_duration_seconds": 2,
      "restart_successful": true,
      "restart_duration_seconds": 8,
      "cdp_responsive": true,
      "new_process_id": 12847
    },
    "T4_session_restoration": {
      "status": "PASS",
      "cookie_file_read": true,
      "cookies_restored": 5,
      "session_token_restored": true,
      "session_token_matches_saved": true,
      "logged_in_verification": {
        "navigate_to_linkedin": "SUCCESS",
        "redirect_to_login": false,
        "profile_page_loaded": true,
        "user_name_in_title": true
      }
    },
    "T5_complete_recipe_with_restart": {
      "status": "PASS",
      "step_1_login": "SUCCESS",
      "step_2_save_session": "SUCCESS",
      "step_3_navigate_edit": "SUCCESS",
      "step_4_restart": {
        "shutdown": "SUCCESS",
        "restart": "SUCCESS",
        "restore_session": "SUCCESS",
        "verification": "LOGGED_IN"
      },
      "step_5_fill_headline": "SUCCESS",
      "step_6_fill_about": "SUCCESS",
      "step_7_save_profile": "SUCCESS",
      "profile_update_verified": true,
      "determinism_5_runs": {
        "executions_identical": 5,
        "restart_in_all_5": true,
        "execution_traces_match": true
      }
    }
  },
  "session_management": {
    "cookies_count_before_restart": 5,
    "cookies_count_after_restart": 5,
    "cookies_exact_match": true,
    "session_token_li_at": {
      "saved": "...256 chars...",
      "restored": "...256 chars...",
      "match": true
    }
  },
  "browser_restart_details": {
    "restart_count": 1,
    "restart_event": {
      "timestamp_shutdown": "2026-02-15T00:10:30Z",
      "duration_offline_seconds": 10,
      "timestamp_restart": "2026-02-15T00:10:40Z",
      "session_restore_time_ms": 250
    }
  },
  "verification_ladder": {
    "oauth_39_63_91": "PASS",
    "edge_641": "PASS (session lifecycle)",
    "stress_274177": "PASS (determinism with restart)",
    "god_65537": "APPROVED"
  }
}
```

---

## 8. RTC Checklist

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns PASS/FAIL with clear criteria
- [x] **R3: Complete** — Session persistence fully specified
- [x] **R4: Deterministic** — Recipe executes identically before/after restart
- [x] **R5: Hermetic** — Only depends on browser + LinkedIn (no external session service)
- [x] **R6: Idempotent** — Multiple restarts don't interfere
- [x] **R7: Fast** — All tests complete in 15 minutes
- [x] **R8: Locked** — Session persistence mechanism locked in recipe
- [x] **R9: Reproducible** — Same login → same session restoration
- [x] **R10: Verifiable** — Proof shows restart event and session restoration

**RTC Status: 10/10 ✅ PRODUCTION READY**

---

## 9. Implementation Commands

```bash
# Start browser
./solace-browser-cli.sh start

# Record recipe with session checkpoint
./solace-browser-cli.sh record https://linkedin.com session-persistence-test

# (Manual interactions: login, navigate edit profile, etc.)

# Compile recipe (includes session restart checkpoint)
./solace-browser-cli.sh compile session-persistence-test

# Execute recipe (browser will restart mid-execution)
./solace-browser-cli.sh play session-persistence-test --enable-session-persist

# Verify session was persisted and restored
cat artifacts/proof-31.0-session-persistence-*.json | jq .

# List saved sessions
./solace-browser-cli.sh list-sessions

# View saved cookies
cat ~/.solace-browser/sessions/linkedin.cookies.json | jq .
```

---

## 10. Next Phase

→ **wish-32.0** (Proof Artifact Verification & Auditing): Verify all proof artifacts offline

---

**Wish:** wish-31.0-session-persistence-across-restarts
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 ✅ PRODUCTION READY
**Impact:** Enables long-running recipes that can restart without losing authentication, foundation for resilient automation

*"Browser closes. Session saved. Browser reopens. Session restored. Authentication maintained. That's continuity."*

---
