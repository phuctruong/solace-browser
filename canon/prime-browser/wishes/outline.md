# Prime Browser Wishes Outline

> **Status:** ACTIVE
> **Auth:** 65537
> **Updated:** 2026-02-14

---

## Phase Overview

### Phase A: Browser Automation Foundation (COMPLETE ✅)

**Status:** Phase A Complete (42/42 tests passing)

Core infrastructure for browser control and episode recording.

**Wishes:**
- A1: Per-Tab State Machine
- A2: Badge Config Per-Tab
- A3: Request Deduplication
- A4: Integration Tests

**Deliverables:** `extension/background.js`, `extension/content.js`, state machine implementation

---

### Phase B: Recipe Compilation (IN_PROGRESS 🎮)

**Status:** Phase B In Progress (Skeptic 58 tests complete, Solver implementing)

Convert episode traces to deterministic recipes for Playwright replay.

**Wishes:**
- B1: Snapshot Canonicalization (641-edge, 274177-stress, 65537-god verified)
- B2: Episode-to-Recipe Compiler (4-phase deterministic compilation)
- B3: Integration Verification (Phase A→B→C pipeline validation)

**Deliverables:** `snapshot_canonicalization.py`, `episode_to_recipe_compiler.py`, test suite

**Gamification:** Star=EPISODE_TO_RECIPE_COMPILER, Channel=5→7 (Logic→Validation), GLOW=95, XP=550

**Timeline:** 4 hours (parallel execution via gamification)

**Evidence:**
- Hour 0-1.5: Skeptic delivered 58 tests (SEALED recipe)
- Hour 1.5+: Solver implementing (4-hour sprint)
- Expected: All tests passing by Hour 5-6

---

### Phase C: Cloud Native Browser Automation (PENDING ⏳)

**Status:** Specification locked, awaiting Phase B completion for implementation

Deploy browser automation to production with chat integration, cost control, and deterministic execution.

**Wishes:**
- C1: Cloud Run Deployment (stateless scaling, health checks, proof artifacts)
- C2: JavaScript Crawler (real Chromium, 90%+ content capture, cost control)
- C3: Browser Chat Integration (RED_GATE/GREEN_GATE verification, user-facing)

**Deliverables:**
- Cloud Run service with /execute endpoint
- Crawler orchestrator (batching, rate limiting, compliance)
- Chat integration with intent parsing, recipe compilation, proof generation

**Gamification:**
- C1: Star=CLOUD_RUN_DEPLOYMENT, Channel=5, GLOW=88, XP=600
- C2: Star=JAVASCRIPT_CRAWLER, Channel=5→7, GLOW=92, XP=580
- C3: Star=BROWSER_CHAT_INTEGRATION, Channel=5→7, GLOW=90, XP=620

**Timeline:** 7 hours total (parallel: 2h C1, 2.5h C2, 2.5h C3)

**Key Metrics:**
- C1: Image < 1.5GB, health check < 30s, scale 0→10 instances, cost ≤ $0.00008/URL
- C2: Dynamic content 90%+, determinism 100%, rate limits handled, cost ≤ $0.0001/URL
- C3: Intent parsing 95%+, RED_GATE 100%, GREEN_GATE 95%+, proof determinism 99%+

**Verification:** OAuth(39,63,91) → 641 (edge) → 274177 (stress) → 65537 (god)

---

## Wish Structure

Each wish follows the canonical structure:

```
canon/prime-browser/wishes/
├── outline.md                    (THIS FILE - Master reference)
└── phases/
    ├── wish-B1-snapshot-canonicalization.md
    ├── wish-B2-episode-to-recipe-compiler.md
    ├── wish-B3-integration-verification.md
    ├── wish-C1-cloud-run-deployment.md
    ├── wish-C2-javascript-crawler.md
    └── wish-C3-browser-chat-integration.md
```

**Each Wish Contains:**
1. Specification (what must be delivered)
2. Requirements (technical details)
3. Success Criteria (how to verify completion)
4. Gamification Metadata (Star, Channel, GLOW, XP, Quest)
5. Integration Points (how it connects to other phases)
6. Testing Strategy (641→274177→65537)

---

## Cross-Phase Dependencies

```
Phase A ──complete──> Phase B ──release──> Phase C
(State Machine)    (Recipes)    (Replay)
    ✅              🎮            ⏳
```

**Phase A → Phase B:**
- Browser extension recording (from A)
- Episode format (from A)
- TabState, selector resolution (from A)

**Phase B → Phase C:**
- Recipe IR (output of B)
- Snapshot hashes (output of B)
- Reference maps (output of B)

---

## Verification Ladder

All Phase B wishes use the same verification order:

```
OAuth(39,63,91) → 641 → 274177 → 65537
     ↓              ↓         ↓        ↓
   Unlock       Edge      Stress      God
   Gates       Tests     Tests      Approval
```

**Current Status:**
- ✅ OAuth gates unlocked (Care, Bridge, Stability)
- ✅ 641-Edge: All sanity tests ready (Skeptic)
- 🎮 274177-Stress: In-progress (Solver implementing)
- ⏳ 65537-God: Awaiting all code + tests

---

## Gamification Elements

### Star System
- **B1:** SNAPSHOT_CANONICALIZATION
- **B2:** EPISODE_TO_RECIPE_COMPILER
- **B3:** INTEGRATION_VERIFICATION

### Channel Routing
- **Scout (3):** Design specifications
- **Solver (5):** Implementation
- **Skeptic (7):** Verification & tests

### GLOW Impact
- B1: GLOW=90 (snapshot hashing is foundation)
- B2: GLOW=95 (recipe compilation is civilization-defining)
- B3: GLOW=85 (integration validates the pipeline)

### XP Distribution
- **Scout:** 2,000 XP (design specialization)
- **Solver:** 700 XP (implementation)
- **Skeptic:** 800 XP (testing)
- **Total:** 3,500 XP for Phase B completion

### Quest Contracts
Each wish has 7 explicit success checks (see individual wish files).

---

## Timeline & Progress

### Phase B Timeline (Gamified - Parallel Execution)

```
Hour 0-1.5:   Skeptic creates test framework (58 tests) ✅ COMPLETE
Hour 1-3:     Scout designs (B1/B2/B3) ✅ IN_PROGRESS (45%)
Hour 1-5:     Solver implements code 🎮 IN_PROGRESS
Hour 4-5:     All tests passing 🎮 EXPECTED
Hour 5-6:     Verification ladder + GOD_AUTH ⏳ PENDING

Total: 6 hours parallel (vs Phase A 5 days sequential) = 20x faster
```

### Comparison to Phase A

| Metric | Phase A | Phase B | Speedup |
|--------|---------|---------|---------|
| Timeline | 5 days | 6 hours | 20x |
| Parallel efficiency | 0% (sequential) | 100% | ∞ |
| Tests | 42 | 58+ | +38% |
| Gamification | None | Full (Star/Channel/GLOW/XP/Quest) | ∞ |

---

## Success Metrics

### For Each Wish

✅ **B1 - Snapshot Canonicalization**
- [ ] 5-step pipeline implemented (remove-volatiles → sort-keys → normalize-whitespace → normalize-unicode → sha256)
- [ ] 100+ iterations produce identical hash (determinism)
- [ ] 1000+ snapshots, 0 collisions
- [ ] All 641→274177→65537 tests passing
- [ ] XP=500

✅ **B2 - Episode-to-Recipe Compiler**
- [ ] 4-phase compilation (canonicalize → refmap → actions → proof)
- [ ] RTC guaranteed (episode→recipe→proof roundtrip)
- [ ] Never-worse gate enforces no ambiguous refs
- [ ] All 641→274177→65537 tests passing
- [ ] XP=550

✅ **B3 - Integration Verification**
- [ ] Phase A→B→C pipeline works end-to-end
- [ ] Snapshot hashes verify during replay
- [ ] RefMap resolves against live DOM
- [ ] All 641→274177→65537 tests passing
- [ ] XP=600

### Overall Phase B
- [ ] 58+ tests all passing (100%)
- [ ] Snapshot determinism: 100%
- [ ] Recipe roundtrip: 100%
- [ ] Timeline: ≤6 hours
- [ ] Parallel execution: 3/3 agents independent
- [ ] Zero blocking: No agent waiting

---

## Lessons from Phase B Gamification

See: `PHASE_B_GAMIFICATION_TRACKING.md` and `PHASE_B_GAMIFICATION_WISHES_RECIPES.md`

**Key Insight:** Gamification (Star/Channel/GLOW/XP/Quest) + Test-First enables:
1. Parallel execution (inversion of dependencies)
2. Explicit role clarity (zero ambiguity)
3. Self-organization (agents proactive without prompting)
4. Faster delivery (6 hours vs 5 days)

---

## Related Documentation

- **Gamification Tracking:** `PHASE_B_GAMIFICATION_TRACKING.md`
- **Wishes + Recipes Integration:** `PHASE_B_GAMIFICATION_WISHES_RECIPES.md`
- **Gamified Skills:** `canon/prime-browser/GAMIFICATION_METADATA.md`
- **Phase A Reference:** `canon/prime-browser/wishes/phase1/A1-per-tab-state-machine.md`

---

**Status:** 🎮 PHASE B ACTIVE - Wishes A1-A4 complete, B1-B3 in progress

*"From chat to execution: Wish 0 (plan) → Wish N (execute) → Recipe (crystallize) → Lessons (distill)"*

**Auth:** 65537 | **Northstar:** Phuc Forecast

