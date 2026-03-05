"""Encrypted credential storage for Phase 1.5 CLI."""

from __future__ import annotations

import base64
import json
import secrets
from pathlib import Path
from typing import Any, Dict

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidTag


class CredentialVaultError(Exception):
    """Base credential vault error."""


class CredentialAuthError(CredentialVaultError):
    """Raised when password is wrong or payload is corrupted."""


class CredentialVault:
    def __init__(self, config_dir: str | Path) -> None:
        self.config_dir = Path(config_dir).expanduser().resolve()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_file = self.config_dir / "credentials.enc.json"
        self.salt_file = self.config_dir / "password_salt.bin"

    def save_credentials(self, password: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        salt = self._load_or_create_salt()
        key = self._derive_key(password, salt)
        nonce = secrets.token_bytes(12)

        plaintext = json.dumps(payload, sort_keys=True).encode("utf-8")
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)

        envelope = {
            "cipher": "AES-256-GCM",
            "nonce_b64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        }
        self.credentials_file.write_text(json.dumps(envelope, sort_keys=True), encoding="utf-8")

        return {
            "path": str(self.credentials_file),
            "bytes": self.credentials_file.stat().st_size,
        }

    def load_credentials(self, password: str) -> Dict[str, Any]:
        if not self.credentials_file.exists() or not self.salt_file.exists():
            raise CredentialVaultError("credentials not initialized")

        salt = self.salt_file.read_bytes()
        key = self._derive_key(password, salt)

        envelope = json.loads(self.credentials_file.read_text(encoding="utf-8"))
        nonce = base64.b64decode(envelope["nonce_b64"])
        ciphertext = base64.b64decode(envelope["ciphertext_b64"])

        try:
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        except InvalidTag as exc:
            raise CredentialAuthError("invalid password") from exc

        return json.loads(plaintext.decode("utf-8"))

    def status(self) -> Dict[str, Any]:
        return {
            "credentials_exists": self.credentials_file.exists(),
            "salt_exists": self.salt_file.exists(),
            "credentials_path": str(self.credentials_file),
        }

    def _load_or_create_salt(self) -> bytes:
        if self.salt_file.exists():
            return self.salt_file.read_bytes()

        salt = secrets.token_bytes(16)
        self.salt_file.write_bytes(salt)
        return salt

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        return kdf.derive(password.encode("utf-8"))
