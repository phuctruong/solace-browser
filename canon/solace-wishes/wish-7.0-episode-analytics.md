# WISH 7.0: Episode Analytics & Summarization

**Spec ID:** wish-7.0-episode-analytics
**Authority:** 65537
**Phase:** 7 (Analytics & Summary)
**Depends On:** wish-6.0 (live episode recorder complete)
**Scope:** Analyze recorded episodes, extract patterns, generate summaries
**Non-Goals:** ML training (Phase 8+), visualization, real-time streaming
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 800 | **GLOW:** 97

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Episodes contain behavioral patterns that can be extracted
  Verification:    Each pattern is actionable (can be automated)
  Canonicalization: Summaries stored in canonical format for comparison
  Content-addressing: Pattern fingerprint = SHA256(action_sequence)
```

---

## 1. Observable Wish

> "I can analyze recorded episodes to extract action patterns, generate summaries, and identify common workflows."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ ML-based pattern recognition (Phase 8+)
- ❌ Visual UI analysis
- ❌ Performance optimization
- ❌ Real-time monitoring

**Minimum success criteria:**
- ✅ Episode collection loaded and parsed
- ✅ Action sequence analysis (count, frequency, order)
- ✅ State transition analysis (what URLs visited, how)
- ✅ Pattern fingerprint generation
- ✅ Summary report created

---

## 3. Context Capsule (Test-Only)

```
Initial:   Episodes recorded (wish-6.0), stored in canonical format
Behavior:  Load episodes, analyze patterns, generate reports
Final:     Analytics working, ready for ML training (Phase 8)
```

---

## 4. State Space: 4 States

```
state_diagram-v2
    [*] --> NOT_ANALYZING
    NOT_ANALYZING --> LOADING: load_episodes()
    LOADING --> ANALYZING: episodes_loaded
    ANALYZING --> SUMMARIZING: analysis_complete
    SUMMARIZING --> COMPLETE: summary_generated
    LOADING --> ERROR: load_failed
    ANALYZING --> ERROR: analysis_failed
    SUMMARIZING --> ERROR: summary_failed
    ERROR --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** All episodes loaded into memory with valid JSON structure
**INV-2:** Action sequence extracted from each episode
**INV-3:** Pattern fingerprints deterministic (same actions → same fingerprint)
**INV-4:** Summary includes: total episodes, total actions, action frequency, top patterns
**INV-5:** Summary statistics are consistent (counts add up correctly)

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Episode Collection Loaded
```
Setup:   Episodes stored in artifacts/episodes/
Input:   Load all episode files into memory
Expect:  All episodes parsed successfully
Verify:  Episode count matches file count, all have valid structure
```

### T2: Action Sequence Analysis
```
Setup:   Episodes loaded
Input:   Extract action sequences from episodes
Expect:  Each episode yields ordered action list
Verify:  Total action count matches sum of episode actions
```

### T3: State Transition Analysis
```
Setup:   Action sequences extracted
Input:   Analyze state transitions (URLs, page changes)
Expect:  Transition graph generated
Verify:  Graph is acyclic and consistent
```

### T4: Pattern Fingerprint Generation
```
Setup:   Analyses complete
Input:   Generate fingerprint for each action sequence
Expect:  Fingerprints deterministic (same sequence = same fingerprint)
Verify:  Fingerprints are 64-char hex (SHA256)
```

### T5: Summary Report Generated
```
Setup:   All analyses complete
Input:   Generate comprehensive summary
Expect:  Summary includes counts, frequencies, top patterns
Verify:  Summary JSON valid, all statistics consistent
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Episode files missing → T1 fails
**F2:** Episode format invalid → T1 parsing fails
**F3:** Action extraction incomplete → T2 counts wrong
**F4:** State transitions cyclic → T3 fails
**F5:** Fingerprints non-deterministic → T4 fails

---

## 8. Visual Evidence (Proof Artifacts)

**analytics-report.json structure:**
```json
{
  "report_timestamp": "2026-02-14T17:10:00Z",
  "episode_statistics": {
    "total_episodes": 3,
    "total_actions": 9,
    "average_actions_per_episode": 3.0,
    "episodes_analyzed": 3
  },
  "action_frequency": {
    "click": 3,
    "type": 2,
    "navigate": 2,
    "scroll": 2
  },
  "top_patterns": [
    {
      "pattern": "click → type → navigate",
      "frequency": 1,
      "fingerprint": "sha256:..."
    }
  ],
  "state_transitions": {
    "unique_urls": ["https://example.com", "https://example.com/search"],
    "transition_count": 3
  },
  "summary": {
    "primary_workflow": "search_and_navigate",
    "dataset_quality": "good",
    "ready_for_ml": true
  }
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Analytics pipeline fully specified
- [x] **R4: Deterministic** — Pattern analysis is repeatable
- [x] **R5: Hermetic** — No external services, uses local episodes
- [x] **R6: Idempotent** — Analysis doesn't modify episodes
- [x] **R7: Fast** — All tests complete in <10 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same episodes always produce same analysis
- [x] **R10: Verifiable** — Report artifacts prove all analyses complete

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Episode collection loaded successfully
- [ ] Action sequences extracted correctly
- [ ] Pattern fingerprints deterministic
- [ ] Summary report generated and verified

---

## 11. Next Phase

→ **wish-8.0** (Batch Processing): Execute multiple episodes in sequence with verification

---

**Wish:** wish-7.0-episode-analytics
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-8.0, enables Phase 8 ML training with dataset insights

*"Analyze episodes before training models."*
