from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from store_client.metrics_reporter import MetricsReporter
from store_client.store_client import StoreError


class _ClientOK:
    def __init__(self) -> None:
        self.calls = []

    def post_metrics(self, recipe_id: str, metrics: dict) -> dict:
        self.calls.append((recipe_id, metrics))
        return {"status": "recorded", "recipe_id": recipe_id, "metrics_count": len(metrics.get("executions", []))}


class _ClientFail:
    def post_metrics(self, recipe_id: str, metrics: dict) -> dict:
        raise StoreError("store down")


def test_metrics_reporter_batches_and_submits(tmp_path: Path) -> None:
    client = _ClientOK()
    reporter = MetricsReporter(
        client=client,
        queue_file=tmp_path / "metrics_queue.jsonl",
        submission_log=tmp_path / "submission.jsonl",
        batch_size=2,
        flush_interval_seconds=3600,
    )

    out1 = reporter.submit_metrics("compose-email", {"latency_ms": 10}, version="1.2.0")
    assert out1["status"] == "queued"

    out2 = reporter.submit_metrics("compose-email", {"latency_ms": 11}, version="1.2.0")
    assert out2["status"] == "recorded"
    assert out2["submitted"] == 2
    assert len(client.calls) == 1


def test_metrics_reporter_keeps_queue_on_failure(tmp_path: Path) -> None:
    reporter = MetricsReporter(
        client=_ClientFail(),
        queue_file=tmp_path / "metrics_queue.jsonl",
        submission_log=tmp_path / "submission.jsonl",
        batch_size=1,
        flush_interval_seconds=3600,
    )

    with pytest.raises(StoreError):
        reporter.submit_metrics("compose-email", {"latency_ms": 33}, version="1.2.0")

    lines = (tmp_path / "metrics_queue.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1


def test_metrics_reporter_flushes_on_hourly_window(tmp_path: Path) -> None:
    client = _ClientOK()
    queue_file = tmp_path / "metrics_queue.jsonl"

    old_row = {
        "recipe_id": "compose-email",
        "version": "1.2.0",
        "metrics": {"latency_ms": 77},
        "queued_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
    }
    queue_file.write_text(json.dumps(old_row) + "\n", encoding="utf-8")

    reporter = MetricsReporter(
        client=client,
        queue_file=queue_file,
        submission_log=tmp_path / "submission.jsonl",
        batch_size=10,
        flush_interval_seconds=3600,
    )

    out = reporter.flush(force=False)
    assert out["status"] == "recorded"
    assert out["submitted"] == 1
    assert len(client.calls) == 1
