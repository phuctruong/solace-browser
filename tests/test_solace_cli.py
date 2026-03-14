# Diagram: 05-solace-runtime-architecture
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


TEST_PORT = 18888
TOKEN_SHA256 = "a" * 64


def _write_port_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / ".solace" / "port.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"token_sha256": TOKEN_SHA256}))


def test_cli_status_calls_correct_endpoint(monkeypatch, tmp_path):
    import solace_cli

    _write_port_lock(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    called = {}

    def fake_request(method, path, token, payload=None, timeout=10):
        called.update(
            method=method,
            path=path,
            token=token,
            payload=payload,
            timeout=timeout,
        )
        return {"status": "ok"}

    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
    stdout = io.StringIO()
    stderr = io.StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = solace_cli.main(["status"])

    assert TEST_PORT == 18888
    assert exit_code == 0
    assert called == {
        "method": "GET",
        "path": "/api/v1/system/status",
        "token": TOKEN_SHA256,
        "payload": None,
        "timeout": 10,
    }
    assert json.loads(stdout.getvalue()) == {"status": "ok"}
    assert stderr.getvalue() == ""


def test_cli_apps_list(monkeypatch, tmp_path):
    import solace_cli

    _write_port_lock(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    called = {}

    def fake_request(method, path, token, payload=None, timeout=10):
        called.update(method=method, path=path, token=token, payload=payload)
        return [{"id": "calendar"}]

    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
    stdout = io.StringIO()

    with redirect_stdout(stdout):
        exit_code = solace_cli.main(["apps", "list"])

    assert exit_code == 0
    assert called == {
        "method": "GET",
        "path": "/api/v1/apps",
        "token": TOKEN_SHA256,
        "payload": None,
    }
    assert json.loads(stdout.getvalue()) == [{"id": "calendar"}]


def test_cli_sessions_list(monkeypatch, tmp_path):
    import solace_cli

    _write_port_lock(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    called = {}

    def fake_request(method, path, token, payload=None, timeout=10):
        called.update(method=method, path=path, token=token, payload=payload)
        return [{"id": "sess-1"}]

    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
    stdout = io.StringIO()

    with redirect_stdout(stdout):
        exit_code = solace_cli.main(["sessions", "list"])

    assert exit_code == 0
    assert called == {
        "method": "GET",
        "path": "/api/v1/sessions",
        "token": TOKEN_SHA256,
        "payload": None,
    }
    assert json.loads(stdout.getvalue()) == [{"id": "sess-1"}]


def test_cli_evidence_tail(monkeypatch, tmp_path):
    import solace_cli

    _write_port_lock(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    called = {}

    def fake_request(method, path, token, payload=None, timeout=10):
        called.update(method=method, path=path, token=token, payload=payload)
        return [{"id": "ev-1"}]

    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
    stdout = io.StringIO()

    with redirect_stdout(stdout):
        exit_code = solace_cli.main(["evidence", "tail", "--limit", "10"])

    assert exit_code == 0
    assert called == {
        "method": "GET",
        "path": "/api/v1/evidence?limit=10",
        "token": TOKEN_SHA256,
        "payload": None,
    }
    assert json.loads(stdout.getvalue()) == [{"id": "ev-1"}]


def test_cli_tunnel_status(monkeypatch, tmp_path):
    import solace_cli

    _write_port_lock(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    called = {}

    def fake_request(method, path, token, payload=None, timeout=10):
        called.update(method=method, path=path, token=token, payload=payload)
        return {"status": "idle"}

    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
    stdout = io.StringIO()

    with redirect_stdout(stdout):
        exit_code = solace_cli.main(["tunnel", "status"])

    assert exit_code == 0
    assert called == {
        "method": "GET",
        "path": "/api/v1/tunnel/status",
        "token": TOKEN_SHA256,
        "payload": None,
    }
    assert json.loads(stdout.getvalue()) == {"status": "idle"}


def test_cli_no_token_exits_cleanly(monkeypatch, tmp_path):
    import solace_cli

    monkeypatch.setenv("HOME", str(tmp_path))
    stdout = io.StringIO()
    stderr = io.StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = solace_cli.main(["status"])

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Yinyang Server not running. Start it first." in stderr.getvalue()


def test_cli_session_rules_list(monkeypatch, tmp_path):
    import solace_cli

    _write_port_lock(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    called = {}

    def fake_request(method, path, token, payload=None, timeout=10):
        called.update(method=method, path=path, token=token, payload=payload)
        return [{"app": "browser"}]

    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
    stdout = io.StringIO()

    with redirect_stdout(stdout):
        exit_code = solace_cli.main(["session-rules", "list"])

    assert exit_code == 0
    assert called == {
        "method": "GET",
        "path": "/api/v1/session-rules",
        "token": TOKEN_SHA256,
        "payload": None,
    }
    assert json.loads(stdout.getvalue()) == [{"app": "browser"}]
