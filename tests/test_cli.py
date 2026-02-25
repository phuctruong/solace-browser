from __future__ import annotations

import json
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cli.cli import SolaceCLI


def test_cli_init_login_submit_run_status(tmp_path: Path) -> None:
    workspace = tmp_path / ".solace"
    cli = SolaceCLI(solace_home=workspace)

    init_result = cli.init()
    assert Path(init_result["root"]) == workspace.resolve()

    recipe_rel = "inbox/recipe_inputs/demo.recipe.json"
    recipe_file = workspace / recipe_rel
    recipe_file.parent.mkdir(parents=True, exist_ok=True)
    recipe_file.write_text(json.dumps({"name": "demo", "steps": ["read", "write"]}), encoding="utf-8")

    login = cli.auth_login(password="phase15-password", ttl_seconds=900)
    assert login["status"] == "ok"

    submit = cli.recipe_submit(recipe_rel, password="phase15-password")
    assert submit["status"] == "submitted"
    assert submit["recipe_name"] == "demo"

    run = cli.recipe_run("demo", password="phase15-password", seed=42)
    assert run["status"] == "success"
    assert run["recipe_name"] == "demo"

    out_file = workspace / "outbox/recipe_outputs/demo.result.json"
    assert out_file.exists()

    status = cli.status(password="phase15-password")
    assert status["oauth3"]["token_present"] is True
    assert "fs.read" in status["oauth3"]["scopes"]
