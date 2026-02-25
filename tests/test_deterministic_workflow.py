from __future__ import annotations

import json
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cli.cli import SolaceCLI


def _run_once(root: Path, seed: int) -> dict:
    cli = SolaceCLI(solace_home=root)
    cli.init()

    recipe_rel = "inbox/recipe_inputs/replay.recipe.json"
    recipe_file = root / recipe_rel
    recipe_file.parent.mkdir(parents=True, exist_ok=True)
    recipe_file.write_text(json.dumps({"name": "replay-demo", "steps": ["A", "B", "C"]}), encoding="utf-8")

    cli.auth_login(password="deterministic-pass", ttl_seconds=1800)
    cli.recipe_submit(recipe_rel, password="deterministic-pass")
    return cli.recipe_run("replay-demo", password="deterministic-pass", seed=seed)


def test_three_replays_identical_with_same_seed(tmp_path: Path) -> None:
    run1 = _run_once(tmp_path / "r1", 777)
    run2 = _run_once(tmp_path / "r2", 777)
    run3 = _run_once(tmp_path / "r3", 777)

    assert run1 == run2 == run3
    assert run1["status"] == "success"
