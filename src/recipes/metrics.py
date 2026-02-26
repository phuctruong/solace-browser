"""Recipe execution metrics for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List

from cli.init_workspace import resolve_solace_home


@dataclass(frozen=True)
class ExecutionMetrics:
    latency_ms: int
    status: str
    steps: int
    scopes_used: List[str]
    cost_estimate: float
    cached: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latency_ms": int(self.latency_ms),
            "status": self.status,
            "steps": int(self.steps),
            "scopes_used": list(self.scopes_used),
            "cost_estimate": float(self.cost_estimate),
            "cached": bool(self.cached),
        }


class MetricsTracker:
    def __init__(self, metrics_file: str | Path | None = None) -> None:
        if metrics_file is None:
            metrics_file = resolve_solace_home() / "vault" / "execution_metrics.jsonl"
        self.metrics_file = Path(metrics_file).expanduser().resolve()
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        payload = metrics.to_dict()
        with self.metrics_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload

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

    def summary(self) -> Dict[str, Any]:
        rows = self.load()
        if not rows:
            return {
                "count": 0,
                "hit_rate": 0.0,
                "avg_latency_ms": 0.0,
                "error_rate": 0.0,
            }

        count = len(rows)
        cached = sum(1 for row in rows if bool(row.get("cached")))
        avg_latency = sum(int(row.get("latency_ms", 0)) for row in rows) / count
        errors = sum(1 for row in rows if row.get("status") != "success")

        return {
            "count": count,
            "hit_rate": cached / count,
            "avg_latency_ms": avg_latency,
            "error_rate": errors / count,
        }
