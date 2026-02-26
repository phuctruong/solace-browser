from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.metrics import ExecutionMetrics, MetricsTracker


def test_recipe_metrics_log_and_summary(tmp_path: Path) -> None:
    tracker = MetricsTracker(metrics_file=tmp_path / "execution_metrics.jsonl")

    tracker.log(
        ExecutionMetrics(
            latency_ms=120,
            status="success",
            steps=4,
            scopes_used=["browser.navigate", "browser.click"],
            cost_estimate=0.0,
            cached=False,
        )
    )
    tracker.log(
        ExecutionMetrics(
            latency_ms=80,
            status="success",
            steps=4,
            scopes_used=["browser.navigate"],
            cost_estimate=0.0,
            cached=True,
        )
    )
    tracker.log(
        ExecutionMetrics(
            latency_ms=300,
            status="failed",
            steps=2,
            scopes_used=["browser.navigate"],
            cost_estimate=0.0,
            cached=False,
        )
    )

    summary = tracker.summary()
    assert summary["count"] == 3
    assert summary["hit_rate"] == 1 / 3
    assert summary["error_rate"] == 1 / 3
    assert summary["avg_latency_ms"] > 0
