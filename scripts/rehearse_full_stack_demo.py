#!/usr/bin/env python3
"""Run the full Solace presentation rehearsal: Hub first-run, local Browser, and paid cloud."""

from __future__ import annotations

import json
import time
from pathlib import Path

import rehearse_hub_first_run
import rehearse_local_demo
import rehearse_paid_cloud_demo


ARTIFACTS_DIR = Path.home() / ".solace" / "artifacts"


def run_rehearsal() -> dict:
    hub_first_run = rehearse_hub_first_run.run_rehearsal()
    local_demo = rehearse_local_demo.run_rehearsal(fresh=False)
    paid_cloud = rehearse_paid_cloud_demo.run_rehearsal()
    return {
        "hub_first_run": hub_first_run,
        "local_demo": local_demo,
        "paid_cloud": paid_cloud,
        "summary": {
            "hub_onboarding_complete": hub_first_run["onboarding_after"].get("completed") is True,
            "local_custom_app": local_demo["custom_app"].get("app_id"),
            "morning_brief_contains_app": local_demo.get("morning_brief_contains_app") is True,
            "billing_plan": paid_cloud["billing_subscription"].get("plan"),
            "stillwater_render_ok": paid_cloud["stillwater"].get("render_contains_title") is True,
            "twin_terminated": paid_cloud["twin_delete"].get("terminated") is True,
        },
    }


def main() -> int:
    result = run_rehearsal()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACTS_DIR / f"full-stack-demo-rehearsal-{int(time.time())}.json"
    artifact_path.write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {
                "artifact": str(artifact_path),
                "ok": True,
                "local_custom_app": result["summary"]["local_custom_app"],
                "billing_plan": result["summary"]["billing_plan"],
                "stillwater_render_ok": result["summary"]["stillwater_render_ok"],
                "twin_terminated": result["summary"]["twin_terminated"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
