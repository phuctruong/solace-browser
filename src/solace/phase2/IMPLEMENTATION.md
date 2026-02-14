# IMPLEMENTATION: Phase 2 - Episode Recording Step-by-Step Guide

> **Star:** SOLACE_BROWSER_PHASE_2
> **Channel:** 7 (Implementation)
> **Status:** READY FOR SOLVER
> **Auth:** 65537

---

## Prerequisites

**Solver has:**
- Architecture: `DESIGN.md` (Extension-First, not C++ renderer)
- API: `API.md` (all function signatures locked)
- Schema: `EPISODE_SCHEMA.json` (JSON Schema for validation)
- Tests: `TEST_SPEC.md` (75 tests across verification ladder)

**Solver does NOT need:**
- Chromium source code modifications
- C++ compilation
- Mojo IPC definitions
- BUILD.gn changes

**All work is in:**
- `~/projects/stillwater/canon/prime-browser/extension/content.js` (extend)
- `~/projects/stillwater/canon/prime-browser/extension/background.js` (extend)
- `~/projects/stillwater/canon/prime-browser/extension/manifest.json` (minor update)

---

## Step 1: SnapshotEngine (content.js) -- Day 1

### What to Build

Add to `content.js` after line 428 (after the existing `sleep()` function):

```javascript
// ============================================================
// PHASE 2: SNAPSHOT ENGINE (Phase B1 compatible)
// ============================================================
```

### Functions to Implement

#### 1a. `ALLOWED_ATTRS` and `STRIP_ATTRS` constants

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

const SKIP_TAGS = Object.freeze(new Set([
  'script', 'style', 'noscript', 'link', 'meta'
]));
```

#### 1b. `extractAllowedAttrs(element)`

```javascript
function extractAllowedAttrs(element) {
  const result = {};
  for (const attr of element.attributes) {
    if (ALLOWED_ATTRS.has(attr.name)) {
      result[attr.name] = attr.value;
    }
    // STRIP_ATTRS: silently skip
    // Unknown attrs: silently skip (warn in debug mode)
  }
  return result;
}
```

#### 1c. `extractDirectText(node)`

```javascript
function extractDirectText(node) {
  let text = '';
  for (const child of node.childNodes) {
    if (child.nodeType === Node.TEXT_NODE) {
      text += child.textContent;
    }
  }
  text = text.trim();
  return text.length > 0 ? text : null;
}
```

#### 1d. `captureStructuredDOM(root, depth, nodeCount)`

```javascript
const MAX_NODES = 200000;
const MAX_DEPTH = 50;
const SNAPSHOT_TIMEOUT_MS = 50;

function captureStructuredDOM(root, depth = 0, context = { count: 0, startTime: performance.now() }) {
  // Guard: depth limit
  if (depth > MAX_DEPTH) return null;

  // Guard: node limit
  if (context.count >= MAX_NODES) return null;

  // Guard: time budget
  if (performance.now() - context.startTime > SNAPSHOT_TIMEOUT_MS) return null;

  const tag = root.tagName.toLowerCase();

  // Skip non-content elements
  if (SKIP_TAGS.has(tag)) return null;

  context.count++;

  const node = {
    tag: tag,
    attrs: extractAllowedAttrs(root),
    children: [],
    text: extractDirectText(root)
  };

  for (const child of root.children) {
    const childNode = captureStructuredDOM(child, depth + 1, context);
    if (childNode) {
      node.children.push(childNode);
    }
  }

  return node;
}
```

#### 1e. `extractLandmarks(root)`

```javascript
const LANDMARK_ROLES = new Set([
  'navigation', 'main', 'banner', 'contentinfo',
  'complementary', 'form', 'region', 'search'
]);

const LANDMARK_TAGS = {
  'nav': 'navigation',
  'main': 'main',
  'header': 'banner',
  'footer': 'contentinfo',
  'aside': 'complementary',
  'form': 'form',
  'section': 'region'
};

function extractLandmarks(root, path = 'body', results = []) {
  const tag = root.tagName.toLowerCase();
  const role = root.getAttribute('role') || LANDMARK_TAGS[tag] || null;

  if (role && LANDMARK_ROLES.has(role)) {
    results.push({
      role: role,
      label: root.getAttribute('aria-label') || null,
      ref_path: path
    });
  }

  let childIndex = {};
  for (const child of root.children) {
    const childTag = child.tagName.toLowerCase();
    if (!childIndex[childTag]) childIndex[childTag] = 0;
    const childPath = `${path}>${childTag}:${childIndex[childTag]}`;
    childIndex[childTag]++;
    extractLandmarks(child, childPath, results);
  }

  return results;
}
```

#### 1f. `waitForDOMSettle(timeout)`

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
    timer = setTimeout(() => {
      observer.disconnect();
      resolve();
    }, 100);
    setTimeout(() => {
      observer.disconnect();
      resolve();
    }, timeout);
  });
}
```

#### 1g. `takeSnapshotV2(step)`

```javascript
function takeSnapshotV2(step) {
  const startTime = performance.now();
  const dom = captureStructuredDOM(document.body);
  const landmarks = extractLandmarks(document.body);
  const captureTime = performance.now() - startTime;

  // Count nodes
  function countNodes(node) {
    if (!node) return 0;
    return 1 + node.children.reduce((sum, c) => sum + countNodes(c), 0);
  }
  function maxDepth(node, d = 0) {
    if (!node || node.children.length === 0) return d;
    return Math.max(...node.children.map(c => maxDepth(c, d + 1)));
  }

  return {
    version: "0.2.0",
    url: window.location.href,
    timestamp: new Date().toISOString(),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight
    },
    dom: dom,
    landmarks: landmarks,
    metadata: {
      node_count: countNodes(dom),
      max_depth: maxDepth(dom),
      landmark_count: landmarks.length,
      step: step || undefined,
      capture_time_ms: Math.round(captureTime * 100) / 100
    }
  };
}
```

### Verification (Step 1)

Load the extension, navigate to a simple page, and run in DevTools console:
```javascript
// Should return structured JSON, not HTML
const snap = takeSnapshotV2("test");
console.log("Nodes:", snap.metadata.node_count);
console.log("Depth:", snap.metadata.max_depth);
console.log("Time:", snap.metadata.capture_time_ms, "ms");
console.log("Landmarks:", snap.landmarks.length);
```

---

## Step 2: ElementID (content.js) -- Day 1-2

### Functions to Implement

#### 2a. `extractSemanticId(element)`

See API.md for exact signature. Extract all semantic attributes from the element.

#### 2b. `getNthChildIndex(element)`

```javascript
function getNthChildIndex(element) {
  const parent = element.parentElement;
  if (!parent) return 0;
  const tag = element.tagName;
  let index = 0;
  for (const sibling of parent.children) {
    if (sibling === element) return index;
    if (sibling.tagName === tag) index++;
  }
  return index;
}
```

#### 2c. `generateRefPath(element)`

```javascript
function generateRefPath(element) {
  const parts = [];
  let current = element;
  while (current && current !== document.documentElement) {
    const tag = current.tagName.toLowerCase();
    const index = getNthChildIndex(current);
    parts.unshift(`${tag}:${index}`);
    current = current.parentElement;
  }
  return parts.join('>');
}
```

#### 2d. `generateCSSSelector(element)`

```javascript
function generateCSSSelector(element) {
  // Priority: #id > [data-testid] > tag.class:nth-child

  if (element.id) {
    return `#${CSS.escape(element.id)}`;
  }

  const testId = element.getAttribute('data-testid');
  if (testId) {
    return `[data-testid="${CSS.escape(testId)}"]`;
  }

  // Build path from root
  const parts = [];
  let current = element;
  while (current && current !== document.body && current !== document.documentElement) {
    let selector = current.tagName.toLowerCase();
    if (current.id) {
      selector = `#${CSS.escape(current.id)}`;
      parts.unshift(selector);
      break;
    }
    const parent = current.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter(
        s => s.tagName === current.tagName
      );
      if (siblings.length > 1) {
        const idx = siblings.indexOf(current) + 1;
        selector += `:nth-of-type(${idx})`;
      }
    }
    parts.unshift(selector);
    current = current.parentElement;
  }

  return parts.join(' > ');
}
```

#### 2e. `generateXPath(element)`

```javascript
function generateXPath(element) {
  const parts = [];
  let current = element;
  while (current && current.nodeType === Node.ELEMENT_NODE) {
    let index = 1;
    let sibling = current.previousElementSibling;
    while (sibling) {
      if (sibling.tagName === current.tagName) index++;
      sibling = sibling.previousElementSibling;
    }
    const tag = current.tagName.toLowerCase();
    parts.unshift(`${tag}[${index}]`);
    current = current.parentElement;
  }
  return '/' + parts.join('/');
}
```

#### 2f. `extractStructuralId(element)`

See API.md. Compose the above helpers.

### Verification (Step 2)

```javascript
// Click a button, extract IDs
const btn = document.querySelector('button');
const sem = extractSemanticId(btn);
const str = extractStructuralId(btn);
console.log("Semantic:", sem);
console.log("Structural:", str);
// Verify resolution: document.querySelector(str.css_selector) === btn
```

---

## Step 3: EventCapture + DOMHook (content.js) -- Day 2-3

### 3a. DOMHook State Machine

```javascript
let domHookState = 'IDLE';
let domObserver = null;
let mutationCount = 0;

function startDOMObserver() {
  if (domHookState !== 'IDLE') return;
  mutationCount = 0;
  domObserver = new MutationObserver((mutations) => {
    mutationCount += mutations.length;
  });
  domObserver.observe(document.body, MUTATION_CONFIG);
  domHookState = 'OBSERVING';
}

function pauseDOMObserver() {
  if (domHookState !== 'OBSERVING') return;
  domObserver.disconnect();
  domHookState = 'PAUSED';
}

function resumeDOMObserver() {
  if (domHookState !== 'PAUSED') return;
  domObserver.observe(document.body, MUTATION_CONFIG);
  domHookState = 'OBSERVING';
}

function stopDOMObserver() {
  if (domObserver) domObserver.disconnect();
  domObserver = null;
  domHookState = 'IDLE';
  mutationCount = 0;
}
```

### 3b. EventCapture State

```javascript
let captureActive = false;
let captureSessionId = null;
let actionBuffer = [];
let actionIndex = 0;

// TYPE debounce state
let typeDebounceTimer = null;
let typeBuffer = { element: null, startValue: '', currentValue: '', startTimestamp: null };
```

### 3c. Event Handlers

**handleClick:**
```javascript
async function handleClick(event) {
  if (!captureActive) return;
  if (!isInteractiveClick(event)) return;

  const element = event.target;
  pauseDOMObserver();
  const snapshotBefore = takeSnapshotV2('before_click');
  // Event propagates naturally (we're in capture phase, not preventing)
  await waitForDOMSettle();
  const snapshotAfter = takeSnapshotV2('after_click');
  resumeDOMObserver();

  const action = {
    index: actionIndex++,
    type: 'CLICK',
    timestamp: new Date().toISOString(),
    target: {
      semantic: extractSemanticId(element),
      structural: extractStructuralId(element)
    },
    value: null,
    snapshot_before: snapshotBefore,
    snapshot_after: snapshotAfter
  };

  actionBuffer.push(action);
  chrome.runtime.sendMessage({ type: 'ACTION_CAPTURED', action, snapshot_before: snapshotBefore, snapshot_after: snapshotAfter });
}
```

**handleInput (with debounce):**
```javascript
function handleInput(event) {
  if (!captureActive) return;
  const el = event.target;
  if (!['INPUT', 'TEXTAREA'].includes(el.tagName) && el.contentEditable !== 'true') return;

  if (typeDebounceTimer) clearTimeout(typeDebounceTimer);

  if (!typeBuffer.element || typeBuffer.element !== el) {
    if (typeBuffer.element) flushTypeAction();
    typeBuffer = {
      element: el,
      startValue: '',
      currentValue: el.value || el.textContent,
      startTimestamp: new Date().toISOString(),
      snapshotBefore: takeSnapshotV2('before_type')
    };
  } else {
    typeBuffer.currentValue = el.value || el.textContent;
  }

  typeDebounceTimer = setTimeout(flushTypeAction, 500);
}

async function flushTypeAction() {
  if (!typeBuffer.element) return;
  typeDebounceTimer = null;

  await waitForDOMSettle(500);
  const snapshotAfter = takeSnapshotV2('after_type');

  const action = {
    index: actionIndex++,
    type: 'TYPE',
    timestamp: typeBuffer.startTimestamp,
    target: {
      semantic: extractSemanticId(typeBuffer.element),
      structural: extractStructuralId(typeBuffer.element)
    },
    value: typeBuffer.currentValue,
    snapshot_before: typeBuffer.snapshotBefore,
    snapshot_after: snapshotAfter
  };

  actionBuffer.push(action);
  chrome.runtime.sendMessage({ type: 'ACTION_CAPTURED', action });

  typeBuffer = { element: null, startValue: '', currentValue: '', startTimestamp: null };
}
```

**handleChange (for SELECT):**
```javascript
async function handleChange(event) {
  if (!captureActive) return;
  const el = event.target;
  if (el.tagName !== 'SELECT') return;

  pauseDOMObserver();
  const snapshotBefore = takeSnapshotV2('before_select');
  await waitForDOMSettle();
  const snapshotAfter = takeSnapshotV2('after_select');
  resumeDOMObserver();

  const selectedOption = el.options[el.selectedIndex];
  const action = {
    index: actionIndex++,
    type: 'SELECT',
    timestamp: new Date().toISOString(),
    target: {
      semantic: extractSemanticId(el),
      structural: extractStructuralId(el)
    },
    value: {
      selected_text: selectedOption ? selectedOption.text : '',
      selected_value: el.value,
      previous_value: ''
    },
    snapshot_before: snapshotBefore,
    snapshot_after: snapshotAfter
  };

  actionBuffer.push(action);
  chrome.runtime.sendMessage({ type: 'ACTION_CAPTURED', action });
}
```

**handleSubmit:**
```javascript
async function handleSubmit(event) {
  if (!captureActive) return;
  const form = event.target;
  if (form.tagName !== 'FORM') return;

  pauseDOMObserver();
  const snapshotBefore = takeSnapshotV2('before_submit');

  // Extract form fields
  const fields = {};
  const formData = new FormData(form);
  for (const [key, value] of formData.entries()) {
    fields[key] = String(value);
  }

  // Let submit propagate, then capture after
  await waitForDOMSettle();
  const snapshotAfter = takeSnapshotV2('after_submit');
  resumeDOMObserver();

  const action = {
    index: actionIndex++,
    type: 'SUBMIT',
    timestamp: new Date().toISOString(),
    target: {
      semantic: extractSemanticId(form),
      structural: extractStructuralId(form)
    },
    value: {
      method: (form.method || 'GET').toUpperCase(),
      action: form.action || window.location.href,
      fields: fields
    },
    snapshot_before: snapshotBefore,
    snapshot_after: snapshotAfter
  };

  actionBuffer.push(action);
  chrome.runtime.sendMessage({ type: 'ACTION_CAPTURED', action });
}
```

**handleNavigate:**
```javascript
async function handleNavigate(event) {
  if (!captureActive) return;

  pauseDOMObserver();
  // snapshot_before was the previous page state
  // For navigation, we capture after the new page loads
  await waitForDOMSettle();
  const snapshotAfter = takeSnapshotV2('after_navigate');
  resumeDOMObserver();

  const action = {
    index: actionIndex++,
    type: 'NAVIGATE',
    timestamp: new Date().toISOString(),
    target: {
      semantic: { url: window.location.href },
      structural: { url: window.location.href }
    },
    value: window.location.href,
    snapshot_before: null,  // Previous page is gone
    snapshot_after: snapshotAfter
  };

  actionBuffer.push(action);
  chrome.runtime.sendMessage({ type: 'ACTION_CAPTURED', action });
}
```

### 3d. IPC Handlers (Content Script side)

Add to the existing `chrome.runtime.onMessage.addListener` switch:

```javascript
case "START_CAPTURE":
  captureActive = true;
  captureSessionId = request.session_id;
  actionBuffer = [];
  actionIndex = 0;
  startDOMObserver();

  // Register event listeners
  document.addEventListener('click', handleClick, true);
  document.addEventListener('input', handleInput, true);
  document.addEventListener('change', handleChange, true);
  document.addEventListener('submit', handleSubmit, true);
  window.addEventListener('popstate', handleNavigate, true);
  window.addEventListener('hashchange', handleNavigate, true);

  sendResponse({ type: 'CAPTURE_STARTED', session_id: captureSessionId });
  break;

case "STOP_CAPTURE":
  // Flush any pending type action
  if (typeBuffer.element) flushTypeAction();

  captureActive = false;
  stopDOMObserver();

  // Remove event listeners
  document.removeEventListener('click', handleClick, true);
  document.removeEventListener('input', handleInput, true);
  document.removeEventListener('change', handleChange, true);
  document.removeEventListener('submit', handleSubmit, true);
  window.removeEventListener('popstate', handleNavigate, true);
  window.removeEventListener('hashchange', handleNavigate, true);

  sendResponse({
    type: 'CAPTURE_STOPPED',
    session_id: captureSessionId,
    action_count: actionBuffer.length,
    actions: actionBuffer
  });

  captureSessionId = null;
  actionBuffer = [];
  actionIndex = 0;
  break;

case "TAKE_SNAPSHOT_V2":
  sendResponse(takeSnapshotV2(request.step));
  break;
```

---

## Step 4: RecordingManager (background.js) -- Day 3-4

### What to Build

Add to `background.js` after line 724 (after the existing `connect()` call):

### 4a. Episode Tracking State

```javascript
const episodeState = new Map(); // Map<tabId, { session_id, actions, startTime, url_start }>
```

### 4b. `startRecordingV2(tabId, options)`

```javascript
async function startRecordingV2(tabId, options = {}) {
  const sessionId = `session_${Date.now()}`;
  const startTime = new Date().toISOString();

  // Get current URL
  const tab = await chrome.tabs.get(tabId);

  episodeState.set(tabId, {
    session_id: sessionId,
    actions: [],
    startTime: startTime,
    url_start: tab.url,
    options: options
  });

  // Transition tab state
  transitionTabState(tabId, "RECORDING", "startRecordingV2");

  // Tell content script to start capturing
  await chrome.tabs.sendMessage(tabId, {
    type: "START_CAPTURE",
    session_id: sessionId,
    options: options
  });

  // Take initial snapshot (NAVIGATE action index 0)
  const initialSnapshot = await chrome.tabs.sendMessage(tabId, {
    type: "TAKE_SNAPSHOT_V2",
    step: "initial"
  });

  // Record initial NAVIGATE action
  const navigateAction = {
    index: 0,
    type: "NAVIGATE",
    timestamp: startTime,
    target: {
      semantic: { url: tab.url },
      structural: { url: tab.url }
    },
    value: tab.url,
    snapshot_before: null,
    snapshot_after: initialSnapshot
  };
  episodeState.get(tabId).actions.push(navigateAction);

  return { session_id: sessionId, started_at: startTime, tab_id: tabId };
}
```

### 4c. `stopRecordingV2(tabId)`

```javascript
async function stopRecordingV2(tabId) {
  const state = episodeState.get(tabId);
  if (!state) throw new Error(`No recording for tab ${tabId}`);

  // Get final state from content script
  const captureResult = await chrome.tabs.sendMessage(tabId, {
    type: "STOP_CAPTURE",
    session_id: state.session_id
  });

  // Reconcile: use content script actions (they have snapshots)
  // Background tracked actions are backup
  const actions = captureResult.actions || state.actions;

  // Get current URL
  const tab = await chrome.tabs.get(tabId);
  const endTime = new Date().toISOString();

  // Build episode
  const episodeId = await generateEpisodeId();
  const episode = {
    version: "0.2.0",
    episode_id: episodeId,
    recording_date: state.startTime,
    url_start: state.url_start,
    url_end: tab.url,
    actions: actions,
    metadata: {
      browser_version: `solace-browser-${navigator.userAgent.match(/Chrome\/([0-9.]+)/)?.[1] || 'unknown'}`,
      screen_size: { width: screen.width, height: screen.height },
      locale: navigator.language,
      action_count: actions.length,
      duration_ms: new Date(endTime) - new Date(state.startTime),
      recording_mode: "user_interactive"
    }
  };

  // Save episode
  await saveEpisode(episode);

  // Clean up
  episodeState.delete(tabId);
  transitionTabState(tabId, "CONNECTED", "stopRecordingV2");

  return {
    episode_id: episodeId,
    action_count: actions.length,
    duration_ms: episode.metadata.duration_ms,
    url_start: state.url_start,
    url_end: tab.url
  };
}
```

### 4d. Handle ACTION_CAPTURED from content

Add to the `chrome.runtime.onMessage.addListener`:

```javascript
if (request.type === "ACTION_CAPTURED") {
  const tabId = sender.tab.id;
  const state = episodeState.get(tabId);
  if (state) {
    state.actions.push(request.action);
  }
  return;
}
```

### 4e. Wire into existing handleCommand

Update the START_RECORDING and STOP_RECORDING cases:

```javascript
case "START_RECORDING":
  const startResult = await startRecordingV2(resolvedTabId, payload);
  sendMessage({
    type: "RECORDING_STARTED",
    ...startResult,
    request_id
  });
  break;

case "STOP_RECORDING":
  const stopResult = await stopRecordingV2(resolvedTabId);
  sendMessage({
    type: "RECORDING_STOPPED",
    ...stopResult,
    request_id
  });
  break;
```

---

## Step 5: EpisodeStorage (background.js) -- Day 4-5

### 5a. Episode ID Generation

```javascript
async function generateEpisodeId() {
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const key = `episode_counter_${today}`;

  const stored = await chrome.storage.local.get([key]);
  const sequence = (stored[key] || 0) + 1;
  await chrome.storage.local.set({ [key]: sequence });

  return `ep_${today}_${String(sequence).padStart(3, '0')}`;
}
```

### 5b. Save/Load/List

```javascript
async function saveEpisode(episode) {
  const key = `episode_${episode.episode_id}`;
  const json = JSON.stringify(episode, Object.keys(episode).sort(), 0);

  await chrome.storage.local.set({ [key]: episode });

  // Update index
  const indexKey = 'episode_index';
  const stored = await chrome.storage.local.get([indexKey]);
  const index = stored[indexKey] || [];
  index.push({
    episode_id: episode.episode_id,
    url_start: episode.url_start,
    action_count: episode.metadata.action_count,
    created: episode.recording_date,
    size_bytes: json.length
  });
  await chrome.storage.local.set({ [indexKey]: index });

  console.log(`[Solace] Episode saved: ${episode.episode_id} (${episode.metadata.action_count} actions)`);
  return episode.episode_id;
}

async function loadEpisode(episodeId) {
  const key = `episode_${episodeId}`;
  const stored = await chrome.storage.local.get([key]);
  return stored[key] || null;
}

async function listEpisodes() {
  const stored = await chrome.storage.local.get(['episode_index']);
  return stored['episode_index'] || [];
}

async function deleteEpisode(episodeId) {
  const key = `episode_${episodeId}`;
  await chrome.storage.local.remove([key]);

  const stored = await chrome.storage.local.get(['episode_index']);
  const index = (stored['episode_index'] || []).filter(e => e.episode_id !== episodeId);
  await chrome.storage.local.set({ 'episode_index': index });
  return true;
}

async function exportEpisode(episodeId) {
  const episode = await loadEpisode(episodeId);
  if (!episode) throw new Error(`Episode not found: ${episodeId}`);

  const json = JSON.stringify(episode, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  await chrome.downloads.download({
    url: url,
    filename: `${episodeId}.json`,
    saveAs: false
  });
}
```

---

## Step 6: Manifest Update

Add `downloads` permission to `manifest.json`:

```json
"permissions": [
  "scripting",
  "webRequest",
  "tabs",
  "storage",
  "debugger",
  "webNavigation",
  "activeTab",
  "downloads"
]
```

---

## Step 7: Integration Testing -- Day 5-7

### Manual Test Flow

1. Load extension in Chromium (chrome://extensions -> Load unpacked)
2. Navigate to a test page (e.g., a local HTML form)
3. Open DevTools -> Background page console
4. Start recording:
   ```javascript
   // From popup or background console:
   startRecordingV2(TAB_ID, { domain: "test" });
   ```
5. Interact with the page (click buttons, type in fields, submit forms)
6. Stop recording:
   ```javascript
   const result = await stopRecordingV2(TAB_ID);
   console.log(result);
   ```
7. Verify episode:
   ```javascript
   const ep = await loadEpisode(result.episode_id);
   console.log("Actions:", ep.actions.length);
   console.log("First action:", ep.actions[0].type);
   // Verify snapshot structure
   console.log("Snapshot nodes:", ep.actions[0].snapshot_after.metadata.node_count);
   ```

### Automated Test Setup

See TEST_SPEC.md for the full 75-test verification ladder.

Test framework: Puppeteer or Playwright driving a Chromium instance with the extension loaded.

```bash
# Launch Chromium with extension
chromium --load-extension=./canon/prime-browser/extension/ --no-first-run

# Run tests
pytest tests/phase2/ -v
```

---

## Compilation Flags

No C++ compilation needed. However, if loading the extension into Solace Browser (custom build):

```bash
# From ~/projects/solace-browser/
# The extension is loaded at runtime, not compiled in
./out/Release/chrome --load-extension=~/projects/stillwater/canon/prime-browser/extension/
```

For development, use any Chromium/Chrome browser with developer mode enabled.

---

## Success Criteria (Phase 2 Complete)

1. All 5 action types captured (NAVIGATE, CLICK, TYPE, SELECT, SUBMIT)
2. Before/after snapshots per action (structured DOM, not HTML string)
3. Semantic + structural dual selectors per element
4. Episodes serialize to Phase B schema (passes JSON Schema validation)
5. Episodes persist to chrome.storage.local
6. Episode export to JSON file works
7. All 75 tests pass (25 OAuth + 29 edge + 18 stress + 28 god)

---

**Auth:** 65537
**Northstar:** Phuc Forecast (DREAM -> FORECAST -> DECIDE -> ACT -> VERIFY)
