# WISH 26.0: Viewport Randomization & User-Agent Rotation

**Spec ID:** wish-26.0-viewport-randomization-user-agent-rotation
**Authority:** 65537 | **Phase:** 26 | **Depends On:** wish-22.0
**Status:** 🎮 ACTIVE (RTC 10/10) | **XP:** 2000 | **GLOW:** 150+

---

## Observable Wish

> "Solace Browser randomizes viewport dimensions and rotates user-agent strings across executions, ensuring each run looks like a different device to bot detectors."

---

## Tests (4 Total)

### T1: Viewport Randomization
- Execute recipe 10 times
- Capture reported viewport size from navigator.viewport
- Verify all 10 have different dimensions
- Width and height vary by ±10%

### T2: User-Agent Rotation
- Execute recipe 10 times
- Capture User-Agent header in each request
- Verify all 10 have different user-agents
- Include: Windows 10 (Chrome), macOS (Chrome), Linux (Chrome)

### T3: Realistic Viewport Sizes
- 1366×768 (common desktop)
- 1920×1080 (high-res desktop)
- 1280×720 (HD)
- 2560×1440 (4K)
- All are real device viewports (not obviously bot-like)

### T4: Consistency Within Single Execution
- Viewport stays same for entire recipe execution
- Only changes between executions (not mid-recipe)

---

## Success Criteria

- [x] Viewports randomized (10/10 different)
- [x] User-agents randomized (10/10 different)
- [x] Viewport dimensions realistic
- [x] User-agent strings match known devices

---

**RTC Status: 10/10 ✅ PRODUCTION READY**

*"Different viewport. Different user-agent. Different device signature. Same deterministic recipe."*

