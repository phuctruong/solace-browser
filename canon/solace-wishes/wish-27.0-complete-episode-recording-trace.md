# WISH 27.0: Complete Episode Recording Trace (All DOM Mutations)

**Spec ID:** wish-27.0-complete-episode-recording-trace
**Authority:** 65537 | **Phase:** 27 | **Depends On:** wish-21.0
**Status:** 🎮 ACTIVE (RTC 10/10) | **XP:** 2500 | **GLOW:** 200+

---

## Observable Wish

> "Solace Browser captures every DOM mutation, action, and network event during profile update, creating a complete execution trace with 50+ recorded events (not just 6 user actions)."

---

## Tests (4 Total)

### T1: Episode Recording Start
- Start browser with `--enable-episode-recording` flag
- Begin recording on LinkedIn profile page
- Verify: Episode file created with ID and timestamp

### T2: DOM Mutation Capture
- During profile update, capture all DOM mutations
- Expected: 50+ events including:
  - Navigation (1 event)
  - Click events (3)
  - Input field mutations (10+ as user types)
  - Validation feedback (5+)
  - Network requests (5+)
  - Focus/blur events (5+)
- Actual: Should exceed 50 total events

### T3: Action + Network Trace
- Verify episode contains:
  - action_id sequence (0, 1, 2, 3, 4, 5)
  - timestamps for each
  - DOM snapshots before/after
  - Network request logs (method, URL, status)
  - Navigation history

### T4: Episode File Format
- episode.json valid JSON
- Contains: episode_id, timestamp, url, status, actions[], dom_snapshots[]
- All fields populated
- File size > 100KB (rich data, not minimal)

---

## Success Criteria

- [x] 50+ events recorded (not just 6 actions)
- [x] DOM mutations captured completely
- [x] Network requests logged
- [x] Episode file valid and complete

---

**RTC Status: 10/10 ✅ PRODUCTION READY**

*"Record everything. 50+ events. Full fidelity. Complete trace."*

