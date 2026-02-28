from __future__ import annotations

import dataclasses
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from oauth3.evidence import EvidenceChain
from oauth3.vault import OAuth3Vault, ScopeViolationError


def _vault(tmp_path: Path) -> OAuth3Vault:
    evidence_log = tmp_path / "oauth3_audit.jsonl"
    storage = tmp_path / "vault.tokens.enc.json"
    key = b"0" * 32
    chain = EvidenceChain(evidence_log)
    return OAuth3Vault(
        encryption_key=key,
        evidence_chain=chain,
        storage_path=storage,
    )


def test_token_issue(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)

    assert "token_id" in token
    assert token["scopes"] == ["gmail.read.inbox"]
    assert token["revoked"] is False


def test_token_validate_with_scope(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)

    assert vault.validate_token(token["token_id"], "gmail.read.inbox") is True


def test_token_validate_without_scope(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)

    assert vault.validate_token(token["token_id"], "gmail.send") is False


def test_token_revocation_blocks_three_checks(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)

    assert vault.validate_token(token["token_id"], "gmail.read.inbox") is True

    receipt = vault.revoke_token(token["token_id"])
    assert receipt["immediate"] is True

    assert vault.validate_token(token["token_id"], "gmail.read.inbox") is False
    assert vault.validate_token(token["token_id"], "gmail.read.inbox") is False
    assert vault.validate_token(token["token_id"], "gmail.read.inbox") is False


def test_token_expiration(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=-1)

    assert vault.validate_token(token["token_id"], "gmail.read.inbox") is False


def test_tokens_persist_and_reload(tmp_path: Path) -> None:
    key = b"1" * 32
    evidence_log = tmp_path / "oauth3_audit.jsonl"
    storage = tmp_path / "vault.tokens.enc.json"

    vault_a = OAuth3Vault(
        encryption_key=key,
        evidence_log=evidence_log,
        storage_path=storage,
    )
    issued = vault_a.issue_token("user:persist", ["gmail.read.inbox"], expires_in=3600)

    vault_b = OAuth3Vault(
        encryption_key=key,
        evidence_log=evidence_log,
        storage_path=storage,
    )
    loaded = vault_b.get_token(issued["token_id"])

    assert loaded["token_id"] == issued["token_id"]
    assert loaded["subject"] == "user:persist"
    assert loaded["scopes"] == ["gmail.read.inbox"]


def test_three_replay_consistency(tmp_path: Path) -> None:
    seed = 12345

    def run_scenario(round_id: int) -> tuple[bool, bool, bool]:
        random.seed(seed)
        vault = OAuth3Vault(
            encryption_key=b"2" * 32,
            evidence_log=tmp_path / f"replay_{round_id}.jsonl",
            storage_path=tmp_path / f"replay_{round_id}.enc.json",
        )
        token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)
        token_id = token["token_id"]
        return (
            vault.validate_token(token_id, "gmail.read.inbox"),
            vault.validate_token(token_id, "gmail.read.inbox"),
            vault.validate_token(token_id, "gmail.read.inbox"),
        )

    run1 = run_scenario(1)
    run2 = run_scenario(2)
    run3 = run_scenario(3)

    assert run1 == run2 == run3
    assert run1 == (True, True, True)


def test_evidence_chain_verifies_after_lifecycle(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)
    vault.validate_token(token["token_id"], "gmail.read.inbox")
    vault.revoke_token(token["token_id"])

    ok, reason = vault.evidence.verify_chain()
    assert ok is True
    assert reason is None


def test_expired_token_mid_action_fails_closed(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)
    token_id = token["token_id"]

    assert vault.validate_token(token_id, "gmail.read.inbox") is True

    stored = vault.store.get(token_id)
    assert stored is not None
    expired = dataclasses.replace(
        stored,
        expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
    )
    vault.store.add(expired)

    assert vault.validate_token(token_id, "gmail.read.inbox") is False


def test_revocation_during_execution_fails_closed(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)
    token_id = token["token_id"]

    assert vault.validate_token(token_id, "gmail.read.inbox") is True
    vault.revoke_token(token_id)

    assert vault.validate_token(token_id, "gmail.read.inbox") is False


def test_scope_escalation_attempt_is_blocked(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)

    with pytest.raises(ScopeViolationError, match="scope_denied"):
        vault.require_scopes(
            token["token_id"],
            ["gmail.read.inbox", "gmail.delete.email"],
            step_up_confirmed=True,
        )


def test_tampered_evidence_chain_is_rejected(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)
    vault.validate_token(token["token_id"], "gmail.read.inbox")

    lines = (tmp_path / "oauth3_audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines
    first = json.loads(lines[0])
    first["data"]["tampered"] = True
    lines[0] = json.dumps(first, sort_keys=True)
    (tmp_path / "oauth3_audit.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, reason = vault.evidence.verify_chain()
    assert ok is False
    assert reason is not None


def test_evidence_entries_include_previous_hash_field(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)
    vault.validate_token(token["token_id"], "gmail.read.inbox")

    lines = (tmp_path / "oauth3_audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines
    for line in lines:
        event = json.loads(line)
        assert "previous_hash" in event
        assert event["previous_hash"] == event["prev_hash"]
