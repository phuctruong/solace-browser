"""Workspace initialization for the ~/.solace contract."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List
import os


DEFAULT_LAYOUT = [
    "inbox/recipe_inputs",
    "inbox/user_uploads",
    "outbox/recipe_outputs",
    "outbox/audit_logs",
    "vault/search_index",
    "vault/timeline",
    "vault/semantic_memory",
    "config",
]


def resolve_solace_home(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser().resolve()

    env = os.environ.get("SOLACE_HOME")
    if env:
        return Path(env).expanduser().resolve()

    return (Path.home() / ".solace").resolve()


def init_workspace(path: str | Path | None = None) -> Dict[str, List[str]]:
    root = resolve_solace_home(path)
    root.mkdir(parents=True, exist_ok=True)

    created: List[str] = []
    for rel in DEFAULT_LAYOUT:
        d = root / rel
        if not d.exists():
            created.append(str(d.relative_to(root)))
        d.mkdir(parents=True, exist_ok=True)

    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# .solace workspace\n\n"
            "This directory stores inbox/outbox/vault/config for local agent workflows.\n",
            encoding="utf-8",
        )

    gitignore = root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "config/\n"
            "vault/*.enc.json\n"
            "*.bin\n"
            "*.png\n",
            encoding="utf-8",
        )

    return {
        "root": str(root),
        "created": created,
    }
