from __future__ import annotations

import json
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cli.cli import SolaceCLI


def test_cli_recipe_workflow_produces_output_artifact(tmp_path: Path) -> None:
    workspace = tmp_path / ".solace"
    cli = SolaceCLI(solace_home=workspace)
    cli.init()
    cli.auth_login(password="workflow-pass")

    recipe_rel = "inbox/recipe_inputs/workflow.json"
    (workspace / recipe_rel).parent.mkdir(parents=True, exist_ok=True)
    (workspace / recipe_rel).write_text(
        json.dumps({"name": "workflow-demo", "steps": ["collect", "emit"]}),
        encoding="utf-8",
    )

    cli.recipe_submit(recipe_rel, password="workflow-pass")
    result = cli.recipe_run("workflow-demo", password="workflow-pass", seed=9)

    assert result["status"] == "success"
    assert (workspace / "outbox/recipe_outputs/workflow-demo.result.json").exists()
