"""Local cache for recipes fetched from Stillwater Store."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from typing import Any, Dict

from cli.init_workspace import resolve_solace_home


class StoreRecipeCache:
    def __init__(self, cache_root: str | Path | None = None) -> None:
        if cache_root is None:
            cache_root = resolve_solace_home() / "vault" / "store_cache"
        self.cache_root = Path(cache_root).expanduser().resolve()
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def cache_recipe(self, recipe_id: str, version: str, recipe_ir: Dict[str, Any]) -> Path:
        path = self._recipe_path(recipe_id, version)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "schema_version": "1.0.0",
            "recipe_id": recipe_id,
            "version": version,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "recipe_ir": recipe_ir,
        }
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return path

    def get_cached_recipe(self, recipe_id: str, version: str) -> Dict[str, Any] | None:
        path = self._recipe_path(recipe_id, version)
        if not path.exists():
            self.misses += 1
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        self.hits += 1
        return dict(payload.get("recipe_ir") or {})

    def is_cache_stale(self, recipe_id: str, version: str, max_age_hours: int = 24) -> bool:
        path = self._recipe_path(recipe_id, version)
        if not path.exists():
            return True

        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age = datetime.now(timezone.utc) - modified
        return age > timedelta(hours=max_age_hours)

    def hit_rate(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def stats(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate(),
        }

    def _recipe_path(self, recipe_id: str, version: str) -> Path:
        safe_id = recipe_id.strip().replace("/", "_")
        safe_version = version.strip().replace("/", "_")
        return self.cache_root / safe_id / f"{safe_version}.json"
