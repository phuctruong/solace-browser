from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_compiler import compile
from recipes.recipe_parser import parse


RECIPE = """
stateDiagram-v2
  [*] --> NavigateHome
  NavigateHome --> ClickCompose: action_ok
  ClickCompose --> FillRecipient: action_ok
  FillRecipient --> ScreenshotProof: action_ok
  ScreenshotProof --> VerifyPage: action_ok
  VerifyPage --> Complete: action_ok
  Complete --> [*]: done
""".strip()


def test_compiler_outputs_expected_ir_schema() -> None:
    ast = parse(RECIPE, recipe_id="compile-schema")
    ir = compile(ast, determinism_seed=65537).to_dict()

    assert ir["recipe_id"] == "compile-schema"
    assert ir["version"] == "1.0.0"
    assert ir["determinism_seed"] == 65537
    assert isinstance(ir["ir_hash"], str) and len(ir["ir_hash"]) == 64
    assert "browser.navigate" in ir["scopes_required"]
    assert "browser.click" in ir["scopes_required"]
    assert len(ir["steps"]) == 6

    first = ir["steps"][0]
    assert set(first.keys()) == {"step_id", "state", "action", "target", "params", "condition_next_state"}
