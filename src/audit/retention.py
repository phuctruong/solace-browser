"""
audit/retention.py — Record Retention Policy Engine

FDA 21 CFR Part 11 §11.10(c):
    "Protection of records to enable their accurate and ready retrieval
    throughout the records retention period."

Retention rules:
  - Records within their retention window CANNOT be deleted (protected).
  - Records past their maximum retention are auto-archived (not deleted — moved).
  - Regulated records (clinical / financial / regulatory) use the global
    min_days / max_days policy regardless of user tier.
  - Non-regulated records use tier-based overrides.

Retention window semantics:
  - can_delete() is False while age < min_days (for regulated records)
    or age < tier retention days (for non-regulated records).
  - records_to_archive() returns records where age > max_days (regulated)
    or age > tier days (non-regulated) and the record is not already archived.
  - records_to_protect() returns records where age < their applicable min threshold.

Rung: 641
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# RetentionPolicy
# ---------------------------------------------------------------------------

@dataclass
class RetentionPolicy:
    """
    Record retention policy (21 CFR Part 11 §11.10(c)).

    Attributes:
        min_days:       Minimum days a regulated record must be retained before
                        deletion is permitted. Default: 730 (2 years, FDA standard).
        max_days:       Maximum days before auto-archival is triggered.
                        Default: 3650 (10 years).
        tier_overrides: Per-subscription-tier retention days for non-regulated records.
                        Keys are tier names; values are days.
    """
    min_days: int = 730       # 2 years minimum (FDA standard for regulated records)
    max_days: int = 3650      # 10 years maximum retention window

    tier_overrides: Dict[str, int] = field(
        default_factory=lambda: {
            "free": 7,
            "student": 30,
            "warrior": 90,
            "master": 365,
            "grandmaster": 3650,  # 10 years (same as regulatory max)
        }
    )

    def days_for_tier(self, tier: str) -> int:
        """
        Return the retention days for a given tier.

        Falls back to the free-tier minimum if tier is unknown.

        Args:
            tier: Subscription tier name.

        Returns:
            Retention days for that tier.
        """
        if tier in self.tier_overrides:
            return self.tier_overrides[tier]
        # Fall back to free-tier days if defined, otherwise 7 days (FDA minimum)
        return self.tier_overrides.get("free", 7)


# ---------------------------------------------------------------------------
# RetentionEngine
# ---------------------------------------------------------------------------

class RetentionEngine:
    """
    Enforce record retention policies.

    Usage:
        engine = RetentionEngine()                      # default policy
        engine = RetentionEngine(RetentionPolicy(...))  # custom policy

    Records are expected to be dicts with at minimum:
        {"created_at": float}   — Unix timestamp of record creation

    Optional fields the engine will use if present:
        {"archived": bool}      — True if already archived
    """

    def __init__(self, policy: Optional[RetentionPolicy] = None):
        self.policy = policy or RetentionPolicy()

    # ------------------------------------------------------------------
    # can_delete
    # ------------------------------------------------------------------

    def can_delete(
        self,
        created_at: float,
        tier: str = "free",
        regulated: bool = False,
    ) -> dict:
        """
        Check whether a record is eligible for deletion.

        Deletion is:
          - BLOCKED if the record is within its retention window (min_days for
            regulated; tier days for non-regulated).
          - ALLOWED after the retention window has elapsed.

        Args:
            created_at: Unix timestamp (float) when the record was created.
            tier:       Subscription tier — used for non-regulated retention days.
            regulated:  If True, the FDA min_days / max_days policy applies.
                        If False, tier_overrides applies.

        Returns:
            {
                "allowed": bool,
                "reason": str,
                "earliest_delete_date": str,   # ISO 8601 UTC
            }
        """
        now_ts = time.time()
        age_days = (now_ts - created_at) / 86400.0

        if regulated:
            required_days = self.policy.min_days
            policy_label = f"regulated (FDA min {self.policy.min_days} days)"
        else:
            required_days = self.policy.days_for_tier(tier)
            policy_label = f"tier '{tier}' ({required_days} days)"

        earliest_delete_ts = created_at + required_days * 86400.0
        earliest_delete_dt = datetime.fromtimestamp(
            earliest_delete_ts, tz=timezone.utc
        ).isoformat()

        if age_days < required_days:
            return {
                "allowed": False,
                "reason": (
                    f"Record is within retention window: "
                    f"{age_days:.1f} days old, policy={policy_label}"
                ),
                "earliest_delete_date": earliest_delete_dt,
            }

        return {
            "allowed": True,
            "reason": (
                f"Record has exceeded retention window: "
                f"{age_days:.1f} days old, policy={policy_label}"
            ),
            "earliest_delete_date": earliest_delete_dt,
        }

    # ------------------------------------------------------------------
    # records_to_archive
    # ------------------------------------------------------------------

    def records_to_archive(
        self,
        records: List[Dict[str, Any]],
        tier: str = "free",
    ) -> List[Dict[str, Any]]:
        """
        Find records that have exceeded their retention period and should be archived.

        A record is included if:
          - It is NOT already archived (record.get("archived") is not True).
          - Its age exceeds the policy's max_days (for regulated) or
            tier days (for non-regulated).

        Note: This method does NOT modify records. The caller is responsible
        for performing the actual archival.

        Args:
            records: List of record dicts. Each must have "created_at" (float).
                     May optionally have "archived" (bool) and "regulated" (bool).
            tier:    Subscription tier for non-regulated retention.

        Returns:
            Subset of records that should be archived.
        """
        now_ts = time.time()
        result = []

        for rec in records:
            # Skip already-archived records
            if rec.get("archived", False):
                continue

            created_at = rec.get("created_at", 0.0)
            age_days = (now_ts - created_at) / 86400.0
            is_regulated = rec.get("regulated", False)

            if is_regulated:
                threshold_days = self.policy.max_days
            else:
                threshold_days = self.policy.days_for_tier(tier)

            if age_days > threshold_days:
                result.append(rec)

        return result

    # ------------------------------------------------------------------
    # records_to_protect
    # ------------------------------------------------------------------

    def records_to_protect(
        self,
        records: List[Dict[str, Any]],
        tier: str = "free",
    ) -> List[Dict[str, Any]]:
        """
        Find records that are within their retention window and cannot be deleted.

        A record is included if:
          - Its age is less than the policy minimum (regulated: min_days,
            non-regulated: tier days).

        Args:
            records: List of record dicts. Each must have "created_at" (float).
                     May optionally have "regulated" (bool).
            tier:    Subscription tier for non-regulated retention.

        Returns:
            Subset of records that are protected from deletion.
        """
        now_ts = time.time()
        result = []

        for rec in records:
            created_at = rec.get("created_at", 0.0)
            age_days = (now_ts - created_at) / 86400.0
            is_regulated = rec.get("regulated", False)

            if is_regulated:
                required_days = self.policy.min_days
            else:
                required_days = self.policy.days_for_tier(tier)

            if age_days < required_days:
                result.append(rec)

        return result
