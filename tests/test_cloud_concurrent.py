from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.cloud_test_support import build_cloud_app


@pytest.mark.asyncio
async def test_cloud_concurrent_execution_10_requests(tmp_path: Path) -> None:
    app, token_id, _ = build_cloud_app(tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async def one(i: int):
            req = {
                "recipe_id": "compose-email",
                "version": "1.2.0",
                "inputs": {"seed": 65537 + i},
                "scope_token": token_id,
            }
            return await client.post("/execute", json=req)

        responses = await asyncio.gather(*(one(i) for i in range(10)))

    assert all(r.status_code == 200 for r in responses)
    payloads = [r.json() for r in responses]
    assert all(p["status"] == "success" for p in payloads)

    health_transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=health_transport, base_url="http://test") as c2:
        h = await c2.get("/health")
    assert h.status_code == 200
    assert h.json()["peak_concurrency"] >= 1
