from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from fs_gateway import FSPathError, FilesystemGatewayService
from oauth3.vault import OAuth3Vault


def _make_vault(tmp_path: Path) -> OAuth3Vault:
    return OAuth3Vault(
        encryption_key=b"f" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "oauth3_tokens.enc.json",
    )


def test_fs_read_write_list_hash(tmp_path: Path) -> None:
    workspace = tmp_path / ".solace"
    vault = _make_vault(tmp_path)
    token = vault.issue_token(["fs.read", "fs.write", "fs.list", "fs.hash"], ttl_seconds=3600)

    proof_log = tmp_path / "fs_gateway_proof.jsonl"
    fs = FilesystemGatewayService(vault=vault, workspace_root=workspace, proof_log=proof_log)

    content = '{"name":"demo","version":1}'
    write_res = fs.write("inbox/recipe_inputs/demo.json", content, token["token_id"])
    read_res = fs.read("inbox/recipe_inputs/demo.json", token["token_id"])
    list_res = fs.list("inbox/recipe_inputs", token["token_id"])
    hash_res = fs.hash("inbox/recipe_inputs/demo.json", token["token_id"])

    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    assert write_res["hash"] == expected_hash
    assert read_res["hash"] == expected_hash
    assert hash_res["hash"] == expected_hash
    assert list_res["files"] == ["demo.json"]

    events = [json.loads(line) for line in proof_log.read_text(encoding="utf-8").splitlines()]
    assert [evt["event_type"] for evt in events] == ["FS_WRITE", "FS_READ", "FS_LIST", "FS_HASH"]


def test_fs_path_outside_workspace_is_denied(tmp_path: Path) -> None:
    workspace = tmp_path / ".solace"
    vault = _make_vault(tmp_path)
    token = vault.issue_token(["fs.read"], ttl_seconds=3600)

    fs = FilesystemGatewayService(vault=vault, workspace_root=workspace, proof_log=tmp_path / "proof.jsonl")

    with pytest.raises(FSPathError):
        fs.read("../outside.txt", token["token_id"])
