Command:

```bash
pytest -q tests/test_cli_agent_integration.py
```

Output before the server patch:

```text
F..FF...F.                                                               [100%]
=================================== FAILURES ===================================
____________________ test_cli_agents_detect_returns_agents _____________________

cli_agent_server = {'httpd': <yinyang_server.ReusableThreadingHTTPServer object at 0x7e98cc048250>, 'module': <module 'yinyang_server' from '/home/phuc/projects/solace-browser/yinyang_server.py'>}
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7e98cbe76a40>

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
>       assert data["agents"] == [
            {"name": "claude", "path": "/usr/bin/claude", "default_model": "claude-sonnet-4-6"},
            {"name": "codex", "path": "/usr/bin/codex", "default_model": "gpt-5.4"},
            {"name": "gemini", "path": "/usr/bin/gemini", "default_model": "gemini-2.0-flash"},
            {"name": "aider", "path": "/usr/bin/aider", "default_model": "gpt-4o"},
        ]
E       AssertionError: assert [{'default_mo...r/bin/aider'}] == [{'default_mo...r/bin/aider'}]
E
E         At index 3 diff: {'name': 'aider', 'path': '/usr/bin/aider', 'default_model': 'configured-backend'} != {'name': 'aider', 'path': '/usr/bin/aider', 'default_model': 'gpt-4o'}

tests/test_cli_agent_integration.py:101: AssertionError
___________________ test_cli_agents_generate_requires_prompt ___________________

cli_agent_server = {'httpd': <yinyang_server.ReusableThreadingHTTPServer object at 0x7e98cc048250>, 'module': <module 'yinyang_server' from '/home/phuc/projects/solace-browser/yinyang_server.py'>}
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7e98cbc3cd00>

    def test_cli_agents_generate_requires_prompt(cli_agent_server, monkeypatch: pytest.MonkeyPatch):
        ys = cli_agent_server["module"]
        _set_detected_agents(monkeypatch, ys, {"gemini": "/usr/bin/gemini"})

        status, data = _request("POST", "/api/v1/cli-agents/generate", {"agent": "gemini"})

        assert status == 400
>       assert data == {"error": "prompt is required", "code": "MISSING_PROMPT"}
E       AssertionError: assert {'error': 'pr... is required'} == {'code': 'MIS... is required'}

tests/test_cli_agent_integration.py:134: AssertionError
_________________ test_cli_agents_generate_cost_usd_is_string __________________

cli_agent_server = {'httpd': <yinyang_server.ReusableThreadingHTTPServer object at 0x7e98cc048250>, 'module': <module 'yinyang_server' from '/home/phuc/projects/solace-browser/yinyang_server.py'>}
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7e98cbbd45b0>

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

>       status, data = _request(
            "POST",
            "/api/v1/cli-agents/generate",
            {
                "agent": "auto",
                "prompt": "write tests",
                "skill_pack": ["prime-safety", "prime-coder"],
                "timeout_s": 12,
            },
        )
E       http.client.RemoteDisconnected: Remote end closed connection without response

tests/test_cli_agent_integration.py:165:
----------------------------- Captured stderr call -----------------------------
AssertionError: assert 'claude' == 'gemini'
________________ test_cli_agents_generate_without_installed_cli ________________

cli_agent_server = {'httpd': <yinyang_server.ReusableThreadingHTTPServer object at 0x7e98cc048250>, 'module': <module 'yinyang_server' from '/home/phuc/projects/solace-browser/yinyang_server.py'>}
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7e98cc1e0370>

    def test_cli_agents_generate_without_installed_cli(cli_agent_server, monkeypatch: pytest.MonkeyPatch):
        ys = cli_agent_server["module"]
        _set_detected_agents(monkeypatch, ys, {})

        status, data = _request(
            "POST",
            "/api/v1/cli-agents/generate",
            {"agent": "gemini", "prompt": "Say hi"},
        )

        assert status == 400
>       assert data == {
            "error": "Agent 'gemini' not found on PATH",
            "code": "AGENT_NOT_FOUND",
            "available": [],
        }
E       assert {'error': "Ag...ound on PATH"} == {'available': [], 'code': 'AGENT_NOT_FOUND', 'error': "Agent 'gemini' not found on PATH"}

tests/test_cli_agent_integration.py:243: AssertionError
=========================== short test summary info ============================
FAILED tests/test_cli_agent_integration.py::test_cli_agents_detect_returns_agents
FAILED tests/test_cli_agent_integration.py::test_cli_agents_generate_requires_prompt
FAILED tests/test_cli_agent_integration.py::test_cli_agents_generate_cost_usd_is_string
FAILED tests/test_cli_agent_integration.py::test_cli_agents_generate_without_installed_cli
4 failed, 6 passed in 0.86s
```
