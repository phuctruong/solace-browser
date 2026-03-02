"""
LiveDiagram — Acceptance Tests
SolaceBrowser T6 | Belt: Yellow | Rung: 65537

Tests (12 total):
  T01  test_empty_steps_minimal_diagram
  T02  test_single_step_renders_correctly
  T03  test_all_done_steps
  T04  test_one_running_step_highlight
  T05  test_mixed_states_render_correct_symbols
  T06  test_completion_pct_all_pending
  T07  test_completion_pct_all_done
  T08  test_completion_pct_mixed
  T09  test_highlight_current_no_running
  T10  test_highlight_current_returns_step_num
  T11  test_mermaid_output_format
  T12  test_failed_step_rendering

  T13  test_recipe_name_required
  T14  test_invalid_status_raises
  T15  test_completion_pct_failed_counts_as_done

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_live_diagram.py -v

Rung: 65537
"""

import sys
from pathlib import Path

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ui.live_diagram import LiveDiagram


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_step(
    step_num: int,
    action: str = "navigate",
    status: str = "pending",
) -> dict:
    return {"step_num": step_num, "action": action, "status": status}


# ---------------------------------------------------------------------------
# T01-T02: Empty and single step
# ---------------------------------------------------------------------------

class TestBasicRendering:
    """Tests for LiveDiagram basic rendering."""

    def test_empty_steps_minimal_diagram(self):
        """T01: Empty steps → stateDiagram-v2 with [*] --> [*]"""
        diagram = LiveDiagram("test-recipe", [])
        output = diagram.render()
        assert output.startswith("stateDiagram-v2")
        assert "[*] --> [*]" in output

    def test_single_step_renders_correctly(self):
        """T02: Single step → [*] --> Step1, Step1 --> [*], note right of Step1"""
        steps = [_make_step(1, "navigate", "done")]
        diagram = LiveDiagram("my-recipe", steps)
        output = diagram.render()
        assert "stateDiagram-v2" in output
        assert "[*] --> Step1" in output
        assert "Step1 --> [*]" in output
        assert "note right of Step1" in output
        assert "navigate" in output
        assert "✓" in output  # done symbol

    def test_all_done_steps(self):
        """T03: All done steps → all nodes present, all show ✓"""
        steps = [
            _make_step(1, "navigate", "done"),
            _make_step(2, "click", "done"),
            _make_step(3, "extract", "done"),
        ]
        diagram = LiveDiagram("recipe", steps)
        output = diagram.render()
        assert "Step1 --> Step2" in output
        assert "Step2 --> Step3" in output
        assert output.count("✓") == 3

    def test_one_running_step_highlight(self):
        """T04: Step with status running → shown with → symbol"""
        steps = [
            _make_step(1, "navigate", "done"),
            _make_step(2, "click", "running"),
            _make_step(3, "extract", "pending"),
        ]
        diagram = LiveDiagram("recipe", steps)
        output = diagram.render()
        # Running step note should contain →
        assert "click (→)" in output

    def test_mixed_states_render_correct_symbols(self):
        """T05: Mixed states → each status symbol appears correctly."""
        steps = [
            _make_step(1, "navigate", "done"),
            _make_step(2, "click", "running"),
            _make_step(3, "extract", "failed"),
            _make_step(4, "screenshot", "pending"),
        ]
        diagram = LiveDiagram("recipe", steps)
        output = diagram.render()
        assert "navigate (✓)" in output
        assert "click (→)" in output
        assert "extract (✗)" in output
        assert "screenshot (○)" in output


# ---------------------------------------------------------------------------
# T06-T08: completion_pct
# ---------------------------------------------------------------------------

class TestCompletionPct:
    """Tests for LiveDiagram.completion_pct."""

    def test_completion_pct_all_pending(self):
        """T06: All pending → 0.0"""
        steps = [_make_step(i, status="pending") for i in range(1, 4)]
        diagram = LiveDiagram("recipe", steps)
        assert diagram.completion_pct() == 0.0

    def test_completion_pct_all_done(self):
        """T07: All done → 1.0"""
        steps = [_make_step(i, status="done") for i in range(1, 4)]
        diagram = LiveDiagram("recipe", steps)
        assert diagram.completion_pct() == 1.0

    def test_completion_pct_mixed(self):
        """T08: 2 done out of 4 → 0.5"""
        steps = [
            _make_step(1, status="done"),
            _make_step(2, status="done"),
            _make_step(3, status="pending"),
            _make_step(4, status="pending"),
        ]
        diagram = LiveDiagram("recipe", steps)
        assert diagram.completion_pct() == 0.5

    def test_completion_pct_failed_counts_as_done(self):
        """T15: Failed steps count as completed in pct calculation."""
        steps = [
            _make_step(1, status="done"),
            _make_step(2, status="failed"),
            _make_step(3, status="pending"),
        ]
        diagram = LiveDiagram("recipe", steps)
        # 2 out of 3 are done/failed
        assert abs(diagram.completion_pct() - 2 / 3) < 1e-9

    def test_completion_pct_empty_steps(self):
        """Empty steps → 0.0"""
        diagram = LiveDiagram("recipe", [])
        assert diagram.completion_pct() == 0.0


# ---------------------------------------------------------------------------
# T09-T10: highlight_current
# ---------------------------------------------------------------------------

class TestHighlightCurrent:
    """Tests for LiveDiagram.highlight_current."""

    def test_highlight_current_no_running(self):
        """T09: No running step → None"""
        steps = [
            _make_step(1, status="done"),
            _make_step(2, status="pending"),
        ]
        diagram = LiveDiagram("recipe", steps)
        assert diagram.highlight_current() is None

    def test_highlight_current_returns_step_num(self):
        """T10: Running step → returns its step_num."""
        steps = [
            _make_step(1, status="done"),
            _make_step(2, status="running"),
            _make_step(3, status="pending"),
        ]
        diagram = LiveDiagram("recipe", steps)
        assert diagram.highlight_current() == 2

    def test_highlight_current_empty(self):
        """Empty steps → None"""
        diagram = LiveDiagram("recipe", [])
        assert diagram.highlight_current() is None


# ---------------------------------------------------------------------------
# T11-T12: Mermaid output format and failed step
# ---------------------------------------------------------------------------

class TestMermaidOutput:
    """Tests for Mermaid stateDiagram-v2 format compliance."""

    def test_mermaid_output_format(self):
        """T11: Output starts with stateDiagram-v2 header."""
        steps = [_make_step(1, "navigate", "done")]
        diagram = LiveDiagram("recipe", steps)
        output = diagram.render()
        lines = output.splitlines()
        assert lines[0] == "stateDiagram-v2"

    def test_failed_step_rendering(self):
        """T12: Failed step → shown with ✗ symbol in note."""
        steps = [_make_step(1, "navigate", "failed")]
        diagram = LiveDiagram("recipe", steps)
        output = diagram.render()
        assert "navigate (✗)" in output
        assert "Step1 --> [*]" in output

    def test_transitions_chain_in_order(self):
        """Steps render as a sequential chain from [*] through all nodes to [*]."""
        steps = [
            _make_step(1, "navigate", "done"),
            _make_step(2, "click", "done"),
            _make_step(3, "extract", "pending"),
        ]
        diagram = LiveDiagram("recipe", steps)
        output = diagram.render()
        assert "[*] --> Step1" in output
        assert "Step1 --> Step2" in output
        assert "Step2 --> Step3" in output
        assert "Step3 --> [*]" in output


# ---------------------------------------------------------------------------
# T13-T14: Input validation
# ---------------------------------------------------------------------------

class TestValidation:
    """Tests for LiveDiagram input validation."""

    def test_recipe_name_required(self):
        """T13: Empty recipe name raises ValueError."""
        with pytest.raises(ValueError, match="recipe_name must not be empty"):
            LiveDiagram("   ", [])

    def test_invalid_status_raises(self):
        """T14: Invalid status string raises ValueError."""
        steps = [{"step_num": 1, "action": "navigate", "status": "INVALID"}]
        with pytest.raises(ValueError, match="status"):
            LiveDiagram("recipe", steps)

    def test_steps_not_list_raises(self):
        """Non-list steps raises TypeError."""
        with pytest.raises(TypeError, match="steps must be list"):
            LiveDiagram("recipe", "not a list")

    def test_recipe_name_not_str_raises(self):
        """Non-string recipe_name raises TypeError."""
        with pytest.raises(TypeError, match="recipe_name must be str"):
            LiveDiagram(42, [])

    def test_step_missing_step_num_raises(self):
        """Step dict missing step_num raises ValueError."""
        steps = [{"action": "navigate", "status": "done"}]
        with pytest.raises(ValueError, match="step_num"):
            LiveDiagram("recipe", steps)
