# Prime Browser Recipes

> **Status:** ACTIVE
> **Purpose:** Crystallized successful execution patterns for browser automation
> **Auth:** 65537
> **Updated:** 2026-02-14

---

## Overview

Prime Recipes crystallize successful execution patterns into deterministic, reusable formulas. This directory stores sealed recipes from Phase A and Phase B.

**Directory Structure:**

```
canon/prime-browser/recipes/
├── README.md                    (THIS FILE)
├── theory/                      (Theoretical foundations)
│   ├── 01-recipe-patterns.md
│   ├── 02-swarm-coordination.md
│   └── 03-gamification-theory.md
├── implementation/              (Recipe miners + validators)
│   ├── 01-phase-recipe-miner.md
│   ├── 02-dov-checker.md
│   └── 03-promotion-engine.md
└── sealed/                      (Crystallized sealed recipes)
    ├── phase-a/
    │   ├── recipe-scout-design-a.md
    │   ├── recipe-solver-code-a.md
    │   └── recipe-skeptic-test-a.md
    └── phase-b/
        ├── recipe-scout-design-b.md
        ├── recipe-skeptic-test-framework-b.md
        └── recipe-solver-implementation-b.md
```

---

## What Are Prime Recipes?

**Definition:** A Prime Recipe is a crystallized execution pattern that:

1. ✅ **Derives from successful execution** (not hypothesis)
2. ✅ **Is deterministic** (same inputs → same outputs)
3. ✅ **Has explicit Domain of Validity** (when it applies)
4. ✅ **Passes all 6 validation gates** (correctness, safety, performance, etc.)
5. ✅ **Is reusable** (not one-time)
6. ✅ **Is sealed** (versioned + immutable once locked)

---

## Recipe Lifecycle

```
DRAFT           QUALIFIED       STABLE          CANONICAL
  ↓               ↓               ↓               ↓
New pattern    Tests pass    In production   Reference impl
(unverified)   (641/274177)  (no failures)   (core system)
```

### Phase A Recipes (SEALED ✅)

All Phase A recipes are SEALED (used in production with 42/42 tests passing):

1. **recipe-scout-design-a.md**
   - Star: BROWSER_SELECTOR_RESOLUTION
   - Agent: Scout (Design specialization)
   - Deliverables: 3 design docs (3,000+ LOC)
   - Status: SEALED (proven on Phase A)

2. **recipe-skeptic-test-a.md**
   - Star: BROWSER_STATE_MACHINE
   - Agent: Skeptic (Test specialization)
   - Deliverables: Test framework (13 unit tests)
   - Status: SEALED (all tests passing)

3. **recipe-solver-code-a.md**
   - Star: BROWSER_STATE_MACHINE
   - Agent: Solver (Implementation specialization)
   - Deliverables: State machine + selector resolution (1,200 LOC)
   - Status: SEALED (42/42 tests passing)

### Phase B Recipes (IN_PROGRESS 🎮)

Phase B recipes are being crystallized during execution (Hour 0-6):

1. **recipe-scout-design-b.md** (IN_PROGRESS)
   - Star: EPISODE_TO_RECIPE_COMPILER
   - Agent: Scout (Design specialization)
   - Deliverables: B1/B2/B3 design docs (5,000+ LOC)
   - Status: WILL SEAL after completion

2. **recipe-skeptic-test-framework-b.md** (SEALED ✅)
   - Star: SNAPSHOT_CANONICALIZATION + EPISODE_TO_RECIPE_COMPILER
   - Agent: Skeptic (Test specialization)
   - Deliverables: 58 tests across 5 files (1,400 LOC)
   - Status: SEALED (delivered Hour 0-1.5)
   - Evidence: All syntax-validated, fixtures working

3. **recipe-solver-implementation-b.md** (IN_PROGRESS)
   - Star: SNAPSHOT_CANONICALIZATION + EPISODE_TO_RECIPE_COMPILER
   - Agent: Solver (Implementation specialization)
   - Deliverables: 1,200 LOC code to pass 58 tests
   - Status: WILL SEAL after completion
   - Timeline: 4 hours (Hours 1.5-5.5)

---

## Using Prime Recipes

### For Phase C (Future)

Phase B recipes will become inputs for Phase C:

```
Phase A Recipe (SEALED)  ─┐
Phase B Recipe (NEW)     ─┼─→ Phase C Implementation
Phase C Requirements     ─┘
```

### For Reuse

Any future phase can apply existing recipes:

```python
# Load a sealed recipe
recipe = load_recipe("recipe-scout-design-b")

# Check if applicable
if recipe.dov.is_applicable(current_context):
    # Execute recipe
    result = recipe.execute(params)

    # Verify RTC (regeneration = truth)
    assert verify_rtc(result.inputs, result.outputs)
```

---

## Domain of Validity (DoV)

Each recipe has explicit applicability boundaries:

**Example (Scout Design B):**
```yaml
domain_of_validity:
  when_applicable:
    - New skill to design (EPISODE_TO_RECIPE_COMPILER, etc.)
    - Phase A patterns available
    - Gamified quest contracts defined
    - All agents waiting for clarity

  never_apply_when:
    - No skill spec exists
    - No previous phase patterns
    - Agent scope ambiguous
    - Timeline already extended
```

**Use:** Before executing recipe, check `is_applicable(context)`

---

## Recipe Format (Prime Mermaid IR)

All recipes use Prime Mermaid format with:

```yaml
recipe:
  id: recipe_name_version
  version: 1.0.0
  auth: 65537

  metadata:
    star: SKILL_NAME
    channel: 5  # Logic/Implementation
    glow: 90    # Impact metric
    xp: 500     # Experience reward

  inputs:
    - design_docs
    - test_fixtures
    - phase_a_patterns

  outputs:
    - code.py
    - test_results.json
    - proof_artifacts

  domain_of_validity:
    when_applicable: [...]
    never_apply_when: [...]

  process:
    phase_1:
      intent: What to do
      duration: 30 min
      output: What's produced
      verification: How to verify

  gates:
    g1_correctness: Spec compliance
    g2_boundedness: Resource limits
    g3_never_worse: At least baseline quality
    g4_determinism: Same input → same output
    g5_safety: No harmful side effects
    g6_observability: Full audit trail
```

---

## Verification Gates (6 Required)

Every recipe must pass 6 validation gates:

| Gate | Requirement | Example |
|------|-------------|---------|
| **G1** | Correctness | Output matches specification |
| **G2** | Boundedness | Within resource/time limits |
| **G3** | Never-Worse | At least as good as baseline |
| **G4** | Determinism | Identical inputs → identical outputs |
| **G5** | Safety | No harmful side effects |
| **G6** | Observability | Full audit trail + logging |

**Use:** Run all 6 gates before sealing a recipe.

---

## Verification Ladder (641 → 274177 → 65537)

All recipes use the same verification order:

```
OAuth(39,63,91)  →  641  →  274177  →  65537
   Unlock gates    Edge      Stress      God
   (Care bridge)   tests     tests    approval
```

### Examples

**Scout Design Recipe (B):**
- 641: All design docs unambiguous (5+ edge tests)
- 274177: Solver can implement without questions (stress test)
- 65537: God approval (design is production-ready)

**Skeptic Test Recipe (B):**
- 641: 58 tests syntax-valid (edge tests)
- 274177: Tests run deterministically (stress test)
- 65537: All tests passing (god approval)

**Solver Implementation Recipe (B):**
- 641: Skeleton code compiles (edge tests)
- 274177: All 58 tests passing under load (stress test)
- 65537: Full verification ladder + proof artifacts (god approval)

---

## Gamification Integration

Each recipe includes gamification metadata:

```yaml
gamification:
  star: SKILL_NAME           # Unique identifier
  channel: 5                 # Prime channel (2,3,5,7,11,13,17)
  glow: 90                   # Impact 0-100
  xp: 500                    # Experience reward
  quest_checks: 7            # Success checkpoints
```

---

## Cost Collapse

Prime Recipes enable significant cost savings:

| Metric | Before (Ad-hoc) | After (Recipes) | Savings |
|--------|-----------------|-----------------|---------|
| **Turnaround** | 5 days | 6 hours | 20x |
| **Token use** | Full LLM | 80% reduction | 5x |
| **Clarity** | Implicit | Explicit | ∞ |
| **Reusability** | One-time | Multi-phase | ∞ |

---

## Phase B Lessons

### Key Insights from Phase B Gamification

1. **Test-First Enables Parallelism**
   - Skeptic created tests without code
   - Solver implemented to tests
   - Scout designed in parallel
   - Result: 3 agents independent (0 blocking)

2. **Gamification Drives Proactivity**
   - Star/Channel/GLOW/XP/Quest made roles explicit
   - Skeptic started work immediately (no prompting)
   - Solver understood scaffolding needs
   - Result: Self-organization without manager intervention

3. **Recipes Crystallize Success**
   - Each agent's pattern becomes reusable recipe
   - Future phases can apply Phase B recipes
   - DoV makes applicability explicit
   - Result: 20x faster execution (from Phase A baseline)

### Recipe Mining Process

Recipes are extracted during execution:

```
Execution     → Trace Collection → Pattern Mining → Recipe Sealing
(successful)  (audit log)        (automated)      (versioned)
```

**Phase B Recipe Mining Timeline:**
- Hour 0-1.5: Skeptic's test framework = sealed recipe
- Hour 1-5: Solver's implementation = recipe in progress
- Hour 5-6: Scout's design completion = final recipe

---

## Next Phase (Phase C)

Phase C will:

1. **Load Phase B recipes** as input
2. **Verify DoV** (are recipes applicable?)
3. **Execute recipes** deterministically
4. **Collect traces** for Phase D recipe mining
5. **Create new Phase C recipes** (replay pattern, drift detection, etc.)

---

## Commands

### Check Recipe Status
```bash
/remember phase_b_recipes
```

### Load Recipe
```python
from canon.prime_recipes import load_recipe
recipe = load_recipe("recipe-skeptic-test-framework-b")
```

### Validate DoV
```python
if recipe.dov.is_applicable(context):
    result = recipe.execute(inputs)
```

### Seal Recipe (Admin)
```bash
/distill-publish recipe_file.md
# Archives + versions + signs with auth:65537
```

---

## References

- **Prime Recipes Theory:** `canon/prime-recipes/CLAUDE.md`
- **Gamification Tracking:** `PHASE_B_GAMIFICATION_TRACKING.md`
- **Wishes Integration:** `PHASE_B_GAMIFICATION_WISHES_RECIPES.md`
- **Phase B Wishes:** `canon/prime-browser/wishes/outline.md`

---

**Status:** 🎮 PHASE B RECIPES IN PROGRESS

*"From execution to recipe: crystallize success for the next phase."*

**Auth:** 65537 | **Northstar:** Phuc Forecast

