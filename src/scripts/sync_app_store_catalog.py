#!/usr/bin/env python3
"""Sync official git-backed app-store catalog from manifest files."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid manifest object: {path}")
    return payload


def _normalize_site(site: str) -> str:
    normalized = site.strip().lower()
    return normalized.replace("https://", "").replace("http://", "").rstrip("/")


def _entry_from_manifest(app_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(manifest.get("id", app_id)).strip() or app_id,
        "name": str(manifest.get("name", app_id)).strip() or app_id,
        "description": str(manifest.get("description", "")).strip(),
        "category": str(manifest.get("category", "uncategorized")).strip() or "uncategorized",
        "status": str(manifest.get("status", "available")).strip() or "available",
        "safety": str(manifest.get("safety", "A")).strip() or "A",
        "site": _normalize_site(str(manifest.get("site", ""))),
        "type": str(manifest.get("type", "standard")).strip() or "standard",
        "scopes": manifest.get("scopes", []) if isinstance(manifest.get("scopes"), list) else [],
        "source": "official_git",
    }


def build_catalog(default_apps_root: Path) -> dict[str, Any]:
    apps: list[dict[str, Any]] = []
    for app_root in sorted(default_apps_root.iterdir()):
        if not app_root.is_dir():
            continue
        manifest_path = app_root / "manifest.yaml"
        if not manifest_path.exists():
            continue
        manifest = _read_manifest(manifest_path)
        apps.append(_entry_from_manifest(app_root.name, manifest))
    apps.sort(key=lambda item: item["name"].lower())

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_mode": "git",
        "apps": apps,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["catalog_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync app-store official catalog from manifests")
    parser.add_argument("--apps-root", default="data/default/apps")
    parser.add_argument("--output", default="data/default/app-store/official-store.json")
    args = parser.parse_args()

    apps_root = Path(args.apps_root).resolve()
    output_path = Path(args.output).resolve()
    if not apps_root.exists():
        raise FileNotFoundError(f"Apps root does not exist: {apps_root}")

    catalog = build_catalog(apps_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote catalog: {output_path}")
    print(f"Apps: {len(catalog['apps'])}")
    print(f"Catalog SHA256: {catalog['catalog_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

