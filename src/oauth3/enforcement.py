"""
OAuth3 Enforcement Middleware

Scope enforcement before recipe execution.
Fail-closed: any ambiguous or missing check → deny.

Four gates per spec §1.4:
  G1: Schema  — token parses, all required fields present
  G2: TTL     — expires_at > current UTC time
  G3: Scope   — requested action scope in token's scopes list
  G4: Revocation — token id not in revocation registry

ScopeGate class orchestrates all four gates.
All gate failures are fail-closed: action is blocked.

Reference: oauth3-spec-v0.1.md §1.4
Rung: 641
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .token import AgencyToken, parse_iso8601
from .scopes import HIGH_RISK_SCOPES, get_scope_risk_level
from .revocation import TokenStore


# ---------------------------------------------------------------------------
# Gate result constants
# ---------------------------------------------------------------------------

GATE_PASS = "PASS"
GATE_BLOCKED = "BLOCKED"


# ---------------------------------------------------------------------------
# ScopeGate — four-gate enforcement class
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    """Result of a single gate check."""

    gate: str          # "G1", "G2", "G3", "G4"
    status: str        # GATE_PASS or GATE_BLOCKED
    error_code: Optional[str] = None
    error_detail: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.status == GATE_PASS


class ScopeGate:
    """
    Four-gate scope enforcement per OAuth3 spec §1.4.

    Usage:
        gate = ScopeGate(token, required_scopes=["linkedin.post.text"])
        result = gate.check_all(step_up_nonce=None)
        if result.allowed:
            # proceed
        else:
            # result.missing_scopes, result.blocking_gate

    Gates:
        G1: Schema check — token is not None, has required fields
        G2: Expiry check — token not expired
        G3: Scope check  — all required_scopes present in token.scopes
        G4: Revocation   — token.revoked is False

    Fail-closed: all four gates must PASS; any failure blocks the action.
    """

    def __init__(
        self,
        token: Optional[AgencyToken] = None,
        required_scopes: Optional[List[str]] = None,
        *,
        store: Optional[TokenStore] = None,
    ) -> None:
        """
        Initialize the gate with a token and the scopes needed for the action.

        Args:
            token:           AgencyToken to check against.
            required_scopes: Scopes the recipe needs to execute.
        """
        self.token = token
        self.required_scopes = list(required_scopes or [])
        self.store = store

    # -------------------------------------------------------------------------
    # Individual gate checks
    # -------------------------------------------------------------------------

    def g1_schema(self) -> GateResult:
        """
        G1: Schema check — token has all required fields.

        Checks: token_id, issuer, subject, scopes, issued_at, expires_at are present.
        """
        if self.token is None:
            return GateResult(
                gate="G1",
                status=GATE_BLOCKED,
                error_code="OAUTH3_MALFORMED_TOKEN",
                error_detail="Token is None.",
            )

        missing = []
        for field in ("token_id", "issuer", "subject", "issued_at", "expires_at"):
            if not getattr(self.token, field, None):
                missing.append(field)

        if not self.token.scopes:
            missing.append("scopes")

        if missing:
            return GateResult(
                gate="G1",
                status=GATE_BLOCKED,
                error_code="OAUTH3_MALFORMED_TOKEN",
                error_detail=f"Missing required fields: {missing}",
            )

        return GateResult(gate="G1", status=GATE_PASS)

    def g2_expiry(self) -> GateResult:
        """
        G2: TTL check — token expires_at > current UTC time.
        """
        try:
            expires_at = parse_iso8601(self.token.expires_at)
        except (ValueError, AttributeError) as exc:
            return GateResult(
                gate="G2",
                status=GATE_BLOCKED,
                error_code="OAUTH3_MALFORMED_TOKEN",
                error_detail=f"Cannot parse expires_at: {exc}",
            )

        now = datetime.now(timezone.utc)
        if now > expires_at:
            return GateResult(
                gate="G2",
                status=GATE_BLOCKED,
                error_code="OAUTH3_TOKEN_EXPIRED",
                error_detail=(
                    f"Token expired at {self.token.expires_at}; "
                    f"current time is {now.isoformat()}"
                ),
            )

        return GateResult(gate="G2", status=GATE_PASS)

    def g3_scope(self) -> Tuple[GateResult, List[str]]:
        """
        G3: Scope check — all required_scopes present in token.scopes.

        Returns:
            (GateResult, missing_scopes: list)
        """
        missing = [s for s in self.required_scopes if s not in self.token.scopes]

        if missing:
            return (
                GateResult(
                    gate="G3",
                    status=GATE_BLOCKED,
                    error_code="OAUTH3_SCOPE_DENIED",
                    error_detail=(
                        f"Scope(s) {missing} not in granted scopes: "
                        f"{list(self.token.scopes)}"
                    ),
                ),
                missing,
            )

        return GateResult(gate="G3", status=GATE_PASS), []

    def g4_revocation(self) -> GateResult:
        """
        G4: Revocation check — token.revoked is False.
        """
        if self.token.revoked:
            revoked_at = self.token.revoked_at or "unknown"
            return GateResult(
                gate="G4",
                status=GATE_BLOCKED,
                error_code="OAUTH3_TOKEN_REVOKED",
                error_detail=f"Token was revoked at {revoked_at}.",
            )

        return GateResult(gate="G4", status=GATE_PASS)

    # -------------------------------------------------------------------------
    # Composite check
    # -------------------------------------------------------------------------

    def check_all(
        self,
        step_up_nonce: Optional[str] = None,
    ) -> "ScopeGateResult":
        """
        Run all four gates in order: G1 → G2 → G3 → G4.

        Fail-closed: stops at the first failing gate and returns BLOCKED.
        G4 (step-up) is only enforced for high-risk scopes when step_up_nonce is None.

        Args:
            step_up_nonce: When provided, indicates step-up consent has been
                           performed. High-risk scopes are allowed to proceed.
                           Set to None to enforce step-up blocking (default).

        Returns:
            ScopeGateResult with allowed=True if all gates pass.
        """
        # G1: Schema
        g1 = self.g1_schema()
        if not g1.passed:
            return _build_scope_gate_result(
                token_id=getattr(self.token, "token_id", None),
                gate_results=[g1],
                missing_scopes=[],
                error_code=g1.error_code,
                error_detail=g1.error_detail,
                blocking_gate="G1",
            )

        # G2: Expiry
        g2 = self.g2_expiry()
        if not g2.passed:
            return _build_scope_gate_result(
                token_id=getattr(self.token, "token_id", None),
                gate_results=[g1, g2],
                missing_scopes=[],
                error_code=g2.error_code,
                error_detail=g2.error_detail,
                blocking_gate="G2",
            )

        # G3: Scope
        g3, missing = self.g3_scope()
        if not g3.passed:
            return _build_scope_gate_result(
                token_id=getattr(self.token, "token_id", None),
                gate_results=[g1, g2, g3],
                missing_scopes=missing,
                error_code=g3.error_code,
                error_detail=g3.error_detail,
                blocking_gate="G3",
            )

        # G4: Revocation
        g4 = self.g4_revocation()
        if not g4.passed:
            return _build_scope_gate_result(
                token_id=getattr(self.token, "token_id", None),
                gate_results=[g1, g2, g3, g4],
                missing_scopes=[],
                error_code=g4.error_code,
                error_detail=g4.error_detail,
                blocking_gate="G4",
            )

        high_risk_required = [scope for scope in self.required_scopes if scope in HIGH_RISK_SCOPES]
        if high_risk_required and not step_up_nonce:
            step_up_gate = GateResult(
                gate="G4",
                status=GATE_BLOCKED,
                error_code="OAUTH3_STEP_UP_REQUIRED",
                error_detail=f"step_up_required for scopes {high_risk_required}",
            )
            return _build_scope_gate_result(
                token_id=getattr(self.token, "token_id", None),
                gate_results=[g1, g2, g3, step_up_gate],
                missing_scopes=[],
                error_code=step_up_gate.error_code,
                error_detail=step_up_gate.error_detail,
                blocking_gate="G4",
            )

        return _build_scope_gate_result(
            token_id=getattr(self.token, "token_id", None),
            gate_results=[g1, g2, g3, g4],
            missing_scopes=[],
            error_code=None,
            error_detail=None,
            blocking_gate=None,
        )

    def check(
        self,
        *,
        token_id: str,
        required_scope: str,
        is_destructive: bool,
        step_up_confirmed: bool = False,
    ) -> "ScopeGateResult":
        """
        Diagram-facing API: evaluate the 4-gate cascade from token_id + store.

        This keeps the existing token-based API (`check_all`) intact while
        enabling the newer diagram tests that construct `ScopeGate(store=...)`.
        """
        if self.store is None:
            raise ValueError("ScopeGate(store=...) is required for check(token_id=...).")

        token = self.store.get(token_id)
        if token is None or token.revoked:
            reason = "token_not_found" if token is None else "token_revoked"
            gate = GateResult(
                gate="G1",
                status=GATE_BLOCKED,
                error_code="OAUTH3_TOKEN_NOT_FOUND" if token is None else "OAUTH3_TOKEN_REVOKED",
                error_detail=reason,
            )
            return _build_scope_gate_result(
                token_id=token_id,
                gate_results=[gate],
                missing_scopes=[],
                error_code=gate.error_code,
                error_detail=gate.error_detail,
                blocking_gate="G1",
            )

        self.token = token
        self.required_scopes = [required_scope]

        step_up_needed = is_destructive or required_scope in HIGH_RISK_SCOPES
        nonce = "step-up-confirmed" if (step_up_confirmed or not step_up_needed) else None
        return self.check_all(step_up_nonce=nonce)


@dataclass
class ScopeGateResult:
    """Result of running all gates via ScopeGate.check_all()."""

    allowed: bool
    blocking_gate: Optional[str]     # None if allowed; "G1", "G2", "G3", "G4" if blocked
    gate_results: List[GateResult]
    missing_scopes: List[str]        # Scopes not in token (G3 failure only)
    error_code: Optional[str]        # OAUTH3_* code if blocked
    error_detail: Optional[str]      # Human-readable explanation
    token_id: Optional[str] = None
    g1_token_exists: bool = False
    g2_not_expired: Optional[bool] = None
    g3_scope_present: Optional[bool] = None
    g4_step_up_satisfied: Optional[bool] = None
    overall_result: str = GATE_BLOCKED
    failure_gate: Optional[str] = None
    failure_reason: Optional[str] = None


def _build_scope_gate_result(
    *,
    token_id: Optional[str],
    gate_results: List[GateResult],
    missing_scopes: List[str],
    error_code: Optional[str],
    error_detail: Optional[str],
    blocking_gate: Optional[str],
) -> ScopeGateResult:
    g1_exists = False
    g2_not_expired: Optional[bool] = None
    g3_scope_present: Optional[bool] = None
    g4_step_up_satisfied: Optional[bool] = None

    for gate in gate_results:
        if gate.gate == "G1":
            g1_exists = gate.passed
        elif gate.gate == "G2":
            g2_not_expired = gate.passed
        elif gate.gate == "G3":
            g3_scope_present = gate.passed
        elif gate.gate == "G4":
            g4_step_up_satisfied = gate.passed

    allowed = blocking_gate is None
    return ScopeGateResult(
        allowed=allowed,
        blocking_gate=blocking_gate,
        gate_results=gate_results,
        missing_scopes=missing_scopes,
        error_code=error_code,
        error_detail=error_detail,
        token_id=token_id,
        g1_token_exists=g1_exists,
        g2_not_expired=g2_not_expired,
        g3_scope_present=g3_scope_present,
        g4_step_up_satisfied=g4_step_up_satisfied,
        overall_result=GATE_PASS if allowed else GATE_BLOCKED,
        failure_gate=blocking_gate,
        failure_reason=error_detail,
    )


# ---------------------------------------------------------------------------
# Standalone enforcement functions (convenience API)
# ---------------------------------------------------------------------------

def enforce_scopes(
    token: Optional[AgencyToken] = None,
    required_scopes: Optional[List[str]] = None,
    *,
    token_id: Optional[str] = None,
    required_scope: Optional[str] = None,
    is_destructive: bool = False,
    step_up_confirmed: bool = False,
    store: Optional[TokenStore] = None,
) -> Union[Tuple[bool, List[str]], str]:
    """
    Check that a token grants all required scopes.

    Does NOT check expiry or revocation — use ScopeGate.check_all() for
    full four-gate enforcement.

    Args:
        token:           AgencyToken to check.
        required_scopes: Scopes needed by the recipe.

    Returns:
        (allowed: bool, missing: List[str])
        allowed is True if all required_scopes are in token.scopes.
    """
    # Backward-compatible API:
    #   enforce_scopes(token, [scope_a, scope_b]) -> (allowed, missing)
    if token is not None and required_scopes is not None:
        missing = [s for s in required_scopes if s not in token.scopes]
        return len(missing) == 0, missing

    # Diagram-facing API:
    #   enforce_scopes(token_id=..., required_scope=..., is_destructive=..., store=...)
    if not token_id:
        raise ValueError("token_id is required when calling enforce_scopes() in gate mode.")
    if not required_scope:
        raise ValueError("required_scope is required when calling enforce_scopes() in gate mode.")
    if store is None:
        raise ValueError("store is required when calling enforce_scopes() in gate mode.")

    gate = ScopeGate(store=store)
    result = gate.check(
        token_id=token_id,
        required_scope=required_scope,
        is_destructive=is_destructive,
        step_up_confirmed=step_up_confirmed,
    )
    return result.overall_result


def require_step_up(token: AgencyToken, scope: str) -> bool:
    """
    Return True if the scope is high-risk AND no step-up nonce is present.

    In practice, this signals that the caller must obtain step-up consent
    before proceeding (spec §3.4).

    Args:
        token: AgencyToken to check.
        scope: The specific scope about to be exercised.

    Returns:
        True if step-up is required (scope is high-risk).
        False if step-up is not needed (scope is low/medium risk).
    """
    return scope in HIGH_RISK_SCOPES


# ---------------------------------------------------------------------------
# Backward-compat helpers (for existing code that uses the old enforcement API)
# ---------------------------------------------------------------------------

def check_token_valid(token: AgencyToken) -> Tuple[bool, str]:
    """
    Check if the token itself is valid (not expired, not revoked).

    Returns:
        (is_valid: bool, error_message: str)
    """
    return token.validate()


def check_scope(token: AgencyToken, required_scope: str) -> Tuple[bool, str]:
    """
    Check if the token contains a specific required scope.

    Returns:
        (has_scope: bool, error_message: str)
    """
    if token.has_scope(required_scope):
        return True, ""
    return False, (
        f"insufficient_scope: token does not include '{required_scope}'. "
        f"Token scopes: {list(token.scopes)}"
    )


def check_step_up(token: AgencyToken, required_scope: str) -> Tuple[bool, str]:
    """
    Check if a scope requires step-up re-consent.

    Returns:
        (can_proceed_without_step_up: bool, error_message: str)
        Returns (False, 'step_up_required for scope ...') when step-up is needed.
    """
    if required_scope in HIGH_RISK_SCOPES:
        return False, f"step_up_required for scope '{required_scope}'"
    return True, ""


def build_evidence_token_entry(
    token_id: str,
    scope_used: str,
    step_up_performed: bool = False,
    token_expires_at: Optional[str] = None,
) -> dict:
    """
    Build the agency_token evidence bundle entry.

    Returns:
        Dict for inclusion in evidence["agency_token"].
    """
    return {
        "token_id": token_id,
        "scope_used": scope_used,
        "step_up_performed": step_up_performed,
        "token_expires_at": token_expires_at,
    }


def enforce_oauth3(
    token_or_id: Union[AgencyToken, str],
    required_scope: Union[str, List[str]],
    step_up_confirmed: bool = False,
    token_dir=None,
) -> Tuple[bool, dict]:
    """
    Full enforcement pipeline — backward-compatible.

    Accepts either an AgencyToken object OR a token_id string.
    When a string is passed, loads the token from file (requires token_dir).

    Runs: token load → validation → scope check → step-up check.

    Args:
        token_or_id:       AgencyToken or token_id string.
        required_scope:    Scope string or list of scope strings required.
        step_up_confirmed: If True, step-up scopes are allowed to proceed.
        token_dir:         Directory for file-based token loading.

    Returns:
        (passes: bool, details: dict)
        details contains 'error', 'token_id', 'scope', 'consent_url', etc.
    """
    details: dict = {}

    # Normalize required_scope to a single scope string (first if list)
    if isinstance(required_scope, list):
        scope = required_scope[0] if required_scope else ""
    else:
        scope = required_scope

    # Load token if a token_id string was provided
    if isinstance(token_or_id, str):
        token_id = token_or_id
        if token_dir is None:
            details["error"] = "token_not_found"
            details["detail"] = "token_dir required when passing token_id string"
            return False, details
        try:
            from .token import AgencyToken as _AgencyToken
            token = _AgencyToken.load_from_file(token_id, token_dir=token_dir)
        except FileNotFoundError:
            details["error"] = "token_not_found"
            details["token_id"] = token_id
            details["required_scope"] = scope
            details["consent_url"] = f"/consent?scopes={scope}"
            return False, details
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            details["error"] = "token_load_error"
            details["token_id"] = token_id
            details["detail"] = str(exc)
            return False, details
    else:
        token = token_or_id
        token_id = token.token_id

    # Gate 1: Token validity (expiry + revocation)
    is_valid, error_msg = check_token_valid(token)
    if not is_valid:
        # Map error message to canonical error codes
        if "revoked" in error_msg:
            details["error"] = "token_revoked"
        elif "expired" in error_msg:
            details["error"] = "token_expired"
        else:
            details["error"] = error_msg
        details["token_id"] = token_id
        details["error_detail"] = error_msg
        return False, details

    # Gate 2: Scope check
    if scope:
        has_scope, scope_error = check_scope(token, scope)
        if not has_scope:
            details["error"] = "insufficient_scope"
            details["token_id"] = token_id
            details["scope"] = scope
            details["consent_url"] = f"/consent?scopes={scope}"
            details["error_detail"] = scope_error
            return False, details

    # Gate 3: Step-up check for high-risk scopes
    if scope and scope in HIGH_RISK_SCOPES:
        if not step_up_confirmed:
            details["error"] = "step_up_required"
            details["token_id"] = token_id
            details["scope"] = scope
            details["action"] = scope
            details["step_up_required"] = True
            details["confirm_url"] = f"/step-up?token_id={token_id}&action={scope}"
            return False, details
        else:
            details["step_up_performed"] = True

    # All gates passed
    details["token_id"] = token_id
    details["scope"] = scope
    details["expires_at"] = token.expires_at
    details["passed"] = True
    return True, details
