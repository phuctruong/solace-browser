"""
ui/preview_explainer.py — Recipe Preview Explainer

Generates plain-English preview of recipe steps BEFORE user approves
execution. Follows the "LLM once at preview" design decision: the preview
is produced once, shown to the user, and no LLM is called during execution.

Design constraints:
  - No external dependencies (stdlib only)
  - ANSI colors for terminal display
  - Fail on bad input — no silent fallbacks
  - Specific exception catches only (Fallback Ban)

Time estimates (seconds per step action):
  navigate:   5s
  click:      3s
  input/fill: 2s
  extract:    10s
  llm_call:   15s
  <default>:  3s

Cost estimates:
  llm_call:  $0.001 per step
  all other: $0 (CPU only)

Rung: 274177
"""

from __future__ import annotations

from typing import List

# ---------------------------------------------------------------------------
# ANSI color codes (stdlib only — no external deps)
# ---------------------------------------------------------------------------

_RESET   = "\033[0m"
_BOLD    = "\033[1m"
_DIM     = "\033[2m"
_CYAN    = "\033[36m"
_GREEN   = "\033[32m"
_YELLOW  = "\033[33m"
_BLUE    = "\033[34m"
_MAGENTA = "\033[35m"
_WHITE   = "\033[97m"

# ---------------------------------------------------------------------------
# Time budget per action type (seconds)
# ---------------------------------------------------------------------------

_TIME_PER_ACTION: dict = {
    "navigate":  5,
    "click":     3,
    "input":     2,
    "fill":      2,
    "extract":   10,
    "llm_call":  15,
}

_DEFAULT_TIME_PER_ACTION: int = 3

# ---------------------------------------------------------------------------
# Cost per action type (USD)
# ---------------------------------------------------------------------------

_COST_PER_ACTION: dict = {
    "llm_call": 0.001,
}

_DEFAULT_COST_PER_ACTION: float = 0.0

# ---------------------------------------------------------------------------
# Human-readable scope descriptions
# ---------------------------------------------------------------------------

_SCOPE_DESCRIPTIONS: dict = {
    "gmail.read":          "Read Gmail inbox",
    "gmail.send":          "Send emails via Gmail",
    "gmail.compose":       "Compose Gmail drafts",
    "gmail.delete":        "Delete Gmail messages",
    "browser.navigate":    "Open URLs in your browser",
    "browser.read":        "Read page content",
    "browser.click":       "Click elements on pages",
    "browser.fill":        "Fill in form fields",
    "browser.screenshot":  "Take page screenshots",
    "browser.session":     "Manage browser sessions",
    "linkedin.read":       "Read LinkedIn profile and feed",
    "linkedin.post":       "Post to LinkedIn",
    "linkedin.delete":     "Delete LinkedIn content",
    "notion.read":         "Read Notion pages",
    "notion.write":        "Write to Notion pages",
    "twitter.read":        "Read Twitter timeline",
    "twitter.post":        "Post tweets",
    "substack.read":       "Read Substack posts",
    "substack.write":      "Publish to Substack",
}

# ---------------------------------------------------------------------------
# PreviewExplainer
# ---------------------------------------------------------------------------


class PreviewExplainer:
    """
    Generates a plain-English preview of a recipe before execution.

    Shows the user what will happen, what permissions are needed, and
    estimated time + cost — all before they approve.

    Args:
        recipe_name: Human-readable recipe name (e.g. "Morning Email Triage").
        steps:       List of step dicts. Each step must have at minimum:
                     {"action": str, "target": str, "description": str}
                     Additional keys (e.g. "scope") are allowed.
        scopes:      List of OAuth3 scope strings the recipe requires.

    Raises:
        TypeError:  If recipe_name is not a str, or steps/scopes not lists.
        ValueError: If recipe_name is empty, or any step is missing "action".
    """

    def __init__(
        self,
        recipe_name: str,
        steps: List[dict],
        scopes: List[str],
    ) -> None:
        if not isinstance(recipe_name, str):
            raise TypeError(
                f"recipe_name must be a str, got {type(recipe_name).__name__}"
            )
        if not recipe_name.strip():
            raise ValueError("recipe_name must not be empty")
        if not isinstance(steps, list):
            raise TypeError(
                f"steps must be a list, got {type(steps).__name__}"
            )
        if not isinstance(scopes, list):
            raise TypeError(
                f"scopes must be a list, got {type(scopes).__name__}"
            )

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                raise TypeError(
                    f"steps[{i}] must be a dict, got {type(step).__name__}"
                )
            if "action" not in step:
                raise ValueError(
                    f"steps[{i}] is missing required key 'action'"
                )

        self.recipe_name = recipe_name.strip()
        self.steps = steps
        self.scopes = scopes

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def render_preview(self) -> str:
        """
        Render the full preview as a terminal-ready string.

        Returns:
            Multi-line string with ANSI color codes for terminal display.
        """
        lines: List[str] = []

        # Header
        lines.append(
            f"{_BOLD}{_CYAN}Recipe: {self.recipe_name}{_RESET}"
        )
        lines.append("")

        # "This recipe will:" block
        lines.append(f"{_WHITE}This recipe will:{_RESET}")
        for i, step in enumerate(self.steps, start=1):
            lines.append(self.render_step(i, step))

        lines.append("")

        # Permissions
        if self.scopes:
            lines.append(
                f"{_YELLOW}Permissions needed:{_RESET} "
                + self.render_permissions(self.scopes)
            )
        else:
            lines.append(f"{_YELLOW}Permissions needed:{_RESET} None")

        # Time + cost on one line
        lines.append(
            f"{_BLUE}Estimated time:{_RESET} {self.estimate_time(self.steps)}"
            f"   {_GREEN}Estimated cost:{_RESET} {self.estimate_cost(self.steps)}"
        )

        lines.append("")

        # Approval prompt
        lines.append(self.render_approval_prompt())

        return "\n".join(lines)

    def render_step(self, step_num: int, step: dict) -> str:
        """
        Render a single step as a numbered plain-English line.

        Args:
            step_num: 1-based step number.
            step:     Step dict with at least {"action": str}.
                      "description" key is used if present; otherwise a
                      description is derived from "action" and "target".

        Returns:
            Indented numbered step string with ANSI formatting.

        Raises:
            TypeError:  If step is not a dict.
            ValueError: If step is missing "action" key.
        """
        if not isinstance(step, dict):
            raise TypeError(
                f"step must be a dict, got {type(step).__name__}"
            )
        if "action" not in step:
            raise ValueError("step is missing required key 'action'")

        description = step.get("description", "").strip()
        if not description:
            description = _derive_description(step)

        return f"  {_DIM}{step_num}.{_RESET} {description}"

    def estimate_time(self, steps: List[dict]) -> str:
        """
        Estimate total execution time based on step actions.

        Time budget:
          navigate:  5s | click: 3s | input/fill: 2s | extract: 10s |
          llm_call: 15s | default: 3s

        Args:
            steps: List of step dicts (each must have "action" key).

        Returns:
            Human-readable string: "~N seconds" or "~N minutes".

        Raises:
            TypeError:  If steps is not a list.
            ValueError: If any step is missing "action".
        """
        if not isinstance(steps, list):
            raise TypeError(
                f"steps must be a list, got {type(steps).__name__}"
            )

        total_seconds = 0
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                raise TypeError(
                    f"steps[{i}] must be a dict, got {type(step).__name__}"
                )
            if "action" not in step:
                raise ValueError(
                    f"steps[{i}] is missing required key 'action'"
                )
            action = step["action"].lower().strip()
            total_seconds += _TIME_PER_ACTION.get(action, _DEFAULT_TIME_PER_ACTION)

        return _format_duration(total_seconds)

    def estimate_cost(self, steps: List[dict]) -> str:
        """
        Estimate total cost in USD based on step actions.

        Only llm_call steps incur cost ($0.001 each). All CPU-only steps
        are free.

        Args:
            steps: List of step dicts (each must have "action" key).

        Returns:
            Cost string formatted as "$0.000" (always 3 decimal places).

        Raises:
            TypeError:  If steps is not a list.
            ValueError: If any step is missing "action".
        """
        if not isinstance(steps, list):
            raise TypeError(
                f"steps must be a list, got {type(steps).__name__}"
            )

        total_cost = 0.0
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                raise TypeError(
                    f"steps[{i}] must be a dict, got {type(step).__name__}"
                )
            if "action" not in step:
                raise ValueError(
                    f"steps[{i}] is missing required key 'action'"
                )
            action = step["action"].lower().strip()
            total_cost += _COST_PER_ACTION.get(action, _DEFAULT_COST_PER_ACTION)

        return f"${total_cost:.3f}"

    def render_permissions(self, scopes: List[str]) -> str:
        """
        Render a plain-English comma-separated list of OAuth3 scopes.

        Known scopes are translated to human-readable descriptions.
        Unknown scopes are shown as-is.

        Args:
            scopes: List of OAuth3 scope strings.

        Returns:
            Comma-separated human-readable permission descriptions.

        Raises:
            TypeError: If scopes is not a list.
        """
        if not isinstance(scopes, list):
            raise TypeError(
                f"scopes must be a list, got {type(scopes).__name__}"
            )

        if not scopes:
            return "None"

        descriptions = [
            _SCOPE_DESCRIPTIONS.get(scope, scope)
            for scope in scopes
        ]
        return ", ".join(descriptions)

    def render_approval_prompt(self) -> str:
        """
        Render the approval prompt shown after the preview.

        Returns:
            Approval prompt string with ANSI formatting.
        """
        return (
            f"{_BOLD}{_MAGENTA}Approve?{_RESET} "
            f"[{_GREEN}Y{_RESET}/{_DIM}n{_RESET}] "
            f"{_DIM}(auto-denies in 60 seconds){_RESET}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_description(step: dict) -> str:
    """
    Derive a plain-English description from action + target when no
    explicit "description" is provided.

    Args:
        step: Step dict with "action" key and optional "target" key.

    Returns:
        Derived description string.
    """
    action = step.get("action", "").strip()
    target = step.get("target", "").strip()

    action_verbs: dict = {
        "navigate":  "Open",
        "click":     "Click on",
        "input":     "Type into",
        "fill":      "Fill in",
        "extract":   "Extract data from",
        "llm_call":  "Process with AI",
        "screenshot":"Take screenshot of",
        "scroll":    "Scroll",
        "wait":      "Wait for",
        "verify":    "Verify",
        "session":   "Manage session for",
        "branch":    "Branch based on",
        "transform": "Transform",
    }

    verb = action_verbs.get(action.lower(), action.capitalize())

    if target:
        return f"{verb} {target}"
    return verb


def _format_duration(total_seconds: int) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Under 60s:  "~N seconds"
    60s+:       "~N minutes" (rounded up to nearest minute)

    Args:
        total_seconds: Duration in seconds (non-negative int).

    Returns:
        Formatted duration string.
    """
    if total_seconds < 60:
        return f"~{total_seconds} seconds"

    # Round up to nearest whole minute
    minutes = (total_seconds + 59) // 60
    return f"~{minutes} minutes"
