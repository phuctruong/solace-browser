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
                   EvidenceChainManager (B9: two-stream evidence, cross-app chains)
                   EvidenceEntry, ChainBreakError, ChainSealedError
  alcoa.py      — ALCOA+ validation report
  retention.py  — RetentionPolicy + RetentionEngine

Rung: 641 (local correctness)
"""

from .chain import AuditEntry, AuditChain
from .chain import EvidenceChainManager, EvidenceEntry, ChainBreakError, ChainSealedError
from .alcoa import ALCOAReport, validate_alcoa
from .retention import RetentionPolicy, RetentionEngine

__all__ = [
    "AuditEntry",
    "AuditChain",
    "EvidenceChainManager",
    "EvidenceEntry",
    "ChainBreakError",
    "ChainSealedError",
    "ALCOAReport",
    "validate_alcoa",
    "RetentionPolicy",
    "RetentionEngine",
]

__version__ = "0.2.0"
__rung__ = 641
