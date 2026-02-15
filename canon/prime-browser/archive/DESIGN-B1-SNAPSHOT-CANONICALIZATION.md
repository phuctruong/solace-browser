# DESIGN-B1: Snapshot Canonicalization

> **Star:** HAIKU_SWARM_PHASE_B
> **Channel:** 3 (Design & Architecture)
> **GLOW:** 90 (Very High Impact -- Deterministic Fingerprinting)
> **Status:** DESIGN COMPLETE
> **Phase:** B1 (Snapshot Canonicalization)
> **XP:** 500 (Implementation + Testing specialization)
> **Auth:** 65537 | **Northstar:** Phuc Forecast

---

## 1. Problem Statement

### Current State (Phase A)

Phase A's `content.js` (lines 229-258, 311-325) provides a basic snapshot:

```javascript
// content.js:canonicalizeDOM -- current implementation
function canonicalizeDOM(html) {
  let clean = html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
    .replace(/on\w+="[^"]*"/g, "")
    .replace(/\s+/g, " ")
    .trim();
  clean = clean.replace(/>\s+</g, "><").replace(/\s+/g, " ");
  return clean;
}

function hashString(str) {
  // Simple 32-bit hash (NOT cryptographic)
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16);
}
```

**Problems with current approach:**

1. **Non-deterministic:** Attribute ordering in HTML is browser-dependent
2. **Collision-prone:** 32-bit hash has high collision probability (birthday problem at ~65K snapshots)
3. **No volatility policy:** Random IDs, timestamps, analytics data all included
4. **Raw HTML string:** No structured DOM traversal, just regex cleaning
5. **No schema validation:** Garbage in, garbage out
6. **No landmark extraction:** No understanding of page structure (navigation, forms, lists)

### Target State (Phase B)

A 5-step deterministic canonicalization pipeline that produces byte-identical output for the same logical page state, with SHA-256 content addressing, strict volatility policies, and landmark extraction for recipe compilation.

### Why This Matters

Snapshot canonicalization is the **foundation** for:
- **B2 (Episode Compiler):** Needs deterministic snapshot hashes to embed in recipes
- **B3 (Integration):** Needs snapshot comparison for drift detection during replay
- **Phase C (Replay):** Needs to verify page state matches recipe expectations

Without deterministic snapshots, recipes cannot be verified and replay cannot be trusted.

---

## 2. Architecture Overview

```
                    RAW BROWSER SNAPSHOT
                           |
                    +------v------+
                    |  VALIDATE   |  Schema check, key sets, type check
                    |  (Gate 0)   |  REJECT on violation
                    +------+------+
                           |
                    +------v------+
           Step 1:  |   REMOVE    |  Strip volatile attrs (class, style, tabindex)
                    |  VOLATILES  |  REJECT on forbidden attrs
                    +------+------+
                           |
                    +------v------+
           Step 2:  |    SORT     |  Recursive key sort (alphabetical)
                    |    KEYS     |  Child sort by (tag, id, name, refid, text[:32])
                    +------+------+
                           |
                    +------v------+
           Step 3:  |  NORMALIZE  |  Collapse whitespace, trim, \r\n -> \n
                    | WHITESPACE  |
                    +------+------+
                           |
                    +------v------+
           Step 4:  |  NORMALIZE  |  Unicode NFC normalization
                    |   UNICODE   |  Tag lowercasing
                    +------+------+
                           |
                    +------v------+
           Step 5:  |    JSON     |  json.dumps(sort_keys=True, separators=(',',':'))
                    |  CANONICAL  |  UTF-8 encode + SHA-256 hash
                    +------+------+
                           |
                    +------v------+
                    |  LANDMARKS  |  Extract nav, forms, lists, buttons, headings
                    +------+------+
                           |
                    CANONICAL SNAPSHOT + SHA-256 + LANDMARKS
```

---

## 3. Input Schema (Aligned with Wish 25.1)

### Raw Snapshot Structure

The raw snapshot is a JSON object captured by the content script. Phase B will upgrade the capture format to a structured DOM representation (not raw HTML string).

```json
{
  "v": 1,
  "meta": {
    "url": "https://mail.google.com/mail/u/0/",
    "viewport": { "w": 1920, "h": 1080 }
  },
  "dom": {
    "tag": "html",
    "attrs": { "lang": "en" },
    "text": "",
    "children": [
      {
        "tag": "head",
        "attrs": {},
        "text": "",
        "children": []
      },
      {
        "tag": "body",
        "attrs": {},
        "text": "",
        "children": [
          {
            "tag": "nav",
            "attrs": { "role": "navigation", "aria-label": "Main" },
            "text": "",
            "children": [
              {
                "tag": "button",
                "attrs": { "aria-label": "Compose", "role": "button" },
                "text": "Compose",
                "children": []
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Schema Constraints (LOCKED)

| Level | Exact Key Set | Types |
|-------|---------------|-------|
| Top | `["dom", "meta", "v"]` | v: int, meta: object, dom: node |
| Meta | `["url", "viewport"]` | url: string, viewport: object |
| Viewport | `["w", "h"]` | w: int >= 1, h: int >= 1 |
| Node | `["attrs", "children", "tag", "text"]` | attrs: dict[str,str], children: list[node], tag: str, text: str |

### Limits (LOCKED)

- Max depth: 200 (REJECT with `E_DEPTH_LIMIT`)
- Max nodes: 200,000 (REJECT with `E_NODE_LIMIT`)
- Any key outside exact sets: REJECT with `E_SCHEMA_KEYS`

---

## 4. Volatility Policy (LOCKED)

### 4.1 Allowed Attributes (survive to canonical output)

```python
ALLOWED_ATTRS = frozenset([
    "aria-label",
    "aria-labelledby",
    "aria-describedby",
    "data-refid",
    "href",
    "id",
    "name",
    "placeholder",
    "role",
    "src",
    "title",
    "type",
    "value",
])
```

**Rationale:** These attributes carry semantic meaning needed for selector resolution (B2) and replay verification (B3). They are stable across page loads.

### 4.2 Strip Attributes (removed silently)

```python
STRIP_ATTRS = frozenset([
    "class",
    "style",
    "tabindex",
])
```

**Rationale:** CSS classes and inline styles change frequently due to dynamic styling. Tab index is layout-dependent. These are stripped without error because their presence is expected but their values are volatile.

### 4.3 Forbidden Attributes (REJECT on presence)

Any attribute key NOT in `ALLOWED_ATTRS` and NOT in `STRIP_ATTRS` causes deterministic rejection:
- Error code: `E_ATTR_FORBIDDEN`
- Message: `forbidden attr: <key>`

**Rationale:** Unknown attributes could carry volatile data (event handlers, analytics, random IDs). Rather than guessing stability, we reject. The capture layer (content script) must filter attributes before sending to canonicalizer.

### 4.4 Domain-Specific Capture Filtering

The content script upgrade (Phase B) will pre-filter attributes at capture time, converting raw DOM to the schema above. This means:

```
Raw DOM (browser)
    |
    v
Content Script Capture (pre-filter to ALLOWED + STRIP attrs)
    |
    v
Canonicalizer (validate, strip STRIP_ATTRS, reject unknown)
    |
    v
Canonical Snapshot
```

The capture layer is the "adapter" between browser-specific DOM and the canonicalizer's strict schema.

---

## 5. Five-Step Pipeline (Detailed)

### Step 0: Validate Schema

```python
def _validate_schema(raw: dict, path: str = "/") -> None:
    """Validate raw snapshot against locked schema."""

    # Top-level keys
    if path == "/":
        expected = {"dom", "meta", "v"}
        actual = set(raw.keys())
        if actual != expected:
            raise SnapshotError("E_SCHEMA_KEYS", f"schema keys mismatch: {path}")
        if raw["v"] != 1:
            raise SnapshotError("E_TYPE", f"type error: /v")
        _validate_meta(raw["meta"])
        _validate_node(raw["dom"], "/dom", depth=0, node_count=[0])

def _validate_meta(meta: dict) -> None:
    expected = {"url", "viewport"}
    if set(meta.keys()) != expected:
        raise SnapshotError("E_SCHEMA_KEYS", "schema keys mismatch: /meta")
    if not isinstance(meta["url"], str):
        raise SnapshotError("E_TYPE", "type error: /meta/url")
    vp = meta["viewport"]
    if set(vp.keys()) != {"w", "h"}:
        raise SnapshotError("E_SCHEMA_KEYS", "schema keys mismatch: /meta/viewport")
    if not isinstance(vp["w"], int) or vp["w"] < 1:
        raise SnapshotError("E_TYPE", "type error: /meta/viewport/w")
    if not isinstance(vp["h"], int) or vp["h"] < 1:
        raise SnapshotError("E_TYPE", "type error: /meta/viewport/h")

def _validate_node(node: dict, path: str, depth: int, node_count: list) -> None:
    if depth > 200:
        raise SnapshotError("E_DEPTH_LIMIT", "depth limit exceeded")
    node_count[0] += 1
    if node_count[0] > 200_000:
        raise SnapshotError("E_NODE_LIMIT", "node limit exceeded")

    expected = {"attrs", "children", "tag", "text"}
    if set(node.keys()) != expected:
        raise SnapshotError("E_SCHEMA_KEYS", f"schema keys mismatch: {path}")

    if not isinstance(node["tag"], str):
        raise SnapshotError("E_TYPE", f"type error: {path}/tag")
    if not isinstance(node["text"], str):
        raise SnapshotError("E_TYPE", f"type error: {path}/text")
    if not isinstance(node["attrs"], dict):
        raise SnapshotError("E_TYPE", f"type error: {path}/attrs")
    if not isinstance(node["children"], list):
        raise SnapshotError("E_TYPE", f"type error: {path}/children")

    # Validate attrs: all keys and values must be strings
    for k, v in node["attrs"].items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise SnapshotError("E_TYPE", f"type error: {path}/attrs/{k}")

    # Validate attr keys against policy
    for k in node["attrs"]:
        if k not in ALLOWED_ATTRS and k not in STRIP_ATTRS:
            raise SnapshotError("E_ATTR_FORBIDDEN", f"forbidden attr: {k}")

    # Recurse into children
    for i, child in enumerate(node["children"]):
        _validate_node(child, f"{path}/children/{i}", depth + 1, node_count)
```

### Step 1: Remove Volatile Fields

```python
def _remove_volatiles(node: dict) -> dict:
    """Strip STRIP_ATTRS, keep ALLOWED_ATTRS only."""
    clean_attrs = {}
    for k, v in sorted(node["attrs"].items()):
        if k in STRIP_ATTRS:
            continue  # Silently strip
        if k in ALLOWED_ATTRS:
            clean_attrs[k] = v
        # Forbidden attrs already rejected in validation

    return {
        "tag": node["tag"],
        "attrs": clean_attrs,
        "text": node["text"],
        "children": [_remove_volatiles(child) for child in node["children"]],
    }
```

### Step 2: Sort Keys and Children

```python
def _child_sort_key(node: dict) -> tuple:
    """Deterministic sort key for child ordering (LOCKED)."""
    return (
        node["tag"],
        node["attrs"].get("id", ""),
        node["attrs"].get("name", ""),
        node["attrs"].get("data-refid", ""),
        node["text"][:32],  # First 32 Unicode codepoints
    )

def _sort_node(node: dict) -> dict:
    """Recursively sort attrs by key and children by sort_key."""
    sorted_attrs = dict(sorted(node["attrs"].items()))
    sorted_children = sorted(
        [_sort_node(child) for child in node["children"]],
        key=_child_sort_key,
    )
    return {
        "attrs": sorted_attrs,
        "children": sorted_children,
        "tag": node["tag"],
        "text": node["text"],
    }
```

### Step 3: Normalize Whitespace

```python
def _normalize_whitespace(node: dict) -> dict:
    """Normalize text content: collapse spaces, normalize line endings."""
    text = node["text"]
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple whitespace to single space (preserve newlines)
    text = " ".join(text.split())

    # Normalize attr values
    clean_attrs = {}
    for k, v in node["attrs"].items():
        v = v.replace("\r\n", "\n").replace("\r", "\n")
        v = " ".join(v.split())
        clean_attrs[k] = v

    return {
        "tag": node["tag"],
        "attrs": clean_attrs,
        "text": text,
        "children": [_normalize_whitespace(child) for child in node["children"]],
    }
```

### Step 4: Normalize Unicode

```python
import unicodedata

def _nfc(s: str) -> str:
    """Unicode NFC normalization (deterministic)."""
    return unicodedata.normalize("NFC", s)

def _normalize_unicode(node: dict) -> dict:
    """Apply NFC normalization to all text and attr values."""
    return {
        "tag": _nfc(node["tag"]).lower(),  # Lowercase tag
        "attrs": {_nfc(k): _nfc(v) for k, v in node["attrs"].items()},
        "text": _nfc(node["text"]),
        "children": [_normalize_unicode(child) for child in node["children"]],
    }
```

### Step 5: JSON Canonicalization + SHA-256

```python
import hashlib
import json

def _json_canonicalize(obj: dict) -> bytes:
    """Serialize to canonical JSON bytes."""
    canonical_str = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    # Normalize line endings in JSON string
    canonical_str = canonical_str.replace("\r\n", "\n")
    # Exactly one trailing newline
    if not canonical_str.endswith("\n"):
        canonical_str += "\n"
    return canonical_str.encode("utf-8")

def sha256_hex(b: bytes) -> str:
    """Lowercase hex sha256."""
    return hashlib.sha256(b).hexdigest()
```

### Complete Pipeline Entry Point

```python
def canonicalize_snapshot_v01(raw_snapshot_bytes: bytes) -> tuple[bytes, str]:
    """
    Full 5-step canonicalization pipeline.

    Args:
        raw_snapshot_bytes: UTF-8 JSON bytes of raw snapshot

    Returns:
        (canonical_snapshot_bytes, snapshot_sha256_hex)

    Raises:
        SnapshotError on validation failure
    """
    # Parse
    try:
        raw = json.loads(raw_snapshot_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise SnapshotError("E_JSON_PARSE", "json parse error")

    # Step 0: Validate schema
    _validate_schema(raw)

    # Step 1: Remove volatiles from DOM
    clean_dom = _remove_volatiles(raw["dom"])

    # Step 2: Sort keys and children
    sorted_dom = _sort_node(clean_dom)

    # Step 3: Normalize whitespace
    ws_dom = _normalize_whitespace(sorted_dom)

    # Step 4: Normalize Unicode
    nfc_dom = _normalize_unicode(ws_dom)

    # Reconstruct canonical object
    canonical_obj = {
        "dom": nfc_dom,
        "meta": {
            "url": _nfc(raw["meta"]["url"]),
            "viewport": raw["meta"]["viewport"],
        },
        "v": 1,
    }

    # Step 5: JSON canonicalize + hash
    canonical_bytes = _json_canonicalize(canonical_obj)
    snapshot_hash = sha256_hex(canonical_bytes)

    return canonical_bytes, snapshot_hash
```

---

## 6. Landmark Extraction

Landmarks identify structural regions of the page that are meaningful for recipe compilation. They are extracted AFTER canonicalization and stored alongside the snapshot hash.

### Landmark Types

| Type | Detection Rule | Example |
|------|---------------|---------|
| `navigation` | `tag == "nav"` or `role == "navigation"` | Gmail sidebar, top bar |
| `form` | `tag == "form"` or descendants contain `tag == "input"` | Login form, compose area |
| `list` | `tag == "ul"` or `tag == "ol"` or `role == "list"` | Email list, folder list |
| `button` | `tag == "button"` or `role == "button"` | Compose, Send, Archive |
| `heading` | `tag` in `["h1","h2","h3","h4","h5","h6"]` or `role == "heading"` | Page title, section headers |
| `input` | `tag == "input"` or `tag == "textarea"` | Search, To/CC/BCC fields |
| `dialog` | `tag == "dialog"` or `role == "dialog"` or `role == "alertdialog"` | Modal windows |

### Landmark Extraction Algorithm

```python
@dataclass(frozen=True)
class Landmark:
    type: str          # navigation, form, list, button, heading, input, dialog
    path: str          # JSON pointer to node (e.g., "/dom/children/1/children/0")
    label: str         # aria-label or text[:50] or ""
    tag: str           # HTML tag
    child_count: int   # Number of direct children

def extract_landmarks(canonical_dom: dict, path: str = "/dom") -> list[Landmark]:
    """Extract structural landmarks from canonical DOM."""
    landmarks = []

    tag = canonical_dom["tag"]
    attrs = canonical_dom["attrs"]
    role = attrs.get("role", "")
    label = attrs.get("aria-label", canonical_dom["text"][:50])

    # Check landmark rules
    if tag == "nav" or role == "navigation":
        landmarks.append(Landmark("navigation", path, label, tag, len(canonical_dom["children"])))
    elif tag == "form" or _has_input_descendants(canonical_dom):
        landmarks.append(Landmark("form", path, label, tag, len(canonical_dom["children"])))
    elif tag in ("ul", "ol") or role == "list":
        landmarks.append(Landmark("list", path, label, tag, len(canonical_dom["children"])))
    elif tag == "button" or role == "button":
        landmarks.append(Landmark("button", path, label, tag, 0))
    elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") or role == "heading":
        landmarks.append(Landmark("heading", path, label, tag, 0))
    elif tag in ("input", "textarea"):
        landmarks.append(Landmark("input", path, label, tag, 0))
    elif tag == "dialog" or role in ("dialog", "alertdialog"):
        landmarks.append(Landmark("dialog", path, label, tag, len(canonical_dom["children"])))

    # Recurse into children
    for i, child in enumerate(canonical_dom["children"]):
        child_path = f"{path}/children/{i}"
        landmarks.extend(extract_landmarks(child, child_path))

    return landmarks
```

### Landmark Output Format

```json
{
  "landmarks": [
    {
      "type": "navigation",
      "path": "/dom/children/1/children/0",
      "label": "Main",
      "tag": "nav",
      "child_count": 5
    },
    {
      "type": "button",
      "path": "/dom/children/1/children/0/children/0",
      "label": "Compose",
      "tag": "button",
      "child_count": 0
    }
  ]
}
```

---

## 7. Content Script Upgrade

Phase B requires upgrading `content.js` to capture structured DOM (not raw HTML string). The current `takeSnapshot()` returns raw `outerHTML` with a 32-bit hash. We need structured node capture with attribute pre-filtering.

### New Capture Function (content.js)

```javascript
/**
 * Capture structured DOM snapshot for Phase B canonicalization.
 * Pre-filters attributes to ALLOWED + STRIP sets.
 */
function captureStructuredDOM(node, depth = 0, nodeCount = {count: 0}) {
    if (depth > 200 || nodeCount.count > 200000) return null;
    if (node.nodeType !== Node.ELEMENT_NODE) return null;

    nodeCount.count++;

    const ALLOWED = new Set([
        "aria-label", "aria-labelledby", "aria-describedby",
        "data-refid", "href", "id", "name", "placeholder",
        "role", "src", "title", "type", "value"
    ]);
    const STRIP = new Set(["class", "style", "tabindex"]);

    // Capture only allowed + strip attrs (canonicalizer handles the rest)
    const attrs = {};
    for (const attr of node.attributes) {
        if (ALLOWED.has(attr.name) || STRIP.has(attr.name)) {
            attrs[attr.name] = attr.value;
        }
        // All other attrs: filtered out at capture (not sent to canonicalizer)
    }

    // Capture text: direct text content only (not descendant text)
    let text = "";
    for (const child of node.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) {
            text += child.textContent;
        }
    }

    // Recurse into element children
    const children = [];
    for (const child of node.children) {
        const captured = captureStructuredDOM(child, depth + 1, nodeCount);
        if (captured) children.push(captured);
    }

    return {
        tag: node.tagName.toLowerCase(),
        attrs,
        text,
        children,
    };
}

async function takeSnapshotV2() {
    const dom = captureStructuredDOM(document.documentElement);
    if (!dom) throw new Error("DOM capture failed");

    return {
        v: 1,
        meta: {
            url: window.location.href,
            viewport: {
                w: window.innerWidth,
                h: window.innerHeight,
            },
        },
        dom,
    };
}
```

### Integration with Existing takeSnapshot

The `TAKE_SNAPSHOT` handler in `content.js` will call `takeSnapshotV2()` and return the structured format. The old `metadata`, `a11y_tree`, and `canonical_hash` fields are preserved for backward compatibility but the new `v2_snapshot` field carries the structured data.

```javascript
case "TAKE_SNAPSHOT":
    const legacySnapshot = await takeSnapshot();
    const v2Snapshot = await takeSnapshotV2();
    sendResponse({
        ...legacySnapshot,
        v2_snapshot: v2Snapshot,
    });
    break;
```

---

## 8. Data Structures

### Error Types

```python
class SnapshotError(Exception):
    """Deterministic snapshot rejection error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

# Error codes (LOCKED)
# E_JSON_PARSE      - json parse error
# E_SCHEMA_KEYS     - schema keys mismatch: <path>
# E_TYPE            - type error: <path>
# E_ATTR_FORBIDDEN  - forbidden attr: <key>
# E_DEPTH_LIMIT     - depth limit exceeded
# E_NODE_LIMIT      - node limit exceeded
```

### Canonical Result

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CanonicalSnapshot:
    """Result of successful canonicalization."""
    canonical_bytes: bytes       # UTF-8 canonical JSON
    snapshot_sha256: str         # Lowercase hex SHA-256
    size_bytes: int              # Length of canonical_bytes
    landmarks: list[Landmark]    # Extracted structural landmarks
    node_count: int              # Total nodes in canonical DOM
```

---

## 9. State Machine

```
STATE_SET:
  - RAW_PARSED         (JSON bytes decoded to Python dict)
  - VALIDATED           (Schema, types, limits, attr policy checked)
  - VOLATILES_REMOVED   (STRIP_ATTRS removed)
  - SORTED              (Keys and children sorted deterministically)
  - WHITESPACE_NORMAL   (Whitespace collapsed and normalized)
  - UNICODE_NORMAL      (NFC normalization, tag lowercasing)
  - CANONICALIZED       (JSON serialized, SHA-256 computed)
  - REJECTED            (Error raised, no canonical output)

TRANSITIONS (LOCKED):
  RAW_PARSED       -> VALIDATED
  VALIDATED        -> VOLATILES_REMOVED
  VOLATILES_REMOVED -> SORTED
  SORTED           -> WHITESPACE_NORMAL
  WHITESPACE_NORMAL -> UNICODE_NORMAL
  UNICODE_NORMAL   -> CANONICALIZED
  ANY              -> REJECTED (on first error)

FORBIDDEN_STATES:
  - TIMESTAMP_IN_SNAPSHOT
  - RANDOM_ID_DEPENDENT
  - ENV_DEPENDENT_ORDERING
  - BEST_EFFORT_CANONICALIZE
  - SILENT_ATTR_DROPS (only STRIP_ATTRS are silent; unknown -> REJECT)
```

### State Diagram

```
  [*] --> RAW_PARSED
  RAW_PARSED --> VALIDATED
  RAW_PARSED --> REJECTED: parse/schema/type/limits
  VALIDATED --> VOLATILES_REMOVED
  VALIDATED --> REJECTED: forbidden attr
  VOLATILES_REMOVED --> SORTED
  SORTED --> WHITESPACE_NORMAL
  WHITESPACE_NORMAL --> UNICODE_NORMAL
  UNICODE_NORMAL --> CANONICALIZED
  CANONICALIZED --> [*]
  REJECTED --> [*]
```

---

## 10. Determinism Guarantee

### Proof of Reproducibility

The pipeline is deterministic because every step is a pure function (no side effects, no randomness, no time dependency):

1. **Validation:** Exact key set comparison, exact type checks
2. **Volatile removal:** Set membership (frozen sets)
3. **Sorting:** `sorted()` on ASCII strings (total order)
4. **Whitespace:** `str.split()` + `" ".join()` (deterministic)
5. **Unicode:** `unicodedata.normalize("NFC", s)` (canonical form, stable)
6. **JSON:** `json.dumps(sort_keys=True, separators=(",",":"))` (deterministic)
7. **Hash:** SHA-256 (deterministic)

### Forbidden Imports (LOCKED)

The canonicalizer module MUST NOT import:
- `time`, `datetime` (no timestamps in pipeline)
- `uuid`, `random` (no randomness)
- `requests`, `httpx`, `socket` (no network)
- `subprocess`, `os.system` (no shell)

### Verification Test

```python
def test_determinism(raw_bytes: bytes, iterations: int = 100) -> None:
    """Same input bytes must produce identical output every time."""
    results = set()
    for _ in range(iterations):
        canonical_bytes, sha256_hex = canonicalize_snapshot_v01(raw_bytes)
        results.add(sha256_hex)
    assert len(results) == 1, f"Non-deterministic: {len(results)} distinct hashes"
```

---

## 11. Integration Points

### 11.1 Phase A -> B1 (Input)

Episode recording in `background.js` calls `takeSnapshot()` after navigate/click/type. Phase B upgrades this to capture structured DOM via `takeSnapshotV2()`. The raw v2 snapshot bytes are passed to `canonicalize_snapshot_v01()`.

```
background.js:takeSnapshot()
    -> content.js:takeSnapshotV2()
    -> JSON.stringify(v2_snapshot)
    -> canonicalize_snapshot_v01(bytes)
    -> (canonical_bytes, sha256)
```

### 11.2 B1 -> B2 (Output to Episode Compiler)

The episode-to-recipe compiler (B2) consumes canonical snapshots:

```python
# In B2 compiler
for step_id, raw_snapshot in episode["snapshots"].items():
    raw_bytes = json.dumps(raw_snapshot).encode("utf-8")
    canonical_bytes, sha256 = canonicalize_snapshot_v01(raw_bytes)
    landmarks = extract_landmarks(json.loads(canonical_bytes)["dom"])

    recipe["snapshots"][f"snapshot_{step_id}"] = {
        "step": step_id,
        "sha256": sha256,
        "landmarks": [asdict(lm) for lm in landmarks],
    }
```

### 11.3 B1 -> B3 (Output to Integration Verification)

Integration verification uses snapshot comparison (drift detection from Wish 25.2):

```python
# During replay verification
expected_hash = recipe["snapshots"]["snapshot_0"]["sha256"]
current_raw = capture_current_dom()  # v2 structured capture
current_bytes, current_hash = canonicalize_snapshot_v01(current_raw)

if current_hash != expected_hash:
    drift_report = classify_snapshot_drift_v01(expected_bytes, current_bytes)
    # Typed drift: NO_DRIFT, DRIFT_TAG, DRIFT_TEXT, DRIFT_ATTRS, etc.
```

---

## 12. File Structure

### New Files

```
solace_cli/core/browser_recipe/
    __init__.py
    canonical_snapshot_v01.py      # 5-step pipeline + landmarks
    canonical_snapshot_types_v01.py # SnapshotError, CanonicalSnapshot, Landmark

tests/
    test_wish_25_1_canonical_snapshot_v01.py  # 10+ deterministic tests

canon/prime-browser/extension/
    content.js                     # Modified: add captureStructuredDOM + takeSnapshotV2
```

### Surface Lock (LOCKED)

```
SURFACE_LOCK:
  ALLOWED_MODULES:
    - solace_cli/core/browser_recipe/
    - tests/
  ALLOWED_NEW_FILES:
    - solace_cli/core/browser_recipe/canonical_snapshot_v01.py
    - solace_cli/core/browser_recipe/canonical_snapshot_types_v01.py
    - tests/test_wish_25_1_canonical_snapshot_v01.py
  FORBIDDEN_IMPORTS:
    - time
    - datetime
    - uuid
    - random
    - requests
    - httpx
    - socket
    - subprocess
  ENTRYPOINTS:
    - canonicalize_snapshot_v01
    - sha256_hex
    - extract_landmarks
```

---

## 13. Success Criteria (641 Edge Tests)

### T1: Determinism (same input twice)

- **Setup:** Raw snapshot fixture A
- **Input:** `canonicalize_snapshot_v01(A)` twice
- **Expect:** Canonical bytes identical
- **Verify:** SHA-256 identical

### T2: Order independence (children reversed)

- **Setup:** Fixture B identical to A except children list reversed
- **Input:** Canonicalize A and B
- **Expect:** Canonical bytes identical
- **Verify:** Child sorting rule produces deterministic order

### T3: Strip attrs (class/style/tabindex removed)

- **Setup:** Raw includes `class`, `style`, `tabindex` attributes
- **Input:** Canonicalize
- **Expect:** Output lacks those keys, no rejection
- **Verify:** SHA-256 stable

### T4: Reject forbidden attr

- **Setup:** Raw includes `{"onclick": "alert(1)"}`
- **Input:** Canonicalize
- **Expect:** `SnapshotError("E_ATTR_FORBIDDEN", "forbidden attr: onclick")`

### T5: Reject unknown schema key

- **Setup:** Top-level includes extra key `"timestamp"`
- **Input:** Canonicalize
- **Expect:** `SnapshotError("E_SCHEMA_KEYS", "schema keys mismatch: /")`

### T6: NFC normalization

- **Setup:** Text with decomposed Unicode (e + combining accent)
- **Input:** Canonicalize
- **Expect:** Output uses NFC composed form

### T7: Newline normalization

- **Setup:** Text contains `\r\n`
- **Input:** Canonicalize
- **Expect:** Output contains `\n` only, no `\r` bytes

### T8: Canonical JSON formatting

- **Setup:** Any successful canonical output
- **Input:** Canonical bytes
- **Expect:** No `": "` or `", "` patterns, ends with exactly one `\n`

### T9: Depth limit rejection

- **Setup:** DOM depth 201
- **Input:** Canonicalize
- **Expect:** `SnapshotError("E_DEPTH_LIMIT", "depth limit exceeded")`

### T10: Node limit rejection

- **Setup:** 200,001 nodes (wide tree)
- **Input:** Canonicalize
- **Expect:** `SnapshotError("E_NODE_LIMIT", "node limit exceeded")`

### T11: Landmark extraction

- **Setup:** Canonical DOM with nav, form, button elements
- **Input:** `extract_landmarks(dom)`
- **Expect:** Landmarks detected with correct types, paths, labels

---

## 14. Stress Tests (274177)

### S1: Collision-free (1000+ snapshots)

- Generate 1000 distinct snapshots with different DOM structures
- Canonicalize all
- Verify 0 hash collisions (all 1000 SHA-256 values distinct)

### S2: Determinism at scale (100 iterations per snapshot)

- Take 10 snapshots from different page states
- Canonicalize each 100 times
- Verify each snapshot produces exactly 1 unique hash

### S3: Size variance (1KB to 1MB)

- Snapshots ranging from minimal (single node) to large (100K nodes)
- All canonicalize within 100ms
- All produce valid SHA-256

### S4: Unicode stress

- Snapshots with CJK, Arabic, emoji, combining characters
- All normalize deterministically to NFC
- No bytes differ across platforms

---

## 15. God Approval (65537)

- RTC verified: `canonicalize(parse(canonical_bytes)) == canonical_bytes`
- Proof artifacts hash correctly (SHA-256 chain)
- No timing-dependent behavior (forbidden imports enforced)
- Landmark extraction complete and accurate
- Integration with B2 compiler verified

---

## 16. Risk Assessment

### R1: Content Script Capture Fidelity (HIGH)

**Risk:** The content script capture may produce different DOM structures on different page loads (dynamic content, lazy loading, ads).

**Mitigation:** The canonicalizer operates on whatever DOM is captured. Snapshot comparison (Wish 25.2) detects drift between expected and actual states. The volatility policy filters known sources of non-determinism. The `captureStructuredDOM` function pre-filters at the source.

### R2: Attribute Whitelist Too Restrictive (MEDIUM)

**Risk:** Some useful attributes (like `data-testid`, `data-tooltip`) may be blocked by the strict ALLOWED set.

**Mitigation:** The ALLOWED set can be extended in v0.2 if needed. For v0.1, the strict policy ensures correctness over completeness. The capture layer filters unknown attrs before they reach the canonicalizer.

### R3: Large DOM Performance (LOW)

**Risk:** Pages with 100K+ nodes may be slow to canonicalize.

**Mitigation:** The 200K node limit prevents unbounded computation. Benchmark target is <100ms for typical pages (1K-10K nodes). SHA-256 of the canonical JSON is fast (>1GB/s on modern hardware).

### R4: Child Sort Key Collisions (LOW)

**Risk:** Two sibling nodes with identical (tag, id, name, refid, text[:32]) tuples produce ambiguous ordering.

**Mitigation:** This is acceptable in v0.1 -- the sort is stable, so insertion order is the tiebreaker. If this causes issues, v0.2 can add a position index to the sort key.

---

## 17. Gamification Integration

### Quest Contract

```yaml
quest_id: "B1_SNAPSHOT_CANONICALIZATION"
star: "SNAPSHOT_CANONICALIZATION"
channel: 5
glow: 90
xp_reward: 500

quest_contract:
  goal: "5-step deterministic snapshot canonicalization with SHA-256"
  checks:
    - "Step 0: Schema validation rejects invalid input"
    - "Step 1: Volatile attributes stripped or rejected"
    - "Step 2: Keys and children sorted deterministically"
    - "Step 3: Whitespace normalized"
    - "Step 4: Unicode NFC normalized"
    - "Step 5: JSON canonicalized, SHA-256 hashed"
    - "Landmarks extracted from canonical DOM"
  verification: "641 -> 274177 -> 65537"
```

### XP Distribution

- Solver (Implementation): 200 XP -- 5-step pipeline + landmark extraction
- Skeptic (Verification): 300 XP -- 10 edge tests + 4 stress tests + determinism proof

---

## 18. Open Questions

1. **Snapshot capture timing:** Should we wait for network idle before capturing? (Deferred to Phase C replay design)
2. **Shadow DOM:** Should we traverse into shadow roots? (Not for v0.1; add in v0.2 if needed)
3. **iframes:** Should child frames be captured? (Not for v0.1; single-frame focus)

---

**Version:** 1.0.0
**Auth:** 65537
**Northstar:** Phuc Forecast
**Status:** Design Complete -- Ready for Solver Implementation

*"Deterministic snapshots: fingerprint pages, not pixels."*
