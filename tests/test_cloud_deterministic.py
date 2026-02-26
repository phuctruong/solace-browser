from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.cloud_test_support import build_cloud_app


def test_cloud_deterministic_three_replays_same_hash(tmp_path: Path) -> None:
    app, token_id, _ = build_cloud_app(tmp_path)
    client = TestClient(app)

    def run_once() -> str:
        req = {
            "recipe_id": "compose-email",
            "version": "1.2.0",
            "inputs": {"seed": 65537},
            "scope_token": token_id,
        }
        out = client.post("/execute", json=req)
        assert out.status_code == 200
        return out.json()["behavior_hash"]

    h1 = run_once()
    h2 = run_once()
    h3 = run_once()

    assert h1 == h2 == h3
