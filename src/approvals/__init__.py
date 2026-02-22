"""
approvals — OAuth3-Governed Execution Approval System
SolaceBrowser Phase 2 (Security Feature #9)

Provides exec approval gating and time-bounded elevated privilege sessions
with stronger guarantees than any generic approval mechanism.

Architecture:
  gate.py     — ApprovalRequest + ApprovalDecision + ApprovalGate
  elevated.py — ElevatedSession + ElevatedMode

Design principles:
  - All timestamps ISO8601 UTC
  - All durations as int seconds
  - SHA256 integrity hash on every audit entry
  - No external dependencies (stdlib only)
  - Dual-control for critical-risk actions
  - Fail-closed: deny on ambiguity or TTL expiry

Rung: 274177 (approval gates are irreversible decisions)
"""

from .gate import (
    ApprovalRequest,
    ApprovalDecision,
    ApprovalGate,
    ApprovalPolicy,
    ApprovalStatus,
)
from .elevated import (
    ElevatedSession,
    ElevatedMode,
    ElevatedModeError,
)

__all__ = [
    "ApprovalRequest",
    "ApprovalDecision",
    "ApprovalGate",
    "ApprovalPolicy",
    "ApprovalStatus",
    "ElevatedSession",
    "ElevatedMode",
    "ElevatedModeError",
]

__version__ = "1.0.0"
__rung__ = 274177
