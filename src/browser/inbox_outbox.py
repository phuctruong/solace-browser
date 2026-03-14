# Diagram: 01-triangle-architecture
"""Inbox/outbox filesystem contract for Solace apps."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


INBOX_TYPES: tuple[str, ...] = (
    "prompts",
    "templates",
    "assets",
    "policies",
    "datasets",
    "requests",
)
OUTBOX_TYPES: tuple[str, ...] = (
    "previews",
    "drafts",
    "reports",
    "suggestions",
    "runs",
)
REQUIRED_DIAGRAMS: tuple[str, ...] = (
    "workflow.md",
    "data-flow.md",
    "partner-contracts.md",
)
OUTBOX_STATUS_BY_TYPE: dict[str, str] = {
    "previews": "pending_approval",
    "drafts": "delivered",
    "reports": "delivered",
    "suggestions": "suggested",
    "runs": "sealed",
}


class InboxOutboxError(Exception):
    """Base exception for the inbox/outbox contract."""


class AppFolderNotFoundError(InboxOutboxError):
    """Raised when an app folder does not exist."""


class InboxOutboxValidationError(InboxOutboxError):
    """Raised when an app violates the required folder contract."""

    def __init__(self, app_id: str, missing: list[str]) -> None:
        self.app_id = app_id
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(f"App '{app_id}' is missing required files or folders: {joined}")


class InboxOutboxManager:
    """Read and validate app inbox/outbox folders."""

    def __init__(
        self,
        *,
        solace_home: str | Path | None = None,
        apps_root: str | Path | None = None,
    ) -> None:
        if apps_root is not None:
            self._apps_root = Path(apps_root).expanduser().resolve()
        else:
            home = Path(solace_home or "~/.solace").expanduser().resolve()
            self._apps_root = home / "apps"

    @property
    def apps_root(self) -> Path:
        return self._apps_root

    def resolve_app_root(self, app_id: str) -> Path:
        app_root = (self._apps_root / app_id).resolve()
        if not app_root.exists():
            raise AppFolderNotFoundError(f"App '{app_id}' does not exist under {self._apps_root}")
        if app_root.parent != self._apps_root:
            raise AppFolderNotFoundError(f"App '{app_id}' resolved outside {self._apps_root}")
        return app_root

    def read_manifest(self, app_id: str) -> dict[str, Any]:
        app_root = self.resolve_app_root(app_id)
        manifest_path = app_root / "manifest.yaml"
        if not manifest_path.exists():
            raise AppFolderNotFoundError(f"App '{app_id}' is missing manifest.yaml")
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    def read_budget(self, app_id: str) -> dict[str, Any]:
        app_root = self.resolve_app_root(app_id)
        budget_path = app_root / "budget.json"
        if not budget_path.exists():
            return {}
        payload = json.loads(budget_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    def write_budget(self, app_id: str, budget: dict[str, Any]) -> Path:
        app_root = self.resolve_app_root(app_id)
        budget_path = app_root / "budget.json"
        budget_path.write_text(json.dumps(budget, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return budget_path

    def list_inbox(self, app_id: str) -> dict[str, list[dict[str, Any]]]:
        app_root = self.resolve_app_root(app_id)
        inbox_root = app_root / "inbox"
        listing: dict[str, list[dict[str, Any]]] = {item: [] for item in INBOX_TYPES}
        for item in INBOX_TYPES:
            directory = inbox_root / item
            listing[item] = self._list_directory(directory, default_status="loaded")
        return listing

    def list_outbox(self, app_id: str) -> dict[str, list[dict[str, Any]]]:
        app_root = self.resolve_app_root(app_id)
        outbox_root = app_root / "outbox"
        listing: dict[str, list[dict[str, Any]]] = {item: [] for item in OUTBOX_TYPES}
        for item in OUTBOX_TYPES:
            directory = outbox_root / item
            listing[item] = self._list_directory(
                directory,
                default_status=OUTBOX_STATUS_BY_TYPE[item],
            )
        return listing

    def list_runs(self, app_id: str) -> list[dict[str, Any]]:
        app_root = self.resolve_app_root(app_id)
        runs_root = app_root / "outbox" / "runs"
        if not runs_root.exists():
            return []
        runs: list[dict[str, Any]] = []
        for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
            run_json = run_dir / "run.json"
            if run_json.exists():
                payload = json.loads(run_json.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    runs.append(payload)
                    continue
            runs.append(
                {
                    "run_id": run_dir.name,
                    "trigger": "manual",
                    "actions_summary": "",
                    "cost_usd": 0.0,
                    "state": "SEALED",
                    "created_at": self._isoformat(run_dir.stat().st_mtime),
                }
            )
        runs.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return runs

    def read_file(self, app_id: str, path: str) -> dict[str, Any]:
        app_root = self.resolve_app_root(app_id)
        candidate = (app_root / path).resolve()
        if app_root not in candidate.parents and candidate != app_root:
            raise InboxOutboxError(f"Path escapes app root: {path}")
        if not candidate.exists() or not candidate.is_file():
            raise FileNotFoundError(path)
        raw = candidate.read_bytes()
        return {
            "path": str(candidate.relative_to(app_root)),
            "content": raw.decode("utf-8"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        }

    def write_outbox(self, app_id: str, outbox_type: str, name: str, content: str) -> dict[str, Any]:
        if outbox_type not in OUTBOX_TYPES:
            raise InboxOutboxError(f"Invalid outbox type: {outbox_type}")
        if Path(name).name != name:
            raise InboxOutboxError(f"Outbox name must be a single file or folder name: {name}")
        app_root = self.resolve_app_root(app_id)
        target = app_root / "outbox" / outbox_type / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        relative_path = str(target.relative_to(app_root))
        self._update_outbox_manifest(app_root, relative_path, digest, target.stat().st_size)
        return {
            "path": str(target),
            "relative_path": relative_path,
            "sha256": digest,
            "size_bytes": target.stat().st_size,
        }

    def validate_inbox(self, app_id: str) -> dict[str, Any]:
        app_root = self.resolve_app_root(app_id)
        manifest = self.read_manifest(app_id)
        missing: list[str] = []
        for filename in ("manifest.yaml", "recipe.json", "budget.json"):
            if not (app_root / filename).exists():
                missing.append(filename)
        diagrams_root = app_root / "diagrams"
        if not diagrams_root.exists():
            missing.append("diagrams/")
        for name in REQUIRED_DIAGRAMS:
            if not (diagrams_root / name).exists():
                missing.append(f"diagrams/{name}")

        inbox_root = app_root / "inbox"
        outbox_root = app_root / "outbox"
        for item in INBOX_TYPES:
            if not (inbox_root / item).exists():
                missing.append(f"inbox/{item}/")
        conventions_root = inbox_root / "conventions"
        if not conventions_root.exists():
            missing.append("inbox/conventions/")
        if not (conventions_root / "examples").exists():
            missing.append("inbox/conventions/examples/")
        for item in OUTBOX_TYPES:
            if not (outbox_root / item).exists():
                missing.append(f"outbox/{item}/")

        required = manifest.get("required_inbox", {})
        if isinstance(required, dict):
            for item in INBOX_TYPES:
                required_names = required.get(item, [])
                if isinstance(required_names, list):
                    for name in required_names:
                        if not (inbox_root / item / str(name)).exists():
                            missing.append(f"inbox/{item}/{name}")
            conventions = required.get("conventions", {})
            if isinstance(conventions, dict):
                config_name = str(conventions.get("config", "config.yaml"))
                defaults_name = str(conventions.get("defaults", "defaults.yaml"))
                if not (conventions_root / config_name).exists():
                    missing.append(f"inbox/conventions/{config_name}")
                if not (conventions_root / defaults_name).exists():
                    missing.append(f"inbox/conventions/{defaults_name}")

        if missing:
            raise InboxOutboxValidationError(app_id, missing)
        return {"valid": True, "missing": []}

    def _list_directory(self, directory: Path, *, default_status: str) -> list[dict[str, Any]]:
        if not directory.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(directory.iterdir()):
            stat_result = path.stat()
            items.append(
                {
                    "name": path.name + ("/" if path.is_dir() else ""),
                    "status": default_status,
                    "size_bytes": 0 if path.is_dir() else stat_result.st_size,
                    "created_at": self._isoformat(stat_result.st_mtime),
                }
            )
        return items

    def _update_outbox_manifest(
        self,
        app_root: Path,
        relative_path: str,
        sha256: str,
        size_bytes: int,
    ) -> None:
        manifest_path = app_root / "outbox" / "manifest.json"
        if manifest_path.exists():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        else:
            payload = {}
        entries = payload.get("entries")
        if not isinstance(entries, dict):
            entries = {}
            payload["entries"] = entries
        entries[relative_path] = {
            "sha256": sha256,
            "size_bytes": size_bytes,
            "updated_at": self._isoformat(datetime.now(timezone.utc).timestamp()),
        }
        manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _isoformat(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
