# TEST SPECIFICATION: Phase 2 - Episode Recording

> **Star:** SOLACE_BROWSER_PHASE_2
> **Channel:** 11 (Testing)
> **Status:** LOCKED -- READY FOR SKEPTIC
> **Auth:** 65537 | **Verification Ladder:** OAuth(39,63,91) -> 641 -> 274177 -> 65537
> **Total Tests:** 75

---

## Test Infrastructure

### Framework
- **Runner:** Puppeteer (drives Chromium with extension loaded)
- **Assertions:** Jest or pytest
- **Validation:** JSON Schema (EPISODE_SCHEMA.json)
- **Fixtures:** Static HTML test pages (deterministic DOM)

### Test Page Setup

Create `test_pages/` directory with deterministic HTML files:

```
test_pages/
  simple_form.html      # Basic form with all input types
  navigation.html       # Page with links for navigate tests
  interactive.html      # Buttons, dropdowns, checkboxes
  large_dom.html        # 10,000+ elements for stress tests
  dynamic.html          # JavaScript-driven DOM changes
  landmark.html         # ARIA landmarks for snapshot testing
```

### Extension Loading

```javascript
const browser = await puppeteer.launch({
  headless: false,
  args: [
    `--load-extension=${EXTENSION_PATH}`,
    '--no-first-run',
    '--disable-extensions-except=' + EXTENSION_PATH
  ]
});
```

---

## OAuth Foundation (39, 63, 91) -- 25 Tests

### Care (39) -- 10 Tests

Basic sanity: "Does it work at all?"

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 1 | `care_001_start_recording` | Recording can be started | `startRecordingV2()` returns session_id |
| 2 | `care_002_stop_recording` | Recording can be stopped | `stopRecordingV2()` returns episode_id |
| 3 | `care_003_episode_structure` | Episode has required fields | JSON validates against EPISODE_SCHEMA.json |
| 4 | `care_004_actions_array` | Actions array is initialized | `episode.actions` is array, length >= 0 |
| 5 | `care_005_metadata_captured` | Metadata fields populated | `browser_version`, `screen_size`, `locale` all present |
| 6 | `care_006_episode_saved` | Episode persists to storage | `loadEpisode(id)` returns same episode |
| 7 | `care_007_single_action` | One click = one action recorded | `episode.actions.length === 2` (NAVIGATE + CLICK) |
| 8 | `care_008_timestamp_format` | Timestamps are ISO 8601 | Regex: `/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/` |
| 9 | `care_009_episode_id_format` | Episode ID matches pattern | Regex: `/^ep_\d{8}_\d{3}$/` |
| 10 | `care_010_json_valid` | Episode is valid JSON | `JSON.parse(JSON.stringify(episode))` roundtrips |

### Bridge (63) -- 8 Tests

Connectivity: "Do the parts connect?"

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 11 | `bridge_001_ipc_start` | START_CAPTURE reaches content | Content responds with CAPTURE_STARTED |
| 12 | `bridge_002_ipc_stop` | STOP_CAPTURE reaches content | Content responds with CAPTURE_STOPPED + actions |
| 13 | `bridge_003_snapshot_v2` | TAKE_SNAPSHOT_V2 returns structured DOM | Response has `dom.tag`, `landmarks`, `metadata` |
| 14 | `bridge_004_event_listeners` | Click listener fires | `handleClick` called on button click |
| 15 | `bridge_005_dom_observer` | MutationObserver detects changes | `getDOMMutationCount() > 0` after DOM mutation |
| 16 | `bridge_006_action_to_bg` | ACTION_CAPTURED reaches background | Background receives action with snapshots |
| 17 | `bridge_007_episode_saved` | Episode writes to chrome.storage | `chrome.storage.local.get()` returns episode data |
| 18 | `bridge_008_index_updated` | Episode index has new entry | `listEpisodes()` includes new episode |

### Stability (91) -- 7 Tests

Reliability: "Does it hold up?"

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 19 | `stability_001_100_actions` | 100 actions without crash | `episode.actions.length === 101` (NAVIGATE + 100) |
| 20 | `stability_002_cross_page` | Recording survives page navigation | Episode has NAVIGATE actions for each page |
| 21 | `stability_003_no_lost_actions` | All captured actions in episode | Content buffer count === background action count |
| 22 | `stability_004_state_machine` | State transitions are valid | No invalid transition errors in audit log |
| 23 | `stability_005_storage_robust` | Save + load roundtrips | `loadEpisode(saveEpisode(ep))` deep-equals `ep` |
| 24 | `stability_006_error_recovery` | Error state recoverable | After ERROR, can transition to IDLE and record again |
| 25 | `stability_007_deterministic` | Same actions = same episode structure | Two identical interaction sequences produce matching episode structure (excluding timestamps) |

---

## RIVAL-EDGE (641) -- 29 Tests

Edge cases for each action type.

### Navigate Tests (5)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 26 | `edge_nav_001_simple` | Simple URL navigation | Action type=NAVIGATE, value=URL |
| 27 | `edge_nav_002_fragment` | Hash fragment change (#anchor) | Action captures new URL with fragment |
| 28 | `edge_nav_003_back_forward` | Browser back/forward | `popstate` events captured as NAVIGATE |
| 29 | `edge_nav_004_redirect` | HTTP redirect (30x) | Final URL captured (not intermediate) |
| 30 | `edge_nav_005_first_null` | First action has null snapshot_before | `actions[0].snapshot_before === null` |

### Click Tests (6)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 31 | `edge_click_001_button` | Button click | `type=CLICK`, `target.structural.tag=button` |
| 32 | `edge_click_002_link` | Anchor link click | `type=CLICK`, `target.structural.tag=a` |
| 33 | `edge_click_003_hidden` | Click on hidden element | No action recorded (element not interactive/visible) |
| 34 | `edge_click_004_nested` | Click on nested span inside button | Target resolves to nearest interactive ancestor |
| 35 | `edge_click_005_non_interactive` | Click on plain div | No action recorded (not interactive) |
| 36 | `edge_click_006_role_button` | Click on `[role="button"]` div | Action recorded (INTERACTIVE_ROLES match) |

### Type Tests (6)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 37 | `edge_type_001_single_char` | Type one character | `type=TYPE`, `value.length === 1` |
| 38 | `edge_type_002_full_word` | Type "hello" | `value === "hello"` (debounced to 1 action) |
| 39 | `edge_type_003_special_chars` | Type `!@#$%` | Special chars preserved in value |
| 40 | `edge_type_004_textarea` | Type in textarea | `target.structural.tag === "textarea"` |
| 41 | `edge_type_005_clear_retype` | Clear field and retype | Two TYPE actions (clear + new text) |
| 42 | `edge_type_006_debounce` | Rapid typing = single action | 20 keystrokes in 200ms = 1 TYPE action |

### Select Tests (4)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 43 | `edge_select_001_dropdown` | Select dropdown option | `type=SELECT`, `value.selected_text` populated |
| 44 | `edge_select_002_change` | Change selection | `value.previous_value` is old, `value.selected_value` is new |
| 45 | `edge_select_003_multi` | Multi-select (if applicable) | Action recorded for change event |
| 46 | `edge_select_004_no_change` | Select same option | No action (no change event fires) |

### Submit Tests (4)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 47 | `edge_submit_001_button` | Submit via button click | `type=SUBMIT`, `value.fields` populated |
| 48 | `edge_submit_002_enter` | Submit via Enter key in input | `type=SUBMIT` recorded |
| 49 | `edge_submit_003_fields` | Form with 5 fields | `value.fields` has all 5 field names |
| 50 | `edge_submit_004_method` | POST form | `value.method === "POST"` |

### Snapshot Tests (4)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 51 | `edge_snap_001_structure` | Snapshot has dom/landmarks/metadata | All 3 top-level fields present |
| 52 | `edge_snap_002_allowed_attrs` | Only ALLOWED_ATTRS in dom.attrs | No `class`, `style`, `tabindex` in any node |
| 53 | `edge_snap_003_skip_tags` | No script/style in snapshot | No nodes with `tag === "script"` or `tag === "style"` |
| 54 | `edge_snap_004_landmarks` | ARIA landmarks extracted | `landmarks.length > 0` on page with `<nav>`, `<main>` |

---

## RIVAL-STRESS (274177) -- 18 Tests

Scaling, memory, reliability, concurrency.

### Scaling Tests (6)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 55 | `stress_scale_001_100_actions` | 100 consecutive clicks | All 100 actions in episode |
| 56 | `stress_scale_002_50_episodes` | Record 50 episodes sequentially | All 50 in index, all loadable |
| 57 | `stress_scale_003_large_dom` | Record on 10K element page | Snapshot completes within 50ms budget |
| 58 | `stress_scale_004_rapid_clicks` | 10 clicks in 1 second | All 10 actions captured (no drops) |
| 59 | `stress_scale_005_long_text` | Type 5000 characters | Single TYPE action with full text |
| 60 | `stress_scale_006_mixed` | 20 of each action type (100 total) | 100 actions, correct type distribution |

### Memory Tests (4)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 61 | `stress_mem_001_100_actions` | Memory after 100 actions | Heap < 200MB (extension process) |
| 62 | `stress_mem_002_large_snapshots` | 50 snapshots of 5K-node page | No OOM, all snapshots valid |
| 63 | `stress_mem_003_long_recording` | 5-minute continuous recording | Memory stable (< 50% growth) |
| 64 | `stress_mem_004_episode_storage` | Store 20 episodes | chrome.storage.local usage < quota |

### Reliability Tests (4)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 65 | `stress_rel_001_page_reload` | Recording survives soft reload | Episode has actions from before and after |
| 66 | `stress_rel_002_tab_hide` | Recording while tab is hidden | Actions still captured on re-focus |
| 67 | `stress_rel_003_rapid_nav` | 5 navigations in 3 seconds | All navigation actions recorded |
| 68 | `stress_rel_004_error_continue` | Error in one action, rest continue | Episode has all actions except errored |

### Concurrency Tests (4)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 69 | `stress_conc_001_multi_tab` | Record 2 tabs simultaneously | Each tab's episode is isolated |
| 70 | `stress_conc_002_busy_page` | Record while page does heavy JS | Actions still captured, no freeze |
| 71 | `stress_conc_003_bg_snapshot` | Background snapshot during recording | On-demand snapshot works independently |
| 72 | `stress_conc_004_race_condition` | Start/stop rapid toggle | No orphaned state, clean recovery |

---

## GOD-APPROVAL (65537) -- 28 Tests

Phase B integration, end-to-end workflows, evidence.

### Phase B Integration (8)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 73 | `god_b_001_schema_valid` | Episode passes JSON Schema | `ajv.validate(schema, episode) === true` |
| 74 | `god_b_002_snapshot_format` | Snapshots match B1 input format | Snapshot has `dom`, `landmarks`, `metadata` |
| 75 | `god_b_003_action_types` | All 5 action types in enum | `['NAVIGATE','CLICK','TYPE','SELECT','SUBMIT']` |
| 76 | `god_b_004_timestamps` | All timestamps ISO 8601 with ms | Every `timestamp` field matches format |
| 77 | `god_b_005_determinism` | Same inputs = same output (modulo timestamps) | Structural equality on two identical recordings |
| 78 | `god_b_006_unicode` | Unicode text in TYPE action | CJK, emoji, RTL text preserved |
| 79 | `god_b_007_empty_episode` | 0-action episode (start/stop immediately) | Valid JSON, `actions: []`, schema passes |
| 80 | `god_b_008_export` | Episode exported to JSON file | File exists, parseable, matches stored episode |

### End-to-End Workflows (10)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 81 | `god_e2e_001_form_fill` | Navigate -> Type in 3 fields -> Submit | 5 actions (NAV + 3 TYPE + SUBMIT) |
| 82 | `god_e2e_002_search` | Navigate -> Type query -> Click search | 3 actions (NAV + TYPE + CLICK) |
| 83 | `god_e2e_003_multi_page` | Navigate 3 pages, interact on each | 6+ actions across 3 URLs |
| 84 | `god_e2e_004_dropdown_submit` | Select dropdown -> Submit form | 3 actions (NAV + SELECT + SUBMIT) |
| 85 | `god_e2e_005_login` | Type username -> Type password -> Click login | 4 actions |
| 86 | `god_e2e_006_checkbox` | Toggle checkbox -> Submit | CLICK on checkbox + SUBMIT |
| 87 | `god_e2e_007_textarea` | Type long text in textarea -> Submit | TYPE has full text, SUBMIT has fields |
| 88 | `god_e2e_008_link_chain` | Click link -> Click link -> Click link | 3 CLICK + 3 NAVIGATE actions |
| 89 | `god_e2e_009_mixed` | All 5 action types in one episode | All 5 types present |
| 90 | `god_e2e_010_real_page` | Record on Wikipedia (live page) | Episode valid, snapshots present |

### Phase A Compatibility (6)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 91 | `god_compat_001_bg_state` | Background state machine still works | `getTabState()` returns valid state |
| 92 | `god_compat_002_old_recording` | Phase A START_RECORDING still works | Backward compatible (falls through to V2) |
| 93 | `god_compat_003_old_snapshot` | `takeSnapshot()` still works | Old function still returns data |
| 94 | `god_compat_004_websocket` | WebSocket commands still work | PING/PONG, NAVIGATE, CLICK, TYPE via WS |
| 95 | `god_compat_005_popup` | Popup UI still functional | GET_STATUS returns recording state |
| 96 | `god_compat_006_badge` | Badge shows REC during recording | Badge text === "REC", color === "#DC2626" |

### Evidence (4)

| # | Test ID | Description | Assertion |
|---|---------|-------------|-----------|
| 97 | `god_evidence_001_version` | Episode has version field | `episode.version === "0.2.0"` |
| 98 | `god_evidence_002_index` | Episode index is consistent | All indexed episodes are loadable |
| 99 | `god_evidence_003_action_order` | Actions ordered by index | `actions[i].index === i` for all i |
| 100 | `god_evidence_004_snapshot_pair` | Every non-first action has both snapshots | `snapshot_before !== null && snapshot_after !== null` |

---

## Test Execution Order

```
Phase 1: OAuth (39, 63, 91) -- Must ALL pass before proceeding
  -> Run 25 tests
  -> Gate: 25/25 pass

Phase 2: Edge (641) -- Must ALL pass before proceeding
  -> Run 29 tests
  -> Gate: 29/29 pass

Phase 3: Stress (274177) -- Must ALL pass before proceeding
  -> Run 18 tests
  -> Gate: 18/18 pass

Phase 4: God (65537) -- Final approval
  -> Run 28 tests
  -> Gate: 28/28 pass

TOTAL: 75/75 pass = Phase 2 COMPLETE
```

---

## Success Criteria

Phase 2 testing is COMPLETE when:

1. **75/75 tests passing** (zero failures)
2. **Schema validation passes** (EPISODE_SCHEMA.json)
3. **Determinism verified** (same inputs -> same structure)
4. **Phase A compatibility** (existing extension features still work)
5. **No memory leaks** (stable under 5-minute recording)
6. **Snapshot performance** (< 50ms per capture)

---

**Auth:** 65537
**Northstar:** Phuc Forecast (DREAM -> FORECAST -> DECIDE -> ACT -> VERIFY)
**Verification:** OAuth(39,63,91) -> 641 -> 274177 -> 65537
