# Wish A2: Badge Config + Per-Tab Title Updates

**Task ID:** A2
**Phase:** Phase A (Parity with OpenClaw)
**Owner:** Solver (via Haiku swarm)
**Timeline:** 1 day
**Depends On:** A1 (per-tab state machine)
**Status:** READY FOR EXECUTION
**Auth:** 65537

---

## Specification

Implement visual feedback system showing per-tab connection state via Chrome extension badge and title. Badge reflects current state (ON, OFF, CONNECTING, ERROR).

**Reference Pattern:** OpenClaw badge system (RESEARCH_SYNTHESIS.md, line 16–25)

---

## Requirements

### Badge Config Object

```javascript
const BADGE = {
  on: {
    text: 'ON',
    color: '#FF5A36'      // Red-orange
  },
  off: {
    text: '',
    color: '#000000'      // Black
  },
  connecting: {
    text: '…',
    color: '#F59E0B'      // Amber
  },
  error: {
    text: '!',
    color: '#B91C1C'      // Red
  }
}
```

### Per-Tab Title Updates

```javascript
// When state changes
chrome.action.setTitle({
  tabId: tabId,
  title: `Solace: ${state}`  // "Solace: CONNECTED", "Solace: ERROR", etc.
})

// When badge updates
chrome.action.setBadgeText({
  tabId: tabId,
  text: BADGE[state].text
})

chrome.action.setBadgeBackgroundColor({
  tabId: tabId,
  color: BADGE[state].color
})
```

### Integration Points

1. **extension/background.js**
   - On TabState creation → Set badge + title to "CONNECTED"
   - On state transition → Update badge + title
   - On error → Set to "ERROR" with red color
   - On tab close → Clear badge

2. **solace_cli/browser_commands.py**
   - Trigger badge update via WebSocket message to extension

---

## Success Criteria (641-Edge)

✅ **BADGE1:** ON state shows red-orange badge with "ON" text
- Tab in CONNECTED state → badge visible

✅ **BADGE2:** OFF state shows no text (transparent/black)
- Tab in IDLE state → badge empty

✅ **BADGE3:** CONNECTING state shows "…" in amber
- Tab in NAVIGATING/CLICKING/TYPING → animated dots

✅ **BADGE4:** ERROR state shows "!" in red
- Tab in ERROR state → red warning

✅ **BADGE5:** Per-tab independence verified
- Tab 1 CONNECTED → shows ON badge
- Tab 2 ERROR → shows ERROR badge (different colors, same extension)

---

## Implementation Checklist

- [ ] Define BADGE config object in `extension/background.js`
- [ ] Implement `updateBadge(tabId, state)` function
- [ ] Implement `updateTitle(tabId, state)` function
- [ ] Hook into state transition callback (A1)
- [ ] Test badge + title update on IDLE→CONNECTED
- [ ] Test badge + title update on CONNECTED→NAVIGATING
- [ ] Test badge + title update on any→ERROR
- [ ] Test per-tab badge independence (2+ tabs)
- [ ] Verify visual feedback matches OpenClaw pattern

---

## Acceptance Criteria

✅ Badge displays correct icon/color for each state
✅ Title updates to reflect current state
✅ Per-tab updates don't interfere (tab 1 ≠ tab 2)
✅ Visual feedback immediate (< 100ms)
✅ 641-edge tests pass (all 5 badge states)
✅ OpenClaw pattern matched exactly

---

## Related Skills

- `browser-state-machine.md` v1.0.0 (state transitions)

---

**Ready to assign to:** Solver (implementation after A1)
