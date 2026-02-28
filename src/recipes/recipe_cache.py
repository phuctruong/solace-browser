"""Deterministic recipe result cache for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from cli.init_workspace import resolve_solace_home


@dataclass(frozen=True)
class CacheStats:
    hit_count: int
    miss_count: int
    hit_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate": self.hit_rate,
        }


class RecipeCache:
    def __init__(self, cache_dir: str | Path | None = None) -> None:
        if cache_dir is None:
            cache_dir = resolve_solace_home() / "vault" / "recipe_cache"
        self.cache_dir = Path(cache_dir).expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def cache_key(self, recipe_ir: Dict[str, Any], inputs: Dict[str, Any]) -> str:
        payload = {
            "recipe_ir": recipe_ir,
            "inputs": inputs,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.md5(canonical.encode("utf-8")).hexdigest()

    def save_result(self, key: str, result: Dict[str, Any]) -> Path | None:
        if result.get("status") != "success":
            return None

        record = {
            "schema_version": "1.0.0",
            "cache_key": key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
        }
        path = self._path_for_key(key)
        path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        return path

    def get_result(self, key: str, max_age_hours: int = 24) -> Dict[str, Any] | None:
        path = self._path_for_key(key)
        if not path.exists():
            self.misses += 1
            return None

        if self.is_stale(key, max_age_hours=max_age_hours):
            self.misses += 1
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        self.hits += 1
        return payload.get("result")

    def is_stale(self, key: str, max_age_hours: int = 24) -> bool:
        path = self._path_for_key(key)
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

    def cache_stats(self) -> CacheStats:
        return CacheStats(
            hit_count=self.hits,
            miss_count=self.misses,
            hit_rate=self.hit_rate(),
        )

    def stats(self) -> Dict[str, Any]:
        return self.cache_stats().to_dict()

    def _path_for_key(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"
