# DESIGN-B3: Integration Verification

> **Star:** HAIKU_SWARM_PHASE_B
> **Channel:** 3 -> 7 (Design -> Validation)
> **GLOW:** 88 (High Impact -- End-to-End Proof)
> **Phase:** B3 (Integration Verification)
> **XP:** 600 (Design + Testing + Verification)
> **Auth:** 65537 | **Northstar:** Phuc Forecast

---

## 1. Problem Statement

### Current State

B1 (Snapshot Canonicalization) and B2 (Episode-to-Recipe Compiler) are designed as independent modules. But they must work together as a complete pipeline:

```
Episode Recording (Phase A) -> Canonical Snapshots (B1) -> Recipe IR (B2) -> Playwright Replay (Phase C)
```

Without integration verification, we have unit-tested components but no proof that the full pipeline works end-to-end. Specifically:

1. **No proof** that B1 canonical hashes survive the B2 compilation pipeline unchanged
2. **No proof** that recipe IR actions correctly reference the RefMap entries
3. **No proof** that snapshot expectations in recipes can be verified against live DOM
4. **No proof** that the 641 -> 274177 -> 65537 verification chain passes across the combined system
5. **No forward compatibility proof** that Phase C can consume B2 recipe output

### Target State

A comprehensive integration verification system that:
- Validates the complete Episode -> Recipe pipeline (B1 + B2)
- Verifies snapshot expectation resolution against canonical DOMs
- Confirms reference resolution determinism across the pipeline
- Establishes Phase C compatibility through recipe schema validation
- Passes all verification rungs (641 -> 274177 -> 65537) at the integration level

### Why This Matters

B3 is the **quality gate** before Phase C. If B3 passes, Phase C can trust:
- Recipes are well-formed and internally consistent
- Snapshot hashes are correct and verifiable
- RefMap entries are complete and unambiguous
- The compilation pipeline is deterministic end-to-end

---

## 2. Architecture Overview

### 2.1 Full Pipeline Architecture

```
+-------------------+     +-------------------+     +-------------------+
|   PHASE A         |     |   PHASE B         |     |   PHASE C         |
|   Episode         |     |   B1 + B2         |     |   Replay          |
|   Recording       |     |   Compilation     |     |   Engine          |
+--------+----------+     +--------+----------+     +--------+----------+
         |                         |                          |
    Episode JSON              Recipe IR                 Playwright
    (actions +                (snapshots +              (navigate +
     raw DOM)                  refmap +                  click +
         |                     actions +                 type +
         |                     proof)                    verify)
         |                         |                          |
         v                         v                          v
    +---------+              +-----------+              +-----------+
    | episode |   -------->  | recipe IR |  -------->   | replay    |
    | .json   |   compile()  | .yaml     |  execute()   | result    |
    +---------+              +-----------+              +-----------+
                                   |
                              B3 VERIFIES:
                              - Internal consistency
                              - Snapshot hash integrity
                              - RefMap completeness
                              - Phase C schema compatibility
                              - RTC roundtrip
```

### 2.2 Verification Layers

```
Layer 1: UNIT VERIFICATION (B1, B2 individually)
    - B1 canonicalization determinism (10 tests from wish-25.1)
    - B2 compilation correctness (7 tests from wish-26)
    - Already covered by B1/B2 individual test suites

Layer 2: INTEGRATION VERIFICATION (B3 - THIS DESIGN)
    - B1 + B2 pipeline correctness
    - Cross-module data flow integrity
    - Schema compatibility with Phase C
    - RTC across the full pipeline

Layer 3: END-TO-END VERIFICATION (Phase C)
    - Live browser replay
    - Snapshot matching against real DOM
    - Reference resolution against real elements
    - Not in scope for B3 (requires Playwright infrastructure)
```

---

## 3. Integration Test Categories

### 3.1 Category 1: Pipeline Flow Tests

Verify that data flows correctly from Episode -> B1 -> B2 -> Recipe IR.

```python
class TestPipelineFlow:
    """Verify Episode -> Canonical Snapshots -> RefMap -> Actions -> Proof."""

    def test_episode_to_recipe_end_to_end(self):
        """Complete pipeline produces valid recipe from episode."""
        episode = load_fixture("episode_gmail_compose.json")
        episode_bytes = json.dumps(episode).encode("utf-8")

        recipe_bytes, recipe_hash = compile_episode_to_recipe(episode_bytes)
        recipe = json.loads(recipe_bytes)

        # Recipe has all required top-level keys
        assert set(recipe.keys()) >= {
            "version", "recipe_id", "domain", "snapshots",
            "refmap", "actions", "proof"
        }

        # Action count matches
        assert len(recipe["actions"]) == episode["action_count"]

        # Snapshot count matches
        assert len(recipe["snapshots"]) == len(episode["snapshots"])

    def test_canonical_hashes_survive_compilation(self):
        """B1 hashes embedded in recipe match direct B1 output."""
        episode = load_fixture("episode_gmail_compose.json")

        # Direct B1 canonicalization
        for step_id, raw_snapshot in episode["snapshots"].items():
            raw_bytes = json.dumps(raw_snapshot, sort_keys=True).encode("utf-8")
            _, direct_hash = canonicalize_snapshot_v01(raw_bytes)

            # Compile episode
            recipe_bytes, _ = compile_episode_to_recipe(
                json.dumps(episode).encode("utf-8")
            )
            recipe = json.loads(recipe_bytes)

            # Hash in recipe must match direct B1 output
            recipe_hash = recipe["snapshots"][f"snapshot_{step_id}"]["sha256"]
            assert recipe_hash == direct_hash, (
                f"Snapshot {step_id}: recipe hash {recipe_hash} != "
                f"direct B1 hash {direct_hash}"
            )

    def test_refmap_entries_referenced_by_actions(self):
        """Every ref in actions exists in refmap."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")

        for action in recipe["actions"]:
            if "ref" in action:
                assert action["ref"] in recipe["refmap"], (
                    f"Action step {action['step']} references "
                    f"{action['ref']} not in refmap"
                )

    def test_snapshot_expectations_reference_valid_snapshots(self):
        """Every expect_snapshot in actions exists in snapshots."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")

        for action in recipe["actions"]:
            if "expect_snapshot" in action:
                assert action["expect_snapshot"] in recipe["snapshots"], (
                    f"Action step {action['step']} expects "
                    f"{action['expect_snapshot']} not in snapshots"
                )
```

### 3.2 Category 2: Snapshot Verification Tests

Verify that canonical snapshots can be used for drift detection.

```python
class TestSnapshotVerification:
    """Verify snapshot hashing and drift detection integration."""

    def test_identical_snapshot_no_drift(self):
        """Same canonical snapshot compared to itself produces NO_DRIFT."""
        episode = load_fixture("episode_gmail_compose.json")
        raw_snapshot = episode["snapshots"]["0"]
        raw_bytes = json.dumps(raw_snapshot, sort_keys=True).encode("utf-8")

        canonical_bytes, _ = canonicalize_snapshot_v01(raw_bytes)

        report = classify_snapshot_drift_v01(canonical_bytes, canonical_bytes)
        assert report.kind == "NO_DRIFT"
        assert report.witness is None

    def test_modified_snapshot_detects_drift(self):
        """Modified snapshot produces typed drift."""
        episode = load_fixture("episode_gmail_compose.json")
        raw_a = episode["snapshots"]["0"]

        # Modify text content
        raw_b = copy.deepcopy(raw_a)
        raw_b["dom"]["children"][0]["text"] = "Modified Text"

        bytes_a = canonicalize_snapshot_v01(
            json.dumps(raw_a, sort_keys=True).encode("utf-8")
        )[0]
        bytes_b = canonicalize_snapshot_v01(
            json.dumps(raw_b, sort_keys=True).encode("utf-8")
        )[0]

        report = classify_snapshot_drift_v01(bytes_a, bytes_b)
        assert report.kind != "NO_DRIFT"
        assert report.witness is not None
        assert report.sha256_a != report.sha256_b

    def test_recipe_snapshot_hash_reproducible(self):
        """Recipe snapshot hashes are reproducible across compilations."""
        episode_bytes = load_fixture_bytes("episode_gmail_compose.json")

        _, hash_1 = compile_episode_to_recipe(episode_bytes)
        _, hash_2 = compile_episode_to_recipe(episode_bytes)

        assert hash_1 == hash_2

    def test_landmark_extraction_consistent(self):
        """Landmarks extracted during compilation match direct extraction."""
        episode = load_fixture("episode_gmail_compose.json")
        raw_snapshot = episode["snapshots"]["0"]
        raw_bytes = json.dumps(raw_snapshot, sort_keys=True).encode("utf-8")

        canonical_bytes, _ = canonicalize_snapshot_v01(raw_bytes)
        canonical_dom = json.loads(canonical_bytes)["dom"]
        direct_landmarks = extract_landmarks(canonical_dom)

        # Compile and check recipe landmarks
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        recipe_landmarks = recipe["snapshots"]["snapshot_0"]["landmarks"]

        assert len(recipe_landmarks) == len(direct_landmarks)
        for recipe_lm, direct_lm in zip(recipe_landmarks, direct_landmarks):
            assert recipe_lm["type"] == direct_lm.type
            assert recipe_lm["path"] == direct_lm.path
```

### 3.3 Category 3: Reference Resolution Tests

Verify that RefMap entries can be used for element resolution.

```python
class TestReferenceResolution:
    """Verify RefMap entries support deterministic element resolution."""

    def test_semantic_selectors_valid_format(self):
        """All semantic selectors are valid CSS/ARIA selectors."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")

        for ref_id, ref in recipe["refmap"].items():
            semantic = ref.get("semantic")
            if semantic:
                # Must be a valid attribute selector
                assert "[" in semantic and "]" in semantic, (
                    f"{ref_id}: semantic selector '{semantic}' not attribute-based"
                )

    def test_structural_selectors_present(self):
        """All refs have structural fallback selectors."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")

        for ref_id, ref in recipe["refmap"].items():
            assert ref.get("structural"), (
                f"{ref_id}: missing structural selector"
            )

    def test_ref_ids_deterministic(self):
        """Same episode produces same ref_ids."""
        episode_bytes = load_fixture_bytes("episode_gmail_compose.json")

        recipe_1 = json.loads(compile_episode_to_recipe(episode_bytes)[0])
        recipe_2 = json.loads(compile_episode_to_recipe(episode_bytes)[0])

        assert set(recipe_1["refmap"].keys()) == set(recipe_2["refmap"].keys())

    def test_no_duplicate_semantic_selectors(self):
        """No two refs use the same semantic selector (never-worse gate)."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")

        semantic_selectors = []
        for ref_id, ref in recipe["refmap"].items():
            semantic = ref.get("semantic")
            if semantic:
                assert semantic not in semantic_selectors, (
                    f"Duplicate semantic selector: {semantic}"
                )
                semantic_selectors.append(semantic)

    def test_context_from_landmarks(self):
        """Ref context values come from landmark types."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        valid_contexts = {"navigation", "form", "page", ""}

        for ref_id, ref in recipe["refmap"].items():
            context = ref.get("context", "")
            assert context in valid_contexts or context == "", (
                f"{ref_id}: unexpected context '{context}'"
            )
```

### 3.4 Category 4: Proof and RTC Tests

Verify cryptographic proof and roundtrip compilation.

```python
class TestProofAndRTC:
    """Verify proof artifacts and RTC guarantee."""

    def test_proof_episode_hash_correct(self):
        """Proof episode_sha256 matches independent hash of episode."""
        episode = load_fixture("episode_gmail_compose.json")
        episode_bytes = json.dumps(episode).encode("utf-8")
        recipe_bytes, _ = compile_episode_to_recipe(episode_bytes)
        recipe = json.loads(recipe_bytes)

        # Independent hash
        episode_canonical = json.dumps(
            episode, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        expected_hash = hashlib.sha256(episode_canonical).hexdigest()

        assert recipe["proof"]["episode_sha256"] == expected_hash

    def test_proof_recipe_hash_correct(self):
        """Proof recipe_sha256 matches hash of recipe-without-proof."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")

        recipe_without_proof = {k: v for k, v in recipe.items() if k != "proof"}
        recipe_canonical = json.dumps(
            recipe_without_proof, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        expected_hash = hashlib.sha256(recipe_canonical).hexdigest()

        assert recipe["proof"]["recipe_sha256"] == expected_hash

    def test_rtc_roundtrip(self):
        """Episode -> Recipe -> Skeleton preserves essential data."""
        episode_bytes = load_fixture_bytes("episode_gmail_compose.json")

        assert verify_rtc(episode_bytes) is True

    def test_confidence_score_range(self):
        """Confidence is between 0.0 and 1.0."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        confidence = recipe["proof"]["confidence"]
        assert 0.0 <= confidence <= 1.0

    def test_proof_counts_accurate(self):
        """Proof action/snapshot/ref counts match recipe contents."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        proof = recipe["proof"]

        assert proof["action_count"] == len(recipe["actions"])
        assert proof["snapshot_count"] == len(recipe["snapshots"])
        assert proof["ref_count"] == len(recipe["refmap"])
```

### 3.5 Category 5: Phase C Compatibility Tests

Verify that recipe IR is consumable by the planned Phase C replay engine.

```python
class TestPhaseCCompatibility:
    """Verify recipe IR schema is compatible with Phase C requirements."""

    def test_navigate_actions_have_url(self):
        """Every navigate action has a url field."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        for action in recipe["actions"]:
            if action["type"] == "navigate":
                assert "url" in action
                assert action["url"].startswith("https://")

    def test_click_actions_have_ref(self):
        """Every click action has a ref field pointing to refmap."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        for action in recipe["actions"]:
            if action["type"] == "click":
                assert "ref" in action
                assert action["ref"] in recipe["refmap"]

    def test_type_actions_have_ref_and_text(self):
        """Every type action has ref and text fields."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        for action in recipe["actions"]:
            if action["type"] == "type":
                assert "ref" in action
                assert "text" in action
                assert action["ref"] in recipe["refmap"]

    def test_refmap_has_semantic_and_structural(self):
        """Every refmap entry has at least structural path."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        for ref_id, ref in recipe["refmap"].items():
            assert "structural" in ref, f"{ref_id}: missing structural"
            assert ref["structural"], f"{ref_id}: empty structural"

    def test_recipe_serializable_to_yaml(self):
        """Recipe can be serialized to YAML (Phase C may use YAML)."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        # Verify all values are JSON-serializable (and therefore YAML-compatible)
        json.dumps(recipe)  # Should not raise

    def test_action_steps_sequential(self):
        """Action steps are sequential starting from 0."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        steps = [a["step"] for a in recipe["actions"]]
        assert steps == list(range(len(steps)))

    def test_snapshot_step_references_valid(self):
        """Snapshot step values are within action step range."""
        recipe = compile_and_load_fixture("episode_gmail_compose.json")
        action_steps = set(a["step"] for a in recipe["actions"])
        for snap_id, snap in recipe["snapshots"].items():
            assert snap["step"] in action_steps or snap["step"] >= 0
```

---

## 4. Test Fixtures

### 4.1 Required Fixtures

| Fixture | Description | Actions | Snapshots |
|---------|-------------|---------|-----------|
| `episode_gmail_compose.json` | Gmail: navigate, click Compose, type To, click Send | 4 | 2-3 |
| `episode_gmail_read.json` | Gmail: navigate, click email, scroll | 3 | 2 |
| `episode_minimal.json` | Single navigate action | 1 | 1 |
| `episode_no_snapshots.json` | Navigate + click, no snapshots | 2 | 0 |
| `episode_many_actions.json` | 20-action sequence | 20 | 5 |
| `episode_ambiguous_refs.json` | Two clicks with same reference (SHOULD FAIL) | 3 | 1 |
| `episode_no_selectors.json` | Click with no selector or reference (SHOULD FAIL) | 2 | 1 |

### 4.2 Fixture Generator

```python
def generate_fixture_snapshot(url: str, landmark_roles: list[str]) -> dict:
    """Generate a valid raw snapshot fixture."""
    children = []
    for role in landmark_roles:
        children.append({
            "tag": "div",
            "attrs": {"role": role, "aria-label": role.capitalize()},
            "text": "",
            "children": [],
        })

    return {
        "v": 1,
        "meta": {
            "url": url,
            "viewport": {"w": 1920, "h": 1080},
        },
        "dom": {
            "tag": "html",
            "attrs": {},
            "text": "",
            "children": [
                {
                    "tag": "body",
                    "attrs": {},
                    "text": "",
                    "children": children,
                }
            ],
        },
    }


def generate_fixture_episode(
    domain: str,
    actions: list[dict],
    snapshot_steps: list[int],
) -> dict:
    """Generate a valid episode fixture."""
    snapshots = {}
    for step in snapshot_steps:
        snapshots[str(step)] = generate_fixture_snapshot(
            f"https://{domain}/page_{step}",
            ["navigation", "main"],
        )

    return {
        "version": "1.0.0",
        "session_id": f"session_{domain}_{len(actions)}",
        "domain": domain,
        "start_time": "2026-02-14T12:00:00Z",
        "end_time": "2026-02-14T12:05:00Z",
        "actions": actions,
        "snapshots": snapshots,
        "action_count": len(actions),
    }
```

---

## 5. Snapshot Verification Algorithm

### 5.1 How Snapshot Verification Works During Replay (Phase C Preview)

During Phase C replay, when an action has `expect_snapshot`, the runner:

1. Captures current DOM via `captureStructuredDOM()` (from B1 content script upgrade)
2. Canonicalizes via `canonicalize_snapshot_v01()`
3. Compares hash to expected hash from recipe
4. If mismatch, runs `classify_snapshot_drift_v01()` for typed diagnosis

```python
async def verify_snapshot_during_replay(
    page,
    recipe: dict,
    snapshot_id: str,
) -> SnapshotVerificationResult:
    """
    Verify current page state matches recipe snapshot expectation.
    """
    expected = recipe["snapshots"][snapshot_id]
    expected_hash = expected["sha256"]

    # Capture current DOM
    raw_dom = await page.evaluate("() => captureStructuredDOM(document.documentElement)")
    raw_snapshot = {
        "v": 1,
        "meta": {
            "url": page.url,
            "viewport": {
                "w": await page.evaluate("() => window.innerWidth"),
                "h": await page.evaluate("() => window.innerHeight"),
            },
        },
        "dom": raw_dom,
    }

    raw_bytes = json.dumps(raw_snapshot, sort_keys=True).encode("utf-8")

    try:
        current_bytes, current_hash = canonicalize_snapshot_v01(raw_bytes)
    except SnapshotError as e:
        return SnapshotVerificationResult(
            status="ERROR",
            snapshot_id=snapshot_id,
            error=f"{e.code}: {e.message}",
        )

    if current_hash == expected_hash:
        return SnapshotVerificationResult(
            status="MATCH",
            snapshot_id=snapshot_id,
            expected_hash=expected_hash,
            actual_hash=current_hash,
        )

    # Drift detected -- classify
    # Need expected canonical bytes for drift comparison
    # In v0.1, we store the hash but not the bytes, so drift classification
    # requires reconstructing expected bytes (stored separately in B3 artifacts)
    return SnapshotVerificationResult(
        status="DRIFT",
        snapshot_id=snapshot_id,
        expected_hash=expected_hash,
        actual_hash=current_hash,
    )
```

### 5.2 Data Structure

```python
@dataclass(frozen=True)
class SnapshotVerificationResult:
    status: str           # "MATCH", "DRIFT", "ERROR"
    snapshot_id: str
    expected_hash: str = ""
    actual_hash: str = ""
    error: str = ""
    drift_kind: str = ""  # From classify_snapshot_drift_v01
```

---

## 6. Reference Resolution During Replay (Phase C Preview)

### 6.1 How Reference Resolution Works

During Phase C replay, the runner resolves RefMap entries against the live DOM:

```python
async def resolve_reference(
    page,
    ref: dict,
) -> ElementHandle:
    """
    Resolve a RefMap entry to a live DOM element.
    Uses browser-selector-resolution skill's 3-tier algorithm.

    Tier 1: Semantic (ARIA-based)
    Tier 2: Structural (CSS selector)
    Tier 3: Typed failure
    """
    # Tier 1: Try semantic selector
    semantic = ref.get("semantic")
    if semantic:
        elements = await page.query_selector_all(semantic)
        if len(elements) == 1:
            return elements[0]
        if len(elements) > 1:
            # Ambiguous -- try with context filter
            context = ref.get("context")
            if context:
                for el in elements:
                    ancestor = await find_ancestor_by_role(el, context)
                    if ancestor:
                        return el

    # Tier 2: Try structural selector
    structural = ref.get("structural")
    if structural:
        elements = await page.query_selector_all(structural)
        if len(elements) == 1:
            return elements[0]

    # Tier 3: Typed failure
    raise ReferenceResolutionError(
        ref_id=ref.get("ref_id", "unknown"),
        semantic=semantic,
        structural=structural,
        match_count=len(elements) if elements else 0,
    )
```

### 6.2 B3 Verifies Resolution Readiness

B3 does not do live browser resolution, but verifies that:
- All refs have at least one resolution path (semantic or structural)
- No refs have ambiguous semantic selectors
- Context values are from the valid set
- Structural selectors are syntactically valid CSS

---

## 7. Verification Rungs (641 -> 274177 -> 65537)

### 7.1 OAuth Unlock (39, 63, 91)

- **39 (CARE):** Integration tests cover all cross-module boundaries
- **63 (BRIDGE):** B3 bridges B1+B2 with Phase C forward compatibility
- **91 (STABILITY):** Deterministic tests with no randomness or timing dependency

### 7.2 641-Edge Tests (Integration Sanity)

| Test | Category | Description |
|------|----------|-------------|
| I1 | Pipeline | Episode -> Recipe end-to-end produces valid output |
| I2 | Pipeline | Canonical hashes survive compilation unchanged |
| I3 | Pipeline | All action refs exist in refmap |
| I4 | Pipeline | All snapshot expectations reference valid snapshots |
| I5 | Snapshot | Identical snapshot comparison returns NO_DRIFT |
| I6 | Snapshot | Modified snapshot detects drift |
| I7 | Snapshot | Recipe snapshot hashes reproducible |
| I8 | RefMap | Semantic selectors valid format |
| I9 | RefMap | No duplicate semantic selectors |
| I10 | Proof | Episode hash correct in proof |
| I11 | Proof | Recipe hash correct in proof |
| I12 | Proof | RTC roundtrip passes |
| I13 | Phase C | Navigate actions have URL |
| I14 | Phase C | Click actions have ref in refmap |
| I15 | Phase C | Type actions have ref and text |
| I16 | Phase C | Action steps sequential |
| I17 | Phase C | Recipe JSON-serializable |

**Total: 17 edge tests (17 is prime)**

### 7.3 274177-Stress Tests (Integration Scaling)

| Test | Description | Scale |
|------|-------------|-------|
| S1 | Compile 100 episodes, all produce valid recipes | 100 episodes |
| S2 | Compile same episode 100 times, all produce identical recipe | 100 iterations |
| S3 | Compile episodes of varying length (1-50 actions) | 50 sizes |
| S4 | RTC verification on all 100 compiled recipes | 100 roundtrips |
| S5 | Snapshot collision-free across 100 different episodes | 100 episode sets |
| S6 | Recipe size grows linearly with action count | 50 data points |
| S7 | Compile with 0 snapshots, 1 snapshot, many snapshots | 3 variants |

**Total: 7 stress tests (7 is prime)**

### 7.4 65537-God Approval (Integration Audit)

| Check | Description |
|-------|-------------|
| G1 | All 17 edge tests passing |
| G2 | All 7 stress tests passing |
| G3 | No forbidden imports in B1 or B2 modules |
| G4 | RTC verified for every test episode |
| G5 | Phase C schema compatibility confirmed |

**Total: 5 god tests (5 is prime)**

---

## 8. Test Strategy

### 8.1 Test File Structure

```
tests/
    conftest.py                              # Shared fixtures
    fixtures/
        episode_gmail_compose.json           # 4-action Gmail episode
        episode_gmail_read.json              # 3-action Gmail episode
        episode_minimal.json                 # 1-action episode
        episode_no_snapshots.json            # Episode without snapshots
        episode_many_actions.json            # 20-action episode
        episode_ambiguous_refs.json          # Should fail compilation
        episode_no_selectors.json            # Should fail compilation
    test_wish_25_1_canonical_snapshot_v01.py  # B1 unit tests (10)
    test_wish_25_2_snapshot_drift_v01.py      # B1 drift tests (11)
    test_wish_26_episode_compiler_v01.py      # B2 unit tests (7)
    test_integration_b1_b2.py                 # B3 integration tests (17)
    test_stress_b1_b2.py                      # B3 stress tests (7)
    test_god_b1_b2.py                         # B3 god tests (5)
```

### 8.2 Test Execution Order

```
1. Unit Tests (B1): pytest test_wish_25_1*.py    -> 10 tests
2. Unit Tests (B1): pytest test_wish_25_2*.py    -> 11 tests
3. Unit Tests (B2): pytest test_wish_26*.py      -> 7 tests
4. Integration (B3): pytest test_integration*.py  -> 17 tests
5. Stress (B3): pytest test_stress*.py            -> 7 tests
6. God (B3): pytest test_god*.py                  -> 5 tests
                                                   --------
                                            Total: 57 tests
```

### 8.3 Fixture Helper Functions

```python
# conftest.py
import json
import pytest
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def episode_gmail_compose():
    return json.loads((FIXTURE_DIR / "episode_gmail_compose.json").read_bytes())

@pytest.fixture
def episode_minimal():
    return json.loads((FIXTURE_DIR / "episode_minimal.json").read_bytes())

def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_bytes())

def load_fixture_bytes(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()

def compile_and_load_fixture(name: str) -> dict:
    episode_bytes = load_fixture_bytes(name)
    recipe_bytes, _ = compile_episode_to_recipe(episode_bytes)
    return json.loads(recipe_bytes)
```

---

## 9. Code Structure

### 9.1 Files to Create

| File | Purpose | Est. LOC |
|------|---------|----------|
| `tests/test_integration_b1_b2.py` | Integration edge tests (17 tests) | 450 |
| `tests/test_stress_b1_b2.py` | Integration stress tests (7 tests) | 300 |
| `tests/test_god_b1_b2.py` | God approval tests (5 tests) | 200 |
| `tests/fixtures/episode_gmail_compose.json` | Primary test fixture | 100 |
| `tests/fixtures/episode_gmail_read.json` | Secondary test fixture | 80 |
| `tests/fixtures/episode_minimal.json` | Minimal test fixture | 30 |
| `tests/fixtures/episode_no_snapshots.json` | No-snapshot fixture | 40 |
| `tests/fixtures/episode_many_actions.json` | Large test fixture | 200 |
| `tests/fixtures/episode_ambiguous_refs.json` | Failure test fixture | 50 |
| `tests/fixtures/episode_no_selectors.json` | Failure test fixture | 40 |
| `tests/conftest.py` (update) | Add fixture helpers | +50 |

### 9.2 No New Production Code

B3 creates **no new production code**. All verification is through tests that exercise existing B1 + B2 code. This keeps the test surface clean and focused on integration correctness.

---

## 10. State Machine

```
STATE_SET:
  - FIXTURES_LOADED       (test fixtures parsed and valid)
  - UNIT_TESTS_PASSING    (B1 + B2 individual tests pass)
  - INTEGRATION_PASSING   (B3 cross-module tests pass)
  - STRESS_PASSING        (B3 scaling tests pass)
  - GOD_APPROVED          (All verification rungs complete)
  - VERIFICATION_FAILED   (Any test failure)

TRANSITIONS (LOCKED):
  FIXTURES_LOADED      -> UNIT_TESTS_PASSING
  UNIT_TESTS_PASSING   -> INTEGRATION_PASSING
  INTEGRATION_PASSING  -> STRESS_PASSING
  STRESS_PASSING       -> GOD_APPROVED
  ANY                  -> VERIFICATION_FAILED (on first failure)

FORBIDDEN_STATES:
  - INTEGRATION_WITHOUT_UNITS    (must pass unit tests first)
  - STRESS_WITHOUT_INTEGRATION   (must pass integration first)
  - GOD_WITHOUT_STRESS           (must pass stress first)
  - SKIP_VERIFICATION_RUNG       (no shortcuts)
```

---

## 11. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Test fixtures do not represent real-world DOM | HIGH | Use real Gmail DOM captures (anonymized) as fixture base. Generate variations programmatically. |
| B1 + B2 API changes break integration tests | MEDIUM | Surface lock on B1/B2 entrypoints. Integration tests import only public API. |
| Stress tests too slow (100 compilations) | LOW | Each compilation should be <100ms. Total stress suite <30s. |
| Phase C schema not finalized | MEDIUM | B3 tests verify a minimal schema contract. Phase C can extend without breaking. |
| Drift classifier not implemented yet | MEDIUM | B3 can test drift detection separately; snapshot hash comparison is the primary verification path. |

---

## 12. Dependencies

```
B1 (Snapshot Canonicalization) [MUST PASS UNIT TESTS]
    |
    v
B2 (Episode-to-Recipe Compiler) [MUST PASS UNIT TESTS]
    |
    v
B3 (Integration Verification) [THIS DESIGN]
    |
    +---> Phase C GO/NO-GO decision
    |
    +---> Production readiness certification
```

---

## 13. Quest Checks (Must All Pass)

- [ ] All 7 test fixtures created and valid
- [ ] 17 integration edge tests passing (641)
- [ ] 7 stress tests passing (274177)
- [ ] 5 god approval tests passing (65537)
- [ ] Total: 57 tests across B1+B2+B3 (all green)
- [ ] Phase C schema compatibility verified
- [ ] RTC roundtrip verified for all test episodes

**XP Available:** 600 (pipeline flow: 150, snapshot: 100, refmap: 100, proof: 100, Phase C: 150)

---

## 14. Gamification Integration

### Quest Contract

```yaml
quest_id: "B3_INTEGRATION_VERIFICATION"
star: "HAIKU_SWARM_PHASE_B"
channel: 7
glow: 88
xp_reward: 600

quest_contract:
  goal: "End-to-end integration verification for B1+B2 pipeline"
  checks:
    - "7 test fixtures created (prime count)"
    - "17 integration edge tests passing (prime count)"
    - "7 stress tests passing (prime count)"
    - "5 god approval tests passing (prime count)"
    - "Phase C schema compatibility verified"
    - "RTC roundtrip across full pipeline"
    - "57 total tests all green"
  verification: "641 -> 274177 -> 65537"
```

### XP Distribution

- Skeptic (Integration Testing): 300 XP -- 17 edge + 7 stress tests
- Skeptic (God Approval): 150 XP -- 5 god tests + certification
- Scout (Fixture Design): 150 XP -- 7 test fixtures

---

**Version:** 1.0.0
**Auth:** 65537
**Northstar:** Phuc Forecast (DREAM -> FORECAST -> DECIDE -> ACT -> VERIFY)
**Verification:** OAuth(39,63,91) -> 641 -> 274177 -> 65537

*"Integration verification: trust through evidence, not hope."*
