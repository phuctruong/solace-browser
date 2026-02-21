"""
audit — FDA 21 CFR Part 11 Compliant Audit Trail Infrastructure
SolaceBrowser Phase 2 (Regulatory)

Provides hash-chained, append-only audit logs that satisfy:
  - FDA 21 CFR Part 11 §11.10(b)(c)(e) — Audit trails, retention, signature meanings
  - ALCOA+ principles — Attributable, Legible, Contemporaneous, Original, Accurate,
    Complete, Consistent, Enduring, Available
  - EU Annex 11 §9 — Reason for action ("Why" field)

Architecture:
  chain.py      — AuditEntry + AuditChain (hash-chained, append-only)
  alcoa.py      — ALCOA+ validation report
  retention.py  — RetentionPolicy + RetentionEngine

Rung: 641 (local correctness)
"""

from .chain import AuditEntry, AuditChain
from .alcoa import ALCOAReport, validate_alcoa
from .retention import RetentionPolicy, RetentionEngine

__all__ = [
    "AuditEntry",
    "AuditChain",
    "ALCOAReport",
    "validate_alcoa",
    "RetentionPolicy",
    "RetentionEngine",
]

__version__ = "0.1.0"
__rung__ = 641
