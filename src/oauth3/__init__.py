"""
OAuth3 — Delegated Agency Authorization
SolaceBrowser Phase 1.5 — v0.1.0 (spec-aligned)

Extends OAuth 2.0 to cover action delegation (not just authentication).
Every recipe execution is bounded by a scoped, time-bound, revocable agency token.

Architecture:
  token.py       — AgencyToken frozen dataclass + validation + SHA-256 stub
  scopes.py      — Scope registry (triple-segment: platform.action.resource)
  enforcement.py — ScopeGate (G1-G4) + standalone enforce_scopes()
  revocation.py  — TokenStore (in-memory CRUD + revocation)

Reference: oauth3-spec-v0.1.md
Rung: 641 (local correctness)
"""

# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

from .token import (
    AgencyToken,
    create_token,
    validate_token,
    is_expired,
    parse_iso8601,
    _parse_iso8601,           # backward compat
    SPEC_VERSION,
    DEFAULT_TTL_SECONDS,
    MAX_TTL_SECONDS,
)

# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------

from .scopes import (
    SCOPE_REGISTRY,
    ALL_SCOPES,
    HIGH_RISK_SCOPES,
    DESTRUCTIVE_SCOPES,
    STEP_UP_REQUIRED_SCOPES,  # backward compat alias
    SCOPES,                   # backward compat alias
    validate_scopes,
    get_high_risk_scopes,
    group_by_platform,
    get_scope_description,
    get_scope_risk_level,
    is_step_up_required,
)

# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------

from .enforcement import (
    ScopeGate,
    ScopeGateResult,
    GateResult,
    enforce_scopes,
    require_step_up,
    # backward compat
    check_token_valid,
    check_scope,
    check_step_up,
    build_evidence_token_entry,
    enforce_oauth3,
)

# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------

from .revocation import (
    TokenStore,
    revoke_token,
    revoke_all_for_subject,
    get_active_tokens,
    cleanup_expired,
    # file-based backward compat
    revoke_token_file,
    is_revoked_file,
    is_revoked,
    list_all_tokens,
    revoke_all_tokens_for_scope,
)

# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    # Token
    "AgencyToken",
    "create_token",
    "validate_token",
    "is_expired",
    "parse_iso8601",
    "SPEC_VERSION",
    "DEFAULT_TTL_SECONDS",
    "MAX_TTL_SECONDS",
    # Scopes
    "SCOPE_REGISTRY",
    "ALL_SCOPES",
    "HIGH_RISK_SCOPES",
    "DESTRUCTIVE_SCOPES",
    "STEP_UP_REQUIRED_SCOPES",
    "SCOPES",
    "validate_scopes",
    "get_high_risk_scopes",
    "group_by_platform",
    "get_scope_description",
    "get_scope_risk_level",
    "is_step_up_required",
    # Enforcement
    "ScopeGate",
    "ScopeGateResult",
    "GateResult",
    "enforce_scopes",
    "require_step_up",
    "check_token_valid",
    "check_scope",
    "check_step_up",
    "build_evidence_token_entry",
    "enforce_oauth3",
    # Revocation
    "TokenStore",
    "revoke_token",
    "revoke_all_for_subject",
    "get_active_tokens",
    "cleanup_expired",
    "revoke_token_file",
    "is_revoked_file",
    "is_revoked",
    "list_all_tokens",
    "revoke_all_tokens_for_scope",
]

__version__ = "0.1.0"
__rung__ = 641
