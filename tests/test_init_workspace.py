from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cli.init_workspace import DEFAULT_LAYOUT, init_workspace


def test_init_workspace_creates_expected_layout(tmp_path: Path) -> None:
    root = tmp_path / ".solace"
    result = init_workspace(root)

    assert result["root"] == str(root.resolve())
    for rel in DEFAULT_LAYOUT:
        assert (root / rel).exists()

    assert (root / ".gitignore").exists()
    assert (root / "README.md").exists()


def test_init_workspace_idempotent(tmp_path: Path) -> None:
    root = tmp_path / ".solace"
    init_workspace(root)
    second = init_workspace(root)

    assert second["created"] == []
