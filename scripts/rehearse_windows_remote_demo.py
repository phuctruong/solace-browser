# Diagram: 29-chromium-build-pipeline
#!/usr/bin/env python3
"""
rehearse_windows_remote_demo.py — Native-host Windows validation for Browser + Hub.
Auth: 65537 | Hub first | Port 8888 only

Run this on the Windows machine after installing the real MSI from solaceagi.com.
It verifies:
  - the live website points to the Windows MSI URL
  - the local Hub runtime is healthy on 8888
  - the cloud tunnel can reach the local Browser through solaceagi.com
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import requests


LIVE_DOWNLOAD_URL = "https://solaceagi.com/download/solace-browser"
LIVE_TUNNEL_STATUS_URL = "https://solaceagi.com/api/v1/tunnel/status"
LIVE_TUNNEL_PROXY_BASE = "https://solaceagi.com/api/v1/tunnel/proxy"
LOCAL_BASE = "http://127.0.0.1:8888"


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def _http_json(method: str, url: str, *, headers: dict[str, str] | None = None, payload: dict | None = None) -> dict:
    response = requests.request(method, url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def _download_page_contains_windows_msi() -> str:
    html = urllib.request.urlopen(LIVE_DOWNLOAD_URL).read().decode("utf-8", "ignore")
    match = re.search(
        r"https://storage\.googleapis\.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64\.msi",
        html,
    )
    if not match:
        raise SystemExit("Live download page does not yet expose the Windows MSI URL.")
    return match.group(0)


def _wait_for_local_runtime() -> dict:
    last_error: str | None = None
    for _ in range(30):
        try:
            return _http_json("GET", f"{LOCAL_BASE}/api/status")
        except Exception as exc:  # noqa: BLE001 - native smoke witness
            last_error = str(exc)
            time.sleep(1)
    raise SystemExit(f"Local Hub runtime did not become healthy on 8888: {last_error}")


def main() -> int:
    api_key = _require_env("SOLACEAGI_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}

    msi_url = _download_page_contains_windows_msi()
    local_status = _wait_for_local_runtime()

    tunnel_start = _http_json("POST", f"{LOCAL_BASE}/api/v1/tunnel/start-cloud")
    tunnel_status = _http_json("GET", LIVE_TUNNEL_STATUS_URL, headers=headers)

    launch = _http_json(
        "POST",
        f"{LIVE_TUNNEL_PROXY_BASE}/api/v1/browser/launch",
        headers={**headers, "Content-Type": "application/json"},
        payload={
            "url": f"{LOCAL_BASE}/agents",
            "source": "windows-native-remote-proof",
            "head_hidden": True,
        },
    )
    remote_status = _http_json("GET", f"{LIVE_TUNNEL_PROXY_BASE}/api/v1/browser/status", headers=headers)
    close = _http_json("POST", f"{LIVE_TUNNEL_PROXY_BASE}/api/v1/browser/close", headers=headers)
    tunnel_stop = _http_json("POST", f"{LOCAL_BASE}/api/v1/tunnel/stop")

    artifact = {
        "ok": True,
        "timestamp": int(time.time()),
        "live_windows_msi_url": msi_url,
        "local_runtime": {
            "port": local_status.get("port"),
            "apps": local_status.get("apps"),
        },
        "tunnel_start": tunnel_start,
        "tunnel_status": tunnel_status,
        "remote_launch": {
            "ok": launch.get("ok"),
            "session_id": launch.get("session_id"),
            "head_hidden": launch.get("head_hidden"),
        },
        "remote_status": {
            "tracked_session_count": remote_status.get("tracked_session_count"),
            "visible_window_count": remote_status.get("visible_window_count"),
        },
        "remote_close": close,
        "tunnel_stop": tunnel_stop,
    }

    out_dir = Path.home() / ".solace" / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"windows-native-remote-proof-{artifact['timestamp']}.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
