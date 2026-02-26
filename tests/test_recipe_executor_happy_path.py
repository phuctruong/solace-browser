from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from browser.context import BrowserContext
from oauth3.vault import OAuth3Vault
from recipes.recipe_compiler import compile
from recipes.recipe_executor import RecipeExecutor
from recipes.recipe_parser import parse


RECIPE = """
stateDiagram-v2
  [*] --> NavigateHome
  NavigateHome --> ClickCompose: action_ok
  ClickCompose --> FillRecipient: action_ok
  FillRecipient --> ScreenshotProof: action_ok
  ScreenshotProof --> VerifyPage: action_ok
  VerifyPage --> Complete: action_ok
  Complete --> [*]: done
""".strip()


@pytest.mark.asyncio
async def test_recipe_executor_happy_path(tmp_path: Path) -> None:

    ast = parse(RECIPE, recipe_id="executor-happy")
    ir = compile(ast, determinism_seed=65537).to_dict()

    vault = OAuth3Vault(
        encryption_key=b"h" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )

    scopes = sorted(set(ir["scopes_required"] + ["browser.read", "browser.dom"]))
    token = vault.issue_token(scopes, ttl_seconds=3600)

    browser = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
        seed=101,
    )

    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        determinism_seed=65537,
        execution_log=tmp_path / "recipe_execution_proof.jsonl",
    )

    result = await executor.execute(ir, browser)

    assert result.status == "success"
    assert result.steps_executed == 6
    assert len(result.behavior_hash) == 64
    assert (tmp_path / "recipe_execution_proof.jsonl").exists()

    await browser.close()
