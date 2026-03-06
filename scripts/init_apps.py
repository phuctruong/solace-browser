#!/usr/bin/env python3
"""Create the 18 day-one app templates and install them into ~/.solace/apps."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SRC_ROOT))

from inbox_outbox import InboxOutboxManager


APP_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "gmail-inbox-triage",
        "name": "Gmail Inbox Triage",
        "description": "Scan Gmail, prioritize messages, and draft safe replies.",
        "category": "communications",
        "status": "installed",
        "safety": "B",
        "site": "mail.google.com",
        "type": "standard",
        "scopes": ["gmail.read.inbox", "gmail.draft.create", "local.evidence"],
        "produces_for": ["google-drive-saver", "slack-triage", "calendar-brief"],
        "consumes_from": ["morning-brief", "linkedin-outreach"],
    },
    {
        "id": "calendar-brief",
        "name": "Calendar Brief",
        "description": "Summarize the day and surface upcoming constraints.",
        "category": "productivity",
        "status": "installed",
        "safety": "A",
        "site": "calendar.google.com",
        "type": "standard",
        "scopes": ["calendar.read.events", "local.evidence"],
        "produces_for": ["morning-brief", "lead-pipeline"],
        "consumes_from": ["gmail-inbox-triage"],
    },
    {
        "id": "focus-timer",
        "name": "Focus Timer",
        "description": "Run local focus sessions and produce lightweight reports.",
        "category": "productivity",
        "status": "installed",
        "safety": "A",
        "site": "local-machine",
        "type": "standard",
        "scopes": ["machine.read.clock", "local.evidence"],
        "produces_for": ["weekly-digest"],
        "consumes_from": [],
    },
    {
        "id": "github-issue-triage",
        "name": "GitHub Issue Triage",
        "description": "Review issues, classify urgency, and prepare follow-up drafts.",
        "category": "engineering",
        "status": "installed",
        "safety": "B",
        "site": "github.com",
        "type": "standard",
        "scopes": ["github.read.issues", "github.write.drafts", "local.evidence"],
        "produces_for": ["slack-triage", "morning-brief"],
        "consumes_from": ["weekly-digest"],
    },
    {
        "id": "slack-triage",
        "name": "Slack Triage",
        "description": "Summarize channels, draft responses, and escalate urgent items.",
        "category": "communications",
        "status": "installed",
        "safety": "B",
        "site": "app.slack.com",
        "type": "standard",
        "scopes": ["slack.read.channels", "slack.write.drafts", "local.evidence"],
        "produces_for": ["morning-brief"],
        "consumes_from": ["gmail-inbox-triage", "github-issue-triage"],
    },
    {
        "id": "linkedin-outreach",
        "name": "LinkedIn Outreach",
        "description": "Draft outreach sequences and manage lead handoff safely.",
        "category": "sales",
        "status": "installed",
        "safety": "C",
        "site": "linkedin.com",
        "type": "standard",
        "scopes": ["linkedin.read.profile", "linkedin.write.drafts", "local.evidence"],
        "produces_for": ["gmail-inbox-triage", "lead-pipeline"],
        "consumes_from": ["lead-pipeline"],
    },
    {
        "id": "google-drive-saver",
        "name": "Google Drive Saver",
        "description": "Save approved artifacts into Drive using the web UI.",
        "category": "productivity",
        "status": "installed",
        "safety": "A",
        "site": "drive.google.com",
        "type": "standard",
        "scopes": ["drive.read.files", "drive.write.files", "local.evidence"],
        "produces_for": [],
        "consumes_from": ["gmail-inbox-triage", "youtube-script-writer"],
    },
    {
        "id": "youtube-script-writer",
        "name": "YouTube Script Writer",
        "description": "Draft scripts from source notes and hand them to downstream apps.",
        "category": "sales",
        "status": "installed",
        "safety": "B",
        "site": "studio.youtube.com",
        "type": "standard",
        "scopes": ["youtube.read.channel", "youtube.write.drafts", "local.evidence"],
        "produces_for": ["google-drive-saver", "twitter-monitor"],
        "consumes_from": ["weekly-digest"],
    },
    {
        "id": "twitter-monitor",
        "name": "Twitter Monitor",
        "description": "Watch timelines and produce read-only summaries.",
        "category": "social",
        "status": "installed",
        "safety": "A",
        "site": "x.com",
        "type": "standard",
        "scopes": ["twitter.read.timeline", "local.evidence"],
        "produces_for": ["morning-brief"],
        "consumes_from": [],
    },
    {
        "id": "reddit-scanner",
        "name": "Reddit Scanner",
        "description": "Scan communities and surface relevant discussions.",
        "category": "engineering",
        "status": "installed",
        "safety": "A",
        "site": "reddit.com",
        "type": "standard",
        "scopes": ["reddit.read.posts", "local.evidence"],
        "produces_for": ["morning-brief"],
        "consumes_from": [],
    },
    {
        "id": "whatsapp-responder",
        "name": "WhatsApp Responder",
        "description": "Prepare responses in WhatsApp Web with explicit approval.",
        "category": "communications",
        "status": "installed",
        "safety": "C",
        "site": "web.whatsapp.com",
        "type": "standard",
        "scopes": ["whatsapp.read.messages", "whatsapp.write.drafts", "local.evidence"],
        "produces_for": [],
        "consumes_from": ["morning-brief"],
    },
    {
        "id": "amazon-price-tracker",
        "name": "Amazon Price Tracker",
        "description": "Monitor wishlist prices through the consumer web UI.",
        "category": "shopping",
        "status": "installed",
        "safety": "A",
        "site": "amazon.com",
        "type": "standard",
        "scopes": ["amazon.read.product", "local.evidence"],
        "produces_for": ["weekly-digest"],
        "consumes_from": [],
    },
    {
        "id": "instagram-poster",
        "name": "Instagram Poster",
        "description": "Draft and publish Instagram posts after approval.",
        "category": "social",
        "status": "installed",
        "safety": "C",
        "site": "instagram.com",
        "type": "standard",
        "scopes": ["instagram.read.feed", "instagram.write.posts", "local.evidence"],
        "produces_for": [],
        "consumes_from": ["weekly-digest"],
    },
    {
        "id": "twitter-poster",
        "name": "Twitter Poster",
        "description": "Queue tweets and threads without relying on the paid API.",
        "category": "social",
        "status": "installed",
        "safety": "C",
        "site": "x.com",
        "type": "standard",
        "scopes": ["twitter.read.timeline", "twitter.write.posts", "local.evidence"],
        "produces_for": [],
        "consumes_from": ["youtube-script-writer", "weekly-digest"],
    },
    {
        "id": "linkedin-poster",
        "name": "LinkedIn Poster",
        "description": "Draft and publish LinkedIn posts through the native web UI.",
        "category": "social",
        "status": "installed",
        "safety": "C",
        "site": "linkedin.com",
        "type": "standard",
        "scopes": ["linkedin.read.profile", "linkedin.write.posts", "local.evidence"],
        "produces_for": [],
        "consumes_from": ["weekly-digest", "lead-pipeline"],
    },
    {
        "id": "morning-brief",
        "name": "Morning Brief",
        "description": "Orchestrate the daily cross-app brief.",
        "category": "productivity",
        "status": "installed",
        "safety": "A",
        "site": "multi-site",
        "type": "orchestrator",
        "orchestrates": ["gmail-inbox-triage", "calendar-brief", "github-issue-triage", "slack-triage"],
        "scopes": ["local.evidence"],
        "produces_for": [],
        "consumes_from": ["gmail-inbox-triage", "calendar-brief", "github-issue-triage", "slack-triage", "twitter-monitor", "reddit-scanner"],
    },
    {
        "id": "weekly-digest",
        "name": "Weekly Digest",
        "description": "Collect five days of reports and synthesize one weekly view.",
        "category": "productivity",
        "status": "installed",
        "safety": "A",
        "site": "multi-site",
        "type": "orchestrator",
        "orchestrates": ["morning-brief", "focus-timer", "amazon-price-tracker", "youtube-script-writer"],
        "scopes": ["local.evidence"],
        "produces_for": [],
        "consumes_from": ["morning-brief", "focus-timer", "amazon-price-tracker", "youtube-script-writer"],
    },
    {
        "id": "lead-pipeline",
        "name": "Lead Pipeline",
        "description": "Coordinate outreach, email follow-up, and schedule matching.",
        "category": "sales",
        "status": "installed",
        "safety": "A",
        "site": "multi-site",
        "type": "orchestrator",
        "orchestrates": ["linkedin-outreach", "gmail-inbox-triage", "calendar-brief"],
        "scopes": ["local.evidence"],
        "produces_for": [],
        "consumes_from": ["linkedin-outreach", "gmail-inbox-triage", "calendar-brief"],
    },
]


def build_manifest(app: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": app["id"],
        "name": app["name"],
        "description": app["description"],
        "category": app["category"],
        "status": app["status"],
        "safety": app["safety"],
        "site": app["site"],
        "type": app["type"],
        "orchestrates": app.get("orchestrates", []),
        "scopes": app["scopes"],
        "partners": {
            "produces_for": app["produces_for"],
            "consumes_from": app["consumes_from"],
        },
        "required_inbox": {
            "prompts": [],
            "templates": [],
            "assets": [],
            "policies": [],
            "datasets": [],
            "requests": [],
            "conventions": {
                "config": "config.yaml",
                "defaults": "defaults.yaml",
            },
        },
    }


def _resolve_recipe_ref(app_id: str) -> str | None:
    """Find a matching platform recipe for a given app ID.

    Checks data/default/recipes/{platform}/ subdirectories and top-level
    recipe files for a match. Returns the recipe_ref path relative to the
    recipes root, or None if no match is found.
    """
    recipes_root = REPO_ROOT / "data" / "default" / "recipes"
    if not recipes_root.is_dir():
        return None

    # Import resolve logic from the runner to stay consistent
    # We do a simple direct check here to avoid circular imports.
    from apps.runner import APP_RECIPE_MAP

    mapped = APP_RECIPE_MAP.get(app_id)
    if mapped:
        platform_dir, recipe_file = mapped
        candidate = recipes_root / platform_dir / recipe_file
        if candidate.is_file():
            return f"{platform_dir}/{recipe_file}"
        candidate = recipes_root / recipe_file
        if candidate.is_file():
            return recipe_file

    return None


def build_recipe(app: dict[str, Any]) -> dict[str, Any]:
    recipe: dict[str, Any] = {
        "id": app["id"],
        "version": "1.0.0",
        "type": app["type"],
        "steps": [
            {
                "id": "preview",
                "action": "noop",
                "description": f"Preview {app['name']}",
            }
        ],
    }
    ref = _resolve_recipe_ref(app["id"])
    if ref:
        recipe["recipe_ref"] = ref
    return recipe


def build_budget(app: dict[str, Any]) -> dict[str, Any]:
    safety = app["safety"]
    remaining_runs = 200 if safety == "A" else 120 if safety == "B" else 60
    cooldown = 0 if safety == "A" else 5 if safety == "B" else 15
    return {
        "remaining_runs": remaining_runs,
        "cooldown_seconds": cooldown,
        "reads_per_run": 50,
        "drafts_per_run": 5 if safety != "A" else 0,
        "writes_per_run": 1 if safety == "C" else 0,
    }


def write_default_app_library(default_root: Path) -> None:
    default_root.mkdir(parents=True, exist_ok=True)
    for app in APP_DEFINITIONS:
        _write_app_directory(default_root / app["id"], app)


def initialize_solace_home(*, solace_home: Path, library_root: Path) -> None:
    apps_root = solace_home / "apps"
    apps_root.mkdir(parents=True, exist_ok=True)
    for source_root in sorted(path for path in library_root.iterdir() if path.is_dir()):
        target_root = apps_root / source_root.name
        if target_root.exists():
            shutil.rmtree(target_root)
        shutil.copytree(source_root, target_root)

    manager = InboxOutboxManager(solace_home=solace_home)
    for app in APP_DEFINITIONS:
        manager.validate_inbox(app["id"])


def _write_app_directory(app_root: Path, app: dict[str, Any]) -> None:
    if app_root.exists():
        shutil.rmtree(app_root)
    for path in [
        app_root / "diagrams",
        app_root / "inbox" / "prompts",
        app_root / "inbox" / "templates",
        app_root / "inbox" / "assets",
        app_root / "inbox" / "policies",
        app_root / "inbox" / "datasets",
        app_root / "inbox" / "requests",
        app_root / "inbox" / "conventions" / "examples",
        app_root / "outbox" / "previews",
        app_root / "outbox" / "drafts",
        app_root / "outbox" / "reports",
        app_root / "outbox" / "suggestions",
        app_root / "outbox" / "runs",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    (app_root / "manifest.yaml").write_text(yaml.safe_dump(build_manifest(app), sort_keys=False), encoding="utf-8")
    (app_root / "recipe.json").write_text(json.dumps(build_recipe(app), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (app_root / "budget.json").write_text(json.dumps(build_budget(app), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (app_root / "diagrams" / "workflow.md").write_text(_workflow_diagram(app), encoding="utf-8")
    (app_root / "diagrams" / "data-flow.md").write_text(_data_flow_diagram(app), encoding="utf-8")
    (app_root / "diagrams" / "partner-contracts.md").write_text(_partner_diagram(app), encoding="utf-8")
    (app_root / "inbox" / "conventions" / "config.yaml").write_text(
        yaml.safe_dump({"enabled": True, "window": "last_24_hours", "tone": "warm_friendly"}, sort_keys=False),
        encoding="utf-8",
    )
    (app_root / "inbox" / "conventions" / "defaults.yaml").write_text(
        yaml.safe_dump({"enabled": True, "window": "last_7_days", "tone": "neutral_professional"}, sort_keys=False),
        encoding="utf-8",
    )
    (app_root / "inbox" / "conventions" / "examples" / "README.md").write_text(
        f"# {app['name']} examples\n\nDrop app-specific examples here.\n",
        encoding="utf-8",
    )


def _workflow_diagram(app: dict[str, Any]) -> str:
    if app["type"] == "orchestrator":
        children = "\n".join(f"    TRIGGER --> {child.replace('-', '_')}[{child}]" for child in app.get("orchestrates", []))
        return (
            f"# Workflow — {app['name']}\n\n"
            "```mermaid\n"
            "flowchart TD\n"
            "    TRIGGER[Trigger]\n"
            f"{children}\n"
            "    COLLECT[Collect child reports]\n"
            "    COLLECT --> SYNTH[Synthesize one report]\n"
            "    SYNTH --> OUTBOX[outbox/reports/]\n"
            "```\n"
        )
    return (
        f"# Workflow — {app['name']}\n\n"
        "```mermaid\n"
        "flowchart TD\n"
        "    TRIGGER[Trigger] --> PREVIEW[Preview once]\n"
        "    PREVIEW --> APPROVAL[Approve or reject]\n"
        "    APPROVAL --> EXECUTE[Deterministic replay]\n"
        "    EXECUTE --> OUTBOX[outbox/reports/]\n"
        "```\n"
    )


def _data_flow_diagram(app: dict[str, Any]) -> str:
    return (
        f"# Data Flow — {app['name']}\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "    INBOX[inbox/] --> RECIPE[recipe.json]\n"
        "    RECIPE --> BUDGET[budget.json]\n"
        "    BUDGET --> OUTBOX[outbox/]\n"
        "    OUTBOX --> RUNS[outbox/runs/]\n"
        "```\n"
    )


def _partner_diagram(app: dict[str, Any]) -> str:
    produces = app["produces_for"] or ["none"]
    consumes = app["consumes_from"] or ["none"]
    produces_rows = "\n".join(f"    APP --> P_{idx}[{name}]" for idx, name in enumerate(produces, start=1))
    consumes_rows = "\n".join(f"    C_{idx}[{name}] --> APP" for idx, name in enumerate(consumes, start=1))
    return (
        f"# Partner Contracts — {app['name']}\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "    APP[" + app["id"] + "]\n"
        f"{produces_rows}\n"
        f"{consumes_rows}\n"
        "```\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--default-root",
        type=Path,
        default=REPO_ROOT / "data" / "default" / "apps",
        help="Directory that stores the committed app templates.",
    )
    parser.add_argument(
        "--solace-home",
        type=Path,
        default=Path("~/.solace").expanduser(),
        help="Solace home directory that receives ~/.solace/apps.",
    )
    parser.add_argument(
        "--library-only",
        action="store_true",
        help="Write data/default/apps only and skip ~/.solace/apps installation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_default_app_library(args.default_root)
    if not args.library_only:
        initialize_solace_home(solace_home=args.solace_home, library_root=args.default_root)


if __name__ == "__main__":
    main()
