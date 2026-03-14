# Diagram: 29-chromium-build-pipeline
#!/usr/bin/env python3
"""Run a paid-user SolaceAGI cloud rehearsal against production."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path


BASE_URL = "https://solaceagi.com"
ARTIFACTS_DIR = Path.home() / ".solace" / "artifacts"


def _request(
    path: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    merged_headers = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        merged_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=merged_headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode()
    if not body:
        return {}
    return json.loads(body)


def _api_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _get_text(path: str) -> str:
    request = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode()


def _stillwater_witness(api_key: str) -> dict:
    session_id = f"paid-cloud-stillwater-{int(time.time())}"
    create = _request(
        "/api/v1/stillwater/snapshots",
        method="POST",
        payload={
            "session_id": session_id,
            "url": "https://solaceagi.com/demo/stillwater",
            "title": "Paid Cloud Stillwater Witness",
            "captured_at": "2026-03-11T22:20:00Z",
            "html": (
                "<html><body><h1>Paid Cloud Stillwater Witness</h1>"
                f"<p>session={session_id}</p></body></html>"
            ),
        },
        headers=_api_headers(api_key),
    )
    snapshot_id = str(create["snapshot_id"])
    sessions = _request("/api/v1/stillwater/history", headers=_api_headers(api_key))
    snapshots = _request(
        f"/api/v1/stillwater/history/{session_id}",
        headers=_api_headers(api_key),
    )
    snapshot = _request(
        f"/api/v1/stillwater/history/{session_id}/{snapshot_id}",
        headers=_api_headers(api_key),
    )
    render_request = urllib.request.Request(
        f"{BASE_URL}/api/v1/stillwater/history/{session_id}/{snapshot_id}/render",
        headers=_api_headers(api_key),
        method="GET",
    )
    with urllib.request.urlopen(render_request, timeout=30) as response:
        render_html = response.read().decode()
        render_headers = dict(response.headers.items())
    return {
        "create": create,
        "sessions": sessions,
        "snapshots": snapshots,
        "snapshot": snapshot,
        "render_contains_title": "Paid Cloud Stillwater Witness" in render_html,
        "render_header_content_type": render_headers.get("Content-Type"),
    }


def run_rehearsal() -> dict:
    api_key = os.environ.get("SOLACEAGI_API_KEY") or os.environ.get("SOLACE_API_KEY")
    if not api_key:
        raise RuntimeError("Set SOLACEAGI_API_KEY or SOLACE_API_KEY first.")

    health = _request("/api/v1/health")
    dashboard_html = _get_text("/dashboard")
    billing = _request("/api/v1/billing/subscription", headers=_api_headers(api_key))
    usage = _request("/api/v1/billing/usage", headers=_api_headers(api_key))
    storage = _request("/api/v1/billing/storage", headers=_api_headers(api_key))

    oauth3_bearer = _request("/api/v1/oauth3/token", method="POST", payload={"api_key": api_key})
    oauth3_verify = _request(
        "/api/v1/oauth3/verify",
        headers={"Authorization": f"Bearer {oauth3_bearer['access_token']}"},
    )
    scoped = _request(
        "/api/v1/oauth3/tokens",
        method="POST",
        payload={"scopes": ["files.read", "files.write"]},
        headers=_api_headers(api_key),
    )
    fs_sync = _request(
        "/api/v1/fs/sync/status",
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-OAuth3-Token": scoped["token"],
        },
    )

    twin = _request(
        "/api/v1/browser/twin/launch",
        method="POST",
        payload={
            "scope": "twin:browser",
            "ttl_minutes": 15,
            "app_id": "solace-yinyang",
            "url": "https://solaceagi.com/dashboard",
        },
        headers=_api_headers(api_key),
    )
    twin_id = str(twin["twin_id"])
    twin_status = _request(f"/api/v1/browser/twin/status/{twin_id}", headers=_api_headers(api_key))
    twin_approve = _request(
        f"/api/v1/browser/twin/approve/{twin_id}",
        method="POST",
        headers=_api_headers(api_key),
    )
    twin_delete = _request(
        f"/api/v1/browser/twin/{twin_id}",
        method="DELETE",
        headers=_api_headers(api_key),
    )

    return {
        "health": health,
        "dashboard_handoff": {
            "has_onboarding_link": "http://127.0.0.1:8888/onboarding" in dashboard_html,
            "has_local_agents_link": "http://127.0.0.1:8888/agents" in dashboard_html,
            "has_morning_brief_link": "http://127.0.0.1:8888/apps/morning-brief/outbox/reports/today.html" in dashboard_html,
        },
        "billing_subscription": billing,
        "billing_usage": usage,
        "billing_storage": storage,
        "oauth3_bearer": oauth3_bearer,
        "oauth3_verify": oauth3_verify,
        "oauth3_scoped_token": {
            "token_id": scoped.get("token_id"),
            "scopes": scoped.get("scopes", []),
            "expires_at": scoped.get("expires_at"),
            "token_prefix": str(scoped.get("token", ""))[:8],
        },
        "fs_sync_status": fs_sync,
        "twin_launch": twin,
        "twin_status": twin_status,
        "twin_approve": twin_approve,
        "twin_delete": twin_delete,
        "stillwater": _stillwater_witness(api_key),
    }


def main() -> int:
    result = run_rehearsal()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACTS_DIR / f"paid-cloud-rehearsal-{int(time.time())}.json"
    artifact_path.write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {
                "artifact": str(artifact_path),
                "ok": True,
                "plan": result["billing_subscription"].get("plan"),
                "twin_id": result["twin_launch"].get("twin_id"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
