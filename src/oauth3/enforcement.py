"""
OAuth3 Enforcement Middleware

Scope enforcement before recipe execution.
Fail-closed: any ambiguous or missing check → deny.

FSM:
  TOKEN_CHECK → SCOPE_CHECK → STEP_UP_CHECK → ALLOWED | BLOCKED

Rung: 641
"""

from pathlib import Path
from typing import Optional

from .token import AgencyToken, DEFAULT_TOKEN_DIR
from .scopes import is_step_up_required


# -------------------------------------------------------------------------
# Individual checks
# -------------------------------------------------------------------------

def check_token_valid(token: AgencyToken) -> tuple:
    """
    Check if the token itself is valid (not expired, not revoked).

    Args:
        token: AgencyToken instance to check.

    Returns:
        (is_valid: bool, error_message: str)
        error_message is empty string when is_valid is True.
    """
    return token.validate()


def check_scope(token: AgencyToken, required_scope: str) -> tuple:
    """
    Check if the token contains a specific required scope.

    Args:
        token: AgencyToken instance.
        required_scope: The scope the recipe requires.

    Returns:
        (has_scope: bool, error_message: str)
    """
    if token.has_scope(required_scope):
        return True, ""

    return False, (
        f"insufficient_scope: token does not include '{required_scope}'. "
        f"Token scopes: {token.scopes}"
    )


def check_step_up(token: AgencyToken, required_scope: str) -> tuple:
    """
    Check if a scope requires step-up re-consent.

    Note: step-up is required when the scope itself is in STEP_UP_REQUIRED_SCOPES,
    regardless of whether the token was issued with the scope. This enforces
    re-consent for every destructive action, not just at token issuance.

    Args:
        token: AgencyToken instance.
        required_scope: The scope being checked.

    Returns:
        (can_proceed_without_step_up: bool, error_message: str)
        Returns (False, "step_up_required") when step-up is needed.
        Returns (True, "") when no step-up is needed.
    """
    if is_step_up_required(required_scope):
        return False, f"step_up_required for scope '{required_scope}'"

    return True, ""


# -------------------------------------------------------------------------
# Orchestrated enforcement
# -------------------------------------------------------------------------

def enforce_oauth3(
    token_id: str,
    required_scope: str,
    token_dir: Optional[Path] = None,
    step_up_confirmed: bool = False,
) -> tuple:
    """
    Full OAuth3 enforcement pipeline.

    Orchestrates: load token → check validity → check scope → check step-up.

    Fail-closed: any failure returns (False, {error_details}).

    Args:
        token_id: UUID of the agency token to enforce against.
        required_scope: The scope required by the recipe being executed.
        token_dir: Directory containing token files (default: ~/.solace/tokens/).
        step_up_confirmed: When True, skip the step-up re-consent check.
            Set this only after step-up has been performed by the caller.
            Default is False (step-up enforced as normal).

    Returns:
        (passes_all_checks: bool, details: dict)

        When passes_all_checks is True:
            details = {
                "token_id": str,
                "scope": str,
                "user_id": str,
                "expires_at": str,
            }

        When passes_all_checks is False:
            details = {
                "error": str,            # machine-readable error code
                "error_detail": str,     # human-readable explanation
                "token_id": str,
                "required_scope": str,
            }
    """
    token_dir = token_dir or DEFAULT_TOKEN_DIR

    # Step 1: Load token from disk
    try:
        token = AgencyToken.load_from_file(token_id, token_dir=token_dir)
    except FileNotFoundError:
        return False, {
            "error": "token_not_found",
            "error_detail": f"No token found with id={token_id}",
            "token_id": token_id,
            "required_scope": required_scope,
        }
    except Exception as e:
        return False, {
            "error": "token_load_error",
            "error_detail": str(e),
            "token_id": token_id,
            "required_scope": required_scope,
        }

    # Step 2: Check token validity (expiry + revocation)
    is_valid, validity_error = check_token_valid(token)
    if not is_valid:
        # Distinguish revoked vs expired for correct HTTP status code mapping
        error_code = "token_revoked" if token.revoked else "token_expired"
        return False, {
            "error": error_code,
            "error_detail": validity_error,
            "token_id": token_id,
            "required_scope": required_scope,
        }

    # Step 3: Check scope membership
    has_scope, scope_error = check_scope(token, required_scope)
    if not has_scope:
        return False, {
            "error": "insufficient_scope",
            "error_detail": scope_error,
            "token_id": token_id,
            "required_scope": required_scope,
            "token_scopes": token.scopes,
            "consent_url": f"/consent?scopes={required_scope}",
        }

    # Step 4: Check step-up requirement (skipped when caller confirms step-up was performed)
    if not step_up_confirmed:
        can_proceed, step_up_error = check_step_up(token, required_scope)
        if not can_proceed:
            return False, {
                "error": "step_up_required",
                "error_detail": step_up_error,
                "token_id": token_id,
                "required_scope": required_scope,
                "action": required_scope,
            }

    # All checks passed
    return True, {
        "token_id": token.token_id,
        "scope": required_scope,
        "user_id": token.user_id,
        "expires_at": token.expires_at,
    }


def build_evidence_token_entry(
    token_id: str,
    scope_used: str,
    step_up_performed: bool = False,
    token_expires_at: Optional[str] = None,
) -> dict:
    """
    Build the agency_token evidence bundle entry.

    This dict is added to every Stillwater evidence bundle for auditable
    non-repudiation of delegated actions.

    Args:
        token_id: UUID of the token used.
        scope_used: The specific scope exercised.
        step_up_performed: Whether step-up re-consent was performed.
        token_expires_at: Expiry timestamp from the token.

    Returns:
        Dict suitable for inclusion in evidence["agency_token"].
    """
    return {
        "token_id": token_id,
        "scope_used": scope_used,
        "step_up_performed": step_up_performed,
        "token_expires_at": token_expires_at,
    }
