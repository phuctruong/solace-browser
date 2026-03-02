"""
EvidenceSummaryFormatter — plain-English summary of recipe execution evidence.
SolaceBrowser | Belt: Yellow | Rung: 65537

Converts raw action dicts (type, target, result, duration_ms) into human-readable
summaries. Used post-execution to show users exactly what happened, how long it
took, and where the full evidence lives.

DNA: format(actions, steps) x evidence x plain-English = trust_UI

Public API:
  EvidenceSummaryFormatter                         — stateless class (all methods static)
  format_action_summary(actions) -> str            — grouped plain-English summary
  format_step_timing(steps) -> str                 — per-step pipe-delimited timing
  link_to_evidence(evidence_dir, label) -> str     — plain-text path link

Action dict shape:
  {"type": str, "target": str, "result": str, "duration_ms": int}

Step dict shape:
  {"step_num": int, "action": str, "duration_ms": int, "status": str}

FALLBACK BAN: No except Exception: pass. No broad catches. No silent failure.
Stdlib only — no external dependencies.

Rung: 65537
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

# ---------------------------------------------------------------------------
# Action type → human-readable verb mapping
# Each verb is designed to read naturally in the past tense when combined
# with a count: "3 emails navigated" → too awkward; use full result phrases.
# We group by (type, result) and render as "N <result_phrase>".
# ---------------------------------------------------------------------------

# Maps action type → fallback plural noun when no result grouping exists.
_TYPE_NOUN: dict[str, str] = {
    "navigate":   "pages navigated",
    "click":      "clicks",
    "extract":    "items extracted",
    "llm_call":   "LLM calls",
    "screenshot": "screenshots",
    "input":      "inputs",
    "scroll":     "scrolls",
    "wait":       "waits",
    "submit":     "submissions",
    "download":   "downloads",
    "upload":     "uploads",
}


def _pluralise(noun: str, count: int) -> str:
    """Return "N noun" — no smart pluralisation, callers pass plural nouns."""
    return f"{count} {noun}"


def _format_total_time(total_ms: int) -> str:
    """Format milliseconds as Ns or Nmin Ns.

    Args:
        total_ms: Total duration in milliseconds.

    Returns:
        Formatted time string, e.g. "47s" or "2min 3s".
    """
    total_s = total_ms // 1000
    if total_s < 60:
        return f"{total_s}s"
    minutes = total_s // 60
    seconds = total_s % 60
    return f"{minutes}min {seconds}s"


def _summarise_actions(actions: list[dict]) -> str:
    """Group actions by result string and produce comma-joined phrase list.

    Strategy:
      1. Group actions that share the same result string.
      2. For groups with a non-empty result, use "N <result>" phrasing.
      3. For actions with empty/missing result, fall back to type noun.

    Args:
        actions: List of action dicts (type, target, result, duration_ms).

    Returns:
        Comma-separated summary phrase string (no trailing period).
    """
    # result_str → count
    result_counts: dict[str, int] = {}
    # type noun → count (for actions without a meaningful result)
    type_counts: dict[str, int] = {}

    for action in actions:
        if not isinstance(action, dict):
            raise TypeError(f"Each action must be a dict, got {type(action).__name__!r}")
        result = action.get("result", "").strip()
        action_type = action.get("type", "").strip().lower()

        if result:
            result_counts[result] = result_counts.get(result, 0) + 1
        else:
            noun = _TYPE_NOUN.get(action_type, "tasks")
            type_counts[noun] = type_counts.get(noun, 0) + 1

    parts: list[str] = []
    for result_str, count in result_counts.items():
        parts.append(_pluralise(result_str, count))
    for noun, count in type_counts.items():
        parts.append(_pluralise(noun, count))

    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def format_action_summary(actions: list[dict]) -> str:
    """Return plain-English summary of completed recipe actions.

    Example output: "6 emails triaged, 2 marked important, 1 draft created. Time: 47s"

    Each action dict must have:
      - "type": str       — action category (navigate, click, extract, llm_call, etc.)
      - "target": str     — what the action operated on
      - "result": str     — outcome description (used for grouping)
      - "duration_ms": int — time taken in milliseconds

    Rules:
      - Group by result string (count identical result phrases)
      - Unknown action types without a result → count as "tasks"
      - Total time = sum of all duration_ms / 1000, formatted as Ns or Nmin Ns
      - Empty list → "No actions recorded."

    Args:
        actions: List of action dicts.

    Returns:
        Human-readable summary string.

    Raises:
        TypeError: If actions is not a list, or any element is not a dict.
    """
    return EvidenceSummaryFormatter.format_action_summary(actions)


def format_step_timing(steps: list[dict]) -> str:
    """Return per-step timing string.

    Example: "Step 1: navigate (0.3s) | Step 2: extract (2.1s)"
    Failed steps: "Step N: action FAILED"

    Each step dict must have:
      - "step_num": int    — step number (1-based)
      - "action": str      — action type name
      - "duration_ms": int — time taken in milliseconds
      - "status": str      — "done", "failed", "running", "pending"

    Args:
        steps: List of step dicts.

    Returns:
        Pipe-delimited per-step timing string.

    Raises:
        TypeError: If steps is not a list, or any element is not a dict.
    """
    return EvidenceSummaryFormatter.format_step_timing(steps)


def link_to_evidence(evidence_dir: Union[str, Path], label: str = "Full evidence") -> str:
    """Return a plain-text link pointing to the evidence directory.

    Format: "Full evidence: /path/to/evidence/dir"

    Args:
        evidence_dir: Path (str or Path) to the evidence directory.
        label:        Display label for the link. Defaults to "Full evidence".

    Returns:
        Plain-text link string.

    Raises:
        TypeError:  If evidence_dir is not a str or Path.
        ValueError: If label is empty after stripping.
    """
    return EvidenceSummaryFormatter.link_to_evidence(evidence_dir, label=label)


# ---------------------------------------------------------------------------
# EvidenceSummaryFormatter — main class
# ---------------------------------------------------------------------------

class EvidenceSummaryFormatter:
    """Stateless helper class for formatting recipe execution evidence.

    All methods are static — instantiate EvidenceSummaryFormatter() for
    attribute access, or call the module-level functions directly.

    FALLBACK BAN enforced: no broad exception catches, no silent failures.

    Rung: 65537
    """

    @staticmethod
    def format_action_summary(actions: list[dict]) -> str:
        """Return plain-English summary of completed recipe actions.

        Args:
            actions: List of action dicts with keys: type, target, result, duration_ms.

        Returns:
            Human-readable summary string. Empty list → "No actions recorded."

        Raises:
            TypeError: If actions is not a list or any element is not a dict.
        """
        if not isinstance(actions, list):
            raise TypeError(f"actions must be list, got {type(actions).__name__!r}")

        if not actions:
            return "No actions recorded."

        # Validate and collect duration
        total_ms = 0
        for action in actions:
            if not isinstance(action, dict):
                raise TypeError(f"Each action must be a dict, got {type(action).__name__!r}")
            duration = action.get("duration_ms", 0)
            if not isinstance(duration, int):
                raise TypeError(
                    f"duration_ms must be int, got {type(duration).__name__!r}"
                )
            total_ms += duration

        phrase = _summarise_actions(actions)
        time_str = _format_total_time(total_ms)

        if phrase:
            return f"{phrase}. Time: {time_str}"
        return f"No actions recorded. Time: {time_str}"

    @staticmethod
    def format_step_timing(steps: list[dict]) -> str:
        """Return per-step timing: "Step 1: navigate (0.3s) | Step 2: extract (2.1s)".

        Failed steps appear as: "Step N: action FAILED"

        Args:
            steps: List of step dicts with keys: step_num, action, duration_ms, status.

        Returns:
            Pipe-delimited timing string. Empty list → "No steps recorded."

        Raises:
            TypeError: If steps is not a list or any element is not a dict.
        """
        if not isinstance(steps, list):
            raise TypeError(f"steps must be list, got {type(steps).__name__!r}")

        if not steps:
            return "No steps recorded."

        parts: list[str] = []
        for step in steps:
            if not isinstance(step, dict):
                raise TypeError(f"Each step must be a dict, got {type(step).__name__!r}")

            step_num = step.get("step_num", "?")
            action = step.get("action", "unknown").strip() or "unknown"
            status = step.get("status", "").strip().lower()
            duration_ms = step.get("duration_ms", 0)

            if not isinstance(duration_ms, int):
                raise TypeError(
                    f"duration_ms must be int, got {type(duration_ms).__name__!r}"
                )

            if status == "failed":
                parts.append(f"Step {step_num}: {action} FAILED")
            else:
                duration_s = duration_ms / 1000
                # Format: 0.3s (1 decimal), no trailing zero beyond one decimal
                time_str = f"{duration_s:.1f}s"
                parts.append(f"Step {step_num}: {action} ({time_str})")

        return " | ".join(parts)

    @staticmethod
    def link_to_evidence(
        evidence_dir: Union[str, Path],
        label: str = "Full evidence",
    ) -> str:
        """Return a plain-text link to the evidence directory.

        Format: "Full evidence: /path/to/evidence/dir"

        Args:
            evidence_dir: Path to the evidence directory (str or Path).
            label:        Link label text. Defaults to "Full evidence".

        Returns:
            Plain-text link string.

        Raises:
            TypeError:  If evidence_dir is not str or Path, or label is not str.
            ValueError: If label is empty after stripping.
        """
        if not isinstance(evidence_dir, (str, Path)):
            raise TypeError(
                f"evidence_dir must be str or Path, got {type(evidence_dir).__name__!r}"
            )
        if not isinstance(label, str):
            raise TypeError(f"label must be str, got {type(label).__name__!r}")

        label = label.strip()
        if not label:
            raise ValueError("label must not be empty")

        path_str = str(evidence_dir)
        return f"{label}: {path_str}"
