# WISH 13.0: Element Visibility Detection

**Spec ID:** wish-13.0-element-visibility
**Authority:** 65537
**Phase:** 13 (Advanced Element Detection)
**Depends On:** wish-12.0 (network interception complete)
**Scope:** Detect visible elements, check viewport visibility, handle overlays and animations
**Non-Goals:** Accessibility tree parsing, semantic HTML analysis, OCR-based detection
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 1100 | **GLOW:** 108+

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Element visibility is deterministically measurable
  Verification:    Each element's visibility state reproducible
  Canonicalization: Visibility data stored in canonical JSON format
  Content-addressing: Visibility ID = SHA256(element_selector + viewport_hash)
```

---

## 1. Observable Wish

> "I can detect which DOM elements are visible in the viewport, check if elements are hidden/shown, handle elements blocked by overlays, and determine safe click targets before interaction."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Accessibility tree parsing
- ❌ Semantic analysis (alt text, aria labels)
- ❌ OCR or pixel-based detection
- ❌ CSS animation introspection
- ❌ 3D transform calculations

**Minimum success criteria:**
- ✅ Detect elements in viewport (visible_in_viewport boolean)
- ✅ Check display property (visible vs hidden vs none)
- ✅ Detect overlay blocks (element covered by other elements)
- ✅ Verify clickability (visible + not covered + not disabled)
- ✅ Build visibility map (all elements → visibility state)

---

## 3. Context Capsule (Test-Only)

```
Initial:   Network mocking enabled (wish-12.0)
Behavior:  Check element visibility, detect overlays, build visibility maps
Final:     Visibility-aware automation possible, safe clicks guaranteed
```

---

## 4. State Space: 4 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> SCANNING: scan_viewport()
    SCANNING --> ANALYZING: elements_found
    ANALYZING --> REPORTING: visibility_calculated
    REPORTING --> COMPLETE: visibility_map_generated
    SCANNING --> ERROR: scan_failed
    ANALYZING --> ERROR: analysis_failed
    ERROR --> [*]
    COMPLETE --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** All visible elements detected with pixel-perfect accuracy
**INV-2:** Overlay detection prevents clicks on covered elements
**INV-3:** Visibility state change detection works for dynamic content
**INV-4:** Visibility map is deterministic (same page → same map)
**INV-5:** Performance acceptable (<100ms for full page scan)

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Viewport Visibility Detection
```
Setup:   Page loaded with mixed visible/hidden elements
Input:   Scan DOM for visible elements in viewport
Expect:  All visible elements identified with coordinates
Verify:  List includes 100% of visible, excludes hidden elements
```

### T2: Overlay Detection
```
Setup:   Element covered by modal/overlay
Input:   Check if element is obscured by overlay
Expect:  Element marked as "overlay_blocked: true"
Verify:  Overlaid elements excluded from clickable list
```

### T3: Display Property Detection
```
Setup:   Elements with display: none, visibility: hidden, opacity: 0
Input:   Scan for display/visibility/opacity properties
Expect:  Hidden elements detected and categorized
Verify:  Correct categorization: none|hidden|opacity|clipped
```

### T4: Clickability Verification
```
Setup:   Visibility data collected
Input:   Determine which elements are safe to click
Expect:  Clickable elements list (visible + not covered + not disabled)
Verify:  100% safe clicks achieved, no false positives
```

### T5: Visibility Map Generation
```
Setup:   Full page scanned for visibility
Input:   Generate comprehensive visibility report
Expect:  Map includes all elements with visibility states
Verify:  Map valid JSON, deterministic, <100ms generation time
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Viewport scan incomplete → T1 fails, missing visible elements
**F2:** Overlay detection fails → T2 fails, hidden elements marked visible
**F3:** Display property detection wrong → T3 fails, miscategorization
**F4:** Clickability check unsafe → T4 fails, clicks land on wrong targets
**F5:** Visibility map incomplete → T5 fails, missing elements in report

---

## 8. Visual Evidence (Proof Artifacts)

**visibility-scan.json structure:**
```json
{
  "scan_id": "scan-20260214-001",
  "timestamp": "2026-02-14T17:50:00Z",
  "viewport": {
    "width": 1366,
    "height": 768,
    "scroll_x": 0,
    "scroll_y": 0
  },
  "visible_elements": [
    {
      "element_id": "elem-001",
      "selector": "button.primary",
      "tag": "button",
      "text": "Click Me",
      "visible": true,
      "bounding_box": {
        "x": 100,
        "y": 200,
        "width": 120,
        "height": 40
      },
      "in_viewport": true,
      "overlay_blocked": false,
      "clickable": true
    }
  ],
  "hidden_elements": [
    {
      "element_id": "elem-002",
      "selector": "div.modal",
      "tag": "div",
      "visible": false,
      "reason": "display_none",
      "clickable": false
    }
  ],
  "total_visible": 12,
  "total_hidden": 8,
  "total_scanned": 20,
  "scan_duration_ms": 45
}
```

**overlay-detection.json structure:**
```json
{
  "overlay_detection_id": "overlay-20260214-001",
  "timestamp": "2026-02-14T17:51:00Z",
  "overlaid_elements": [
    {
      "element_id": "elem-003",
      "selector": "input.hidden-by-modal",
      "overlay_element": "div.modal-backdrop",
      "overlay_z_index": 1000,
      "element_z_index": 100,
      "coverage_percent": 100,
      "blocked": true
    }
  ],
  "total_overlaid": 1,
  "total_clear": 11,
  "overlay_detection_accuracy": 0.99
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Element visibility detection fully specified
- [x] **R4: Deterministic** — Visibility detection reproducible
- [x] **R5: Hermetic** — No external services, pure DOM inspection
- [x] **R6: Idempotent** — Visibility detection doesn't modify page
- [x] **R7: Fast** — All tests complete in <15 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same page state → same visibility map
- [x] **R10: Verifiable** — Visibility reports prove all elements checked

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Viewport visibility detection 100% accurate
- [ ] Overlay detection prevents false positives
- [ ] Display property detection correct
- [ ] Clickability verification safe
- [ ] Visibility map complete and deterministic

---

## 11. Next Phase

→ **wish-14.0** (Form Filling & Submission): Use visibility detection to fill forms safely

---

**Wish:** wish-13.0-element-visibility
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-14.0, enables smart form interaction

*"See what the user sees. Click what's safe to click."*
