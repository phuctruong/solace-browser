# WISH 15.0: Multi-Tab Navigation & Context Preservation

**Spec ID:** wish-15.0-multitab-navigation
**Authority:** 65537
**Phase:** 15 (Multi-Context Automation)
**Depends On:** wish-14.0 (form filling complete)
**Scope:** Switch between tabs, preserve context, handle window handles
**Non-Goals:** Browser window management, process-level control
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 1000 | **GLOW:** 112+

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Tab switching is deterministically trackable
  Verification:    Each tab state preserved and restorable
  Canonicalization: Tab context stored in canonical JSON
  Content-addressing: Tab ID = SHA256(window_handle + tab_index)
```

---

## 1. Observable Wish

> "I can switch between multiple browser tabs, preserve context across tabs, handle new window opens, and execute complex multi-tab workflows deterministically."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ Browser window management (OS-level)
- ❌ Process management
- ❌ Headless mode window spawning
- ❌ Window position/size manipulation

**Minimum success criteria:**
- ✅ Get all open tabs/windows
- ✅ Switch to specific tab by handle/index
- ✅ Preserve tab context (cookies, storage, variables)
- ✅ Handle new window open events
- ✅ Execute sequence across multiple tabs
- ✅ Close tabs safely

---

## 3. Context Capsule (Test-Only)

```
Initial:   Form automation active (wish-14.0)
Behavior:  Open new tabs, switch context, execute multi-tab workflows
Final:     Complex multi-tab automation possible, context deterministic
```

---

## 4. State Space: 6 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> DISCOVERING: discover_tabs()
    DISCOVERING --> TRACKING: tabs_found
    TRACKING --> SWITCHING: switch_tab()
    SWITCHING --> EXECUTING: tab_active
    EXECUTING --> PRESERVING: context_saved
    PRESERVING --> COMPLETE: workflow_done
    SWITCHING --> ERROR: switch_failed
    ERROR --> [*]
    COMPLETE --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** All open tabs discovered and tracked by handle
**INV-2:** Tab switching instantaneous and deterministic
**INV-3:** Context preserved across tab switches (cookies, storage)
**INV-4:** New window opens detected and handled
**INV-5:** Multi-tab workflows execute in defined order

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Tab Discovery
```
Setup:   Browser with multiple tabs open
Input:   Discover all open tabs
Expect:  3+ tabs found and tracked
Verify:  Tab list includes handles, titles, URLs
```

### T2: Tab Switching
```
Setup:   Tabs discovered, context saved
Input:   Switch to tab 2, execute action, switch to tab 1
Expect:  Tab switching successful, actions isolated
Verify:  Each tab shows correct content after switch
```

### T3: Context Preservation
```
Setup:   Set variable in tab 1, switch to tab 2
Input:   Preserve context (cookies, storage) across switch
Expect:  Context intact when returning to tab 1
Verify:  Variables and state match original values
```

### T4: New Window Handling
```
Setup:   Tab automation active
Input:   Trigger action that opens new window/tab
Expect:  New window detected and added to tab list
Verify:  New window tracked, can switch to it
```

### T5: Multi-Tab Workflow
```
Setup:   3 tabs ready, context preserved
Input:   Execute workflow: tab1→tab2→tab3→tab1
Expect:  All actions execute in correct tab order
Verify:  Workflow complete, all assertions pass
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Tab discovery incomplete → T1 fails, missing tabs
**F2:** Tab switching fails → T2 fails, action on wrong tab
**F3:** Context lost on switch → T3 fails, state corrupted
**F4:** New window not detected → T4 fails, untracked window
**F5:** Multi-tab workflow fails → T5 fails, execution order wrong

---

## 8. Visual Evidence (Proof Artifacts)

**tab-discovery.json structure:**
```json
{
  "discovery_id": "disc-20260214-001",
  "timestamp": "2026-02-14T18:10:00Z",
  "tabs": [
    {
      "tab_id": "tab-001",
      "handle": "CDwindow-ABC123",
      "title": "Home",
      "url": "https://example.com",
      "active": true
    }
  ],
  "total_tabs": 3,
  "discovery_complete": true
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Multi-tab navigation pipeline fully specified
- [x] **R4: Deterministic** — Tab switching reproducible
- [x] **R5: Hermetic** — No external services
- [x] **R6: Idempotent** — Tab navigation doesn't modify content
- [x] **R7: Fast** — All tests complete in <20 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases word-for-word
- [x] **R9: Reproducible** — Same multi-tab sequence → same results
- [x] **R10: Verifiable** — Tab reports prove all switches successful

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Tab discovery complete
- [ ] Tab switching works
- [ ] Context preserved
- [ ] New windows handled
- [ ] Multi-tab workflow succeeds

---

## 11. Next Phase

→ **wish-16.0** (Screenshot & Visual Verification): Capture and compare visual state

---

**Wish:** wish-15.0-multitab-navigation
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-16.0, enables complex workflows

*"Multiple tabs, one deterministic mind."*
