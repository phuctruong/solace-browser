"""
LiveDiagram — Mermaid stateDiagram-v2 generator for recipe execution state.
SolaceBrowser | Belt: Yellow | Rung: 65537

Converts live recipe execution state (pending/running/done/failed steps) into
Mermaid stateDiagram-v2 markup that can be rendered in any browser with the
Mermaid JS library. Used to give users a live visual of recipe progress.

DNA: render(steps) x mermaid x stateDiagram-v2 = live_progress_UI

Public API:
  LiveDiagram(recipe_name, steps)  — instantiate with step list
  render() -> str                  — generate Mermaid stateDiagram-v2 markup
  highlight_current() -> int|None  — step_num of currently running step, or None
  completion_pct() -> float        — fraction of done+failed steps (0.0 to 1.0)

Step dict shape:
  {"step_num": int, "action": str, "status": "pending"|"running"|"done"|"failed"}

Status symbols in notes:
  done    → ✓
  running → →
  failed  → ✗
  pending → ○

FALLBACK BAN: No except Exception: pass. No broad catches. No silent failure.
Stdlib only — no external dependencies.

Rung: 65537
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Status → display symbol mapping
# ---------------------------------------------------------------------------

_STATUS_SYMBOL: dict[str, str] = {
    "done":    "✓",
    "running": "→",
    "failed":  "✗",
    "pending": "○",
}

_VALID_STATUSES = frozenset(_STATUS_SYMBOL.keys())

# Mermaid node ID prefix (must be safe identifier characters)
_NODE_PREFIX = "Step"


def _node_id(step_num: int) -> str:
    """Return the Mermaid node identifier for a step number."""
    return f"{_NODE_PREFIX}{step_num}"


def _validate_steps(steps: list[dict]) -> None:
    """Validate that steps is a list of dicts with required fields.

    Raises:
        TypeError:  If steps is not a list or any element is not a dict.
        ValueError: If any step dict is missing required keys or has invalid values.
    """
    if not isinstance(steps, list):
        raise TypeError(f"steps must be list, got {type(steps).__name__!r}")

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise TypeError(
                f"steps[{i}] must be dict, got {type(step).__name__!r}"
            )
        if "step_num" not in step:
            raise ValueError(f"steps[{i}] missing required key 'step_num'")
        if "action" not in step:
            raise ValueError(f"steps[{i}] missing required key 'action'")
        if "status" not in step:
            raise ValueError(f"steps[{i}] missing required key 'status'")
        if not isinstance(step["step_num"], int):
            raise TypeError(
                f"steps[{i}]['step_num'] must be int, got {type(step['step_num']).__name__!r}"
            )
        status = step["status"]
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"steps[{i}]['status'] must be one of {sorted(_VALID_STATUSES)!r}, "
                f"got {status!r}"
            )


# ---------------------------------------------------------------------------
# LiveDiagram — main class
# ---------------------------------------------------------------------------

class LiveDiagram:
    """Generates Mermaid stateDiagram-v2 markup from recipe execution state.

    Instantiate with a recipe name and a list of step dicts. Call render()
    to get the Mermaid markup. Call highlight_current() to find the running
    step. Call completion_pct() to get progress fraction.

    Status symbols in notes:
      done    → ✓ (check mark)
      running → → (arrow, currently executing)
      failed  → ✗ (cross mark)
      pending → ○ (circle, not yet started)

    FALLBACK BAN enforced: no broad exception catches, no silent failures.

    Rung: 65537
    """

    def __init__(self, recipe_name: str, steps: list[dict]) -> None:
        """Initialise the diagram with a recipe name and step list.

        Args:
            recipe_name: Display name of the recipe being executed.
            steps:       List of step dicts, each with:
                           - step_num: int
                           - action:   str
                           - status:   "pending"|"running"|"done"|"failed"

        Raises:
            TypeError:  If recipe_name is not str, or steps is not a list of dicts.
            ValueError: If recipe_name is empty, or any step dict has invalid values.
        """
        if not isinstance(recipe_name, str):
            raise TypeError(
                f"recipe_name must be str, got {type(recipe_name).__name__!r}"
            )
        recipe_name = recipe_name.strip()
        if not recipe_name:
            raise ValueError("recipe_name must not be empty")

        _validate_steps(steps)

        self._recipe_name = recipe_name
        # Sort steps by step_num for deterministic rendering
        self._steps: list[dict] = sorted(steps, key=lambda s: s["step_num"])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Return Mermaid stateDiagram-v2 markup for the current execution state.

        Format:
          stateDiagram-v2
              [*] --> Step1
              Step1 --> Step2
              Step2 --> [*]

              note right of Step1 : navigate (✓)
              note right of Step2 : click (→)

        Empty steps list → minimal diagram with only [*] transition.

        Returns:
            Mermaid stateDiagram-v2 markup string.
        """
        lines: list[str] = ["stateDiagram-v2"]

        if not self._steps:
            lines.append("    [*] --> [*]")
            return "\n".join(lines)

        # Build state transitions: [*] → Step1 → Step2 → ... → [*]
        first_id = _node_id(self._steps[0]["step_num"])
        lines.append(f"    [*] --> {first_id}")

        for i in range(len(self._steps) - 1):
            current_id = _node_id(self._steps[i]["step_num"])
            next_id = _node_id(self._steps[i + 1]["step_num"])
            lines.append(f"    {current_id} --> {next_id}")

        last_id = _node_id(self._steps[-1]["step_num"])
        lines.append(f"    {last_id} --> [*]")

        # Blank line before notes
        lines.append("")

        # Add notes for each step showing action and status symbol
        for step in self._steps:
            node_id = _node_id(step["step_num"])
            action = step.get("action", "unknown").strip() or "unknown"
            status = step["status"]
            symbol = _STATUS_SYMBOL[status]
            lines.append(f"    note right of {node_id} : {action} ({symbol})")

        return "\n".join(lines)

    def highlight_current(self) -> int | None:
        """Return step_num of the currently running step, or None.

        If multiple steps have status "running" (should not happen in normal
        execution but is not forbidden), returns the first one by step_num.

        Returns:
            step_num int if a running step exists, else None.
        """
        for step in self._steps:
            if step["status"] == "running":
                return step["step_num"]
        return None

    def completion_pct(self) -> float:
        """Return the fraction of completed steps (0.0 to 1.0).

        Both "done" and "failed" count as completed. "pending" and "running"
        do not count. Empty step list → 0.0.

        Returns:
            Float in range [0.0, 1.0].
        """
        if not self._steps:
            return 0.0

        completed = sum(
            1 for step in self._steps
            if step["status"] in ("done", "failed")
        )
        return completed / len(self._steps)

    # ------------------------------------------------------------------
    # Properties (read-only)
    # ------------------------------------------------------------------

    @property
    def recipe_name(self) -> str:
        """The recipe name this diagram was created for."""
        return self._recipe_name

    @property
    def steps(self) -> list[dict]:
        """Copy of the step list (sorted by step_num)."""
        return list(self._steps)
