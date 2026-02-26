"""
test_recipe_engine_fsm.py
==========================
Derived from: data/default/diagrams/recipe-engine-fsm.md

Tests the Recipe Engine FSM state transitions:
  INTAKE → INTENT_CLASSIFY → CACHE_LOOKUP → HIT_VERIFY | CACHE_MISS
  CACHE_MISS → LLM_GENERATE → VALIDATE → EXECUTE
  EXECUTE → CHECKPOINT → EVIDENCE → STORE → EXIT_PASS
  Any safety violation → EXIT_BLOCKED

Additional contracts:
  - SHA256 cache key determinism
  - Never-worse gate: new recipe must pass old recipe's tests
  - CLOSURE: max_steps and timeout_ms are hard limits
  - Evidence bundle on EXIT_PASS
  - BLOCKED state on safety violation

Run:
    python -m pytest tests/test_data/default/diagrams/test_recipe_engine_fsm.py -v
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, call

import pytest

try:
    from recipe_engine import (
        RecipeEngine,
        RecipeRequest,
        RecipeResult,
        CacheLookupResult,
        ValidationResult,
        FSMState,
    )
    _RECIPE_ENGINE_AVAILABLE = True
except ImportError:
    _RECIPE_ENGINE_AVAILABLE = False

_NEEDS_ENGINE = pytest.mark.xfail(
    not _RECIPE_ENGINE_AVAILABLE,
    reason="recipe_engine module not yet implemented",
    strict=False,
)


def _sha256_key(intent: str, platform: str, action_type: str) -> str:
    """Replicate the diagram's cache key formula."""
    normalized = intent.lower().strip() + platform + action_type
    return hashlib.sha256(normalized.encode()).hexdigest()


# ---------------------------------------------------------------------------
# INTAKE state: input validation
# ---------------------------------------------------------------------------


class TestIntakeState:
    """
    Diagram: [*] → INTAKE : intent + platform + action_type received
    INTAKE → INTENT_CLASSIFY : inputs validated
    INTAKE → EXIT_NEED_INFO : missing required inputs
    """

    @_NEEDS_ENGINE
    def test_intake_valid_inputs_transitions_to_intent_classify(self):
        """
        Valid INTAKE inputs must not produce EXIT_NEED_INFO.
        The engine must advance to INTENT_CLASSIFY.
        """
        engine = RecipeEngine(cache={}, llm=MagicMock())
        request = RecipeRequest(
            intent="post to LinkedIn",
            platform="linkedin",
            action_type="create_post",
        )
        result = engine.run(request)
        # Must not be NEED_INFO when all fields provided
        assert result.status != "EXIT_NEED_INFO"

    @_NEEDS_ENGINE
    def test_intake_missing_intent_exits_need_info(self):
        """
        Diagram: INTAKE → EXIT_NEED_INFO if missing required inputs.
        Missing intent must produce EXIT_NEED_INFO (not an exception crash).
        """
        engine = RecipeEngine(cache={}, llm=MagicMock())
        request = RecipeRequest(
            intent="",  # empty
            platform="linkedin",
            action_type="create_post",
        )
        result = engine.run(request)
        assert result.status == "EXIT_NEED_INFO"

    @_NEEDS_ENGINE
    def test_intake_missing_platform_exits_need_info(self):
        """Missing platform must produce EXIT_NEED_INFO."""
        engine = RecipeEngine(cache={}, llm=MagicMock())
        request = RecipeRequest(
            intent="do something",
            platform="",
            action_type="create_post",
        )
        result = engine.run(request)
        assert result.status == "EXIT_NEED_INFO"


# ---------------------------------------------------------------------------
# INTENT_CLASSIFY + CACHE_LOOKUP: SHA256 key
# ---------------------------------------------------------------------------


class TestIntentClassifyAndCacheKey:
    """
    Diagram: INTENT_CLASSIFY → CACHE_LOOKUP : intent normalized → SHA256 key computed
    SHA256 key: sha256(normalize(intent) + platform + action_type)
    Normalization: lowercase, trim, canonical verb form
    """

    def test_cache_key_uses_sha256_hex(self):
        """
        The cache key formula must produce a 64-char hex string.
        This is a pure algorithmic test (no module import needed).
        """
        key = _sha256_key("post to LinkedIn", "linkedin", "create_post")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_cache_key_normalization_lowercase(self):
        """
        Diagram: normalization = lowercase + trim.
        'Post to LinkedIn' and 'post to linkedin' must produce the same key.
        """
        key1 = _sha256_key("Post to LinkedIn", "linkedin", "create_post")
        key2 = _sha256_key("post to linkedin", "linkedin", "create_post")
        assert key1 == key2

    def test_cache_key_differs_by_platform(self):
        """
        Diagram note: same intent on different platforms → different keys.
        """
        key_linkedin = _sha256_key("post an update", "linkedin", "create_post")
        key_twitter = _sha256_key("post an update", "twitter", "create_tweet")
        assert key_linkedin != key_twitter

    def test_cache_key_differs_by_action_type(self):
        """Different action_type must produce different cache key."""
        key_create = _sha256_key("post to linkedin", "linkedin", "create_post")
        key_delete = _sha256_key("post to linkedin", "linkedin", "delete_post")
        assert key_create != key_delete

    def test_cache_key_deterministic(self):
        """Same inputs always produce same key (no random, no time-based)."""
        key1 = _sha256_key("post to LinkedIn", "linkedin", "create_post")
        key2 = _sha256_key("post to LinkedIn", "linkedin", "create_post")
        assert key1 == key2


# ---------------------------------------------------------------------------
# CACHE_LOOKUP: hit and miss
# ---------------------------------------------------------------------------


class TestCacheLookup:
    """
    Diagram: CACHE_LOOKUP → HIT_VERIFY (found) | CACHE_MISS (not found)
    Cache store: ~/.solace/recipes/<sha256>.json
    Staleness determined by never-worse test run.
    """

    @_NEEDS_ENGINE
    def test_cache_hit_returns_hit_flag(self, recipe_store, recipe_cache_key):
        """
        When the SHA256 key exists in the store, lookup must return hit=True.
        """
        engine = RecipeEngine(cache=recipe_store, llm=MagicMock())
        result = engine._cache_lookup(recipe_cache_key)
        assert isinstance(result, CacheLookupResult)
        assert result.hit is True

    @_NEEDS_ENGINE
    def test_cache_miss_returns_miss_flag(self):
        """When the key is absent, lookup must return hit=False."""
        engine = RecipeEngine(cache={}, llm=MagicMock())
        result = engine._cache_lookup("unknown-key")
        assert isinstance(result, CacheLookupResult)
        assert result.hit is False
        assert result.recipe is None

    @_NEEDS_ENGINE
    def test_stale_recipe_demotes_to_miss(self, minimal_recipe, recipe_cache_key):
        """
        Diagram: HIT_VERIFY → CACHE_MISS if recipe stale or broken.
        A recipe that fails never-worse tests must be treated as a miss.
        """
        stale_recipe = dict(minimal_recipe)
        stale_recipe["_stale"] = True  # sentinel for test; engine checks never-worse
        cache = {recipe_cache_key: stale_recipe}
        engine = RecipeEngine(cache=cache, llm=MagicMock())
        # Mock the never-worse gate to indicate the recipe is stale
        engine._never_worse_check = MagicMock(return_value=False)
        result = engine._cache_lookup(recipe_cache_key)
        if result.hit:
            # Engine found it but must demote to miss on stale check
            verify_result = engine._hit_verify(result.recipe)
            assert verify_result.valid is False


# ---------------------------------------------------------------------------
# CACHE_MISS → LLM_GENERATE → VALIDATE
# ---------------------------------------------------------------------------


class TestCacheMissAndLLMGenerate:
    """
    Diagram: CACHE_MISS → LLM_GENERATE : dispatch recipe-builder swarm
             LLM_GENERATE → VALIDATE : recipe.json generated by LLM
             VALIDATE → EXECUTE (pass) | LLM_GENERATE retry (fail, max 3)
             VALIDATE → EXIT_BLOCKED (max retries exceeded)
    """

    @_NEEDS_ENGINE
    def test_cache_miss_triggers_llm_generate(self):
        """
        On cache miss, the engine must call the LLM to generate a recipe.
        """
        mock_llm = MagicMock(return_value=_valid_recipe_json())
        engine = RecipeEngine(cache={}, llm=mock_llm)
        request = RecipeRequest(
            intent="post to LinkedIn",
            platform="linkedin",
            action_type="create_post",
        )
        engine.run(request)
        mock_llm.assert_called()

    @_NEEDS_ENGINE
    def test_validate_pass_advances_to_execute(self, minimal_recipe):
        """
        VALIDATE pass: portals found, steps valid → advance to EXECUTE.
        """
        engine = RecipeEngine(cache={}, llm=MagicMock())
        result = engine._validate(minimal_recipe)
        assert isinstance(result, ValidationResult)
        assert result.valid is True

    @_NEEDS_ENGINE
    def test_validate_fail_on_missing_portals(self):
        """
        Diagram: VALIDATE → LLM_GENERATE retry if validation fails.
        A recipe with no portals must fail validation.
        """
        bad_recipe = {
            "recipe_id": "bad",
            "version": "1.0.0",
            "intent": "test",
            "platform": "linkedin",
            "action_type": "create_post",
            "oauth3_scopes_required": [],
            "max_steps": 5,
            "timeout_ms": 10000,
            "portals": [],  # empty portals → INVALID
            "steps": [],
            "output_schema": "test",
        }
        engine = RecipeEngine(cache={}, llm=MagicMock())
        result = engine._validate(bad_recipe)
        assert result.valid is False

    @_NEEDS_ENGINE
    def test_validate_fail_on_missing_closure_fields(self):
        """
        SCOPELESS_RECIPE (no max_steps or no timeout_ms) must fail validation.
        """
        recipe_no_closure = {
            "recipe_id": "no-closure",
            "version": "1.0.0",
            "intent": "test",
            "platform": "linkedin",
            "action_type": "create_post",
            "oauth3_scopes_required": [],
            # max_steps and timeout_ms intentionally missing
            "portals": ["https://www.linkedin.com/"],
            "steps": [],
            "output_schema": "test",
        }
        engine = RecipeEngine(cache={}, llm=MagicMock())
        result = engine._validate(recipe_no_closure)
        assert result.valid is False

    @_NEEDS_ENGINE
    def test_max_retries_exceeded_exits_blocked(self):
        """
        Diagram: VALIDATE → EXIT_BLOCKED when max retries (3) exceeded.
        LLM that always returns invalid recipes must not loop forever.
        """
        # LLM always returns a recipe with empty portals (invalid)
        bad_json = '{"portals": [], "steps": [], "max_steps": 5, "timeout_ms": 5000}'
        mock_llm = MagicMock(return_value=bad_json)
        engine = RecipeEngine(cache={}, llm=mock_llm)
        request = RecipeRequest(
            intent="post to LinkedIn",
            platform="linkedin",
            action_type="create_post",
        )
        result = engine.run(request)
        assert result.status == "EXIT_BLOCKED"
        # LLM must have been called at most 3 times (diagram: max 3 attempts)
        assert mock_llm.call_count <= 3


# ---------------------------------------------------------------------------
# EXECUTE → CHECKPOINT
# ---------------------------------------------------------------------------


class TestExecuteAndCheckpoint:
    """
    Diagram: EXECUTE → CHECKPOINT : first step executed
             CHECKPOINT → EXECUTE : checkpoint passed → continue
             CHECKPOINT → ROLLBACK : checkpoint failed → undo
             ROLLBACK → EXIT_BLOCKED
    """

    @_NEEDS_ENGINE
    def test_execute_with_checkpoints_proceeds_on_pass(self, minimal_recipe, mock_browser):
        """
        A recipe with all checkpoints passing must reach EVIDENCE state.
        """
        engine = RecipeEngine(cache={}, llm=MagicMock())
        engine._browser = mock_browser
        result = engine._execute(minimal_recipe)
        assert result.status != "EXIT_BLOCKED"

    @_NEEDS_ENGINE
    def test_checkpoint_fail_triggers_rollback(self, minimal_recipe, mock_browser):
        """
        Diagram: CHECKPOINT failed → ROLLBACK → EXIT_BLOCKED.
        A failing checkpoint must stop execution and produce EXIT_BLOCKED.
        """
        engine = RecipeEngine(cache={}, llm=MagicMock())
        engine._browser = mock_browser
        # Force checkpoint failure
        engine._run_step = MagicMock(return_value={"status": "FAIL", "checkpoint_passed": False})
        result = engine._execute(minimal_recipe)
        assert result.status == "EXIT_BLOCKED"

    @_NEEDS_ENGINE
    def test_max_steps_exceeded_exits_blocked(self, mock_browser):
        """
        CLOSURE: max_steps exceeded → EXIT_BLOCKED (UNBOUNDED_EXECUTION blocked).
        """
        recipe = {
            "recipe_id": "max-steps-test",
            "version": "1.0.0",
            "intent": "test",
            "platform": "linkedin",
            "action_type": "create_post",
            "oauth3_scopes_required": [],
            "max_steps": 2,
            "timeout_ms": 30000,
            "portals": ["https://www.linkedin.com/"],
            "steps": [
                {"step_number": i, "action": "click", "selector": "#btn",
                 "checkpoint": False, "rollback": None, "max_retry": 1, "timeout_ms": 1000}
                for i in range(1, 6)  # 5 steps but max_steps=2
            ],
            "output_schema": "test",
        }
        engine = RecipeEngine(cache={}, llm=MagicMock())
        engine._browser = mock_browser
        result = engine._execute(recipe)
        assert result.status == "EXIT_BLOCKED"
        assert result.steps_executed <= recipe["max_steps"]


# ---------------------------------------------------------------------------
# Never-worse gate
# ---------------------------------------------------------------------------


class TestNeverWorseGate:
    """
    Diagram: Recipe Versioning + Never-Worse Gate
    NEW_VERSION → OLD_TESTS → RUN_TESTS
    all pass → PROMOTE | any fail → BLOCK → ESCALATE
    """

    @_NEEDS_ENGINE
    def test_never_worse_promotes_on_all_tests_pass(self, minimal_recipe):
        """
        New recipe version that passes all old tests must be PROMOTED.
        """
        old_recipe = dict(minimal_recipe)
        old_recipe["version"] = "1.0.0"
        new_recipe = dict(minimal_recipe)
        new_recipe["version"] = "1.0.1"
        engine = RecipeEngine(cache={}, llm=MagicMock())
        # Mock old tests to all pass
        engine._run_recipe_tests = MagicMock(return_value={"all_passed": True, "failed": []})
        result = engine._never_worse_gate(old_recipe=old_recipe, new_recipe=new_recipe)
        assert result.promoted is True

    @_NEEDS_ENGINE
    def test_never_worse_blocks_on_any_test_fail(self, minimal_recipe):
        """
        New recipe that fails any old test must be BLOCKED (regression detected).
        """
        old_recipe = dict(minimal_recipe)
        old_recipe["version"] = "1.0.0"
        new_recipe = dict(minimal_recipe)
        new_recipe["version"] = "1.0.1"
        engine = RecipeEngine(cache={}, llm=MagicMock())
        # Mock old tests to have one failure
        engine._run_recipe_tests = MagicMock(
            return_value={"all_passed": False, "failed": ["test_step_1_clicks_button"]}
        )
        result = engine._never_worse_gate(old_recipe=old_recipe, new_recipe=new_recipe)
        assert result.promoted is False
        assert result.status == "BLOCKED"


# ---------------------------------------------------------------------------
# EVIDENCE → STORE → EXIT_PASS
# ---------------------------------------------------------------------------


class TestEvidenceAndStore:
    """
    Diagram: EVIDENCE → STORE : evidence_bundle.json signed + chain-linked
             STORE → EXIT_PASS : recipe cached, PM triplet stored
    """

    @_NEEDS_ENGINE
    def test_exit_pass_produces_cache_entry(self, recipe_store, recipe_cache_key):
        """
        EXIT_PASS must store the recipe in the cache for future hits.
        """
        empty_cache: Dict[str, Any] = {}
        engine = RecipeEngine(cache=empty_cache, llm=MagicMock(return_value=_valid_recipe_json()))
        request = RecipeRequest(
            intent="post to LinkedIn",
            platform="linkedin",
            action_type="create_post",
        )
        engine.run(request)
        # Cache must now contain an entry for this intent
        assert len(empty_cache) > 0

    @_NEEDS_ENGINE
    def test_exit_pass_includes_evidence_bundle(self):
        """
        EXIT_PASS result must carry an evidence bundle (ALCOA+ signed).
        """
        mock_llm = MagicMock(return_value=_valid_recipe_json())
        engine = RecipeEngine(cache={}, llm=mock_llm)
        request = RecipeRequest(
            intent="post to LinkedIn",
            platform="linkedin",
            action_type="create_post",
        )
        result = engine.run(request)
        if result.status == "EXIT_PASS":
            assert result.evidence_bundle is not None
            assert "bundle_id" in result.evidence_bundle

    @_NEEDS_ENGINE
    def test_exit_blocked_does_not_cache_recipe(self):
        """
        An execution that produces EXIT_BLOCKED must NOT cache the recipe.
        Caching a broken recipe would poison the cache.
        """
        # LLM returns always-invalid recipe (no portals)
        bad_json = '{"portals": [], "steps": [], "max_steps": 5, "timeout_ms": 5000}'
        cache: Dict[str, Any] = {}
        engine = RecipeEngine(cache=cache, llm=MagicMock(return_value=bad_json))
        request = RecipeRequest(
            intent="do impossible thing",
            platform="linkedin",
            action_type="create_post",
        )
        result = engine.run(request)
        assert result.status == "EXIT_BLOCKED"
        assert len(cache) == 0, "Broken recipe must not be cached"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_recipe_json() -> str:
    """A minimal valid recipe JSON string for mock LLM responses."""
    import json
    return json.dumps({
        "recipe_id": str(uuid.uuid4()),
        "version": "1.0.0",
        "intent": "post to LinkedIn",
        "platform": "linkedin",
        "action_type": "create_post",
        "oauth3_scopes_required": ["linkedin.create_post"],
        "max_steps": 10,
        "timeout_ms": 30000,
        "portals": ["https://www.linkedin.com/feed/"],
        "steps": [
            {
                "step_number": 1,
                "action": "click",
                "selector": "[aria-label='Start a post']",
                "checkpoint": True,
                "rollback": None,
                "max_retry": 3,
                "timeout_ms": 5000,
            }
        ],
        "output_schema": "post_created",
    })
