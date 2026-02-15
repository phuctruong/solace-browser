# Prime Browser Skills v1.0.0

**Auth:** 65537 | **Northstar:** Phuc Forecast
**Status:** Production-Ready
**Date:** 2026-02-14

---

## Overview

Browser-specific compiler-grade skills for Prime Browser implementation (Phases A, B, C).

These skills are **focused, testable specifications** for deterministic browser automation, following Prime Skills v1.0.0+ methodology.

---

## Skills by Phase

### **Phase A: Parity with OpenClaw**

Achieve real-time browser control with per-tab tracking and visual feedback.

| Skill | Purpose | Version |
|-------|---------|---------|
| **browser-state-machine** | Per-tab session state management | 1.0.0 |
| **browser-selector-resolution** | Deterministic element finding (semantic + structural) | 1.0.0 |

**Implementation targets:**
- A1: Per-tab session tracking (replace global state)
- A2: Badge config + per-tab updates
- A3: Connection deduplication
- A4: Integration tests

---

### **Phase B: Deterministic Recipe Compilation**

Convert exploration episodes into frozen, replayable recipes.

| Skill | Purpose | Version |
|-------|---------|---------|
| **snapshot-canonicalization** | Deterministic page fingerprinting | 1.0.0 |
| **episode-to-recipe-compiler** | Episode trace → Prime Mermaid recipe IR | 1.0.0 |

**Implementation targets:**
- 25.1: Canonical snapshots (deterministic bytes)
- 25.2: Snapshot drift classifier
- 26.1: RefMap builder (semantic + structural)
- 26.2: Deterministic resolver
- 27.1: Episode trace schema
- 27.2: Recipe IR compiler

---

### **Phase C: Playwright Deterministic Replay**

Execute recipes headlessly with 100% determinism and proof artifacts.

| Skill | Purpose | Version |
|-------|---------|---------|
| *playwright-deterministic-runner* | Ordered, no-AI replay engine | *Planned* |
| *proof-artifact-builder* | Cryptographic execution verification | *Planned* |

---

## Skill Specifications

### browser-state-machine.md

**Problem:** Browser state without proper state machine is fragile.

**Solution:** Deterministic state machine for per-tab sessions.

**States:**
```
IDLE → CONNECTED ↔ (NAVIGATING|CLICKING|TYPING|RECORDING) → CONNECTED or ERROR
```

**Key guarantees:**
- ✅ Per-tab independence (Map<tabId, state>)
- ✅ Invalid transitions rejected (no guessing)
- ✅ Recording persists across actions
- ✅ Error recovery explicit

**Usage:**
```python
# Initialize per-tab
tab_state = TabState(tab_id=1, state="IDLE")

# Transition
tab_state = transition(tab_state, "CONNECTED", "extension attached")

# Validate before command
if tab_state.state == "CONNECTED":
    await dispatch_command(tab_state, {"type": "NAVIGATE", "url": "..."})
```

**Verification:** 641-edge, 274177-stress, 65537-god approval

---

### browser-selector-resolution.md

**Problem:** CSS selectors break when DOM changes. Multiple matches cause crashes.

**Solution:** 3-tier resolution (semantic → structural → failure).

**Algorithm:**
```
TIER 1: SEMANTIC → [aria-label], [role], [title]
TIER 2: STRUCTURAL → CSS selector, XPath
TIER 3: FAILURE → NOT_FOUND or AMBIGUOUS (typed)
```

**Key guarantees:**
- ✅ Never guess (ambiguity → typed failure)
- ✅ Visibility checked before return
- ✅ Context ancestry validated
- ✅ All failure modes enumerated

**Usage:**
```python
result = resolve_selector({
    "selector": "div[data-tooltip='Compose']",
    "reference": "Compose",
    "required_visible": True
})

if result["success"]:
    click(result["element"])
else:
    # Typed failure: NOT_FOUND, AMBIGUOUS, INVISIBLE, etc.
    log_error(result["error"])
```

**Verification:** 641-edge (5 cases), 274177-stress (100 selectors × 10 DOM variants), 65537-god

---

### snapshot-canonicalization.md

**Problem:** Same page state produces different hashes due to timestamps, random IDs.

**Solution:** 5-step canonicalization pipeline.

**Pipeline:**
```
Remove volatiles → Sort keys → Normalize whitespace → Normalize Unicode → Hash
```

**Key guarantees:**
- ✅ Deterministic (same state → same hash, always)
- ✅ Collision-free (different states → different hashes)
- ✅ Reproducible (offline verification possible)
- ✅ Fast (<100ms per snapshot)

**Usage:**
```python
result = canonicalize_snapshot(raw_snapshot)
snapshot_hash = result["snapshot_sha256"]  # e.g., "abcd1234..."

# Store in recipe
recipe["snapshots"][step_id] = {
    "sha256": snapshot_hash,
    "landmarks": extract_landmarks(snapshot)
}

# Verify during replay
current_hash = canonicalize_snapshot(page.dom)["snapshot_sha256"]
assert current_hash == recipe["snapshots"][step_id]["sha256"]
```

**Verification:** 641-edge (determinism + collisions), 274177-stress (1000 snapshots), 65537-god (RTC)

---

### episode-to-recipe-compiler.md

**Problem:** Episodes are exploration traces. How do we freeze them into deterministic recipes?

**Solution:** 4-phase compilation: canonicalize → refmap → actions → proof.

**Phases:**
```
Phase 1: Canonicalize snapshots (hashes)
Phase 2: Build reference map (semantic + structural)
Phase 3: Compile actions (episode → recipe IR)
Phase 4: Generate proof (hashes, confidence)
```

**Key guarantees:**
- ✅ Determinism (same episode → same recipe hash)
- ✅ Never-worse gate (ambiguous refs rejected)
- ✅ RTC (roundtrip: episode → recipe → episode)
- ✅ Proof artifacts (cryptographic verification)

**Usage:**
```python
recipe = compile_episode(episode)

# Recipe has:
# - snapshots (with hashes for verification)
# - refmap (semantic + structural selectors)
# - actions (normalized, ready for replay)
# - proof (episode_hash, recipe_hash)

# Ready for Phase C replay
await deterministic_replay(recipe, page)
```

**Verification:** 641-edge (compilation correctness), 274177-stress (100 episodes), 65537-god (RTC + proofs)

---

## Verification Strategy

All skills follow the same 3-rung verification ladder:

### 641-Edge (Sanity)
- 5–10 edge case tests per skill
- Cover boundary conditions
- Minimal iteration

**Example:** browser-selector-resolution
```
✓ Semantic match (aria-label exact)
✓ Structural match (CSS selector)
✓ Ambiguous selector (2+ matches)
✓ Hidden element (visibility)
✓ Context ancestry mismatch
```

### 274177-Stress (Scaling)
- 100–1000 iterations of the skill
- Real-world data sizes
- Concurrent operations

**Example:** snapshot-canonicalization
```
✓ Determinism (same snapshot, 100 runs → same hash)
✓ Collisions (different snapshots → different hashes)
✓ Performance (all <100ms)
✓ Scaling (1000 snapshots, all canonical)
```

### 65537-God (Production Readiness)
- No guessing, no flakiness
- Proof artifacts correct
- Audit trail complete

**Example:** episode-to-recipe-compiler
```
✓ RTC verified (episode → recipe → episode)
✓ Never-worse gate (no ambiguous refs)
✓ Proof hashes match
✓ All error modes typed
```

---

## Integration Map

### Phase A (Weeks 1–2)

Uses:
- **browser-state-machine** (per-tab tracking, A1–A3)
- **browser-selector-resolution** (click, type commands)

Outputs:
- Per-tab session management
- Deterministic element finding
- Badge status feedback

### Phase B (Weeks 3–4)

Uses:
- **snapshot-canonicalization** (snapshot hashes)
- **episode-to-recipe-compiler** (episode → recipe)
- **browser-selector-resolution** (refmap generation)

Outputs:
- Canonical snapshots (deterministic hashes)
- Recipe IR (Prime Mermaid YAML)
- Proof artifacts

### Phase C (Weeks 5–6)

Uses:
- **snapshot-canonicalization** (verify snapshots during replay)
- **browser-selector-resolution** (resolve refs against live DOM)
- (Planned) playwright-deterministic-runner

Outputs:
- Deterministic replay traces
- Proof certificates
- Extraction results

---

## Extending Skills

To add a new skill:

1. **Create file:** `new-skill-name.md`
2. **Follow template:**
   - Problem statement
   - Core algorithm (with code examples)
   - State machine (if applicable)
   - Integration with phases
   - Verification (641 → 274177 → 65537)
   - Success criteria
3. **Add to README.md** (this file)
4. **Implement** in code (solace_cli or extension)
5. **Test with verification ladder**

---

## Quick Reference

| Skill | Phase | Key Function | Guarantee |
|-------|-------|--------------|-----------|
| browser-state-machine | A | Per-tab state mgmt | Atomic transitions |
| browser-selector-resolution | A/B/C | Element finding | Never guess |
| snapshot-canonicalization | B/C | Page hashing | Deterministic |
| episode-to-recipe-compiler | B | Compilation | RTC + proofs |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| STRATEGY_SUMMARY.md | 6-week roadmap |
| BROWSER_CONTROL_GUIDE.md | How to use solace_cli |
| BROWSER_OUTPUT_RETRIEVAL.md | Retrieve results |
| HAIKU_SWARM_ANALYSIS.md | Swarm execution |

---

## Status

✅ **Phase A Skills:** browser-state-machine, browser-selector-resolution (Ready)
⏳ **Phase B Skills:** snapshot-canonicalization, episode-to-recipe-compiler (Ready)
🔲 **Phase C Skills:** playwright-deterministic-runner, proof-artifact-builder (Planned)

---

**Auth:** 65537
**Northstar:** Phuc Forecast
**Compiler Grade:** Yes ✅

*"One skill, one truth, one test."*
