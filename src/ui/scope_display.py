"""
ScopeDisplay — plain-English OAuth3 scope confirmation UI
SolaceBrowser | Belt: Yellow | Rung: 641

Converts OAuth3 scope strings (e.g. "gmail.read.inbox") into human-readable
terminal confirmation modals. Used at the point of permission grant: the
user sees exactly what a recipe is asking for, in plain English, with risk
colour-coding, before approving.

DNA: display(describe, categorize, diff, render) x OAuth3 x ANSI = consent_UI

Public API:
  ScopeDisplay                       — stateless helper class (all methods static)
  describe_scope(scope) -> str       — single scope → plain English
  categorize_scopes(scopes) -> dict  — group scopes by app/platform
  render_scope_modal(scopes, name)   — full ANSI terminal modal string
  render_scope_diff(old, new) -> str — added / removed scope comparison

Risk levels (fail-closed — unknown scope = HIGH):
  LOW    — read-only scopes  (green ANSI)
  MEDIUM — write/send scopes (yellow ANSI)
  HIGH   — admin/delete scopes (red ANSI)

FALLBACK BAN: No except Exception: pass. No broad catches. No silent failure.
Stdlib only — no external dependencies.

Rung: 641
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Resolve src/ so oauth3 imports work when this module is used standalone
# ---------------------------------------------------------------------------

_SRC_PATH = Path(__file__).parent.parent
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from oauth3.scopes import (
    get_scope_description,
    get_scope_risk_level,
    group_by_platform,
)

# ---------------------------------------------------------------------------
# ANSI colour codes (terminal output only — no curses dependency)
# ---------------------------------------------------------------------------

# Colour resets
_RESET = "\033[0m"

# Text colours
_GREEN = "\033[32m"       # LOW risk — read-only
_YELLOW = "\033[33m"      # MEDIUM risk — write/send
_RED = "\033[31m"         # HIGH risk — admin/delete

# Bold + colour variants for headers
_BOLD = "\033[1m"
_DIM = "\033[2m"

# Background accent colours for risk badges
_BG_GREEN = "\033[42m\033[30m"   # green bg, black text
_BG_YELLOW = "\033[43m\033[30m"  # yellow bg, black text
_BG_RED = "\033[41m\033[37m"     # red bg, white text

# Diff colours
_GREEN_BRIGHT = "\033[92m"       # added scope
_RED_BRIGHT = "\033[91m"         # removed scope

# ---------------------------------------------------------------------------
# Risk level metadata
# ---------------------------------------------------------------------------

# Maps risk_level string → (ANSI colour, badge text, check symbol)
_RISK_META: Dict[str, Tuple[str, str, str]] = {
    "low":    (_GREEN,  "LOW",    "✓"),
    "medium": (_YELLOW, "MEDIUM", "~"),
    "high":   (_RED,    "HIGH",   "!"),
}

# Canonical platform display names (fallback: title-case first segment)
_PLATFORM_LABELS: Dict[str, str] = {
    "gmail":       "Gmail",
    "drive":       "Google Drive",
    "calendar":    "Google Calendar",
    "linkedin":    "LinkedIn",
    "github":      "GitHub",
    "slack":       "Slack",
    "reddit":      "Reddit",
    "hackernews":  "Hacker News",
    "twitter":     "Twitter / X",
    "browser":     "Browser",
    "fs":          "Local Filesystem",
    "agent":       "Agent Router",
    "plugin":      "Plugin Registry",
    "machine":     "Machine",
}

# ---------------------------------------------------------------------------
# Fallback English descriptions for scopes not in the registry
# ---------------------------------------------------------------------------

_FALLBACK_DESCRIPTIONS: Dict[str, str] = {
    # gmail
    "gmail.read":          "Read your Gmail inbox",
    "gmail.send":          "Send emails on your behalf",
    "gmail.draft":         "Create draft emails (not sent)",
    # drive
    "drive.read":          "Read files from your Google Drive",
    "drive.write":         "Write files to your Google Drive",
    "drive.delete":        "Delete files from your Google Drive",
    # calendar
    "calendar.read":       "Read your Google Calendar events",
    "calendar.write":      "Create and edit calendar events",
    # browser
    "browser.navigate":    "Navigate to web pages",
    "browser.screenshot":  "Capture browser screenshots",
    "browser.click":       "Click page elements on your behalf",
    "browser.input":       "Fill in form fields on your behalf",
    # slack
    "slack.read":          "Read messages from your Slack workspace",
    "slack.send":          "Send messages to your Slack workspace",
    # linkedin
    "linkedin.read":       "Read your LinkedIn profile and feed",
    "linkedin.post":       "Post content to LinkedIn on your behalf",
    # github
    "github.read":         "Read your GitHub repositories and issues",
    "github.write":        "Write to your GitHub repositories",
}


def _fallback_description(scope: str) -> str:
    """
    Generate a best-effort plain-English description for an unregistered scope.

    Strategy:
      1. Check _FALLBACK_DESCRIPTIONS exact match.
      2. Prefix-match on platform.action.
      3. Parse the scope segments and build a sentence.

    Args:
        scope: Scope string (any format).

    Returns:
        Human-readable description string.
    """
    if scope in _FALLBACK_DESCRIPTIONS:
        return _FALLBACK_DESCRIPTIONS[scope]

    # Try prefix match (platform.action)
    parts = scope.split(".")
    if len(parts) >= 2:
        prefix = f"{parts[0]}.{parts[1]}"
        if prefix in _FALLBACK_DESCRIPTIONS:
            return _FALLBACK_DESCRIPTIONS[prefix]

    # Generic construction from segments
    platform_label = _PLATFORM_LABELS.get(parts[0], parts[0].title()) if parts else "Unknown"
    action_words = " ".join(p.replace("_", " ") for p in parts[1:]) if len(parts) > 1 else ""
    if action_words:
        return f"{action_words.capitalize()} access to {platform_label}"
    return f"Access to {platform_label}"


def _risk_colour(risk: str) -> str:
    """Return the ANSI colour code for a given risk level string."""
    meta = _RISK_META.get(risk, _RISK_META["high"])
    return meta[0]


def _risk_badge(risk: str, plain: bool = False) -> str:
    """
    Return a coloured risk badge string.

    Args:
        risk:  Risk level string ("low", "medium", "high").
        plain: If True, return plain text badge without ANSI codes.

    Returns:
        Badge string like "[LOW]" (plain) or ANSI-coloured equivalent.
    """
    meta = _RISK_META.get(risk, _RISK_META["high"])
    colour, label, _ = meta
    if plain:
        return f"[{label}]"
    if risk == "low":
        bg = _BG_GREEN
    elif risk == "medium":
        bg = _BG_YELLOW
    else:
        bg = _BG_RED
    return f"{bg} {label} {_RESET}"


def _check_symbol(risk: str, plain: bool = False) -> str:
    """
    Return the scope line check symbol appropriate for the risk level.

    Args:
        risk:  Risk level string.
        plain: If True, return raw symbol without ANSI codes.

    Returns:
        Coloured or plain check symbol.
    """
    meta = _RISK_META.get(risk, _RISK_META["high"])
    colour, _, symbol = meta
    if plain:
        return symbol
    return f"{colour}{symbol}{_RESET}"


# ---------------------------------------------------------------------------
# Module-level convenience functions (thin wrappers over ScopeDisplay)
# ---------------------------------------------------------------------------

def describe_scope(scope: str) -> str:
    """
    Return a plain-English description for a single OAuth3 scope string.

    Looks up the scope in the OAuth3 registry first. Falls back to a
    best-effort description if the scope is unregistered.

    Args:
        scope: OAuth3 scope string (e.g. "gmail.read.inbox").

    Returns:
        Human-readable description (never empty).
    """
    return ScopeDisplay.describe_scope(scope)


def categorize_scopes(scopes: List[str]) -> Dict[str, List[str]]:
    """
    Group a list of OAuth3 scopes by their platform/app.

    Args:
        scopes: List of scope strings.

    Returns:
        Dict mapping platform label → list of scope strings.
        e.g. {"Gmail": ["gmail.read.inbox", "gmail.send.email"], "LinkedIn": [...]}
    """
    return ScopeDisplay.categorize_scopes(scopes)


def render_scope_modal(scopes: List[str], recipe_name: str, plain: bool = False) -> str:
    """
    Render a full terminal consent modal for a list of OAuth3 scopes.

    Shows:
      - Recipe name header
      - "This recipe needs permission to:" prompt
      - Bulleted list: "✓ Read your Gmail inbox  [LOW]"
      - Overall risk indicator

    Args:
        scopes:      List of OAuth3 scope strings.
        recipe_name: Display name for the recipe requesting the scopes.
        plain:       If True, strip ANSI colour codes for plain-text output.

    Returns:
        Multi-line string ready for terminal display.
    """
    return ScopeDisplay.render_scope_modal(scopes, recipe_name, plain=plain)


def render_scope_diff(old_scopes: List[str], new_scopes: List[str], plain: bool = False) -> str:
    """
    Render a diff of two scope lists showing added and removed scopes.

    Added scopes appear in green with a "+" prefix.
    Removed scopes appear in red with a "-" prefix.
    Unchanged scopes appear dimmed with a "=" prefix.

    Args:
        old_scopes: Previous scope list.
        new_scopes: New scope list.
        plain:      If True, strip ANSI colour codes.

    Returns:
        Multi-line diff string.
    """
    return ScopeDisplay.render_scope_diff(old_scopes, new_scopes, plain=plain)


# ---------------------------------------------------------------------------
# ScopeDisplay — main class
# ---------------------------------------------------------------------------

class ScopeDisplay:
    """
    Stateless helper class for rendering OAuth3 scopes as plain-English
    terminal UI.

    All methods are static — instantiate ScopeDisplay() for convenient
    attribute access, or call the module-level functions directly.

    Risk classification:
      LOW    — read-only (green)    e.g. gmail.read.inbox
      MEDIUM — write/send (yellow)  e.g. gmail.send.email, browser.click
      HIGH   — admin/delete (red)   e.g. gmail.delete.email, linkedin.delete.post

    FALLBACK BAN enforced: unknown scope → HIGH risk (fail-closed). Never
    silently accepts an unclassified scope as safe.

    Rung: 641
    """

    # ------------------------------------------------------------------
    # Core: scope → English
    # ------------------------------------------------------------------

    @staticmethod
    def describe_scope(scope: str) -> str:
        """
        Return a plain-English description for a single scope string.

        Looks up the OAuth3 registry (via oauth3.scopes.get_scope_description).
        Falls back to _fallback_description() for unregistered scopes.

        Args:
            scope: OAuth3 scope string.

        Returns:
            Non-empty human-readable description string.
        """
        if not isinstance(scope, str):
            raise TypeError(f"scope must be str, got {type(scope).__name__!r}")
        scope = scope.strip()
        if not scope:
            raise ValueError("scope must not be empty")

        registered = get_scope_description(scope)
        if registered:
            return registered
        return _fallback_description(scope)

    @staticmethod
    def risk_level(scope: str) -> str:
        """
        Return the risk level for a scope: "low", "medium", or "high".

        Unknown scopes → "high" (fail-closed per Fallback Ban).

        Args:
            scope: OAuth3 scope string.

        Returns:
            "low", "medium", or "high".
        """
        if not isinstance(scope, str):
            raise TypeError(f"scope must be str, got {type(scope).__name__!r}")
        return get_scope_risk_level(scope.strip())

    # ------------------------------------------------------------------
    # Categorisation: group scopes by platform
    # ------------------------------------------------------------------

    @staticmethod
    def categorize_scopes(scopes: List[str]) -> Dict[str, List[str]]:
        """
        Group scopes by platform, returning a dict with human-readable
        platform labels as keys.

        Args:
            scopes: List of OAuth3 scope strings.

        Returns:
            Dict[platform_label, List[scope_string]].
            e.g. {"Gmail": ["gmail.read.inbox"], "LinkedIn": ["linkedin.post.text"]}
        """
        if not isinstance(scopes, list):
            raise TypeError(f"scopes must be list, got {type(scopes).__name__!r}")

        # group_by_platform returns {platform_key → [scopes]}
        raw: Dict[str, List[str]] = group_by_platform(scopes)

        # Re-key with human-readable labels
        labelled: Dict[str, List[str]] = {}
        for platform_key, platform_scopes in raw.items():
            label = _PLATFORM_LABELS.get(platform_key, platform_key.title())
            labelled[label] = platform_scopes

        return labelled

    # ------------------------------------------------------------------
    # Rendering: single scope line
    # ------------------------------------------------------------------

    @staticmethod
    def _render_scope_line(scope: str, plain: bool = False) -> str:
        """
        Render a single scope as a terminal bullet line.

        Format: "  ✓ Read your Gmail inbox  [LOW]"

        Args:
            scope: OAuth3 scope string.
            plain: If True, no ANSI codes.

        Returns:
            Single-line string (no trailing newline).
        """
        description = ScopeDisplay.describe_scope(scope)
        risk = ScopeDisplay.risk_level(scope)
        symbol = _check_symbol(risk, plain=plain)
        badge = _risk_badge(risk, plain=plain)

        if plain:
            return f"  {symbol} {description}  {badge}"

        colour = _risk_colour(risk)
        return f"  {symbol} {colour}{description}{_RESET}  {badge}"

    # ------------------------------------------------------------------
    # Rendering: modal
    # ------------------------------------------------------------------

    @staticmethod
    def render_scope_modal(
        scopes: List[str],
        recipe_name: str,
        plain: bool = False,
    ) -> str:
        """
        Render a full consent modal for terminal display.

        Layout:
          ╔══════════════════════════════════════╗
          ║  Permission Request                  ║
          ╚══════════════════════════════════════╝
          Recipe: "send-linkedin-post"
          This recipe needs permission to:

            ✓ Read your Gmail inbox          [LOW]
            ~ Send emails on your behalf  [MEDIUM]
            ! Delete an email permanently   [HIGH]

          Overall risk: HIGH
          ─────────────────────────────────────

        Args:
            scopes:      List of OAuth3 scope strings.
            recipe_name: Recipe display name.
            plain:       Strip ANSI codes if True.

        Returns:
            Multi-line modal string.

        Raises:
            TypeError:  If scopes is not a list or recipe_name is not a str.
            ValueError: If recipe_name is empty.
        """
        if not isinstance(scopes, list):
            raise TypeError(f"scopes must be list, got {type(scopes).__name__!r}")
        if not isinstance(recipe_name, str):
            raise TypeError(f"recipe_name must be str, got {type(recipe_name).__name__!r}")
        recipe_name = recipe_name.strip()
        if not recipe_name:
            raise ValueError("recipe_name must not be empty")

        width = 50
        border = "─" * width

        # Header
        if plain:
            header = (
                f"╔{'═' * (width - 2)}╗\n"
                f"║{'  Permission Request'.ljust(width - 2)}║\n"
                f"╚{'═' * (width - 2)}╝"
            )
        else:
            header = (
                f"{_BOLD}╔{'═' * (width - 2)}╗\n"
                f"║{'  Permission Request'.ljust(width - 2)}║\n"
                f"╚{'═' * (width - 2)}╝{_RESET}"
            )

        # Recipe name line
        if plain:
            recipe_line = f'Recipe: "{recipe_name}"'
        else:
            recipe_line = f'{_BOLD}Recipe:{_RESET} "{recipe_name}"'

        # Preamble
        if plain:
            preamble = "This recipe needs permission to:"
        else:
            preamble = f"{_BOLD}This recipe needs permission to:{_RESET}"

        # Scope lines — empty list renders as explicit "(no permissions requested)"
        if not scopes:
            scope_block = "  (no permissions requested)"
        else:
            scope_lines = [
                ScopeDisplay._render_scope_line(s, plain=plain) for s in scopes
            ]
            scope_block = "\n".join(scope_lines)

        # Overall risk level (highest risk among all scopes)
        overall_risk = ScopeDisplay._overall_risk(scopes)
        risk_colour = _risk_colour(overall_risk) if not plain else ""
        risk_reset = _RESET if not plain else ""
        risk_badge = _risk_badge(overall_risk, plain=plain)
        if plain:
            risk_line = f"Overall risk: {overall_risk.upper()}"
        else:
            risk_line = f"{_BOLD}Overall risk:{_RESET} {risk_badge}"

        lines = [
            header,
            recipe_line,
            preamble,
            "",
            scope_block,
            "",
            risk_line,
            border,
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Rendering: diff
    # ------------------------------------------------------------------

    @staticmethod
    def render_scope_diff(
        old_scopes: List[str],
        new_scopes: List[str],
        plain: bool = False,
    ) -> str:
        """
        Render a diff between two scope lists.

        Lines are prefixed:
          +  Added scope   (green)
          -  Removed scope (red)
          =  Unchanged     (dim)

        Args:
            old_scopes: Previous scope list.
            new_scopes: New (requested) scope list.
            plain:      Strip ANSI codes if True.

        Returns:
            Multi-line diff string.

        Raises:
            TypeError: If either argument is not a list.
        """
        if not isinstance(old_scopes, list):
            raise TypeError(f"old_scopes must be list, got {type(old_scopes).__name__!r}")
        if not isinstance(new_scopes, list):
            raise TypeError(f"new_scopes must be list, got {type(new_scopes).__name__!r}")

        old_set = set(old_scopes)
        new_set = set(new_scopes)
        added = sorted(new_set - old_set)
        removed = sorted(old_set - new_set)
        unchanged = sorted(old_set & new_set)

        lines: List[str] = []
        width = 50
        border = "─" * width

        if plain:
            lines.append("Scope Changes:")
        else:
            lines.append(f"{_BOLD}Scope Changes:{_RESET}")
        lines.append(border)

        if not added and not removed and not unchanged:
            lines.append("  (no scopes)")
            lines.append(border)
            return "\n".join(lines)

        for scope in added:
            desc = ScopeDisplay.describe_scope(scope)
            risk = ScopeDisplay.risk_level(scope)
            badge = _risk_badge(risk, plain=plain)
            if plain:
                lines.append(f"  + {desc}  {badge}")
            else:
                lines.append(
                    f"  {_GREEN_BRIGHT}+{_RESET} {_GREEN_BRIGHT}{desc}{_RESET}  {badge}"
                )

        for scope in removed:
            desc = ScopeDisplay.describe_scope(scope)
            risk = ScopeDisplay.risk_level(scope)
            badge = _risk_badge(risk, plain=plain)
            if plain:
                lines.append(f"  - {desc}  {badge}")
            else:
                lines.append(
                    f"  {_RED_BRIGHT}-{_RESET} {_RED_BRIGHT}{desc}{_RESET}  {badge}"
                )

        for scope in unchanged:
            desc = ScopeDisplay.describe_scope(scope)
            risk = ScopeDisplay.risk_level(scope)
            badge = _risk_badge(risk, plain=plain)
            if plain:
                lines.append(f"  = {desc}  {badge}")
            else:
                lines.append(
                    f"  {_DIM}={_RESET} {_DIM}{desc}{_RESET}  {badge}"
                )

        lines.append(border)

        # Summary line
        summary_parts = []
        if added:
            n = len(added)
            if plain:
                summary_parts.append(f"+{n} added")
            else:
                summary_parts.append(f"{_GREEN_BRIGHT}+{n} added{_RESET}")
        if removed:
            n = len(removed)
            if plain:
                summary_parts.append(f"-{n} removed")
            else:
                summary_parts.append(f"{_RED_BRIGHT}-{n} removed{_RESET}")
        if unchanged:
            n = len(unchanged)
            if plain:
                summary_parts.append(f"={n} unchanged")
            else:
                summary_parts.append(f"{_DIM}={n} unchanged{_RESET}")

        if summary_parts:
            lines.append("  " + "  ".join(summary_parts))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _overall_risk(scopes: List[str]) -> str:
        """
        Return the highest risk level among a list of scopes.

        Risk precedence: high > medium > low. Empty list → "low".

        Args:
            scopes: List of scope strings.

        Returns:
            "high", "medium", or "low".
        """
        _ORDER = {"high": 2, "medium": 1, "low": 0}
        max_risk = "low"
        for scope in scopes:
            risk = get_scope_risk_level(scope)
            if _ORDER.get(risk, 2) > _ORDER.get(max_risk, 0):
                max_risk = risk
        return max_risk
