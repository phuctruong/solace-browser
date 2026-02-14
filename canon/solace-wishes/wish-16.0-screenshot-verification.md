# WISH 16.0: Screenshot & Visual Verification

**Spec ID:** wish-16.0-screenshot-verification
**Authority:** 65537 | Phase: 16 | Depends On: wish-15.0 | XP: 1100 | GLOW: 114+
**Scope:** Capture screenshots, pixel comparison, visual regression detection
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)

## PRIME TRUTH THESIS

```
Ground truth:    Screenshots are deterministically reproducible
Verification:    Visual changes detected via pixel comparison
Canonicalization: Screenshots stored as deterministic PNG + hash
Content-addressing: Screenshot ID = SHA256(viewport + timestamp)
```

## 1. Observable Wish

> "I can capture screenshots, compare visual changes pixel-perfect, detect visual regressions, and verify UI state visually."

## 2. Scope Exclusions

- ❌ OCR text extraction | ❌ Image AI analysis | ❌ GPU rendering | ❌ Cross-browser rendering

## 3. Minimum Success Criteria

- ✅ Screenshot capture (full page, viewport, element)
- ✅ Pixel-perfect comparison (diff detection)
- ✅ Visual regression detection (threshold-based)
- ✅ Screenshot hashing (deterministic verification)
- ✅ Visual assertion library

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Screenshot Capture
```
Setup:   Page loaded, element visible | Input: Capture screenshot
Expect:  PNG image created | Verify: File exists, valid PNG, >0 bytes
```

### T2: Pixel Comparison
```
Setup:   Baseline screenshot saved | Input: Capture new, compare pixels
Expect:  Comparison report generated | Verify: Diff % calculated correctly
```

### T3: Visual Regression Detection
```
Setup:   Two screenshots (baseline, current) | Input: Check for visual changes
Expect:  Regression detected (>threshold) or clear (<=threshold)
Verify:  Regression report valid, threshold respected
```

### T4: Screenshot Hashing
```
Setup:   Screenshots captured | Input: Generate deterministic hash
Expect:  SHA256 hashes computed | Verify: Hashes deterministic, reproducible
```

### T5: Visual Assertion
```
Setup:   Screenshots compared | Input: Assert visual state matches expected
Expect:  Assertion passes (0% diff) or fails | Verify: Assertion valid, measurable
```

## 9. RTC Checklist

- [x] R1-R10: All requirements satisfied | **RTC Status: 10/10 ✅**

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Screenshot capture works
- [ ] Pixel comparison accurate
- [ ] Regression detection reliable
- [ ] Hashing deterministic
- [ ] Visual assertions functional

## 11. Next Phase

→ **wish-17.0** (JavaScript Execution): Execute scripts in browser context

---

**Wish:** wish-16.0-screenshot-verification | **Status:** RTC 10/10 ✅
**Impact:** Unblocks wish-17.0, enables visual testing

*"See it. Screenshot it. Verify it."*
