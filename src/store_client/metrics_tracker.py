"""Execution metrics tracking for store-integrated recipes."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List

from cli.init_workspace import resolve_solace_home


class StoreMetricsTracker:
    def __init__(self, metrics_file: str | Path | None = None) -> None:
        if metrics_file is None:
            metrics_file = resolve_solace_home() / "vault" / "execution_metrics.jsonl"
        self.metrics_file = Path(metrics_file).expanduser().resolve()
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def track_execution(
        self,
        recipe_id: str,
        execution_result: Dict[str, Any],
        *,
        latency_ms: int,
        scopes_used: List[str] | None = None,
        cache_hit: bool = False,
        version: str = "latest",
    ) -> Dict[str, Any]:
        trace = execution_result.get("output", {}).get("trace", [])
        step_details = [
            {
                "step": int(row.get("step", 0)),
                "action": row.get("action"),
                "status": row.get("result", {}).get("status"),
            }
            for row in trace
            if isinstance(row, dict)
        ]

        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recipe_id": recipe_id,
            "version": version,
            "latency_ms": int(latency_ms),
            "status": execution_result.get("status", "failed"),
            "steps_executed": int(execution_result.get("steps_executed", len(step_details))),
            "scopes_used": list(scopes_used or []),
            "step_details": step_details,
            "cache_hit": bool(cache_hit),
            "behavior_hash": execution_result.get("behavior_hash"),
        }

        with self.metrics_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(metrics, sort_keys=True) + "\n")

        return metrics

    def load(self) -> List[Dict[str, Any]]:
        if not self.metrics_file.exists():
            return []

        rows: List[Dict[str, Any]] = []
        with self.metrics_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows

    def aggregate(self) -> Dict[str, Any]:
        rows = self.load()
        if not rows:
            return {
                "count": 0,
                "hit_rate": 0.0,
                "avg_latency_ms": 0.0,
                "error_rate": 0.0,
            }

        count = len(rows)
        hit_rate = sum(1 for row in rows if bool(row.get("cache_hit"))) / count
        avg_latency = sum(int(row.get("latency_ms", 0)) for row in rows) / count
        error_rate = sum(1 for row in rows if row.get("status") != "success") / count

        return {
            "count": count,
            "hit_rate": hit_rate,
            "avg_latency_ms": avg_latency,
            "error_rate": error_rate,
        }
