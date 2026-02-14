# WISH 1.0: Build Infrastructure Setup & Verification

**Spec ID:** wish-1.0-build-infrastructure
**Authority:** 65537
**Phase:** 1 (Fork & Setup)
**Depends On:** none (foundation)
**Scope:** Verify build tools, scripts, and directory structure are correctly configured
**Non-Goals:** Downloading source code, compilation (Phase 1.1+)
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 400 | **GLOW:** 75

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Build infrastructure is ready (tools exist, scripts present, dirs structured)
  Verification:    `gn --version` and `ninja --version` both work
  Canonicalization: Directory structure matches expected Chromium layout
  Content-addressing: Script hashes stored, build logs preserved
```

---

## 1. Observable Wish

> "I can verify that all build infrastructure (gn, ninja, build script, directories) is correctly configured and ready for Chromium source setup."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Downloading Chromium source (separate: wish-1.0b)
- ❌ Compiling browser (Phase 1.1)
- ❌ Running browser (Phase 1.2)

**Minimum success criteria:**
- ✅ `gn --version` outputs version string
- ✅ `ninja --version` outputs version string
- ✅ `build_solace.sh` script exists and is executable
- ✅ Directory structure correct: `source_full/`, `out/`, `artifacts/`
- ✅ Project configuration: `.gn` files, `BUILDCONFIG.gn` present

---

## 3. Context Capsule (Test-Only)

```
Initial:   Ungoogled Chromium fork on disk
Behavior:  Run tests T1-T5, verify all tools present
Final:     Build ready for source fetch (wish-1.0b)
```

---

## 4. State Space: 5 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> CHECKING_TOOLS: start()
    CHECKING_TOOLS --> VERIFYING_STRUCTURE: tools found
    VERIFYING_STRUCTURE --> VALIDATING_CONFIG: dirs OK
    VALIDATING_CONFIG --> SUCCESS: config valid
    CHECKING_TOOLS --> ERROR: tools missing
    VERIFYING_STRUCTURE --> ERROR: dirs missing
    VALIDATING_CONFIG --> ERROR: config missing
    ERROR --> [*]
    SUCCESS --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** `gn` binary exists at /usr/bin/gn and is executable
**INV-2:** `ninja` binary exists at /usr/bin/ninja and is executable
**INV-3:** `build_solace.sh` exists in project root
**INV-4:** `source_full/` directory structure present
**INV-5:** Project directories: `out/`, `artifacts/`, `canon/` all exist

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: GN Tool Available
```
Setup:   System PATH includes /usr/bin
Input:   which gn
Expect:  /usr/bin/gn
Verify:  gn --version returns version ≥ 1.0
```

### T2: Ninja Tool Available
```
Setup:   System PATH includes /usr/bin
Input:   which ninja
Expect:  /usr/bin/ninja
Verify:  ninja --version returns version ≥ 1.x
```

### T3: Build Script Exists & Executable
```
Setup:   Current directory = project root
Input:   ls -la build_solace.sh
Expect:  File exists with -rwxr-xr-x permissions
Verify:  File is readable, executable, contains valid bash shebang
```

### T4: Directory Structure Correct
```
Setup:   Current directory = project root
Input:   find . -maxdepth 1 -type d -name 'source_full' -o -name 'out' -o -name 'artifacts'
Expect:  All three directories exist
Verify:  Each directory has appropriate permissions (755/775)
```

### T5: Project Configuration Present
```
Setup:   Current directory = project root
Input:   ls -la *.md, canon/, scripts/
Expect:  README.md exists, canon/ has content, scripts/ present
Verify:  Key files readable (not corrupted)
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** gn not installed → INV-1 fails → T1 fails
**F2:** ninja not installed → INV-2 fails → T2 fails
**F3:** build_solace.sh deleted → INV-3 fails → T3 fails
**F4:** source_full/ not created → INV-4 fails → T4 fails
**F5:** Directory permissions wrong → T4 verify fails

---

## 8. Visual Evidence (Proof Artifacts)

**proof.json structure:**
```json
{
  "spec_id": "wish-1.0-build-infrastructure",
  "timestamp": "2026-02-14T16:10:00Z",
  "authority": "65537",
  "tests": [
    {
      "test_id": "T1",
      "name": "GN Tool Available",
      "status": "PASS",
      "evidence": {
        "gn_path": "/usr/bin/gn",
        "gn_version": "1.4.1",
        "invocation": "gn --version"
      }
    }
  ],
  "invariants": [
    {
      "inv_id": "INV-1",
      "status": "PASS",
      "verified": true
    }
  ],
  "summary": {
    "passed": 5,
    "failed": 0,
    "status": "SUCCESS"
  }
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — No ambiguous assertions; all states mapped
- [x] **R4: Deterministic** — No network calls, no randomness
- [x] **R5: Hermetic** — Only checks system state, doesn't modify
- [x] **R6: Idempotent** — Tests can run multiple times safely
- [x] **R7: Fast** — All tests complete in <5 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same inputs → Same outputs always
- [x] **R10: Verifiable** — Artifacts prove success (proof.json, logs)

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] proof.json generated with full evidence
- [ ] Script output logged to artifacts/
- [ ] No system modifications (read-only testing)
- [ ] Repeatable: Can re-run and get same results

---

## 11. Next Phase

→ **wish-1.0b** (Source Fetch): Download Chromium source via gclient
→ **wish-1.1** (Compilation): Compile Chromium to browser binary

---

**Wish:** wish-1.0-build-infrastructure
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-1.0b, establishes foundation for Phase 1

*"Verify infrastructure before building on it."*
