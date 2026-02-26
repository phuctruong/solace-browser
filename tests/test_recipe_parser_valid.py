from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_parser import parse


VALID_RECIPE = """
stateDiagram-v2
  [*] --> NavigateHome
  NavigateHome --> ClickCompose: action_ok
  ClickCompose --> FillRecipient: action_ok
  FillRecipient --> ScreenshotProof: action_ok
  ScreenshotProof --> VerifyPage: action_ok
  VerifyPage --> Complete: action_ok
  Complete --> [*]: done
""".strip()


def test_parse_valid_mermaid_recipe() -> None:
    ast = parse(VALID_RECIPE, recipe_id="valid-demo")

    assert ast.recipe_id == "valid-demo"
    assert ast.initial_state == "NavigateHome"
    assert len(ast.states) == 6
    assert len(ast.transitions) == 7
