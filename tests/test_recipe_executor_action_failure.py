from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from browser.context import BrowserContext
from oauth3.vault import OAuth3Vault
from recipes.recipe_executor import ExecutionError, RecipeExecutor


@pytest.mark.asyncio
async def test_recipe_executor_action_failure_raises_execution_error(tmp_path: Path) -> None:
    ir = {
        "recipe_id": "action-failure",
        "version": "1.0.0",
        "determinism_seed": 7,
        "initial_state": "ClickMissing",
        "scopes_required": ["browser.click"],
        "steps": [
            {
                "step_id": "s1",
                "state": "ClickMissing",
                "action": "click",
                "target": "#missing-button",
                "params": {},
                "condition_next_state": [{"condition": "always", "next_state": "[*]"}],
            }
        ],
    }

    vault = OAuth3Vault(
        encryption_key=b"j" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )
    token = vault.issue_token(["browser.click"], ttl_seconds=3600)

    browser = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
        seed=22,
    )

    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        determinism_seed=7,
        execution_log=tmp_path / "recipe_execution_proof.jsonl",
    )

    with pytest.raises(ExecutionError):
        await executor.execute(ir, browser)

    await browser.close()
