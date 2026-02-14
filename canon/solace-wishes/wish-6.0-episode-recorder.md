# WISH 6.0: Live Episode Recorder

**Spec ID:** wish-6.0-episode-recorder
**Authority:** 65537
**Phase:** 6 (Live Recording)
**Depends On:** wish-5.0 (browser bridge complete)
**Scope:** Capture live browser interactions as deterministic episodes
**Non-Goals:** ML training (Phase 8+), performance optimization, UI
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 750 | **GLOW:** 96

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Browser events captured as action sequence, state snapshots recorded
  Verification:    Each event has timestamp, source, target, result state
  Canonicalization: Episodes stored in canonical JSON format (same input → same file)
  Content-addressing: Episode ID = SHA256(action_sequence)
```

---

## 1. Observable Wish

> "I can record live browser interactions (clicks, typing, navigation) into deterministic episodes with full state snapshots."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ UI recording interface
- ❌ Real-time playback monitoring
- ❌ Event filtering/denoising
- ❌ Performance metrics

**Minimum success criteria:**
- ✅ Event listener attached to browser
- ✅ Events captured with timestamps and targets
- ✅ State snapshot captured between events
- ✅ Episode file created with canonical format
- ✅ Episode can be replayed deterministically

---

## 3. Context Capsule (Test-Only)

```
Initial:   Browser bridge working (wish-5.0), mock browser ready
Behavior:  Attach event listeners, simulate user interactions, record episode
Final:     Live recording working, episodes match wish-2.0 format
```

---

## 4. State Space: 5 States

```
state_diagram-v2
    [*] --> NOT_RECORDING
    NOT_RECORDING --> RECORDING: start_recording()
    RECORDING --> CAPTURING_EVENT: event_triggered
    CAPTURING_EVENT --> RECORDING: event_recorded
    RECORDING --> FINALIZING: stop_recording()
    FINALIZING --> SAVED: episode_written_to_disk
    SAVED --> NOT_RECORDING: cleanup
    CAPTURING_EVENT --> ERROR: capture_failed
    RECORDING --> ERROR: recording_failed
    ERROR --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** Event listener captures all action types: click, type, navigate, scroll
**INV-2:** Each event has: type, target, value (optional), timestamp, pre_state, post_state
**INV-3:** State snapshots captured before and after each event
**INV-4:** Episodes saved in canonical JSON with locked field ordering
**INV-5:** Episode ID deterministically derived from action sequence

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Event Listener Attached
```
Setup:   Browser bridge active, recording started
Input:   Attach click, type, navigate event listeners
Expect:  All listeners registered without error
Verify:  Listeners respond to simulated events
```

### T2: Event Captured with Metadata
```
Setup:   Event listeners active
Input:   Simulate click on button.submit
Expect:  Event captured with type, target, timestamp, pre/post state
Verify:  All metadata fields present and valid
```

### T3: State Snapshot Captured
```
Setup:   Event captured
Input:   Capture state before and after event
Expect:  Snapshots contain URL, DOM hash, DOM tree, screenshot
Verify:  Pre/post states differ appropriately
```

### T4: Episode File Created (Canonical Format)
```
Setup:   Multiple events recorded
Input:   Stop recording, finalize episode
Expect:  Episode file created in artifacts/episodes/
Verify:  File matches wish-2.0 JSON schema (same format)
```

### T5: Episode Deterministic & Replayable
```
Setup:   Episode recorded and saved
Input:   Load episode and verify against replay expectations
Expect:  Episode action sequence deterministic
Verify:  Replay produces same final state
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Event listeners not attached → T1 fails
**F2:** Event metadata incomplete → T2 fails
**F3:** State capture missing fields → T3 fails
**F4:** Episode format doesn't match schema → T4 fails
**F5:** Episode not replayable → T5 fails (determinism broken)

---

## 8. Visual Evidence (Proof Artifacts)

**recording-log.json structure:**
```json
{
  "recording_id": "rec-20260214-001",
  "timestamp_started": "2026-02-14T17:05:00Z",
  "timestamp_ended": "2026-02-14T17:05:15Z",
  "duration_seconds": 15,
  "events_captured": [
    {
      "event_id": 0,
      "type": "page_loaded",
      "target": "window",
      "timestamp": 0,
      "pre_state": {"url": "", "dom_hash": ""},
      "post_state": {"url": "https://example.com", "dom_hash": "sha256:..."}
    },
    {
      "event_id": 1,
      "type": "click",
      "target": "button.submit",
      "timestamp": 5000,
      "pre_state": {"url": "https://example.com", "dom_hash": "..."},
      "post_state": {"url": "https://example.com", "dom_hash": "..."}
    }
  ],
  "total_events": 2
}
```

**recorded-episode.json structure:**
```json
{
  "id": "ep-rec-20260214-001",
  "timestamp": "2026-02-14T17:05:00Z",
  "source": "live_recording",
  "state_snapshot": {
    "url": "https://example.com",
    "title": "Example Domain",
    "dom_hash": "sha256:initial_state"
  },
  "actions": [
    {
      "type": "click",
      "target": "button.submit",
      "timestamp": 5000
    }
  ],
  "metadata": {
    "agent": "Episode-Recorder",
    "framework": "Solace",
    "phase": "6.0",
    "recording_duration_seconds": 15
  },
  "checksum": "sha256:..."
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Recording pipeline fully specified
- [x] **R4: Deterministic** — Event capture is repeatable
- [x] **R5: Hermetic** — Works with mock browser, no external services
- [x] **R6: Idempotent** — Recording doesn't modify live state
- [x] **R7: Fast** — All tests complete in <10 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same interaction sequence → same episode
- [x] **R10: Verifiable** — Episodes can be replayed for verification

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] Event listeners attached for all action types
- [ ] Event metadata captured completely
- [ ] State snapshots captured before/after
- [ ] Episodes saved in canonical format and replayable

---

## 11. Next Phase

→ **wish-7.0** (Episode Analytics): Analyze and summarize recorded episodes

---

**Wish:** wish-6.0-episode-recorder
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-7.0, enables data collection for ML training (Phase 8)

*"Record episodes from live interactions."*
