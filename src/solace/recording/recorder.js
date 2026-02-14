/**
 * Solace Browser - Episode Recorder (JavaScript Implementation)
 * Auth: 65537 | Phase 2: Episode Recording
 *
 * This is the JavaScript implementation of the episode recording module.
 * It works with the existing Chrome extension infrastructure (background.js + content.js)
 * and produces Phase B compatible episode JSON.
 *
 * Usage:
 *   const recorder = new EpisodeRecorder();
 *   recorder.startRecording("https://example.com", { w: 1920, h: 1080 });
 *   recorder.recordClick({ selector: "button#submit", reference: "Submit" });
 *   recorder.recordType({ selector: "input[name='q']", reference: "Search" }, "query");
 *   recorder.stopRecording();
 *   const json = recorder.serializeEpisode();
 */

// Phase B allowed attributes for snapshot canonicalization
const ALLOWED_ATTRS = new Set([
  "aria-label", "aria-labelledby", "aria-describedby",
  "data-refid", "href", "id", "name", "placeholder",
  "role", "src", "title", "type", "value",
]);

const STRIP_ATTRS = new Set(["class", "style", "tabindex"]);

const VALID_ACTION_TYPES = new Set([
  "navigate", "click", "type", "select", "submit", "snapshot",
]);

const MAX_DOM_DEPTH = 200;
const MAX_DOM_NODES = 200000;

class EpisodeRecorder {
  constructor() {
    this._recording = false;
    this._episode = null;
    this._autoSnapshot = false;
    this._snapshotCallback = null;
  }

  // --- Lifecycle ---

  startRecording(initialUrl, viewport) {
    if (this._recording) {
      this.stopRecording();
    }

    this._recording = true;
    this._episode = {
      version: "1.0.0",
      session_id: this._generateSessionId(),
      domain: this._extractDomain(initialUrl),
      start_time: new Date().toISOString(),
      end_time: null,
      actions: [],
      snapshots: {},
      action_count: 0,
    };

    // Record initial navigation
    this.recordNavigate(initialUrl);
  }

  stopRecording() {
    if (!this._recording) return;
    this._recording = false;
    this._episode.end_time = new Date().toISOString();
    this._episode.action_count = this._episode.actions.length;
  }

  isRecording() {
    return this._recording;
  }

  // --- Action Recording ---

  recordNavigate(url) {
    if (!this._recording) return;
    this._recordAction("navigate", { url });
  }

  recordClick(target) {
    if (!this._recording) return;
    const data = {};
    if (target.selector) data.selector = target.selector;
    if (target.reference) data.reference = target.reference;
    this._recordAction("click", data);
  }

  recordType(target, text) {
    if (!this._recording) return;
    const data = { text };
    if (target.selector) data.selector = target.selector;
    if (target.reference) data.reference = target.reference;
    this._recordAction("type", data);
  }

  recordSelect(target, value) {
    if (!this._recording) return;
    const data = { value };
    if (target.selector) data.selector = target.selector;
    if (target.reference) data.reference = target.reference;
    this._recordAction("select", data);
  }

  recordSubmit(target) {
    if (!this._recording) return;
    const data = {};
    if (target.selector) data.selector = target.selector;
    if (target.reference) data.reference = target.reference;
    this._recordAction("submit", data);
  }

  // --- Snapshot Management ---

  attachSnapshot(step, snapshot) {
    if (!this._episode) return;
    this._episode.snapshots[String(step)] = snapshot;
  }

  setAutoSnapshot(enabled) {
    this._autoSnapshot = enabled;
  }

  setSnapshotCallback(callback) {
    this._snapshotCallback = callback;
  }

  // --- Snapshot Canonicalization (B1 Pipeline) ---

  canonicalizeSnapshot(rawSnapshot) {
    // Step 0: Validate schema
    const validationError = this._validateSnapshotSchema(rawSnapshot);
    if (validationError) {
      return { success: false, error_code: "E_SCHEMA", error_message: validationError };
    }

    // Step 1: Remove volatiles
    let dom = this._removeVolatiles(rawSnapshot.dom);

    // Step 2: Sort keys
    dom = this._sortKeys(dom);

    // Step 3: Normalize whitespace
    dom = this._normalizeWhitespace(dom);

    // Step 4: Normalize unicode (tag lowercasing)
    dom = this._normalizeUnicode(dom);

    // Step 5: Canonical JSON + hash
    const canonical = {
      v: 1,
      meta: { url: rawSnapshot.meta.url, viewport: rawSnapshot.meta.viewport },
      dom: dom,
    };

    // Deterministic JSON (sorted keys, no extra whitespace)
    const canonicalJson = this._deterministicStringify(canonical);
    const sha256 = this._computeSHA256(canonicalJson);

    // Extract landmarks
    const landmarks = this._extractLandmarks(dom);

    return {
      success: true,
      canonical_json: canonicalJson,
      sha256: sha256,
      landmarks: landmarks,
    };
  }

  // --- Serialization ---

  serializeEpisode() {
    if (!this._episode) return null;

    // Ensure action_count is correct
    const episode = { ...this._episode };
    episode.action_count = episode.actions.length;

    // Produce deterministic JSON with sorted keys
    return this._deterministicStringify(episode, 2);
  }

  getEpisode() {
    return this._episode;
  }

  getActionCount() {
    return this._episode ? this._episode.actions.length : 0;
  }

  // --- Validation ---

  validateEpisode(episode) {
    const errors = [];
    const ep = episode || this._episode;
    if (!ep) {
      errors.push("No episode to validate");
      return errors;
    }

    // Required keys
    const required = ["version", "session_id", "domain", "actions", "snapshots", "action_count"];
    for (const key of required) {
      if (!(key in ep)) {
        errors.push(`Missing required key: ${key}`);
      }
    }

    // Action count match
    if (ep.actions && ep.action_count !== ep.actions.length) {
      errors.push(`action_count=${ep.action_count} but ${ep.actions.length} actions`);
    }

    // Action validation
    if (ep.actions) {
      for (let i = 0; i < ep.actions.length; i++) {
        const action = ep.actions[i];
        if (action.step !== i) {
          errors.push(`Action ${i} has step=${action.step}, expected ${i}`);
        }
        if (!VALID_ACTION_TYPES.has(action.type)) {
          errors.push(`Action ${i} has invalid type: ${action.type}`);
        }
        if (!action.data) {
          errors.push(`Action ${i} missing data`);
        }
        if (!action.timestamp) {
          errors.push(`Action ${i} missing timestamp`);
        }
      }
    }

    return errors;
  }

  // --- File I/O ---

  async saveToFile(path) {
    if (!this._episode) return false;
    if (this._recording) this.stopRecording();

    const json = this.serializeEpisode();
    if (!json) return false;

    // Node.js environment
    if (typeof require !== "undefined") {
      const fs = require("fs");
      const pathMod = require("path");
      const dir = pathMod.dirname(path);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path, json, { mode: 0o600 });
      return true;
    }

    // Browser environment -- save to downloads
    if (typeof chrome !== "undefined" && chrome.downloads) {
      const blob = new Blob([json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      await chrome.downloads.download({
        url: url,
        filename: path,
        saveAs: false,
      });
      URL.revokeObjectURL(url);
      return true;
    }

    return false;
  }

  async saveToDefault() {
    const filename = `${this._episode.session_id}.json`;
    const defaultPath = `.solace/browser/episodes/${filename}`;

    // Node.js: use HOME
    if (typeof require !== "undefined") {
      const home = process.env.HOME || "/tmp";
      return this.saveToFile(`${home}/${defaultPath}`);
    }

    return this.saveToFile(defaultPath);
  }

  // --- JSONL Index ---

  getIndexEntry() {
    if (!this._episode) return null;
    return JSON.stringify({
      session_id: this._episode.session_id,
      domain: this._episode.domain,
      action_count: this._episode.action_count,
      start_time: this._episode.start_time,
      end_time: this._episode.end_time,
    });
  }

  // --- Private Methods ---

  _recordAction(type, data) {
    const step = this._episode.actions.length;
    const action = {
      step: step,
      type: type,
      data: data,
      timestamp: new Date().toISOString(),
    };
    this._episode.actions.push(action);

    // Auto-capture snapshot if enabled
    if (this._autoSnapshot && this._snapshotCallback) {
      const snapshot = this._snapshotCallback();
      if (snapshot) {
        this._episode.snapshots[String(step)] = snapshot;
      }
    }
  }

  _generateSessionId() {
    if (!EpisodeRecorder._sessionCounter) {
      EpisodeRecorder._sessionCounter = 0;
    }
    EpisodeRecorder._sessionCounter++;
    return `session_${Date.now()}_${EpisodeRecorder._sessionCounter}`;
  }

  _extractDomain(url) {
    try {
      const u = new URL(url);
      return u.hostname;
    } catch {
      return "unknown";
    }
  }

  // --- Deterministic JSON Serialization ---

  _deterministicStringify(obj, indent = 0) {
    return JSON.stringify(obj, (key, value) => {
      if (value && typeof value === "object" && !Array.isArray(value)) {
        // Sort object keys alphabetically
        const sorted = {};
        for (const k of Object.keys(value).sort()) {
          sorted[k] = value[k];
        }
        return sorted;
      }
      return value;
    }, indent);
  }

  // --- B1 Canonicalization Pipeline (Steps 1-4) ---

  _validateSnapshotSchema(snap) {
    if (!snap || typeof snap !== "object") return "snapshot must be an object";
    if (snap.v !== 1) return "E_TYPE: version must be 1";
    if (!snap.meta || typeof snap.meta !== "object") return "E_SCHEMA_KEYS: missing meta";
    if (!snap.dom || typeof snap.dom !== "object") return "E_SCHEMA_KEYS: missing dom";

    const topKeys = Object.keys(snap).sort().join(",");
    if (topKeys !== "dom,meta,v") return `E_SCHEMA_KEYS: expected dom,meta,v got ${topKeys}`;

    // Validate meta
    if (!snap.meta.url || typeof snap.meta.url !== "string") return "E_TYPE: meta.url";
    if (!snap.meta.viewport) return "E_SCHEMA_KEYS: missing viewport";
    if (typeof snap.meta.viewport.w !== "number" || snap.meta.viewport.w < 1) return "E_TYPE: viewport.w";
    if (typeof snap.meta.viewport.h !== "number" || snap.meta.viewport.h < 1) return "E_TYPE: viewport.h";

    // Validate DOM tree
    const nodeCount = { count: 0 };
    const nodeError = this._validateDomNode(snap.dom, 0, nodeCount);
    if (nodeError) return nodeError;

    return null; // valid
  }

  _validateDomNode(node, depth, nodeCount) {
    if (depth > MAX_DOM_DEPTH) return "E_DEPTH_LIMIT: depth exceeds 200";
    nodeCount.count++;
    if (nodeCount.count > MAX_DOM_NODES) return "E_NODE_LIMIT: node count exceeds 200000";

    const nodeKeys = Object.keys(node).sort().join(",");
    if (nodeKeys !== "attrs,children,tag,text") {
      return `E_SCHEMA_KEYS: node keys must be attrs,children,tag,text got ${nodeKeys}`;
    }

    if (typeof node.tag !== "string") return "E_TYPE: node.tag";
    if (typeof node.text !== "string") return "E_TYPE: node.text";
    if (typeof node.attrs !== "object" || Array.isArray(node.attrs)) return "E_TYPE: node.attrs";
    if (!Array.isArray(node.children)) return "E_TYPE: node.children";

    // Validate attrs
    for (const [k, v] of Object.entries(node.attrs)) {
      if (typeof k !== "string" || typeof v !== "string") return `E_TYPE: attr ${k}`;
      if (!ALLOWED_ATTRS.has(k) && !STRIP_ATTRS.has(k)) {
        return `E_ATTR_FORBIDDEN: forbidden attr: ${k}`;
      }
    }

    // Recurse children
    for (const child of node.children) {
      const err = this._validateDomNode(child, depth + 1, nodeCount);
      if (err) return err;
    }

    return null;
  }

  _removeVolatiles(node) {
    const attrs = {};
    for (const [k, v] of Object.entries(node.attrs)) {
      if (ALLOWED_ATTRS.has(k)) {
        attrs[k] = v;
      }
      // STRIP_ATTRS are silently dropped
    }
    return {
      tag: node.tag,
      text: node.text,
      attrs: attrs,
      children: node.children.map(c => this._removeVolatiles(c)),
    };
  }

  _sortKeys(node) {
    // Sort children by (tag, id, name, data-refid, text[:32])
    const sortedChildren = node.children
      .map(c => this._sortKeys(c))
      .sort((a, b) => {
        if (a.tag !== b.tag) return a.tag < b.tag ? -1 : 1;
        const aId = a.attrs.id || "";
        const bId = b.attrs.id || "";
        if (aId !== bId) return aId < bId ? -1 : 1;
        const aName = a.attrs.name || "";
        const bName = b.attrs.name || "";
        if (aName !== bName) return aName < bName ? -1 : 1;
        const aRef = a.attrs["data-refid"] || "";
        const bRef = b.attrs["data-refid"] || "";
        if (aRef !== bRef) return aRef < bRef ? -1 : 1;
        return (a.text || "").substring(0, 32).localeCompare((b.text || "").substring(0, 32));
      });

    return {
      tag: node.tag,
      text: node.text,
      attrs: node.attrs,
      children: sortedChildren,
    };
  }

  _normalizeWhitespace(node) {
    return {
      tag: node.tag,
      text: this._normalizeText(node.text),
      attrs: Object.fromEntries(
        Object.entries(node.attrs).map(([k, v]) => [k, this._normalizeText(v)])
      ),
      children: node.children.map(c => this._normalizeWhitespace(c)),
    };
  }

  _normalizeUnicode(node) {
    return {
      tag: node.tag.toLowerCase(),
      text: node.text,
      attrs: node.attrs,
      children: node.children.map(c => this._normalizeUnicode(c)),
    };
  }

  _normalizeText(text) {
    return text
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  // --- Landmark Extraction ---

  _extractLandmarks(dom, path = "") {
    const landmarks = [];
    const currentPath = path ? `${path} > ${dom.tag}` : dom.tag;
    const role = dom.attrs.role || "";
    const label = dom.attrs["aria-label"] || (dom.text || "").substring(0, 64);

    if (dom.tag === "nav" || role === "navigation") {
      landmarks.push({ type: "nav", label, role, selector: currentPath });
    }
    if (dom.tag === "form" || role === "form") {
      landmarks.push({ type: "form", label, role, selector: currentPath });
    }
    if (/^h[1-6]$/.test(dom.tag)) {
      landmarks.push({ type: "heading", label, role, selector: currentPath });
    }
    if (dom.tag === "button" || role === "button" ||
        (dom.tag === "input" && dom.attrs.type === "submit")) {
      landmarks.push({ type: "button", label, role, selector: currentPath });
    }
    if (dom.tag === "ul" || dom.tag === "ol" || role === "list") {
      landmarks.push({ type: "list", label, role, selector: currentPath });
    }

    for (const child of dom.children) {
      landmarks.push(...this._extractLandmarks(child, currentPath));
    }

    return landmarks;
  }

  // --- SHA-256 (using Web Crypto API or fallback) ---

  _computeSHA256(input) {
    // Synchronous fallback: simple hash for non-cryptographic use
    // In production, use crypto.subtle.digest for proper SHA-256
    if (typeof crypto !== "undefined" && crypto.subtle) {
      // We need a sync version here, so use the simple hash as placeholder
      // The async version is available via computeSHA256Async
      return this._simpleSHA256(input);
    }
    return this._simpleSHA256(input);
  }

  async computeSHA256Async(input) {
    if (typeof crypto !== "undefined" && crypto.subtle) {
      const encoder = new TextEncoder();
      const data = encoder.encode(input);
      const hashBuffer = await crypto.subtle.digest("SHA-256", data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
    }
    return this._simpleSHA256(input);
  }

  _simpleSHA256(input) {
    // FNV-1a 64-bit as placeholder hash (NOT cryptographic)
    // In production, replace with proper SHA-256
    let h1 = 0x811c9dc5;
    let h2 = 0xcbf29ce4;
    for (let i = 0; i < input.length; i++) {
      const c = input.charCodeAt(i);
      h1 ^= c;
      h1 = Math.imul(h1, 0x01000193);
      h2 ^= c;
      h2 = Math.imul(h2, 0x01000193);
    }
    return (
      (h1 >>> 0).toString(16).padStart(8, "0") +
      (h2 >>> 0).toString(16).padStart(8, "0") +
      "0000000000000000" +
      "0000000000000000"
    );
  }
}

// --- DOM Snapshot Capture Utility ---

function captureSnapshot(document, viewport) {
  const dom = captureDomNode(document.documentElement);
  return {
    v: 1,
    meta: {
      url: document.location.href,
      viewport: viewport || { w: window.innerWidth, h: window.innerHeight },
    },
    dom: dom,
  };
}

function captureDomNode(element) {
  const tag = element.tagName ? element.tagName.toLowerCase() : "text";
  const text = element.childNodes.length === 0 ? (element.textContent || "").trim() : "";

  const attrs = {};
  if (element.attributes) {
    for (const attr of element.attributes) {
      if (ALLOWED_ATTRS.has(attr.name) || STRIP_ATTRS.has(attr.name)) {
        attrs[attr.name] = attr.value;
      }
    }
  }

  const children = [];
  for (const child of element.children || []) {
    children.push(captureDomNode(child));
  }

  return { tag, text, attrs, children };
}

// --- Element Identification Utility ---

function identifyElement(element) {
  const ref = {
    selector: "",
    reference: "",
    tag: element.tagName ? element.tagName.toLowerCase() : "",
    id: element.id || "",
    role: element.getAttribute("role") || "",
  };

  // Build CSS selector
  if (element.id) {
    ref.selector = `#${element.id}`;
  } else if (element.getAttribute("data-testid")) {
    ref.selector = `[data-testid="${element.getAttribute("data-testid")}"]`;
  } else if (element.getAttribute("name")) {
    ref.selector = `${ref.tag}[name="${element.getAttribute("name")}"]`;
  } else if (element.getAttribute("aria-label")) {
    ref.selector = `[aria-label="${element.getAttribute("aria-label")}"]`;
  } else {
    // Fallback: tag + nth-child
    const parent = element.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter(
        c => c.tagName === element.tagName
      );
      const idx = siblings.indexOf(element) + 1;
      ref.selector = `${ref.tag}:nth-of-type(${idx})`;
    } else {
      ref.selector = ref.tag;
    }
  }

  // Semantic reference
  ref.reference =
    element.getAttribute("aria-label") ||
    element.getAttribute("title") ||
    element.getAttribute("placeholder") ||
    (element.textContent || "").trim().substring(0, 64) ||
    ref.selector;

  return ref;
}

// Export for different environments
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    EpisodeRecorder,
    captureSnapshot,
    captureDomNode,
    identifyElement,
    ALLOWED_ATTRS,
    STRIP_ATTRS,
    VALID_ACTION_TYPES,
  };
}

if (typeof globalThis !== "undefined") {
  globalThis.SolaceRecorder = {
    EpisodeRecorder,
    captureSnapshot,
    captureDomNode,
    identifyElement,
  };
}
