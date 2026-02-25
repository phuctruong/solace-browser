"""
OAuth3 Vault

Reference implementation for Phase 1 token lifecycle:
issue -> verify -> revoke, with evidence-chain logging.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .enforcement import ScopeGate
from .evidence import EvidenceChain
from .revocation import TokenStore
from .scopes import HIGH_RISK_SCOPES
from .token import AgencyToken, create_token


class OAuth3VaultError(Exception):
    """Base vault error."""


class TokenNotFoundError(OAuth3VaultError):
    """Token id not present in vault."""


class TokenValidationError(OAuth3VaultError):
    """Token failed schema/ttl/revocation validation."""


class ScopeViolationError(OAuth3VaultError):
    """Token missing required scopes or step-up."""


class OAuth3Vault:
    """
    In-memory OAuth3 token vault with evidence-chain logging.

    This class intentionally uses in-memory token storage for the reference
    implementation and can be swapped to persistent backends later.
    """

    def __init__(
        self,
        *,
        store: Optional[TokenStore] = None,
        evidence_chain: Optional[EvidenceChain] = None,
        evidence_log: Optional[Path | str] = None,
        issuer: str = "https://www.solaceagi.com",
    ) -> None:
        self.store = store or TokenStore()
        if evidence_chain is not None:
            self.evidence = evidence_chain
        else:
            log = evidence_log or Path("artifacts") / "oauth3" / "oauth3_audit.jsonl"
            self.evidence = EvidenceChain(logfile=log)
        self.issuer = issuer

    def issue_token(self, user_id: str, scopes: List[str], expires_in: int = 3600) -> str:
        """Issue a scoped token and return its token_id."""
        token = create_token(
            issuer=self.issuer,
            subject=user_id,
            scopes=scopes,
            intent="delegated browser action",
            ttl_seconds=expires_in,
        )
        self.store.add(token)
        self.evidence.log_event(
            "TOKEN_ISSUED",
            {
                "token_id": token.token_id,
                "subject": token.subject,
                "scopes": list(token.scopes),
                "expires_at": token.expires_at,
            },
        )
        return token.token_id

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify token is present, non-expired, and non-revoked."""
        existing = self.store.get(token)
        if existing is None:
            raise TokenNotFoundError(f"Token not found: {token}")

        gate = ScopeGate(existing, required_scopes=[])
        result = gate.check_all()
        if not result.allowed:
            raise TokenValidationError(
                f"Token blocked at {result.blocking_gate}: {result.error_code}"
            )

        payload = existing.to_dict()
        self.evidence.log_event(
            "TOKEN_VERIFIED",
            {
                "token_id": existing.token_id,
                "subject": existing.subject,
                "valid": True,
            },
        )
        return payload

    def revoke_token(self, token: str) -> None:
        """Revoke token immediately."""
        if not self.store.revoke(token):
            raise TokenNotFoundError(f"Token not found: {token}")

        self.evidence.log_event("TOKEN_REVOKED", {"token_id": token})

    def require_scopes(
        self,
        token_id: str,
        required_scopes: List[str],
        *,
        step_up_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Enforce required scopes plus step-up gate for high-risk actions."""
        token = self.store.get(token_id)
        if token is None:
            raise TokenNotFoundError(f"Token not found: {token_id}")

        gate = ScopeGate(token=token, required_scopes=required_scopes)
        gate_result = gate.check_all()
        if not gate_result.allowed:
            raise ScopeViolationError(
                f"Scope gate blocked at {gate_result.blocking_gate}: {gate_result.error_code}"
            )

        high_risk_required = [s for s in required_scopes if s in HIGH_RISK_SCOPES]
        if high_risk_required and not step_up_confirmed:
            raise ScopeViolationError(
                f"step_up_required for scopes {high_risk_required}"
            )

        self.evidence.log_event(
            "TOKEN_SCOPE_CHECK",
            {
                "token_id": token_id,
                "required_scopes": required_scopes,
                "step_up_confirmed": step_up_confirmed,
                "allowed": True,
            },
        )
        return token.to_dict()
