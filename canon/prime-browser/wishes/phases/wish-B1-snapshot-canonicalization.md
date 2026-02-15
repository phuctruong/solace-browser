# Wish B1: Snapshot Canonicalization

> **Task ID:** B1
> **Phase:** Phase B (Recipe Compilation)
> **Owner:** Solver (Haiku Swarm)
> **Timeline:** 1.5 hours
> **Status:** IN_PROGRESS 🎮
> **Auth:** 65537

---

## Specification

Implement 5-step deterministic snapshot canonicalization pipeline that converts raw browser DOM snapshots to canonical byte-exact hashes.

**Skill Reference:** `canon/prime-browser/skills/snapshot-canonicalization.md` v1.0.0

**Star:** SNAPSHOT_CANONICALIZATION
**Channel:** 5 → 7 (Logic → Validation)
**GLOW:** 90
**XP:** 500

---

## Requirements

### 5-Step Pipeline

1. **Remove Volatiles**
   - Strip timestamp, sessionId, requestId, uuid fields
   - Remove browser-specific metadata
   - Keep structural content + text

2. **Sort Keys**
   - Recursively sort all JSON object keys
   - Alphabetical order for determinism
   - Consistent across all snapshots

3. **Normalize Whitespace**
   - Trim leading/trailing whitespace
   - Collapse internal whitespace to single space
   - Remove newlines from text content

4. **Normalize Unicode**
   - Convert all unicode escapes to normalized form (NFC)
   - Consistent character representation
   - No encoding surprises

5. **SHA256 Canonicalization**
   - Hash canonical JSON bytes
   - Deterministic (100 iterations → identical hash)
   - Collision-free (1000+ snapshots)

### Data Structure

```python
class SnapshotCanonicalizer:
    # Constants
    VOLATILES_ALWAYS_REMOVE = [
        'timestamp', 'sessionId', 'requestId', 'uuid',
        'computedStyle', 'boundingClientRect', 'offsetTop'
    ]

    # Methods
    def remove_volatiles(snapshot: dict) -> dict:
        """Remove browser-specific volatile fields"""

    def sort_keys(obj: dict) -> dict:
        """Recursively sort all JSON keys alphabetically"""

    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace (collapse, trim)"""

    def normalize_unicode(obj: dict) -> dict:
        """Normalize unicode to NFC"""

    def json_canonicalize(obj: dict) -> str:
        """Canonical JSON string (sorted, compact)"""

    def canonicalize_snapshot(raw_snapshot: dict) -> dict:
        """Full 5-step pipeline → {sha256, canonical_json}"""
```

---

## Success Criteria

### Acceptance

✅ **All 7 checks must pass:**

1. **Determinism:** 100+ identical snapshots → identical hash
2. **Collision-Free:** 1000+ unique snapshots → 0 collisions
3. **Volatiles Removed:** No timestamp, sessionId, uuid in output
4. **Keys Sorted:** All dict keys in alphabetical order
5. **Whitespace Normalized:** No extra spaces, newlines
6. **Unicode Normalized:** Consistent character representation
7. **Integration Ready:** Works with episode_to_recipe_compiler.py

### Test Coverage

**641-Edge Tests (8):**
- ✅ Simple snapshot determinism
- ✅ Whitespace normalization
- ✅ Unicode escapes
- ✅ Volatile field removal
- ✅ Key sorting
- ✅ Empty/null handling
- ✅ Nested structure recursion
- ✅ Large DOM determinism

**274177-Stress Tests (4):**
- ✅ 100 iterations identical hash
- ✅ 1000 variant snapshots, 0 collisions
- ✅ Performance: <100ms per snapshot
- ✅ Large DOM (100KB+)

**65537-God Tests (4):**
- ✅ Collision-free (adversarial)
- ✅ JSON roundtrip (encode/decode)
- ✅ Structure preservation
- ✅ Idempotent (hash(hash) = hash)

### Code Quality

- [ ] 100% deterministic (no randomness)
- [ ] No external dependencies (use standard library)
- [ ] Type-hinted (typing module)
- [ ] Fully tested (58 tests passing)
- [ ] Documented (docstrings for all methods)

---

## Integration Points

### From Phase A
- **Input:** Episode snapshots from browser recording
- **Uses:** canonical_json.py utility (if available)
- **Compatible:** TabState, DOM structure from A

### To Phase B (Episode Compiler)
- **Output:** Canonical snapshot hashes
- **Used By:** `episode_to_recipe_compiler.py`
- **Guarantee:** RTC (roundtrip verification)

### To Phase C (Playwright Replay)
- **Output:** Snapshot expectations in recipe IR
- **Used For:** Verification during replay
- **Guarantee:** Can detect drift via hash mismatch

---

## Testing Strategy

### Verification Ladder: OAuth → 641 → 274177 → 65537

**OAuth(39,63,91) - Unlock Gates:**
- ✅ Care (39): Motivation to handle edge cases
- ✅ Bridge (63): Connection to Phase A
- ✅ Stability (91): Determinism is stable

**641-Edge Tests:**
```python
def test_641_determinism_simple():
    """Same snapshot → identical hash (sanity)"""

def test_641_whitespace_normalization():
    """Extra spaces/newlines removed"""

def test_641_unicode_normalization():
    """Unicode escapes consistent"""

def test_641_volatile_removal():
    """Timestamps, UUIDs removed"""

def test_641_key_sorting():
    """All keys alphabetically sorted"""

def test_641_empty_handling():
    """Empty/null values handled"""

def test_641_nested_recursion():
    """Nested structures sorted recursively"""

def test_641_large_dom():
    """Large snapshot (>10KB) deterministic"""
```

**274177-Stress Tests:**
```python
def test_274177_100_iterations():
    """100 runs of same snapshot → identical hash"""

def test_274177_1000_variants():
    """1000 different snapshots → 0 collisions"""

def test_274177_performance():
    """Each snapshot <100ms"""

def test_274177_large_100kb():
    """100KB+ DOM deterministic"""
```

**65537-God Tests:**
```python
def test_65537_collision_adversarial():
    """Adversarial: Try to cause collision"""

def test_65537_json_roundtrip():
    """encode/decode/encode = encode"""

def test_65537_structure_preserved():
    """Content structure unchanged"""

def test_65537_idempotent():
    """hash(hash) preserves hash"""
```

---

## Implementation Roadmap

### Step 1: Create Class Stub (15 min)
```python
class SnapshotCanonicalizer:
    VOLATILES_ALWAYS_REMOVE = [...]
    # Methods with pass
```

### Step 2: Implement remove_volatiles() (20 min)
- Recursively traverse dict
- Remove keys in VOLATILES_ALWAYS_REMOVE
- Preserve structure

### Step 3: Implement sort_keys() (20 min)
- Recursively sort all dicts
- Preserve order for lists
- Maintain types

### Step 4: Implement normalize_whitespace() (10 min)
- Strip leading/trailing
- Collapse internal spaces
- Handle newlines

### Step 5: Implement normalize_unicode() (10 min)
- Use unicodedata.normalize('NFC', ...)
- Handle all string fields

### Step 6: Implement json_canonicalize() (15 min)
- json.dumps with sort_keys=True
- Compact output (no spaces)
- Deterministic

### Step 7: Implement canonicalize_snapshot() (10 min)
- Chain all 5 steps
- Return {sha256, canonical_json, landmarks}

### Step 8: Run Tests & Verify (30 min)
- pytest test_phase_b_canonicalization.py -v
- All 16 tests passing
- Check performance metrics

---

## Gamification

**Star:** SNAPSHOT_CANONICALIZATION
**Channel:** 5 → 7 (Logic → Validation)
**GLOW:** 90 (Snapshot hashing is high-impact foundation)

**Quest Contract (7 checks):**
1. ✅ 5-step pipeline implemented
2. ✅ 100+ iterations deterministic
3. ✅ 1000+ snapshots, 0 collisions
4. ✅ All 641-edge tests (8) passing
5. ✅ All 274177-stress tests (4) passing
6. ✅ All 65537-god tests (4) passing
7. ✅ Integration with episode_to_recipe_compiler.py

**XP:** 500 (earned upon quest completion)

---

## Handoff Notes

### For Solver
- Start: `snapshot_canonicalization.py` in `solace_cli/browser/`
- Tests: `test_phase_b_canonicalization.py` (ready to run)
- API: Exact method signatures in test fixtures
- Timeline: 1.5 hours for implementation + testing
- Success: 16 tests passing

### For Skeptic
- Tests ready: 16 edge/stress/god tests
- Fixtures available: MINIMAL_DOM, GMAIL_DOM variants
- Run: `pytest test_phase_b_canonicalization.py -v`
- Report: Test results → proof artifacts

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Implementation** | 500 LOC | 🎮 IN_PROGRESS |
| **Determinism** | 100% (100+ iterations) | 🎮 EXPECTED |
| **Collisions** | 0 (1000+ snapshots) | 🎮 EXPECTED |
| **Tests Passing** | 16/16 | 🎮 EXPECTED |
| **Verification Ladder** | 641→274177→65537 | 🎮 EXPECTED |
| **Timeline** | 1.5 hours | 🎮 IN_PROGRESS |

---

**Status:** 🎮 IN_PROGRESS (Solver implementing)

*"Deterministic hashing: the foundation for reliable recipe compilation."*

**Auth:** 65537 | **Northstar:** Phuc Forecast

