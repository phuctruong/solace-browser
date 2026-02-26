from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from store_client.recipe_cache import StoreRecipeCache


def test_store_recipe_cache_hit_and_stale_detection(tmp_path: Path) -> None:
    cache = StoreRecipeCache(cache_root=tmp_path / "store_cache")

    cache.cache_recipe("compose-email", "1.2.0", {"steps": [{"action": "navigate"}]})
    cached = cache.get_cached_recipe("compose-email", "1.2.0")
    assert cached is not None
    assert cached["steps"][0]["action"] == "navigate"

    p = tmp_path / "store_cache" / "compose-email" / "1.2.0.json"
    old = time.time() - (48 * 3600)
    os.utime(p, (old, old))

    assert cache.is_cache_stale("compose-email", "1.2.0", max_age_hours=24) is True
    miss = cache.get_cached_recipe("compose-email", "2.0.0")
    assert miss is None
    assert cache.stats()["hit_rate"] >= 0.5
