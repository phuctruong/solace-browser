from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from browser.context import BrowserContext
from oauth3.vault import OAuth3Vault
from recipes.recipe_executor import RecipeExecutor
from store_client.store_client import StillwaterStoreClient


class _Resp:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(self.text)

    def json(self) -> dict:
        return self._body


class _Session:
    def request(self, method, url, timeout=15, **kwargs):
        if method == "GET" and url.endswith("/store/recipes/compose-email"):
            return _Resp(
                200,
                {
                    "recipe_id": "compose-email",
                    "version": "1.2.0",
                    "channel": "stable",
                    "rung_verified": 641,
                    "recipe_ir": {
                        "recipe_id": "compose-email",
                        "initial_state": "NavigateHome",
                        "steps": [
                            {
                                "step_id": "s1",
                                "state": "NavigateHome",
                                "action": "navigate",
                                "target": "https://example.com",
                                "params": {},
                                "condition_next_state": [{"condition": "done", "next_state": "[*]"}],
                            }
                        ],
                        "scopes_required": ["browser.navigate"],
                    },
                },
            )
        raise AssertionError(f"unexpected request {method} {url}")


async def _run_once(tmp_path: Path) -> str:
    client = StillwaterStoreClient(base_url="https://example.com", session=_Session())
    fetched = client.fetch_recipe("compose-email")

    vault = OAuth3Vault(
        encryption_key=b"t" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )
    scopes = sorted(set(fetched["recipe_ir"]["scopes_required"] + ["browser.read"]))
    token = vault.issue_token(scopes, ttl_seconds=3600)

    browser = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
        seed=65537,
    )
    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        determinism_seed=65537,
        execution_log=tmp_path / "recipe_execution_proof.jsonl",
    )

    result = await executor.execute(fetched["recipe_ir"], browser)
    await browser.close()
    return result.behavior_hash


@pytest.mark.asyncio
async def test_deterministic_store_execution_three_replays(tmp_path: Path) -> None:
    h1 = await _run_once(tmp_path / "r1")
    h2 = await _run_once(tmp_path / "r2")
    h3 = await _run_once(tmp_path / "r3")

    assert h1 == h2 == h3
