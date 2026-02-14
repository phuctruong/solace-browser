# WISH 2.0: Episode Recording Infrastructure

**Spec ID:** wish-2.0-episode-recording
**Authority:** 65537
**Phase:** 2 (Recording & Capture)
**Depends On:** wish-1.0 (build infrastructure verified)
**Scope:** Verify episode recording system can capture browser state, actions, and events deterministically
**Non-Goals:** Full automation (Phase 3+), ML training (Phase 8+)
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 550 | **GLOW:** 85

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Episode recording captures browser state snapshots, action sequences
  Verification:    Each episode has valid JSON schema, checksums match, playback deterministic
  Canonicalization: Episodes stored as canonical JSON with locked field ordering
  Content-addressing: SHA256(episode.json) used for deduplication and versioning
```

---

## 1. Observable Wish

> "I can record browser episodes (state snapshots + action sequences) deterministically, store them as canonical JSON, and verify each episode's integrity."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Live browser automation (Phase 3)
- ❌ Episode playback/execution (Phase 4+)
- ❌ ML training on episodes (Phase 8+)
- ❌ Cross-browser testing (Phase 10+)

**Minimum success criteria:**
- ✅ Episode JSON schema defined
- ✅ Sample episode captured to file
- ✅ Episode validates against schema
- ✅ Episode checksum is deterministic
- ✅ Episode can be re-captured identically

---

## 3. Context Capsule (Test-Only)

```
Initial:   Build infrastructure ready (wish-1.0)
Behavior:  Define episode schema, record sample episodes, verify integrity
Final:     Episode recording system verified, ready for Phase 3 automation
```

---

## 4. State Space: 4 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> DEFINING_SCHEMA: start()
    DEFINING_SCHEMA --> RECORDING: schema defined
    RECORDING --> VERIFYING: episode recorded
    VERIFYING --> SUCCESS: schema valid & checksum OK
    DEFINING_SCHEMA --> ERROR: schema malformed
    RECORDING --> ERROR: capture failed
    VERIFYING --> ERROR: integrity failed
    ERROR --> [*]
    SUCCESS --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** Episode schema file exists at `canon/episode-schema.json`
**INV-2:** Episode schema is valid JSON and matches OpenAPI 3.0 format
**INV-3:** All episodes have required fields: `id`, `timestamp`, `state_snapshot`, `actions`, `checksum`
**INV-4:** Checksums are SHA256 and deterministic (same input = same hash)
**INV-5:** Episode files stored in `artifacts/episodes/` with timestamp naming

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Episode Schema Exists & Valid
```
Setup:   Project root with canon/ directory
Input:   Load canon/episode-schema.json
Expect:  Valid JSON document with episode structure
Verify:  Schema has required fields: id, timestamp, state_snapshot, actions, metadata
```

### T2: Record Sample Episode
```
Setup:   Schema validated, artifacts/episodes/ directory created
Input:   Capture episode (mock: use fixture data)
Expect:  Episode JSON file created with valid structure
Verify:  File contains all required fields, no nulls in critical paths
```

### T3: Episode Validates Against Schema
```
Setup:   Episode recorded
Input:   Validate episode against schema (jsonschema library)
Expect:  Validation passes (no schema violations)
Verify:  All required fields present, types match
```

### T4: Episode Checksum Deterministic
```
Setup:   Episode validated
Input:   Calculate SHA256(episode.json) twice
Expect:  Both checksums identical
Verify:  Determinism proof (same input always produces same hash)
```

### T5: Episode Playback Ready (Schema Only)
```
Setup:   Episode verified, checksum stored
Input:   Check episode format for playback compatibility
Expect:  Action sequence is array of {type, target, value, timestamp}
Verify:  All playback-required fields present, valid action types
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Schema file missing → INV-1 fails → T1 fails
**F2:** Schema is invalid JSON → Schema validation fails → T1 fails
**F3:** Episode missing required field → T2 capture fails or T3 validation fails
**F4:** Episode checksum varies → F4 non-deterministic → T4 fails
**F5:** Action format incompatible with playback → T5 fails

---

## 8. Visual Evidence (Proof Artifacts)

**Artifacts generated:**
- `canon/episode-schema.json` - OpenAPI 3.0 schema for episodes
- `artifacts/episodes/episode-*.json` - Sample recorded episodes
- `artifacts/episode-proof.json` - Validation proof with checksums

**proof.json structure:**
```json
{
  "spec_id": "wish-2.0-episode-recording",
  "timestamp": "2026-02-14T16:45:00Z",
  "authority": "65537",
  "tests": [
    {
      "test_id": "T1",
      "name": "Episode Schema Valid",
      "status": "PASS",
      "evidence": {
        "schema_file": "canon/episode-schema.json",
        "schema_version": "1.0.0",
        "fields_count": 8
      }
    }
  ],
  "episodes_recorded": 3,
  "checksums": [
    {"episode_id": "ep-001", "checksum": "sha256:...", "determinism_verified": true}
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
- [x] **R3: Complete** — No ambiguous assertions; schema and playback fully defined
- [x] **R4: Deterministic** — No timestamps in comparison, fixed schema
- [x] **R5: Hermetic** — Tests don't require live browser, only schema validation
- [x] **R6: Idempotent** — Tests can run multiple times safely
- [x] **R7: Fast** — All tests complete in <5 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same episodes always produce same checksums
- [x] **R10: Verifiable** — Artifacts prove schema validity and episode integrity

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Episode schema generated with correct structure
- [ ] Sample episodes recorded and validated
- [ ] Checksums deterministic and stored
- [ ] Proof artifact generated

---

## 11. Next Phase

→ **wish-3.0** (Action Automation): Implement action playback from episodes

---

**Wish:** wish-2.0-episode-recording
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-3.0 (automation), establishes core Solace feature

*"Record episodes before automating them."*
