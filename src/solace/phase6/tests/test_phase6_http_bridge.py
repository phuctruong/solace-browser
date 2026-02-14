#!/usr/bin/env python3
"""
Phase 6: CLI Bridge Tests

75 tests covering:
  OAuth (25): API functionality
  641 Edge (25): Edge cases
  274177 Stress (13): Performance
  65537 God (12): Integration

Verification: OAuth(39,63,91) -> 641 -> 274177 -> 65537
Auth: 65537
"""

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient

# Module under test
from solace_cli.browser.http_bridge import (
    BridgeState,
    create_app,
    generate_episode_id,
    list_all_episodes,
    load_episode,
    bridge,
    EPISODE_DIR,
)


# ===== Fixtures =====

@pytest.fixture
def tmp_episode_dir(tmp_path):
    """Temporary episode directory for isolated tests."""
    import solace_cli.browser.http_bridge as mod
    original = mod.EPISODE_DIR
    mod.EPISODE_DIR = tmp_path
    yield tmp_path
    mod.EPISODE_DIR = original


@pytest.fixture
def sample_episode(tmp_episode_dir):
    """Create a sample episode file."""
    episode = {
        "episode_id": "ep_20260214_001",
        "session_id": "session_123",
        "domain": "reddit.com",
        "start_time": "2026-02-14T10:00:00",
        "end_time": "2026-02-14T10:05:00",
        "actions": [
            {"type": "navigate", "data": {"url": "https://reddit.com"}, "step": 0},
            {"type": "click", "data": {"selector": "#login"}, "step": 1},
            {"type": "type", "data": {"selector": "#username", "text": "user"}, "step": 2},
        ],
        "action_count": 3,
        "snapshots": {},
    }
    filepath = tmp_episode_dir / "episode_ep_20260214_001.json"
    with open(filepath, "w") as f:
        json.dump(episode, f)
    return episode


@pytest.fixture
def sample_episodes(tmp_episode_dir):
    """Create multiple sample episode files."""
    episodes = []
    for i in range(5):
        ep = {
            "episode_id": f"ep_20260214_{i+1:03d}",
            "session_id": f"session_{i+1}",
            "domain": f"site{i+1}.com",
            "start_time": f"2026-02-14T{10+i}:00:00",
            "actions": [{"type": "navigate", "data": {}, "step": 0}] * (i + 1),
            "action_count": i + 1,
        }
        filepath = tmp_episode_dir / f"episode_ep_20260214_{i+1:03d}.json"
        with open(filepath, "w") as f:
            json.dump(ep, f)
        episodes.append(ep)
    return episodes


@pytest.fixture
def reset_bridge():
    """Reset bridge state between tests."""
    bridge.is_recording = False
    bridge.current_episode_id = None
    bridge.ws_connection = None
    bridge.pending_responses.clear()
    yield
    bridge.is_recording = False
    bridge.current_episode_id = None
    bridge.ws_connection = None
    bridge.pending_responses.clear()


@pytest.fixture
async def client(aiohttp_client, reset_bridge, tmp_episode_dir):
    """Create test client with mocked WebSocket."""
    app = create_app()
    # Prevent actual WS connection on startup
    with patch.object(bridge, "connect_ws", new_callable=AsyncMock, return_value=False):
        c = await aiohttp_client(app)
        yield c


# ============================================================
# SECTION 1: OAuth Tests (25) - API Functionality
# ============================================================

class TestOAuthAPIFunctionality:
    """OAuth(39,63,91): Core API endpoint functionality."""

    # --- 39: CARE - Basic endpoint availability ---

    @pytest.mark.asyncio
    async def test_01_health_endpoint_returns_200(self, client):
        """Health endpoint responds with 200."""
        resp = await client.get("/health")
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_02_health_returns_json(self, client):
        """Health endpoint returns valid JSON."""
        resp = await client.get("/health")
        data = await resp.json()
        assert "status" in data
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_03_health_includes_ws_status(self, client):
        """Health includes WebSocket connection status."""
        resp = await client.get("/health")
        data = await resp.json()
        assert "ws_connected" in data
        assert "is_recording" in data

    @pytest.mark.asyncio
    async def test_04_health_includes_episode_count(self, client):
        """Health includes episode count."""
        resp = await client.get("/health")
        data = await resp.json()
        assert "episode_count" in data

    @pytest.mark.asyncio
    async def test_05_health_includes_timestamp(self, client):
        """Health includes server timestamp."""
        resp = await client.get("/health")
        data = await resp.json()
        assert "timestamp" in data

    # --- 63: BRIDGE - Recording lifecycle ---

    @pytest.mark.asyncio
    async def test_06_record_episode_requires_url(self, client):
        """POST /record-episode requires url field."""
        resp = await client.post("/record-episode", json={})
        assert resp.status == 400
        data = await resp.json()
        assert "url" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_07_record_episode_starts_recording(self, client):
        """POST /record-episode starts recording and returns episode_id."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED", "session_id": "s1"}):
            resp = await client.post("/record-episode", json={"url": "https://reddit.com"})
            assert resp.status == 200
            data = await resp.json()
            assert "episode_id" in data
            assert data["recording"] is True

    @pytest.mark.asyncio
    async def test_08_record_episode_extracts_domain(self, client):
        """Recording extracts domain from URL."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED"}):
            resp = await client.post("/record-episode", json={"url": "https://www.reddit.com/r/test"})
            data = await resp.json()
            assert data.get("domain") == "www.reddit.com"

    @pytest.mark.asyncio
    async def test_09_stop_recording_returns_episode(self, client):
        """POST /stop-recording returns episode summary."""
        bridge.is_recording = True
        bridge.current_episode_id = "ep_test_001"
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STOPPED", "episode": {"actions": [1,2,3]}}):
            resp = await client.post("/stop-recording")
            assert resp.status == 200
            data = await resp.json()
            assert data["episode_id"] == "ep_test_001"
            assert data["action_count"] == 3

    @pytest.mark.asyncio
    async def test_10_stop_recording_clears_state(self, client):
        """Stop recording clears bridge recording state."""
        bridge.is_recording = True
        bridge.current_episode_id = "ep_test_001"
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STOPPED", "episode": {"actions": []}}):
            await client.post("/stop-recording")
            assert bridge.is_recording is False
            assert bridge.current_episode_id is None

    # --- 91: STABILITY - Episode CRUD ---

    @pytest.mark.asyncio
    async def test_11_list_episodes_empty(self, client, tmp_episode_dir):
        """GET /list-episodes returns empty list when no episodes."""
        # Clear any files
        for f in tmp_episode_dir.glob("*.json"):
            f.unlink()
        resp = await client.get("/list-episodes")
        assert resp.status == 200
        data = await resp.json()
        assert data["episodes"] == []

    @pytest.mark.asyncio
    async def test_12_list_episodes_with_data(self, client, sample_episodes):
        """GET /list-episodes returns all episodes."""
        resp = await client.get("/list-episodes")
        data = await resp.json()
        assert len(data["episodes"]) == 5

    @pytest.mark.asyncio
    async def test_13_get_episode_by_id(self, client, sample_episode):
        """GET /episode/{id} returns episode details."""
        resp = await client.get("/episode/ep_20260214_001")
        assert resp.status == 200
        data = await resp.json()
        assert data["domain"] == "reddit.com"

    @pytest.mark.asyncio
    async def test_14_get_episode_not_found(self, client, tmp_episode_dir):
        """GET /episode/{id} returns 404 for missing episode."""
        resp = await client.get("/episode/nonexistent")
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_15_export_episode(self, client, sample_episode, tmp_episode_dir):
        """POST /export-episode exports episode file."""
        resp = await client.post("/export-episode", json={"episode_id": "ep_20260214_001"})
        assert resp.status == 200
        data = await resp.json()
        assert "file" in data
        assert "size" in data
        assert data["size"] > 0

    @pytest.mark.asyncio
    async def test_16_export_episode_not_found(self, client, tmp_episode_dir):
        """POST /export-episode returns 404 for missing episode."""
        resp = await client.post("/export-episode", json={"episode_id": "nonexistent"})
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_17_play_recipe_requires_episode_id(self, client):
        """POST /play-recipe requires episode_id."""
        resp = await client.post("/play-recipe", json={})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_18_play_recipe_not_found(self, client, tmp_episode_dir):
        """POST /play-recipe returns 404 for missing episode."""
        resp = await client.post("/play-recipe", json={"episode_id": "nonexistent"})
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_19_play_recipe_executes_actions(self, client, sample_episode):
        """POST /play-recipe replays all actions."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "NAVIGATION_COMPLETE"}):
            resp = await client.post("/play-recipe", json={"episode_id": "ep_20260214_001"})
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert data["actions_executed"] == 3

    @pytest.mark.asyncio
    async def test_20_get_snapshot_sends_ws_command(self, client):
        """POST /get-snapshot sends SNAPSHOT command via WS."""
        snapshot_data = {"metadata": {"title": "Test Page"}, "a11y_tree": []}
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SNAPSHOT_TAKEN", "snapshot": snapshot_data}):
            resp = await client.post("/get-snapshot")
            assert resp.status == 200
            data = await resp.json()
            assert data["metadata"]["title"] == "Test Page"

    @pytest.mark.asyncio
    async def test_21_verify_interaction_requires_ref_id(self, client):
        """POST /verify-interaction requires ref_id."""
        resp = await client.post("/verify-interaction", json={})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_22_verify_interaction_match(self, client):
        """POST /verify-interaction returns match result."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SCRIPT_EXECUTED", "result": {"result": {"found": True, "value": "hello", "tag": "INPUT", "visible": True}}}):
            resp = await client.post("/verify-interaction", json={"ref_id": "test_input", "expected": "hello"})
            assert resp.status == 200
            data = await resp.json()
            assert data["matches"] is True

    @pytest.mark.asyncio
    async def test_23_verify_interaction_mismatch(self, client):
        """POST /verify-interaction detects mismatch."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SCRIPT_EXECUTED", "result": {"result": {"found": True, "value": "wrong", "tag": "INPUT", "visible": True}}}):
            resp = await client.post("/verify-interaction", json={"ref_id": "test_input", "expected": "hello"})
            data = await resp.json()
            assert data["matches"] is False

    @pytest.mark.asyncio
    async def test_24_episode_list_has_correct_fields(self, client, sample_episode):
        """Episode list entries contain required fields."""
        resp = await client.get("/list-episodes")
        data = await resp.json()
        ep = data["episodes"][0]
        assert "episode_id" in ep
        assert "action_count" in ep
        assert "domain" in ep
        assert "created" in ep

    @pytest.mark.asyncio
    async def test_25_record_episode_returns_url(self, client):
        """Record response echoes back the URL."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED"}):
            resp = await client.post("/record-episode", json={"url": "https://example.com"})
            data = await resp.json()
            assert data["url"] == "https://example.com"


# ============================================================
# SECTION 2: 641 Edge Tests (25) - Edge Cases
# ============================================================

class TestEdge641:
    """641: Edge case testing for API robustness."""

    @pytest.mark.asyncio
    async def test_26_record_invalid_json(self, client):
        """POST /record-episode with invalid JSON body."""
        resp = await client.post("/record-episode",
                                 data=b"not json",
                                 headers={"Content-Type": "application/json"})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_27_record_already_recording(self, client):
        """POST /record-episode when already recording returns 409."""
        bridge.is_recording = True
        bridge.current_episode_id = "ep_existing"
        resp = await client.post("/record-episode", json={"url": "https://example.com"})
        assert resp.status == 409

    @pytest.mark.asyncio
    async def test_28_stop_not_recording(self, client):
        """POST /stop-recording when not recording returns 409."""
        bridge.is_recording = False
        resp = await client.post("/stop-recording")
        assert resp.status == 409

    @pytest.mark.asyncio
    async def test_29_play_recipe_invalid_json(self, client):
        """POST /play-recipe with invalid JSON."""
        resp = await client.post("/play-recipe",
                                 data=b"bad",
                                 headers={"Content-Type": "application/json"})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_30_export_invalid_json(self, client):
        """POST /export-episode with invalid JSON."""
        resp = await client.post("/export-episode",
                                 data=b"bad",
                                 headers={"Content-Type": "application/json"})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_31_export_missing_episode_id(self, client):
        """POST /export-episode without episode_id."""
        resp = await client.post("/export-episode", json={})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_32_verify_invalid_json(self, client):
        """POST /verify-interaction with invalid JSON."""
        resp = await client.post("/verify-interaction",
                                 data=b"bad",
                                 headers={"Content-Type": "application/json"})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_33_verify_element_not_found(self, client):
        """Verify interaction when element doesn't exist."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SCRIPT_EXECUTED", "result": {"result": {"found": False}}}):
            resp = await client.post("/verify-interaction", json={"ref_id": "nonexistent"})
            data = await resp.json()
            assert data["matches"] is False
            assert "not found" in data.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_34_snapshot_no_extension(self, client):
        """Snapshot when extension not connected returns 503."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value=None):
            resp = await client.post("/get-snapshot")
            assert resp.status == 503

    @pytest.mark.asyncio
    async def test_35_snapshot_extension_error(self, client):
        """Snapshot when extension returns error."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "ERROR", "error": "Tab not found"}):
            resp = await client.post("/get-snapshot")
            assert resp.status == 500

    @pytest.mark.asyncio
    async def test_36_record_url_without_protocol(self, client):
        """Record with URL missing protocol adds https://."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED"}):
            resp = await client.post("/record-episode", json={"url": "reddit.com"})
            data = await resp.json()
            assert data["domain"] == "reddit.com"

    @pytest.mark.asyncio
    async def test_37_get_episode_special_chars_in_id(self, client, tmp_episode_dir):
        """Episode ID with special characters handled safely."""
        resp = await client.get("/episode/../../etc/passwd")
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_38_play_recipe_with_failed_action(self, client, sample_episode):
        """Play recipe reports partial failure."""
        call_count = 0
        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return {"type": "ERROR", "error": "Element not found"}
            return {"type": "NAVIGATION_COMPLETE"}
        with patch.object(bridge, "send_and_wait", side_effect=mock_send):
            resp = await client.post("/play-recipe", json={"episode_id": "ep_20260214_001"})
            data = await resp.json()
            assert data["actions_executed"] < data["actions_total"]

    @pytest.mark.asyncio
    async def test_39_record_empty_url(self, client):
        """Record with empty string URL returns 400."""
        resp = await client.post("/record-episode", json={"url": ""})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_40_verify_no_expected_value(self, client):
        """Verify without expected value checks only existence."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SCRIPT_EXECUTED", "result": {"result": {"found": True, "value": "anything", "tag": "DIV", "visible": True}}}):
            resp = await client.post("/verify-interaction", json={"ref_id": "test_el"})
            data = await resp.json()
            assert data["matches"] is True

    @pytest.mark.asyncio
    async def test_41_unknown_route_returns_404(self, client):
        """Unknown routes return 404."""
        resp = await client.get("/nonexistent-endpoint")
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_42_record_ws_failure_fallback(self, client):
        """Recording falls back gracefully when WS fails."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value=None):
            resp = await client.post("/record-episode", json={"url": "https://example.com"})
            assert resp.status == 200
            data = await resp.json()
            assert "note" in data

    @pytest.mark.asyncio
    async def test_43_stop_ws_failure_graceful(self, client):
        """Stop recording is graceful when WS fails."""
        bridge.is_recording = True
        bridge.current_episode_id = "ep_test"
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value=None):
            resp = await client.post("/stop-recording")
            assert resp.status == 200
            assert bridge.is_recording is False

    @pytest.mark.asyncio
    async def test_44_verify_ws_no_response(self, client):
        """Verify returns 503 when WS has no response."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value=None):
            resp = await client.post("/verify-interaction", json={"ref_id": "test"})
            assert resp.status == 503

    @pytest.mark.asyncio
    async def test_45_list_episodes_with_corrupt_file(self, client, tmp_episode_dir):
        """List episodes skips corrupt JSON files."""
        corrupt = tmp_episode_dir / "episode_corrupt.json"
        corrupt.write_text("not valid json {{{")
        valid = tmp_episode_dir / "episode_valid.json"
        valid.write_text(json.dumps({"episode_id": "valid", "actions": []}))

        resp = await client.get("/list-episodes")
        data = await resp.json()
        assert len(data["episodes"]) == 1

    @pytest.mark.asyncio
    async def test_46_double_stop_recording(self, client):
        """Double stop returns 409 on second call."""
        bridge.is_recording = True
        bridge.current_episode_id = "ep_test"
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STOPPED", "episode": {"actions": []}}):
            resp1 = await client.post("/stop-recording")
            assert resp1.status == 200
        resp2 = await client.post("/stop-recording")
        assert resp2.status == 409

    @pytest.mark.asyncio
    async def test_47_play_recipe_empty_actions(self, client, tmp_episode_dir):
        """Play recipe with zero actions succeeds."""
        ep = {"episode_id": "ep_empty", "actions": []}
        filepath = tmp_episode_dir / "episode_ep_empty.json"
        with open(filepath, "w") as f:
            json.dump(ep, f)
        resp = await client.post("/play-recipe", json={"episode_id": "ep_empty"})
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["actions_executed"] == 0

    @pytest.mark.asyncio
    async def test_48_episode_id_format(self, client):
        """Generated episode IDs follow naming convention."""
        eid = generate_episode_id()
        assert eid.startswith("ep_")
        parts = eid.split("_")
        assert len(parts) == 3

    @pytest.mark.asyncio
    async def test_49_concurrent_record_rejected(self, client):
        """Concurrent record attempts rejected with 409."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED"}):
            resp1 = await client.post("/record-episode", json={"url": "https://a.com"})
            assert resp1.status == 200
        resp2 = await client.post("/record-episode", json={"url": "https://b.com"})
        assert resp2.status == 409

    @pytest.mark.asyncio
    async def test_50_export_episode_creates_file(self, client, sample_episode, tmp_episode_dir):
        """Export creates a physical file on disk."""
        resp = await client.post("/export-episode", json={"episode_id": "ep_20260214_001"})
        data = await resp.json()
        assert Path(data["path"]).exists()


# ============================================================
# SECTION 3: 274177 Stress Tests (13) - Performance
# ============================================================

class TestStress274177:
    """274177: Stress and performance testing."""

    @pytest.mark.asyncio
    async def test_51_list_many_episodes(self, client, tmp_episode_dir):
        """List works with 100 episodes."""
        for i in range(100):
            ep = {"episode_id": f"ep_stress_{i:04d}", "actions": [{"type": "click"}] * 10}
            filepath = tmp_episode_dir / f"episode_ep_stress_{i:04d}.json"
            with open(filepath, "w") as f:
                json.dump(ep, f)
        resp = await client.get("/list-episodes")
        data = await resp.json()
        assert len(data["episodes"]) == 100

    @pytest.mark.asyncio
    async def test_52_rapid_health_checks(self, client):
        """Health endpoint handles rapid sequential requests."""
        for _ in range(50):
            resp = await client.get("/health")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_53_large_episode_load(self, client, tmp_episode_dir):
        """Load episode with many actions."""
        actions = [{"type": "click", "data": {"selector": f"#btn_{i}"}, "step": i}
                   for i in range(1000)]
        ep = {"episode_id": "ep_large", "actions": actions, "action_count": 1000}
        filepath = tmp_episode_dir / "episode_ep_large.json"
        with open(filepath, "w") as f:
            json.dump(ep, f)
        resp = await client.get("/episode/ep_large")
        assert resp.status == 200
        data = await resp.json()
        assert data["action_count"] == 1000

    @pytest.mark.asyncio
    async def test_54_export_large_episode(self, client, tmp_episode_dir):
        """Export large episode to file."""
        actions = [{"type": "type", "data": {"text": "x" * 1000}, "step": i}
                   for i in range(500)]
        ep = {"episode_id": "ep_big", "actions": actions}
        filepath = tmp_episode_dir / "episode_ep_big.json"
        with open(filepath, "w") as f:
            json.dump(ep, f)
        resp = await client.post("/export-episode", json={"episode_id": "ep_big"})
        data = await resp.json()
        assert data["size"] > 0

    @pytest.mark.asyncio
    async def test_55_sequential_record_stop_cycles(self, client):
        """Multiple record/stop cycles work correctly."""
        for i in range(10):
            bridge.is_recording = False
            bridge.current_episode_id = None
            with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                             return_value={"type": "RECORDING_STARTED"}):
                resp = await client.post("/record-episode", json={"url": f"https://site{i}.com"})
                assert resp.status == 200

            with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                             return_value={"type": "RECORDING_STOPPED", "episode": {"actions": []}}):
                resp = await client.post("/stop-recording")
                assert resp.status == 200

    @pytest.mark.asyncio
    async def test_56_concurrent_list_requests(self, client, sample_episodes):
        """Multiple concurrent list requests all succeed."""
        tasks = [client.get("/list-episodes") for _ in range(20)]
        responses = await asyncio.gather(*tasks)
        for resp in responses:
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_57_concurrent_health_requests(self, client):
        """Multiple concurrent health requests all succeed."""
        tasks = [client.get("/health") for _ in range(20)]
        responses = await asyncio.gather(*tasks)
        for resp in responses:
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_58_get_many_episodes_sequentially(self, client, sample_episodes):
        """Retrieve all 5 episodes sequentially."""
        for i in range(5):
            resp = await client.get(f"/episode/ep_20260214_{i+1:03d}")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_59_play_recipe_many_actions(self, client, tmp_episode_dir):
        """Replay episode with 50 actions."""
        actions = [{"type": "click", "data": {"selector": f"#btn_{i}"}, "step": i}
                   for i in range(50)]
        ep = {"episode_id": "ep_50", "actions": actions}
        filepath = tmp_episode_dir / "episode_ep_50.json"
        with open(filepath, "w") as f:
            json.dump(ep, f)
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "CLICK_COMPLETE"}):
            resp = await client.post("/play-recipe", json={"episode_id": "ep_50"})
            data = await resp.json()
            assert data["actions_executed"] == 50

    @pytest.mark.asyncio
    async def test_60_rapid_snapshot_requests(self, client):
        """Multiple rapid snapshot requests handled."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SNAPSHOT_TAKEN", "snapshot": {"metadata": {"title": "Test"}}}):
            for _ in range(10):
                resp = await client.post("/get-snapshot")
                assert resp.status == 200

    @pytest.mark.asyncio
    async def test_61_rapid_verify_requests(self, client):
        """Multiple rapid verify requests handled."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SCRIPT_EXECUTED", "result": {"result": {"found": True, "value": "ok", "tag": "SPAN", "visible": True}}}):
            for _ in range(10):
                resp = await client.post("/verify-interaction", json={"ref_id": "test", "expected": "ok"})
                assert resp.status == 200

    @pytest.mark.asyncio
    async def test_62_episode_dir_with_many_files(self, client, tmp_episode_dir):
        """Listing is robust with mixed file types in dir."""
        # Add some non-episode files
        for i in range(20):
            (tmp_episode_dir / f"other_{i}.txt").write_text("not an episode")
        # Add real episodes
        for i in range(10):
            ep = {"episode_id": f"ep_mixed_{i}", "actions": []}
            (tmp_episode_dir / f"episode_ep_mixed_{i}.json").write_text(json.dumps(ep))

        resp = await client.get("/list-episodes")
        data = await resp.json()
        assert len(data["episodes"]) == 10

    @pytest.mark.asyncio
    async def test_63_bridge_state_thread_safety(self, client):
        """Bridge state transitions are consistent under concurrent access."""
        bridge.is_recording = False
        bridge.current_episode_id = None

        # Record then stop, verify state is clean
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED"}):
            await client.post("/record-episode", json={"url": "https://test.com"})
        assert bridge.is_recording is True

        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STOPPED", "episode": {"actions": []}}):
            await client.post("/stop-recording")
        assert bridge.is_recording is False
        assert bridge.current_episode_id is None


# ============================================================
# SECTION 4: 65537 God Tests (12) - Integration
# ============================================================

class TestGod65537:
    """65537: Full integration and workflow tests."""

    @pytest.mark.asyncio
    async def test_64_full_workflow_record_list_replay(self, client, tmp_episode_dir):
        """Full workflow: record -> stop -> list -> replay."""
        # Start recording
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED"}):
            resp = await client.post("/record-episode", json={"url": "https://example.com"})
            assert resp.status == 200
            episode_id = (await resp.json())["episode_id"]

        # Stop recording - save episode to disk for list/replay
        ep_data = {
            "episode_id": episode_id,
            "actions": [{"type": "navigate", "data": {"url": "https://example.com"}, "step": 0}],
            "action_count": 1,
            "domain": "example.com",
            "start_time": datetime.now().isoformat(),
        }
        filepath = tmp_episode_dir / f"episode_{episode_id}.json"
        with open(filepath, "w") as f:
            json.dump(ep_data, f)

        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STOPPED", "episode": ep_data}):
            resp = await client.post("/stop-recording")
            assert resp.status == 200

        # List episodes
        resp = await client.get("/list-episodes")
        data = await resp.json()
        ids = [ep["episode_id"] for ep in data["episodes"]]
        assert episode_id in ids

        # Replay
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "NAVIGATION_COMPLETE"}):
            resp = await client.post("/play-recipe", json={"episode_id": episode_id})
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_65_full_workflow_record_export(self, client, tmp_episode_dir):
        """Full workflow: record -> stop -> export."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED"}):
            resp = await client.post("/record-episode", json={"url": "https://github.com"})
            episode_id = (await resp.json())["episode_id"]

        # Write episode to disk
        ep_data = {"episode_id": episode_id, "actions": [], "domain": "github.com"}
        (tmp_episode_dir / f"episode_{episode_id}.json").write_text(json.dumps(ep_data))

        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STOPPED", "episode": ep_data}):
            await client.post("/stop-recording")

        # Export
        resp = await client.post("/export-episode", json={"episode_id": episode_id})
        assert resp.status == 200
        data = await resp.json()
        assert data["size"] > 0

    @pytest.mark.asyncio
    async def test_66_snapshot_and_verify_workflow(self, client):
        """Workflow: snapshot then verify element."""
        # Snapshot
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SNAPSHOT_TAKEN", "snapshot": {"metadata": {"title": "Login Page"}}}):
            resp = await client.post("/get-snapshot")
            assert resp.status == 200

        # Verify
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "SCRIPT_EXECUTED", "result": {"result": {"found": True, "value": "Submit", "tag": "BUTTON", "visible": True}}}):
            resp = await client.post("/verify-interaction", json={"ref_id": "submit_btn", "expected": "Submit"})
            data = await resp.json()
            assert data["matches"] is True

    @pytest.mark.asyncio
    async def test_67_error_recovery_after_ws_failure(self, client):
        """System recovers after WebSocket failure."""
        # Snapshot fails
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value=None):
            resp = await client.post("/get-snapshot")
            assert resp.status == 503

        # Health still works
        resp = await client.get("/health")
        assert resp.status == 200

        # Recording still works
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "RECORDING_STARTED"}):
            resp = await client.post("/record-episode", json={"url": "https://test.com"})
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_68_play_recipe_mixed_action_types(self, client, tmp_episode_dir):
        """Replay handles all action types (navigate, click, type, snapshot)."""
        ep = {
            "episode_id": "ep_mixed",
            "actions": [
                {"type": "navigate", "data": {"url": "https://example.com"}, "step": 0},
                {"type": "click", "data": {"selector": "#btn"}, "step": 1},
                {"type": "type", "data": {"selector": "#input", "text": "hello"}, "step": 2},
                {"type": "snapshot", "data": {}, "step": 3},
            ],
        }
        (tmp_episode_dir / "episode_ep_mixed.json").write_text(json.dumps(ep))

        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "NAVIGATION_COMPLETE"}):
            resp = await client.post("/play-recipe", json={"episode_id": "ep_mixed"})
            data = await resp.json()
            assert data["actions_executed"] == 4

    @pytest.mark.asyncio
    async def test_69_episode_get_by_session_id(self, client, sample_episode):
        """Can retrieve episode by session_id (backward compat)."""
        resp = await client.get("/episode/session_123")
        assert resp.status == 200
        data = await resp.json()
        assert data["session_id"] == "session_123"

    @pytest.mark.asyncio
    async def test_70_record_with_ws_error_response(self, client):
        """Record handles WS error response gracefully."""
        with patch.object(bridge, "send_and_wait", new_callable=AsyncMock,
                         return_value={"type": "ERROR", "error": "Tab not available"}):
            resp = await client.post("/record-episode", json={"url": "https://test.com"})
            assert resp.status == 500

    @pytest.mark.asyncio
    async def test_71_health_reflects_recording_state(self, client):
        """Health endpoint accurately reflects recording state."""
        # Not recording
        resp = await client.get("/health")
        data = await resp.json()
        assert data["is_recording"] is False

        # Start recording
        bridge.is_recording = True
        bridge.current_episode_id = "ep_active"
        resp = await client.get("/health")
        data = await resp.json()
        assert data["is_recording"] is True
        assert data["current_episode"] == "ep_active"

    @pytest.mark.asyncio
    async def test_72_app_has_all_routes(self, client):
        """Application has all 9 required routes."""
        app = client.app
        routes = [r.resource.canonical for r in app.router.routes() if hasattr(r, 'resource')]
        expected = [
            "/health",
            "/record-episode",
            "/stop-recording",
            "/play-recipe",
            "/list-episodes",
            "/episode/{episode_id}",
            "/export-episode",
            "/get-snapshot",
            "/verify-interaction",
        ]
        for route in expected:
            assert route in routes, f"Missing route: {route}"

    @pytest.mark.asyncio
    async def test_73_bridge_state_isolation(self, client):
        """BridgeState maintains clean isolation between operations."""
        state = BridgeState()
        assert state.is_recording is False
        assert state.current_episode_id is None
        assert state.ws_connection is None
        assert len(state.pending_responses) == 0

    @pytest.mark.asyncio
    async def test_74_generate_episode_id_unique(self, tmp_episode_dir):
        """Generated episode IDs are unique."""
        ids = set()
        for _ in range(10):
            eid = generate_episode_id()
            ids.add(eid)
            # Create file so next call sees it
            (tmp_episode_dir / f"episode_{eid}.json").write_text("{}")
        assert len(ids) == 10

    @pytest.mark.asyncio
    async def test_75_load_episode_returns_none_for_missing(self, tmp_episode_dir):
        """load_episode returns None for non-existent episodes."""
        result = load_episode("does_not_exist")
        assert result is None
