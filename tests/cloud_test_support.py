from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from cloud_runner.cloud_app import create_cloud_app
from oauth3.vault import OAuth3Vault
from store_client.metrics_reporter import MetricsReporter
from store_client.metrics_tracker import StoreMetricsTracker
from store_client.recipe_cache import StoreRecipeCache
from store_client.store_client import StoreError


class FakeStoreClient:
    def __init__(self, recipe_ir: Dict[str, Any], *, fail_fetch: bool = False) -> None:
        self.recipe_ir = recipe_ir
        self.fail_fetch = fail_fetch
        self.metrics_calls = []

    def list_recipes(self, channel: str = "stable"):
        return [{"recipe_id": "compose-email", "version": "1.2.0", "downloads": 1, "channel": channel}]

    def fetch_recipe(self, recipe_id: str, version: str = "latest"):
        if self.fail_fetch:
            raise StoreError("store fetch failed")
        return {
            "recipe_id": recipe_id,
            "version": "1.2.0" if version == "latest" else version,
            "channel": "stable",
            "recipe_ir": self.recipe_ir,
            "rung_verified": 641,
        }

    def post_metrics(self, recipe_id: str, metrics: Dict[str, Any]):
        self.metrics_calls.append((recipe_id, metrics))
        executions = metrics.get("executions", [])
        return {
            "status": "recorded",
            "recipe_id": recipe_id,
            "metrics_count": len(executions),
        }


def default_recipe_ir() -> Dict[str, Any]:
    return {
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
        "determinism_seed": 65537,
    }


def build_cloud_app(tmp_path: Path, *, timeout_seconds: int = 300, recipe_ir: Dict[str, Any] | None = None, fail_fetch: bool = False):
    ir = recipe_ir or default_recipe_ir()
    client = FakeStoreClient(ir, fail_fetch=fail_fetch)
    cache = StoreRecipeCache(cache_root=tmp_path / "store_cache")
    tracker = StoreMetricsTracker(metrics_file=tmp_path / "execution_metrics.jsonl")
    reporter = MetricsReporter(
        client=client,
        queue_file=tmp_path / "metrics_queue.jsonl",
        submission_log=tmp_path / "metrics_submission_proof.jsonl",
        batch_size=1,
        flush_interval_seconds=3600,
    )
    vault = OAuth3Vault(
        encryption_key=b"w" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )
    token = vault.issue_token(["browser.navigate", "browser.read"], ttl_seconds=3600)

    app = create_cloud_app(
        store_client=client,
        recipe_cache=cache,
        metrics_tracker=tracker,
        metrics_reporter=reporter,
        oauth3_vault=vault,
        execution_timeout_seconds=timeout_seconds,
    )

    return app, token["token_id"], client
