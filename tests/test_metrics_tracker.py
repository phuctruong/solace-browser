from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from store_client.metrics_tracker import StoreMetricsTracker


def test_metrics_tracker_captures_and_aggregates(tmp_path: Path) -> None:
    tracker = StoreMetricsTracker(metrics_file=tmp_path / "execution_metrics.jsonl")

    tracker.track_execution(
        "compose-email",
        {"status": "success", "steps_executed": 3, "behavior_hash": "h1", "output": {"trace": [{"step": 1, "action": "navigate", "result": {"status": "success"}}]}},
        latency_ms=120,
        scopes_used=["browser.navigate"],
        cache_hit=False,
        version="1.2.0",
    )
    tracker.track_execution(
        "compose-email",
        {"status": "failed", "steps_executed": 2, "behavior_hash": "h2", "output": {"trace": [{"step": 1, "action": "navigate", "result": {"status": "success"}}]}},
        latency_ms=300,
        scopes_used=["browser.navigate"],
        cache_hit=True,
        version="1.2.0",
    )

    summary = tracker.aggregate()
    assert summary["count"] == 2
    assert summary["avg_latency_ms"] == 210
    assert summary["hit_rate"] == 0.5
    assert summary["error_rate"] == 0.5
