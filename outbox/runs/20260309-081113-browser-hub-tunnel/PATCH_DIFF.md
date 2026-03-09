--- /dev/null
+++ b/hub_tunnel_client.py
@@
+import asyncio
+import json
+import urllib.error
+import urllib.request
+
+import websockets
+from websockets.exceptions import ConnectionClosed, InvalidHandshake
+
+SOLACEAGI_WS_URL = "wss://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/tunnel/connect"
+SOLACEAGI_RELAY_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app"
+RECONNECT_DELAY_SECONDS = 5
+MAX_RETRIES = 3
+
+
+class HubTunnelClient:
+    def __init__(self, api_key: str, yinyang_bearer: str, yinyang_port: int = 8888):
+        self.api_key = api_key
+        self.yinyang_bearer = yinyang_bearer
+        self.yinyang_port = yinyang_port
+        self.retries = 0
+        self.max_retries = MAX_RETRIES
+        self._running = False
+        self._websocket = None
+
+    async def run(self) -> None:
+        self._running = True
+        while self._running and self.retries < self.max_retries:
+            try:
+                async with websockets.connect(
+                    SOLACEAGI_WS_URL,
+                    extra_headers={"Authorization": f"Bearer {self.api_key}"},
+                ) as websocket:
+                    self._websocket = websocket
+                    while self._running:
+                        raw_message = await websocket.recv()
+                        message = json.loads(raw_message)
+                        response = await self._handle_message(message)
+                        if response is not None:
+                            await websocket.send(json.dumps(response))
+            except json.JSONDecodeError:
+                continue
+            except (ConnectionClosed, InvalidHandshake, OSError):
+                self.retries += 1
+                self._websocket = None
+                if not self._running or self.retries >= self.max_retries:
+                    break
+                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
+        self._running = False
+        self._websocket = None
+
+    async def _handle_message(self, msg: dict) -> dict:
+        if msg.get("type") == "ping":
+            return {"type": "pong"}
+
+        request_id = msg.get("id")
+        method = str(msg.get("method", "GET")).upper()
+        path = str(msg.get("path", "/"))
+        if not path.startswith("/"):
+            path = f"/{path}"
+
+        headers = {}
+        if self.yinyang_bearer:
+            headers["Authorization"] = f"Bearer {self.yinyang_bearer}"
+
+        body = msg.get("body")
+        data = None
+        if body is not None:
+            if isinstance(body, str):
+                data = body.encode()
+            else:
+                data = json.dumps(body).encode()
+                headers["Content-Type"] = "application/json"
+
+        request = urllib.request.Request(
+            f"http://localhost:{self.yinyang_port}{path}",
+            data=data,
+            headers=headers,
+            method=method,
+        )
+
+        try:
+            with urllib.request.urlopen(request, timeout=5) as response:
+                return {
+                    "id": request_id,
+                    "status": response.status,
+                    "headers": dict(response.headers),
+                    "body": response.read().decode(),
+                }
+        except urllib.error.HTTPError as exc:
+            return {
+                "id": request_id,
+                "status": exc.code,
+                "headers": dict(exc.headers),
+                "body": exc.read().decode(),
+            }
+        except urllib.error.URLError as exc:
+            return {
+                "id": request_id,
+                "status": 502,
+                "headers": {},
+                "body": str(exc.reason),
+            }
+
+    async def stop(self) -> None:
+        self._running = False
+        websocket = self._websocket
+        self._websocket = None
+        if websocket is not None:
+            try:
+                await websocket.close()
+            except ConnectionClosed:
+                pass

--- /dev/null
+++ b/requirements.txt
@@
+websockets>=12.0

--- a/yinyang_server.py
+++ b/yinyang_server.py
@@
-import argparse
+import argparse
+import asyncio
@@
-from pathlib import Path
-from typing import Optional
+from pathlib import Path
+from typing import Optional
+
+from hub_tunnel_client import HubTunnelClient, SOLACEAGI_RELAY_URL
@@
-OAUTH3_TOKENS_PATH: Path = Path.home() / ".solace" / "oauth3-tokens.json"
-ONBOARDING_PATH: Path = Path.home() / ".solace" / "onboarding.json"
+OAUTH3_TOKENS_PATH: Path = Path.home() / ".solace" / "oauth3-tokens.json"
+ONBOARDING_PATH: Path = Path.home() / ".solace" / "onboarding.json"
+SETTINGS_PATH: Path = Path.home() / ".solace" / "settings.json"
@@
 _TUNNEL_PROC: Optional[subprocess.Popen] = None
 _TUNNEL_LOCK = threading.Lock()
 _TUNNEL_URL: str = ""
+_CLOUD_TUNNEL_THREAD: threading.Thread | None = None
+_CLOUD_TUNNEL_CLIENT: Optional[HubTunnelClient] = None
+_CLOUD_TUNNEL_ACTIVE: bool = False
+_CLOUD_TUNNEL_LOOP: Optional[asyncio.AbstractEventLoop] = None
+_CLOUD_TUNNEL_LOCK = threading.Lock()
@@
 def record_evidence(event_type: str, data: dict) -> dict:
@@
     with EVIDENCE_PATH.open("a") as fh:
         fh.write(json.dumps(record) + "\n")
     return record
+
+
+def _load_cloud_api_key() -> str:
+    try:
+        settings = json.loads(SETTINGS_PATH.read_text())
+    except FileNotFoundError:
+        return ""
+    except json.JSONDecodeError:
+        return ""
+    except OSError:
+        return ""
+    if not isinstance(settings, dict):
+        return ""
+    account = settings.get("account", {})
+    if not isinstance(account, dict):
+        return ""
+    api_key = account.get("api_key", "")
+    return api_key if isinstance(api_key, str) else ""
+
+
+def _cloud_tunnel_worker(api_key: str, yinyang_bearer: str, yinyang_port: int) -> None:
+    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_CLIENT, _CLOUD_TUNNEL_LOOP
+    loop = asyncio.new_event_loop()
+    client = HubTunnelClient(api_key, yinyang_bearer, yinyang_port=yinyang_port)
+    with _CLOUD_TUNNEL_LOCK:
+        _CLOUD_TUNNEL_CLIENT = client
+        _CLOUD_TUNNEL_LOOP = loop
+        _CLOUD_TUNNEL_ACTIVE = True
+    asyncio.set_event_loop(loop)
+    try:
+        loop.run_until_complete(client.run())
+    finally:
+        with _CLOUD_TUNNEL_LOCK:
+            _CLOUD_TUNNEL_ACTIVE = False
+            _CLOUD_TUNNEL_LOOP = None
+        loop.close()
+
+
+def _launch_cloud_tunnel(api_key: str, yinyang_bearer: str, yinyang_port: int) -> None:
+    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_THREAD
+    with _CLOUD_TUNNEL_LOCK:
+        if _CLOUD_TUNNEL_THREAD is not None and _CLOUD_TUNNEL_THREAD.is_alive() and _CLOUD_TUNNEL_ACTIVE:
+            return
+        _CLOUD_TUNNEL_ACTIVE = True
+        _CLOUD_TUNNEL_THREAD = threading.Thread(
+            target=_cloud_tunnel_worker,
+            args=(api_key, yinyang_bearer, yinyang_port),
+            daemon=True,
+        )
+        thread = _CLOUD_TUNNEL_THREAD
+    thread.start()
+
+
+def _stop_cloud_tunnel() -> None:
+    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_CLIENT, _CLOUD_TUNNEL_LOOP, _CLOUD_TUNNEL_THREAD
+    with _CLOUD_TUNNEL_LOCK:
+        client = _CLOUD_TUNNEL_CLIENT
+        loop = _CLOUD_TUNNEL_LOOP
+        thread = _CLOUD_TUNNEL_THREAD
+        _CLOUD_TUNNEL_ACTIVE = False
+    if client is not None and loop is not None and loop.is_running():
+        asyncio.run_coroutine_threadsafe(client.stop(), loop)
+    if thread is not None and thread.is_alive():
+        thread.join(timeout=2)
+    with _CLOUD_TUNNEL_LOCK:
+        _CLOUD_TUNNEL_THREAD = None
+        _CLOUD_TUNNEL_LOOP = None
+
+
+def _cloud_tunnel_status_payload() -> dict:
+    with _CLOUD_TUNNEL_LOCK:
+        retries = _CLOUD_TUNNEL_CLIENT.retries if _CLOUD_TUNNEL_CLIENT is not None else 0
+        active = _CLOUD_TUNNEL_ACTIVE
+    return {
+        "active": active,
+        "relay": SOLACEAGI_RELAY_URL if active else None,
+        "retries": retries,
+    }
@@
         elif path == "/api/v1/tunnel/status":
             self._handle_tunnel_status()
+        elif path == "/api/v1/tunnel/cloud-status":
+            self._handle_tunnel_cloud_status()
         elif path == "/api/v1/sync/status":
             self._handle_sync_status()
@@
         elif path == "/api/v1/tunnel/start":
             self._handle_tunnel_start()
+        elif path == "/api/v1/tunnel/start-cloud":
+            self._handle_tunnel_start_cloud()
         elif path == "/api/v1/tunnel/stop":
             self._handle_tunnel_stop()
+        elif path == "/api/v1/tunnel/stop-cloud":
+            self._handle_tunnel_stop_cloud()
         elif path == "/api/v1/sync/export":
             self._handle_sync_export()
@@
     def _handle_tunnel_status(self) -> None:
         global _TUNNEL_URL
         with _TUNNEL_LOCK:
             active = _TUNNEL_PROC is not None and _TUNNEL_PROC.poll() is None
             url = _TUNNEL_URL if active else ""
         self._send_json({"active": active, "url": url, "port": YINYANG_PORT})
+
+    def _handle_tunnel_cloud_status(self) -> None:
+        if not self._check_auth():
+            return
+        self._send_json(_cloud_tunnel_status_payload())
+
+    def _handle_tunnel_start_cloud(self) -> None:
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        api_key = body.get("api_key", "") if isinstance(body, dict) else ""
+        if not isinstance(api_key, str) or not api_key:
+            api_key = _load_cloud_api_key()
+        if not api_key:
+            self._send_json({"error": "api_key required"}, 400)
+            return
+        _launch_cloud_tunnel(api_key, getattr(self.server, "session_token_sha256", ""), self.server.server_port)
+        record_evidence("cloud_tunnel_start", {"relay": SOLACEAGI_RELAY_URL})
+        self._send_json({"status": "connecting", "relay": SOLACEAGI_RELAY_URL})
+
+    def _handle_tunnel_stop_cloud(self) -> None:
+        if not self._check_auth():
+            return
+        _stop_cloud_tunnel()
+        record_evidence("cloud_tunnel_stop", {"relay": SOLACEAGI_RELAY_URL})
+        self._send_json({"status": "stopped"})

--- /dev/null
+++ b/tests/test_hub_tunnel_client.py
@@
+import asyncio
+import importlib
+import json
+import pathlib
+import sys
+
+import pytest
+from websockets.exceptions import ConnectionClosedOK
+
+REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
+sys.path.insert(0, str(REPO_ROOT))
+
+TEST_PORT = 18888
+SERVER_PORT = TEST_PORT + 1
+VALID_TOKEN = "a" * 64
+RELAY_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app"
+def load_hub_tunnel_client():
+    return importlib.import_module("hub_tunnel_client")
+class FakeResponse:
+    def __init__(self, status: int, body: str, headers: dict | None = None):
+        self.status = status
+        self._body = body.encode()
+        self.headers = headers or {"Content-Type": "application/json"}
+
+    def read(self) -> bytes:
+        return self._body
+
+    def __enter__(self):
+        return self
+
+    def __exit__(self, exc_type, exc, tb):
+        return False
+class FakeWebSocket:
+    def __init__(self, messages: list[object], close_exc):
+        self._messages = list(messages)
+        self._close_exc = close_exc
+        self.sent: list[dict] = []
+        self.closed = False
+
+    async def recv(self) -> str:
+        if self._messages:
+            return json.dumps(self._messages.pop(0))
+        raise self._close_exc
+
+    async def send(self, payload: str) -> None:
+        self.sent.append(json.loads(payload))
+
+    async def close(self) -> None:
+        self.closed = True
+class FakeConnect:
+    def __init__(self, websocket=None, error: BaseException | None = None):
+        self._websocket = websocket
+        self._error = error
+
+    async def __aenter__(self):
+        if self._error is not None:
+            raise self._error
+        return self._websocket
+
+    async def __aexit__(self, exc_type, exc, tb):
+        return False
+def load_yinyang_server():
+    return importlib.import_module("yinyang_server")
+@pytest.fixture
+def cloud_server(monkeypatch, tmp_path):
+    load_hub_tunnel_client()
+    ys = load_yinyang_server()
+    monkeypatch.setattr(ys, "SETTINGS_PATH", tmp_path / "settings.json")
+    monkeypatch.setattr(ys, "EVIDENCE_PATH", tmp_path / "evidence.jsonl")
+    monkeypatch.setattr(ys, "record_evidence", lambda *args, **kwargs: {})
+    ys._CLOUD_TUNNEL_THREAD = None
+    ys._CLOUD_TUNNEL_CLIENT = None
+    ys._CLOUD_TUNNEL_ACTIVE = False
+    ys._CLOUD_TUNNEL_LOOP = None
+    return ys
+def make_handler(ys, body: dict | None = None):
+    handler = object.__new__(ys.YinyangHandler)
+    captured: dict = {"status": None, "data": None}
+    handler.server = type("DummyServer", (), {"session_token_sha256": VALID_TOKEN, "server_port": SERVER_PORT})()
+    handler._check_auth = lambda: True
+    handler._read_json_body = lambda: body
+    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
+    return handler, captured
+@pytest.mark.asyncio
+async def test_client_sends_pong_on_ping(monkeypatch):
+    hub = load_hub_tunnel_client()
+    close_exc = ConnectionClosedOK(None, None)
+    websocket = FakeWebSocket([{"type": "ping"}], close_exc)
+    monkeypatch.setattr(hub.websockets, "connect", lambda *args, **kwargs: FakeConnect(websocket=websocket))
+    async def fake_sleep(_delay):
+        return None
+    monkeypatch.setattr(hub.asyncio, "sleep", fake_sleep)
+    client = hub.HubTunnelClient("api-key", VALID_TOKEN, yinyang_port=TEST_PORT)
+    client.max_retries = 1
+    await client.run()
+    assert websocket.sent == [{"type": "pong"}]
+@pytest.mark.asyncio
+async def test_client_proxies_get_request(monkeypatch):
+    hub = load_hub_tunnel_client()
+    def fake_urlopen(request, timeout=5):
+        assert request.get_method() == "GET"
+        assert request.full_url == f"http://localhost:{TEST_PORT}/health"
+        assert request.headers["Authorization"] == f"Bearer {VALID_TOKEN}"
+        return FakeResponse(200, '{"status":"ok"}')
+    monkeypatch.setattr(hub.urllib.request, "urlopen", fake_urlopen)
+    client = hub.HubTunnelClient("api-key", VALID_TOKEN, yinyang_port=TEST_PORT)
+    response = await client._handle_message({"id": "1", "method": "GET", "path": "/health"})
+    assert response["id"] == "1"
+    assert response["status"] == 200
+    assert response["body"] == '{"status":"ok"}'
+@pytest.mark.asyncio
+async def test_client_proxies_post_request(monkeypatch):
+    hub = load_hub_tunnel_client()
+    def fake_urlopen(request, timeout=5):
+        assert request.get_method() == "POST"
+        assert request.data == b'{"hello": "world"}'
+        return FakeResponse(201, '{"created":true}')
+    monkeypatch.setattr(hub.urllib.request, "urlopen", fake_urlopen)
+    client = hub.HubTunnelClient("api-key", VALID_TOKEN, yinyang_port=TEST_PORT)
+    response = await client._handle_message({
+        "id": "2",
+        "method": "POST",
+        "path": "/api/v1/evidence",
+        "body": {"hello": "world"},
+    })
+    assert response["status"] == 201
+    assert response["body"] == '{"created":true}'
+@pytest.mark.asyncio
+async def test_client_handles_disconnect_gracefully(monkeypatch):
+    hub = load_hub_tunnel_client()
+    close_exc = ConnectionClosedOK(None, None)
+    attempts: list[int] = []
+    def fake_connect(*args, **kwargs):
+        attempts.append(1)
+        return FakeConnect(websocket=FakeWebSocket([], close_exc))
+    async def fake_sleep(_delay):
+        return None
+    monkeypatch.setattr(hub.websockets, "connect", fake_connect)
+    monkeypatch.setattr(hub.asyncio, "sleep", fake_sleep)
+    client = hub.HubTunnelClient("api-key", VALID_TOKEN, yinyang_port=TEST_PORT)
+    client.max_retries = 3
+    await client.run()
+    assert len(attempts) == 3
+    assert client.retries == 3
+def test_start_cloud_no_api_key_returns_400(cloud_server):
+    load_hub_tunnel_client()
+    handler, captured = make_handler(cloud_server, body={})
+    handler._handle_tunnel_start_cloud()
+    assert captured["status"] == 400
+    assert captured["data"]["error"] == "api_key required"
+def test_cloud_status_inactive_by_default(cloud_server):
+    load_hub_tunnel_client()
+    handler, captured = make_handler(cloud_server)
+    handler._handle_tunnel_cloud_status()
+    assert captured["status"] == 200
+    assert captured["data"] == {"active": False, "relay": None, "retries": 0}
+def test_start_cloud_sets_active(cloud_server, monkeypatch):
+    load_hub_tunnel_client()
+    class DummyClient:
+        retries = 0
+    def fake_launch(api_key: str, yinyang_bearer: str, yinyang_port: int) -> None:
+        assert api_key == "sw_sk_test"
+        assert yinyang_bearer == VALID_TOKEN
+        assert yinyang_port == SERVER_PORT
+        cloud_server._CLOUD_TUNNEL_ACTIVE = True
+        cloud_server._CLOUD_TUNNEL_CLIENT = DummyClient()
+
+    monkeypatch.setattr(cloud_server, "_launch_cloud_tunnel", fake_launch)
+    handler, captured = make_handler(cloud_server, body={"api_key": "sw_sk_test"})
+    handler._handle_tunnel_start_cloud()
+    assert captured["status"] == 200
+    assert captured["data"] == {"status": "connecting", "relay": RELAY_URL}
+    status_handler, status_captured = make_handler(cloud_server)
+    status_handler._handle_tunnel_cloud_status()
+    assert status_captured["status"] == 200
+    assert status_captured["data"] == {"active": True, "relay": RELAY_URL, "retries": 0}
