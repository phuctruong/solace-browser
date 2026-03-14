# Diagram: 05-solace-runtime-architecture
import asyncio
import importlib
import json
import pathlib
import sys

import pytest
from websockets.exceptions import ConnectionClosedOK

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18888
SERVER_PORT = TEST_PORT + 1
VALID_TOKEN = "a" * 64
RELAY_URL = "https://solaceagi.com"
WS_URL = "wss://solaceagi.com/api/v1/tunnel/connect"
def load_hub_tunnel_client():
    return importlib.import_module("hub_tunnel_client")
class FakeResponse:
    def __init__(self, status: int, body: str, headers: dict | None = None):
        self.status = status
        self._body = body.encode()
        self.headers = headers or {"Content-Type": "application/json"}

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
class FakeWebSocket:
    def __init__(self, messages: list[object], close_exc):
        self._messages = list(messages)
        self._close_exc = close_exc
        self.sent: list[dict] = []
        self.closed = False

    async def recv(self) -> str:
        if self._messages:
            return json.dumps(self._messages.pop(0))
        raise self._close_exc

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def close(self) -> None:
        self.closed = True
class FakeConnect:
    def __init__(self, websocket=None, error: BaseException | None = None):
        self._websocket = websocket
        self._error = error

    async def __aenter__(self):
        if self._error is not None:
            raise self._error
        return self._websocket

    async def __aexit__(self, exc_type, exc, tb):
        return False
def load_yinyang_server():
    return importlib.import_module("yinyang_server")
@pytest.fixture
def cloud_server(monkeypatch, tmp_path):
    load_hub_tunnel_client()
    ys = load_yinyang_server()
    monkeypatch.setattr(ys, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(ys, "EVIDENCE_PATH", tmp_path / "evidence.jsonl")
    monkeypatch.setattr(ys, "record_evidence", lambda *args, **kwargs: {})
    ys._CLOUD_TUNNEL_THREAD = None
    ys._CLOUD_TUNNEL_CLIENT = None
    ys._CLOUD_TUNNEL_ACTIVE = False
    ys._CLOUD_TUNNEL_LOOP = None
    return ys
def make_handler(ys, body: dict | None = None):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    handler.server = type("DummyServer", (), {"session_token_sha256": VALID_TOKEN, "server_port": SERVER_PORT})()
    handler._check_auth = lambda: True
    handler._read_json_body = lambda: body
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    return handler, captured
@pytest.mark.asyncio
async def test_client_sends_pong_on_ping(monkeypatch):
    hub = load_hub_tunnel_client()
    close_exc = ConnectionClosedOK(None, None)
    websocket = FakeWebSocket([{"type": "ping"}], close_exc)
    captured: dict = {}
    def fake_connect(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return FakeConnect(websocket=websocket)
    monkeypatch.setattr(hub.websockets, "connect", fake_connect)
    async def fake_sleep(_delay):
        return None
    monkeypatch.setattr(hub.asyncio, "sleep", fake_sleep)
    client = hub.HubTunnelClient("api-key", VALID_TOKEN, yinyang_port=TEST_PORT)
    client.max_retries = 1
    await client.run()
    assert captured["args"] == (WS_URL,)
    assert captured["kwargs"]["additional_headers"] == {"Authorization": "Bearer api-key"}
    assert websocket.sent == [{"type": "pong"}]
@pytest.mark.asyncio
async def test_client_proxies_get_request(monkeypatch):
    hub = load_hub_tunnel_client()
    def fake_urlopen(request, timeout=5):
        assert request.get_method() == "GET"
        assert request.full_url == f"http://localhost:{TEST_PORT}/health"
        assert request.headers["Authorization"] == f"Bearer {VALID_TOKEN}"
        return FakeResponse(200, '{"status":"ok"}')
    monkeypatch.setattr(hub.urllib.request, "urlopen", fake_urlopen)
    client = hub.HubTunnelClient("api-key", VALID_TOKEN, yinyang_port=TEST_PORT)
    response = await client._handle_message({"id": "1", "method": "GET", "path": "/health"})
    assert response["id"] == "1"
    assert response["status"] == 200
    assert response["body"] == '{"status":"ok"}'
@pytest.mark.asyncio
async def test_client_proxies_post_request(monkeypatch):
    hub = load_hub_tunnel_client()
    def fake_urlopen(request, timeout=5):
        assert request.get_method() == "POST"
        assert request.data == b'{"hello": "world"}'
        return FakeResponse(201, '{"created":true}')
    monkeypatch.setattr(hub.urllib.request, "urlopen", fake_urlopen)
    client = hub.HubTunnelClient("api-key", VALID_TOKEN, yinyang_port=TEST_PORT)
    response = await client._handle_message({
        "id": "2",
        "method": "POST",
        "path": "/api/v1/evidence",
        "body": {"hello": "world"},
    })
    assert response["status"] == 201
    assert response["body"] == '{"created":true}'
@pytest.mark.asyncio
async def test_client_handles_disconnect_gracefully(monkeypatch):
    hub = load_hub_tunnel_client()
    close_exc = ConnectionClosedOK(None, None)
    attempts: list[int] = []
    def fake_connect(*args, **kwargs):
        attempts.append(1)
        return FakeConnect(websocket=FakeWebSocket([], close_exc))
    async def fake_sleep(_delay):
        return None
    monkeypatch.setattr(hub.websockets, "connect", fake_connect)
    monkeypatch.setattr(hub.asyncio, "sleep", fake_sleep)
    client = hub.HubTunnelClient("api-key", VALID_TOKEN, yinyang_port=TEST_PORT)
    client.max_retries = 3
    await client.run()
    assert len(attempts) == 3
    assert client.retries == 3
def test_start_cloud_no_api_key_returns_400(cloud_server):
    load_hub_tunnel_client()
    handler, captured = make_handler(cloud_server, body={})
    handler._handle_tunnel_start_cloud()
    assert captured["status"] == 400
    assert captured["data"]["error"] == "api_key required"
def test_cloud_status_inactive_by_default(cloud_server):
    load_hub_tunnel_client()
    handler, captured = make_handler(cloud_server)
    handler._handle_tunnel_cloud_status()
    assert captured["status"] == 200
    assert captured["data"] == {"active": False, "relay": None, "retries": 0}
def test_start_cloud_sets_active(cloud_server, monkeypatch):
    load_hub_tunnel_client()
    class DummyClient:
        retries = 0
    def fake_launch(api_key: str, yinyang_bearer: str, yinyang_port: int) -> None:
        assert api_key == "sw_sk_test"
        assert yinyang_bearer == VALID_TOKEN
        assert yinyang_port == SERVER_PORT
        cloud_server._CLOUD_TUNNEL_ACTIVE = True
        cloud_server._CLOUD_TUNNEL_CLIENT = DummyClient()

    monkeypatch.setattr(cloud_server, "_launch_cloud_tunnel", fake_launch)
    handler, captured = make_handler(cloud_server, body={"api_key": "sw_sk_test"})
    handler._handle_tunnel_start_cloud()
    assert captured["status"] == 200
    assert captured["data"] == {"status": "connecting", "relay": RELAY_URL}
    status_handler, status_captured = make_handler(cloud_server)
    status_handler._handle_tunnel_cloud_status()
    assert status_captured["status"] == 200
    assert status_captured["data"] == {"active": True, "relay": RELAY_URL, "retries": 0}
