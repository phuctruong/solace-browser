diff --git a/scripts/install.sh b/scripts/install.sh
index a9c8aef5..cdc48d78 100755
--- a/scripts/install.sh
+++ b/scripts/install.sh
@@ -4,6 +4,7 @@ set -eu
 
 STATE_DIR="${HOME}/.solace"
 LIB_DIR="${HOME}/.local/lib/solace"
+BIN_DIR="${HOME}/.local/bin"
 SYSTEMD_DIR="${HOME}/.config/systemd/user"
 SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
 
@@ -38,18 +39,20 @@ resolve_repo_root() {
 
 require_cmd cp
 require_cmd chmod
+require_cmd ln
 require_cmd mkdir
 require_cmd systemctl
 
 repo_root=$(resolve_repo_root)
 
-mkdir -p "${STATE_DIR}" "${LIB_DIR}" "${SYSTEMD_DIR}"
+mkdir -p "${STATE_DIR}" "${LIB_DIR}" "${BIN_DIR}" "${SYSTEMD_DIR}"
 
 cp "${SCRIPT_DIR}/launch-yinyang.sh" "${LIB_DIR}/launch-yinyang.sh"
 cp "${SCRIPT_DIR}/stop-yinyang.sh" "${LIB_DIR}/stop-yinyang.sh"
 cp "${SCRIPT_DIR}/install.sh" "${LIB_DIR}/install.sh"
 cp "${SCRIPT_DIR}/yinyang.service" "${LIB_DIR}/yinyang.service"
 chmod 755 "${LIB_DIR}/launch-yinyang.sh" "${LIB_DIR}/stop-yinyang.sh" "${LIB_DIR}/install.sh"
+ln -sf "${repo_root}/scripts/solace" "${BIN_DIR}/solace"
 
 printf '%s\n' "${repo_root}" > "${STATE_DIR}/repo-root"
 cp "${SCRIPT_DIR}/yinyang.service" "${SYSTEMD_DIR}/yinyang.service"
@@ -58,4 +61,5 @@ systemctl --user daemon-reload
 systemctl --user enable yinyang
 
 echo "Installed Yinyang launcher to ${LIB_DIR}"
+echo "Installed solace CLI to ${BIN_DIR}/solace"
 echo "Systemd user unit installed at ${SYSTEMD_DIR}/yinyang.service"
diff --git a/solace_cli.py b/solace_cli.py
new file mode 100755
index 00000000..f944312b
--- /dev/null
+++ b/solace_cli.py
@@ -0,0 +1,246 @@
+#!/usr/bin/env python3
+
+from __future__ import annotations
+
+import argparse
+import json
+import sys
+from pathlib import Path
+from typing import Any
+from urllib import error, parse, request
+
+
+HUB_PORT = 8888
+REQUEST_TIMEOUT = 10
+BASE_URL = f"http://localhost:{HUB_PORT}"
+
+
+class CliError(Exception):
+    pass
+
+
+def _load_token() -> str:
+    lock_path = Path.home() / ".solace" / "port.lock"
+    try:
+        payload = lock_path.read_text()
+    except FileNotFoundError as exc:
+        raise CliError("Yinyang Server not running. Start it first.") from exc
+
+    try:
+        data = json.loads(payload)
+    except json.JSONDecodeError as exc:
+        raise CliError("Invalid ~/.solace/port.lock JSON.") from exc
+
+    token_sha256 = data.get("token_sha256")
+    if not isinstance(token_sha256, str) or not token_sha256:
+        raise CliError("Invalid ~/.solace/port.lock: missing token_sha256.")
+    return token_sha256
+
+
+def _error_message(response_body: str, fallback: str) -> str:
+    if not response_body.strip():
+        return fallback
+
+    try:
+        payload = json.loads(response_body)
+    except json.JSONDecodeError:
+        return response_body.strip()
+
+    if isinstance(payload, dict):
+        error_text = payload.get("error")
+        if isinstance(error_text, str) and error_text:
+            return error_text
+    return json.dumps(payload, sort_keys=True)
+
+
+def _request_json(
+    method: str,
+    path: str,
+    token: str,
+    payload: dict[str, Any] | None = None,
+    timeout: int = REQUEST_TIMEOUT,
+) -> Any:
+    url = f"{BASE_URL}{path}"
+    body = None
+    headers = {
+        "Accept": "application/json",
+        "Authorization": f"Bearer {token}",
+    }
+
+    if payload is not None:
+        body = json.dumps(payload).encode("utf-8")
+        headers["Content-Type"] = "application/json"
+
+    http_request = request.Request(url, data=body, headers=headers, method=method)
+
+    try:
+        with request.urlopen(http_request, timeout=timeout) as response:
+            response_body = response.read().decode("utf-8")
+    except error.HTTPError as exc:
+        response_body = exc.read().decode("utf-8")
+        raise CliError(_error_message(response_body, f"HTTP {exc.code}")) from exc
+    except error.URLError as exc:
+        reason = exc.reason if isinstance(exc.reason, str) else str(exc.reason)
+        raise CliError(f"Unable to reach Yinyang Server: {reason}") from exc
+
+    if not response_body:
+        return {}
+
+    try:
+        return json.loads(response_body)
+    except json.JSONDecodeError as exc:
+        raise CliError("Server returned invalid JSON.") from exc
+
+
+def _extract_output_flags(argv: list[str]) -> tuple[list[str], bool, bool]:
+    cleaned: list[str] = []
+    quiet = False
+    raw = False
+
+    for arg in argv:
+        if arg in ("-q", "--quiet"):
+            quiet = True
+        elif arg == "--raw":
+            raw = True
+        else:
+            cleaned.append(arg)
+
+    return cleaned, quiet, raw
+
+
+def _build_parser() -> argparse.ArgumentParser:
+    parser = argparse.ArgumentParser(prog="solace")
+    subparsers = parser.add_subparsers(dest="command", required=True)
+
+    subparsers.add_parser("status")
+
+    apps_parser = subparsers.add_parser("apps")
+    apps_subparsers = apps_parser.add_subparsers(dest="apps_command", required=True)
+    apps_subparsers.add_parser("list")
+    apps_run_parser = apps_subparsers.add_parser("run")
+    apps_run_parser.add_argument("app")
+    apps_run_parser.add_argument("--action")
+
+    sessions_parser = subparsers.add_parser("sessions")
+    sessions_subparsers = sessions_parser.add_subparsers(dest="sessions_command", required=True)
+    sessions_subparsers.add_parser("list")
+    sessions_new_parser = sessions_subparsers.add_parser("new")
+    sessions_new_parser.add_argument("url")
+    sessions_kill_parser = sessions_subparsers.add_parser("kill")
+    sessions_kill_parser.add_argument("session_id")
+
+    evidence_parser = subparsers.add_parser("evidence")
+    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command", required=True)
+    evidence_tail_parser = evidence_subparsers.add_parser("tail")
+    evidence_tail_parser.add_argument("--limit", type=int, default=20)
+    evidence_subparsers.add_parser("verify")
+
+    tunnel_parser = subparsers.add_parser("tunnel")
+    tunnel_subparsers = tunnel_parser.add_subparsers(dest="tunnel_command", required=True)
+    tunnel_subparsers.add_parser("status")
+    tunnel_subparsers.add_parser("start")
+    tunnel_subparsers.add_parser("start-cloud")
+
+    budget_parser = subparsers.add_parser("budget")
+    budget_subparsers = budget_parser.add_subparsers(dest="budget_command", required=True)
+    budget_subparsers.add_parser("status")
+
+    byok_parser = subparsers.add_parser("byok")
+    byok_subparsers = byok_parser.add_subparsers(dest="byok_command", required=True)
+    byok_subparsers.add_parser("list")
+
+    session_rules_parser = subparsers.add_parser("session-rules")
+    session_rules_subparsers = session_rules_parser.add_subparsers(
+        dest="session_rules_command",
+        required=True,
+    )
+    session_rules_subparsers.add_parser("list")
+    session_rules_check_parser = session_rules_subparsers.add_parser("check")
+    session_rules_check_parser.add_argument("app")
+
+    return parser
+
+
+def _build_request_args(args: argparse.Namespace) -> tuple[str, str, dict[str, Any] | None]:
+    if args.command == "status":
+        return "GET", "/api/v1/system/status", None
+
+    if args.command == "apps":
+        if args.apps_command == "list":
+            return "GET", "/api/v1/apps", None
+        if args.apps_command == "run":
+            path = f"/api/v1/apps/{parse.quote(args.app, safe='')}/run"
+            payload = {"action": args.action} if args.action else None
+            return "POST", path, payload
+
+    if args.command == "sessions":
+        if args.sessions_command == "list":
+            return "GET", "/api/v1/sessions", None
+        if args.sessions_command == "new":
+            return "POST", "/api/v1/sessions", {"url": args.url}
+        if args.sessions_command == "kill":
+            path = f"/api/v1/sessions/{parse.quote(args.session_id, safe='')}"
+            return "DELETE", path, None
+
+    if args.command == "evidence":
+        if args.evidence_command == "tail":
+            query = parse.urlencode({"limit": args.limit})
+            return "GET", f"/api/v1/evidence?{query}", None
+        if args.evidence_command == "verify":
+            return "GET", "/api/v1/evidence/verify", None
+
+    if args.command == "tunnel":
+        if args.tunnel_command == "status":
+            return "GET", "/api/v1/tunnel/status", None
+        if args.tunnel_command == "start":
+            return "POST", "/api/v1/tunnel/start", None
+        if args.tunnel_command == "start-cloud":
+            return "POST", "/api/v1/tunnel/start-cloud", None
+
+    if args.command == "budget" and args.budget_command == "status":
+        return "GET", "/api/v1/budget", None
+
+    if args.command == "byok" and args.byok_command == "list":
+        return "GET", "/api/v1/byok/providers", None
+
+    if args.command == "session-rules":
+        if args.session_rules_command == "list":
+            return "GET", "/api/v1/session-rules", None
+        if args.session_rules_command == "check":
+            path = f"/api/v1/session-rules/check/{parse.quote(args.app, safe='')}"
+            return "POST", path, None
+
+    raise CliError("Unsupported command.")
+
+
+def _print_json(payload: Any, raw: bool) -> None:
+    if raw:
+        sys.stdout.write(json.dumps(payload))
+        sys.stdout.write("\n")
+        return
+
+    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
+    sys.stdout.write("\n")
+
+
+def main(argv: list[str] | None = None) -> int:
+    input_argv = list(argv) if argv is not None else sys.argv[1:]
+    cleaned_argv, quiet, raw = _extract_output_flags(input_argv)
+    parser = _build_parser()
+
+    try:
+        args = parser.parse_args(cleaned_argv)
+        token = _load_token()
+        method, path, payload = _build_request_args(args)
+        response = _request_json(method, path, token, payload=payload, timeout=REQUEST_TIMEOUT)
+    except CliError as exc:
+        print(str(exc), file=sys.stderr)
+        return 1
+
+    if not quiet:
+        _print_json(response, raw=raw)
+    return 0
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())
diff --git a/scripts/solace b/scripts/solace
new file mode 100755
index 00000000..85bb34c7
--- /dev/null
+++ b/scripts/solace
@@ -0,0 +1,5 @@
+#!/usr/bin/env bash
+
+set -eu
+
+exec python3 "$(dirname "$0")/../solace_cli.py" "$@"
diff --git a/tests/test_solace_cli.py b/tests/test_solace_cli.py
new file mode 100644
index 00000000..092ab782
--- /dev/null
+++ b/tests/test_solace_cli.py
@@ -0,0 +1,201 @@
+import io
+import json
+from contextlib import redirect_stderr, redirect_stdout
+from pathlib import Path
+
+
+TEST_PORT = 18888
+TOKEN_SHA256 = "a" * 64
+
+
+def _write_port_lock(tmp_path: Path) -> None:
+    lock_path = tmp_path / ".solace" / "port.lock"
+    lock_path.parent.mkdir(parents=True, exist_ok=True)
+    lock_path.write_text(json.dumps({"token_sha256": TOKEN_SHA256}))
+
+
+def test_cli_status_calls_correct_endpoint(monkeypatch, tmp_path):
+    import solace_cli
+
+    _write_port_lock(tmp_path)
+    monkeypatch.setenv("HOME", str(tmp_path))
+    called = {}
+
+    def fake_request(method, path, token, payload=None, timeout=10):
+        called.update(
+            method=method,
+            path=path,
+            token=token,
+            payload=payload,
+            timeout=timeout,
+        )
+        return {"status": "ok"}
+
+    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
+    stdout = io.StringIO()
+    stderr = io.StringIO()
+
+    with redirect_stdout(stdout), redirect_stderr(stderr):
+        exit_code = solace_cli.main(["status"])
+
+    assert TEST_PORT == 18888
+    assert exit_code == 0
+    assert called == {
+        "method": "GET",
+        "path": "/api/v1/system/status",
+        "token": TOKEN_SHA256,
+        "payload": None,
+        "timeout": 10,
+    }
+    assert json.loads(stdout.getvalue()) == {"status": "ok"}
+    assert stderr.getvalue() == ""
+
+
+def test_cli_apps_list(monkeypatch, tmp_path):
+    import solace_cli
+
+    _write_port_lock(tmp_path)
+    monkeypatch.setenv("HOME", str(tmp_path))
+    called = {}
+
+    def fake_request(method, path, token, payload=None, timeout=10):
+        called.update(method=method, path=path, token=token, payload=payload)
+        return [{"id": "calendar"}]
+
+    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
+    stdout = io.StringIO()
+
+    with redirect_stdout(stdout):
+        exit_code = solace_cli.main(["apps", "list"])
+
+    assert exit_code == 0
+    assert called == {
+        "method": "GET",
+        "path": "/api/v1/apps",
+        "token": TOKEN_SHA256,
+        "payload": None,
+    }
+    assert json.loads(stdout.getvalue()) == [{"id": "calendar"}]
+
+
+def test_cli_sessions_list(monkeypatch, tmp_path):
+    import solace_cli
+
+    _write_port_lock(tmp_path)
+    monkeypatch.setenv("HOME", str(tmp_path))
+    called = {}
+
+    def fake_request(method, path, token, payload=None, timeout=10):
+        called.update(method=method, path=path, token=token, payload=payload)
+        return [{"id": "sess-1"}]
+
+    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
+    stdout = io.StringIO()
+
+    with redirect_stdout(stdout):
+        exit_code = solace_cli.main(["sessions", "list"])
+
+    assert exit_code == 0
+    assert called == {
+        "method": "GET",
+        "path": "/api/v1/sessions",
+        "token": TOKEN_SHA256,
+        "payload": None,
+    }
+    assert json.loads(stdout.getvalue()) == [{"id": "sess-1"}]
+
+
+def test_cli_evidence_tail(monkeypatch, tmp_path):
+    import solace_cli
+
+    _write_port_lock(tmp_path)
+    monkeypatch.setenv("HOME", str(tmp_path))
+    called = {}
+
+    def fake_request(method, path, token, payload=None, timeout=10):
+        called.update(method=method, path=path, token=token, payload=payload)
+        return [{"id": "ev-1"}]
+
+    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
+    stdout = io.StringIO()
+
+    with redirect_stdout(stdout):
+        exit_code = solace_cli.main(["evidence", "tail", "--limit", "10"])
+
+    assert exit_code == 0
+    assert called == {
+        "method": "GET",
+        "path": "/api/v1/evidence?limit=10",
+        "token": TOKEN_SHA256,
+        "payload": None,
+    }
+    assert json.loads(stdout.getvalue()) == [{"id": "ev-1"}]
+
+
+def test_cli_tunnel_status(monkeypatch, tmp_path):
+    import solace_cli
+
+    _write_port_lock(tmp_path)
+    monkeypatch.setenv("HOME", str(tmp_path))
+    called = {}
+
+    def fake_request(method, path, token, payload=None, timeout=10):
+        called.update(method=method, path=path, token=token, payload=payload)
+        return {"status": "idle"}
+
+    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
+    stdout = io.StringIO()
+
+    with redirect_stdout(stdout):
+        exit_code = solace_cli.main(["tunnel", "status"])
+
+    assert exit_code == 0
+    assert called == {
+        "method": "GET",
+        "path": "/api/v1/tunnel/status",
+        "token": TOKEN_SHA256,
+        "payload": None,
+    }
+    assert json.loads(stdout.getvalue()) == {"status": "idle"}
+
+
+def test_cli_no_token_exits_cleanly(monkeypatch, tmp_path):
+    import solace_cli
+
+    monkeypatch.setenv("HOME", str(tmp_path))
+    stdout = io.StringIO()
+    stderr = io.StringIO()
+
+    with redirect_stdout(stdout), redirect_stderr(stderr):
+        exit_code = solace_cli.main(["status"])
+
+    assert exit_code == 1
+    assert stdout.getvalue() == ""
+    assert "Yinyang Server not running. Start it first." in stderr.getvalue()
+
+
+def test_cli_session_rules_list(monkeypatch, tmp_path):
+    import solace_cli
+
+    _write_port_lock(tmp_path)
+    monkeypatch.setenv("HOME", str(tmp_path))
+    called = {}
+
+    def fake_request(method, path, token, payload=None, timeout=10):
+        called.update(method=method, path=path, token=token, payload=payload)
+        return [{"app": "browser"}]
+
+    monkeypatch.setattr(solace_cli, "_request_json", fake_request)
+    stdout = io.StringIO()
+
+    with redirect_stdout(stdout):
+        exit_code = solace_cli.main(["session-rules", "list"])
+
+    assert exit_code == 0
+    assert called == {
+        "method": "GET",
+        "path": "/api/v1/session-rules",
+        "token": TOKEN_SHA256,
+        "payload": None,
+    }
+    assert json.loads(stdout.getvalue()) == [{"app": "browser"}]
