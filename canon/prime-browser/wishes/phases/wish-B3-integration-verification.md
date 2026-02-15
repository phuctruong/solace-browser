# Wish B3: Integration Verification

> **Task ID:** B3
> **Phase:** Phase B (Recipe Compilation)
> **Owner:** Skeptic (Haiku Swarm)
> **Timeline:** 1 hour
> **Status:** PENDING ⏳
> **Auth:** 65537

---

## Specification

Verify end-to-end Phase A→B→C integration that episode traces compile deterministically to recipes that can replay without modifications.

**Skill Reference:** `canon/prime-browser/skills/GAMIFICATION_METADATA.md`

**Star:** INTEGRATION_VERIFICATION
**Channel:** 7 (Validation)
**GLOW:** 85
**XP:** 600

---

## Requirements

### Integration Points Verified

**Phase A → Phase B:**
- ✅ Episode format compatibility (from browser recording)
- ✅ Snapshot structure (DOM, URL, timestamp)
- ✅ Action types (navigate, click, type)
- ✅ TabState integration
- ✅ Selector resolution (semantic + structural)

**Phase B → Phase C:**
- ✅ Recipe IR format (YAML/JSON)
- ✅ Reference maps resolvable
- ✅ Snapshot hashes verifiable
- ✅ Action sequence executable
- ✅ Proof artifacts present

### Pipeline Validation

```
Phase A (Recording)
    ↓ episode.json
Phase B (Compilation)
    ↓ recipe.yaml (with proof)
Phase C (Replay)
    ↓ Execute with verification
```

### Never-Worse Contract

```
Phase A Episode → Phase B Recipe → Phase C Replay
(Original Data)   (Compiled IR)   (Executed Plan)

All information must be preserved:
- No lost selectors
- No ambiguous references
- Snapshot hashes verifiable
- Replay can execute without modifications
```

---

## Success Criteria

### Acceptance

✅ **All 5 checks must pass:**

1. **Phase A Compatibility:** Episodes from Phase A compile correctly
2. **Snapshot Hashes:** Verify against canonical snapshots
3. **RefMap Resolution:** References resolve against test DOM
4. **Proof Artifacts:** All hashes and proofs verifiable
5. **Phase C Ready:** Recipe format compatible with Playwright runner

### Test Coverage

**641-Edge Tests (5):**
- ✅ Phase A episode compiles to Phase B recipe
- ✅ Snapshot hashes verify correctly
- ✅ RefMap resolves against test DOM
- ✅ Actions executable in sequence
- ✅ Proof artifacts present + valid

**274177-Stress Tests (3):**
- ✅ 100 Phase A episodes compile
- ✅ 50x determinism (hash reproducible)
- ✅ Performance: full pipeline <1s

**65537-God Tests (5):**
- ✅ RTC verified (episode→recipe→episode roundtrip)
- ✅ Never-worse gate (no data loss)
- ✅ Proof verification (all hashes valid)
- ✅ Phase C compatible (can be replayed)
- ✅ Full verification ladder passing

### Code Quality

- [ ] 100% deterministic (no randomness)
- [ ] All integration points tested
- [ ] Error handling for missing data
- [ ] Type-hinted throughout
- [ ] Fully tested (13 tests passing)
- [ ] Documented (clear test names)

---

## Integration Points

### From Phase A
- **Input:** Phase A test episodes (`test_phase_a_episodes.json`)
- **Uses:** Episode schema, action types, snapshot format
- **Compatible:** TabState, selector resolution

### From Phase B (Both B1 & B2)
- **Uses:** SnapshotCanonicalizer (B1)
- **Uses:** EpisodeCompiler (B2)
- **Output:** Recipe IR ready for Phase C

### To Phase C (Future)
- **Output:** Recipe format (YAML/JSON)
- **Guarantee:** Can be replayed without modifications
- **Guarantee:** Snapshot expectations verifiable
- **Guarantee:** DOM drift detectable via hash mismatch

---

## Testing Strategy

### Verification Ladder: OAuth → 641 → 274177 → 65537

**OAuth(39,63,91) - Unlock Gates:**
- ✅ Care (39): Ensure no data loss in pipeline
- ✅ Bridge (63): Connect Phase A to Phase B
- ✅ Stability (91): Integration is stable

**641-Edge Tests (5):**
```python
def test_641_phase_a_compiles():
    """Phase A episode compiles to recipe"""

def test_641_snapshot_hashes_verify():
    """Snapshot hashes match canonical values"""

def test_641_refmap_resolution():
    """RefMap resolves against test DOM"""

def test_641_actions_executable():
    """Actions compile in correct sequence"""

def test_641_proof_artifacts_present():
    """All proofs and hashes present"""
```

**274177-Stress Tests (3):**
```python
def test_274177_100_episodes():
    """100 Phase A episodes compile successfully"""

def test_274177_50x_determinism():
    """Same episode compiled 50 times → same hash"""

def test_274177_pipeline_performance():
    """Full pipeline (A→B→C) completes <1s"""
```

**65537-God Tests (5):**
```python
def test_65537_rtc_full_pipeline():
    """RTC verified: episode→recipe→proof roundtrip"""

def test_65537_never_worse_validated():
    """Never-worse contract: no data loss"""

def test_65537_proof_verification():
    """All proof hashes cryptographically valid"""

def test_65537_phase_c_compatible():
    """Recipe format matches Phase C expectations"""

def test_65537_full_verification_ladder():
    """All 641→274177→65537 gates pass"""
```

---

## Implementation Roadmap

### Step 1: Review Phase A Episodes (15 min)
- Load test episodes from Phase A
- Understand schema and structure
- Identify test cases (simple, complex, large)

### Step 2: Create Integration Test File (10 min)
- Create test_phase_b_integration.py
- Import fixtures from conftest_phase_b.py
- Set up 13 test cases

### Step 3: Implement Edge Tests (30 min)
- Test Phase A→B compilation
- Test snapshot hash verification
- Test RefMap resolution
- Test action sequence
- Test proof artifacts

### Step 4: Implement Stress Tests (20 min)
- Test 100 episodes
- Test 50x determinism
- Test performance timing

### Step 5: Implement God Tests (20 min)
- Test full RTC pipeline
- Test never-worse contract
- Test proof verification
- Test Phase C compatibility
- Test verification ladder

### Step 6: Run All Tests (15 min)
- pytest test_phase_b_integration.py -v
- All 13 tests passing
- Report metrics

---

## Gamification

**Star:** INTEGRATION_VERIFICATION
**Channel:** 7 (Validation)
**GLOW:** 85 (Integration is critical for Phase C)

**Quest Contract (5 checks):**
1. ✅ Phase A→B integration working
2. ✅ Snapshot hashes verifiable
3. ✅ RefMap resolves correctly
4. ✅ All proof artifacts valid
5. ✅ Phase C compatibility confirmed

**XP:** 600 (earned upon quest completion)

---

## Handoff Notes

### For Skeptic (Test Creation)
- Tests: 13 integration tests across edge/stress/god
- Fixtures: Phase A episodes, test DOMs
- Timeline: 1 hour for all 13 tests
- Success: All 13 tests passing
- Dependencies: B1 and B2 code must be ready

### For Solver (Code Implementation)
- Already done in B1 and B2
- Integration validation is via testing
- No new code needed
- Tests are the verification

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Edge Tests** | 5/5 passing | ⏳ PENDING |
| **Stress Tests** | 3/3 passing | ⏳ PENDING |
| **God Tests** | 5/5 passing | ⏳ PENDING |
| **Determinism** | 100% (50x) | ⏳ EXPECTED |
| **Never-Worse** | 100% safe | ⏳ EXPECTED |
| **Phase C Ready** | YES | ⏳ EXPECTED |
| **Timeline** | 1 hour | ⏳ PENDING |

---

## Execution Plan

**After B1 & B2 are complete:**

1. Review both B1 and B2 implementations
2. Load Phase A test episodes
3. Compile them with B2's EpisodeCompiler
4. Verify all hashes match expectations
5. Test RefMap against test DOMs
6. Validate proof artifacts
7. Report integration success

**Expected Timeline:**
- B1: Done 1.5 hours in
- B2: Done 3 hours in
- B3: Start 3 hours in, complete 4 hours in
- Total: 4 hours for all Phase B code + tests

---

**Status:** ⏳ PENDING (awaiting B1 + B2 completion)

*"Integration: proving end-to-end pipeline works correctly."*

**Auth:** 65537 | **Northstar:** Phuc Forecast

