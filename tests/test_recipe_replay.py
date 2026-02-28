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
from recipes.recipe_executor import RecipeExecutor, ReplayError
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


async def _execute_once(tmp_path: Path) -> tuple[RecipeExecutor, dict[str, object], object]:
    ast = parse(RECIPE, recipe_id="replay-demo")
    ir = compile(ast, determinism_seed=65537).to_dict()

    vault = OAuth3Vault(
        encryption_key=b"r" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )

    scopes = sorted(set(ir["scopes_required"] + ["browser.read", "browser.dom"]))
    token = vault.issue_token(scopes, ttl_seconds=3600)
    browser = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
        seed=202,
    )
    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        determinism_seed=65537,
        execution_log=tmp_path / "recipe_execution_proof.jsonl",
    )

    result = await executor.execute(ir, browser)
    await browser.close()
    return executor, ir, result


@pytest.mark.asyncio
async def test_execute_seal_and_replay_match_hash(tmp_path: Path) -> None:
    executor, ir, result = await _execute_once(tmp_path)

    sealed = executor.seal_output(ir, result)

    assert executor.execute_replay(ir, sealed) is True


@pytest.mark.asyncio
async def test_replay_detects_tampered_sealed_output(tmp_path: Path) -> None:
    executor, ir, result = await _execute_once(tmp_path)

    sealed = executor.seal_output(ir, result)
    sealed["output"]["trace"][0]["state"] = "TamperedState"

    assert executor.execute_replay(ir, sealed) is False


@pytest.mark.asyncio
async def test_replay_cost_is_zero(tmp_path: Path) -> None:
    executor, ir, result = await _execute_once(tmp_path)

    sealed = executor.seal_output(ir, result)

    assert executor.execute_replay(ir, sealed) is True
    assert executor.last_replay_cost == 0.0


@pytest.mark.asyncio
async def test_replay_three_times_is_identical(tmp_path: Path) -> None:
    executor, ir, result = await _execute_once(tmp_path)
    sealed = executor.seal_output(ir, result)

    outcomes = [executor.execute_replay(ir, sealed) for _ in range(3)]

    assert outcomes == [True, True, True]


def test_replay_missing_recipe_raises_specific_error(tmp_path: Path) -> None:
    vault = OAuth3Vault(
        encryption_key=b"r" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )
    token = vault.issue_token(["browser.navigate"], ttl_seconds=3600)
    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        determinism_seed=65537,
        execution_log=tmp_path / "recipe_execution_proof.jsonl",
    )

    with pytest.raises(ReplayError):
        executor.execute_replay({}, {"recipe_id": "missing", "output": {}, "output_hash": "x"})
