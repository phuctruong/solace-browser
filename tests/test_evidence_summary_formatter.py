"""
EvidenceSummaryFormatter — Acceptance Tests
SolaceBrowser T5 | Belt: Yellow | Rung: 65537

Tests (15 total):
  T01  test_empty_actions_returns_no_actions_recorded
  T02  test_single_action_with_result
  T03  test_single_action_without_result_uses_type_noun
  T04  test_mixed_actions_grouped_by_result
  T05  test_unknown_action_type_counted_as_tasks
  T06  test_timing_format_seconds_only
  T07  test_timing_format_minutes_and_seconds
  T08  test_format_step_timing_empty_steps
  T09  test_format_step_timing_single_done_step
  T10  test_format_step_timing_failed_step
  T11  test_format_step_timing_multiple_steps_pipe_separated
  T12  test_format_step_timing_mixed_statuses
  T13  test_link_to_evidence_default_label
  T14  test_link_to_evidence_custom_label
  T15  test_link_to_evidence_pathlib_path

  T16  test_format_action_summary_type_error_not_list
  T17  test_format_step_timing_type_error_not_list
  T18  test_link_to_evidence_empty_label_raises
  T19  test_module_level_functions_proxy_to_class
  T20  test_total_time_multiple_actions

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_evidence_summary_formatter.py -v

Rung: 65537
"""

import sys
from pathlib import Path

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from evidence.summary_formatter import (
    EvidenceSummaryFormatter,
    format_action_summary,
    format_step_timing,
    link_to_evidence,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_action(
    action_type: str = "navigate",
    target: str = "https://example.com",
    result: str = "",
    duration_ms: int = 1000,
) -> dict:
    return {
        "type": action_type,
        "target": target,
        "result": result,
        "duration_ms": duration_ms,
    }


def _make_step(
    step_num: int = 1,
    action: str = "navigate",
    duration_ms: int = 300,
    status: str = "done",
) -> dict:
    return {
        "step_num": step_num,
        "action": action,
        "duration_ms": duration_ms,
        "status": status,
    }


# ---------------------------------------------------------------------------
# T01-T07: format_action_summary
# ---------------------------------------------------------------------------

class TestFormatActionSummary:
    """Tests for EvidenceSummaryFormatter.format_action_summary."""

    def test_empty_actions_returns_no_actions_recorded(self):
        """T01: Empty list → 'No actions recorded.'"""
        result = EvidenceSummaryFormatter.format_action_summary([])
        assert result == "No actions recorded."

    def test_single_action_with_result(self):
        """T02: Single action with result → '1 <result>. Time: Xs'"""
        actions = [_make_action(result="email triaged", duration_ms=5000)]
        result = EvidenceSummaryFormatter.format_action_summary(actions)
        assert "1 email triaged" in result
        assert "Time: 5s" in result

    def test_single_action_without_result_uses_type_noun(self):
        """T03: Action without result → falls back to type noun"""
        actions = [_make_action(action_type="navigate", result="", duration_ms=300)]
        result = EvidenceSummaryFormatter.format_action_summary(actions)
        assert "pages navigated" in result
        assert "Time: 0s" in result

    def test_mixed_actions_grouped_by_result(self):
        """T04: Multiple actions with same result are grouped and counted."""
        actions = [
            _make_action(result="email triaged", duration_ms=2000),
            _make_action(result="email triaged", duration_ms=3000),
            _make_action(result="marked important", duration_ms=1000),
        ]
        result = EvidenceSummaryFormatter.format_action_summary(actions)
        assert "2 email triaged" in result
        assert "1 marked important" in result
        assert "Time: 6s" in result

    def test_unknown_action_type_counted_as_tasks(self):
        """T05: Unknown action type with no result → 'tasks'"""
        actions = [_make_action(action_type="unknown_type", result="", duration_ms=1000)]
        result = EvidenceSummaryFormatter.format_action_summary(actions)
        assert "1 tasks" in result

    def test_timing_format_seconds_only(self):
        """T06: Time < 60s → formatted as 'Ns'"""
        actions = [_make_action(duration_ms=47000)]
        result = EvidenceSummaryFormatter.format_action_summary(actions)
        assert "Time: 47s" in result

    def test_timing_format_minutes_and_seconds(self):
        """T07: Time >= 60s → formatted as 'Nmin Ns'"""
        actions = [_make_action(duration_ms=123000)]  # 2min 3s
        result = EvidenceSummaryFormatter.format_action_summary(actions)
        assert "Time: 2min 3s" in result

    def test_total_time_multiple_actions(self):
        """T20: Total time = sum of all duration_ms values. 60s = 1min 0s."""
        actions = [
            _make_action(duration_ms=10000),
            _make_action(duration_ms=20000),
            _make_action(duration_ms=30000),
        ]
        result = EvidenceSummaryFormatter.format_action_summary(actions)
        # 60 seconds hits the >= 60 branch → "1min 0s"
        assert "Time: 1min 0s" in result

    def test_format_action_summary_type_error_not_list(self):
        """T16: Non-list input raises TypeError."""
        with pytest.raises(TypeError, match="actions must be list"):
            EvidenceSummaryFormatter.format_action_summary("not a list")

    def test_six_emails_example(self):
        """Acceptance: '6 emails triaged' style summary works correctly."""
        actions = [
            _make_action(result="emails triaged", duration_ms=5000),
            _make_action(result="emails triaged", duration_ms=6000),
            _make_action(result="emails triaged", duration_ms=4000),
            _make_action(result="emails triaged", duration_ms=5000),
            _make_action(result="emails triaged", duration_ms=6000),
            _make_action(result="emails triaged", duration_ms=5000),
            _make_action(result="marked important", duration_ms=3000),
            _make_action(result="marked important", duration_ms=3000),
            _make_action(result="draft created", duration_ms=10000),
        ]
        result = EvidenceSummaryFormatter.format_action_summary(actions)
        assert "6 emails triaged" in result
        assert "2 marked important" in result
        assert "1 draft created" in result
        assert "Time: 47s" in result


# ---------------------------------------------------------------------------
# T08-T12: format_step_timing
# ---------------------------------------------------------------------------

class TestFormatStepTiming:
    """Tests for EvidenceSummaryFormatter.format_step_timing."""

    def test_format_step_timing_empty_steps(self):
        """T08: Empty list → 'No steps recorded.'"""
        result = EvidenceSummaryFormatter.format_step_timing([])
        assert result == "No steps recorded."

    def test_format_step_timing_single_done_step(self):
        """T09: Single done step → 'Step 1: navigate (0.3s)'"""
        steps = [_make_step(step_num=1, action="navigate", duration_ms=300, status="done")]
        result = EvidenceSummaryFormatter.format_step_timing(steps)
        assert result == "Step 1: navigate (0.3s)"

    def test_format_step_timing_failed_step(self):
        """T10: Failed step → 'Step N: action FAILED'"""
        steps = [_make_step(step_num=2, action="click", duration_ms=500, status="failed")]
        result = EvidenceSummaryFormatter.format_step_timing(steps)
        assert result == "Step 2: click FAILED"

    def test_format_step_timing_multiple_steps_pipe_separated(self):
        """T11: Multiple steps joined by ' | '"""
        steps = [
            _make_step(step_num=1, action="navigate", duration_ms=300, status="done"),
            _make_step(step_num=2, action="extract", duration_ms=2100, status="done"),
        ]
        result = EvidenceSummaryFormatter.format_step_timing(steps)
        assert result == "Step 1: navigate (0.3s) | Step 2: extract (2.1s)"

    def test_format_step_timing_mixed_statuses(self):
        """T12: Mix of done, failed, running, pending steps."""
        steps = [
            _make_step(step_num=1, action="navigate", duration_ms=300, status="done"),
            _make_step(step_num=2, action="click", duration_ms=0, status="failed"),
            _make_step(step_num=3, action="extract", duration_ms=1500, status="running"),
        ]
        result = EvidenceSummaryFormatter.format_step_timing(steps)
        assert "Step 1: navigate (0.3s)" in result
        assert "Step 2: click FAILED" in result
        assert "Step 3: extract (1.5s)" in result
        assert " | " in result

    def test_format_step_timing_type_error_not_list(self):
        """T17: Non-list input raises TypeError."""
        with pytest.raises(TypeError, match="steps must be list"):
            EvidenceSummaryFormatter.format_step_timing({"step_num": 1})


# ---------------------------------------------------------------------------
# T13-T15: link_to_evidence
# ---------------------------------------------------------------------------

class TestLinkToEvidence:
    """Tests for EvidenceSummaryFormatter.link_to_evidence."""

    def test_link_to_evidence_default_label(self):
        """T13: Default label is 'Full evidence'."""
        result = EvidenceSummaryFormatter.link_to_evidence("/tmp/evidence/run-001")
        assert result == "Full evidence: /tmp/evidence/run-001"

    def test_link_to_evidence_custom_label(self):
        """T14: Custom label is used in the output."""
        result = EvidenceSummaryFormatter.link_to_evidence(
            "/tmp/evidence/run-001", label="View evidence"
        )
        assert result == "View evidence: /tmp/evidence/run-001"

    def test_link_to_evidence_pathlib_path(self):
        """T15: Path objects are accepted and converted to string."""
        p = Path("/tmp/evidence/run-002")
        result = EvidenceSummaryFormatter.link_to_evidence(p)
        assert "/tmp/evidence/run-002" in result
        assert "Full evidence:" in result

    def test_link_to_evidence_empty_label_raises(self):
        """T18: Empty label raises ValueError."""
        with pytest.raises(ValueError, match="label must not be empty"):
            EvidenceSummaryFormatter.link_to_evidence("/tmp/evidence", label="   ")

    def test_link_to_evidence_type_error_bad_path(self):
        """Bad evidence_dir type raises TypeError."""
        with pytest.raises(TypeError, match="evidence_dir must be str or Path"):
            EvidenceSummaryFormatter.link_to_evidence(12345)


# ---------------------------------------------------------------------------
# T19: Module-level functions proxy to class
# ---------------------------------------------------------------------------

class TestModuleLevelFunctions:
    """T19: Module-level functions delegate to EvidenceSummaryFormatter."""

    def test_module_level_functions_proxy_to_class(self):
        """T19: Module-level format_action_summary, format_step_timing, link_to_evidence."""
        # format_action_summary
        assert format_action_summary([]) == "No actions recorded."

        # format_step_timing
        assert format_step_timing([]) == "No steps recorded."

        # link_to_evidence
        result = link_to_evidence("/tmp/evidence")
        assert "Full evidence:" in result
        assert "/tmp/evidence" in result
