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
  FillRecipient --> VerifyPage: action_ok
  VerifyPage --> Complete: action_ok
  Complete --> [*]: done
""".strip()


async def _run_once(tmp_path: Path) -> str:
    ast = parse(RECIPE, recipe_id="determinism")
    ir = compile(ast, determinism_seed=65537).to_dict()

    vault = OAuth3Vault(
        encryption_key=b"k" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )
    scopes = sorted(set(ir["scopes_required"] + ["browser.read", "browser.dom"]))
    token = vault.issue_token(scopes, ttl_seconds=3600)

    browser = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
        seed=77,
    )

    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        determinism_seed=65537,
        execution_log=tmp_path / "recipe_execution_proof.jsonl",
    )

    result = await executor.execute(ir, browser)
    await browser.close()
    return result.behavior_hash


@pytest.mark.asyncio
async def test_three_replays_same_seed_same_behavior_hash(tmp_path: Path) -> None:
    run1 = await _run_once(tmp_path / "r1")
    run2 = await _run_once(tmp_path / "r2")
    run3 = await _run_once(tmp_path / "r3")

    assert run1 == run2 == run3
