from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "init_apps.py"
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inbox_outbox import InboxOutboxManager


def _load_script_module():
    spec = importlib.util.spec_from_file_location("init_apps_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_default_app_templates_exist() -> None:
    default_root = REPO_ROOT / "data" / "default" / "apps"
    assert default_root.exists()
    directories = sorted(path.name for path in default_root.iterdir() if path.is_dir())
    assert len(directories) == 22
    assert "morning-brief" in directories
    assert "linkedin-poster" in directories


def test_init_apps_creates_18_day_one_apps(tmp_path: Path) -> None:
    module = _load_script_module()
    default_root = tmp_path / "default-apps"
    solace_home = tmp_path / "solace-home"

    module.write_default_app_library(default_root)
    module.initialize_solace_home(solace_home=solace_home, library_root=default_root)

    app_dirs = sorted(path.name for path in (solace_home / "apps").iterdir() if path.is_dir())
    assert len(app_dirs) == 18
    assert app_dirs[0] == "amazon-price-tracker"


def test_all_generated_apps_pass_validate_inbox(tmp_path: Path) -> None:
    module = _load_script_module()
    default_root = tmp_path / "default-apps"
    solace_home = tmp_path / "solace-home"

    module.write_default_app_library(default_root)
    module.initialize_solace_home(solace_home=solace_home, library_root=default_root)

    manager = InboxOutboxManager(solace_home=solace_home)
    for app_root in sorted((solace_home / "apps").iterdir()):
        result = manager.validate_inbox(app_root.name)
        assert result["valid"] is True


def test_orchestrator_manifest_contains_cross_app_wiring(tmp_path: Path) -> None:
    module = _load_script_module()
    default_root = tmp_path / "default-apps"

    module.write_default_app_library(default_root)

    manifest_path = default_root / "morning-brief" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["type"] == "orchestrator"
    assert manifest["orchestrates"] == [
        "gmail-inbox-triage",
        "calendar-brief",
        "github-issue-triage",
        "slack-triage",
    ]
    assert manifest["partners"]["produces_for"] == []


def test_diagrams_are_mermaid_markdown(tmp_path: Path) -> None:
    module = _load_script_module()
    default_root = tmp_path / "default-apps"

    module.write_default_app_library(default_root)

    diagram = (default_root / "lead-pipeline" / "diagrams" / "workflow.md").read_text(encoding="utf-8")
    assert "```mermaid" in diagram
