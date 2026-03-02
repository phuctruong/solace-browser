"""
execution_progress.py — Step-by-step execution progress UI

Tracks and renders recipe execution progress in the terminal.

Displays:
  - "Step 3/6: Extracting emails..."              (in-progress, spinner)
  - "✓ Step 1/6: Navigating to Gmail (2.3s)"      (complete, green)
  - "✗ Step 3/6: Extracting emails — timeout..."   (failed, red)
  - "- Step 4/6: Filtering by date"                (pending, dim)

No external dependencies — stdlib only.
ANSI colors: green=complete, yellow=in-progress, red=failed, dim=pending.

Rung: 641
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# ANSI color helpers (stdlib-only, no third-party deps)
# ---------------------------------------------------------------------------

class ANSI:
    """Terminal escape codes. Use reset() after every colored segment."""

    RESET  = "\033[0m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    RED    = "\033[31m"
    DIM    = "\033[2m"
    BOLD   = "\033[1m"

    @staticmethod
    def green(text: str) -> str:
        return f"{ANSI.GREEN}{text}{ANSI.RESET}"

    @staticmethod
    def yellow(text: str) -> str:
        return f"{ANSI.YELLOW}{text}{ANSI.RESET}"

    @staticmethod
    def red(text: str) -> str:
        return f"{ANSI.RED}{text}{ANSI.RESET}"

    @staticmethod
    def dim(text: str) -> str:
        return f"{ANSI.DIM}{text}{ANSI.RESET}"

    @staticmethod
    def bold(text: str) -> str:
        return f"{ANSI.BOLD}{text}{ANSI.RESET}"


# ---------------------------------------------------------------------------
# Step state enum
# ---------------------------------------------------------------------------

class StepState(str, Enum):
    """Life-cycle state of a single execution step."""

    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE    = "complete"
    FAILED      = "failed"


# ---------------------------------------------------------------------------
# Step record dataclass
# ---------------------------------------------------------------------------

@dataclass
class StepRecord:
    """Immutable-ish record for a single recipe step."""

    step_num: int
    description: str
    state: StepState = StepState.PENDING
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    started_at: Optional[float] = None   # monotonic timestamp


# ---------------------------------------------------------------------------
# ExecutionProgress
# ---------------------------------------------------------------------------

_SPINNER_FRAMES: List[str] = ["⟳", "⟳", "⟳", "⟳"]   # single-char, no animation needed
_SPINNER_CHAR   = "⟳"
_COMPLETE_CHAR  = "✓"
_FAILED_CHAR    = "✗"
_PENDING_CHAR   = "-"
_BAR_FILL       = "█"
_BAR_EMPTY      = "░"


class ExecutionProgress:
    """
    Tracks and renders step-by-step recipe execution progress.

    Usage::

        prog = ExecutionProgress(total_steps=6, recipe_name="Extract Gmail")
        prog.start_step(1, "Navigating to Gmail")
        prog.complete_step(1, duration_seconds=1.4)
        prog.start_step(2, "Extracting emails")
        prog.fail_step(2, error="timeout after 30s", duration_seconds=30.0)
        print(prog.render())
        print(prog.render_summary())
    """

    def __init__(self, total_steps: int, recipe_name: str) -> None:
        if total_steps < 1:
            raise ValueError(f"total_steps must be >= 1, got {total_steps}")
        if not recipe_name or not recipe_name.strip():
            raise ValueError("recipe_name must be a non-empty string")

        self._total_steps: int = total_steps
        self._recipe_name: str = recipe_name.strip()
        self._steps: List[StepRecord] = []
        self._started_at: float = time.monotonic()

    # ------------------------------------------------------------------
    # Public mutators
    # ------------------------------------------------------------------

    def start_step(self, step_num: int, description: str) -> None:
        """Mark a step as in-progress. Creates the record if it does not exist."""
        self._validate_step_num(step_num)
        if not description or not description.strip():
            raise ValueError("description must be a non-empty string")

        record = self._find_step(step_num)
        if record is None:
            record = StepRecord(step_num=step_num, description=description.strip())
            self._steps.append(record)
            self._steps.sort(key=lambda s: s.step_num)
        else:
            record.description = description.strip()

        record.state = StepState.IN_PROGRESS
        record.started_at = time.monotonic()

    def complete_step(self, step_num: int, duration_seconds: float) -> None:
        """Mark a step as complete with its measured duration."""
        self._validate_step_num(step_num)
        if duration_seconds < 0:
            raise ValueError(f"duration_seconds must be >= 0, got {duration_seconds}")

        record = self._require_step(step_num)
        record.state = StepState.COMPLETE
        record.duration_seconds = duration_seconds

    def fail_step(self, step_num: int, error: str, duration_seconds: float) -> None:
        """Mark a step as failed with error message and measured duration."""
        self._validate_step_num(step_num)
        if not error or not error.strip():
            raise ValueError("error must be a non-empty string")
        if duration_seconds < 0:
            raise ValueError(f"duration_seconds must be >= 0, got {duration_seconds}")

        record = self._require_step(step_num)
        record.state = StepState.FAILED
        record.error = error.strip()
        record.duration_seconds = duration_seconds

    # ------------------------------------------------------------------
    # Public queries
    # ------------------------------------------------------------------

    def is_complete(self) -> bool:
        """True when every step has reached COMPLETE or FAILED state."""
        if len(self._steps) < self._total_steps:
            return False
        return all(s.state in (StepState.COMPLETE, StepState.FAILED) for s in self._steps)

    def has_failures(self) -> bool:
        """True when at least one step is in FAILED state."""
        return any(s.state == StepState.FAILED for s in self._steps)

    def get_progress_bar(self, width: int = 40) -> str:
        """
        Return an ASCII progress bar of the given character width.

        Example: [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]
        """
        if width < 2:
            raise ValueError(f"width must be >= 2, got {width}")

        completed = sum(
            1 for s in self._steps
            if s.state in (StepState.COMPLETE, StepState.FAILED)
        )
        filled = int(round(width * completed / self._total_steps))
        filled = max(0, min(width, filled))
        bar_inner = _BAR_FILL * filled + _BAR_EMPTY * (width - filled)
        return f"[{bar_inner}]"

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> str:
        """
        Render the full step list with header and progress bar.

        Returns a multi-line string suitable for printing to a terminal.
        """
        lines: List[str] = []

        # Header
        elapsed = self._elapsed_seconds()
        header = ANSI.bold(f"Recipe: {self._recipe_name}")
        lines.append(header)

        # Progress bar
        bar = self.get_progress_bar(width=40)
        completed_count = sum(
            1 for s in self._steps
            if s.state in (StepState.COMPLETE, StepState.FAILED)
        )
        lines.append(
            f"{ANSI.yellow(bar)}  {completed_count}/{self._total_steps} steps  "
            f"({elapsed:.1f}s elapsed)"
        )
        lines.append("")

        # Build a lookup for known steps
        known: dict[int, StepRecord] = {s.step_num: s for s in self._steps}

        for n in range(1, self._total_steps + 1):
            if n in known:
                lines.append(self._render_step(known[n]))
            else:
                # Implicitly pending step (never started)
                lines.append(
                    ANSI.dim(
                        f"  {_PENDING_CHAR} Step {n}/{self._total_steps}: (not yet started)"
                    )
                )

        return "\n".join(lines)

    def render_summary(self) -> str:
        """
        Return a one-line final summary.

        Examples:
          "6 steps completed in 47.2s"
          "5 steps completed, 1 failed in 47.2s"
        """
        elapsed = self._elapsed_seconds()
        completed = sum(1 for s in self._steps if s.state == StepState.COMPLETE)
        failed    = sum(1 for s in self._steps if s.state == StepState.FAILED)

        if failed == 0:
            summary = f"{completed} step{'s' if completed != 1 else ''} completed in {elapsed:.1f}s"
            return ANSI.green(summary)

        parts: List[str] = []
        if completed > 0:
            parts.append(f"{completed} step{'s' if completed != 1 else ''} completed")
        parts.append(f"{failed} failed")
        summary = ", ".join(parts) + f" in {elapsed:.1f}s"
        return ANSI.red(summary)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render_step(self, record: StepRecord) -> str:
        n     = record.step_num
        total = self._total_steps
        desc  = record.description

        if record.state == StepState.COMPLETE:
            dur_str = f" ({record.duration_seconds:.1f}s)" if record.duration_seconds is not None else ""
            line = f"  {_COMPLETE_CHAR} Step {n}/{total}: {desc}{dur_str}"
            return ANSI.green(line)

        if record.state == StepState.IN_PROGRESS:
            line = f"  {_SPINNER_CHAR} Step {n}/{total}: {desc}..."
            return ANSI.yellow(line)

        if record.state == StepState.FAILED:
            error_part = f" \u2014 {record.error}" if record.error else ""
            dur_str = f" ({record.duration_seconds:.1f}s)" if record.duration_seconds is not None else ""
            line = f"  {_FAILED_CHAR} Step {n}/{total}: {desc}{error_part}{dur_str}"
            return ANSI.red(line)

        # PENDING
        line = f"  {_PENDING_CHAR} Step {n}/{total}: {desc}"
        return ANSI.dim(line)

    def _elapsed_seconds(self) -> float:
        return time.monotonic() - self._started_at

    def _validate_step_num(self, step_num: int) -> None:
        if not isinstance(step_num, int):
            raise TypeError(f"step_num must be int, got {type(step_num).__name__}")
        if step_num < 1 or step_num > self._total_steps:
            raise ValueError(
                f"step_num {step_num} out of range [1, {self._total_steps}]"
            )

    def _find_step(self, step_num: int) -> Optional[StepRecord]:
        for s in self._steps:
            if s.step_num == step_num:
                return s
        return None

    def _require_step(self, step_num: int) -> StepRecord:
        record = self._find_step(step_num)
        if record is None:
            raise LookupError(
                f"Step {step_num} has not been started — call start_step() first"
            )
        return record
