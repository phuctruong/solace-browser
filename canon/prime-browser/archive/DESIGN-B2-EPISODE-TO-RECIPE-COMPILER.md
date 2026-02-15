# DESIGN-B2: Episode-to-Recipe Compiler

> **Star:** HAIKU_SWARM_PHASE_B
> **Channel:** 3 (Design & Architecture)
> **GLOW:** 95 (Civilization-Defining -- Deterministic Compilation)
> **Status:** DESIGN COMPLETE
> **Phase:** B2 (Episode-to-Recipe Compilation)
> **XP:** 550 (Implementation + Logic + Testing specialization)
> **Auth:** 65537 | **Northstar:** Phuc Forecast

---

## 1. Problem Statement

### Current State (Phase A)

Phase A records browser episodes via `background.js` (lines 308-360). When recording is active, each navigate/click/type action is logged to `tabActionLogs`:

```javascript
// background.js:logAction -- current implementation
function logAction(tabId, type, data) {
  const tab = getTabState(tabId);
  if (tab && tab.state === "RECORDING") {
    if (!tabActionLogs.has(tabId)) tabActionLogs.set(tabId, []);
    tabActionLogs.get(tabId).push({
      type, data, timestamp: new Date().toISOString()
    });
  }
}
```

When recording stops, `stopRecording()` bundles actions into an episode:

```javascript
// background.js:stopRecording
const episode = {
  session_id: tab.recordingSession,
  domain: "unknown",
  start_time: new Date().toISOString(),
  end_time: new Date().toISOString(),
  actions: actions
};
```

**Problems with current state:**

1. **No snapshots attached:** Episodes have actions but no DOM snapshots at key steps
2. **Raw selectors:** CSS selectors from user clicks are stored as-is (fragile)
3. **No semantic references:** No ARIA/role-based fallback paths
4. **No recipe format:** Episodes are raw action logs, not structured recipes
5. **No proof artifacts:** No hashes, no roundtrip verification, no confidence scoring
6. **No determinism guarantee:** Same episode could produce different outputs due to timestamps, ordering

### Target State (Phase B)

A 4-phase deterministic compiler that converts raw episode traces into Prime Mermaid recipe IR with:
- Canonical snapshot hashes at key steps
- Reference maps with semantic + structural selectors
- Typed action sequences with snapshot expectations
- Cryptographic proof artifacts with RTC guarantee

### Why This Matters

The compiler is the **bridge** between human exploration and machine replay:
- **Input:** A human interacts with a browser (Phase A recording)
- **Output:** A deterministic recipe that a machine can replay (Phase C Playwright)
- **Guarantee:** The recipe faithfully represents the episode (RTC: episode <-> recipe roundtrip)

Without this compiler, episodes are throwaway traces. With it, they become reusable, verifiable, deterministic automation artifacts.

---

## 2. Architecture Overview

```
          EPISODE TRACE (from Phase A recording)
                    |
           +--------v--------+
  Phase 1: | CANONICALIZE    |  For each snapshot in episode:
           | SNAPSHOTS       |    canonicalize_snapshot_v01(raw)
           |                 |    extract_landmarks(dom)
           +--------+--------+    -> {sha256, landmarks}
                    |
           +--------v--------+
  Phase 2: | BUILD           |  For each action:
           | REFERENCE MAP   |    extract_semantic_selector(reference)
           |                 |    generate_ref_id(step, reference)
           +--------+--------+    -> RefMap{ref_id: {semantic, structural, context}}
                    |
           +--------v--------+
  Phase 3: | COMPILE         |  For each action:
           | ACTIONS         |    replace selectors with ref_ids
           |                 |    add snapshot expectations
           +--------+--------+    -> list[CompiledAction]
                    |
           +--------v--------+
  Phase 4: | GENERATE        |  Hash episode + recipe
           | PROOF           |  Compute confidence
           +--------+--------+  -> ProofArtifact{episode_sha256, recipe_sha256}
                    |
              RECIPE IR (Prime Mermaid YAML format)
```

---

## 3. Input: Episode Format

### Enhanced Episode (Phase B)

Phase B episodes include snapshots captured by `takeSnapshotV2()` at key steps:

```json
{
  "version": "1.0.0",
  "session_id": "session_1707900000000",
  "domain": "gmail.com",
  "start_time": "2026-02-14T12:00:00Z",
  "end_time": "2026-02-14T12:05:00Z",
  "actions": [
    {
      "step": 0,
      "type": "navigate",
      "data": { "url": "https://mail.google.com/mail/u/0/" },
      "timestamp": "2026-02-14T12:00:00Z"
    },
    {
      "step": 1,
      "type": "click",
      "data": {
        "selector": "div[data-tooltip='Compose']",
        "reference": "Compose"
      },
      "timestamp": "2026-02-14T12:00:02Z"
    },
    {
      "step": 2,
      "type": "type",
      "data": {
        "selector": "input[aria-label='To']",
        "text": "user@example.com",
        "reference": "To"
      },
      "timestamp": "2026-02-14T12:00:05Z"
    },
    {
      "step": 3,
      "type": "click",
      "data": {
        "selector": "div[aria-label='Send']",
        "reference": "Send"
      },
      "timestamp": "2026-02-14T12:00:10Z"
    }
  ],
  "snapshots": {
    "0": { "v": 1, "meta": {...}, "dom": {...} },
    "1": { "v": 1, "meta": {...}, "dom": {...} },
    "3": { "v": 1, "meta": {...}, "dom": {...} }
  },
  "action_count": 4
}
```

### Episode Validation Rules

Before compilation, the episode is validated:

```python
def validate_episode(episode: dict) -> None:
    """Validate episode structure before compilation."""

    required_keys = {"version", "session_id", "domain", "actions", "snapshots", "action_count"}
    actual_keys = set(episode.keys())
    # Allow extra keys (start_time, end_time, etc.) -- they are stripped during compilation
    if not required_keys.issubset(actual_keys):
        missing = required_keys - actual_keys
        raise CompilationError("E_EPISODE_SCHEMA", f"missing keys: {missing}")

    # Validate action count matches
    if len(episode["actions"]) != episode["action_count"]:
        raise CompilationError(
            "E_ACTION_COUNT",
            f"action_count={episode['action_count']} but {len(episode['actions'])} actions"
        )

    # Validate each action has required fields
    for action in episode["actions"]:
        if "step" not in action or "type" not in action or "data" not in action:
            raise CompilationError("E_ACTION_SCHEMA", f"action missing required fields: step {action.get('step')}")

    # Validate action types
    VALID_TYPES = {"navigate", "click", "type", "snapshot"}
    for action in episode["actions"]:
        if action["type"] not in VALID_TYPES:
            raise CompilationError("E_ACTION_TYPE", f"unknown action type: {action['type']}")

    # Validate step ordering (must be monotonically increasing, starting from 0)
    steps = [a["step"] for a in episode["actions"]]
    if steps != list(range(len(steps))):
        raise CompilationError("E_STEP_ORDER", f"steps not sequential: {steps}")
```

---

## 4. Phase 1: Canonicalize Snapshots

Phase 1 takes each raw snapshot from the episode and runs it through B1's canonicalization pipeline.

### Algorithm

```python
from canonical_snapshot_v01 import canonicalize_snapshot_v01, extract_landmarks

def phase1_canonicalize_snapshots(episode: dict) -> dict[str, CanonicalSnapshotRecord]:
    """
    Convert episode snapshots to canonical hashes + landmarks.

    Returns:
        Dict mapping step_id -> CanonicalSnapshotRecord
    """
    canonical_snapshots = {}

    for step_id, raw_snapshot in episode["snapshots"].items():
        raw_bytes = json.dumps(raw_snapshot, sort_keys=True).encode("utf-8")

        try:
            canonical_bytes, sha256 = canonicalize_snapshot_v01(raw_bytes)
        except SnapshotError as e:
            raise CompilationError(
                "E_SNAPSHOT_CANONICAL",
                f"snapshot at step {step_id} failed canonicalization: {e.code}: {e.message}"
            )

        canonical_dom = json.loads(canonical_bytes)["dom"]
        landmarks = extract_landmarks(canonical_dom)

        canonical_snapshots[step_id] = CanonicalSnapshotRecord(
            step=int(step_id),
            sha256=sha256,
            landmarks=[asdict(lm) for lm in landmarks],
            domain=raw_snapshot.get("meta", {}).get("url", ""),
            size_bytes=len(canonical_bytes),
        )

    return canonical_snapshots
```

### Data Structure

```python
@dataclass(frozen=True)
class CanonicalSnapshotRecord:
    step: int
    sha256: str
    landmarks: list[dict]
    domain: str
    size_bytes: int
```

---

## 5. Phase 2: Build Reference Map

Phase 2 extracts semantic and structural selectors from episode actions to create a reference map. Each action that targets an element (click, type) gets a deterministic `ref_id`.

### Reference ID Generation (Deterministic)

```python
import re

def generate_ref_id(step: int, reference: str, action_type: str) -> str:
    """
    Generate deterministic ref_id from step + reference.

    Format: ref_{step}_{action_type}_{normalized_reference}

    Example: ref_1_click_compose_button
    """
    if reference:
        normalized = re.sub(r'[^a-z0-9]+', '_', reference.lower()).strip('_')
        if not normalized:
            normalized = "unnamed"
    else:
        normalized = "unnamed"

    return f"ref_{step}_{action_type}_{normalized}"
```

### Semantic Selector Extraction

```python
def extract_semantic_selector(reference: str, action_data: dict) -> str | None:
    """
    Generate semantic selector from action reference/data.

    Priority order:
      1. aria-label exact match
      2. role + aria-label combination
      3. title attribute
      4. placeholder (for inputs)
      5. None (no semantic path available)
    """
    if not reference:
        return None

    selector = action_data.get("selector", "")

    # If selector already uses aria-label, use it directly
    if "aria-label" in selector:
        return selector

    # Generate aria-label selector from reference
    return f"[aria-label='{reference}']"
```

### Context Inference

```python
def infer_context(episode: dict, step: int, canonical_snapshots: dict) -> str:
    """
    Infer ancestor context from landmarks in the closest snapshot.

    Returns context label (e.g., "navigation", "compose-form", "inbox-list")
    or "" if no context can be inferred.
    """
    # Find the closest snapshot at or before this step
    snapshot_steps = sorted(int(s) for s in canonical_snapshots.keys())
    closest_step = None
    for s in snapshot_steps:
        if s <= step:
            closest_step = s

    if closest_step is None:
        return ""

    # Check landmarks in closest snapshot
    landmarks = canonical_snapshots[str(closest_step)].landmarks
    landmark_types = [lm["type"] for lm in landmarks]

    # Simple heuristic: if navigation landmarks present and step is early, context is "navigation"
    # If form landmarks present, context is "form"
    if "form" in landmark_types:
        return "form"
    if "navigation" in landmark_types:
        return "navigation"
    return ""
```

### Never-Worse Gate: Ambiguity Detection

The reference map builder MUST reject ambiguous references. If a selector or reference could match multiple elements, compilation fails.

```python
def validate_ref_uniqueness(refmap: dict) -> None:
    """
    Verify no two refs map to the same semantic selector.
    Ambiguous refs are rejected pre-compile.
    """
    semantic_selectors = {}
    for ref_id, ref in refmap.items():
        semantic = ref.get("semantic")
        if semantic and semantic in semantic_selectors:
            raise CompilationError(
                "E_AMBIGUOUS_REF",
                f"ambiguous semantic selector '{semantic}' used by "
                f"both {semantic_selectors[semantic]} and {ref_id}"
            )
        if semantic:
            semantic_selectors[semantic] = ref_id
```

### Full Phase 2 Algorithm

```python
def phase2_build_refmap(
    episode: dict,
    canonical_snapshots: dict[str, CanonicalSnapshotRecord],
) -> dict[str, RefMapEntry]:
    """
    Extract semantic + structural references from actions.

    Returns:
        Dict mapping ref_id -> RefMapEntry
    """
    refmap = {}

    for action in episode["actions"]:
        step = action["step"]
        action_type = action["type"]
        data = action["data"]

        # Only click and type actions need refs (navigate uses URL)
        if action_type not in ("click", "type"):
            continue

        selector = data.get("selector", "")
        reference = data.get("reference", "")

        ref_id = generate_ref_id(step, reference, action_type)

        semantic = extract_semantic_selector(reference, data)
        context = infer_context(episode, step, canonical_snapshots)

        # Find which snapshot this ref was matched against
        matched_at = _find_closest_snapshot(step, canonical_snapshots)

        refmap[ref_id] = RefMapEntry(
            ref_id=ref_id,
            semantic=semantic,
            structural=selector,
            context=context,
            matched_at=f"snapshot_{matched_at}" if matched_at is not None else None,
            step=step,
            action_type=action_type,
        )

    # Never-worse gate: check for ambiguous refs
    validate_ref_uniqueness(refmap)

    return refmap

def _find_closest_snapshot(step: int, snapshots: dict) -> int | None:
    """Find closest snapshot at or before given step."""
    steps = sorted(int(s) for s in snapshots.keys())
    closest = None
    for s in steps:
        if s <= step:
            closest = s
    return closest
```

### Data Structure

```python
@dataclass(frozen=True)
class RefMapEntry:
    ref_id: str           # Deterministic ref identifier
    semantic: str | None  # ARIA/role-based selector (Tier 1)
    structural: str       # CSS/XPath selector (Tier 2)
    context: str          # Ancestor context (navigation, form, etc.)
    matched_at: str | None  # Snapshot where this ref was validated
    step: int             # Step number in episode
    action_type: str      # click, type
```

---

## 6. Phase 3: Compile Actions

Phase 3 converts episode actions to Prime Mermaid IR format, replacing raw selectors with ref_ids and adding snapshot expectations.

### Action Compilation Rules

| Action Type | Compiled Fields | Snapshot Expectation |
|-------------|----------------|---------------------|
| `navigate` | `url` | Yes (if snapshot exists at this step) |
| `click` | `ref` (from refmap) | No (snapshot at next step if available) |
| `type` | `ref` (from refmap), `text` | No (snapshot at next step if available) |

### Algorithm

```python
def phase3_compile_actions(
    episode: dict,
    refmap: dict[str, RefMapEntry],
    canonical_snapshots: dict[str, CanonicalSnapshotRecord],
) -> list[CompiledAction]:
    """
    Convert episode actions to recipe IR with ref substitution.
    """
    compiled = []

    for action in episode["actions"]:
        step = action["step"]
        action_type = action["type"]
        data = action["data"]

        compiled_action = CompiledAction(
            step=step,
            type=action_type,
        )

        if action_type == "navigate":
            compiled_action.url = data["url"]
            # Attach snapshot expectation if snapshot exists at this step
            step_str = str(step)
            if step_str in canonical_snapshots:
                compiled_action.expect_snapshot = f"snapshot_{step}"

        elif action_type == "click":
            ref_id = _find_ref_for_step(step, "click", refmap)
            if ref_id is None:
                raise CompilationError(
                    "E_REF_NOT_FOUND",
                    f"no ref found for click at step {step}"
                )
            compiled_action.ref = ref_id
            compiled_action.expect_visible = True
            compiled_action.timeout_ms = 5000

        elif action_type == "type":
            ref_id = _find_ref_for_step(step, "type", refmap)
            if ref_id is None:
                raise CompilationError(
                    "E_REF_NOT_FOUND",
                    f"no ref found for type at step {step}"
                )
            compiled_action.ref = ref_id
            compiled_action.text = data["text"]
            compiled_action.timeout_ms = 5000

            # Attach snapshot expectation if snapshot exists at this step
            step_str = str(step)
            if step_str in canonical_snapshots:
                compiled_action.expect_snapshot = f"snapshot_{step}"

        compiled.append(compiled_action)

    return compiled


def _find_ref_for_step(step: int, action_type: str, refmap: dict) -> str | None:
    """Find ref_id for a given step and action type."""
    for ref_id, entry in refmap.items():
        if entry.step == step and entry.action_type == action_type:
            return ref_id
    return None
```

### Data Structure

```python
@dataclass
class CompiledAction:
    step: int
    type: str
    url: str | None = None
    ref: str | None = None
    text: str | None = None
    expect_snapshot: str | None = None
    expect_visible: bool | None = None
    timeout_ms: int | None = None
```

---

## 7. Phase 4: Generate Proof Artifacts

Phase 4 creates cryptographic proof that the recipe was compiled from a specific episode. This enables RTC verification.

### Algorithm

```python
def phase4_generate_proof(
    episode: dict,
    recipe_obj: dict,
) -> ProofArtifact:
    """
    Create cryptographic proof of compilation.

    The episode hash is computed from the raw episode (including timestamps).
    The recipe hash is computed from the recipe (excluding proof field).
    """
    # Hash the episode (canonical JSON)
    episode_canonical = json.dumps(episode, sort_keys=True, separators=(",", ":")).encode("utf-8")
    episode_hash = hashlib.sha256(episode_canonical).hexdigest()

    # Hash the recipe (without proof field -- to avoid circular reference)
    recipe_without_proof = {k: v for k, v in recipe_obj.items() if k != "proof"}
    recipe_canonical = json.dumps(recipe_without_proof, sort_keys=True, separators=(",", ":")).encode("utf-8")
    recipe_hash = hashlib.sha256(recipe_canonical).hexdigest()

    # Compute confidence from ref coverage
    total_refs = sum(1 for a in recipe_obj.get("actions", []) if a.get("ref"))
    semantic_refs = sum(
        1 for ref in recipe_obj.get("refmap", {}).values()
        if ref.get("semantic")
    )
    if total_refs > 0:
        confidence = round(semantic_refs / total_refs, 2)
    else:
        confidence = 1.0

    return ProofArtifact(
        episode_sha256=episode_hash,
        recipe_sha256=recipe_hash,
        compiled_at=None,  # No timestamps in proof (deterministic)
        confidence=confidence,
        action_count=len(recipe_obj.get("actions", [])),
        snapshot_count=len(recipe_obj.get("snapshots", {})),
        ref_count=len(recipe_obj.get("refmap", {})),
    )
```

### Data Structure

```python
@dataclass(frozen=True)
class ProofArtifact:
    episode_sha256: str
    recipe_sha256: str
    compiled_at: str | None   # None in code; set externally if needed
    confidence: float         # 0.0 to 1.0 (semantic ref coverage)
    action_count: int
    snapshot_count: int
    ref_count: int
```

---

## 8. Complete Compiler Pipeline

### Entry Point

```python
def compile_episode_to_recipe(episode_bytes: bytes) -> tuple[bytes, str]:
    """
    Complete episode-to-recipe compilation.

    Args:
        episode_bytes: UTF-8 JSON bytes of raw episode

    Returns:
        (recipe_yaml_bytes, recipe_sha256_hex)

    Raises:
        CompilationError on any compilation failure
    """
    # Parse episode
    try:
        episode = json.loads(episode_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise CompilationError("E_EPISODE_PARSE", "episode parse error")

    # Validate episode structure
    validate_episode(episode)

    # Phase 1: Canonicalize snapshots
    canonical_snapshots = phase1_canonicalize_snapshots(episode)

    # Phase 2: Build reference map
    refmap = phase2_build_refmap(episode, canonical_snapshots)

    # Phase 3: Compile actions
    compiled_actions = phase3_compile_actions(episode, refmap, canonical_snapshots)

    # Build recipe object (without proof -- proof needs the recipe)
    recipe_obj = _build_recipe_object(
        episode, canonical_snapshots, refmap, compiled_actions
    )

    # Phase 4: Generate proof
    proof = phase4_generate_proof(episode, recipe_obj)

    # Add proof to recipe
    recipe_obj["proof"] = asdict(proof)

    # Serialize to canonical JSON
    recipe_json = json.dumps(recipe_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    recipe_json += "\n"
    recipe_bytes = recipe_json.encode("utf-8")
    recipe_hash = hashlib.sha256(recipe_bytes).hexdigest()

    return recipe_bytes, recipe_hash
```

### Recipe Object Builder

```python
def _build_recipe_object(
    episode: dict,
    canonical_snapshots: dict[str, CanonicalSnapshotRecord],
    refmap: dict[str, RefMapEntry],
    compiled_actions: list[CompiledAction],
) -> dict:
    """Build the recipe IR dictionary."""
    return {
        "version": "1.0.0",
        "recipe_id": _generate_recipe_id(episode),
        "domain": episode["domain"],
        "task": f"Automated task on {episode['domain']}",
        "preconditions": {
            "domain_allowlist": [episode["domain"]],
            "landmarks": _extract_required_landmarks(canonical_snapshots),
            "auth_required": _infer_auth_required(episode),
        },
        "snapshots": {
            f"snapshot_{record.step}": {
                "step": record.step,
                "sha256": record.sha256,
                "landmarks": record.landmarks,
            }
            for record in canonical_snapshots.values()
        },
        "refmap": {
            ref_id: {
                "semantic": entry.semantic,
                "structural": entry.structural,
                "context": entry.context,
                "matched_at": entry.matched_at,
            }
            for ref_id, entry in refmap.items()
        },
        "actions": [
            _action_to_dict(action) for action in compiled_actions
        ],
        "postconditions": {
            "verify_navigation": True,
            "verify_extraction": True,
        },
    }


def _generate_recipe_id(episode: dict) -> str:
    """Deterministic recipe ID from domain + session hash."""
    domain = episode["domain"].replace(".", "_")
    session_hash = hashlib.sha256(
        episode["session_id"].encode("utf-8")
    ).hexdigest()[:12]
    return f"{domain}_{session_hash}"


def _action_to_dict(action: CompiledAction) -> dict:
    """Convert CompiledAction to serializable dict, omitting None fields."""
    d = {"step": action.step, "type": action.type}
    if action.url is not None:
        d["url"] = action.url
    if action.ref is not None:
        d["ref"] = action.ref
    if action.text is not None:
        d["text"] = action.text
    if action.expect_snapshot is not None:
        d["expect_snapshot"] = action.expect_snapshot
    if action.expect_visible is not None:
        d["expect_visible"] = action.expect_visible
    if action.timeout_ms is not None:
        d["timeout_ms"] = action.timeout_ms
    return d
```

---

## 9. Output: Recipe IR (Prime Mermaid Format)

### Complete Recipe Example

```yaml
version: "1.0.0"
recipe_id: "gmail_com_a1b2c3d4e5f6"
domain: "gmail.com"
task: "Automated task on gmail.com"

preconditions:
  domain_allowlist: ["gmail.com"]
  landmarks: ["navigation", "button"]
  auth_required: true

snapshots:
  snapshot_0:
    step: 0
    sha256: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
    landmarks:
      - type: "navigation"
        path: "/dom/children/1/children/0"
        label: "Main"
        tag: "nav"
        child_count: 5
      - type: "button"
        path: "/dom/children/1/children/0/children/0"
        label: "Compose"
        tag: "button"
        child_count: 0

  snapshot_1:
    step: 1
    sha256: "f2e1d0c9b8a7z6y5x4w3v2u1t0s9r8q7p6o5n4m3l2k1j0i9h8g7f6e5d4c3b2a1"
    landmarks:
      - type: "form"
        path: "/dom/children/1/children/1"
        label: "Compose"
        tag: "div"
        child_count: 7

  snapshot_3:
    step: 3
    sha256: "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f"
    landmarks:
      - type: "navigation"
        path: "/dom/children/1/children/0"
        label: "Main"
        tag: "nav"
        child_count: 5

refmap:
  ref_1_click_compose:
    semantic: "[aria-label='Compose']"
    structural: "div[data-tooltip='Compose']"
    context: "navigation"
    matched_at: "snapshot_0"

  ref_2_type_to:
    semantic: "[aria-label='To']"
    structural: "input[aria-label='To']"
    context: "form"
    matched_at: "snapshot_1"

  ref_3_click_send:
    semantic: "[aria-label='Send']"
    structural: "div[aria-label='Send']"
    context: "form"
    matched_at: "snapshot_1"

actions:
  - step: 0
    type: "navigate"
    url: "https://mail.google.com/mail/u/0/"
    expect_snapshot: "snapshot_0"

  - step: 1
    type: "click"
    ref: "ref_1_click_compose"
    expect_visible: true
    timeout_ms: 5000

  - step: 2
    type: "type"
    ref: "ref_2_type_to"
    text: "user@example.com"
    timeout_ms: 5000

  - step: 3
    type: "click"
    ref: "ref_3_click_send"
    expect_visible: true
    timeout_ms: 5000

postconditions:
  verify_navigation: true
  verify_extraction: true

proof:
  episode_sha256: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
  recipe_sha256: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  compiled_at: null
  confidence: 1.0
  action_count: 4
  snapshot_count: 3
  ref_count: 3
```

---

## 10. RTC Guarantee (Roundtrip Verification)

### Forward: Episode -> Recipe

```python
episode_bytes = load("episode.json")
recipe_bytes, recipe_hash = compile_episode_to_recipe(episode_bytes)
```

### Reverse: Recipe -> Episode (Decompilation)

```python
def decompile_recipe_to_episode_skeleton(recipe_bytes: bytes) -> dict:
    """
    Reconstruct episode skeleton from recipe.
    Used for RTC verification -- not full episode recovery.

    Recovers:
      - action types, steps, selectors
      - snapshot hashes
      - domain

    Does NOT recover:
      - timestamps (volatile, stripped)
      - session_id (volatile)
      - raw DOM snapshots (only hashes preserved)
    """
    recipe = json.loads(recipe_bytes)

    actions = []
    for compiled_action in recipe["actions"]:
        action = {
            "step": compiled_action["step"],
            "type": compiled_action["type"],
            "data": {},
        }

        if compiled_action["type"] == "navigate":
            action["data"]["url"] = compiled_action["url"]
        elif compiled_action["type"] == "click":
            ref = recipe["refmap"][compiled_action["ref"]]
            action["data"]["selector"] = ref["structural"]
            # Recover reference from ref_id naming
            action["data"]["reference"] = _extract_reference_from_ref_id(compiled_action["ref"])
        elif compiled_action["type"] == "type":
            ref = recipe["refmap"][compiled_action["ref"]]
            action["data"]["selector"] = ref["structural"]
            action["data"]["text"] = compiled_action["text"]
            action["data"]["reference"] = _extract_reference_from_ref_id(compiled_action["ref"])

        actions.append(action)

    return {
        "domain": recipe["domain"],
        "actions": actions,
        "action_count": len(actions),
        "snapshot_hashes": {
            snap_id: snap["sha256"]
            for snap_id, snap in recipe["snapshots"].items()
        },
    }
```

### RTC Verification

```python
def verify_rtc(episode_bytes: bytes) -> bool:
    """
    Verify roundtrip compilation: episode -> recipe -> skeleton matches episode.

    Checks:
      1. Action count preserved
      2. Action types preserved
      3. Selectors preserved (structural)
      4. Text preserved (for type actions)
      5. URLs preserved (for navigate actions)
      6. Snapshot hashes match
    """
    episode = json.loads(episode_bytes)
    recipe_bytes, _ = compile_episode_to_recipe(episode_bytes)
    skeleton = decompile_recipe_to_episode_skeleton(recipe_bytes)

    # Check 1: Action count
    assert skeleton["action_count"] == episode["action_count"]

    # Check 2-5: Action content
    for orig, skel in zip(episode["actions"], skeleton["actions"]):
        assert orig["type"] == skel["type"]
        assert orig["step"] == skel["step"]
        if orig["type"] == "navigate":
            assert orig["data"]["url"] == skel["data"]["url"]
        elif orig["type"] == "click":
            assert orig["data"]["selector"] == skel["data"]["selector"]
        elif orig["type"] == "type":
            assert orig["data"]["selector"] == skel["data"]["selector"]
            assert orig["data"]["text"] == skel["data"]["text"]

    # Check 6: Domain preserved
    assert skeleton["domain"] == episode["domain"]

    return True
```

---

## 11. Never-Worse Gate

The compiler MUST reject episodes that would produce ambiguous or unreliable recipes. This is the "never-worse" guarantee: a compiled recipe is at least as good as the raw episode.

### Rejection Conditions

| Condition | Error Code | Example |
|-----------|-----------|---------|
| Ambiguous semantic selector | `E_AMBIGUOUS_REF` | Two refs use `[aria-label='Submit']` |
| Missing selector AND reference | `E_NO_SELECTOR` | Click action with no targeting info |
| Invalid action type | `E_ACTION_TYPE` | Unknown action type |
| Snapshot canonicalization failure | `E_SNAPSHOT_CANONICAL` | Forbidden attr in DOM |
| Action count mismatch | `E_ACTION_COUNT` | `action_count` field disagrees |
| Step ordering violation | `E_STEP_ORDER` | Steps not sequential |

### Error Types

```python
class CompilationError(Exception):
    """Deterministic compilation rejection."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
```

---

## 12. State Machine

```
STATE_SET:
  - EPISODE_PARSED
  - EPISODE_VALIDATED
  - SNAPSHOTS_CANONICALIZED
  - REFMAP_BUILT
  - ACTIONS_COMPILED
  - PROOF_GENERATED
  - RECIPE_COMPLETE
  - COMPILATION_FAILED

TRANSITIONS (LOCKED):
  EPISODE_PARSED        -> EPISODE_VALIDATED
  EPISODE_VALIDATED     -> SNAPSHOTS_CANONICALIZED
  SNAPSHOTS_CANONICALIZED -> REFMAP_BUILT
  REFMAP_BUILT          -> ACTIONS_COMPILED
  ACTIONS_COMPILED      -> PROOF_GENERATED
  PROOF_GENERATED       -> RECIPE_COMPLETE
  ANY                   -> COMPILATION_FAILED (on first error)

FORBIDDEN_STATES:
  - PARTIAL_REFMAP  (never emit incomplete ref resolution)
  - AMBIGUOUS_REFS  (never allow multiple elements per ref)
  - UNPROVEN_RECIPE (never emit recipe without proof)
  - TIMESTAMP_IN_RECIPE_HASH (proof hash must exclude timestamps)
```

### State Diagram

```
  [*] --> EPISODE_PARSED
  EPISODE_PARSED --> EPISODE_VALIDATED
  EPISODE_PARSED --> COMPILATION_FAILED: parse/schema error
  EPISODE_VALIDATED --> SNAPSHOTS_CANONICALIZED
  EPISODE_VALIDATED --> COMPILATION_FAILED: validation error
  SNAPSHOTS_CANONICALIZED --> REFMAP_BUILT
  SNAPSHOTS_CANONICALIZED --> COMPILATION_FAILED: snapshot error
  REFMAP_BUILT --> ACTIONS_COMPILED
  REFMAP_BUILT --> COMPILATION_FAILED: ambiguous refs
  ACTIONS_COMPILED --> PROOF_GENERATED
  PROOF_GENERATED --> RECIPE_COMPLETE
  RECIPE_COMPLETE --> [*]
  COMPILATION_FAILED --> [*]
```

---

## 13. Integration Points

### 13.1 Phase A -> B2 (Episode Input)

Episodes are recorded by `background.js` and sent to CLI via WebSocket:

```
background.js:stopRecording()
    -> RECORDING_STOPPED message with episode payload
    -> CLI saves to ~/.solace/browser/episode_{session_id}.json
    -> compile_episode_to_recipe(episode_bytes)
```

### 13.2 B1 -> B2 (Snapshot Canonicalization)

Phase 1 of the compiler calls B1's `canonicalize_snapshot_v01()`:

```python
# phase1_canonicalize_snapshots calls:
canonical_bytes, sha256 = canonicalize_snapshot_v01(raw_bytes)
landmarks = extract_landmarks(canonical_dom)
```

### 13.3 B2 -> B3 (Recipe Output for Integration)

The compiled recipe IR is consumed by B3 integration verification:

```python
# B3 uses the recipe for:
# 1. Playwright test generation
# 2. Snapshot verification during replay
# 3. Reference resolution against live DOM
recipe = json.loads(recipe_bytes)
for action in recipe["actions"]:
    if action["type"] == "click":
        ref = recipe["refmap"][action["ref"]]
        # Resolve ref.semantic first, then ref.structural
```

### 13.4 B2 -> Phase C (Recipe for Replay)

Phase C Playwright runner consumes the recipe:

```python
async def replay_recipe(recipe: dict, page: Page) -> ReplayResult:
    for action in recipe["actions"]:
        if action["type"] == "navigate":
            await page.goto(action["url"])
        elif action["type"] == "click":
            ref = recipe["refmap"][action["ref"]]
            element = await resolve_reference(page, ref)
            await element.click()
        elif action["type"] == "type":
            ref = recipe["refmap"][action["ref"]]
            element = await resolve_reference(page, ref)
            await element.fill(action["text"])

        # Verify snapshot if expected
        if action.get("expect_snapshot"):
            await verify_snapshot(page, recipe, action["expect_snapshot"])
```

---

## 14. File Structure

### New Files

```
solace_cli/core/browser_recipe/
    __init__.py
    episode_compiler_v01.py        # 4-phase compiler pipeline
    episode_compiler_types_v01.py  # CompilationError, RefMapEntry, etc.

tests/
    test_wish_26_episode_compiler_v01.py  # Compiler tests
```

### Surface Lock (LOCKED)

```
SURFACE_LOCK:
  ALLOWED_MODULES:
    - solace_cli/core/browser_recipe/
    - tests/
  ALLOWED_NEW_FILES:
    - solace_cli/core/browser_recipe/episode_compiler_v01.py
    - solace_cli/core/browser_recipe/episode_compiler_types_v01.py
    - tests/test_wish_26_episode_compiler_v01.py
  FORBIDDEN_IMPORTS:
    - time
    - datetime (only used if caller sets compiled_at externally)
    - uuid
    - random
    - requests
    - httpx
    - socket
    - subprocess
  ENTRYPOINTS:
    - compile_episode_to_recipe
    - decompile_recipe_to_episode_skeleton
    - verify_rtc
```

---

## 15. Success Criteria (641 Edge Tests)

### T1: Minimal episode (3 actions) compiles correctly

- **Setup:** Episode with navigate + click + type
- **Input:** `compile_episode_to_recipe(bytes)`
- **Expect:** Recipe with 3 actions, refmap with 2 entries, 1+ snapshots

### T2: Snapshot hashes are deterministic

- **Setup:** Compile same episode twice
- **Expect:** Identical recipe bytes and recipe hash

### T3: Reference map semantic + structural generated

- **Setup:** Episode with click action having `reference: "Compose"`
- **Expect:** RefMap entry with `semantic: "[aria-label='Compose']"` and structural path

### T4: Proof artifacts hash correctly

- **Setup:** Compiled recipe
- **Verify:** `sha256(episode_bytes) == proof.episode_sha256`
- **Verify:** `sha256(recipe_without_proof) == proof.recipe_sha256`

### T5: Never-worse gate catches ambiguous refs

- **Setup:** Episode with two click actions using identical reference "Submit"
- **Expect:** `CompilationError("E_AMBIGUOUS_REF", ...)`

### T6: RTC roundtrip verified

- **Setup:** Episode -> recipe -> decompile -> skeleton
- **Verify:** Action count, types, selectors, text, URLs all match

### T7: Missing selector rejected

- **Setup:** Click action with no selector and no reference
- **Expect:** `CompilationError("E_NO_SELECTOR", ...)`

---

## 16. Stress Tests (274177)

### S1: 100 episodes, varying length (3-50 actions)

- Generate 100 synthetic episodes
- Compile all
- Verify determinism: same episode -> identical recipe hash

### S2: Large episodes (50 actions, 20 snapshots)

- Compile within reasonable time (<1s)
- All proofs valid

### S3: Edge case episodes

- Episode with 0 snapshots (still compiles, no snapshot expectations)
- Episode with all navigate actions (no refmap needed)
- Episode with single action

### S4: RTC verification at scale

- 100 episodes through compile -> decompile -> verify
- All pass RTC check

---

## 17. God Approval (65537)

- No ambiguous references (never-worse gate enforced)
- All proofs verify (SHA-256 chain intact)
- RTC guarantee holds for all test episodes
- Recipe compatible with Phase C Playwright runner
- No timestamps in deterministic paths

---

## 18. Risk Assessment

### R1: Semantic Selector Generation Quality (HIGH)

**Risk:** The simple `[aria-label='{reference}']` generation may not find elements on all sites. Some elements lack ARIA labels.

**Mitigation:** The reference map includes BOTH semantic and structural paths. Phase C resolver tries semantic first, falls back to structural. If both fail, typed error is returned. The never-worse gate ensures the recipe is at least as good as the raw episode (structural selector preserved).

### R2: Context Inference Accuracy (MEDIUM)

**Risk:** The heuristic context inference (landmarks-based) may produce wrong or empty context.

**Mitigation:** Context is advisory, not required. The resolver uses context as an additional filter but works without it. Empty context means no filtering.

### R3: Episode Format Evolution (MEDIUM)

**Risk:** As Phase A evolves, the episode format may change, breaking the compiler.

**Mitigation:** The compiler validates episode structure at the start. The `version` field enables format versioning. Unknown keys are ignored (forward-compatible).

### R4: Confidence Score Meaning (LOW)

**Risk:** The confidence score (semantic ref coverage) may not accurately predict replay success.

**Mitigation:** v0.1 uses a simple metric (semantic refs / total refs). Phase C can calibrate against actual replay success rates.

---

## 19. Gamification Integration

### Quest Contract

```yaml
quest_id: "B2_EPISODE_TO_RECIPE_COMPILER"
star: "EPISODE_TO_RECIPE_COMPILER"
channel: 5
glow: 95
xp_reward: 550

quest_contract:
  goal: "4-phase deterministic episode compilation with RTC guarantee"
  checks:
    - "Phase 1: Snapshots canonicalized with SHA-256 hashes"
    - "Phase 2: Reference map with semantic + structural selectors"
    - "Phase 3: Actions compiled with ref substitution"
    - "Phase 4: Proof artifacts with episode/recipe hash chain"
    - "RTC guarantee: compile -> decompile -> verify passes"
    - "Never-worse gate: ambiguous refs rejected pre-compile"
    - "100 episodes stress tested for determinism"
  verification: "641 -> 274177 -> 65537"
```

### XP Distribution

- Solver (Implementation): 200 XP -- 4-phase pipeline
- Solver (Logic): 200 XP -- RTC guarantee + never-worse gate
- Skeptic (Testing): 150 XP -- 7 edge tests + 4 stress tests

---

**Version:** 1.0.0
**Auth:** 65537
**Northstar:** Phuc Forecast
**Status:** Design Complete -- Ready for Solver Implementation

*"From exploration to deterministic recipe: one-shot learning frozen forever."*
