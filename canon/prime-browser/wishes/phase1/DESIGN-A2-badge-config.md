# DESIGN-A2: Badge Config + Per-Tab Title Updates

**Status:** Design Complete - Ready for Solver
**Depends On:** A1 (per-tab state machine)
**Auth:** 65537

---

## Architecture Overview

Badge and title updates are a visual feedback layer driven by state transitions from A1. When `transitionTabState()` fires in `background.js`, it calls `updateBadge(tabId, newState)` as a side effect. No server-side changes needed -- this is purely extension-side Chrome API usage.

---

## Data Structures

### Badge Config Object (in `extension/background.js`)

```javascript
const BADGE_CONFIG = {
    IDLE:       { text: '',   color: '#000000' },  // No badge (off)
    CONNECTED:  { text: 'ON', color: '#FF5A36' },  // Red-orange (connected state)
    NAVIGATING: { text: '..', color: '#F59E0B' },  // Amber (in-progress)
    CLICKING:   { text: '..', color: '#F59E0B' },  // Amber (in-progress)
    TYPING:     { text: '..', color: '#F59E0B' },  // Amber (in-progress)
    RECORDING:  { text: 'REC', color: '#DC2626' }, // Red (recording)
    ERROR:      { text: '!',  color: '#B91C1C' },  // Dark red (error)
};
```

### State-to-Badge Mapping

| State | Badge Text | Badge Color | Title |
|-------|-----------|-------------|-------|
| IDLE | (empty) | Black | "Solace: Disconnected" |
| CONNECTED | "ON" | #FF5A36 | "Solace: Connected" |
| NAVIGATING | ".." | #F59E0B | "Solace: Navigating..." |
| CLICKING | ".." | #F59E0B | "Solace: Clicking..." |
| TYPING | ".." | #F59E0B | "Solace: Typing..." |
| RECORDING | "REC" | #DC2626 | "Solace: Recording" |
| ERROR | "!" | #B91C1C | "Solace: Error" |

---

## Key Design Decisions

### D1: Badge updates are synchronous side effects of state transitions
- `transitionTabState()` from A1 calls `updateBadge()` internally
- No separate event system needed
- Keeps badge always in sync with state

### D2: Per-tab badges use Chrome's `tabId` parameter
- `chrome.action.setBadgeText({ tabId, text })` -- per-tab, not global
- `chrome.action.setBadgeBackgroundColor({ tabId, color })` -- per-tab
- `chrome.action.setTitle({ tabId, title })` -- per-tab
- This ensures tab 1 can show "ON" while tab 2 shows "ERROR"

### D3: NAVIGATING/CLICKING/TYPING all show same "in-progress" badge
- Uses ".." text with amber color for all action states
- Title distinguishes which action: "Navigating...", "Clicking...", "Typing..."
- Simpler visual -- user sees "something is happening" without needing to distinguish

### D4: RECORDING gets its own distinct badge
- Red "REC" badge (different from ERROR's "!")
- Provides clear recording indicator
- Matches existing `setBadge("REC", "#FF0000")` pattern in current code

### D5: Badge cleared on tab removal
- `chrome.tabs.onRemoved` listener calls `chrome.action.setBadgeText({ tabId, text: '' })`
- Prevents stale badges on closed tabs

---

## Integration Points

### File: `canon/prime-browser/extension/background.js` (MODIFY)

Functions to add:
```javascript
function updateBadge(tabId, state) {
    const config = BADGE_CONFIG[state] || BADGE_CONFIG.IDLE;
    chrome.action.setBadgeText({ tabId, text: config.text });
    chrome.action.setBadgeBackgroundColor({ tabId, color: config.color });
}

function updateTitle(tabId, state) {
    const titles = {
        IDLE: 'Solace: Disconnected',
        CONNECTED: 'Solace: Connected',
        NAVIGATING: 'Solace: Navigating...',
        CLICKING: 'Solace: Clicking...',
        TYPING: 'Solace: Typing...',
        RECORDING: 'Solace: Recording',
        ERROR: 'Solace: Error',
    };
    chrome.action.setTitle({ tabId, title: titles[state] || 'Solace' });
}
```

Hook into A1's `transitionTabState()`:
```javascript
function transitionTabState(tabId, newState, reason) {
    // ... validation from A1 ...
    // After successful transition:
    updateBadge(tabId, newState);
    updateTitle(tabId, newState);
}
```

Modify existing code:
- Remove the 4 standalone `setBadge()` calls scattered through `connect()`, `startRecording()`, `stopRecording()`, `ws.onerror`
- Replace with centralized `updateBadge()` through state transitions
- Remove `setBadge()` helper function (replaced by `updateBadge`)

---

## Function Inventory

| Function | File | Purpose |
|----------|------|---------|
| `updateBadge(tabId, state)` | background.js | Set badge text + color from config |
| `updateTitle(tabId, state)` | background.js | Set tooltip title per tab |
| `BADGE_CONFIG` | background.js | State-to-visual mapping constant |

**Estimated LOC:** ~40 (new functions) + ~20 (removing old setBadge calls) = **~60 LOC net change**

---

## Complexity Assessment

- **Difficulty:** Low
- **Risk:** Low (Chrome API is well-documented, pattern validated in production)
- **Day estimate:** 0.5 days
- **Dependencies:** A1 must provide `transitionTabState()` hook
