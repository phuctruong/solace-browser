# API Specification: Phase 2 - Episode Recording

> **Star:** SOLACE_BROWSER_PHASE_2
> **Channel:** 5 (API Design)
> **Status:** LOCKED -- READY FOR SOLVER
> **Auth:** 65537

---

## 1. Content Script API (content.js)

### 1.1 SnapshotEngine

#### `captureStructuredDOM(root?: Element): SnapshotDOM`

Recursively traverses the DOM tree from `root` (default: `document.body`) and returns a structured JSON representation compatible with Phase B1 canonicalization.

**Parameters:**
- `root` (Element, optional): DOM element to start traversal. Default: `document.body`

**Returns:** `SnapshotDOM` object:
```typescript
interface SnapshotDOM {
  tag: string;           // Lowercase tag name
  attrs: Record<string, string>;  // Filtered attributes (ALLOWED_ATTRS only)
  children: SnapshotDOM[];        // Recursive child nodes
  text: string | null;            // Direct text content (not descendants')
}
```

**Constraints:**
- Max node count: 200,000 (returns partial tree with `_truncated: true` if exceeded)
- Max depth: 50 (deeper nodes ignored)
- Time budget: 50ms (returns partial with `_timeout: true` if exceeded)
- Excludes `<script>`, `<style>`, `<noscript>` elements

**Example:**
```javascript
const dom = captureStructuredDOM(document.body);
// { tag: "body", attrs: {}, children: [...], text: null }
```

---

#### `takeSnapshotV2(step?: string): Snapshot`

High-level function that captures a complete Phase B1-compatible snapshot including DOM tree, landmarks, and metadata.

**Parameters:**
- `step` (string, optional): Label for this snapshot (e.g., "before_click", "after_navigate")

**Returns:** `Snapshot` object:
```typescript
interface Snapshot {
  version: "0.2.0";
  url: string;
  timestamp: string;     // ISO 8601 with ms
  viewport: { width: number; height: number };
  dom: SnapshotDOM;
  landmarks: Landmark[];
  metadata: {
    node_count: number;
    max_depth: number;
    landmark_count: number;
    step?: string;
    capture_time_ms: number;
  };
}

interface Landmark {
  role: string;          // ARIA role
  label: string | null;  // aria-label
  ref_path: string;      // e.g., "body>nav:0"
}
```

**Example:**
```javascript
const snap = takeSnapshotV2("before_click");
// { version: "0.2.0", url: "https://...", dom: {...}, landmarks: [...], metadata: {...} }
```

---

#### `extractAllowedAttrs(element: Element): Record<string, string>`

Extracts only attributes in the ALLOWED_ATTRS set from an element.

**Parameters:**
- `element` (Element): DOM element to extract attributes from

**Returns:** Object with attribute name -> value pairs. Only ALLOWED_ATTRS are included. STRIP_ATTRS and unknown attributes are excluded.

---

#### `extractDirectText(node: Node): string | null`

Extracts the direct text content of a node, excluding text from child elements.

**Parameters:**
- `node` (Node): DOM node

**Returns:** Trimmed text string or null if empty/whitespace-only

---

#### `extractLandmarks(root: Element): Landmark[]`

Finds ARIA landmarks (navigation, main, form, complementary, etc.) in the DOM tree.

**Parameters:**
- `root` (Element): Root element to search

**Returns:** Array of `Landmark` objects with role, label, and ref_path.

---

#### `waitForDOMSettle(timeout?: number): Promise<void>`

Waits for the DOM to settle (no mutations for 100ms) or until timeout.

**Parameters:**
- `timeout` (number, optional): Max wait time in ms. Default: 2000

**Returns:** Promise that resolves when DOM is settled or timeout reached.

---

### 1.2 ElementID

#### `extractSemanticId(element: Element): SemanticId`

Extracts all semantic identifiers from an element.

**Returns:**
```typescript
interface SemanticId {
  aria_label: string | null;
  aria_describedby: string | null;
  role: string | null;
  placeholder: string | null;
  alt: string | null;
  title: string | null;
  data_testid: string | null;
  data_qa: string | null;
  text: string | null;        // First 100 chars of innerText
  name: string | null;
  type: string | null;
  for_attr: string | null;
}
```

---

#### `extractStructuralId(element: Element): StructuralId`

Extracts structural identifiers (CSS selector, XPath, ref_path).

**Returns:**
```typescript
interface StructuralId {
  css_selector: string;
  xpath: string;
  tag: string;
  id: string | null;
  nth_child: number;
  ref_path: string;
}
```

---

#### `generateCSSSelector(element: Element): string`

Builds the shortest unique CSS selector for an element. Priority: `#id` > `[data-testid]` > `tag.class:nth-child(n)`.

---

#### `generateXPath(element: Element): string`

Builds an absolute XPath from document root to the element.

**Example:** `"/html/body/main/form/input[2]"`

---

#### `generateRefPath(element: Element): string`

Builds a ref_path notation using tag name and sibling index.

**Example:** `"body>main:0>form:0>input:2"`

---

### 1.3 EventCapture

#### Event Handler Signatures

```typescript
function handleClick(event: MouseEvent): void;
function handleInput(event: InputEvent): void;
function handleChange(event: Event): void;
function handleSubmit(event: SubmitEvent): void;
function handleNavigate(event: PopStateEvent | HashChangeEvent): void;
```

Each handler:
1. Checks if recording is active (`captureState === 'OBSERVING'`)
2. Filters non-interactive events (CLICK only)
3. Captures snapshot_before
4. Lets event propagate
5. Waits for DOM settle
6. Captures snapshot_after
7. Builds action object
8. Sends ACTION_CAPTURED to background

---

#### `isInteractiveClick(event: MouseEvent): boolean`

Returns true if the click target is an interactive element (button, link, input, etc.)

---

#### `flushTypeAction(): void`

Flushes the debounce buffer for TYPE actions. Called on timeout (500ms) or when a new element receives input.

---

### 1.4 DOMHook

#### `startDOMObserver(): void`

Starts the global MutationObserver. Transitions state: IDLE -> OBSERVING.

---

#### `stopDOMObserver(): void`

Stops the MutationObserver. Transitions state: OBSERVING/PAUSED -> IDLE.

---

#### `pauseDOMObserver(): void`

Temporarily disconnects the observer (for snapshot capture). State: OBSERVING -> PAUSED.

---

#### `resumeDOMObserver(): void`

Reconnects the observer after pause. State: PAUSED -> OBSERVING.

---

#### `getDOMMutationCount(): number`

Returns the number of mutations observed since the last reset.

---

#### `resetDOMMutations(): void`

Resets the mutation counter to 0.

---

### 1.5 IPC Handlers (Content Script)

#### `handleStartCapture(message: { session_id, options }): void`

Initializes EventCapture + DOMHook. Sends CAPTURE_STARTED back.

---

#### `handleStopCapture(message: { session_id }): void`

Tears down EventCapture + DOMHook. Returns final action buffer via CAPTURE_STOPPED.

---

## 2. Background Script API (background.js)

### 2.1 RecordingManager

#### `startRecordingV2(tabId: number, options?: RecordingOptions): SessionInfo`

Starts episode recording for a tab.

**Parameters:**
- `tabId` (number): Chrome tab ID
- `options` (RecordingOptions, optional):
```typescript
interface RecordingOptions {
  domain?: string;         // Domain hint for metadata
  max_actions?: number;    // Max actions before auto-stop (default: 1000)
  auto_snapshot?: boolean; // Auto-snapshot on navigate (default: true)
}
```

**Returns:**
```typescript
interface SessionInfo {
  session_id: string;    // "session_TIMESTAMP"
  started_at: string;    // ISO 8601
  tab_id: number;
}
```

**Side Effects:**
- Transitions tab state to RECORDING
- Sends START_CAPTURE to content script
- Initializes episode object

---

#### `stopRecordingV2(tabId: number): EpisodeSummary`

Stops recording and finalizes the episode.

**Returns:**
```typescript
interface EpisodeSummary {
  episode_id: string;
  action_count: number;
  duration_ms: number;
  file_path: string;    // Storage key or filename
  url_start: string;
  url_end: string;
}
```

**Side Effects:**
- Sends STOP_CAPTURE to content script
- Collects final action buffer
- Builds complete episode JSON
- Saves via EpisodeStorage
- Transitions tab state to CONNECTED

---

#### `getCurrentEpisode(tabId: number): Episode | null`

Returns the in-progress episode without stopping recording.

---

#### `getRecordingStatus(tabId: number): RecordingStatus`

```typescript
interface RecordingStatus {
  is_recording: boolean;
  session_id: string | null;
  action_count: number;
  duration_ms: number;
  state: "IDLE" | "RECORDING" | "FINALIZING" | "ERROR";
}
```

---

### 2.2 EpisodeStorage

#### `saveEpisode(episode: Episode): Promise<string>`

Serializes episode to JSON and persists to chrome.storage.local.

**Returns:** Episode ID (storage key)

---

#### `loadEpisode(episodeId: string): Promise<Episode | null>`

Loads an episode from storage by ID.

---

#### `listEpisodes(): Promise<EpisodeIndexEntry[]>`

Returns metadata for all stored episodes.

```typescript
interface EpisodeIndexEntry {
  episode_id: string;
  url_start: string;
  action_count: number;
  created: string;       // ISO 8601
  size_bytes: number;
}
```

---

#### `deleteEpisode(episodeId: string): Promise<boolean>`

Deletes an episode from storage. Returns true if found and deleted.

---

#### `exportEpisode(episodeId: string): Promise<void>`

Exports an episode as a JSON file download via chrome.downloads API.

Downloaded to: `~/Downloads/ep_YYYYMMDD_NNN.json`

---

#### `generateEpisodeId(): string`

Generates deterministic episode ID: `ep_YYYYMMDD_NNN`.

Sequence number NNN is zero-padded and increments per day. Uses chrome.storage.local to track the daily counter.

---

### 2.3 IPC Handlers (Background)

#### `handleActionCaptured(message, sender)`

Handles ACTION_CAPTURED from content script:
1. Validates action structure
2. Assigns sequential index
3. Appends to current episode

---

#### `handleCaptureStarted(message, sender)`

Acknowledges content script has started capture.

---

#### `handleCaptureStopped(message, sender)`

Receives final action buffer from content script on stop. Reconciles with background's action list.

---

## 3. Data Types Summary

### Action
```typescript
interface Action {
  index: number;                    // 0-based, contiguous
  type: "NAVIGATE" | "CLICK" | "TYPE" | "SELECT" | "SUBMIT";
  timestamp: string;                // ISO 8601 with ms
  target: {
    semantic: SemanticId | { url: string };
    structural: StructuralId | { url: string };
  };
  value: string | object | null;   // Action-type specific
  snapshot_before: Snapshot | null; // null for first action
  snapshot_after: Snapshot;
}
```

### Episode
```typescript
interface Episode {
  version: "0.2.0";
  episode_id: string;               // "ep_YYYYMMDD_NNN"
  recording_date: string;           // ISO 8601
  url_start: string;
  url_end: string;
  actions: Action[];
  metadata: {
    browser_version: string;
    screen_size: { width: number; height: number };
    locale: string;
    action_count: number;
    duration_ms: number;
    recording_mode: "user_interactive" | "cli_driven";
  };
}
```

---

## 4. Error Types

```typescript
type CaptureError =
  | { code: "NOT_RECORDING", message: string }
  | { code: "SNAPSHOT_TIMEOUT", message: string, partial?: Snapshot }
  | { code: "NODE_LIMIT_EXCEEDED", message: string, count: number }
  | { code: "CONTENT_SCRIPT_NOT_LOADED", message: string }
  | { code: "STORAGE_QUOTA_EXCEEDED", message: string }
  | { code: "INVALID_ACTION", message: string }
  | { code: "TAB_NOT_FOUND", message: string };
```

All errors are typed. No silent failures. Content script sends CAPTURE_ERROR to background. Background logs and may auto-stop recording on critical errors.

---

**Auth:** 65537
**Northstar:** Phuc Forecast
**Surface Lock:** All function signatures in this document are LOCKED. Solver implements exactly these signatures.
