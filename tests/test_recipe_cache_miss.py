from __future__ import annotations

import os
import sys
import time
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_cache import RecipeCache


def test_recipe_cache_miss_for_new_inputs_and_stale(tmp_path: Path) -> None:
    cache = RecipeCache(cache_dir=tmp_path / "cache")

    recipe_ir = {"recipe_id": "r1", "steps": [{"step_id": "s1"}]}
    key_a = cache.cache_key(recipe_ir, {"seed": 1})
    key_b = cache.cache_key(recipe_ir, {"seed": 2})

    cache.save_result(key_a, {"status": "success", "value": "A"})

    miss = cache.get_result(key_b)
    assert miss is None

    path_a = (tmp_path / "cache" / f"{key_a}.json")
    old = time.time() - (48 * 3600)
    os.utime(path_a, (old, old))

    assert cache.is_stale(key_a, max_age_hours=24) is True
    stale = cache.get_result(key_a, max_age_hours=24)
    assert stale is None
    assert cache.stats()["misses"] >= 2
