"""
Browser gate wrapper for the OAuth3 4-gate cascade.

Provides a browser-facing result schema plus gate audit record builder.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from oauth3.scopes import HIGH_RISK_SCOPES
from oauth3.token import AgencyToken, parse_iso8601

GATE_PASS = "PASS"
GATE_BLOCKED = "BLOCKED"


@dataclass
class BrowserGateResult:
    token_id: Optional[str]
    g1_token_exists: bool
    g2_not_expired: Optional[bool]
    g3_scope_present: Optional[bool]
    g4_step_up_satisfied: Optional[bool]
    overall_result: str
    failure_gate: Optional[str]
    failure_reason: Optional[str]


def _coerce_token(token: Any) -> Optional[AgencyToken]:
    if token is None:
        return None
    if isinstance(token, AgencyToken):
        return token
    if isinstance(token, dict):
        payload = dict(token)
        payload.setdefault("issuer", "https://www.solaceagi.com")
        payload.setdefault("subject", "unknown")
        payload.setdefault("intent", "browser action")
        payload.setdefault("revoked", False)
        payload.setdefault("revoked_at", None)
        payload.setdefault("signature_stub", "sha256:placeholder")
        payload.setdefault("step_up_required_for", [])
        payload.setdefault(
            "issued_at",
            datetime.now(timezone.utc).isoformat(),
        )
        payload.setdefault(
            "expires_at",
            datetime.now(timezone.utc).isoformat(),
        )
        if "token_id" not in payload:
            payload["token_id"] = str(uuid.uuid4())
        return AgencyToken.from_dict(payload)
    return None


def run_4gate_cascade(
    *,
    token: Any,
    required_scope: str,
    is_destructive: bool,
    step_up_confirmed: bool = False,
) -> BrowserGateResult:
    """Run G1-G4 checks for browser actions."""
    agency_token = _coerce_token(token)

    if agency_token is None or agency_token.revoked:
        return BrowserGateResult(
            token_id=None,
            g1_token_exists=False,
            g2_not_expired=None,
            g3_scope_present=None,
            g4_step_up_satisfied=None,
            overall_result=GATE_BLOCKED,
            failure_gate="G1",
            failure_reason="token_missing_or_revoked",
        )

    token_id = agency_token.token_id

    now = datetime.now(timezone.utc)
    expires_at = parse_iso8601(agency_token.expires_at)
    g2 = now <= expires_at
    if not g2:
        return BrowserGateResult(
            token_id=token_id,
            g1_token_exists=True,
            g2_not_expired=False,
            g3_scope_present=None,
            g4_step_up_satisfied=None,
            overall_result=GATE_BLOCKED,
            failure_gate="G2",
            failure_reason="token_expired",
        )

    g3 = required_scope in agency_token.scopes
    if not g3:
        return BrowserGateResult(
            token_id=token_id,
            g1_token_exists=True,
            g2_not_expired=True,
            g3_scope_present=False,
            g4_step_up_satisfied=None,
            overall_result=GATE_BLOCKED,
            failure_gate="G3",
            failure_reason="scope_missing",
        )

    step_up_needed = bool(is_destructive or required_scope in HIGH_RISK_SCOPES)
    g4 = (not step_up_needed) or bool(step_up_confirmed)
    if not g4:
        return BrowserGateResult(
            token_id=token_id,
            g1_token_exists=True,
            g2_not_expired=True,
            g3_scope_present=True,
            g4_step_up_satisfied=False,
            overall_result=GATE_BLOCKED,
            failure_gate="G4",
            failure_reason="step_up_required",
        )

    return BrowserGateResult(
        token_id=token_id,
        g1_token_exists=True,
        g2_not_expired=True,
        g3_scope_present=True,
        g4_step_up_satisfied=True,
        overall_result=GATE_PASS,
        failure_gate=None,
        failure_reason=None,
    )


def build_gate_audit_record(
    *,
    gate_result: Any,
    action_id: str,
    platform: str,
    action_type: str,
    prev_chain_link: Optional[str],
) -> Dict[str, Any]:
    """Build a gate_audit.json-style record from gate results."""
    timestamp = datetime.now(timezone.utc).isoformat()
    record: Dict[str, Any] = {
        "audit_id": str(uuid.uuid4()),
        "action_id": action_id,
        "platform": platform,
        "action_type": action_type,
        "token_id": getattr(gate_result, "token_id", None),
        "g1_token_exists": bool(getattr(gate_result, "g1_token_exists", False)),
        "g2_not_expired": getattr(gate_result, "g2_not_expired", None),
        "g3_scope_present": getattr(gate_result, "g3_scope_present", None),
        "g4_step_up_satisfied": getattr(gate_result, "g4_step_up_satisfied", None),
        "overall_result": getattr(gate_result, "overall_result", GATE_BLOCKED),
        "failure_gate": getattr(gate_result, "failure_gate", None),
        "failure_reason": getattr(gate_result, "failure_reason", None),
        "timestamp_iso8601": timestamp,
    }

    prev = prev_chain_link or ("0" * 64)
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
    chain = hashlib.sha256(f"{prev}:{canonical}".encode("utf-8")).hexdigest()
    record["sha256_chain_link"] = chain
    return record
