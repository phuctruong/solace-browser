# DESIGN: Phase 2 - Episode Recording Architecture

> **Star:** SOLACE_BROWSER_PHASE_2
> **Channel:** 3 (Design & Architecture)
> **Status:** DESIGN COMPLETE -- READY FOR SOLVER
> **Phase:** 2 (Episode Recording)
> **Auth:** 65537 | **Northstar:** Phuc Forecast

---

## 1. Problem Statement

### Current State (Phase A Extension)

Phase A's Chrome extension (`canon/prime-browser/extension/`) records episodes via WebSocket commands from the CLI. The `background.js` has:

- Per-tab state machine (7 states: IDLE, CONNECTED, NAVIGATING, CLICKING, TYPING, RECORDING, ERROR)
- `logAction()` appends raw action objects `{type, data, timestamp}` to `tabActionLogs` Map
- `stopRecording()` bundles actions into a basic episode: `{session_id, domain, start_time, end_time, actions}`
- `content.js` has `takeSnapshot()` returning HTML hash + a11y tree (32-bit non-crypto hash)
- No structured DOM tree in snapshots (regex cleaning only via `canonicalizeDOM()`)
- No before/after snapshot pairing per action
- No semantic+structural dual selectors
- Episodes are raw traces, not Phase B compatible

### Target State (Phase 2)

Episode recording that:
1. Captures 5 action types: NAVIGATE, CLICK, TYPE, SELECT, SUBMIT
2. Creates before/after canonical snapshots per action (Phase B1 compatible)
3. Extracts semantic + structural element identifiers per action
4. Serializes to Phase B episode format (compatible with B1 canonicalization + B2 compiler)
5. Stores episodes to `~/.solace/browser/episodes/`

---

## 2. Architecture Decision: Extension-First

### Decision

**Use the Chrome Extension architecture (Manifest V3), NOT Chromium renderer process patches.**

### Justification

| Factor | Renderer Process (C++) | Extension (MV3 JS) |
|--------|----------------------|---------------------|
| DOM access | Blink C++ internals | content script (full DOM API) |
| Build time | 20-60 min recompile | Instant reload |
| Maintenance | Must rebase on Chromium HEAD | Independent of browser version |
| Phase A reuse | None (different layer) | Direct (extend background.js + content.js) |
| MutationObserver | Must hook Blink C++ | Standard Web API |
| Event capture | Custom C++ hooks | Standard addEventListener |
| Debugging | C++ debugger, complex | Chrome DevTools, trivial |
| Phase B compat | Custom C++ serialization | JavaScript, same as B1/B2 designs |
| Risk | HIGH (C++ bugs = crashes) | LOW (sandboxed extension) |

The existing DESIGN initially proposed renderer process (Mojo IPC, `blink::Element`, etc.). This is **wrong** for Phase 2. Reasons:

1. **No C++ build infrastructure exists yet.** The `~/projects/solace-browser/source/` is stock Ungoogled Chromium with no custom patches. Adding C++ modules requires BUILD.gn integration, Mojo IDL definitions, and cross-process IPC plumbing.

2. **Phase A extension already works.** The extension already records, already has per-tab state machine, already captures snapshots. We extend it, not replace it.

3. **Phase B designs (B1, B2) are JavaScript/Python.** The canonicalization pipeline, the episode compiler -- all designed for JSON in/out. The extension outputs JSON natively.

4. **Iteration speed.** Extension changes take 1 second (reload). C++ changes take 20-60 minutes (recompile Chromium). For Phase 2's 80-hour budget, this is the difference between 100 iterations and 5.

### When to Go Native (Future Phases)

Native renderer hooks for:
- Sub-millisecond event capture (Phase 7+)
- Paint-level recording (screenshot/video)
- chrome:// page interaction
- Security-critical operations

None of these apply to Phase 2.

---

## 3. Component Architecture

```
                     SOLACE BROWSER (Ungoogled Chromium 145.0.7632.45)
                              |
                    Extension (Manifest V3)
                              |
                    +---------+---------+
                    |                   |
             background.js         content.js
             (Service Worker)      (Per-page)
                    |                   |
          +---------+--------+    +-----+------+------+
          |         |        |    |     |      |      |
     Recording  Episode   IPC   DOM   Event  Snapshot Element
     Manager    Storage  Bridge Hook  Capture  Engine   ID
          |         |        |    |     |      |      |
          +----+----+        +----+-----+------+------+
               |                       |
          Episode JSON          Action + Snapshot Pair
          (~/.solace/           (before/after per action)
           browser/
           episodes/)
```

### 3.1 Content Script Layer (content.js extensions)

These are NEW functions added to the existing `content.js` (429 lines currently).

#### A. DOMHook -- MutationObserver Manager

State machine:
```
STATE_SET    = { IDLE, OBSERVING, PAUSED }
TRANSITIONS  = {
  IDLE:      [OBSERVING],
  OBSERVING: [PAUSED, IDLE],
  PAUSED:    [OBSERVING, IDLE]
}
FORBIDDEN    = { IDLE -> PAUSED }
```

Purpose: Global MutationObserver that tracks DOM mutations between user actions. Used to detect page-driven changes vs user-driven changes.

Configuration:
```javascript
const MUTATION_CONFIG = {
  childList: true,
  attributes: true,
  characterData: true,
  subtree: true,
  attributeOldValue: true,
  characterDataOldValue: true
};
```

Key function:
```javascript
// Returns mutation count since last reset
function getDOMMutationCount() -> number
// Resets mutation counter
function resetDOMMutations() -> void
```

#### B. EventCapture -- User Interaction Listeners

Captures user interactions in the capture phase (before page handlers can stopPropagation):

```javascript
// Listener registration (capture phase = true)
document.addEventListener('click',    handleClick,    true);
document.addEventListener('input',    handleInput,    true);
document.addEventListener('change',   handleChange,   true);
document.addEventListener('submit',   handleSubmit,   true);
window.addEventListener('popstate',   handleNavigate, true);
window.addEventListener('hashchange', handleNavigate, true);
```

Interactive element filter (for CLICK only):
```javascript
const INTERACTIVE_TAGS = new Set([
  'A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA',
  'SUMMARY', 'DETAILS', 'LABEL'
]);
const INTERACTIVE_ROLES = new Set([
  'button', 'link', 'tab', 'menuitem', 'option',
  'checkbox', 'radio', 'switch', 'combobox'
]);
```

TYPE debounce: Collect input events for 500ms after last keystroke, then emit a single TYPE action with the full value.

#### C. SnapshotEngine -- Structured DOM Capture

Phase B1-compatible structured DOM traversal (replaces the old regex-based `canonicalizeDOM()`):

```javascript
function captureStructuredDOM(root = document.body) {
  return {
    tag: root.tagName.toLowerCase(),
    attrs: extractAllowedAttrs(root),
    children: Array.from(root.children).map(c => captureStructuredDOM(c)),
    text: extractDirectText(root)
  };
}
```

Attribute policy (aligned with B1 DESIGN-B1-SNAPSHOT-CANONICALIZATION.md):

```javascript
const ALLOWED_ATTRS = Object.freeze(new Set([
  'id', 'name', 'type', 'href', 'src', 'alt', 'title',
  'role', 'aria-label', 'aria-describedby', 'aria-expanded',
  'aria-hidden', 'aria-selected', 'aria-checked',
  'data-testid', 'data-qa', 'data-refid',
  'placeholder', 'value', 'action', 'method',
  'for', 'target', 'rel'
]));

const STRIP_ATTRS = Object.freeze(new Set([
  'class', 'style', 'tabindex', 'draggable',
  'data-reactid', 'data-react-checksum'
]));
```

Snapshot output format:
```json
{
  "version": "0.2.0",
  "url": "https://example.com/page",
  "timestamp": "2026-02-14T12:34:56.789Z",
  "viewport": { "width": 1920, "height": 1080 },
  "dom": {
    "tag": "body",
    "attrs": { "id": "main-body" },
    "children": [ ... ],
    "text": null
  },
  "landmarks": [
    { "role": "navigation", "label": "Main Nav", "ref_path": "body>nav:0" },
    { "role": "main", "label": null, "ref_path": "body>main:0" }
  ],
  "metadata": {
    "node_count": 1523,
    "max_depth": 12,
    "landmark_count": 2
  }
}
```

Performance constraints:
- Node limit: 200,000 (skip snapshot if exceeded, log warning)
- Max depth: 50 (truncate deeper nodes)
- Time budget: 50ms (abort and return partial if exceeded)
- JSON size cap: 5 MB per snapshot

#### D. ElementID -- Dual Identifier Extraction

For each interacted element, extract both semantic and structural IDs:

```javascript
function extractSemanticId(element) {
  return {
    aria_label:      element.getAttribute('aria-label'),
    aria_describedby: element.getAttribute('aria-describedby'),
    role:            element.getAttribute('role'),
    placeholder:     element.getAttribute('placeholder'),
    alt:             element.getAttribute('alt'),
    title:           element.getAttribute('title'),
    data_testid:     element.getAttribute('data-testid'),
    data_qa:         element.getAttribute('data-qa'),
    text:            element.innerText?.substring(0, 100) || null,
    name:            element.getAttribute('name'),
    type:            element.getAttribute('type'),
    for_attr:        element.getAttribute('for')
  };
}

function extractStructuralId(element) {
  return {
    css_selector: generateCSSSelector(element),
    xpath:        generateXPath(element),
    tag:          element.tagName.toLowerCase(),
    id:           element.id || null,
    nth_child:    getNthChildIndex(element),
    ref_path:     generateRefPath(element)
  };
}
```

`generateRefPath` produces paths like `"body>main:0>form:0>input:2"` using tag name and sibling index.

`generateCSSSelector` builds the shortest unique CSS selector by walking up the tree, preferring id > data-testid > class + nth-child.

`generateXPath` builds an absolute XPath from root.

### 3.2 Background Script Layer (background.js extensions)

#### A. RecordingManager -- Recording Lifecycle

State machine (extends Phase A's per-tab state machine):

```
STATE_SET    = { IDLE, RECORDING, FINALIZING, ERROR }
TRANSITIONS  = {
  IDLE:       [RECORDING],
  RECORDING:  [FINALIZING, ERROR],
  FINALIZING: [IDLE, ERROR],
  ERROR:      [IDLE]
}
FORBIDDEN    = { IDLE -> FINALIZING, IDLE -> ERROR }
```

Integration with Phase A: The existing VALID_TRANSITIONS in background.js already has RECORDING state. RecordingManager wraps the existing state machine and adds episode-level bookkeeping.

#### B. EpisodeStorage -- Disk Persistence

Storage location:
```
~/.solace/browser/episodes/
  episodes.jsonl          # One-line JSON index per episode
  ep_20260214_001.json    # Episode files
  ep_20260214_002.json
  ...
```

Filename convention: `ep_YYYYMMDD_NNN.json` where NNN is zero-padded sequence number per day.

Write process:
1. Serialize episode to JSON (`JSON.stringify` with sorted keys)
2. Use `chrome.storage.local` to persist (or native messaging host for filesystem)
3. Append index line to `episodes.jsonl`
4. Verify by reading back and comparing

Index format (`episodes.jsonl`, one line per episode):
```json
{"episode_id":"ep_20260214_001","url_start":"https://reddit.com","action_count":5,"created":"2026-02-14T12:34:56Z","file":"ep_20260214_001.json","size_bytes":245000}
```

#### C. IPC Bridge -- Content <-> Background Communication

Messages from background to content:
| Message | Payload | Purpose |
|---------|---------|---------|
| `START_CAPTURE` | `{ session_id, options }` | Enable listeners + observer |
| `STOP_CAPTURE` | `{ session_id }` | Disable listeners, return buffered actions |
| `TAKE_SNAPSHOT_V2` | `{ step }` | On-demand structured snapshot |

Messages from content to background:
| Message | Payload | Purpose |
|---------|---------|---------|
| `ACTION_CAPTURED` | `{ action, snapshot_before, snapshot_after }` | New action with snapshots |
| `CAPTURE_STARTED` | `{ session_id }` | Acknowledgment |
| `CAPTURE_STOPPED` | `{ session_id, action_count, actions }` | Final buffer on stop |
| `CAPTURE_ERROR` | `{ error, context }` | Error during capture |

Buffering: Content script buffers actions locally and sends each to background via `chrome.runtime.sendMessage()`. Background is authoritative. On STOP, content confirms with final buffer.

---

## 4. Snapshot Timing Per Action

```
User performs action (e.g., clicks button):
  1. EventCapture intercepts event (capture phase)
  2. PAUSE DOMHook (MutationObserver)
  3. captureStructuredDOM() -> snapshot_before
  4. Allow event to propagate (action executes)
  5. waitForDOMSettle(timeout=2000ms)
     - MutationObserver watches for 100ms of silence
     - Fallback: 2s max timeout
  6. captureStructuredDOM() -> snapshot_after
  7. RESUME DOMHook
  8. Build action object with both snapshots
  9. Send ACTION_CAPTURED to background
```

DOM settle detection:
```javascript
async function waitForDOMSettle(timeout = 2000) {
  return new Promise(resolve => {
    let timer = null;
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        observer.disconnect();
        resolve();
      }, 100);
    });
    observer.observe(document.body, {
      childList: true, subtree: true,
      attributes: true, characterData: true
    });
    // Initial settle check
    timer = setTimeout(() => {
      observer.disconnect();
      resolve();
    }, 100);
    // Hard timeout
    setTimeout(() => {
      observer.disconnect();
      resolve();
    }, timeout);
  });
}
```

---

## 5. Action Type Specifications

### NAVIGATE
- **Triggers:** `popstate`, `hashchange`, `chrome.webNavigation.onCompleted` (from background)
- **Value:** URL string
- **Target:** `{ semantic: { url }, structural: { url } }`
- **Special:** First action in episode has `snapshot_before: null`

### CLICK
- **Trigger:** `click` event (capture phase)
- **Filter:** Only interactive elements (INTERACTIVE_TAGS or INTERACTIVE_ROLES or `[role="button"]` ancestor)
- **Value:** `null`
- **Target:** Full semantic + structural identification of clicked element

### TYPE
- **Trigger:** `input` event, debounced 500ms
- **Value:** Full typed text string
- **Target:** Identification of input/textarea element
- **Special:** Debounce prevents one action per keystroke

### SELECT
- **Trigger:** `change` event on `<select>` elements
- **Value:** `{ selected_text, selected_value, previous_value }`
- **Target:** Identification of select element

### SUBMIT
- **Trigger:** `submit` event on `<form>` elements
- **Value:** `{ method, action, fields: { field_name: value } }`
- **Target:** Identification of form element

---

## 6. Episode Schema (Phase B Compatible)

See: `EPISODE_SCHEMA.json` for the complete JSON Schema.

Example:
```json
{
  "version": "0.2.0",
  "episode_id": "ep_20260214_001",
  "recording_date": "2026-02-14T12:34:56.000Z",
  "url_start": "https://reddit.com/r/test",
  "url_end": "https://reddit.com/r/test/submit",
  "actions": [
    {
      "index": 0,
      "type": "NAVIGATE",
      "timestamp": "2026-02-14T12:34:56.000Z",
      "target": {
        "semantic": { "url": "https://reddit.com/r/test" },
        "structural": { "url": "https://reddit.com/r/test" }
      },
      "value": "https://reddit.com/r/test",
      "snapshot_before": null,
      "snapshot_after": { "version": "0.2.0", "url": "...", "dom": {...}, "landmarks": [...], "metadata": {...} }
    },
    {
      "index": 1,
      "type": "CLICK",
      "timestamp": "2026-02-14T12:34:58.123Z",
      "target": {
        "semantic": { "role": "button", "aria_label": "Create Post", "text": "Create Post" },
        "structural": { "css_selector": "button.create-post-btn", "xpath": "//button[contains(@class,'create-post')]", "tag": "button", "ref_path": "body>main:0>div:2>button:0" }
      },
      "value": null,
      "snapshot_before": {...},
      "snapshot_after": {...}
    }
  ],
  "metadata": {
    "browser_version": "solace-browser-145.0.7632.45",
    "screen_size": { "width": 1920, "height": 1080 },
    "locale": "en-US",
    "action_count": 5,
    "duration_ms": 14500,
    "recording_mode": "user_interactive"
  }
}
```

### Schema Invariants

1. `episode_id` format: `ep_YYYYMMDD_NNN` (deterministic)
2. `actions` array ordered by `index` (0-based, contiguous, no gaps)
3. `type` in `{NAVIGATE, CLICK, TYPE, SELECT, SUBMIT}` (exactly 5 types)
4. Every action except first has both `snapshot_before` and `snapshot_after`
5. First action's `snapshot_before` is `null`
6. `target` always has both `semantic` and `structural` sub-objects
7. Timestamps are ISO 8601 with millisecond precision
8. `version` field for forward compatibility

---

## 7. Implementation Roadmap (for Solver)

### Step 1: Content Script -- SnapshotEngine (Day 1)

**File:** `canon/prime-browser/extension/content.js`
**Add:**
- `captureStructuredDOM(root)` -- recursive DOM traversal returning structured JSON
- `extractAllowedAttrs(element)` -- filter attributes per ALLOWED_ATTRS set
- `extractDirectText(node)` -- get direct text content (not children's)
- `extractLandmarks(root)` -- find ARIA landmarks in DOM tree
- `waitForDOMSettle(timeout)` -- MutationObserver-based settle detection

**Test:** Verify snapshot output matches Phase B1 schema on a simple HTML page.

### Step 2: Content Script -- ElementID (Day 1-2)

**File:** `canon/prime-browser/extension/content.js`
**Add:**
- `extractSemanticId(element)` -- extract all semantic attributes
- `extractStructuralId(element)` -- generate CSS selector, XPath, ref_path
- `generateCSSSelector(element)` -- shortest unique CSS selector
- `generateXPath(element)` -- absolute XPath from document
- `generateRefPath(element)` -- `tag:index` path notation
- `getNthChildIndex(element)` -- sibling index of same tag

**Test:** Verify selectors resolve back to the same element on a test page.

### Step 3: Content Script -- EventCapture + DOMHook (Day 2-3)

**File:** `canon/prime-browser/extension/content.js`
**Add:**
- Event listeners for all 5 action types (capture phase)
- `isInteractiveClick(event)` -- filter non-interactive clicks
- TYPE debounce logic (500ms buffer, flush on new element or timeout)
- DOMHook MutationObserver wrapper (start/pause/resume/stop)
- `handleClick()`, `handleInput()`, `handleChange()`, `handleSubmit()`, `handleNavigate()`
- Action buffer (array of pending actions)
- IPC: respond to `START_CAPTURE`, `STOP_CAPTURE` from background

**Test:** Verify all 5 action types are captured on a test page with forms.

### Step 4: Background Script -- RecordingManager (Day 3-4)

**File:** `canon/prime-browser/extension/background.js`
**Add:**
- `startRecordingV2(tabId, options)` -- sends START_CAPTURE to content, manages state
- `stopRecordingV2(tabId)` -- sends STOP_CAPTURE, collects actions, builds episode JSON
- `getCurrentEpisode(tabId)` -- returns in-progress episode
- Handle `ACTION_CAPTURED` messages from content script
- Episode-level bookkeeping (action indexing, timestamp tracking)

**Integration:** Wire into existing `handleCommand()` switch for START_RECORDING/STOP_RECORDING.

### Step 5: Background Script -- EpisodeStorage (Day 4-5)

**File:** `canon/prime-browser/extension/background.js`
**Add:**
- `saveEpisode(episode)` -- serialize and persist to chrome.storage.local
- `loadEpisode(episodeId)` -- read back from storage
- `listEpisodes()` -- return all episode metadata
- `exportEpisode(episodeId)` -- download as JSON file via chrome.downloads API
- Episode ID generation (`ep_YYYYMMDD_NNN`)
- JSONL index management

**Test:** Verify episodes persist across extension reload.

### Step 6: Integration Testing (Day 5-7)

- Wire all components together
- Test full flow: start recording -> interact -> stop -> verify episode JSON
- Run 641 edge tests (29 tests)
- Run 274177 stress tests (18 tests)
- Run 65537 god tests (28 tests)

### Step 7: Phase B Compatibility Verification (Day 7-8)

- Verify episode snapshots pass through B1 canonicalization pipeline
- Verify episodes can be consumed by B2 compiler
- Verify RTC: snapshot -> canonicalize -> de-canonicalize -> compare
- Verify semantic selectors work with B2 RefMap builder

---

## 8. File Locations

### Files Modified (extend existing)

| File | Changes |
|------|---------|
| `canon/prime-browser/extension/content.js` | Add: SnapshotEngine, ElementID, EventCapture, DOMHook (~300 lines) |
| `canon/prime-browser/extension/background.js` | Add: RecordingManager V2, EpisodeStorage, new IPC handlers (~200 lines) |
| `canon/prime-browser/extension/manifest.json` | Add: `downloads` permission if using chrome.downloads for export |

### Files Created

| File | Purpose |
|------|---------|
| `src/solace/phase2/DESIGN.md` | This document |
| `src/solace/phase2/API.md` | API specification |
| `src/solace/phase2/EPISODE_SCHEMA.json` | JSON Schema for episodes |
| `src/solace/phase2/IMPLEMENTATION.md` | Step-by-step guide |
| `src/solace/phase2/TEST_SPEC.md` | Test specification |

### No New C++ Files

Phase 2 does NOT modify `~/projects/solace-browser/source/`. No C++ compilation. No Mojo IPC. All JavaScript extension code.

---

## 9. Risk Assessment

### HIGH

| Risk | Impact | Mitigation |
|------|--------|------------|
| Snapshot blocks UI (>50ms) | User perceives lag | 50ms time budget; abort and return partial |
| Memory pressure from large DOMs | Tab crash | 200K node limit; stream snapshots to background |
| Event listeners conflict with page JS | Page breaks | Capture phase only; never stopPropagation |

### MEDIUM

| Risk | Impact | Mitigation |
|------|--------|------------|
| TYPE debounce loses rapid input | Missing text | 500ms debounce with flush-on-new-element |
| chrome.storage.local quota (10MB) | Cannot save episodes | Export to filesystem via chrome.downloads |
| MutationObserver misses changes | Incomplete after-snapshot | waitForDOMSettle with 2s hard timeout |

### LOW

| Risk | Impact | Mitigation |
|------|--------|------------|
| Content script not injected | No recording | Verify injection on START_CAPTURE; report error |
| Timestamp drift | Ordering issues | Use `performance.now()` for relative; `Date.now()` for absolute |

---

**Auth:** 65537
**Northstar:** Phuc Forecast (DREAM -> FORECAST -> DECIDE -> ACT -> VERIFY)
**Verification:** OAuth(39,63,91) -> 641 -> 274177 -> 65537
