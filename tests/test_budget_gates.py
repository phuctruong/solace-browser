"""Tests for the fail-closed budget gate checker (B1-B6).

Test structure:
  - Each gate tested individually (B1-B6)
  - All gates pass -> allowed
  - Any single gate fail -> blocked
  - Cross-app MIN-cap logic
  - Missing policy file -> blocked (fail-closed)
  - Negative/zero budget -> blocked

Auth: 65537 | Rung: 641
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from budget_gates import (
    BudgetGateChecker,
    BudgetPolicyNotFoundError,
    check_budget,
)


# ---------------------------------------------------------------------------
# Helpers — build a complete app filesystem for testing
# ---------------------------------------------------------------------------


def _make_app(
    apps_root: Path,
    app_id: str = "gmail-inbox-triage",
    *,
    remaining_runs: int = 5,
    include_policy: bool = True,
    allowed_domains: list[str] | None = None,
    evidence_mode: str = "full",
    partners: list[str] | None = None,
) -> Path:
    """Create a fully valid app directory under apps_root.

    Returns the app_root path.
    """
    app_root = apps_root / app_id
    inbox_root = app_root / "inbox"
    outbox_root = app_root / "outbox"

    for path in [
        inbox_root / "prompts",
        inbox_root / "templates",
        inbox_root / "assets",
        inbox_root / "policies",
        inbox_root / "datasets",
        inbox_root / "requests",
        inbox_root / "conventions" / "examples",
        outbox_root / "previews",
        outbox_root / "drafts",
        outbox_root / "reports",
        outbox_root / "suggestions",
        outbox_root / "runs",
        app_root / "diagrams",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    # manifest.yaml
    manifest: dict[str, Any] = {
        "id": app_id,
        "name": app_id.replace("-", " ").title(),
        "required_inbox": {
            "prompts": [],
            "templates": [],
            "assets": [],
            "policies": [],
            "datasets": [],
            "requests": [],
            "conventions": {"config": "config.yaml", "defaults": "defaults.yaml"},
        },
    }
    if partners is not None:
        manifest["produces_for"] = partners
    (app_root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )

    # recipe.json
    (app_root / "recipe.json").write_text(
        json.dumps({"id": app_id, "steps": []}), encoding="utf-8"
    )

    # budget.json
    (app_root / "budget.json").write_text(
        json.dumps({"remaining_runs": remaining_runs}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # diagrams
    for name in ["workflow.md", "data-flow.md", "partner-contracts.md"]:
        (app_root / "diagrams" / name).write_text(
            "```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8"
        )

    # inbox/conventions
    (inbox_root / "conventions" / "config.yaml").write_text("scan_hours: 2\n", encoding="utf-8")
    (inbox_root / "conventions" / "defaults.yaml").write_text(
        "scan_hours: 24\n", encoding="utf-8"
    )

    # budget-policy.yaml
    if include_policy:
        policy: dict[str, Any] = {"evidence_mode": evidence_mode}
        if allowed_domains is not None:
            policy["allowed_domains"] = allowed_domains
        (inbox_root / "policies" / "budget-policy.yaml").write_text(
            yaml.safe_dump(policy, sort_keys=False), encoding="utf-8"
        )

    return app_root


def _context(
    apps_root: Path,
    app_id: str = "gmail-inbox-triage",
    trigger: str = "mail.google.com:read-inbox",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a context dict for check_all."""
    ctx: dict[str, Any] = {
        "app_id": app_id,
        "trigger": trigger,
        "run_id": f"{app_id}-20260301120000000000",
        "apps_root": str(apps_root),
    }
    ctx.update(kwargs)
    return ctx


# ---------------------------------------------------------------------------
# B1: Policy file present
# ---------------------------------------------------------------------------


class TestGateB1PolicyPresent:
    def test_b1_pass_when_policy_exists(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, include_policy=True)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is True

    def test_b1_blocked_when_policy_missing(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, include_policy=False)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is False
        assert "B1" in result["reason"]
        assert "budget-policy.yaml" in result["reason"]

    def test_b1_blocked_when_app_directory_missing(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        apps_root.mkdir(parents=True)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root, app_id="nonexistent"))

        assert result["allowed"] is False
        assert "B1" in result["reason"]


# ---------------------------------------------------------------------------
# B2: Remaining limit > 0
# ---------------------------------------------------------------------------


class TestGateB2RemainingLimit:
    def test_b2_pass_with_positive_budget(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=10)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is True
        assert result["effective_budget"] == 10

    def test_b2_blocked_with_zero_budget(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=0)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is False
        assert "B2" in result["reason"]
        assert "0" in result["reason"]

    def test_b2_blocked_with_negative_budget(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=-3)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is False
        assert "B2" in result["reason"]

    def test_b2_blocked_when_remaining_runs_missing(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, remaining_runs=5)
        # Overwrite budget.json with no remaining_runs key
        (app_root / "budget.json").write_text(
            json.dumps({"total_runs": 100}) + "\n", encoding="utf-8"
        )
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is False
        assert "B2" in result["reason"]

    def test_b2_blocked_when_budget_json_missing(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, remaining_runs=5)
        (app_root / "budget.json").unlink()
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is False
        assert "B2" in result["reason"]

    def test_b2_blocked_when_remaining_runs_is_string(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, remaining_runs=5)
        (app_root / "budget.json").write_text(
            json.dumps({"remaining_runs": "five"}) + "\n", encoding="utf-8"
        )
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is False
        assert "B2" in result["reason"]


# ---------------------------------------------------------------------------
# B3: Target domain in allowed list
# ---------------------------------------------------------------------------


class TestGateB3DomainAllowed:
    def test_b3_pass_when_domain_in_allowed_list(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, allowed_domains=["mail.google.com", "slack.com"])
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, trigger="mail.google.com:read-inbox")
        )

        assert result["allowed"] is True

    def test_b3_pass_when_no_allowed_domains_configured(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, allowed_domains=None)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, trigger="any.domain.com:action")
        )

        assert result["allowed"] is True

    def test_b3_pass_with_wildcard_domain(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, allowed_domains=["*"])
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, trigger="anything.example.com:action")
        )

        assert result["allowed"] is True

    def test_b3_blocked_when_domain_not_in_list(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, allowed_domains=["mail.google.com"])
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, trigger="evil.example.com:steal-data")
        )

        assert result["allowed"] is False
        assert "B3" in result["reason"]
        assert "evil.example.com" in result["reason"]

    def test_b3_blocked_when_allowed_domains_empty(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, allowed_domains=[])
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, trigger="mail.google.com:read-inbox")
        )

        assert result["allowed"] is False
        assert "B3" in result["reason"]

    def test_b3_blocked_when_trigger_empty(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, allowed_domains=["mail.google.com"])
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root, trigger=""))

        assert result["allowed"] is False
        assert "B3" in result["reason"]

    def test_b3_domain_extracted_from_colon_separated_trigger(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, allowed_domains=["github.com"])
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, trigger="github.com:create-issue:urgent")
        )

        assert result["allowed"] is True


# ---------------------------------------------------------------------------
# B4: Step-up required
# ---------------------------------------------------------------------------


class TestGateB4StepUp:
    def test_b4_pass_low_risk_no_step_up(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, risk_level="low", step_up_approved=False)
        )

        assert result["allowed"] is True

    def test_b4_pass_medium_risk_no_step_up(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, risk_level="medium", step_up_approved=False)
        )

        assert result["allowed"] is True

    def test_b4_pass_high_risk_with_step_up(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, risk_level="high", step_up_approved=True)
        )

        assert result["allowed"] is True

    def test_b4_pass_critical_risk_with_step_up(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, risk_level="critical", step_up_approved=True)
        )

        assert result["allowed"] is True

    def test_b4_blocked_high_risk_no_step_up(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, risk_level="high", step_up_approved=False)
        )

        assert result["allowed"] is False
        assert "B4" in result["reason"]
        assert "high" in result["reason"]

    def test_b4_blocked_critical_risk_no_step_up(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, risk_level="critical", step_up_approved=False)
        )

        assert result["allowed"] is False
        assert "B4" in result["reason"]
        assert "critical" in result["reason"]


# ---------------------------------------------------------------------------
# B5: Evidence mode meets minimum
# ---------------------------------------------------------------------------


class TestGateB5EvidenceMode:
    def test_b5_pass_full_evidence(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, evidence_mode="full")
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is True

    def test_b5_pass_minimal_evidence(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, evidence_mode="minimal")
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is True

    def test_b5_blocked_disabled_evidence(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, evidence_mode="disabled")
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is False
        assert "B5" in result["reason"]
        assert "disabled" in result["reason"]

    def test_b5_context_evidence_mode_overrides_policy(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, evidence_mode="full")
        checker = BudgetGateChecker(apps_root)

        # Context says disabled, even though policy says full
        result = checker.check_all(
            _context(apps_root, evidence_mode="disabled")
        )

        assert result["allowed"] is False
        assert "B5" in result["reason"]


# ---------------------------------------------------------------------------
# B6: Cross-app gate
# ---------------------------------------------------------------------------


class TestGateB6CrossApp:
    def test_b6_pass_valid_cross_app(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="gmail-inbox-triage", remaining_runs=5, partners=["slack-triage"])
        _make_app(apps_root, app_id="slack-triage", remaining_runs=3)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, app_id="gmail-inbox-triage", target_app_id="slack-triage")
        )

        assert result["allowed"] is True
        # MIN-cap: min(5, 3) = 3
        assert result["effective_budget"] == 3

    def test_b6_min_cap_uses_lower_budget(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="gmail-inbox-triage", remaining_runs=2, partners=["slack-triage"])
        _make_app(apps_root, app_id="slack-triage", remaining_runs=10)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, app_id="gmail-inbox-triage", target_app_id="slack-triage")
        )

        assert result["allowed"] is True
        # MIN-cap: min(2, 10) = 2
        assert result["effective_budget"] == 2

    def test_b6_blocked_target_not_installed(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="gmail-inbox-triage", remaining_runs=5, partners=["nonexistent-app"])
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, app_id="gmail-inbox-triage", target_app_id="nonexistent-app")
        )

        assert result["allowed"] is False
        assert "B6" in result["reason"]
        assert "not installed" in result["reason"]

    def test_b6_blocked_target_not_in_partners(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="gmail-inbox-triage", remaining_runs=5, partners=["slack-triage"])
        _make_app(apps_root, app_id="calendar-brief", remaining_runs=3)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, app_id="gmail-inbox-triage", target_app_id="calendar-brief")
        )

        assert result["allowed"] is False
        assert "B6" in result["reason"]
        assert "not in source manifest partners" in result["reason"]

    def test_b6_blocked_target_budget_zero(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="gmail-inbox-triage", remaining_runs=5, partners=["slack-triage"])
        _make_app(apps_root, app_id="slack-triage", remaining_runs=0)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, app_id="gmail-inbox-triage", target_app_id="slack-triage")
        )

        assert result["allowed"] is False
        assert "B6" in result["reason"]
        assert "no remaining budget" in result["reason"]

    def test_b6_blocked_target_budget_negative(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="gmail-inbox-triage", remaining_runs=5, partners=["slack-triage"])
        _make_app(apps_root, app_id="slack-triage", remaining_runs=-1)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, app_id="gmail-inbox-triage", target_app_id="slack-triage")
        )

        assert result["allowed"] is False
        assert "B6" in result["reason"]

    def test_b6_no_cross_app_when_target_app_id_absent(self, tmp_path: Path) -> None:
        """B6 is skipped when no target_app_id in context."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=5)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(_context(apps_root))

        assert result["allowed"] is True
        assert result["effective_budget"] == 5


# ---------------------------------------------------------------------------
# Integration: All gates pass
# ---------------------------------------------------------------------------


class TestAllGatesPass:
    def test_all_gates_pass_returns_allowed_with_budget(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            remaining_runs=7,
            allowed_domains=["mail.google.com"],
            evidence_mode="full",
        )
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(
                apps_root,
                trigger="mail.google.com:read-inbox",
                risk_level="low",
            )
        )

        assert result["allowed"] is True
        assert result["effective_budget"] == 7

    def test_all_gates_pass_high_risk_with_step_up(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            remaining_runs=3,
            allowed_domains=["mail.google.com"],
            evidence_mode="full",
        )
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(
                apps_root,
                trigger="mail.google.com:send-email",
                risk_level="high",
                step_up_approved=True,
            )
        )

        assert result["allowed"] is True
        assert result["effective_budget"] == 3


# ---------------------------------------------------------------------------
# Integration: Any single gate fail -> blocked
# ---------------------------------------------------------------------------


class TestAnySingleGateFailBlocks:
    """Verify that exactly one failing gate blocks even when all others pass."""

    def _base_context(self, apps_root: Path) -> dict[str, Any]:
        return _context(
            apps_root,
            trigger="mail.google.com:read-inbox",
            risk_level="low",
            step_up_approved=False,
            evidence_mode="full",
        )

    def test_only_b1_fails(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            include_policy=False,  # B1 fail
            remaining_runs=5,
        )
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(self._base_context(apps_root))

        assert result["allowed"] is False
        assert "B1" in result["reason"]

    def test_only_b2_fails(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            remaining_runs=0,  # B2 fail
            allowed_domains=["mail.google.com"],
        )
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(self._base_context(apps_root))

        assert result["allowed"] is False
        assert "B2" in result["reason"]

    def test_only_b3_fails(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            remaining_runs=5,
            allowed_domains=["slack.com"],  # B3 fail: mail.google.com not in list
        )
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(self._base_context(apps_root))

        assert result["allowed"] is False
        assert "B3" in result["reason"]

    def test_only_b4_fails(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            remaining_runs=5,
            allowed_domains=["mail.google.com"],
        )
        checker = BudgetGateChecker(apps_root)

        ctx = self._base_context(apps_root)
        ctx["risk_level"] = "critical"
        ctx["step_up_approved"] = False  # B4 fail
        result = checker.check_all(ctx)

        assert result["allowed"] is False
        assert "B4" in result["reason"]

    def test_only_b5_fails(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            remaining_runs=5,
            allowed_domains=["mail.google.com"],
            evidence_mode="disabled",  # B5 fail via policy
        )
        checker = BudgetGateChecker(apps_root)

        # Do NOT pass evidence_mode in context — let policy value ("disabled") apply
        ctx = self._base_context(apps_root)
        del ctx["evidence_mode"]
        result = checker.check_all(ctx)

        assert result["allowed"] is False
        assert "B5" in result["reason"]

    def test_only_b6_fails_target_not_partner(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            app_id="gmail-inbox-triage",
            remaining_runs=5,
            allowed_domains=["mail.google.com"],
            partners=[],  # no partners
        )
        _make_app(apps_root, app_id="slack-triage", remaining_runs=3)
        checker = BudgetGateChecker(apps_root)

        ctx = self._base_context(apps_root)
        ctx["target_app_id"] = "slack-triage"  # B6 fail: not in partners
        result = checker.check_all(ctx)

        assert result["allowed"] is False
        assert "B6" in result["reason"]


# ---------------------------------------------------------------------------
# Atomic budget decrement
# ---------------------------------------------------------------------------


class TestAtomicDecrement:
    def test_decrement_reduces_by_one(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=5)
        checker = BudgetGateChecker(apps_root)

        result = checker.decrement_budget("gmail-inbox-triage")

        assert result["decremented"] is True
        assert result["remaining_runs"] == 4

        # Verify file on disk
        budget = json.loads(
            (apps_root / "gmail-inbox-triage" / "budget.json").read_text(encoding="utf-8")
        )
        assert budget["remaining_runs"] == 4

    def test_decrement_from_one_to_zero(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=1)
        checker = BudgetGateChecker(apps_root)

        result = checker.decrement_budget("gmail-inbox-triage")

        assert result["decremented"] is True
        assert result["remaining_runs"] == 0

    def test_decrement_fails_at_zero(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=0)
        checker = BudgetGateChecker(apps_root)

        result = checker.decrement_budget("gmail-inbox-triage")

        assert result["decremented"] is False

    def test_decrement_fails_when_budget_json_missing(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, remaining_runs=5)
        (app_root / "budget.json").unlink()
        checker = BudgetGateChecker(apps_root)

        result = checker.decrement_budget("gmail-inbox-triage")

        assert result["decremented"] is False

    def test_decrement_multiple_times(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=3)
        checker = BudgetGateChecker(apps_root)

        r1 = checker.decrement_budget("gmail-inbox-triage")
        r2 = checker.decrement_budget("gmail-inbox-triage")
        r3 = checker.decrement_budget("gmail-inbox-triage")
        r4 = checker.decrement_budget("gmail-inbox-triage")

        assert r1 == {"decremented": True, "remaining_runs": 2}
        assert r2 == {"decremented": True, "remaining_runs": 1}
        assert r3 == {"decremented": True, "remaining_runs": 0}
        assert r4["decremented"] is False

    def test_decrement_preserves_other_budget_fields(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, remaining_runs=5)
        # Add extra fields to budget.json
        budget = {"remaining_runs": 5, "total_runs": 100, "tier": "pro"}
        (app_root / "budget.json").write_text(
            json.dumps(budget, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        checker = BudgetGateChecker(apps_root)

        checker.decrement_budget("gmail-inbox-triage")

        updated = json.loads(
            (app_root / "budget.json").read_text(encoding="utf-8")
        )
        assert updated["remaining_runs"] == 4
        assert updated["total_runs"] == 100
        assert updated["tier"] == "pro"


# ---------------------------------------------------------------------------
# Top-level check_budget function
# ---------------------------------------------------------------------------


class TestCheckBudgetFunction:
    def test_check_budget_uses_apps_root_from_context(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=3)

        result = check_budget({
            "app_id": "gmail-inbox-triage",
            "trigger": "mail.google.com:read-inbox",
            "run_id": "test-001",
            "apps_root": str(apps_root),
        })

        assert result["allowed"] is True
        assert result["effective_budget"] == 3

    def test_check_budget_blocked_on_missing_policy(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, include_policy=False)

        result = check_budget({
            "app_id": "gmail-inbox-triage",
            "trigger": "mail.google.com:read-inbox",
            "run_id": "test-002",
            "apps_root": str(apps_root),
        })

        assert result["allowed"] is False
        assert "B1" in result["reason"]


# ---------------------------------------------------------------------------
# Edge cases and fail-closed behavior
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_budget_json_is_not_valid_json(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, remaining_runs=5)
        (app_root / "budget.json").write_text("NOT JSON", encoding="utf-8")
        checker = BudgetGateChecker(apps_root)

        with pytest.raises(json.JSONDecodeError):
            checker.check_all(_context(apps_root))

    def test_policy_yaml_is_not_valid_yaml(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, include_policy=True)
        policy_path = app_root / "inbox" / "policies" / "budget-policy.yaml"
        policy_path.write_text(":\n  :\n    : [", encoding="utf-8")
        checker = BudgetGateChecker(apps_root)

        with pytest.raises((yaml.YAMLError, BudgetPolicyNotFoundError)):
            checker.check_all(_context(apps_root))

    def test_policy_yaml_parses_to_non_dict(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, include_policy=True)
        policy_path = app_root / "inbox" / "policies" / "budget-policy.yaml"
        policy_path.write_text("- item1\n- item2\n", encoding="utf-8")
        checker = BudgetGateChecker(apps_root)

        with pytest.raises(BudgetPolicyNotFoundError):
            checker.check_all(_context(apps_root))

    def test_allowed_domains_not_a_list(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        app_root = _make_app(apps_root, include_policy=True)
        policy_path = app_root / "inbox" / "policies" / "budget-policy.yaml"
        policy_path.write_text(
            yaml.safe_dump({"allowed_domains": "mail.google.com", "evidence_mode": "full"}),
            encoding="utf-8",
        )
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, trigger="mail.google.com:read")
        )

        assert result["allowed"] is False
        assert "B3" in result["reason"]
        assert "not a list" in result["reason"]

    def test_budget_one_remaining_passes_then_blocks(self, tmp_path: Path) -> None:
        """Budget = 1: first check passes, decrement, second check blocks."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, remaining_runs=1)
        checker = BudgetGateChecker(apps_root)

        result1 = checker.check_all(_context(apps_root))
        assert result1["allowed"] is True

        checker.decrement_budget("gmail-inbox-triage")

        result2 = checker.check_all(_context(apps_root))
        assert result2["allowed"] is False
        assert "B2" in result2["reason"]

    def test_cross_app_equal_budgets(self, tmp_path: Path) -> None:
        """MIN-cap when both budgets are equal."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="gmail-inbox-triage", remaining_runs=4, partners=["slack-triage"])
        _make_app(apps_root, app_id="slack-triage", remaining_runs=4)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, app_id="gmail-inbox-triage", target_app_id="slack-triage")
        )

        assert result["allowed"] is True
        assert result["effective_budget"] == 4

    def test_cross_app_uses_consumes_from_as_partner(self, tmp_path: Path) -> None:
        """B6 checks consumes_from in addition to produces_for."""
        apps_root = tmp_path / "apps"
        app_root = _make_app(
            apps_root, app_id="gmail-inbox-triage", remaining_runs=5, partners=[]
        )
        # Manually add consumes_from to manifest
        manifest = yaml.safe_load(
            (app_root / "manifest.yaml").read_text(encoding="utf-8")
        )
        manifest["consumes_from"] = ["slack-triage"]
        (app_root / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        _make_app(apps_root, app_id="slack-triage", remaining_runs=3)
        checker = BudgetGateChecker(apps_root)

        result = checker.check_all(
            _context(apps_root, app_id="gmail-inbox-triage", target_app_id="slack-triage")
        )

        assert result["allowed"] is True
        assert result["effective_budget"] == 3
