from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_readme_quick_start_is_hub_first() -> None:
    readme = _read("README.md")

    assert "Solace Hub starts first" in readme
    assert "curl http://127.0.0.1:8888/api/status" in readme
    assert "systemctl --user start yinyang" not in readme


def test_hub_docs_keep_hub_first_8888_contract() -> None:
    hub_readme = _read("solace-hub/README.md")
    start_script = _read("scripts/start-hub.sh")

    assert "localhost:8888" in hub_readme
    assert "/api/status" in hub_readme
    assert "Solace Hub starts first" in hub_readme
    assert "9222" not in hub_readme
    assert "Solace Hub starts first" in start_script
    assert "env -i" in start_script
