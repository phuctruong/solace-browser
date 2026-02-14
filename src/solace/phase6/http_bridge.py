#!/usr/bin/env python3
"""
Solace Browser CLI Bridge - HTTP API Server (Phase 6)

Exposes browser control via HTTP on localhost:9999.
Bridges HTTP requests to the existing WebSocket server on localhost:9222.

Endpoints:
  POST /record-episode      Start recording
  POST /stop-recording      Stop recording
  POST /play-recipe         Replay an episode
  GET  /list-episodes       List recorded episodes
  GET  /episode/{id}        Get episode details
  POST /export-episode      Export episode as JSON
  POST /get-snapshot        Get current page snapshot
  POST /verify-interaction  Verify element state

Architecture:
  HTTP client (curl/bash) -> HTTP API (port 9999) -> WebSocket (port 9222) -> Chrome extension

Auth: 65537
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from aiohttp import web

logger = logging.getLogger(__name__)

# Configuration
HTTP_HOST = "127.0.0.1"
HTTP_PORT = 9999
WS_HOST = "localhost"
WS_PORT = 9222
EPISODE_DIR = Path.home() / ".solace" / "browser"
REQUEST_TIMEOUT = 30  # seconds

# Ensure episode directory exists
EPISODE_DIR.mkdir(parents=True, exist_ok=True)


class BridgeState:
    """Tracks bridge-level state: recording status, connected extensions."""

    def __init__(self):
        self.is_recording = False
        self.current_episode_id: Optional[str] = None
        self.ws_connection = None
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self._ws_listener_task: Optional[asyncio.Task] = None

    async def connect_ws(self) -> bool:
        """Connect to the WebSocket server."""
        try:
            import websockets
            self.ws_connection = await websockets.connect(
                f"ws://{WS_HOST}:{WS_PORT}"
            )
            self._ws_listener_task = asyncio.create_task(self._listen_ws())
            logger.info("Connected to WebSocket server at ws://%s:%s", WS_HOST, WS_PORT)
            return True
        except Exception as e:
            logger.error("Failed to connect to WebSocket server: %s", e)
            self.ws_connection = None
            return False

    async def disconnect_ws(self):
        """Disconnect from WebSocket server."""
        if self._ws_listener_task:
            self._ws_listener_task.cancel()
            try:
                await self._ws_listener_task
            except asyncio.CancelledError:
                pass
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None

    async def _listen_ws(self):
        """Background listener for WebSocket responses."""
        try:
            async for message in self.ws_connection:
                try:
                    data = json.loads(message)
                    request_id = data.get("request_id")
                    if request_id and request_id in self.pending_responses:
                        future = self.pending_responses.pop(request_id)
                        if not future.done():
                            future.set_result(data)
                    else:
                        logger.debug("Unmatched WS message: %s", data.get("type"))
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from WebSocket")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("WebSocket listener error: %s", e)
            self.ws_connection = None

    async def send_and_wait(self, command: Dict, timeout: float = REQUEST_TIMEOUT) -> Optional[Dict]:
        """Send a command via WebSocket and wait for the response."""
        if not self.ws_connection:
            connected = await self.connect_ws()
            if not connected:
                return None

        request_id = str(uuid.uuid4())[:8]
        command["request_id"] = request_id

        future = asyncio.get_event_loop().create_future()
        self.pending_responses[request_id] = future

        try:
            await self.ws_connection.send(json.dumps(command))
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self.pending_responses.pop(request_id, None)
            logger.error("Request %s timed out after %ss", request_id, timeout)
            return None
        except Exception as e:
            self.pending_responses.pop(request_id, None)
            logger.error("Send error: %s", e)
            self.ws_connection = None
            return None


# Global bridge state
bridge = BridgeState()


# --- Utility ---

def generate_episode_id() -> str:
    """Generate a unique episode ID."""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    # Count existing episodes for today
    existing = list(EPISODE_DIR.glob(f"episode_ep_{date_str}_*.json"))
    seq = len(existing) + 1
    return f"ep_{date_str}_{seq:03d}"


def load_episode(episode_id: str) -> Optional[Dict]:
    """Load an episode from disk by ID."""
    # Try exact match first
    path = EPISODE_DIR / f"episode_{episode_id}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    # Try session_id-based files
    for filepath in EPISODE_DIR.glob("episode_*.json"):
        try:
            with open(filepath) as f:
                data = json.load(f)
            if data.get("session_id") == episode_id or data.get("episode_id") == episode_id:
                return data
        except (json.JSONDecodeError, IOError):
            continue
    return None


def list_all_episodes():
    """List all recorded episodes from disk."""
    episodes = []
    for filepath in sorted(EPISODE_DIR.glob("episode_*.json")):
        try:
            with open(filepath) as f:
                data = json.load(f)
            episodes.append({
                "episode_id": data.get("episode_id") or data.get("session_id", filepath.stem),
                "action_count": data.get("action_count", len(data.get("actions", []))),
                "domain": data.get("domain", "unknown"),
                "created": data.get("start_time", "unknown"),
                "file": filepath.name,
            })
        except (json.JSONDecodeError, IOError):
            continue
    return episodes


# --- HTTP Handlers ---

async def handle_record_episode(request: web.Request) -> web.Response:
    """POST /record-episode - Start recording."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON body"}, status=400
        )

    url = body.get("url")
    if not url:
        return web.json_response(
            {"error": "Missing required field: url"}, status=400
        )

    if bridge.is_recording:
        return web.json_response(
            {"error": "Already recording", "episode_id": bridge.current_episode_id},
            status=409,
        )

    episode_id = generate_episode_id()

    # Extract domain from URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url if "://" in url else f"https://{url}")
        domain = parsed.hostname or "unknown"
    except Exception:
        domain = "unknown"

    # Send START_RECORDING to extension via WebSocket
    result = await bridge.send_and_wait({
        "type": "START_RECORDING",
        "payload": {"domain": domain, "episode_id": episode_id},
    })

    if result and result.get("type") == "RECORDING_STARTED":
        bridge.is_recording = True
        bridge.current_episode_id = episode_id

        # Navigate to URL
        await bridge.send_and_wait({
            "type": "NAVIGATE",
            "payload": {"url": url},
        })

        return web.json_response({
            "episode_id": episode_id,
            "recording": True,
            "url": url,
            "domain": domain,
        })
    elif result and result.get("type") == "ERROR":
        return web.json_response(
            {"error": result.get("error", "Recording failed")}, status=500
        )
    else:
        # No WebSocket connection, create local-only recording state
        bridge.is_recording = True
        bridge.current_episode_id = episode_id
        return web.json_response({
            "episode_id": episode_id,
            "recording": True,
            "url": url,
            "domain": domain,
            "note": "Recording started (extension not connected)",
        })


async def handle_stop_recording(request: web.Request) -> web.Response:
    """POST /stop-recording - Stop recording and return episode."""
    if not bridge.is_recording:
        return web.json_response(
            {"error": "Not currently recording"}, status=409
        )

    episode_id = bridge.current_episode_id

    result = await bridge.send_and_wait({
        "type": "STOP_RECORDING",
        "payload": {},
    })

    bridge.is_recording = False
    bridge.current_episode_id = None

    if result and result.get("type") == "RECORDING_STOPPED":
        episode = result.get("episode", {})
        return web.json_response({
            "episode_id": episode_id,
            "action_count": len(episode.get("actions", [])),
            "url_start": episode.get("url_start", ""),
            "url_end": episode.get("url_end", ""),
        })
    else:
        return web.json_response({
            "episode_id": episode_id,
            "action_count": 0,
            "note": "Recording stopped (no episode data from extension)",
        })


async def handle_play_recipe(request: web.Request) -> web.Response:
    """POST /play-recipe - Replay a recorded episode."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON body"}, status=400
        )

    episode_id = body.get("episode_id")
    if not episode_id:
        return web.json_response(
            {"error": "Missing required field: episode_id"}, status=400
        )

    episode = load_episode(episode_id)
    if not episode:
        return web.json_response(
            {"error": f"Episode not found: {episode_id}"}, status=404
        )

    actions = episode.get("actions", [])
    executed = 0
    errors = []

    for action in actions:
        action_type = action.get("type", "")
        action_data = action.get("data", {})

        cmd = None
        if action_type == "navigate":
            cmd = {"type": "NAVIGATE", "payload": {"url": action_data.get("url")}}
        elif action_type == "click":
            cmd = {"type": "CLICK", "payload": action_data}
        elif action_type == "type":
            cmd = {"type": "TYPE", "payload": action_data}
        elif action_type == "snapshot":
            cmd = {"type": "SNAPSHOT", "payload": {}}

        if cmd:
            result = await bridge.send_and_wait(cmd)
            if result and "ERROR" not in result.get("type", ""):
                executed += 1
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response"
                errors.append({"action": action_type, "step": action.get("step"), "error": error_msg})

    success = len(errors) == 0
    response = {
        "success": success,
        "actions_executed": executed,
        "actions_total": len(actions),
        "episode_id": episode_id,
    }
    if errors:
        response["errors"] = errors

    return web.json_response(response, status=200 if success else 500)


async def handle_list_episodes(request: web.Request) -> web.Response:
    """GET /list-episodes - List all recorded episodes."""
    episodes = list_all_episodes()
    return web.json_response({"episodes": episodes})


async def handle_get_episode(request: web.Request) -> web.Response:
    """GET /episode/{episode_id} - Get episode details."""
    episode_id = request.match_info["episode_id"]
    episode = load_episode(episode_id)
    if not episode:
        return web.json_response(
            {"error": f"Episode not found: {episode_id}"}, status=404
        )
    return web.json_response(episode)


async def handle_export_episode(request: web.Request) -> web.Response:
    """POST /export-episode - Export episode as JSON file."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON body"}, status=400
        )

    episode_id = body.get("episode_id")
    if not episode_id:
        return web.json_response(
            {"error": "Missing required field: episode_id"}, status=400
        )

    episode = load_episode(episode_id)
    if not episode:
        return web.json_response(
            {"error": f"Episode not found: {episode_id}"}, status=404
        )

    filename = f"{episode_id}.json"
    export_path = EPISODE_DIR / filename
    with open(export_path, "w") as f:
        json.dump(episode, f, indent=2)

    file_size = export_path.stat().st_size

    return web.json_response({
        "file": filename,
        "path": str(export_path),
        "size": file_size,
    })


async def handle_get_snapshot(request: web.Request) -> web.Response:
    """POST /get-snapshot - Get current page snapshot."""
    result = await bridge.send_and_wait({
        "type": "SNAPSHOT",
        "payload": {},
    })

    if result and result.get("type") == "SNAPSHOT_TAKEN":
        return web.json_response(result.get("snapshot", {}))
    elif result and result.get("type") == "ERROR":
        return web.json_response(
            {"error": result.get("error", "Snapshot failed")}, status=500
        )
    else:
        return web.json_response(
            {"error": "No response from extension (is it connected?)"}, status=503
        )


async def handle_verify_interaction(request: web.Request) -> web.Response:
    """POST /verify-interaction - Verify element state after interaction."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON body"}, status=400
        )

    ref_id = body.get("ref_id")
    expected = body.get("expected")

    if not ref_id:
        return web.json_response(
            {"error": "Missing required field: ref_id"}, status=400
        )

    # Use EXECUTE_SCRIPT to check element state
    script = f"""
    (function() {{
        var el = document.querySelector('[data-ref-id="{ref_id}"]') ||
                 document.getElementById('{ref_id}');
        if (!el) return {{ found: false }};
        return {{
            found: true,
            value: el.value || el.innerText || el.textContent,
            tag: el.tagName,
            visible: el.offsetParent !== null
        }};
    }})();
    """

    result = await bridge.send_and_wait({
        "type": "EXECUTE_SCRIPT",
        "payload": {"script": script},
    })

    if result and result.get("type") == "SCRIPT_EXECUTED":
        script_result = result.get("result", {})
        if isinstance(script_result, dict) and script_result.get("result"):
            inner = script_result["result"]
        else:
            inner = script_result

        if not inner or not inner.get("found"):
            return web.json_response({
                "matches": False,
                "error": f"Element not found: {ref_id}",
                "ref_id": ref_id,
            })

        actual = inner.get("value", "")
        matches = str(actual) == str(expected) if expected is not None else True

        return web.json_response({
            "matches": matches,
            "actual": actual,
            "expected": expected,
            "ref_id": ref_id,
            "element": {
                "tag": inner.get("tag"),
                "visible": inner.get("visible"),
            },
        })
    else:
        return web.json_response(
            {"error": "Verification failed (no response from extension)"}, status=503
        )


async def handle_health(request: web.Request) -> web.Response:
    """GET /health - Health check."""
    ws_connected = bridge.ws_connection is not None
    return web.json_response({
        "status": "ok",
        "ws_connected": ws_connected,
        "is_recording": bridge.is_recording,
        "current_episode": bridge.current_episode_id,
        "episode_count": len(list_all_episodes()),
        "timestamp": datetime.now().isoformat(),
    })


# --- App Setup ---

def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_post("/record-episode", handle_record_episode)
    app.router.add_post("/stop-recording", handle_stop_recording)
    app.router.add_post("/play-recipe", handle_play_recipe)
    app.router.add_get("/list-episodes", handle_list_episodes)
    app.router.add_get("/episode/{episode_id}", handle_get_episode)
    app.router.add_post("/export-episode", handle_export_episode)
    app.router.add_post("/get-snapshot", handle_get_snapshot)
    app.router.add_post("/verify-interaction", handle_verify_interaction)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


async def on_startup(app: web.Application):
    """Connect to WebSocket server on startup."""
    logger.info("Solace Browser CLI Bridge starting on http://%s:%s", HTTP_HOST, HTTP_PORT)
    await bridge.connect_ws()


async def on_cleanup(app: web.Application):
    """Disconnect WebSocket on shutdown."""
    await bridge.disconnect_ws()
    logger.info("Solace Browser CLI Bridge stopped")


def main():
    """Entry point for CLI bridge server."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )
    app = create_app()
    web.run_app(app, host=HTTP_HOST, port=HTTP_PORT, print=None)
    logger.info("Solace Browser CLI Bridge running on http://%s:%s", HTTP_HOST, HTTP_PORT)


if __name__ == "__main__":
    main()
