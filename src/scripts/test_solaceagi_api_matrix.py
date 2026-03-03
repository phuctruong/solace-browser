#!/usr/bin/env python3
"""
Production API matrix tester for solaceagi.com.

Usage:
  python3 src/scripts/test_solaceagi_api_matrix.py \
      --base-url https://www.solaceagi.com \
      --output-dir scratch/prod-api-matrix-2026-03-03
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


HTTP_METHODS = ("get", "post", "put", "patch", "delete")
MUTATING_METHODS = {"post", "put", "patch", "delete"}


@dataclass
class CallResult:
    method: str
    path: str
    url: str
    status_code: int
    duration_ms: int
    response_bytes: int
    error: str | None = None


def _http_json(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=25) as resp:
        body = resp.read()
        return json.loads(body.decode("utf-8"))


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    # ref format: "#/components/schemas/Name"
    node: Any = spec
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    if not isinstance(node, dict):
        raise ValueError(f"Invalid ref target for {ref}")
    return node


def _sample_value_for_schema(spec: dict[str, Any], schema: dict[str, Any], field_name: str = "") -> Any:
    if "$ref" in schema:
        return _sample_value_for_schema(spec, _resolve_ref(spec, schema["$ref"]), field_name)

    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]

    if "const" in schema:
        return schema["const"]

    schema_type = schema.get("type")
    if schema_type == "string":
        fname = field_name.lower()
        if "email" in fname:
            return "qa-user@example.com"
        if "url" in fname:
            return "https://example.com"
        if "id" in fname:
            return f"{field_name or 'id'}-test"
        if "hash" in fname:
            return "0" * 64
        if "token" in fname:
            return "token-test"
        return "test"

    if schema_type == "integer":
        if "minimum" in schema:
            return int(schema["minimum"])
        return 1

    if schema_type == "number":
        if "minimum" in schema:
            return float(schema["minimum"])
        return 1.0

    if schema_type == "boolean":
        return True

    if schema_type == "array":
        item_schema = schema.get("items", {"type": "string"})
        return [_sample_value_for_schema(spec, item_schema, field_name)]

    if schema_type == "object" or "properties" in schema:
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        out: dict[str, Any] = {}
        for key, prop in props.items():
            if required and key not in required:
                continue
            out[key] = _sample_value_for_schema(spec, prop, key)
        return out

    if "anyOf" in schema and schema["anyOf"]:
        return _sample_value_for_schema(spec, schema["anyOf"][0], field_name)

    return "test"


def _sample_path_value(name: str) -> str:
    lname = name.lower()
    if "appid" in lname or "app_id" in lname:
        return "gmail-inbox-triage"
    if "runid" in lname or "run_id" in lname:
        return "run_test_001"
    if "taskid" in lname or "task_id" in lname:
        return "task_test_001"
    if "workflow" in lname:
        return "wf_test_001"
    if "ticket" in lname:
        return "ticket_test_001"
    if "signature" in lname:
        return "sig_test_001"
    if "document" in lname:
        return "doc_test_001"
    if "slug" in lname:
        return "launch"
    return f"{name}-test"


def _build_headers(token: str | None, api_key: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _request(
    url: str,
    method: str,
    headers: dict[str, str],
    body: dict[str, Any] | None,
) -> CallResult:
    payload: bytes | None = None
    req_headers = dict(headers)
    if body is not None:
        req_headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")

    req = Request(url=url, method=method.upper(), headers=req_headers, data=payload)
    t0 = time.perf_counter()
    try:
        with urlopen(req, timeout=25) as resp:
            data = resp.read()
            dt_ms = int((time.perf_counter() - t0) * 1000)
            return CallResult(
                method=method.upper(),
                path="",
                url=url,
                status_code=resp.getcode(),
                duration_ms=dt_ms,
                response_bytes=len(data),
                error=None,
            )
    except HTTPError as err:
        data = err.read() if hasattr(err, "read") else b""
        dt_ms = int((time.perf_counter() - t0) * 1000)
        return CallResult(
            method=method.upper(),
            path="",
            url=url,
            status_code=err.code,
            duration_ms=dt_ms,
            response_bytes=len(data),
            error=str(err),
        )
    except URLError as err:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        return CallResult(
            method=method.upper(),
            path="",
            url=url,
            status_code=0,
            duration_ms=dt_ms,
            response_bytes=0,
            error=str(err),
        )


def _make_operation_payload(
    spec: dict[str, Any],
    operation: dict[str, Any],
) -> dict[str, Any] | None:
    req_body = operation.get("requestBody")
    if not req_body:
        return None

    content = req_body.get("content", {})
    json_content = content.get("application/json")
    if not json_content:
        return None

    schema = json_content.get("schema")
    if not schema:
        return None
    value = _sample_value_for_schema(spec, schema)
    return value if isinstance(value, dict) else {"value": value}


def _prepare_operation_url(
    base_url: str,
    path: str,
    operation: dict[str, Any],
) -> str:
    url_path = path
    query_params: list[tuple[str, str]] = []
    for param in operation.get("parameters", []):
        name = param["name"]
        pin = param.get("in")
        required = bool(param.get("required", False))
        schema = param.get("schema", {})
        if pin == "path":
            replacement = _sample_path_value(name)
            url_path = url_path.replace("{" + name + "}", replacement)
        elif pin == "query" and required:
            value = _sample_path_value(name)
            if schema:
                sampled = _sample_value_for_schema({}, schema, name) if "$ref" not in schema else value
                value = str(sampled)
            query_params.append((name, value))
    query = ("?" + urlencode(query_params)) if query_params else ""
    return f"{base_url}{url_path}{query}"


def _operation_sort_key(item: tuple[str, str]) -> tuple[str, str]:
    return item[0], item[1]


def run_matrix(
    *,
    base_url: str,
    output_dir: Path,
    bearer_token: str | None,
    api_key: str | None,
    include_mutating: bool,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = _http_json(f"{base_url}/openapi.json")
    headers = _build_headers(bearer_token, api_key)

    paths = spec.get("paths", {})
    operations: list[tuple[str, str, dict[str, Any]]] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            if method in MUTATING_METHODS and not include_mutating:
                continue
            operations.append((path, method, operation))

    results: list[CallResult] = []
    for path, method, operation in sorted(operations, key=lambda x: _operation_sort_key((x[0], x[1]))):
        url = _prepare_operation_url(base_url, path, operation)
        body = _make_operation_payload(spec, operation) if method in MUTATING_METHODS else None
        result = _request(url, method, headers, body)
        result.path = path
        results.append(result)

    started_at = datetime.now(timezone.utc).isoformat()
    status_buckets = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "0xx": 0}
    for r in results:
        if r.status_code == 0:
            status_buckets["0xx"] += 1
        elif 200 <= r.status_code < 300:
            status_buckets["2xx"] += 1
        elif 300 <= r.status_code < 400:
            status_buckets["3xx"] += 1
        elif 400 <= r.status_code < 500:
            status_buckets["4xx"] += 1
        elif 500 <= r.status_code < 600:
            status_buckets["5xx"] += 1

    summary = {
        "base_url": base_url,
        "started_at_utc": started_at,
        "include_mutating": include_mutating,
        "auth_mode": {
            "bearer_present": bool(bearer_token),
            "api_key_present": bool(api_key),
        },
        "counts": {
            "operations_tested": len(results),
            "status_buckets": status_buckets,
            "hard_failures": sum(1 for r in results if r.status_code == 0 or r.status_code >= 500),
        },
        "latency_ms": {
            "avg": int(sum(r.duration_ms for r in results) / len(results)) if results else 0,
            "max": max((r.duration_ms for r in results), default=0),
        },
    }

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "results.json").write_text(
        json.dumps([r.__dict__ for r in results], indent=2), encoding="utf-8"
    )

    report_lines = [
        "# SolaceAGI Production API Matrix",
        "",
        f"- Base URL: `{base_url}`",
        f"- Operations tested: **{summary['counts']['operations_tested']}**",
        f"- Status buckets: `{summary['counts']['status_buckets']}`",
        f"- Hard failures (0xx + 5xx): **{summary['counts']['hard_failures']}**",
        f"- Auth bearer present: `{summary['auth_mode']['bearer_present']}`",
        f"- API key present: `{summary['auth_mode']['api_key_present']}`",
        f"- Avg latency: `{summary['latency_ms']['avg']} ms`",
        f"- Max latency: `{summary['latency_ms']['max']} ms`",
        "",
        "## Top 25 slowest operations",
        "",
        "| Method | Path | Status | ms |",
        "|---|---|---:|---:|",
    ]
    slowest = sorted(results, key=lambda r: r.duration_ms, reverse=True)[:25]
    for r in slowest:
        report_lines.append(f"| `{r.method}` | `{r.path}` | `{r.status_code}` | `{r.duration_ms}` |")

    (output_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return summary["counts"]["hard_failures"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a production API matrix against solaceagi.com")
    parser.add_argument("--base-url", default="https://www.solaceagi.com")
    parser.add_argument(
        "--output-dir",
        default=f"scratch/prod-api-matrix-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    )
    parser.add_argument("--bearer-token-env", default="SOLACE_BEARER_TOKEN")
    parser.add_argument("--api-key-env", default="SOLACE_API_KEY")
    parser.add_argument(
        "--include-mutating",
        action="store_true",
        help="Include POST/PUT/PATCH/DELETE operations in matrix",
    )
    args = parser.parse_args()

    bearer_token = os.environ.get(args.bearer_token_env)
    api_key = os.environ.get(args.api_key_env)

    hard_failures = run_matrix(
        base_url=args.base_url.rstrip("/"),
        output_dir=Path(args.output_dir),
        bearer_token=bearer_token,
        api_key=api_key,
        include_mutating=args.include_mutating,
    )
    # Non-zero on hard transport/server failures only.
    return 1 if hard_failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
