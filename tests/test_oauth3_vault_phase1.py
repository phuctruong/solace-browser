from __future__ import annotations

from pathlib import Path

import pytest

from oauth3.evidence import EvidenceChain
from oauth3.vault import (
    OAuth3Vault,
    ScopeViolationError,
    TokenNotFoundError,
    TokenValidationError,
)


def _vault(tmp_path: Path) -> OAuth3Vault:
    evidence_log = tmp_path / "oauth3_audit.jsonl"
    chain = EvidenceChain(evidence_log)
    return OAuth3Vault(evidence_chain=chain)


def test_issue_and_verify_roundtrip(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token_id = vault.issue_token("user:test", ["linkedin.read.feed"], expires_in=1800)

    payload = vault.verify_token(token_id)

    assert payload["token_id"] == token_id
    assert payload["subject"] == "user:test"
    assert "linkedin.read.feed" in payload["scopes"]


def test_revoke_then_verify_fails(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token_id = vault.issue_token("user:test", ["linkedin.read.feed"], expires_in=1800)

    vault.revoke_token(token_id)

    with pytest.raises(TokenValidationError):
        vault.verify_token(token_id)


def test_require_scopes_blocks_missing_scope(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token_id = vault.issue_token("user:test", ["linkedin.read.feed"], expires_in=1800)

    with pytest.raises(ScopeViolationError):
        vault.require_scopes(token_id, ["linkedin.post.text"])


def test_require_scopes_blocks_high_risk_without_step_up(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token_id = vault.issue_token("user:test", ["linkedin.post.text"], expires_in=1800)

    with pytest.raises(ScopeViolationError, match="step_up_required"):
        vault.require_scopes(token_id, ["linkedin.post.text"], step_up_confirmed=False)


def test_evidence_chain_verifies_after_lifecycle(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    token_id = vault.issue_token("user:test", ["linkedin.read.feed"], expires_in=1800)
    vault.verify_token(token_id)
    vault.revoke_token(token_id)

    ok, reason = vault.evidence.verify_chain()
    assert ok is True
    assert reason is None
