from __future__ import annotations

import sys
from pathlib import Path
import time

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from browser.context import BrowserContext
from oauth3.vault import OAuth3Vault
from recipes.recipe_executor import RecipeExecutor
from store_client.metrics_reporter import MetricsReporter
from store_client.metrics_tracker import StoreMetricsTracker
from store_client.recipe_cache import StoreRecipeCache
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
    def __init__(self):
        self.calls = []

    def request(self, method, url, timeout=15, **kwargs):
        self.calls.append((method, url, kwargs))
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
        if method == "POST" and url.endswith("/store/recipes/compose-email/metrics"):
            executions = kwargs.get("json", {}).get("executions", [])
            return _Resp(200, {"status": "recorded", "recipe_id": "compose-email", "metrics_count": len(executions)})
        raise AssertionError(f"unexpected request {method} {url}")


@pytest.mark.asyncio
async def test_store_integration_e2e_fetch_execute_track_report(tmp_path: Path) -> None:
    session = _Session()
    client = StillwaterStoreClient(base_url="https://example.com", session=session)
    cache = StoreRecipeCache(cache_root=tmp_path / "store_cache")
    tracker = StoreMetricsTracker(metrics_file=tmp_path / "execution_metrics.jsonl")
    reporter = MetricsReporter(
        client=client,
        queue_file=tmp_path / "metrics_queue.jsonl",
        submission_log=tmp_path / "metrics_submission_proof.jsonl",
        batch_size=1,
        flush_interval_seconds=3600,
    )

    fetched = client.fetch_recipe("compose-email")
    cache.cache_recipe(fetched["recipe_id"], fetched["version"], fetched["recipe_ir"])
    cached = cache.get_cached_recipe(fetched["recipe_id"], fetched["version"])
    assert cached is not None

    vault = OAuth3Vault(
        encryption_key=b"s" * 32,
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

    t0 = time.perf_counter()
    result = await executor.execute(fetched["recipe_ir"], browser)
    await browser.close()
    latency_ms = int((time.perf_counter() - t0) * 1000)

    metrics = tracker.track_execution(
        fetched["recipe_id"],
        result.to_dict(),
        latency_ms=latency_ms,
        scopes_used=scopes,
        cache_hit=True,
        version=fetched["version"],
    )

    post = reporter.submit_metrics(fetched["recipe_id"], metrics, version=fetched["version"])

    assert result.status == "success"
    assert post["status"] == "recorded"
    assert cache.stats()["hits"] == 1
