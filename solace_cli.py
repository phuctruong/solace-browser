# Diagram: 01-triangle-architecture
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request


HUB_PORT = 8888
REQUEST_TIMEOUT = 10
BASE_URL = f"http://localhost:{HUB_PORT}"


class CliError(Exception):
    pass


def _load_token() -> str:
    lock_path = Path.home() / ".solace" / "port.lock"
    try:
        payload = lock_path.read_text()
    except FileNotFoundError as exc:
        raise CliError("Yinyang Server not running. Start it first.") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CliError("Invalid ~/.solace/port.lock JSON.") from exc

    token_sha256 = data.get("token_sha256")
    if not isinstance(token_sha256, str) or not token_sha256:
        raise CliError("Invalid ~/.solace/port.lock: missing token_sha256.")
    return token_sha256


def _error_message(response_body: str, fallback: str) -> str:
    if not response_body.strip():
        return fallback

    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError:
        return response_body.strip()

    if isinstance(payload, dict):
        error_text = payload.get("error")
        if isinstance(error_text, str) and error_text:
            return error_text
    return json.dumps(payload, sort_keys=True)


def _request_json(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
    timeout: int = REQUEST_TIMEOUT,
) -> Any:
    url = f"{BASE_URL}{path}"
    body = None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    http_request = request.Request(url, data=body, headers=headers, method=method)

    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        raise CliError(_error_message(response_body, f"HTTP {exc.code}")) from exc
    except error.URLError as exc:
        reason = exc.reason if isinstance(exc.reason, str) else str(exc.reason)
        raise CliError(f"Unable to reach Yinyang Server: {reason}") from exc

    if not response_body:
        return {}

    try:
        return json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise CliError("Server returned invalid JSON.") from exc


def _extract_output_flags(argv: list[str]) -> tuple[list[str], bool, bool]:
    cleaned: list[str] = []
    quiet = False
    raw = False

    for arg in argv:
        if arg in ("-q", "--quiet"):
            quiet = True
        elif arg == "--raw":
            raw = True
        else:
            cleaned.append(arg)

    return cleaned, quiet, raw


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="solace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")

    apps_parser = subparsers.add_parser("apps")
    apps_subparsers = apps_parser.add_subparsers(dest="apps_command", required=True)
    apps_subparsers.add_parser("list")
    apps_run_parser = apps_subparsers.add_parser("run")
    apps_run_parser.add_argument("app")
    apps_run_parser.add_argument("--action")

    sessions_parser = subparsers.add_parser("sessions")
    sessions_subparsers = sessions_parser.add_subparsers(dest="sessions_command", required=True)
    sessions_subparsers.add_parser("list")
    sessions_new_parser = sessions_subparsers.add_parser("new")
    sessions_new_parser.add_argument("url")
    sessions_kill_parser = sessions_subparsers.add_parser("kill")
    sessions_kill_parser.add_argument("session_id")

    evidence_parser = subparsers.add_parser("evidence")
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    evidence_tail_parser = evidence_subparsers.add_parser("tail")
    evidence_tail_parser.add_argument("--limit", type=int, default=20)
    evidence_subparsers.add_parser("verify")

    tunnel_parser = subparsers.add_parser("tunnel")
    tunnel_subparsers = tunnel_parser.add_subparsers(dest="tunnel_command", required=True)
    tunnel_subparsers.add_parser("status")
    tunnel_subparsers.add_parser("start")
    tunnel_subparsers.add_parser("start-cloud")

    budget_parser = subparsers.add_parser("budget")
    budget_subparsers = budget_parser.add_subparsers(dest="budget_command", required=True)
    budget_subparsers.add_parser("status")

    byok_parser = subparsers.add_parser("byok")
    byok_subparsers = byok_parser.add_subparsers(dest="byok_command", required=True)
    byok_subparsers.add_parser("list")

    session_rules_parser = subparsers.add_parser("session-rules")
    session_rules_subparsers = session_rules_parser.add_subparsers(
        dest="session_rules_command",
        required=True,
    )
    session_rules_subparsers.add_parser("list")
    session_rules_check_parser = session_rules_subparsers.add_parser("check")
    session_rules_check_parser.add_argument("app")

    return parser


def _build_request_args(args: argparse.Namespace) -> tuple[str, str, dict[str, Any] | None]:
    if args.command == "status":
        return "GET", "/api/v1/system/status", None

    if args.command == "apps":
        if args.apps_command == "list":
            return "GET", "/api/v1/apps", None
        if args.apps_command == "run":
            path = f"/api/v1/apps/{parse.quote(args.app, safe='')}/run"
            payload = {"action": args.action} if args.action else None
            return "POST", path, payload

    if args.command == "sessions":
        if args.sessions_command == "list":
            return "GET", "/api/v1/sessions", None
        if args.sessions_command == "new":
            return "POST", "/api/v1/sessions", {"url": args.url}
        if args.sessions_command == "kill":
            path = f"/api/v1/sessions/{parse.quote(args.session_id, safe='')}"
            return "DELETE", path, None

    if args.command == "evidence":
        if args.evidence_command == "tail":
            query = parse.urlencode({"limit": args.limit})
            return "GET", f"/api/v1/evidence?{query}", None
        if args.evidence_command == "verify":
            return "GET", "/api/v1/evidence/verify", None

    if args.command == "tunnel":
        if args.tunnel_command == "status":
            return "GET", "/api/v1/tunnel/status", None
        if args.tunnel_command == "start":
            return "POST", "/api/v1/tunnel/start", None
        if args.tunnel_command == "start-cloud":
            return "POST", "/api/v1/tunnel/start-cloud", None

    if args.command == "budget" and args.budget_command == "status":
        return "GET", "/api/v1/budget", None

    if args.command == "byok" and args.byok_command == "list":
        return "GET", "/api/v1/byok/providers", None

    if args.command == "session-rules":
        if args.session_rules_command == "list":
            return "GET", "/api/v1/session-rules", None
        if args.session_rules_command == "check":
            path = f"/api/v1/session-rules/check/{parse.quote(args.app, safe='')}"
            return "POST", path, None

    raise CliError("Unsupported command.")


def _print_json(payload: Any, raw: bool) -> None:
    if raw:
        sys.stdout.write(json.dumps(payload))
        sys.stdout.write("\n")
        return

    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    input_argv = list(argv) if argv is not None else sys.argv[1:]
    cleaned_argv, quiet, raw = _extract_output_flags(input_argv)
    parser = _build_parser()

    try:
        args = parser.parse_args(cleaned_argv)
        token = _load_token()
        method, path, payload = _build_request_args(args)
        response = _request_json(method, path, token, payload=payload, timeout=REQUEST_TIMEOUT)
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not quiet:
        _print_json(response, raw=raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
