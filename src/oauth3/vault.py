"""
OAuth3 Vault

Phase 1 reference implementation:
- Issue scoped tokens with TTL
- Validate tokens per scope
- Revoke tokens immediately
- Optional encrypted persistence
- Hash-chained evidence audit
"""

from __future__ import annotations

import base64
import binascii
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .evidence import EvidenceChain
from .revocation import TokenStore
from .scopes import HIGH_RISK_SCOPES
from .token import AgencyToken


class OAuth3VaultError(Exception):
    """Base vault error."""


class TokenNotFoundError(OAuth3VaultError):
    """Token id not present in vault."""


class TokenValidationError(OAuth3VaultError):
    """Token failed schema/ttl/revocation validation."""


class ScopeViolationError(OAuth3VaultError):
    """Token missing required scopes or step-up."""


class OAuth3Vault:
    """OAuth3 token vault with immediate revocation semantics."""

    def __init__(
        self,
        encryption_key: Optional[bytes] = None,
        *,
        store: Optional[TokenStore] = None,
        evidence_chain: Optional[EvidenceChain] = None,
        evidence_log: Optional[Path | str] = None,
        storage_path: Optional[Path | str] = None,
        issuer: str = "https://www.solaceagi.com",
    ) -> None:
        self.encryption_key = encryption_key or secrets.token_bytes(32)
        if len(self.encryption_key) != 32:
            raise ValueError("encryption_key must be exactly 32 bytes (AES-256).")

        self.store = store or TokenStore()
        if evidence_chain is not None:
            self.evidence = evidence_chain
        else:
            log = evidence_log or Path("scratch") / "evidence" / "phase_1" / "oauth3_audit.jsonl"
            self.evidence = EvidenceChain(logfile=log)

        self.storage_path = Path(storage_path) if storage_path else None
        self.issuer = issuer

        if self.storage_path is not None:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._load_tokens_from_disk()

    def issue_token(
        self,
        user_id_or_scopes: str | List[str],
        scopes: Optional[List[str]] = None,
        ttl_seconds: int = 3600,
        *,
        expires_in: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Issue a scoped token with TTL.

        Supported call forms:
        1) `issue_token(["browser.read"], ttl_seconds=3600)`
        2) `issue_token("user:alice", ["browser.read"], expires_in=3600)`
        """
        if expires_in is not None:
            ttl_seconds = expires_in

        if isinstance(user_id_or_scopes, str):
            user_id = user_id_or_scopes
            requested_scopes = list(scopes or [])
        else:
            user_id = "anonymous"
            requested_scopes = list(user_id_or_scopes)

        if not requested_scopes:
            raise ValueError("scopes must not be empty")

        token = AgencyToken.create(
            user_id=user_id,
            issuer=self.issuer,
            scopes=requested_scopes,
            intent="delegated browser action",
            ttl_seconds=ttl_seconds,
        )
        self.store.add(token)
        self._persist_tokens_to_disk()

        payload = self._token_view(token)
        self.evidence.log_event("TOKEN_ISSUED", payload)
        return payload

    def validate_token(self, token_id: str, scope: str) -> bool:
        """Return True only when token exists, is valid, and includes scope."""
        token = self.store.get(token_id)
        if token is None:
            self.evidence.log_event(
                "TOKEN_VALIDATED",
                {
                    "token_id": token_id,
                    "scope": scope,
                    "valid": False,
                    "reason": "token_not_found",
                },
            )
            return False

        is_valid, error = token.validate()
        if not is_valid:
            self.evidence.log_event(
                "TOKEN_VALIDATED",
                {
                    "token_id": token_id,
                    "scope": scope,
                    "valid": False,
                    "reason": error,
                },
            )
            return False

        if scope not in token.scopes:
            self.evidence.log_event(
                "TOKEN_VALIDATED",
                {
                    "token_id": token_id,
                    "scope": scope,
                    "valid": False,
                    "reason": "scope_denied",
                },
            )
            return False

        self.evidence.log_event(
            "TOKEN_VALIDATED",
            {
                "token_id": token_id,
                "scope": scope,
                "valid": True,
                "reason": "ok",
            },
        )
        return True

    def verify_token(self, token_id: str) -> Dict[str, Any]:
        """Backward-compatible strict verification (raises on invalid)."""
        token = self.store.get(token_id)
        if token is None:
            raise TokenNotFoundError(f"Token not found: {token_id}")

        is_valid, error = token.validate()
        if not is_valid:
            raise TokenValidationError(f"Token invalid: {error}")

        payload = self._token_view(token)
        self.evidence.log_event(
            "TOKEN_VERIFIED",
            {
                "token_id": token_id,
                "subject": payload["subject"],
                "valid": True,
            },
        )
        return payload

    def revoke_token(self, token_id: str) -> Dict[str, Any]:
        """Revoke token immediately and return a receipt."""
        if not self.store.revoke(token_id):
            raise TokenNotFoundError(f"Token not found: {token_id}")

        token = self.store.get(token_id)
        revoked_at = token.revoked_at if token is not None else datetime.now(timezone.utc).isoformat()
        self._persist_tokens_to_disk()

        receipt = {
            "token_id": token_id,
            "revoked_at": revoked_at,
            "immediate": True,
        }
        self.evidence.log_event("TOKEN_REVOKED", receipt)
        return receipt

    def get_token(self, token_id: str) -> Dict[str, Any]:
        """Get token data."""
        token = self.store.get(token_id)
        if token is None:
            raise TokenNotFoundError(f"Token not found: {token_id}")
        return self._token_view(token)

    def require_scopes(
        self,
        token_id: str,
        required_scopes: List[str],
        *,
        step_up_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Enforce one or more required scopes plus step-up for high-risk scopes."""
        token = self.store.get(token_id)
        if token is None:
            raise TokenNotFoundError(f"Token not found: {token_id}")

        is_valid, error = token.validate()
        if not is_valid:
            raise ScopeViolationError(f"token_invalid: {error}")

        missing = [scope for scope in required_scopes if scope not in token.scopes]
        if missing:
            raise ScopeViolationError(f"scope_denied: {missing}")

        high_risk = [scope for scope in required_scopes if scope in HIGH_RISK_SCOPES]
        if high_risk and not step_up_confirmed:
            raise ScopeViolationError(f"step_up_required for scopes {high_risk}")

        self.evidence.log_event(
            "TOKEN_SCOPE_CHECK",
            {
                "token_id": token_id,
                "required_scopes": required_scopes,
                "step_up_confirmed": step_up_confirmed,
                "allowed": True,
            },
        )
        return self._token_view(token)

    def _token_view(self, token: AgencyToken) -> Dict[str, Any]:
        return {
            "token_id": token.token_id,
            "scopes": list(token.scopes),
            "created_at": token.issued_at,
            "expires_at": token.expires_at,
            "revoked": bool(token.revoked),
            "revoked_at": token.revoked_at,
            "subject": token.subject,
            "issuer": token.issuer,
        }

    def _persist_tokens_to_disk(self) -> None:
        if self.storage_path is None:
            return

        records = [self._token_view(token) for token in self.store.all_tokens()]
        plaintext = json.dumps({"schema_version": "1.0.0", "tokens": records}, sort_keys=True).encode("utf-8")

        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self.encryption_key).encrypt(nonce, plaintext, None)
        payload = {
            "cipher": "AES-256-GCM",
            "nonce_b64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        }
        self.storage_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def _load_tokens_from_disk(self) -> None:
        if self.storage_path is None or not self.storage_path.exists():
            return

        raw = self.storage_path.read_text(encoding="utf-8").strip()
        if not raw:
            return

        try:
            payload = json.loads(raw)
            nonce = base64.b64decode(payload["nonce_b64"])
            ciphertext = base64.b64decode(payload["ciphertext_b64"])
            plaintext = AESGCM(self.encryption_key).decrypt(nonce, ciphertext, None)
            decoded = json.loads(plaintext.decode("utf-8"))
        except (
            InvalidTag,
            OSError,
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            binascii.Error,
            json.JSONDecodeError,
        ) as exc:
            raise OAuth3VaultError(f"Failed to load persisted tokens: {exc}") from exc

        for row in decoded.get("tokens", []):
            token_payload = {
                "token_id": row["token_id"],
                "issuer": row.get("issuer", self.issuer),
                "subject": row.get("subject", "anonymous"),
                "scopes": row.get("scopes", []),
                "intent": "delegated browser action",
                "issued_at": row["created_at"],
                "expires_at": row["expires_at"],
                "revoked": row.get("revoked", False),
                "revoked_at": row.get("revoked_at"),
                "signature_stub": "sha256:persisted",
                "step_up_required_for": [],
            }
            self.store.add(AgencyToken.from_dict(token_payload))
