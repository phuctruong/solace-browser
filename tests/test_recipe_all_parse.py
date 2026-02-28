from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_parser import parse_deterministic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECIPES_ROOT = PROJECT_ROOT / "data" / "default" / "recipes"


def _json_recipe_files() -> list[Path]:
    return sorted(RECIPES_ROOT.rglob("*.json"))


def test_all_70_json_recipes_parse() -> None:
    files = _json_recipe_files()

    assert len(files) == 70
    for path in files:
        dag, dag_hash = parse_deterministic(path)
        assert dag.recipe_id
        assert len(dag_hash) == 64


def test_every_parsed_recipe_has_steps_and_scopes() -> None:
    for path in _json_recipe_files():
        dag, _ = parse_deterministic(path)
        assert dag.steps, f"{path} normalized to empty steps"
        assert dag.scopes, f"{path} normalized to empty scopes"


def test_no_recipe_has_empty_steps_list() -> None:
    for path in _json_recipe_files():
        dag, _ = parse_deterministic(path)
        assert len(dag.steps) > 0, f"{path} has no steps after normalization"
