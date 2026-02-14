# Phase 2: Episode Recording - Architecture Design

**Status**: READY FOR IMPLEMENTATION
**Auth**: 65537 | **Northstar**: Phuc Forecast

---

## Overview

Episode recording captures user browser interactions natively within Ungoogled Chromium (no extension needed).

### Design Decisions

#### 1. Hook Layer: Renderer Process
- **Choice**: Renderer process MutationObserver + Event listeners
- **Rationale**: Direct DOM access, single-threaded, deterministic snapshots
- **IPC**: Renderer → Browser via mojo messages for storage

#### 2. Snapshot Strategy: Full DOM per Action
- **Choice**: Complete DOM snapshot before/after each action
- **Rationale**: Supports Phase B canonicalization and determinism
- **Compression**: Phase B snapshot canonicalization handles reduction

#### 3. Storage Format: Single JSON File + Index
- **Choice**: One episode per JSON file, optional JSONL index
- **Location**: `~/.solace/browser/episodes/`
- **Naming**: `ep_YYYYMMDD_NNN.json` (deterministic)

---

## Architecture

```
USER ACTION (click, type, navigate)
    ↓
RENDERER PROCESS
    ├─ MutationObserver detects DOM change
    ├─ Event listeners capture interaction details
    ├─ Take snapshot (before action)
    ├─ Wait for DOM settle
    ├─ Take snapshot (after action)
    └─ Serialize to Action object
    ↓
ACTION BUFFER (in-memory)
    └─ Flush to IPC after each action
    ↓
BROWSER PROCESS (via Mojo IPC)
    ├─ Receive Action
    ├─ Add to current Episode
    └─ Maintain in-memory episode state
    ↓
STORAGE
    ├─ On stop_recording(): Serialize Episode to JSON
    ├─ Write to ~/.solace/browser/episodes/ep_NNN.json
    └─ Update index (optional episodes.jsonl)
```

---

## API Specification

### RecordingManager (Browser Process)

```cpp
class RecordingManager {
  public:
    // Start recording at given URL
    void StartRecording(const GURL& initial_url);

    // Stop recording and save episode to disk
    Episode StopRecording();

    // Get current episode (for live preview)
    const Episode& GetCurrentEpisode() const;

    // Save episode to path
    bool SaveEpisode(const Episode& episode,
                     const base::FilePath& path);

    // Get episode storage directory
    base::FilePath GetEpisodeDirectory();

  private:
    Episode current_episode_;
    bool is_recording_ = false;
};
```

### ActionSerializerRenderer (Renderer Process)

```cpp
class ActionSerializer {
  public:
    // Serialize navigation action
    Action SerializeNavigateAction(const GURL& url, int64_t timestamp_ms);

    // Serialize click action
    Action SerializeClickAction(const blink::Element& element, int64_t timestamp_ms);

    // Serialize type action
    Action SerializeTypeAction(const std::string& text, int64_t timestamp_ms);

    // Serialize select action
    Action SerializeSelectAction(const std::string& value, int64_t timestamp_ms);

    // Serialize submit action
    Action SerializeSubmitAction(const blink::Element& form, int64_t timestamp_ms);

  private:
    // Extract semantic selector (aria-*, data-testid, etc.)
    Selector ExtractSemanticSelector(const blink::Element& elem);

    // Extract structural selector (CSS path, XPath)
    Selector ExtractStructuralSelector(const blink::Element& elem);
};
```

### SnapshotCapturer (Renderer Process)

```cpp
class SnapshotCapturer {
  public:
    // Take snapshot of current DOM
    Snapshot TakeSnapshot(blink::Document* doc);

    // Canonicalize snapshot (deterministic, hashable)
    std::string CanonicalizeSnapshot(const Snapshot& snapshot);

    // Compute deterministic hash
    std::string ComputeHash(const Snapshot& snapshot);

  private:
    // Remove volatile elements (timestamps, random IDs, etc.)
    void StripVolatileContent(Snapshot& snapshot);

    // Sort keys for determinism
    void SortKeys(Snapshot& snapshot);
};
```

---

## Episode Schema (Phase B Compatible)

```json
{
  "episode_id": "ep_20250214_001",
  "recording_start": "2025-02-14T14:30:00.000Z",
  "recording_end": "2025-02-14T14:35:30.000Z",
  "url_start": "https://reddit.com/r/test",
  "url_end": "https://reddit.com/r/test/comments/abc123",
  "action_count": 5,
  "metadata": {
    "browser_version": "ungoogled-chromium-127.0.0",
    "browser_build": "Solace-0.1.0",
    "screen_width": 1920,
    "screen_height": 1080,
    "locale": "en-US"
  },
  "actions": [
    {
      "index": 0,
      "type": "NAVIGATE",
      "timestamp": "2025-02-14T14:30:00.000Z",
      "target": {
        "semantic": {
          "type": "URL",
          "value": "https://reddit.com/r/test"
        },
        "structural": {
          "type": "URL",
          "value": "https://reddit.com/r/test"
        }
      },
      "value": "https://reddit.com/r/test",
      "snapshot_before": {
        "type": "DOM_SNAPSHOT",
        "hash": "sha256_before_hash",
        "content_length": 125000,
        "root_tag": "html"
      },
      "snapshot_after": {
        "type": "DOM_SNAPSHOT",
        "hash": "sha256_after_hash",
        "content_length": 130000,
        "root_tag": "html"
      }
    },
    {
      "index": 1,
      "type": "CLICK",
      "timestamp": "2025-02-14T14:30:02.500Z",
      "target": {
        "semantic": {
          "type": "ARIA_LABEL",
          "value": "Create Post"
        },
        "structural": {
          "type": "CSS_SELECTOR",
          "value": "button.submit-button[data-testid='create-post']"
        }
      },
      "value": null,
      "snapshot_before": {...},
      "snapshot_after": {...}
    },
    {
      "index": 2,
      "type": "TYPE",
      "timestamp": "2025-02-14T14:30:05.000Z",
      "target": {
        "semantic": {
          "type": "DATA_TESTID",
          "value": "post-title-input"
        },
        "structural": {
          "type": "CSS_SELECTOR",
          "value": "input#title[type='text']"
        }
      },
      "value": "Test Post Title",
      "snapshot_before": {...},
      "snapshot_after": {...}
    }
  ]
}
```

---

## Implementation Roadmap

### Step 1: File Structure (Phase 2A)
```
src/solace/recording/
├── BUILD.gn
├── recording_manager.h
├── recording_manager.cc
├── action_serializer.h
├── action_serializer.cc
├── snapshot_capturer.h
├── snapshot_capturer.cc
└── episode_schema.h
```

### Step 2: Core Classes (Phase 2B)
- RecordingManager (browser process)
- ActionSerializer (renderer process)
- SnapshotCapturer (renderer process)
- Episode/Action data structures

### Step 3: Event Hooks (Phase 2C)
- MutationObserver for DOM changes
- click, input, change, submit event listeners
- Navigation observer (history/URL changes)

### Step 4: Serialization (Phase 2D)
- Convert Episode → Phase B JSON
- Deterministic snapshot hashing
- File I/O and storage

---

## Testing Strategy

See: TEST_SPEC.md

**Summary:**
- 25 OAuth tests (care, bridge, stability)
- 29 edge tests (641 - single action types, edge cases)
- 18 stress tests (274177 - scaling, memory, concurrency)
- 28 god tests (65537 - Phase B compat, workflows, proofs)

**Total: 75 tests** (all must pass before Phase 2 completion)

---

## Success Criteria

✅ Phase 2 Complete When:
1. All 5 action types working (NAVIGATE, CLICK, TYPE, SELECT, SUBMIT)
2. Snapshots deterministic (same DOM = same hash)
3. Episodes serialize to Phase B JSON
4. Episodes persist to disk (~/.solace/browser/episodes/)
5. All 75 tests passing (641→274177→65537)
6. Zero compiler warnings/errors
7. Code review approved

---

**Next Step**: Proceed to Phase 2B implementation
