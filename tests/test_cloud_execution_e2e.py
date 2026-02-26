from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.cloud_test_support import build_cloud_app


def test_cloud_execute_e2e_success(tmp_path: Path) -> None:
    app, token_id, fake_store = build_cloud_app(tmp_path)
    client = TestClient(app)

    req = {
        "recipe_id": "compose-email",
        "version": "1.2.0",
        "inputs": {"seed": 65537},
        "scope_token": token_id,
    }

    resp = client.post("/execute", json=req)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["recipe_id"] == "compose-email"
    assert body["metrics"]["steps_executed"] == 1
    assert len(body["behavior_hash"]) == 64
    assert len(fake_store.metrics_calls) >= 1
