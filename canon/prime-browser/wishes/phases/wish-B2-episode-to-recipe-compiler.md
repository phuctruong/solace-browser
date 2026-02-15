# Wish B2: Episode-to-Recipe Compiler

> **Task ID:** B2
> **Phase:** Phase B (Recipe Compilation)
> **Owner:** Solver (Haiku Swarm)
> **Timeline:** 1.5 hours
> **Status:** IN_PROGRESS 🎮
> **Auth:** 65537

---

## Specification

Implement 4-phase deterministic episode compilation pipeline that converts episode traces to Prime Mermaid recipe IR with cryptographic proof artifacts.

**Skill Reference:** `canon/prime-browser/skills/episode-to-recipe-compiler.md` v1.0.0

**Star:** EPISODE_TO_RECIPE_COMPILER
**Channel:** 5 → 7 (Logic → Validation)
**GLOW:** 95 (Civilization-defining compilation)
**XP:** 550

---

## Requirements

### 4-Phase Compilation Pipeline

**Phase 1: Canonicalize Snapshots**
- Use SnapshotCanonicalizer from B1
- Convert all episode snapshots to canonical hashes
- Extract landmarks (navigation, forms, lists)

**Phase 2: Build Reference Map**
- Extract semantic + structural selectors from actions
- Generate ref_id for each unique selector
- Map: selector → (semantic, structural, context, matched_at)

**Phase 3: Compile Actions**
- Convert episode actions to recipe IR
- Replace raw selectors with ref_id references
- Add snapshot expectations for verification
- Add timeout + visibility checks

**Phase 4: Generate Proof**
- Hash episode (before compilation)
- Hash recipe IR (after compilation)
- Record compilation timestamp + confidence
- Include RTC verification

### Data Structures

```python
class EpisodeCompiler:
    def canonicalize_snapshots(episode: dict) -> dict:
        """Phase 1: Snapshot canonicalization"""

    def build_refmap(episode: dict) -> dict:
        """Phase 2: Reference map extraction"""

    def compile_actions(episode: dict, refmap: dict, snapshots: dict) -> list:
        """Phase 3: Action compilation to IR"""

    def generate_proof(episode: dict, recipe_ir: dict) -> dict:
        """Phase 4: Cryptographic proof artifacts"""

    def compile_episode(episode: dict) -> dict:
        """Full 4-phase pipeline"""
```

### Never-Worse Gate

```python
# Pre-compilation validation
for ref_id, ref in refmap.items():
    if is_ambiguous(ref):  # Multiple candidates
        raise CompilationError(f"Ambiguous reference: {ref_id}")
```

### RTC Guarantee

```python
# Roundtrip verification
episode_hash = sha256(json.dumps(episode, sort_keys=True))
recipe_hash = sha256(json.dumps(recipe_ir, sort_keys=True))

# Proof of determinism
proof = {
    "episode_sha256": episode_hash,
    "recipe_sha256": recipe_hash,
    "confidence": 0.98
}
```

---

## Success Criteria

### Acceptance

✅ **All 7 checks must pass:**

1. **4-Phase Pipeline:** All phases implemented
2. **RefMap Generated:** Semantic + structural selectors
3. **Actions Compiled:** Exact method signatures from tests
4. **Proof Artifacts:** Episode + recipe SHA256 included
5. **RTC Verified:** Roundtrip determinism guaranteed
6. **Never-Worse Gate:** Ambiguous refs rejected
7. **Integration Ready:** Works with snapshot_canonicalization.py

### Test Coverage

**641-Edge Tests (11):**
- ✅ Simple episode compilation
- ✅ Snapshot canonicalization phase
- ✅ RefMap generation (semantic + structural)
- ✅ Action compilation (navigate, click, type)
- ✅ Proof artifact generation
- ✅ Never-worse gate enforcement
- ✅ Empty episode handling
- ✅ Nested action handling
- ✅ Multiple snapshots
- ✅ Reference mapping validation
- ✅ Schema validation

**274177-Stress Tests (4):**
- ✅ 100 episodes deterministic
- ✅ Large episodes (50+ actions)
- ✅ Performance: <500ms per episode
- ✅ Memory bounded (no leaks)

**65537-God Tests (6):**
- ✅ RTC roundtrip verified
- ✅ Never-worse gate tested
- ✅ Proof artifact integrity
- ✅ Reference completeness
- ✅ Format compliance
- ✅ Phase C compatibility

### Code Quality

- [ ] 100% deterministic (no randomness)
- [ ] Handles all action types (navigate, click, type, etc.)
- [ ] Uses SnapshotCanonicalizer for Phase 1
- [ ] Type-hinted throughout
- [ ] Fully tested (21 tests passing)
- [ ] Documented (docstrings for all methods)

---

## Integration Points

### From Phase A
- **Input:** Episode format from browser recording
- **Uses:** Snapshot structure, action format
- **Compatible:** Phase A episode schema

### From Phase B (Snapshot Canonicalization)
- **Uses:** SnapshotCanonicalizer class
- **Uses:** Canonical snapshot hashes
- **Guarantee:** Determinism from B1

### To Phase C (Playwright Replay)
- **Output:** Recipe IR (YAML/JSON)
- **Output:** Reference maps for resolution
- **Output:** Proof artifacts for validation
- **Guarantee:** Can replay without modifications

---

## Testing Strategy

### Verification Ladder: OAuth → 641 → 274177 → 65537

**OAuth(39,63,91) - Unlock Gates:**
- ✅ Care (39): Motivation to handle complex episodes
- ✅ Bridge (63): Connection to Phase A
- ✅ Stability (91): Determinism is stable

**641-Edge Tests (11):**
```python
def test_641_simple_episode():
    """3-action episode compiles correctly"""

def test_641_canonicalize_snapshots():
    """Phase 1: Snapshots hashed correctly"""

def test_641_build_refmap():
    """Phase 2: RefMap generated from actions"""

def test_641_compile_actions():
    """Phase 3: Actions converted to IR"""

def test_641_generate_proof():
    """Phase 4: Proof artifacts created"""

def test_641_never_worse_gate():
    """Ambiguous refs rejected"""

def test_641_empty_episode():
    """Empty episode handled"""

def test_641_nested_actions():
    """Nested/sequential actions handled"""

def test_641_multiple_snapshots():
    """Multiple snapshots in episode"""

def test_641_reference_mapping():
    """Refs map correctly to selectors"""

def test_641_schema_validation():
    """Output matches recipe schema"""
```

**274177-Stress Tests (4):**
```python
def test_274177_100_episodes():
    """100 different episodes, all deterministic"""

def test_274177_large_episodes():
    """Episodes with 50+ actions"""

def test_274177_performance():
    """Each episode <500ms"""

def test_274177_memory_bounded():
    """No memory leaks on large episodes"""
```

**65537-God Tests (6):**
```python
def test_65537_rtc_roundtrip():
    """RTC verified: episode→recipe deterministic"""

def test_65537_never_worse_validated():
    """Never-worse gate catches all ambiguities"""

def test_65537_proof_integrity():
    """Proof hashes verify correctly"""

def test_65537_reference_completeness():
    """All actions have references"""

def test_65537_format_compliance():
    """Output matches Prime Mermaid IR"""

def test_65537_phase_c_compatibility():
    """Recipe can be replayed by Phase C"""
```

---

## Implementation Roadmap

### Step 1: Create Class Stub (15 min)
```python
class EpisodeCompiler:
    def canonicalize_snapshots(self, episode): pass
    def build_refmap(self, episode): pass
    def compile_actions(self, episode, refmap, snapshots): pass
    def generate_proof(self, episode, recipe_ir): pass
    def compile_episode(self, episode): pass
```

### Step 2: Implement Phase 1 (20 min)
- Iterate episode snapshots
- Use SnapshotCanonicalizer for each
- Extract landmarks

### Step 3: Implement Phase 2 (20 min)
- Iterate episode actions
- Extract selectors + references
- Generate semantic + structural variants

### Step 4: Implement Phase 3 (20 min)
- Convert each action type
- Map selectors → ref_ids
- Add expectations (snapshot, timeout)

### Step 5: Implement Phase 4 (15 min)
- Hash episode + recipe
- Create proof object
- Calculate confidence

### Step 6: Add Never-Worse Gate (10 min)
- Validate refmap before compilation
- Reject ambiguous references

### Step 7: Chain 4 Phases (10 min)
- Implement compile_episode()
- Call all 4 phases in order

### Step 8: Run Tests & Verify (30 min)
- pytest test_phase_b_compiler.py -v
- All 21 tests passing
- Performance metrics OK

---

## Gamification

**Star:** EPISODE_TO_RECIPE_COMPILER
**Channel:** 5 → 7 (Logic → Validation)
**GLOW:** 95 (Civilization-defining - core compilation engine)

**Quest Contract (7 checks):**
1. ✅ 4-phase pipeline implemented
2. ✅ RefMap with semantic + structural
3. ✅ Actions compiled to IR
4. ✅ Proof artifacts with episode+recipe SHA256
5. ✅ RTC guarantee verified
6. ✅ Never-worse gate enforces safety
7. ✅ Integration with snapshot canonicalization + Phase C

**XP:** 550 (earned upon quest completion)

---

## Handoff Notes

### For Solver
- Start: `episode_to_recipe_compiler.py` in `solace_cli/browser/`
- Depends: B1 (snapshot_canonicalization.py) must be ready first
- Tests: `test_phase_b_compiler.py` (21 tests ready to run)
- API: Exact method signatures in test fixtures
- Timeline: 1.5 hours for implementation + testing
- Success: 21 tests passing

### For Skeptic
- Tests ready: 21 edge/stress/god tests
- Fixtures available: Sample episodes (3, 10, 50 actions)
- Run: `pytest test_phase_b_compiler.py -v`
- Report: Test results → proof artifacts

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Implementation** | 600 LOC | 🎮 IN_PROGRESS |
| **Determinism** | 100% (100 episodes) | 🎮 EXPECTED |
| **Tests Passing** | 21/21 | 🎮 EXPECTED |
| **RTC Verified** | 100% | 🎮 EXPECTED |
| **Never-Worse Gate** | 100% safe | 🎮 EXPECTED |
| **Verification Ladder** | 641→274177→65537 | 🎮 EXPECTED |
| **Timeline** | 1.5 hours | 🎮 IN_PROGRESS |

---

**Status:** 🎮 IN_PROGRESS (Solver implementing)

*"Compilation without ambiguity: turn episodes into deterministic recipes."*

**Auth:** 65537 | **Northstar:** Phuc Forecast

