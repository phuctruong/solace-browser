from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_parser import RecipeParseError, RecipeValidationError, parse_deterministic


def test_missing_required_field_raises_validation_error(tmp_path: Path) -> None:
    path = tmp_path / "missing-id.json"
    path.write_text(
        json.dumps(
            {
                "platform": "demo",
                "oauth3_scopes": ["browser.navigate"],
                "steps": [{"step": 1, "action": "navigate", "target": "https://example.com"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RecipeValidationError):
        parse_deterministic(path)


def test_invalid_json_raises_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(RecipeParseError):
        parse_deterministic(path)


def test_circular_dependency_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "cycle.json"
    path.write_text(
        json.dumps(
            {
                "id": "cycle-demo",
                "platform": "demo",
                "oauth3_scopes": ["browser.navigate"],
                "mermaid_fsm": (
                    "stateDiagram-v2\n"
                    "  [*] --> A\n"
                    "  A --> B: action_ok\n"
                    "  B --> A: retry\n"
                    "  B --> [*]: done\n"
                ),
                "steps": [
                    {"step": 1, "action": "navigate", "target": "https://example.com"},
                    {"step": 2, "action": "verify", "selector": "body"},
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RecipeValidationError):
        parse_deterministic(path)


def test_empty_recipe_file_raises_specific_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text("", encoding="utf-8")

    with pytest.raises(RecipeParseError):
        parse_deterministic(path)


def test_unknown_action_type_raises_specific_error(tmp_path: Path) -> None:
    path = tmp_path / "unknown-action.json"
    path.write_text(
        json.dumps(
            {
                "id": "unknown-action",
                "platform": "demo",
                "oauth3_scopes": ["browser.navigate"],
                "steps": [{"step": 1, "action": "teleport", "target": "https://example.com"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RecipeValidationError):
        parse_deterministic(path)
