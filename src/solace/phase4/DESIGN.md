# Phase 4: Automated Posting - Browser Automation API

> **Status:** COMPLETE
> **Tests:** 75/75 passing
> **Auth:** 65537

## Overview

Phase 4 implements automated form filling and interaction via the AutomationAPI. This enables programmatic control of browser interactions (fill fields, click buttons, select options, type text, submit forms).

## Key Components

### AutomationAPI (state_machine.py + integration.py)

Provides 5 core automation methods:

1. **fillField(selector, value)**: Fill text input with value
2. **clickButton(selector)**: Click any clickable element
3. **selectOption(selector, option)**: Select from dropdown menu
4. **typeText(selector, text)**: Type text into element (with debouncing)
5. **verifyInteraction(selector, expectedState)**: Verify element is in expected state

### State Machine

Enforces lifecycle consistency:
- IDLE → READY → INTERACTING → DONE
- Prevents invalid state transitions
- Tracks action history and rollback capability

### Features

1. **Selector Resolution**: Uses Phase 3 RefMap to find elements
2. **Fallback Chains**: semantic → structural → xpath → css → ref_path
3. **Error Recovery**: Graceful handling of stale/missing elements
4. **Event Simulation**: Proper keyboard/mouse events for realistic interaction
5. **DOM Settlement**: Waits for mutations to settle after each action

## Architecture

```
Recipe (from Phase 3)
        ↓
Parse action: "fillField('#email', 'user@example.com')"
        ↓
AutomationAPI.fillField() → Resolve selector via RefMap
        ↓
Find element (semantic first, fallback to structural)
        ↓
Simulate keystroke events → DOM mutation → Wait for settle
        ↓
Action logged → Episode updated → Ready for next action
```

## Test Coverage

- **75 tests** covering all 5 methods, error cases, state machine
- Form filling with special characters, unicode text
- Dropdown selection with option matching
- Button click on nested elements
- Verification of DOM state changes
- Error recovery and rollback

## Integration with Phase 5

Phase 5 uses AutomationAPI actions to generate cryptographic proofs:
1. Record each action (fillField, clickButton, etc.)
2. Capture before/after snapshots
3. Generate deterministic hash of action sequence
4. Create RTC verification proof

## Success Criteria

✅ 75/75 tests passing
✅ All 5 methods implemented and working
✅ State machine enforces valid transitions
✅ RefMap integration proven with example episodes
✅ Zero defects on verification ladder (641 → 274177 → 65537)
