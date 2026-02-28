from __future__ import annotations

import json
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_parser import parse_deterministic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECIPES_ROOT = PROJECT_ROOT / "data" / "default" / "recipes"


def _write_recipe(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _sample_recipe_payload() -> dict[str, object]:
    return {
        "id": "deterministic-sample",
        "platform": "demo",
        "version": "1.0.0",
        "oauth3_scopes": ["browser.navigate"],
        "steps": [
            {"step": 1, "action": "navigate", "target": "https://example.com"},
            {"step": 2, "action": "verify", "selector": "h1"},
        ],
    }


def test_parse_same_recipe_three_times_same_hash(tmp_path: Path) -> None:
    recipe_path = _write_recipe(tmp_path / "recipe.json", _sample_recipe_payload())

    hashes = [parse_deterministic(recipe_path)[1] for _ in range(3)]

    assert hashes[0] == hashes[1] == hashes[2]


def test_parse_ten_corpus_recipes_produce_valid_dags() -> None:
    files = sorted(RECIPES_ROOT.rglob("*.json"))[:10]

    assert len(files) == 10
    for path in files:
        dag, dag_hash = parse_deterministic(path)
        assert dag.recipe_id
        assert dag.nodes
        assert dag.edges
        assert dag.steps
        assert dag.scopes
        assert len(dag_hash) == 64


def test_complex_mermaid_branches_are_deterministic(tmp_path: Path) -> None:
    recipe_path = _write_recipe(
        tmp_path / "branched.json",
        {
            "id": "branched-demo",
            "platform": "demo",
            "oauth3_scopes": ["browser.navigate", "browser.verify"],
            "mermaid_fsm": (
                "stateDiagram-v2\n"
                "  [*] --> OpenPage\n"
                "  OpenPage --> VerifyPage: action_ok\n"
                "  OpenPage --> FailSafe: retry\n"
                "  VerifyPage --> Complete: success\n"
                "  FailSafe --> Complete: recovered\n"
                "  Complete --> [*]: done\n"
            ),
            "steps": [
                {"step": 1, "action": "navigate", "target": "https://example.com"},
                {"step": 2, "action": "verify", "selector": "h1"},
                {"step": 3, "action": "noop"},
            ],
        },
    )

    dag_a, hash_a = parse_deterministic(recipe_path)
    dag_b, hash_b = parse_deterministic(recipe_path)

    assert dag_a.edges == dag_b.edges
    assert hash_a == hash_b


def test_whitespace_only_changes_keep_same_hash(tmp_path: Path) -> None:
    payload = _sample_recipe_payload()
    path_a = _write_recipe(tmp_path / "a.json", payload)
    path_b = tmp_path / "b.json"
    path_b.write_text(
        '{\n  "id": "deterministic-sample",\n  "platform": "demo",\n'
        '  "version": "1.0.0",\n  "oauth3_scopes": [ "browser.navigate" ],\n'
        '  "steps": [\n    { "step": 1, "action": "navigate", "target": "https://example.com" },\n'
        '    { "step": 2, "action": "verify", "selector": "h1" }\n  ]\n}\n',
        encoding="utf-8",
    )

    _, hash_a = parse_deterministic(path_a)
    _, hash_b = parse_deterministic(path_b)

    assert hash_a == hash_b


def test_unicode_recipe_parses_correctly(tmp_path: Path) -> None:
    recipe_path = _write_recipe(
        tmp_path / "unicode.json",
        {
            "id": "unicode-demo",
            "platform": "demo",
            "description": "Resume cafe workflow",
            "oauth3_scopes": ["browser.navigate"],
            "steps": [
                {
                    "step": 1,
                    "action": "navigate",
                    "target": "https://example.com/caf\u00e9",
                    "description": "Open cafe view",
                }
            ],
        },
    )

    dag, dag_hash = parse_deterministic(recipe_path)

    assert dag.recipe_id == "unicode-demo"
    assert dag.steps[0]["description"] == "Open cafe view"
    assert len(dag_hash) == 64
