from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from store_client.store_client import StillwaterStoreClient, StoreError


class _Resp:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(self.text)

    def json(self) -> dict:
        return self._body


class _Session:
    def __init__(self, events):
        self.events = list(events)
        self.calls = 0

    def request(self, method, url, timeout=15, **kwargs):
        self.calls += 1
        event = self.events.pop(0)
        if isinstance(event, Exception):
            raise event
        return event


def test_store_client_list_fetch_and_post_metrics() -> None:
    sess = _Session(
        [
            _Resp(200, {"recipes": [{"recipe_id": "compose-email", "version": "1.2.0", "downloads": 10}]}),
            _Resp(200, {"recipe_id": "compose-email", "version": "1.2.0", "channel": "stable", "recipe_ir": {"steps": []}, "rung_verified": 641}),
            _Resp(200, {"status": "recorded", "recipe_id": "compose-email", "metrics_count": 1}),
        ]
    )
    c = StillwaterStoreClient(base_url="https://example.com", session=sess)

    rows = c.list_recipes(channel="stable")
    assert rows[0]["recipe_id"] == "compose-email"

    recipe = c.fetch_recipe("compose-email", version="latest")
    assert recipe["version"] == "1.2.0"
    assert recipe["rung_verified"] == 641

    out = c.post_metrics("compose-email", {"version": "1.2.0", "executions": [{"latency_ms": 12}]})
    assert out["status"] == "recorded"


def test_store_client_retries_network_errors_then_succeeds() -> None:
    sess = _Session(
        [
            requests.ConnectionError("timeout-1"),
            requests.ConnectionError("timeout-2"),
            _Resp(200, {"recipes": []}),
        ]
    )
    c = StillwaterStoreClient(base_url="https://example.com", session=sess, retries=3)
    rows = c.list_recipes()
    assert rows == []
    assert sess.calls == 3


def test_store_client_fail_loud_after_retry_exhaustion() -> None:
    sess = _Session([
        requests.ConnectionError("timeout-1"),
        requests.ConnectionError("timeout-2"),
        requests.ConnectionError("timeout-3"),
    ])
    c = StillwaterStoreClient(base_url="https://example.com", session=sess, retries=3)

    with pytest.raises(StoreError):
        c.list_recipes()
