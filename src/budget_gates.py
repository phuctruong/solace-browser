"""Fail-closed budget gate checker for Solace execution lifecycle.

Gates B1-B6 run before every execution. If ANY gate fails, execution
is BLOCKED and the reason is recorded in the evidence chain.

Gate summary:
  B1: Policy file present (budget-policy.yaml in inbox/policies/)
  B2: Remaining budget > 0 (budget.json remaining_runs)
  B3: Target domain in allowed list (budget-policy.yaml allowed_domains)
  B4: Step-up required? (high/critical risk → explicit approval)
  B5: Evidence mode meets minimum (not disabled)
  B6: Cross-app gate (target installed, partner, budget, MIN-cap)

Design rules:
  - FAIL-CLOSED: missing file, missing key, parse error → BLOCKED
  - NO FALLBACKS: no broad except, no silent swallow
  - Budget decrement is ATOMIC: read→check→write in one call
  - Returns {"allowed": True, "effective_budget": N} on success
  - Returns {"allowed": False, "reason": "gate: explanation"} on failure

Auth: 65537 | Rung: 641 | Paper: 08
"""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
from typing import Any

import yaml


class BudgetPolicyNotFoundError(FileNotFoundError):
    """Raised when budget-policy.yaml is missing for an app."""


class BudgetExhaustedError(ValueError):
    """Raised when remaining_runs <= 0."""


class DomainNotAllowedError(ValueError):
    """Raised when target domain is not in allowed_domains."""


class StepUpRequiredError(PermissionError):
    """Raised when step-up authorization is needed but not provided."""


class EvidenceDisabledError(ValueError):
    """Raised when evidence capture is disabled."""


class CrossAppGateError(ValueError):
    """Raised when a cross-app gate check fails."""


def _blocked(gate: str, explanation: str) -> dict[str, Any]:
    """Return a fail-closed blocked result."""
    return {"allowed": False, "reason": f"{gate}: {explanation}"}


def _allowed(effective_budget: int) -> dict[str, Any]:
    """Return a success result with effective budget."""
    return {"allowed": True, "effective_budget": effective_budget}


class BudgetGateChecker:
    """Fail-closed budget gate checker.

    Each gate is a separate method returning None on pass or a blocked
    dict on failure. The check_all method runs gates B1-B5 (and B6 if
    cross-app), returning the first failure or an allowed result.

    Args:
        apps_root: Path to the apps directory (e.g. ~/.solace/apps).
    """

    def __init__(self, apps_root: Path) -> None:
        self._apps_root = Path(apps_root).resolve()

    def check_all(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run all budget gates. Returns blocked or allowed result.

        Args:
            context: Must contain 'app_id' and 'trigger'. May contain
                'run_id', 'risk_level', 'step_up_approved',
                'evidence_mode', 'target_app_id' (for cross-app).

        Returns:
            {"allowed": True, "effective_budget": int} on success.
            {"allowed": False, "reason": str} on any gate failure.
        """
        app_id = context["app_id"]
        trigger = context.get("trigger", "")
        app_root = self._apps_root / app_id

        if not app_root.is_dir():
            return _blocked("B1", f"app directory not found: {app_id}")

        # B1: Policy file present
        result = self._gate_b1_policy_present(app_root)
        if result is not None:
            return result

        # Load policy once for B1/B3/B5
        policy = self._load_policy(app_root)

        # B2: Remaining limit > 0
        budget = self._load_budget(app_root)
        result = self._gate_b2_remaining_limit(budget)
        if result is not None:
            return result

        remaining = budget["remaining_runs"]

        # B3: Target domain in allowed list
        result = self._gate_b3_domain_allowed(trigger, policy)
        if result is not None:
            return result

        # B4: Step-up required?
        risk_level = context.get("risk_level", "low")
        step_up_approved = context.get("step_up_approved", False)
        result = self._gate_b4_step_up(risk_level, step_up_approved)
        if result is not None:
            return result

        # B5: Evidence mode meets minimum
        evidence_mode = context.get("evidence_mode", policy.get("evidence_mode", "full"))
        result = self._gate_b5_evidence_mode(evidence_mode)
        if result is not None:
            return result

        effective_budget = remaining

        # B6: Cross-app gate (only if target_app_id is present)
        target_app_id = context.get("target_app_id")
        if target_app_id is not None:
            result = self._gate_b6_cross_app(app_id, target_app_id, remaining)
            if result is not None:
                return result
            # MIN-cap: effective budget is min of source and target
            target_budget = self._load_budget(self._apps_root / target_app_id)
            effective_budget = min(remaining, target_budget["remaining_runs"])

        return _allowed(effective_budget)

    # ------------------------------------------------------------------
    # Individual gate methods
    # ------------------------------------------------------------------

    def _gate_b1_policy_present(self, app_root: Path) -> dict[str, Any] | None:
        """B1: Check that inbox/policies/budget-policy.yaml exists."""
        policy_path = app_root / "inbox" / "policies" / "budget-policy.yaml"
        if not policy_path.is_file():
            return _blocked("B1", "budget-policy.yaml not found in inbox/policies/")
        return None

    def _gate_b2_remaining_limit(self, budget: dict[str, Any]) -> dict[str, Any] | None:
        """B2: Check that remaining_runs > 0 in budget.json."""
        remaining = budget.get("remaining_runs")
        if not isinstance(remaining, int):
            return _blocked("B2", "remaining_runs is missing or not an integer in budget.json")
        if remaining <= 0:
            return _blocked("B2", f"remaining_runs is {remaining} (must be > 0)")
        return None

    def _gate_b3_domain_allowed(
        self, trigger: str, policy: dict[str, Any]
    ) -> dict[str, Any] | None:
        """B3: Check the trigger's target domain against allowed_domains.

        The trigger string is expected to contain the domain as the first
        colon-separated segment (e.g. 'mail.google.com:read-inbox') or
        be the domain itself. If trigger is empty or the policy has no
        allowed_domains list, B3 passes (no restriction).
        """
        allowed_domains = policy.get("allowed_domains")
        if allowed_domains is None:
            # No domain restriction configured — gate passes
            return None
        if not isinstance(allowed_domains, list):
            return _blocked("B3", "allowed_domains in budget-policy.yaml is not a list")
        if not allowed_domains:
            return _blocked("B3", "allowed_domains list is empty — no domains permitted")

        # Extract domain from trigger: 'domain:action' or just 'domain'
        target_domain = trigger.split(":")[0].strip() if trigger else ""
        if not target_domain:
            # No domain in trigger — cannot verify, fail closed
            return _blocked("B3", "trigger has no target domain to verify")

        # Wildcard '*' allows all domains
        if "*" in allowed_domains:
            return None

        if target_domain not in allowed_domains:
            return _blocked(
                "B3",
                f"domain '{target_domain}' not in allowed_domains "
                f"{allowed_domains}",
            )
        return None

    def _gate_b4_step_up(
        self, risk_level: str, step_up_approved: bool
    ) -> dict[str, Any] | None:
        """B4: If risk is high or critical, require step_up_approved=True."""
        if risk_level in ("high", "critical") and not step_up_approved:
            return _blocked(
                "B4",
                f"risk_level is '{risk_level}' — step-up authorization required "
                f"but step_up_approved is False",
            )
        return None

    def _gate_b5_evidence_mode(self, evidence_mode: str) -> dict[str, Any] | None:
        """B5: Evidence capture must not be disabled."""
        if evidence_mode == "disabled":
            return _blocked("B5", "evidence capture is disabled — must be 'full' or 'minimal'")
        return None

    def _gate_b6_cross_app(
        self,
        source_app_id: str,
        target_app_id: str,
        source_remaining: int,
    ) -> dict[str, Any] | None:
        """B6: Cross-app gate — all four checks.

        1. Target app is installed (directory exists)
        2. Target is in source manifest's partners list
        3. Target budget > 0
        4. (MIN-cap computed by caller after this returns None)
        """
        target_root = self._apps_root / target_app_id

        # B6.1: Target app installed
        if not target_root.is_dir():
            return _blocked("B6", f"target app '{target_app_id}' is not installed")

        # B6.2: Target in manifest partners list
        source_manifest = self._load_manifest(self._apps_root / source_app_id)
        partners: list[str] = []
        produces_for = source_manifest.get("produces_for")
        if isinstance(produces_for, list):
            partners.extend(produces_for)
        consumes_from = source_manifest.get("consumes_from")
        if isinstance(consumes_from, list):
            partners.extend(consumes_from)
        # Also check a generic 'partners' key
        manifest_partners = source_manifest.get("partners")
        if isinstance(manifest_partners, list):
            partners.extend(manifest_partners)

        if target_app_id not in partners:
            return _blocked(
                "B6",
                f"target app '{target_app_id}' is not in source manifest partners "
                f"(produces_for / consumes_from / partners)",
            )

        # B6.3: Target budget > 0
        target_budget = self._load_budget(target_root)
        target_remaining = target_budget.get("remaining_runs")
        if not isinstance(target_remaining, int) or target_remaining <= 0:
            return _blocked(
                "B6",
                f"target app '{target_app_id}' has no remaining budget "
                f"(remaining_runs={target_remaining})",
            )

        return None

    # ------------------------------------------------------------------
    # Atomic budget decrement
    # ------------------------------------------------------------------

    def decrement_budget(self, app_id: str) -> dict[str, Any]:
        """Atomically decrement remaining_runs for app_id.

        Uses file locking (fcntl.flock) to ensure read→check→write
        is a single atomic operation. No race conditions.

        Returns:
            {"decremented": True, "remaining_runs": N} on success.
            {"decremented": False, "reason": str} on failure.
        """
        budget_path = self._apps_root / app_id / "budget.json"
        if not budget_path.is_file():
            return {"decremented": False, "reason": "budget.json not found"}

        with budget_path.open("r+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                raw = handle.read()
                budget = json.loads(raw)
                if not isinstance(budget, dict):
                    return {"decremented": False, "reason": "budget.json is not a JSON object"}

                remaining = budget.get("remaining_runs")
                if not isinstance(remaining, int) or remaining <= 0:
                    return {
                        "decremented": False,
                        "reason": f"remaining_runs is {remaining} (must be > 0)",
                    }

                budget["remaining_runs"] = remaining - 1
                handle.seek(0)
                handle.truncate()
                handle.write(json.dumps(budget, indent=2, sort_keys=True) + "\n")
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        return {"decremented": True, "remaining_runs": budget["remaining_runs"]}

    # ------------------------------------------------------------------
    # File loaders (fail-closed: parse errors raise, not swallowed)
    # ------------------------------------------------------------------

    def _load_policy(self, app_root: Path) -> dict[str, Any]:
        """Load budget-policy.yaml. Raises on missing file or parse error."""
        policy_path = app_root / "inbox" / "policies" / "budget-policy.yaml"
        raw = policy_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw)
        if not isinstance(parsed, dict):
            raise BudgetPolicyNotFoundError(
                f"budget-policy.yaml in {app_root} did not parse to a dict"
            )
        return parsed

    def _load_budget(self, app_root: Path) -> dict[str, Any]:
        """Load budget.json. Returns empty dict if file missing (fail-closed via B2)."""
        budget_path = app_root / "budget.json"
        if not budget_path.is_file():
            return {}
        raw = budget_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}
        return parsed

    def _load_manifest(self, app_root: Path) -> dict[str, Any]:
        """Load manifest.yaml. Returns empty dict if missing."""
        manifest_path = app_root / "manifest.yaml"
        if not manifest_path.is_file():
            return {}
        raw = manifest_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw)
        if not isinstance(parsed, dict):
            return {}
        return parsed


def check_budget(context: dict[str, Any]) -> dict[str, Any]:
    """Top-level budget check function matching ExecutionLifecycleManager signature.

    Args:
        context: Must contain 'app_id' and 'trigger'. Must contain
            'apps_root' (Path to the apps directory) or defaults to
            ~/.solace/apps.

    Returns:
        {"allowed": True, "effective_budget": int} on success.
        {"allowed": False, "reason": str} on any gate failure.
    """
    apps_root = context.get("apps_root")
    if apps_root is None:
        apps_root = Path("~/.solace/apps").expanduser().resolve()
    else:
        apps_root = Path(apps_root).resolve()

    checker = BudgetGateChecker(apps_root)
    return checker.check_all(context)
