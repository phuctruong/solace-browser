"""Tests for CLI Agent Integration — Task 064."""

import hashlib
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18888
BASE_URL = f"http://localhost:{TEST_PORT}"
AUTH_HASH = "a" * 64


@pytest.fixture(scope="module")
def cli_agent_server():
    import yinyang_server as ys

    ys._detect_available_agents.cache_clear()
    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=AUTH_HASH)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(40):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"httpd": httpd, "module": ys}

    httpd.shutdown()
    httpd.server_close()
    ys._detect_available_agents.cache_clear()


def _request(
    method: str,
    path: str,
    payload: dict | None = None,
    with_auth: bool = True,
) -> tuple[int, dict]:
    headers: dict[str, str] = {}
    if with_auth:
        headers["Authorization"] = f"Bearer {AUTH_HASH}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def _set_detected_agents(
    monkeypatch: pytest.MonkeyPatch,
    module,
    mapping: dict[str, str],
    counter: dict[str, int] | None = None,
) -> None:
    def fake_which(binary: str) -> str | None:
        if counter is not None:
            counter["calls"] = counter.get("calls", 0) + 1
        return mapping.get(binary)

    module._detect_available_agents.cache_clear()
    monkeypatch.setattr(module.shutil, "which", fake_which)


def test_cli_agents_detect_returns_agents(cli_agent_server, monkeypatch: pytest.MonkeyPatch):
    ys = cli_agent_server["module"]
    _set_detected_agents(
        monkeypatch,
        ys,
        {
            "claude": "/usr/bin/claude",
            "codex": "/usr/bin/codex",
            "gemini": "/usr/bin/gemini",
            "aider": "/usr/bin/aider",
        },
    )

    status, data = _request("GET", "/api/v1/cli-agents/detect")

    assert status == 200
    assert data["count"] == 4
    assert data["cache_status"] == "fresh"
    assert data["agents"] == [
        {"name": "claude", "path": "/usr/bin/claude", "default_model": "claude-sonnet-4-6"},
        {"name": "codex", "path": "/usr/bin/codex", "default_model": "gpt-5.4"},
        {"name": "gemini", "path": "/usr/bin/gemini", "default_model": "gemini-2.0-flash"},
        {"name": "aider", "path": "/usr/bin/aider", "default_model": "gpt-4o"},
    ]
    assert data["not_found"] == []


def test_cli_agents_detect_requires_auth(cli_agent_server):
    status, data = _request("GET", "/api/v1/cli-agents/detect", with_auth=False)
    assert status == 401
    assert data["error"] == "unauthorized"


def test_cli_agents_generate_requires_auth(cli_agent_server):
    status, data = _request(
        "POST",
        "/api/v1/cli-agents/generate",
        {"agent": "gemini", "prompt": "Say hi"},
        with_auth=False,
    )
    assert status == 401
    assert data["error"] == "unauthorized"


def test_cli_agents_generate_requires_prompt(cli_agent_server, monkeypatch: pytest.MonkeyPatch):
    ys = cli_agent_server["module"]
    _set_detected_agents(monkeypatch, ys, {"gemini": "/usr/bin/gemini"})

    status, data = _request("POST", "/api/v1/cli-agents/generate", {"agent": "gemini"})

    assert status == 400
    assert data == {"error": "prompt is required", "code": "MISSING_PROMPT"}


def test_cli_agents_generate_cost_usd_is_string(cli_agent_server, monkeypatch: pytest.MonkeyPatch):
    ys = cli_agent_server["module"]
    _set_detected_agents(
        monkeypatch,
        ys,
        {
            "claude": "/usr/bin/claude",
            "codex": "/usr/bin/codex",
            "gemini": "/usr/bin/gemini",
        },
    )

    def fake_invoke(
        agent_name: str,
        executable: str,
        prompt: str,
        model: str | None = None,
        timeout_s: int = 60,
    ) -> dict[str, str]:
        assert agent_name == "gemini"
        assert executable == "/usr/bin/gemini"
        assert prompt == "[SKILL: prime-safety]\n[SKILL: prime-coder]\n\nwrite tests"
        assert model == "gemini-2.0-flash"
        assert timeout_s == 12
        return {"stdout": "done", "stderr": ""}

    monkeypatch.setattr(ys, "_invoke_cli_agent", fake_invoke)

    status, data = _request(
        "POST",
        "/api/v1/cli-agents/generate",
        {
            "agent": "auto",
            "prompt": "write tests",
            "skill_pack": ["prime-safety", "prime-coder"],
            "timeout_s": 12,
        },
    )

    assert status == 200
    assert data["agent"] == "gemini"
    assert data["model"] == "gemini-2.0-flash"
    assert data["output"] == "done"
    assert isinstance(data["cost_usd"], str)
    assert Decimal(data["cost_usd"]) > 0
    assert "e" not in data["cost_usd"].lower()
    assert isinstance(data["latency_ms"], int)
    assert data["latency_ms"] >= 0
    assert data["evidence_id"] == "sha256:" + hashlib.sha256(b"done").hexdigest()
    assert data["rung"] == 641


def test_cli_agents_refresh_clears_cache(cli_agent_server, monkeypatch: pytest.MonkeyPatch):
    ys = cli_agent_server["module"]
    first_mapping = {"claude": "/usr/bin/claude"}
    second_mapping = {"gemini": "/usr/bin/gemini"}
    state = {"mapping": first_mapping}

    def fake_which(binary: str) -> str | None:
        return state["mapping"].get(binary)

    ys._detect_available_agents.cache_clear()
    monkeypatch.setattr(ys.shutil, "which", fake_which)

    detect_status, detect_data = _request("GET", "/api/v1/cli-agents/detect")
    assert detect_status == 200
    assert [agent["name"] for agent in detect_data["agents"]] == ["claude"]

    state["mapping"] = second_mapping
    refresh_status, refresh_data = _request("GET", "/api/v1/cli-agents/refresh")

    assert refresh_status == 200
    assert refresh_data["cache_status"] == "refreshed"
    assert [agent["name"] for agent in refresh_data["agents"]] == ["gemini"]


def test_cli_agents_detect_no_shell_true():
    source = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    start = source.index("def _detect_available_agents")
    end = source.index("def _default_model_for_agent")
    snippet = source[start:end]
    assert "shell=True" not in snippet


def test_cli_agents_generate_unknown_agent(cli_agent_server):
    status, data = _request(
        "POST",
        "/api/v1/cli-agents/generate",
        {"agent": "unknown_xyz", "prompt": "Say hi"},
    )

    assert status == 400
    assert data["error"] == "unknown agent: unknown_xyz"


def test_cli_agents_generate_without_installed_cli(cli_agent_server, monkeypatch: pytest.MonkeyPatch):
    ys = cli_agent_server["module"]
    _set_detected_agents(monkeypatch, ys, {})

    status, data = _request(
        "POST",
        "/api/v1/cli-agents/generate",
        {"agent": "gemini", "prompt": "Say hi"},
    )

    assert status == 400
    assert data == {
        "error": "Agent 'gemini' not found on PATH",
        "code": "AGENT_NOT_FOUND",
        "available": [],
    }


def test_cli_agents_detect_cache_fresh_on_second_call(cli_agent_server, monkeypatch: pytest.MonkeyPatch):
    ys = cli_agent_server["module"]
    counter = {"calls": 0}
    _set_detected_agents(monkeypatch, ys, {"claude": "/usr/bin/claude"}, counter)

    first_status, first_data = _request("GET", "/api/v1/cli-agents/detect")
    second_status, second_data = _request("GET", "/api/v1/cli-agents/detect")

    assert first_status == 200
    assert second_status == 200
    assert first_data["cache_status"] == "fresh"
    assert second_data["cache_status"] == "fresh"
    assert counter["calls"] == 4
