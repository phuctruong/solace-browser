from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from fs_gateway import FSScopeError, FilesystemGatewayService
from oauth3.vault import OAuth3Vault


def _setup(tmp_path: Path) -> tuple[OAuth3Vault, FilesystemGatewayService]:
    vault = OAuth3Vault(
        encryption_key=b"g" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )
    fs = FilesystemGatewayService(
        vault=vault,
        workspace_root=tmp_path / ".solace",
        proof_log=tmp_path / "fs_proof.jsonl",
    )
    return vault, fs


def test_scope_gate_denies_missing_scope(tmp_path: Path) -> None:
    vault, fs = _setup(tmp_path)
    token = vault.issue_token(["fs.list"], ttl_seconds=3600)

    with pytest.raises(FSScopeError):
        fs.write("outbox/recipe_outputs/a.txt", "hello", token["token_id"])


def test_scope_gate_allows_with_granted_scope(tmp_path: Path) -> None:
    vault, fs = _setup(tmp_path)
    token = vault.issue_token(["fs.write", "fs.read"], ttl_seconds=3600)

    fs.write("outbox/recipe_outputs/a.txt", "hello", token["token_id"])
    loaded = fs.read("outbox/recipe_outputs/a.txt", token["token_id"])

    assert loaded["content"] == "hello"


def test_revoked_token_is_blocked_immediately(tmp_path: Path) -> None:
    vault, fs = _setup(tmp_path)
    token = vault.issue_token(["fs.write", "fs.read"], ttl_seconds=3600)

    fs.write("outbox/recipe_outputs/a.txt", "before", token["token_id"])
    vault.revoke_token(token["token_id"])

    with pytest.raises(FSScopeError):
        fs.read("outbox/recipe_outputs/a.txt", token["token_id"])
