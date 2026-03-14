# Diagram: 29-chromium-build-pipeline
#!/usr/bin/env python3
"""Run a local Solace Hub + Browser rehearsal against localhost:8888."""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:8888"
HOME = Path.home()
ARTIFACTS_DIR = HOME / ".solace" / "artifacts"
ONBOARDING_PATH = HOME / ".solace" / "onboarding.json"
DEMO_APP_ID_PATTERNS = (
    re.compile(r"^demo-rehearsal-\d+$"),
    re.compile(r"^brief-feed-\d+$"),
    re.compile(r"^configured-demo-\d+$"),
    re.compile(r"^market-scout-\d+$"),
    re.compile(r"^config-roundtrip-search(?:-[0-9a-f]+)?$"),
    re.compile(r"^launch-report-search(?:-[0-9a-f]+)?$"),
)
GOOGLE_STARTER_BUNDLE_IDS = {
    "competitor-watch",
    "google-search-mission",
    "google-search-trends",
}


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


def _wait_for_browser(timeout_seconds: float = 20.0) -> dict:
    deadline = time.time() + timeout_seconds
    last: dict = {}
    while time.time() < deadline:
        last = _request("/api/v1/browser/status")
        if int(last.get("tracked_session_count", 0)) > 0:
            return last
        time.sleep(0.5)
    raise RuntimeError(f"browser did not appear before timeout; last={last}")


def _wait_for_no_browser(timeout_seconds: float = 20.0) -> dict:
    deadline = time.time() + timeout_seconds
    last: dict = {}
    while time.time() < deadline:
        last = _request("/api/v1/browser/status")
        if int(last.get("tracked_session_count", 0)) == 0 and int(last.get("visible_window_count", 0)) == 0:
            return last
        time.sleep(0.5)
    raise RuntimeError(f"browser did not terminate before timeout; last={last}")


def _clear_onboarding() -> None:
    try:
        ONBOARDING_PATH.unlink()
    except FileNotFoundError:
        return


def _close_all_browser_sessions() -> dict:
    """Ensure the rehearsal starts from a clean browser state."""
    return _request("/api/v1/browser/close", method="POST", payload={"all": True})


def _list_domain_installed_apps(domain: str) -> list[dict]:
    payload = _request(f"/api/v1/apps/by-domain?domain={urllib.parse.quote(domain, safe='')}")
    installed = payload.get("installed_apps", [])
    if not isinstance(installed, list):
        return []
    return [entry for entry in installed if isinstance(entry, dict)]


def _delete_app(app_id: str) -> dict:
    return _request(f"/api/v1/apps/{urllib.parse.quote(app_id, safe='')}", method="DELETE")


def _purge_demo_apps(domain: str = "google.com") -> list[dict]:
    removed: list[dict] = []
    for app in _list_domain_installed_apps(domain):
        app_id = str(app.get("id", "")).strip()
        if not app_id:
            continue
        should_delete = any(pattern.fullmatch(app_id) for pattern in DEMO_APP_ID_PATTERNS)
        if domain == "google.com" and app_id not in GOOGLE_STARTER_BUNDLE_IDS:
            should_delete = True
        if not should_delete:
            continue
        removed.append(_delete_app(app_id))
    return removed


def run_rehearsal(*, fresh: bool) -> dict:
    if fresh:
        _clear_onboarding()

    status = _request("/api/status")
    if status.get("status") != "ok":
        raise RuntimeError(f"runtime unhealthy: {status}")

    close_result = _close_all_browser_sessions()
    zero_status = _wait_for_no_browser()
    purged_apps = _purge_demo_apps()

    launch = _request("/api/v1/browser/launch", method="POST", payload={"url": "https://solaceagi.com/dashboard"})
    browser_status = _wait_for_browser()

    app_name = f"Demo Rehearsal {int(time.time())}"
    created = _request(
        "/api/v1/apps/custom/create",
        method="POST",
        payload={
            "domain": "google.com",
            "app_name": app_name,
            "description": "Create a custom local research app for the investor demo.",
        },
    )
    app_id = str(created["app_id"])

    config = _request(
        f"/api/v1/apps/{app_id}/config",
        method="POST",
        payload={
            "objective": "Track startup and investor signals and feed them into Morning Brief.",
            "target_url": "https://www.google.com/search?q=solace+agi+agents",
            "cron": "0 7 * * *",
            "keepalive_minutes": 30,
        },
    )

    schedule = _request(
        "/api/v1/browser/schedules",
        method="POST",
        payload={
            "app_id": app_id,
            "cron": "0 7 * * *",
            "url": "https://www.google.com/search?q=solace+agi+agents",
        },
    )

    custom_launch = _request(f"/api/v1/apps/{app_id}/launch", method="POST", payload={})
    brief_launch = _request("/api/v1/apps/morning-brief/launch", method="POST", payload={})
    brief_html = _get_text("/apps/morning-brief/outbox/reports/today.html")
    screenshot = _request("/api/screenshot", method="POST", payload={"filename": f"demo-rehearsal-{int(time.time())}.png"})

    if app_name not in brief_html:
        raise RuntimeError("Morning Brief did not include the custom app")
    if custom_launch.get("report_url", "") not in brief_html:
        raise RuntimeError("Morning Brief did not include the custom app report link")

    return {
        "runtime_status": status,
        "cleanup_before_launch": close_result,
        "cleanup_zero_status": zero_status,
        "purged_demo_apps": purged_apps,
        "browser_launch": launch,
        "browser_status": browser_status,
        "custom_app": created,
        "config_save": config,
        "schedule_create": schedule,
        "custom_launch": custom_launch,
        "morning_brief_launch": brief_launch,
        "morning_brief_contains_app": app_name in brief_html,
        "morning_brief_contains_report": custom_launch.get("report_url", "") in brief_html,
        "screenshot": screenshot,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh", action="store_true", help="Clear onboarding.json before the rehearsal.")
    args = parser.parse_args()

    result = run_rehearsal(fresh=args.fresh)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACTS_DIR / f"demo-rehearsal-{int(time.time())}.json"
    artifact_path.write_text(json.dumps(result, indent=2))
    print(json.dumps({"artifact": str(artifact_path), "ok": True, "custom_app": result["custom_app"]["app_id"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
