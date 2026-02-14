# WISH 1.0b: Chromium Source Fetch & Validation

**Spec ID:** wish-1.0b-chromium-source-fetch
**Authority:** 65537
**Phase:** 1 (Fork & Setup)
**Depends On:** wish-1.0 (build infrastructure verified)
**Scope:** Fetch Ungoogled Chromium source via gclient sync and verify download integrity
**Non-Goals:** Compilation (wish-1.1), patching (Phase 1.2+)
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 500 | **GLOW:** 78

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Chromium source exists at source_full/src with proper structure
  Verification:    .gn file present, buildfiles.gni readable, third_party/ populated
  Canonicalization: Directory tree matches Chromium canonical structure
  Content-addressing: Source manifest SHA256(buildfiles.gni) stored as proof
```

---

## 1. Observable Wish

> "I can fetch the complete Chromium source code into source_full/src, verify it's properly downloaded, and confirm the build system is ready for compilation."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Compiling the source (wish-1.1)
- ❌ Applying Ungoogled patches (Phase 1.2)
- ❌ Running unit tests
- ❌ Building any binaries

**Minimum success criteria:**
- ✅ `gclient sync` completes successfully
- ✅ `source_full/src/.gn` file exists
- ✅ `source_full/src/BUILDCONFIG.gn` exists
- ✅ `source_full/src/third_party/` directory populated
- ✅ `source_full/src/out/` directory ready for build outputs

---

## 3. Context Capsule (Test-Only)

```
Initial:   Build infrastructure verified (wish-1.0), source_full/.gclient configured
Behavior:  Run gclient sync, verify download integrity
Final:     Source_full/src ready for compilation (wish-1.1)
```

---

## 4. State Space: 5 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> CHECKING_GCLIENT: start()
    CHECKING_GCLIENT --> SYNCING_SOURCE: gclient found
    SYNCING_SOURCE --> VALIDATING_SOURCE: sync complete
    VALIDATING_SOURCE --> SUCCESS: structure valid
    CHECKING_GCLIENT --> ERROR: gclient missing
    SYNCING_SOURCE --> ERROR: sync failed
    VALIDATING_SOURCE --> ERROR: structure invalid
    ERROR --> [*]
    SUCCESS --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** `source_full/.gclient` file exists (created by earlier sync attempts)
**INV-2:** `source_full/src/` directory exists after sync
**INV-3:** `source_full/src/.gn` file exists (GN configuration)
**INV-4:** `source_full/src/BUILDCONFIG.gn` exists (build configuration)
**INV-5:** `source_full/src/third_party/` directory populated with at least 10 subdirs

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: GClient Available
```
Setup:   System PATH includes download tools
Input:   which gclient || which depot_tools
Expect:  gclient or depot_tools found in PATH
Verify:  gclient --version returns version string
```

### T2: Run GClient Sync
```
Setup:   Current directory = source_full, .gclient file exists
Input:   gclient sync --with_branch_heads --force
Expect:  Command completes (exit 0), sync logs saved
Verify:  Process completes within 1 hour (or respects --ignore-network)
```

### T3: Chromium Source Structure Valid
```
Setup:   gclient sync completed
Input:   ls -la source_full/src/.gn source_full/src/BUILDCONFIG.gn
Expect:  Both files exist and are readable
Verify:  File sizes > 100 bytes (not empty stubs)
```

### T4: Third-Party Dependencies Present
```
Setup:   Source structure validated
Input:   find source_full/src/third_party -maxdepth 1 -type d | wc -l
Expect:  Count >= 10 (at least 10 major dependencies)
Verify:  Directories like v8, abseil, etc. exist
```

### T5: Source Integrity Check
```
Setup:   Source fully fetched
Input:   Calculate SHA256(source_full/src/buildfiles.gni)
Expect:  SHA256 hash exists and is valid
Verify:  Hash stored in artifacts/source.sha256
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** gclient not installed → INV-1 check fails → T1 fails
**F2:** Network unavailable → gclient sync fails → T2 fails
**F3:** .gclient malformed → sync uses wrong config → T3 fails
**F4:** Incomplete download → third_party/ missing → T4 fails
**F5:** Corrupted files → integrity check fails → T5 fails

---

## 8. Visual Evidence (Proof Artifacts)

**proof.json structure:**
```json
{
  "spec_id": "wish-1.0b-chromium-source-fetch",
  "timestamp": "2026-02-14T16:20:00Z",
  "authority": "65537",
  "source_fetch": {
    "started": "2026-02-14T16:20:00Z",
    "completed": "2026-02-14T17:30:00Z",
    "duration_seconds": 4200,
    "method": "gclient sync --with_branch_heads --force"
  },
  "tests": [
    {
      "test_id": "T1",
      "name": "GClient Available",
      "status": "PASS",
      "evidence": {
        "gclient_path": "/path/to/gclient",
        "gclient_version": "string"
      }
    }
  ],
  "source_integrity": {
    "buildfiles_gni_hash": "sha256:...",
    "third_party_count": 42,
    "key_files_present": true
  },
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
- [x] **R4: Deterministic** — Network-aware (can mock with local copy)
- [x] **R5: Hermetic** — Tests verify fetch, don't corrupt system
- [x] **R6: Idempotent** — Can re-run sync safely (updates existing)
- [x] **R7: Fast** — All tests complete in <10 seconds (sync is separate long-running)
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same inputs → Same source always
- [x] **R10: Verifiable** — Artifacts prove source integrity (proof.json, hashes)

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] proof.json generated with source fetch evidence
- [ ] source_full/src/ contains Chromium source
- [ ] No corruption, all key files present
- [ ] Next phase (wish-1.1) can begin immediately

---

## 11. Next Phase

→ **wish-1.1** (Compilation): Compile Chromium to working browser binary

---

**Wish:** wish-1.0b-chromium-source-fetch
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-1.1 (compilation)

*"Fetch source before building from it."*
