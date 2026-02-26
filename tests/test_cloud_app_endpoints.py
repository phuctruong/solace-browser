from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.cloud_test_support import build_cloud_app


def test_cloud_health_and_metrics_endpoints(tmp_path: Path) -> None:
    app, token_id, _ = build_cloud_app(tmp_path)
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    payload = {
        "recipe_id": "compose-email",
        "version": "1.2.0",
        "metrics": [{"latency_ms": 100, "status": "success", "steps_executed": 1}],
    }
    out = client.post("/metrics", json=payload)
    assert out.status_code == 200
    assert out.json()["status"] == "recorded"
    assert out.json()["metrics_count"] == 1


def test_cloud_execute_timeout_returns_504(tmp_path: Path) -> None:
    app, token_id, _ = build_cloud_app(tmp_path, timeout_seconds=1)
    client = TestClient(app)

    req = {
        "recipe_id": "compose-email",
        "version": "1.2.0",
        "inputs": {"simulate_delay_ms": 1200},
        "scope_token": token_id,
    }
    resp = client.post("/execute", json=req)
    assert resp.status_code == 504
