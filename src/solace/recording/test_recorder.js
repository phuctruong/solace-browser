/**
 * Solace Browser - Episode Recorder Tests
 * Auth: 65537 | Phase 2: Episode Recording
 *
 * Run: node test_recorder.js
 */

const {
  EpisodeRecorder,
  captureSnapshot,
  identifyElement,
  ALLOWED_ATTRS,
  STRIP_ATTRS,
  VALID_ACTION_TYPES,
} = require("./recorder.js");

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  PASS: ${message}`);
  } else {
    failed++;
    console.error(`  FAIL: ${message}`);
  }
}

function assertEqual(actual, expected, message) {
  if (actual === expected) {
    passed++;
    console.log(`  PASS: ${message}`);
  } else {
    failed++;
    console.error(`  FAIL: ${message} (expected ${expected}, got ${actual})`);
  }
}

// === Test Suite: EpisodeRecorder Lifecycle ===

console.log("\n=== Test Suite: Lifecycle ===");

{
  const recorder = new EpisodeRecorder();
  assert(!recorder.isRecording(), "not recording initially");

  recorder.startRecording("https://example.com", { w: 1920, h: 1080 });
  assert(recorder.isRecording(), "recording after start");

  recorder.stopRecording();
  assert(!recorder.isRecording(), "not recording after stop");
}

{
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://example.com", { w: 1920, h: 1080 });
  const episode = recorder.getEpisode();
  assertEqual(episode.version, "1.0.0", "version is 1.0.0");
  assert(episode.session_id.startsWith("session_"), "session_id has prefix");
  assertEqual(episode.domain, "example.com", "domain extracted correctly");
  assert(episode.start_time !== null, "start_time set");
  assertEqual(episode.actions.length, 1, "initial navigate action recorded");
  assertEqual(episode.actions[0].type, "navigate", "first action is navigate");
  assertEqual(episode.actions[0].data.url, "https://example.com", "navigate url correct");
  recorder.stopRecording();
}

// === Test Suite: Action Recording ===

console.log("\n=== Test Suite: Action Recording ===");

{
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://mail.google.com", { w: 1920, h: 1080 });

  // Click
  recorder.recordClick({ selector: "div[data-tooltip='Compose']", reference: "Compose" });
  assertEqual(recorder.getActionCount(), 2, "click recorded (2 total with navigate)");

  const clickAction = recorder.getEpisode().actions[1];
  assertEqual(clickAction.type, "click", "click type correct");
  assertEqual(clickAction.step, 1, "click step is 1");
  assertEqual(clickAction.data.selector, "div[data-tooltip='Compose']", "click selector");
  assertEqual(clickAction.data.reference, "Compose", "click reference");

  // Type
  recorder.recordType({ selector: "input[aria-label='To']", reference: "To" }, "user@example.com");
  assertEqual(recorder.getActionCount(), 3, "type recorded");
  const typeAction = recorder.getEpisode().actions[2];
  assertEqual(typeAction.type, "type", "type type correct");
  assertEqual(typeAction.data.text, "user@example.com", "type text correct");

  // Select
  recorder.recordSelect({ selector: "select#timezone", reference: "Timezone" }, "UTC-8");
  assertEqual(recorder.getActionCount(), 4, "select recorded");
  const selectAction = recorder.getEpisode().actions[3];
  assertEqual(selectAction.type, "select", "select type correct");
  assertEqual(selectAction.data.value, "UTC-8", "select value correct");

  // Submit
  recorder.recordSubmit({ selector: "form#login", reference: "Login Form" });
  assertEqual(recorder.getActionCount(), 5, "submit recorded");
  const submitAction = recorder.getEpisode().actions[4];
  assertEqual(submitAction.type, "submit", "submit type correct");

  recorder.stopRecording();
  assertEqual(recorder.getEpisode().action_count, 5, "action_count correct after stop");
}

// === Test Suite: Step Ordering ===

console.log("\n=== Test Suite: Step Ordering ===");

{
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://example.com", { w: 1920, h: 1080 });
  recorder.recordClick({ selector: "#btn1" });
  recorder.recordClick({ selector: "#btn2" });
  recorder.recordType({ selector: "#input1" }, "hello");
  recorder.stopRecording();

  const actions = recorder.getEpisode().actions;
  for (let i = 0; i < actions.length; i++) {
    assertEqual(actions[i].step, i, `step ${i} is sequential`);
  }
}

// === Test Suite: Serialization ===

console.log("\n=== Test Suite: Serialization ===");

{
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://example.com", { w: 1920, h: 1080 });
  recorder.recordClick({ selector: "#btn", reference: "Submit" });
  recorder.stopRecording();

  const json = recorder.serializeEpisode();
  assert(json !== null, "serialization produces output");

  const parsed = JSON.parse(json);
  assertEqual(parsed.version, "1.0.0", "serialized version correct");
  assertEqual(parsed.action_count, 2, "serialized action_count correct");
  assertEqual(parsed.actions.length, 2, "serialized actions length correct");
  assert(parsed.session_id.startsWith("session_"), "serialized session_id");
  assertEqual(parsed.domain, "example.com", "serialized domain");
}

// === Test Suite: Validation ===

console.log("\n=== Test Suite: Validation ===");

{
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://example.com", { w: 1920, h: 1080 });
  recorder.recordClick({ selector: "#btn" });
  recorder.stopRecording();

  const errors = recorder.validateEpisode();
  assertEqual(errors.length, 0, "valid episode has no errors");
}

{
  const recorder = new EpisodeRecorder();
  const errors = recorder.validateEpisode({ actions: [{ step: 0 }], action_count: 2 });
  assert(errors.length > 0, "invalid episode has errors");
}

// === Test Suite: Snapshot Canonicalization ===

console.log("\n=== Test Suite: Snapshot Canonicalization ===");

{
  const recorder = new EpisodeRecorder();
  const validSnapshot = {
    v: 1,
    meta: { url: "https://example.com", viewport: { w: 1920, h: 1080 } },
    dom: {
      tag: "html",
      text: "",
      attrs: { lang: "en" },
      children: [
        {
          tag: "body",
          text: "",
          attrs: {},
          children: [
            {
              tag: "nav",
              text: "",
              attrs: { role: "navigation", "aria-label": "Main" },
              children: [],
            },
            {
              tag: "button",
              text: "Submit",
              attrs: { "aria-label": "Submit", role: "button" },
              children: [],
            },
          ],
        },
      ],
    },
  };

  // Note: 'lang' is not in ALLOWED_ATTRS or STRIP_ATTRS, will be rejected
  // Let's test with valid attrs only
  const validSnapshot2 = {
    v: 1,
    meta: { url: "https://example.com", viewport: { w: 1920, h: 1080 } },
    dom: {
      tag: "html",
      text: "",
      attrs: {},
      children: [
        {
          tag: "body",
          text: "",
          attrs: {},
          children: [
            {
              tag: "nav",
              text: "",
              attrs: { role: "navigation", "aria-label": "Main" },
              children: [],
            },
            {
              tag: "button",
              text: "Submit",
              attrs: { "aria-label": "Submit", role: "button" },
              children: [],
            },
          ],
        },
      ],
    },
  };

  const result = recorder.canonicalizeSnapshot(validSnapshot2);
  assert(result.success, "valid snapshot canonicalizes successfully");
  assert(result.canonical_json.length > 0, "canonical JSON not empty");
  assert(result.sha256.length > 0, "SHA-256 hash produced");
  assert(result.landmarks.length > 0, "landmarks extracted");

  // Check landmarks
  const navLandmark = result.landmarks.find(l => l.type === "nav");
  assert(navLandmark !== undefined, "nav landmark found");

  const buttonLandmark = result.landmarks.find(l => l.type === "button");
  assert(buttonLandmark !== undefined, "button landmark found");
}

{
  const recorder = new EpisodeRecorder();

  // Forbidden attr should fail
  const badSnapshot = {
    v: 1,
    meta: { url: "https://example.com", viewport: { w: 1920, h: 1080 } },
    dom: {
      tag: "html",
      text: "",
      attrs: { "data-random": "xyz" },
      children: [],
    },
  };

  const result = recorder.canonicalizeSnapshot(badSnapshot);
  assert(!result.success, "forbidden attr causes failure");
  assert(result.error_code === "E_SCHEMA", "error code is E_SCHEMA");
  assert(result.error_message.includes("E_ATTR_FORBIDDEN"), "error mentions forbidden attr");
}

{
  const recorder = new EpisodeRecorder();

  // Strip attrs should be silently removed
  const stripSnapshot = {
    v: 1,
    meta: { url: "https://example.com", viewport: { w: 1920, h: 1080 } },
    dom: {
      tag: "div",
      text: "Hello",
      attrs: { "aria-label": "Main", class: "container", style: "color:red", tabindex: "0" },
      children: [],
    },
  };

  const result = recorder.canonicalizeSnapshot(stripSnapshot);
  assert(result.success, "strip attrs do not cause failure");
  assert(!result.canonical_json.includes("class"), "class attr stripped");
  assert(!result.canonical_json.includes("style"), "style attr stripped");
  assert(!result.canonical_json.includes("tabindex"), "tabindex attr stripped");
  assert(result.canonical_json.includes("aria-label"), "aria-label preserved");
}

// === Test Suite: Deterministic Output ===

console.log("\n=== Test Suite: Deterministic Output ===");

{
  const recorder1 = new EpisodeRecorder();
  const recorder2 = new EpisodeRecorder();

  const snap = {
    v: 1,
    meta: { url: "https://example.com", viewport: { w: 1920, h: 1080 } },
    dom: {
      tag: "html",
      text: "",
      attrs: {},
      children: [
        {
          tag: "body",
          text: "",
          attrs: {},
          children: [
            { tag: "h1", text: "Title", attrs: {}, children: [] },
            { tag: "p", text: "Paragraph", attrs: {}, children: [] },
          ],
        },
      ],
    },
  };

  const result1 = recorder1.canonicalizeSnapshot(snap);
  const result2 = recorder2.canonicalizeSnapshot(snap);

  assertEqual(result1.canonical_json, result2.canonical_json,
    "same input produces identical canonical JSON");
  assertEqual(result1.sha256, result2.sha256,
    "same input produces identical hash");
}

// === Test Suite: Whitespace Normalization ===

console.log("\n=== Test Suite: Whitespace Normalization ===");

{
  const recorder = new EpisodeRecorder();
  const snap = {
    v: 1,
    meta: { url: "https://example.com", viewport: { w: 1920, h: 1080 } },
    dom: {
      tag: "div",
      text: "  hello   world  \r\n  foo  ",
      attrs: { "aria-label": "  spaced   label  " },
      children: [],
    },
  };

  const result = recorder.canonicalizeSnapshot(snap);
  assert(result.success, "whitespace normalization succeeds");
  assert(result.canonical_json.includes("hello world foo"), "whitespace collapsed in text");
  assert(result.canonical_json.includes("spaced label"), "whitespace collapsed in attrs");
}

// === Test Suite: Tag Lowercasing ===

console.log("\n=== Test Suite: Tag Lowercasing ===");

{
  const recorder = new EpisodeRecorder();
  const snap = {
    v: 1,
    meta: { url: "https://example.com", viewport: { w: 1920, h: 1080 } },
    dom: {
      tag: "DIV",
      text: "",
      attrs: {},
      children: [
        { tag: "SPAN", text: "text", attrs: {}, children: [] },
      ],
    },
  };

  const result = recorder.canonicalizeSnapshot(snap);
  assert(result.success, "uppercase tags canonicalize");
  assert(result.canonical_json.includes('"div"'), "DIV lowercased to div");
  assert(result.canonical_json.includes('"span"'), "SPAN lowercased to span");
}

// === Test Suite: Actions Not Recorded When Not Recording ===

console.log("\n=== Test Suite: Guard Against Non-Recording ===");

{
  const recorder = new EpisodeRecorder();
  recorder.recordClick({ selector: "#btn" });
  recorder.recordType({ selector: "#input" }, "text");
  recorder.recordNavigate("https://example.com");
  assertEqual(recorder.getActionCount(), 0, "no actions recorded when not recording");
}

// === Test Suite: Auto-Snapshot ===

console.log("\n=== Test Suite: Auto-Snapshot ===");

{
  const recorder = new EpisodeRecorder();
  let snapshotCallCount = 0;

  recorder.setAutoSnapshot(true);
  recorder.setSnapshotCallback(() => {
    snapshotCallCount++;
    return {
      v: 1,
      meta: { url: "https://example.com", viewport: { w: 1920, h: 1080 } },
      dom: { tag: "html", text: "", attrs: {}, children: [] },
    };
  });

  recorder.startRecording("https://example.com", { w: 1920, h: 1080 });
  recorder.recordClick({ selector: "#btn" });
  recorder.recordType({ selector: "#input" }, "text");
  recorder.stopRecording();

  assertEqual(snapshotCallCount, 3, "snapshot callback called for each action");

  const snapshots = recorder.getEpisode().snapshots;
  const snapshotKeys = Object.keys(snapshots);
  assertEqual(snapshotKeys.length, 3, "3 snapshots attached");
}

// === Test Suite: JSONL Index Entry ===

console.log("\n=== Test Suite: JSONL Index ===");

{
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://example.com", { w: 1920, h: 1080 });
  recorder.recordClick({ selector: "#btn" });
  recorder.stopRecording();

  const entry = recorder.getIndexEntry();
  assert(entry !== null, "index entry produced");

  const parsed = JSON.parse(entry);
  assert(parsed.session_id.startsWith("session_"), "index has session_id");
  assertEqual(parsed.domain, "example.com", "index has domain");
  assertEqual(parsed.action_count, 2, "index has action_count");
}

// === Test Suite: Multiple Recording Sessions ===

console.log("\n=== Test Suite: Multiple Sessions ===");

{
  const recorder = new EpisodeRecorder();

  // Session 1
  recorder.startRecording("https://site1.com", { w: 1920, h: 1080 });
  recorder.recordClick({ selector: "#btn1" });
  recorder.stopRecording();
  const session1Id = recorder.getEpisode().session_id;

  // Session 2 (replaces session 1)
  recorder.startRecording("https://site2.com", { w: 1920, h: 1080 });
  recorder.recordClick({ selector: "#btn2" });
  recorder.stopRecording();
  const session2Id = recorder.getEpisode().session_id;

  assert(session1Id !== session2Id, "different sessions have different IDs");
  assertEqual(recorder.getEpisode().domain, "site2.com", "session 2 domain correct");
}

// === Summary ===

console.log(`\n${"=".repeat(50)}`);
console.log(`Results: ${passed} passed, ${failed} failed, ${passed + failed} total`);
console.log(`${"=".repeat(50)}`);

if (failed > 0) {
  process.exit(1);
}
