# Diagram: 29-chromium-build-pipeline
#!/usr/bin/env python3
"""Rehearse the Hub-first onboarding and sign-in handoff against localhost:8888."""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:8888"
HOME = Path.home()
ARTIFACTS_DIR = HOME / ".solace" / "artifacts"
ONBOARDING_PATH = HOME / ".solace" / "onboarding.json"


def _request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode()
    if not body:
        return {}
    return json.loads(body)


def _get_text(path: str) -> str:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=20) as response:
        return response.read().decode()


def _clear_onboarding() -> None:
    try:
        ONBOARDING_PATH.unlink()
    except FileNotFoundError:
        return


def _wait_for_browser_url(expected_url: str, timeout_seconds: float = 20.0) -> dict:
    deadline = time.time() + timeout_seconds
    last: dict = {}
    while time.time() < deadline:
        last = _request("/api/v1/browser/status")
        sessions = last.get("tracked_sessions", [])
        if sessions:
            current_url = str(sessions[0].get("url", "")).strip()
            if current_url == expected_url:
                return last
        time.sleep(0.5)
    raise RuntimeError(f"browser did not reach {expected_url!r}; last={last}")


def _wait_for_no_browser(timeout_seconds: float = 20.0) -> dict:
    deadline = time.time() + timeout_seconds
    last: dict = {}
    while time.time() < deadline:
        last = _request("/api/v1/browser/status")
        if int(last.get("tracked_session_count", 0)) == 0 and int(last.get("visible_window_count", 0)) == 0:
            return last
        time.sleep(0.5)
    raise RuntimeError(f"browser did not terminate before timeout; last={last}")


def run_rehearsal() -> dict:
    _clear_onboarding()

    runtime = _request("/api/status")
    if runtime.get("status") != "ok":
        raise RuntimeError(f"runtime unhealthy: {runtime}")

    close_before = _request("/api/v1/browser/close", method="POST", payload={"all": True})
    zero_state = _wait_for_no_browser()

    onboarding_before = _request("/api/v1/onboarding/status")
    onboarding_html = _get_text("/onboarding")
    if onboarding_before.get("completed") is not False:
        raise RuntimeError(f"expected fresh onboarding state, got {onboarding_before}")

    agent_setup = _request("/onboarding/complete", method="POST", payload={"mode": "agent"})
    onboarding_after = _request("/api/v1/onboarding/status")

    register_launch = _request(
        "/api/v1/hub/browser/open",
        method="POST",
        payload={"url": "https://solaceagi.com/register", "profile": "default", "mode": "standard"},
    )
    register_status = _wait_for_browser_url("https://solaceagi.com/register")

    close_after_register = _request("/api/v1/browser/close", method="POST", payload={"all": True})
    _wait_for_no_browser()

    dashboard_launch = _request(
        "/api/v1/hub/browser/open",
        method="POST",
        payload={"url": "https://solaceagi.com/dashboard", "profile": "default", "mode": "standard"},
    )
    dashboard_status = _wait_for_browser_url("https://solaceagi.com/dashboard")

    screenshot = _request(
        "/api/screenshot",
        method="POST",
        payload={"filename": f"hub-first-run-{int(time.time())}.png"},
    )

    return {
        "runtime": runtime,
        "close_before": close_before,
        "zero_state": zero_state,
        "onboarding_before": onboarding_before,
        "onboarding_page_contains_modes": all(
            marker in onboarding_html
            for marker in ("AI Agent (Managed LLM)", "BYOK (Bring Your Own Key)", "Pro / Team", "Auto CLI")
        ),
        "agent_setup": agent_setup,
        "onboarding_after": onboarding_after,
        "register_launch": register_launch,
        "register_status": register_status,
        "close_after_register": close_after_register,
        "dashboard_launch": dashboard_launch,
        "dashboard_status": dashboard_status,
        "screenshot": screenshot,
    }


def main() -> int:
    result = run_rehearsal()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACTS_DIR / f"hub-first-run-rehearsal-{int(time.time())}.json"
    artifact_path.write_text(json.dumps(result, indent=2))
    print(json.dumps({"artifact": str(artifact_path), "ok": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
