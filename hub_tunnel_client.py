# Diagram: 09-tunnel-remote-control
import asyncio
import json
import urllib.error
import urllib.request

import websockets
from websockets.exceptions import ConnectionClosed, InvalidHandshake

SOLACEAGI_WS_URL = "wss://solaceagi.com/api/v1/tunnel/connect"
SOLACEAGI_RELAY_URL = "https://solaceagi.com"
RECONNECT_DELAY_SECONDS = 5
MAX_RETRIES = 3


class HubTunnelClient:
    def __init__(self, api_key: str, yinyang_bearer: str, yinyang_port: int = 8888):
        self.api_key = api_key
        self.yinyang_bearer = yinyang_bearer
        self.yinyang_port = yinyang_port
        self.retries = 0
        self.max_retries = MAX_RETRIES
        self._running = False
        self._websocket = None

    async def run(self) -> None:
        self._running = True
        while self._running and self.retries < self.max_retries:
            try:
                async with websockets.connect(
                    SOLACEAGI_WS_URL,
                    additional_headers={"Authorization": f"Bearer {self.api_key}"},
                ) as websocket:
                    self._websocket = websocket
                    while self._running:
                        raw_message = await websocket.recv()
                        message = json.loads(raw_message)
                        response = await self._handle_message(message)
                        if response is not None:
                            await websocket.send(json.dumps(response))
            except json.JSONDecodeError:
                continue
            except (ConnectionClosed, InvalidHandshake, OSError):
                self.retries += 1
                self._websocket = None
                if not self._running or self.retries >= self.max_retries:
                    break
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
        self._running = False
        self._websocket = None

    async def _handle_message(self, msg: dict) -> dict:
        if msg.get("type") == "ping":
            return {"type": "pong"}

        request_id = msg.get("id")
        method = str(msg.get("method", "GET")).upper()
        path = str(msg.get("path", "/"))
        if not path.startswith("/"):
            path = f"/{path}"

        headers = {}
        if self.yinyang_bearer:
            headers["Authorization"] = f"Bearer {self.yinyang_bearer}"

        body = msg.get("body")
        data = None
        if body is not None:
            if isinstance(body, str):
                data = body.encode()
            else:
                data = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"http://localhost:{self.yinyang_port}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return {
                    "id": request_id,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": response.read().decode(),
                }
        except urllib.error.HTTPError as exc:
            return {
                "id": request_id,
                "status": exc.code,
                "headers": dict(exc.headers),
                "body": exc.read().decode(),
            }
        except urllib.error.URLError as exc:
            return {
                "id": request_id,
                "status": 502,
                "headers": {},
                "body": str(exc.reason),
            }

    async def stop(self) -> None:
        self._running = False
        websocket = self._websocket
        self._websocket = None
        if websocket is not None:
            try:
                await websocket.close()
            except ConnectionClosed:
                pass
