"""
TASK-007 acceptance tests:
- Parse all recipe JSON files (>= 57)
- Validate recipe scopes against PrimeWiki actions
- Ensure no unlimited budgets
- Validate evidence requirements for Gmail/Reddit/HackerNews samples
- Validate new Slack/GitHub/Notion recipes and PrimeWiki references
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from evidence_pipeline import EvidencePipeline
from recipe_engine import FSMState, RecipeEngine, RecipeRequest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECIPES_ROOT = PROJECT_ROOT / "data" / "default" / "recipes"
PRIMEWIKI_ROOT = PROJECT_ROOT / "data" / "default" / "primewiki"

SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), f"{path} must contain a JSON object"
    return data


def _recipe_files() -> list[Path]:
    return sorted(RECIPES_ROOT.rglob("*.json"))


def _contains_unlimited(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() == "unlimited"
    if isinstance(value, dict):
        return any(_contains_unlimited(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_unlimited(v) for v in value)
    return False


def _primewiki_scopes(actions_path: Path) -> set[str]:
    actions_doc = _load_json(actions_path)
    actions = actions_doc.get("actions", {})
    assert isinstance(actions, dict), f"{actions_path} missing 'actions' object"
    scopes = {
        action.get("oauth3_scope")
        for action in actions.values()
        if isinstance(action, dict) and isinstance(action.get("oauth3_scope"), str)
    }
    return {scope for scope in scopes if scope}


def _engine_recipe_from(recipe: dict[str, Any]) -> dict[str, Any]:
    steps = recipe.get("steps", [])
    if not isinstance(steps, list):
        steps = []

    return {
        "recipe_id": recipe["id"],
        "version": recipe.get("version", "1.0.0"),
        "intent": recipe.get("description", recipe["id"]),
        "platform": recipe["platform"],
        "action_type": recipe["id"],
        "oauth3_scopes_required": recipe.get("oauth3_scopes", []),
        "max_steps": max(1, len(steps)),
        "timeout_ms": 30000,
        "portals": [f"https://{recipe['platform']}.example.com"],
        "steps": [{"step": idx + 1, "action": "noop"} for idx, _ in enumerate(steps)],
        "output_schema": "json",
    }


class TestTask007MultiPlatformRecipeValidation:
    def test_all_recipe_json_files_parse(self):
        files = _recipe_files()
        assert len(files) >= 57, f"Expected >=57 recipe JSON files, found {len(files)}"
        for path in files:
            recipe = _load_json(path)
            assert recipe, f"{path} parsed but is empty"

    def test_mermaid_fsm_when_present_is_state_machine(self):
        for path in _recipe_files():
            recipe = _load_json(path)
            mermaid_fsm = recipe.get("mermaid_fsm")
            if mermaid_fsm is not None:
                assert isinstance(mermaid_fsm, str) and mermaid_fsm.strip()
                assert "stateDiagram" in mermaid_fsm

    def test_budget_constraints_have_no_unlimited(self):
        for path in _recipe_files():
            recipe = _load_json(path)
            budgets = recipe.get("budgets")
            if budgets is not None:
                assert not _contains_unlimited(budgets), f"{path} contains unlimited budget"

    @pytest.mark.parametrize(
        "recipe_rel,actions_rel",
        [
            ("data/default/recipes/gmail/gmail-read-inbox.json", "data/default/primewiki/gmail/actions.json"),
            ("data/default/recipes/reddit/reddit-browse-subreddit.json", "data/default/primewiki/reddit/actions.json"),
            ("data/default/recipes/hackernews/hn-read-frontpage.json", "data/default/primewiki/hackernews/actions.json"),
            ("data/default/recipes/slack/slack-channel-summary.json", "data/default/primewiki/slack/actions.json"),
            ("data/default/recipes/slack/slack-digest.json", "data/default/primewiki/slack/actions.json"),
            ("data/default/recipes/github/github-issue-triage.json", "data/default/primewiki/github/actions.json"),
            ("data/default/recipes/github/github-pr-review.json", "data/default/primewiki/github/actions.json"),
            ("data/default/recipes/notion/notion-page-reader.json", "data/default/primewiki/notion/actions.json"),
            ("data/default/recipes/notion/notion-daily.json", "data/default/primewiki/notion/actions.json"),
        ],
    )
    def test_scope_requirements_match_primewiki(self, recipe_rel: str, actions_rel: str):
        recipe = _load_json(PROJECT_ROOT / recipe_rel)
        actions_path = PROJECT_ROOT / actions_rel
        assert actions_path.exists(), f"Missing PrimeWiki actions: {actions_path}"
        action_scopes = _primewiki_scopes(actions_path)
        assert action_scopes, f"No oauth3_scope found in {actions_path}"

        recipe_scopes = recipe.get("oauth3_scopes", [])
        assert isinstance(recipe_scopes, list) and recipe_scopes, f"{recipe_rel} missing oauth3_scopes"
        assert set(recipe_scopes).issubset(action_scopes), (
            f"{recipe_rel} scopes {recipe_scopes} not covered by {actions_rel}"
        )

    @pytest.mark.parametrize(
        "recipe_rel",
        [
            "data/default/recipes/gmail/gmail-read-inbox.json",
            "data/default/recipes/reddit/reddit-browse-subreddit.json",
            "data/default/recipes/hackernews/hn-read-frontpage.json",
        ],
    )
    def test_reference_recipes_run_and_emit_evidence(self, recipe_rel: str, tmp_path: Path):
        recipe = _load_json(PROJECT_ROOT / recipe_rel)
        engine_recipe = _engine_recipe_from(recipe)
        engine = RecipeEngine(cache={}, llm=lambda _payload: engine_recipe)
        request = RecipeRequest(
            intent=recipe.get("description", recipe["id"]),
            platform=recipe["platform"],
            action_type=recipe["id"],
        )

        result = engine.run(request)
        assert result.status == FSMState.EXIT_PASS.value
        assert result.evidence_bundle is not None
        assert "bundle_id" in result.evidence_bundle

        pipeline = EvidencePipeline(evidence_dir=tmp_path)
        before = pipeline.capture_before(
            b"<!doctype html><html><body><h1>before</h1></body></html>" + b"x" * 1024,
            require_full_html=True,
        )
        after = pipeline.capture_after(
            b"<!doctype html><html><body><h1>after</h1></body></html>" + b"y" * 1024
        )
        diff = pipeline.compute_diff(before=before.compressed_bytes, after=after.compressed_bytes)
        bundle = pipeline.assemble_bundle(
            before_capture=before,
            after_capture=after,
            diff=diff,
            oauth3_token_id="token-task007",
            action_id=recipe["id"],
            platform=recipe["platform"],
            action_type="read",
            prev_bundle_id=None,
        )

        assert bundle["before_snapshot_pzip_hash"]
        assert bundle["after_snapshot_pzip_hash"]
        assert bundle["diff_hash"]
        assert bundle["signature"]
        assert bundle["alcoa_fields"]["complete"] is True

    def test_new_recipes_exist_with_required_fields(self):
        new_recipes = [
            PROJECT_ROOT / "data/default/recipes/slack/slack-channel-summary.json",
            PROJECT_ROOT / "data/default/recipes/slack/slack-digest.json",
            PROJECT_ROOT / "data/default/recipes/github/github-issue-triage.json",
            PROJECT_ROOT / "data/default/recipes/github/github-pr-review.json",
            PROJECT_ROOT / "data/default/recipes/notion/notion-page-reader.json",
            PROJECT_ROOT / "data/default/recipes/notion/notion-daily.json",
        ]
        required_fields = {"id", "platform", "oauth3_scopes", "budgets", "steps", "mermaid_fsm", "primewiki_reference"}

        for path in new_recipes:
            assert path.exists(), f"Missing recipe: {path}"
            recipe = _load_json(path)
            missing = required_fields - set(recipe.keys())
            assert not missing, f"{path} missing required fields: {sorted(missing)}"
            assert isinstance(recipe["oauth3_scopes"], list) and recipe["oauth3_scopes"]
            assert isinstance(recipe["budgets"], dict) and recipe["budgets"]
            assert isinstance(recipe["steps"], list) and recipe["steps"]
            assert "stateDiagram" in recipe["mermaid_fsm"]
            for step in recipe["steps"]:
                assert isinstance(step, dict)
                assert isinstance(step.get("step_id"), str) and step["step_id"]
                assert isinstance(step.get("action"), str) and step["action"]
                assert isinstance(step.get("scope_required"), str) and step["scope_required"]

            primewiki_path = PROJECT_ROOT / recipe["primewiki_reference"]
            assert primewiki_path.exists(), f"PrimeWiki reference not found: {primewiki_path}"

    @pytest.mark.parametrize("platform", ["slack", "github"])
    def test_new_platform_primewiki_triplet_exists(self, platform: str):
        base = PRIMEWIKI_ROOT / platform
        for name in ("actions.json", "selectors.json", "urls.json"):
            path = base / name
            assert path.exists(), f"Missing {path}"
            _load_json(path)
