from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cli.credential_vault import CredentialAuthError, CredentialVault


def test_credential_vault_encrypts_and_decrypts(tmp_path: Path) -> None:
    vault = CredentialVault(tmp_path / "config")

    payload = {
        "oauth3_token": "token_abc",
        "api_keys": {"stillwater": "sw_sk_123"},
    }
    vault.save_credentials("correct-horse", payload)

    encrypted = vault.credentials_file.read_text(encoding="utf-8")
    assert "token_abc" not in encrypted
    assert "sw_sk_123" not in encrypted

    loaded = vault.load_credentials("correct-horse")
    assert loaded == payload


def test_credential_vault_wrong_password_fails(tmp_path: Path) -> None:
    vault = CredentialVault(tmp_path / "config")
    vault.save_credentials("good-pass", {"oauth3_token": "token_abc"})

    with pytest.raises(CredentialAuthError):
        vault.load_credentials("bad-pass")
