from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_parser import RecipeParseError, parse


def test_parse_rejects_cycle_loop() -> None:
    recipe = """
stateDiagram-v2
  [*] --> A
  A --> B: x
  B --> A: y
  B --> [*]: done
""".strip()

    with pytest.raises(RecipeParseError):
        parse(recipe, recipe_id="loop")


def test_parse_rejects_unreachable_state() -> None:
    recipe = """
stateDiagram-v2
  [*] --> A
  A --> [*]: done
  C --> [*]: orphan
""".strip()

    with pytest.raises(RecipeParseError):
        parse(recipe, recipe_id="unreachable")
