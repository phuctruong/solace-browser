"""
OAuth3 — Delegated Agency Authorization
SolaceBrowser Phase 1.5

Extends OAuth 2.0 to cover action delegation (not just authentication).
Every recipe execution is bounded by a scoped, time-bound, revocable agency token.

Architecture:
  token.py      — AgencyToken dataclass + validation
  scopes.py     — Scope registry (all supported action scopes)
  enforcement.py — Middleware: check scope before recipe execution
  revocation.py — Token revocation + session kill

Reference: OAUTH3-WHITEPAPER.md
Rung: 641 (local correctness)
"""

from .token import AgencyToken
from .scopes import SCOPES, STEP_UP_REQUIRED_SCOPES, validate_scopes, get_scope_description
from .enforcement import check_token_valid, check_scope, check_step_up, enforce_oauth3
from .revocation import revoke_token, revoke_all_tokens_for_scope, is_revoked

__all__ = [
    "AgencyToken",
    "SCOPES",
    "STEP_UP_REQUIRED_SCOPES",
    "validate_scopes",
    "get_scope_description",
    "check_token_valid",
    "check_scope",
    "check_step_up",
    "enforce_oauth3",
    "revoke_token",
    "revoke_all_tokens_for_scope",
    "is_revoked",
]

__version__ = "0.1.0"
__rung__ = 641
