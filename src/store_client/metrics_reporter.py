"""Metrics reporter with batching and durable retry queue."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from typing import Any, Dict, List

from cli.init_workspace import resolve_solace_home

from .store_client import StillwaterStoreClient, StoreError


class MetricsReporter:
    def __init__(
        self,
        *,
        client: StillwaterStoreClient,
        queue_file: str | Path | None = None,
        submission_log: str | Path | None = None,
        batch_size: int = 10,
        flush_interval_seconds: int = 3600,
    ) -> None:
        self.client = client
        if queue_file is None:
            queue_file = resolve_solace_home() / "vault" / "metrics_queue.jsonl"
        if submission_log is None:
            submission_log = Path("scratch") / "evidence" / "phase_3" / "metrics_submission_proof.jsonl"

        self.queue_file = Path(queue_file).expanduser().resolve()
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)

        self.submission_log = Path(submission_log).expanduser().resolve()
        self.submission_log.parent.mkdir(parents=True, exist_ok=True)

        self.batch_size = int(batch_size)
        self.flush_interval_seconds = int(flush_interval_seconds)

    def submit_metrics(self, recipe_id: str, metrics: Dict[str, Any], *, version: str = "latest") -> Dict[str, Any]:
        queued = self._read_queue()
        entry = {
            "recipe_id": recipe_id,
            "version": version,
            "metrics": metrics,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }
        queued.append(entry)
        self._write_queue(queued)
        self._log("QUEUE_APPEND", {"recipe_id": recipe_id, "queue_size": len(queued)})

        should_flush = self._should_flush(queued)
        if should_flush:
            return self.flush(force=False)
        return {"status": "queued", "queue_size": len(queued)}

    def flush(self, *, force: bool = True) -> Dict[str, Any]:
        queued = self._read_queue()
        if not queued:
            return {"status": "no-op", "submitted": 0}

        if not force and not self._should_flush(queued):
            return {"status": "queued", "queue_size": len(queued)}

        grouped: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
        for item in queued:
            key = (str(item["recipe_id"]), str(item.get("version", "latest")))
            grouped.setdefault(key, []).append(dict(item["metrics"]))

        submitted = 0
        for (recipe_id, version), executions in grouped.items():
            payload = {
                "version": version,
                "executions": executions,
            }
            try:
                response = self.client.post_metrics(recipe_id, payload)
            except StoreError as exc:
                self._log("METRICS_SUBMIT_FAILED", {"recipe_id": recipe_id, "error": str(exc)})
                raise

            submitted += len(executions)
            self._log("METRICS_SUBMITTED", {"recipe_id": recipe_id, "count": len(executions), "response": response})

        self._write_queue([])
        return {"status": "recorded", "submitted": submitted}

    def _should_flush(self, queued: List[Dict[str, Any]]) -> bool:
        if len(queued) >= self.batch_size:
            return True

        oldest = queued[0]
        ts_raw = str(oldest.get("queued_at", ""))
        if not ts_raw:
            return False

        queued_at = datetime.fromisoformat(ts_raw)
        return datetime.now(timezone.utc) - queued_at >= timedelta(seconds=self.flush_interval_seconds)

    def _read_queue(self) -> List[Dict[str, Any]]:
        if not self.queue_file.exists():
            return []

        rows: List[Dict[str, Any]] = []
        with self.queue_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows

    def _write_queue(self, rows: List[Dict[str, Any]]) -> None:
        with self.queue_file.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, sort_keys=True) + "\n")

    def _log(self, event_type: str, data: Dict[str, Any]) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data,
        }
        with self.submission_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
