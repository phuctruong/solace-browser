from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_cache import RecipeCache


def test_recipe_cache_hit_returns_cached_result(tmp_path: Path) -> None:
    cache = RecipeCache(cache_dir=tmp_path / "cache")

    recipe_ir = {"recipe_id": "r1", "steps": [{"step_id": "s1"}]}
    inputs = {"seed": 1}
    key = cache.cache_key(recipe_ir, inputs)

    cache.save_result(key, {"status": "success", "output": {"x": 1}})
    cached = cache.get_result(key)

    assert cached is not None
    assert cached["output"]["x"] == 1
    assert cache.stats()["hits"] == 1
    stats = cache.cache_stats()
    assert stats.hit_count == 1
    assert stats.miss_count == 0
