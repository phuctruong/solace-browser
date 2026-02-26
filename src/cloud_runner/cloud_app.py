"""Cloud runner FastAPI app for remote recipe execution."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from browser.context import BrowserContext
from oauth3.vault import OAuth3Vault
from recipes.recipe_executor import ExecutionError, RecipeExecutor
from store_client.metrics_reporter import MetricsReporter
from store_client.metrics_tracker import StoreMetricsTracker
from store_client.recipe_cache import StoreRecipeCache
from store_client.store_client import DEFAULT_BASE_URL, StillwaterStoreClient, StoreError


EXECUTION_TIMEOUT_SECONDS = 300


class ExecuteRequest(BaseModel):
    recipe_id: str
    version: str = "latest"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    scope_token: str


class MetricsRequest(BaseModel):
    recipe_id: str
    version: str = "latest"
    metrics: list[Dict[str, Any]]


@dataclass
class SessionRegistry:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    active: set[str] = field(default_factory=set)
    peak: int = 0

    async def start(self) -> str:
        exec_id = f"exec_{uuid.uuid4().hex[:12]}"
        async with self.lock:
            self.active.add(exec_id)
            if len(self.active) > self.peak:
                self.peak = len(self.active)
        return exec_id

    async def finish(self, exec_id: str) -> None:
        async with self.lock:
            self.active.discard(exec_id)

    async def snapshot(self) -> Dict[str, int]:
        async with self.lock:
            return {
                "active": len(self.active),
                "peak": self.peak,
            }


def create_cloud_app(
    *,
    store_client: StillwaterStoreClient | None = None,
    recipe_cache: StoreRecipeCache | None = None,
    metrics_tracker: StoreMetricsTracker | None = None,
    metrics_reporter: MetricsReporter | None = None,
    oauth3_vault: OAuth3Vault | None = None,
    execution_timeout_seconds: int = EXECUTION_TIMEOUT_SECONDS,
) -> FastAPI:
    phase_dir = Path("scratch") / "evidence" / "phase_4"
    phase_dir.mkdir(parents=True, exist_ok=True)

    client = store_client or StillwaterStoreClient(base_url=DEFAULT_BASE_URL)
    cache = recipe_cache or StoreRecipeCache(cache_root=phase_dir / "store_cache")
    tracker = metrics_tracker or StoreMetricsTracker(metrics_file=phase_dir / "execution_metrics.jsonl")
    reporter = metrics_reporter or MetricsReporter(
        client=client,
        queue_file=phase_dir / "metrics_queue.jsonl",
        submission_log=phase_dir / "metrics_submission_proof.jsonl",
        batch_size=10,
        flush_interval_seconds=3600,
    )
    vault = oauth3_vault or OAuth3Vault(
        encryption_key=b"v" * 32,
        evidence_log=phase_dir / "oauth3_audit.jsonl",
        storage_path=phase_dir / "oauth3_tokens.enc.json",
    )

    registry = SessionRegistry()

    app = FastAPI(title="Solace Cloud Runner", version="1.0.0")
    app.state.store_client = client
    app.state.recipe_cache = cache
    app.state.metrics_tracker = tracker
    app.state.metrics_reporter = reporter
    app.state.oauth3_vault = vault
    app.state.session_registry = registry
    app.state.execution_timeout_seconds = int(execution_timeout_seconds)

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        snap = await registry.snapshot()
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_executions": snap["active"],
            "peak_concurrency": snap["peak"],
        }

    @app.post("/execute")
    async def execute(request: ExecuteRequest) -> Dict[str, Any]:
        if not request.recipe_id.strip():
            raise HTTPException(status_code=422, detail="recipe_id is required")

        execution_id = await registry.start()
        started = time.perf_counter()
        browser: BrowserContext | None = None

        try:
            fetched = _load_recipe(
                client=client,
                cache=cache,
                recipe_id=request.recipe_id,
                version=request.version,
            )
            recipe_ir = dict(fetched.get("recipe_ir") or {})
            if not recipe_ir.get("steps"):
                raise HTTPException(status_code=422, detail="invalid recipe: recipe_ir.steps is required")

            seed = int(request.inputs.get("seed", recipe_ir.get("determinism_seed", 65537)))

            browser = BrowserContext(
                oauth3_vault=vault,
                token_id=request.scope_token,
                evidence_log=phase_dir / "browser_events.jsonl",
                seed=seed,
            )
            executor = RecipeExecutor(
                oauth3_vault=vault,
                token_id=request.scope_token,
                determinism_seed=seed,
                execution_log=phase_dir / "cloud_execution_events.jsonl",
            )

            try:
                async def _run_with_optional_delay() -> Any:
                    simulated = int(request.inputs.get("simulate_delay_ms", 0))
                    if simulated > 0:
                        await asyncio.sleep(simulated / 1000)
                    return await executor.execute(recipe_ir, browser, inputs=request.inputs)

                result = await asyncio.wait_for(
                    _run_with_optional_delay(),
                    timeout=int(execution_timeout_seconds),
                )
            except asyncio.TimeoutError as exc:
                raise HTTPException(status_code=504, detail="execution timeout") from exc
            except ExecutionError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            latency_ms = int((time.perf_counter() - started) * 1000)
            metrics = tracker.track_execution(
                request.recipe_id,
                result.to_dict(),
                latency_ms=latency_ms,
                scopes_used=list(recipe_ir.get("scopes_required") or []),
                cache_hit=bool(fetched.get("source") == "cache"),
                version=str(fetched.get("version", request.version)),
            )
            try:
                report_status = reporter.submit_metrics(
                    request.recipe_id,
                    metrics,
                    version=str(fetched.get("version", request.version)),
                )
            except StoreError as exc:
                raise HTTPException(status_code=500, detail=f"metrics submission failed: {exc}") from exc

            return {
                "status": "success",
                "execution_id": execution_id,
                "recipe_id": request.recipe_id,
                "version": str(fetched.get("version", request.version)),
                "execution_log": result.output.get("trace", []),
                "screenshots": [result.final_screenshot] if result.final_screenshot else [],
                "behavior_hash": result.behavior_hash,
                "metrics": {
                    "latency_ms": metrics["latency_ms"],
                    "steps_executed": metrics["steps_executed"],
                    "status": metrics["status"],
                },
                "report_status": report_status,
            }
        except StoreError as exc:
            raise HTTPException(status_code=422, detail=f"store fetch failed: {exc}") from exc
        finally:
            if browser is not None:
                await browser.close()
            await registry.finish(execution_id)

    @app.post("/metrics")
    async def metrics(request: MetricsRequest) -> Dict[str, Any]:
        if not request.recipe_id.strip():
            raise HTTPException(status_code=422, detail="recipe_id is required")

        recorded = 0
        try:
            for item in request.metrics:
                reporter.submit_metrics(request.recipe_id, dict(item), version=request.version)
                recorded += 1
            flush_result = reporter.flush(force=True)
        except StoreError as exc:
            raise HTTPException(status_code=500, detail=f"metrics submission failed: {exc}") from exc

        return {
            "status": "recorded",
            "recorded": True,
            "metrics_count": recorded,
            "flush": flush_result,
        }

    return app


def _load_recipe(
    *,
    client: StillwaterStoreClient,
    cache: StoreRecipeCache,
    recipe_id: str,
    version: str,
) -> Dict[str, Any]:
    if version != "latest" and not cache.is_cache_stale(recipe_id, version, max_age_hours=24):
        cached = cache.get_cached_recipe(recipe_id, version)
        if cached is not None:
            return {
                "recipe_id": recipe_id,
                "version": version,
                "recipe_ir": cached,
                "source": "cache",
            }

    fetched = client.fetch_recipe(recipe_id, version=version)
    recipe_ir = dict(fetched.get("recipe_ir") or {})
    resolved_version = str(fetched.get("version", version))
    cache.cache_recipe(recipe_id, resolved_version, recipe_ir)

    return {
        "recipe_id": str(fetched.get("recipe_id", recipe_id)),
        "version": resolved_version,
        "recipe_ir": recipe_ir,
        "source": "store",
    }


app = create_cloud_app()
