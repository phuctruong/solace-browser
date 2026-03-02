"""
test_execution_progress.py — Acceptance tests for ExecutionProgress UI module

12 test classes covering:
  1. TestInit                  ( 4) — constructor validation
  2. TestStartStep             ( 4) — start_step() happy + error paths
  3. TestCompleteStep          ( 4) — complete_step() happy + error paths
  4. TestFailStep              ( 4) — fail_step() happy + error paths
  5. TestIsComplete            ( 4) — is_complete() truth table
  6. TestHasFailures           ( 3) — has_failures() truth table
  7. TestGetProgressBar        ( 5) — bar width, fill fraction, edge cases
  8. TestRenderStep            ( 6) — per-state rendering content
  9. TestRender                ( 4) — full render: header, bar, all steps
 10. TestRenderSummary         ( 5) — summary lines for all outcomes
 11. TestAnsi                  ( 4) — ANSI helper methods
 12. TestEdgeCases             ( 5) — boundary values, re-start, ordering

Rung: 641

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_execution_progress.py -v
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ui.execution_progress import (
    ANSI,
    ExecutionProgress,
    StepRecord,
    StepState,
    _BAR_EMPTY,
    _BAR_FILL,
    _COMPLETE_CHAR,
    _FAILED_CHAR,
    _PENDING_CHAR,
    _SPINNER_CHAR,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences for plain-text assertions."""
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


def _make_progress(total: int = 3, name: str = "Test Recipe") -> ExecutionProgress:
    return ExecutionProgress(total_steps=total, recipe_name=name)


# ===========================================================================
# 1. TestInit
# ===========================================================================

class TestInit(unittest.TestCase):
    """Constructor validation — 4 tests."""

    def test_valid_construction(self) -> None:
        prog = ExecutionProgress(total_steps=6, recipe_name="Extract Gmail")
        self.assertEqual(prog._total_steps, 6)
        self.assertEqual(prog._recipe_name, "Extract Gmail")

    def test_recipe_name_stripped(self) -> None:
        prog = ExecutionProgress(total_steps=2, recipe_name="  My Recipe  ")
        self.assertEqual(prog._recipe_name, "My Recipe")

    def test_zero_total_steps_raises(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionProgress(total_steps=0, recipe_name="Bad")

    def test_empty_recipe_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionProgress(total_steps=3, recipe_name="   ")


# ===========================================================================
# 2. TestStartStep
# ===========================================================================

class TestStartStep(unittest.TestCase):
    """start_step() happy and error paths — 4 tests."""

    def test_start_step_creates_record(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "Navigating to Gmail")
        record = prog._find_step(1)
        self.assertIsNotNone(record)
        self.assertEqual(record.state, StepState.IN_PROGRESS)
        self.assertEqual(record.description, "Navigating to Gmail")

    def test_start_step_out_of_range_raises(self) -> None:
        prog = _make_progress(total=3)
        with self.assertRaises(ValueError):
            prog.start_step(4, "Too far")

    def test_start_step_zero_raises(self) -> None:
        prog = _make_progress(total=3)
        with self.assertRaises(ValueError):
            prog.start_step(0, "Zero step")

    def test_start_step_empty_description_raises(self) -> None:
        prog = _make_progress(total=3)
        with self.assertRaises(ValueError):
            prog.start_step(1, "")


# ===========================================================================
# 3. TestCompleteStep
# ===========================================================================

class TestCompleteStep(unittest.TestCase):
    """complete_step() happy and error paths — 4 tests."""

    def test_complete_step_transitions_to_complete(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "Navigate")
        prog.complete_step(1, duration_seconds=2.3)
        record = prog._find_step(1)
        self.assertEqual(record.state, StepState.COMPLETE)
        self.assertAlmostEqual(record.duration_seconds, 2.3)

    def test_complete_step_zero_duration_allowed(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "Instant")
        prog.complete_step(1, duration_seconds=0.0)
        record = prog._find_step(1)
        self.assertEqual(record.duration_seconds, 0.0)

    def test_complete_step_negative_duration_raises(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "Navigate")
        with self.assertRaises(ValueError):
            prog.complete_step(1, duration_seconds=-1.0)

    def test_complete_step_without_start_raises(self) -> None:
        prog = _make_progress(total=3)
        with self.assertRaises(LookupError):
            prog.complete_step(2, duration_seconds=1.0)


# ===========================================================================
# 4. TestFailStep
# ===========================================================================

class TestFailStep(unittest.TestCase):
    """fail_step() happy and error paths — 4 tests."""

    def test_fail_step_transitions_to_failed(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(2, "Extracting emails")
        prog.fail_step(2, error="timeout after 30s", duration_seconds=30.0)
        record = prog._find_step(2)
        self.assertEqual(record.state, StepState.FAILED)
        self.assertEqual(record.error, "timeout after 30s")
        self.assertAlmostEqual(record.duration_seconds, 30.0)

    def test_fail_step_empty_error_raises(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "Something")
        with self.assertRaises(ValueError):
            prog.fail_step(1, error="", duration_seconds=1.0)

    def test_fail_step_negative_duration_raises(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "Something")
        with self.assertRaises(ValueError):
            prog.fail_step(1, error="network error", duration_seconds=-0.5)

    def test_fail_step_without_start_raises(self) -> None:
        prog = _make_progress(total=3)
        with self.assertRaises(LookupError):
            prog.fail_step(3, error="never started", duration_seconds=0.0)


# ===========================================================================
# 5. TestIsComplete
# ===========================================================================

class TestIsComplete(unittest.TestCase):
    """is_complete() truth table — 4 tests."""

    def test_not_complete_when_no_steps_started(self) -> None:
        prog = _make_progress(total=2)
        self.assertFalse(prog.is_complete())

    def test_not_complete_when_step_in_progress(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "Step one")
        self.assertFalse(prog.is_complete())

    def test_complete_when_all_steps_done(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "Step one")
        prog.complete_step(1, 1.0)
        prog.start_step(2, "Step two")
        prog.complete_step(2, 2.0)
        self.assertTrue(prog.is_complete())

    def test_complete_when_all_steps_failed(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "Step one")
        prog.fail_step(1, error="boom", duration_seconds=0.5)
        prog.start_step(2, "Step two")
        prog.fail_step(2, error="crash", duration_seconds=0.5)
        self.assertTrue(prog.is_complete())


# ===========================================================================
# 6. TestHasFailures
# ===========================================================================

class TestHasFailures(unittest.TestCase):
    """has_failures() truth table — 3 tests."""

    def test_no_failures_initially(self) -> None:
        prog = _make_progress(total=3)
        self.assertFalse(prog.has_failures())

    def test_no_failures_after_all_complete(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "A")
        prog.complete_step(1, 1.0)
        prog.start_step(2, "B")
        prog.complete_step(2, 1.0)
        self.assertFalse(prog.has_failures())

    def test_has_failures_after_one_fails(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "A")
        prog.fail_step(1, error="network error", duration_seconds=5.0)
        self.assertTrue(prog.has_failures())


# ===========================================================================
# 7. TestGetProgressBar
# ===========================================================================

class TestGetProgressBar(unittest.TestCase):
    """Progress bar content and dimensions — 5 tests."""

    def test_empty_bar_when_no_steps_done(self) -> None:
        prog = _make_progress(total=4)
        bar = prog.get_progress_bar(width=4)
        self.assertIn(_BAR_EMPTY * 4, bar)
        self.assertNotIn(_BAR_FILL, bar)

    def test_full_bar_when_all_steps_done(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "A")
        prog.complete_step(1, 1.0)
        prog.start_step(2, "B")
        prog.complete_step(2, 1.0)
        bar = prog.get_progress_bar(width=2)
        self.assertIn(_BAR_FILL * 2, bar)
        self.assertNotIn(_BAR_EMPTY, bar)

    def test_bar_width_matches_requested(self) -> None:
        prog = _make_progress(total=4)
        bar = prog.get_progress_bar(width=20)
        # Strip brackets, count inner chars
        inner = bar[1:-1]
        self.assertEqual(len(inner), 20)

    def test_bar_contains_brackets(self) -> None:
        prog = _make_progress(total=4)
        bar = prog.get_progress_bar(width=10)
        self.assertTrue(bar.startswith("["))
        self.assertTrue(bar.endswith("]"))

    def test_bar_width_less_than_2_raises(self) -> None:
        prog = _make_progress(total=4)
        with self.assertRaises(ValueError):
            prog.get_progress_bar(width=1)


# ===========================================================================
# 8. TestRenderStep
# ===========================================================================

class TestRenderStep(unittest.TestCase):
    """Per-state rendering content — 6 tests."""

    def test_complete_step_shows_checkmark(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "Navigate")
        prog.complete_step(1, 2.3)
        rendered = _strip_ansi(prog.render())
        self.assertIn(_COMPLETE_CHAR, rendered)
        self.assertIn("Navigate", rendered)
        self.assertIn("2.3s", rendered)

    def test_in_progress_step_shows_spinner(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(2, "Extracting emails")
        rendered = _strip_ansi(prog.render())
        self.assertIn(_SPINNER_CHAR, rendered)
        self.assertIn("Extracting emails", rendered)

    def test_failed_step_shows_x(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(3, "Upload result")
        prog.fail_step(3, error="timeout after 30s", duration_seconds=30.0)
        rendered = _strip_ansi(prog.render())
        self.assertIn(_FAILED_CHAR, rendered)
        self.assertIn("timeout after 30s", rendered)
        self.assertIn("30.0s", rendered)

    def test_pending_step_shows_dash(self) -> None:
        prog = _make_progress(total=3)
        # step 2 is pending (never started)
        prog.start_step(1, "Navigate")
        rendered = _strip_ansi(prog.render())
        self.assertIn(_PENDING_CHAR, rendered)

    def test_complete_step_shows_step_fraction(self) -> None:
        prog = _make_progress(total=6)
        prog.start_step(3, "Extract")
        prog.complete_step(3, 1.1)
        rendered = _strip_ansi(prog.render())
        self.assertIn("3/6", rendered)

    def test_failed_step_shows_em_dash_separator(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "Navigate")
        prog.fail_step(1, error="network error", duration_seconds=5.0)
        rendered = _strip_ansi(prog.render())
        # em dash — separates description from error
        self.assertIn("\u2014", rendered)


# ===========================================================================
# 9. TestRender
# ===========================================================================

class TestRender(unittest.TestCase):
    """Full render() output — 4 tests."""

    def test_render_contains_recipe_name(self) -> None:
        prog = ExecutionProgress(total_steps=3, recipe_name="My Special Recipe")
        rendered = _strip_ansi(prog.render())
        self.assertIn("My Special Recipe", rendered)

    def test_render_contains_progress_bar(self) -> None:
        prog = _make_progress(total=4)
        rendered = prog.render()
        self.assertIn("[", rendered)
        self.assertIn("]", rendered)

    def test_render_shows_all_step_numbers(self) -> None:
        prog = _make_progress(total=4)
        prog.start_step(1, "Step one")
        prog.complete_step(1, 1.0)
        rendered = _strip_ansi(prog.render())
        for n in range(1, 5):
            self.assertIn(f"{n}/4", rendered)

    def test_render_shows_elapsed_time(self) -> None:
        prog = _make_progress(total=2)
        rendered = _strip_ansi(prog.render())
        self.assertIn("elapsed", rendered)


# ===========================================================================
# 10. TestRenderSummary
# ===========================================================================

class TestRenderSummary(unittest.TestCase):
    """render_summary() lines for all outcomes — 5 tests."""

    def test_all_complete_summary(self) -> None:
        prog = _make_progress(total=3)
        for i in range(1, 4):
            prog.start_step(i, f"Step {i}")
            prog.complete_step(i, float(i))
        summary = _strip_ansi(prog.render_summary())
        self.assertIn("3 steps completed", summary)
        self.assertNotIn("failed", summary)

    def test_mixed_summary_shows_both_counts(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "A")
        prog.complete_step(1, 1.0)
        prog.start_step(2, "B")
        prog.fail_step(2, error="boom", duration_seconds=5.0)
        prog.start_step(3, "C")
        prog.complete_step(3, 2.0)
        summary = _strip_ansi(prog.render_summary())
        self.assertIn("2 steps completed", summary)
        self.assertIn("1 failed", summary)

    def test_summary_contains_elapsed_seconds(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "A")
        prog.complete_step(1, 1.0)
        summary = _strip_ansi(prog.render_summary())
        self.assertIn("s", summary)   # seconds unit present

    def test_all_failed_summary(self) -> None:
        prog = _make_progress(total=2)
        prog.start_step(1, "A")
        prog.fail_step(1, error="err1", duration_seconds=1.0)
        prog.start_step(2, "B")
        prog.fail_step(2, error="err2", duration_seconds=2.0)
        summary = _strip_ansi(prog.render_summary())
        self.assertIn("failed", summary)

    def test_single_step_completed_grammar(self) -> None:
        prog = _make_progress(total=1)
        prog.start_step(1, "Only step")
        prog.complete_step(1, 0.5)
        summary = _strip_ansi(prog.render_summary())
        # "1 step completed" (no plural 's')
        self.assertIn("1 step completed", summary)
        self.assertNotIn("1 steps", summary)


# ===========================================================================
# 11. TestAnsi
# ===========================================================================

class TestAnsi(unittest.TestCase):
    """ANSI helper methods wrap text with escape codes — 4 tests."""

    def test_green_wraps_with_reset(self) -> None:
        result = ANSI.green("hello")
        self.assertIn("hello", result)
        self.assertIn(ANSI.GREEN, result)
        self.assertIn(ANSI.RESET, result)

    def test_red_wraps_with_reset(self) -> None:
        result = ANSI.red("error")
        self.assertIn("error", result)
        self.assertIn(ANSI.RED, result)
        self.assertIn(ANSI.RESET, result)

    def test_yellow_wraps_with_reset(self) -> None:
        result = ANSI.yellow("warn")
        self.assertIn("warn", result)
        self.assertIn(ANSI.YELLOW, result)
        self.assertIn(ANSI.RESET, result)

    def test_dim_wraps_with_reset(self) -> None:
        result = ANSI.dim("pending")
        self.assertIn("pending", result)
        self.assertIn(ANSI.DIM, result)
        self.assertIn(ANSI.RESET, result)


# ===========================================================================
# 12. TestEdgeCases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Boundary values, restart, ordering — 5 tests."""

    def test_single_step_recipe(self) -> None:
        prog = ExecutionProgress(total_steps=1, recipe_name="Quick")
        prog.start_step(1, "Do it")
        prog.complete_step(1, 0.1)
        self.assertTrue(prog.is_complete())
        self.assertFalse(prog.has_failures())

    def test_restart_step_updates_description(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "Old description")
        prog.start_step(1, "New description")   # re-start same step
        record = prog._find_step(1)
        self.assertEqual(record.description, "New description")
        self.assertEqual(record.state, StepState.IN_PROGRESS)

    def test_steps_sorted_by_step_num(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(3, "Third")
        prog.start_step(1, "First")
        prog.start_step(2, "Second")
        nums = [s.step_num for s in prog._steps]
        self.assertEqual(nums, [1, 2, 3])

    def test_non_int_step_num_raises(self) -> None:
        prog = _make_progress(total=3)
        with self.assertRaises(TypeError):
            prog.start_step("1", "Navigate")  # type: ignore[arg-type]

    def test_mixed_complete_and_failed_is_complete(self) -> None:
        prog = _make_progress(total=3)
        prog.start_step(1, "A")
        prog.complete_step(1, 1.0)
        prog.start_step(2, "B")
        prog.fail_step(2, error="crash", duration_seconds=2.0)
        prog.start_step(3, "C")
        prog.complete_step(3, 3.0)
        self.assertTrue(prog.is_complete())
        self.assertTrue(prog.has_failures())


if __name__ == "__main__":
    unittest.main()
