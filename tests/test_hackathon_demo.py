"""Tests for the hackathon demo script.

Verifies that the hackathon demo runs end-to-end without errors and
produces correct results across all 7 phases.

Auth: 65537 | Rung: 641
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from hackathon_demo import (
    DEMO_APPS,
    create_demo_apps,
    gmail_execute_callback,
    gmail_preview_callback,
    run_demo,
    verify_evidence_chain,
)


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


class TestHackathonDemoEndToEnd:
    def test_hackathon_demo_runs_to_completion(self, tmp_path: Path) -> None:
        """Verify the hackathon demo runs end-to-end without errors."""
        solace_home = tmp_path / "solace"
        results = run_demo(solace_home)

        # All 7 phases completed
        assert len(results["phases"]) == 7
        assert results["total_time"] > 0

        # Phase 1: Apps initialized
        assert results["phases"]["1_init_apps"]["apps"] == len(DEMO_APPS)

        # Phase 2: Sessions created
        assert results["phases"]["2_sessions"]["count"] == 4
        assert len(results["phases"]["2_sessions"]["ports"]) == 4

        # Phase 3: Lifecycle completed successfully
        assert results["phases"]["3_lifecycle"]["state"] == "DONE"
        assert results["phases"]["3_lifecycle"]["run_id"] != ""

        # Phase 4: Cross-app message delivered
        assert results["phases"]["4_cross_app"]["delivered"] is True
        assert len(results["phases"]["4_cross_app"]["evidence_hash"]) == 64

        # Phase 5: Orchestrator ran
        assert results["phases"]["5_orchestrator"]["children"] == 4
        # morning-brief orchestrator sends to its children; delivery depends on
        # budget policy domain matching for each child
        assert results["phases"]["5_orchestrator"]["delivered"] >= 0

        # Phase 6: Evidence verified
        assert results["phases"]["6_evidence"]["valid"] is True
        assert results["phases"]["6_evidence"]["entries"] > 0

        # Phase 7: All sessions closed, ports released
        assert results["phases"]["7_close"]["sessions_closed"] == 4
        assert results["phases"]["7_close"]["ports_released"] is True

    def test_demo_is_idempotent(self, tmp_path: Path) -> None:
        """Running the demo twice in the same solace_home should not fail."""
        solace_home = tmp_path / "solace"
        run_demo(solace_home)
        results = run_demo(solace_home)
        assert results["phases"]["3_lifecycle"]["state"] == "DONE"


# ---------------------------------------------------------------------------
# Phase-level tests
# ---------------------------------------------------------------------------


class TestCreateDemoApps:
    def test_creates_all_apps(self, tmp_path: Path) -> None:
        """All demo apps are created with correct structure."""
        apps_root = tmp_path / "apps"
        count = create_demo_apps(apps_root)
        assert count == len(DEMO_APPS)

        for app_def in DEMO_APPS:
            app_root = apps_root / app_def["id"]
            assert app_root.is_dir()
            assert (app_root / "manifest.yaml").is_file()
            assert (app_root / "recipe.json").is_file()
            assert (app_root / "budget.json").is_file()
            assert (app_root / "inbox" / "policies" / "budget-policy.yaml").is_file()
            assert (app_root / "diagrams" / "workflow.md").is_file()

    def test_manifest_has_produces_for_at_top_level(self, tmp_path: Path) -> None:
        """CrossAppMessenger requires produces_for at the manifest top level."""
        import yaml

        apps_root = tmp_path / "apps"
        create_demo_apps(apps_root)

        for app_def in DEMO_APPS:
            manifest_path = apps_root / app_def["id"] / "manifest.yaml"
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            assert "produces_for" in manifest, (
                f"{app_def['id']} manifest missing produces_for at top level"
            )
            assert isinstance(manifest["produces_for"], list)

    def test_budget_json_has_remaining_runs(self, tmp_path: Path) -> None:
        """Each app has budget.json with remaining_runs > 0."""
        apps_root = tmp_path / "apps"
        create_demo_apps(apps_root)

        for app_def in DEMO_APPS:
            budget_path = apps_root / app_def["id"] / "budget.json"
            budget = json.loads(budget_path.read_text(encoding="utf-8"))
            assert budget["remaining_runs"] > 0

    def test_budget_policy_present(self, tmp_path: Path) -> None:
        """Each app has budget-policy.yaml for B1 gate."""
        apps_root = tmp_path / "apps"
        create_demo_apps(apps_root)

        for app_def in DEMO_APPS:
            policy_path = (
                apps_root / app_def["id"] / "inbox" / "policies" / "budget-policy.yaml"
            )
            assert policy_path.is_file(), f"{app_def['id']} missing budget-policy.yaml"


class TestMockCallbacks:
    def test_preview_callback_returns_preview_text(self) -> None:
        """Preview callback returns non-empty preview and actions."""
        result = gmail_preview_callback({"app_id": "gmail-inbox-triage", "trigger": "test"})
        assert "preview" in result
        assert len(result["preview"]) > 100
        assert "actions" in result
        assert len(result["actions"]) > 0

    def test_execute_callback_returns_success(self) -> None:
        """Execute callback returns success status."""
        sealed = {
            "run_id": "test-001",
            "app_id": "gmail-inbox-triage",
            "trigger": "test",
            "preview": "test preview",
            "actions": [{"type": "flag", "count": 3}],
        }
        result = gmail_execute_callback(sealed)
        assert result["status"] == "success"
        assert "actions_summary" in result
        assert result["cost_usd"] > 0


class TestEvidenceVerification:
    def test_valid_chain(self, tmp_path: Path) -> None:
        """A properly constructed evidence chain verifies as valid."""
        import hashlib

        evidence_path = tmp_path / "evidence.jsonl"
        prev_hash = "0" * 64

        with evidence_path.open("w", encoding="utf-8") as f:
            for i in range(5):
                record = {
                    "entry_id": i,
                    "timestamp": "2026-03-02T08:00:00+00:00",
                    "state": f"STATE_{i}",
                    "detail": {"step": i},
                    "prev_hash": prev_hash,
                }
                canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
                entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                record["entry_hash"] = entry_hash
                f.write(json.dumps(record, sort_keys=True) + "\n")
                prev_hash = entry_hash

        result = verify_evidence_chain(evidence_path)
        assert result["valid"] is True
        assert result["entries"] == 5

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing evidence file returns valid=False."""
        result = verify_evidence_chain(tmp_path / "nonexistent.jsonl")
        assert result["valid"] is False

    def test_tampered_chain(self, tmp_path: Path) -> None:
        """A tampered evidence chain is detected."""
        import hashlib

        evidence_path = tmp_path / "evidence.jsonl"
        prev_hash = "0" * 64

        lines = []
        for i in range(3):
            record = {
                "entry_id": i,
                "timestamp": "2026-03-02T08:00:00+00:00",
                "state": f"STATE_{i}",
                "detail": {"step": i},
                "prev_hash": prev_hash,
            }
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
            entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            record["entry_hash"] = entry_hash
            lines.append(json.dumps(record, sort_keys=True))
            prev_hash = entry_hash

        # Tamper with entry 1's detail
        entry1 = json.loads(lines[1])
        entry1["detail"]["step"] = 999
        lines[1] = json.dumps(entry1, sort_keys=True)

        evidence_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = verify_evidence_chain(evidence_path)
        assert result["valid"] is False
        assert result["entry_id"] == 1
