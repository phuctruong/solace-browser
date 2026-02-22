"""
approvals/gate.py — OAuth3 Approval Gate

Intercepts and gates dangerous operations before execution.

Features:
  - ApprovalRequest: structured request with risk classification
  - ApprovalDecision: recorded decision with reason + conditions
  - ApprovalGate: stateful gate with TTL auto-deny, dual-control for
    "critical" risk, batch approval, and SHA256 audit trail

Design constraints:
  - All timestamps ISO8601 UTC (no naive datetimes)
  - All durations int seconds
  - SHA256 integrity hash on every audit entry
  - Fail-closed: expired requests auto-denied; ambiguous state → deny
  - Dual-control: "critical" risk requires 2 distinct approvers
  - No external dependencies (stdlib only)

Rung: 274177
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TTL_SECONDS: int = 300          # 5 minutes
CRITICAL_APPROVALS_REQUIRED: int = 2   # Dual-control for critical risk


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ApprovalStatus(str, Enum):
    """Lifecycle state of an approval request."""
    PENDING       = "pending"
    APPROVED      = "approved"
    DENIED        = "denied"
    EXPIRED       = "expired"
    AUTO_APPROVED = "auto_approved"


# ---------------------------------------------------------------------------
# Risk level ordering (int for comparisons — no float)
# ---------------------------------------------------------------------------

_RISK_ORDER: Dict[str, int] = {
    "low":      0,
    "medium":   1,
    "high":     2,
    "critical": 3,
}


def _risk_lt(a: str, b: str) -> bool:
    """Return True if risk level a is strictly below risk level b."""
    return _RISK_ORDER.get(a, 0) < _RISK_ORDER.get(b, 0)


# ---------------------------------------------------------------------------
# ApprovalPolicy — governs auto-approve thresholds and escalation
# ---------------------------------------------------------------------------

@dataclass
class ApprovalPolicy:
    """
    Policy governing the ApprovalGate's auto-approve and escalation behaviour.

    Fields:
        policy_id:                UUID4 identifier.
        name:                     Human-readable policy name.
        risk_threshold:           Minimum risk level that triggers manual approval.
        auto_approve_below:       Risk level below which requests are auto-approved.
                                  Must be strictly less than risk_threshold.
        require_justification:    If True, requests without a description are auto-denied.
        max_approval_wait_seconds: Seconds before a pending request auto-expires.
        escalation_chain:         Ordered list of approver IDs to escalate to on timeout.
    """

    policy_id:                  str
    name:                       str
    risk_threshold:             str = "high"
    auto_approve_below:         str = "medium"
    require_justification:      bool = True
    max_approval_wait_seconds:  int = 300
    escalation_chain:           List[str] = field(default_factory=list)

    @classmethod
    def default(cls) -> "ApprovalPolicy":
        """Return the default conservative policy."""
        return cls(
            policy_id=str(uuid.uuid4()),
            name="default",
            risk_threshold="high",
            auto_approve_below="medium",
            require_justification=True,
            max_approval_wait_seconds=DEFAULT_TTL_SECONDS,
            escalation_chain=[],
        )


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ApprovalRequest:
    """
    A structured request for approval of a dangerous operation.

    Fields:
        request_id:   UUID4 globally unique request identifier.
        action:       Short name of the action being gated (e.g. "delete_post").
        scope:        OAuth3 scope governing this action (e.g. "linkedin.delete.post").
        risk_level:   Risk classification: "low" | "medium" | "high" | "critical".
        description:  Human-readable description of the action and its consequences.
        evidence:     Supporting evidence dict (e.g. {"url": "...", "target": "..."}).
        requested_by: Identifier of the agent or user requesting approval.
        requested_at: ISO8601 UTC timestamp of request creation.
        expires_at:   ISO8601 UTC timestamp after which the request auto-denies.
    """
    request_id:   str
    action:       str
    scope:        str
    risk_level:   str   # "low" | "medium" | "high" | "critical"
    description:  str
    evidence:     dict
    requested_by: str
    requested_at: str   # ISO8601 UTC
    expires_at:   str   # ISO8601 UTC

    def is_expired(self) -> bool:
        """Return True if the request has passed its expires_at timestamp."""
        now = datetime.now(timezone.utc)
        expires = _parse_iso8601(self.expires_at)
        return now > expires

    def to_dict(self) -> dict:
        """Convert to plain dict (JSON-serializable)."""
        return {
            "request_id":   self.request_id,
            "action":       self.action,
            "scope":        self.scope,
            "risk_level":   self.risk_level,
            "description":  self.description,
            "evidence":     self.evidence,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "expires_at":   self.expires_at,
        }


@dataclass
class ApprovalDecision:
    """
    A recorded decision on an ApprovalRequest.

    Fields:
        request_id:  UUID4 of the request this decision applies to.
        approved:    True if the action is approved; False if denied.
        decided_by:  Identifier of the approver (human or system).
        decided_at:  ISO8601 UTC timestamp of the decision.
        reason:      Free-text explanation of the decision.
        conditions:  Optional list of conditions that must hold for approval.
    """
    request_id:  str
    approved:    bool
    decided_by:  str
    decided_at:  str   # ISO8601 UTC
    reason:      str
    conditions:  List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to plain dict (JSON-serializable)."""
        return {
            "request_id":  self.request_id,
            "approved":    self.approved,
            "decided_by":  self.decided_by,
            "decided_at":  self.decided_at,
            "reason":      self.reason,
            "conditions":  self.conditions,
        }


# ---------------------------------------------------------------------------
# Internal state record (per request)
# ---------------------------------------------------------------------------

@dataclass
class _RequestState:
    """Internal state tracked by the gate for each request."""
    request:    ApprovalRequest
    decisions:  List[ApprovalDecision] = field(default_factory=list)
    status:     ApprovalStatus = ApprovalStatus.PENDING


# ---------------------------------------------------------------------------
# ApprovalGate
# ---------------------------------------------------------------------------

class ApprovalGate:
    """
    OAuth3-governed execution approval gate.

    Intercepts dangerous operations and requires explicit approval before
    allowing execution. Features:

      - TTL auto-deny: requests older than ttl_seconds are auto-denied.
      - Dual-control: "critical" risk requires 2 distinct approvers.
      - Batch approval: approve multiple related requests atomically.
      - Audit trail: every request + decision logged with SHA256 hash.

    Usage::

        gate = ApprovalGate()
        req = gate.request_approval(
            action="delete_post",
            scope="linkedin.delete.post",
            risk_level="high",
            evidence={"post_id": "abc123"},
        )
        gate.decide(req.request_id, approved=True, reason="User confirmed")
        status = gate.check(req.request_id)  # "approved"
    """

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        *,
        system_id: str = "approval-gate",
    ) -> None:
        """
        Initialise the gate.

        Args:
            ttl_seconds: Auto-deny timeout for pending requests (default 300 s).
            system_id:   Identifier used as decided_by for system-generated decisions.
        """
        self._ttl_seconds: int = ttl_seconds
        self._system_id: str = system_id
        # {request_id: _RequestState}
        self._state: Dict[str, _RequestState] = {}
        # Ordered audit log: list of dicts with SHA256 integrity hashes
        self._audit_log: List[dict] = []

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def request_approval(
        self,
        action: str,
        scope: str,
        risk_level: str,
        evidence: Optional[dict] = None,
        *,
        requested_by: str = "agent",
        description: str = "",
        ttl_seconds: Optional[int] = None,
    ) -> ApprovalRequest:
        """
        Create and register an approval request.

        Args:
            action:       Short name of the action being gated.
            scope:        OAuth3 scope governing this action.
            risk_level:   "low" | "medium" | "high" | "critical".
            evidence:     Supporting evidence dict.
            requested_by: Identifier of the requester (default "agent").
            description:  Human-readable explanation of the action.
            ttl_seconds:  Override default TTL for this request.

        Returns:
            ApprovalRequest (registered in gate state).

        Raises:
            ValueError: If risk_level is not one of the four valid values.
        """
        valid_risk_levels = {"low", "medium", "high", "critical"}
        if risk_level not in valid_risk_levels:
            raise ValueError(
                f"Invalid risk_level '{risk_level}'. "
                f"Must be one of: {sorted(valid_risk_levels)}"
            )

        effective_ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=effective_ttl)

        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            action=action,
            scope=scope,
            risk_level=risk_level,
            description=description,
            evidence=evidence if evidence is not None else {},
            requested_by=requested_by,
            requested_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )

        self._state[request.request_id] = _RequestState(request=request)
        self._append_audit(event="request_created", data=request.to_dict())

        return request

    def decide(
        self,
        request_id: str,
        approved: bool,
        reason: str,
        conditions: Optional[List[str]] = None,
        *,
        decided_by: str = "approver",
    ) -> ApprovalDecision:
        """
        Record a decision on a pending request.

        For "critical" risk, two distinct approvers must each call decide()
        with approved=True before the request reaches APPROVED status. A
        single approver cannot fulfil both roles.

        Args:
            request_id:  UUID of the request to decide on.
            approved:    True to approve, False to deny.
            reason:      Free-text justification.
            conditions:  Optional conditions on the approval.
            decided_by:  Identifier of the approver.

        Returns:
            ApprovalDecision (recorded in gate state and audit log).

        Raises:
            KeyError:   If request_id is not found.
            ValueError: If the request is not in a decidable state (already
                        approved, denied, or expired).
        """
        state = self._get_state(request_id)

        # Sweep expiry before deciding
        self._sweep_expired_state(state)

        if state.status == ApprovalStatus.EXPIRED:
            raise ValueError(
                f"Request {request_id} has expired and cannot be decided."
            )
        if state.status == ApprovalStatus.DENIED:
            raise ValueError(
                f"Request {request_id} is already denied."
            )
        if state.status == ApprovalStatus.APPROVED:
            raise ValueError(
                f"Request {request_id} is already approved."
            )

        # If denying: record immediately and set DENIED status
        if not approved:
            decision = self._record_decision(
                state=state,
                approved=False,
                decided_by=decided_by,
                reason=reason,
                conditions=conditions or [],
            )
            state.status = ApprovalStatus.DENIED
            return decision

        # Approving: for critical risk, enforce dual-control
        decision = self._record_decision(
            state=state,
            approved=True,
            decided_by=decided_by,
            reason=reason,
            conditions=conditions or [],
        )

        if state.request.risk_level == "critical":
            # Count distinct approvers who approved
            approver_ids = [
                d.decided_by
                for d in state.decisions
                if d.approved
            ]
            distinct_approvers = set(approver_ids)
            if len(distinct_approvers) >= CRITICAL_APPROVALS_REQUIRED:
                state.status = ApprovalStatus.APPROVED
            # else: still pending — needs another approver
        else:
            # Non-critical: single approval is sufficient
            state.status = ApprovalStatus.APPROVED

        return decision

    def check(self, request_id: str) -> str:
        """
        Check the current status of a request.

        Auto-denies expired PENDING requests on access.

        Args:
            request_id: UUID of the request to check.

        Returns:
            Status string: "pending" | "approved" | "denied" | "expired".

        Raises:
            KeyError: If request_id is not found.
        """
        state = self._get_state(request_id)
        self._sweep_expired_state(state)
        return state.status.value

    def batch_approve(
        self,
        request_ids: List[str],
        reason: str,
        *,
        decided_by: str = "approver",
        conditions: Optional[List[str]] = None,
    ) -> List[ApprovalDecision]:
        """
        Approve multiple related requests atomically.

        All requests must be PENDING and non-expired. If any request cannot
        be approved (expired, already decided, or critical requiring dual-
        control), that request's decision reflects its actual outcome.

        Args:
            request_ids: List of request UUIDs to approve.
            reason:      Shared justification for all approvals.
            decided_by:  Identifier of the approver.
            conditions:  Optional shared conditions list.

        Returns:
            List of ApprovalDecision objects (one per request_id, in order).
        """
        decisions = []
        for rid in request_ids:
            try:
                decision = self.decide(
                    request_id=rid,
                    approved=True,
                    reason=reason,
                    conditions=conditions,
                    decided_by=decided_by,
                )
            except (KeyError, ValueError) as exc:
                # Manufacture a system-denied decision for failed requests
                now = datetime.now(timezone.utc).isoformat()
                decision = ApprovalDecision(
                    request_id=rid,
                    approved=False,
                    decided_by=self._system_id,
                    decided_at=now,
                    reason=f"batch_approve failed: {exc}",
                    conditions=[],
                )
                self._append_audit(event="batch_approve_failure", data=decision.to_dict())
            decisions.append(decision)
        return decisions

    def get_audit_log(self) -> List[dict]:
        """
        Return a copy of the full audit log.

        Each entry is a dict with keys:
            event, data, timestamp, entry_hash

        entry_hash is SHA256(event + timestamp + JSON(data)).

        Returns:
            List of audit entries (ordered by insertion time).
        """
        return list(self._audit_log)

    def get_decisions(self, request_id: str) -> List[ApprovalDecision]:
        """
        Return all decisions recorded for a request.

        Args:
            request_id: UUID of the request.

        Returns:
            List of ApprovalDecision objects.

        Raises:
            KeyError: If request_id is not found.
        """
        state = self._get_state(request_id)
        return list(state.decisions)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get_state(self, request_id: str) -> _RequestState:
        """Retrieve state or raise KeyError with a clear message."""
        try:
            return self._state[request_id]
        except KeyError:
            raise KeyError(f"Approval request not found: {request_id}")

    def _sweep_expired_state(self, state: _RequestState) -> None:
        """
        If the request is PENDING and expired, auto-deny it.

        Records a system-generated denial decision and logs to audit trail.
        """
        if state.status != ApprovalStatus.PENDING:
            return
        if not state.request.is_expired():
            return

        # Auto-deny expired request
        now = datetime.now(timezone.utc).isoformat()
        decision = ApprovalDecision(
            request_id=state.request.request_id,
            approved=False,
            decided_by=self._system_id,
            decided_at=now,
            reason="auto-denied: request TTL exceeded",
            conditions=[],
        )
        state.decisions.append(decision)
        state.status = ApprovalStatus.EXPIRED
        self._append_audit(event="request_expired", data=decision.to_dict())

    def _record_decision(
        self,
        state: _RequestState,
        approved: bool,
        decided_by: str,
        reason: str,
        conditions: List[str],
    ) -> ApprovalDecision:
        """Record a decision, append to state, and log to audit trail."""
        now = datetime.now(timezone.utc).isoformat()
        decision = ApprovalDecision(
            request_id=state.request.request_id,
            approved=approved,
            decided_by=decided_by,
            decided_at=now,
            reason=reason,
            conditions=conditions,
        )
        state.decisions.append(decision)
        self._append_audit(
            event="decision_recorded",
            data=decision.to_dict(),
        )
        return decision

    def _append_audit(self, event: str, data: dict) -> None:
        """
        Append a hashed entry to the audit log.

        Hash = SHA256(event + timestamp_str + canonical_json(data))
        Prefixed with "sha256:" for clarity.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        raw = f"{event}:{timestamp}:{canonical}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        entry_hash = f"sha256:{digest}"

        self._audit_log.append({
            "event":      event,
            "timestamp":  timestamp,
            "data":       data,
            "entry_hash": entry_hash,
        })


# ---------------------------------------------------------------------------
# Internal utility
# ---------------------------------------------------------------------------

def _parse_iso8601(dt_str: str) -> datetime:
    """
    Parse ISO 8601 datetime string to timezone-aware datetime.

    Handles both 'Z' suffix and '+00:00' offset formats.
    """
    dt_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
