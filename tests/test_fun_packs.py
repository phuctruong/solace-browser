"""tests/test_fun_packs.py — Fun Pack Standard acceptance gate."""
import io
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VALID_TOKEN = "a" * 64
TEST_PORT = 18888


def _request(ys, path: str, method: str = "GET", payload=None, token: str | None = VALID_TOKEN):
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    headers = {"Content-Length": str(len(body))}
    if body:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    server = type(
        "DummyServer",
        (),
        {
            "session_token_sha256": VALID_TOKEN,
            "repo_root": str(PROJECT_ROOT),
            "cloud_twin_mode": False,
            "hub_integration_enabled": True,
        },
    )()

    handler = ys.YinyangHandler.__new__(ys.YinyangHandler)
    handler.server = server
    handler.client_address = ("127.0.0.1", TEST_PORT)
    handler.command = method
    handler.path = path
    handler.requestline = f"{method} {path} HTTP/1.1"
    handler.request_version = "HTTP/1.1"
    handler.close_connection = True
    handler.headers = headers
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler._headers_buffer = []
    handler.log_request = lambda *args, **kwargs: None
    handler.log_message = lambda *args, **kwargs: None

    if method == "GET":
        handler.do_GET()
    elif method == "POST":
        handler.do_POST()
    else:
        raise AssertionError(f"Unsupported method: {method}")

    raw = handler.wfile.getvalue()
    header_block, response_body = raw.split(b"\r\n\r\n", 1)
    status_line = header_block.splitlines()[0].decode("utf-8")
    status = int(status_line.split()[1])
    return status, json.loads(response_body or b"{}")


@pytest.fixture
def fun_pack_env(tmp_path, monkeypatch: pytest.MonkeyPatch):
    import yinyang_server as ys

    monkeypatch.setattr(ys, "ACTIVE_PACK_PATH", tmp_path / "active-fun-pack.json", raising=False)
    monkeypatch.setattr(ys, "PORT_LOCK_PATH", tmp_path / "port.lock", raising=False)
    monkeypatch.setattr(ys, "EVIDENCE_PATH", tmp_path / "evidence.jsonl", raising=False)
    return {"module": ys, "active_pack_path": tmp_path / "active-fun-pack.json"}


def test_fun_packs_list_returns_packs(fun_pack_env):
    status, data = _request(fun_pack_env["module"], "/api/v1/fun-packs")
    assert status == 200
    assert data["active_pack_id"] == "default-en"
    assert data["count"] >= 1
    assert any(pack["id"] == "default-en" for pack in data["packs"])


def test_fun_packs_requires_auth(fun_pack_env):
    status, data = _request(fun_pack_env["module"], "/api/v1/fun-packs", token=None)
    assert status == 401
    assert data == {"error": "unauthorized"}


def test_fun_packs_active_returns_full_pack(fun_pack_env):
    status, data = _request(fun_pack_env["module"], "/api/v1/fun-packs/active")
    assert status == 200
    assert data["pack"]["_meta"]["id"] == "default-en"
    assert len(data["pack"]["jokes"]) == 20


def test_fun_packs_random_joke_is_string(fun_pack_env):
    status, data = _request(fun_pack_env["module"], "/api/v1/fun-packs/random-joke")
    assert status == 200
    assert isinstance(data["joke"]["text"], str)
    assert data["joke"]["pack_id"] == "default-en"


def test_fun_packs_random_fact_is_string(fun_pack_env):
    status, data = _request(fun_pack_env["module"], "/api/v1/fun-packs/random-fact")
    assert status == 200
    assert isinstance(data["fact"]["text"], str)
    assert data["fact"]["pack_id"] == "default-en"


def test_fun_packs_greeting_morning(fun_pack_env):
    status, data = _request(fun_pack_env["module"], "/api/v1/fun-packs/greeting?time_of_day=morning")
    assert status == 200
    assert isinstance(data["greeting"]["text"], str)
    assert data["greeting"]["pack_id"] == "default-en"


def test_fun_packs_activate_sets_active(fun_pack_env):
    status, data = _request(
        fun_pack_env["module"],
        "/api/v1/fun-packs/default-en/activate",
        method="POST",
        payload={},
    )
    assert status == 200
    assert data == {"status": "activated", "pack_id": "default-en"}
    stored = json.loads(fun_pack_env["active_pack_path"].read_text(encoding="utf-8"))
    assert stored == {"active_pack_id": "default-en"}


def test_fun_packs_unknown_pack_404(fun_pack_env):
    status, data = _request(fun_pack_env["module"], "/api/v1/fun-packs/nonexistent")
    assert status == 404
    assert data == {"error": "fun pack not found"}


def test_fun_packs_default_en_json_valid():
    path = PROJECT_ROOT / "data" / "fun-packs" / "default-en.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["_meta"]["id"] == "default-en"


def test_fun_packs_default_en_has_20_jokes():
    path = PROJECT_ROOT / "data" / "fun-packs" / "default-en.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["jokes"]) == 20


def test_fun_packs_html_exists():
    assert (PROJECT_ROOT / "web" / "fun-packs.html").exists()


def test_fun_packs_html_no_cdn():
    html_path = PROJECT_ROOT / "web" / "fun-packs.html"
    content = html_path.read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "bootstrap.min.css" not in content
    assert "tailwind" not in content.lower()
    assert "jquery" not in content.lower()
