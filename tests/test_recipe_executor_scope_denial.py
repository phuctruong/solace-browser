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
from recipes.recipe_executor import ExecutionError, RecipeExecutor
from recipes.recipe_parser import parse


RECIPE = """
stateDiagram-v2
  [*] --> NavigateHome
  NavigateHome --> ClickCompose: action_ok
  ClickCompose --> FillRecipient: action_ok
  FillRecipient --> Complete: action_ok
  Complete --> [*]: done
""".strip()


@pytest.mark.asyncio
async def test_recipe_executor_scope_denial_raises_execution_error(tmp_path: Path) -> None:
    ast = parse(RECIPE, recipe_id="scope-denial")
    ir = compile(ast, determinism_seed=9).to_dict()

    vault = OAuth3Vault(
        encryption_key=b"i" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )

    # Omit browser.fill so execution must fail at FillRecipient.
    token = vault.issue_token(["browser.navigate", "browser.click", "browser.read"], ttl_seconds=3600)

    browser = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
        seed=11,
    )

    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        determinism_seed=9,
        execution_log=tmp_path / "recipe_execution_proof.jsonl",
    )

    with pytest.raises(ExecutionError):
        await executor.execute(ir, browser)

    await browser.close()
