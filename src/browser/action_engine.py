# Diagram: 01-triangle-architecture
"""
action_engine.py — AI-Driven Action Execution Engine
Phase 2, BUILD 6: Ref-Based Action Execution

Executes browser actions on DOM elements using DOMRef instead of raw CSS
selectors. The action engine is the bridge between LLM instructions and
actual page interactions.

Design principles:
  - Actions are identified by DOMRef (stable ref_id) not brittle CSS
  - Supported actions are enumerated and validated before dispatch
  - All results include evidence (before/after snapshot diff, ref used)
  - Engine is pure Python at its core; browser adapter is injected

Rung: 641
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from dom_snapshot import DOMRef, DOMSnapshot, DOMSnapshotEngine


# ---------------------------------------------------------------------------
# ActionResult
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """
    Result of an action executed on a DOM element.

    Fields:
        success:    True if the action completed without error
        ref_used:   ref_id of the DOMRef that was targeted (empty if none found)
        action:     the action verb executed (click, type, etc.)
        evidence:   {
                        "before_dom_hash": str,
                        "after_dom_hash": str | None,
                        "diff": dict | None,         # from DOMSnapshotEngine.diff()
                        "screenshot": str | None,    # base64 or path (injected by adapter)
                    }
        error:      error message if success=False, else ""
    """
    success: bool
    ref_used: str
    action: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "ref_used": self.ref_used,
            "action": self.action,
            "evidence": self.evidence,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Instruction parser helpers
# ---------------------------------------------------------------------------

# Maps instruction verbs → canonical action names
_VERB_TO_ACTION: Dict[str, str] = {
    # click synonyms
    "click": "click",
    "press": "click",
    "tap": "click",
    "submit": "click",
    "open": "click",
    "follow": "click",
    "activate": "click",
    # type synonyms
    "type": "type",
    "enter": "type",
    "fill": "type",
    "input": "type",
    "write": "type",
    "set": "type",
    # scroll synonyms
    "scroll": "scroll",
    "swipe": "scroll",
    # select synonyms
    "select": "select",
    "choose": "select",
    "pick": "select",
    # hover synonyms
    "hover": "hover",
    "mouseover": "hover",
    "point": "hover",
    # wait synonyms
    "wait": "wait",
    "pause": "wait",
    "sleep": "wait",
}


def _parse_action_from_instruction(instruction: str) -> str:
    """
    Extract canonical action verb from a natural language instruction.

    Examples:
        "click the Login button"  → "click"
        "type 'hello' in the search box"  → "type"
        "scroll down to see more"  → "scroll"

    Returns "click" as the default if no verb is detected.
    """
    lower = instruction.lower().strip()
    first_word = re.split(r"\W+", lower)[0] if lower else ""

    if first_word in _VERB_TO_ACTION:
        return _VERB_TO_ACTION[first_word]

    # Scan all words for verb match
    words = re.split(r"\W+", lower)
    for word in words:
        if word in _VERB_TO_ACTION:
            return _VERB_TO_ACTION[word]

    return "click"


def _parse_value_from_instruction(instruction: str) -> str:
    """
    Extract a typed value from instruction if present.

    Looks for:
      - Quoted strings:  type "hello world"  →  "hello world"
      - Single quotes:   type 'hello'        →  "hello"

    Returns "" if no quoted value found.
    """
    # Double-quoted
    m = re.search(r'"([^"]*)"', instruction)
    if m:
        return m.group(1)
    # Single-quoted
    m = re.search(r"'([^']*)'", instruction)
    if m:
        return m.group(1)
    return ""


# ---------------------------------------------------------------------------
# BrowserAdapter protocol (duck-typed — no ABC to avoid import overhead)
# ---------------------------------------------------------------------------

class _NullAdapter:
    """
    Default no-op adapter. Simulates execution without a real browser.

    In production, replace with a CDP/Playwright/Puppeteer adapter
    that maps ref.path (CSS selector) to actual browser actions.
    """

    def click(self, css_path: str) -> bool:
        return True

    def type(self, css_path: str, value: str) -> bool:
        return True

    def scroll(self, css_path: str, value: str) -> bool:
        return True

    def select(self, css_path: str, value: str) -> bool:
        return True

    def hover(self, css_path: str) -> bool:
        return True

    def wait(self, value: str) -> bool:
        return True

    def screenshot(self) -> Optional[str]:
        return None  # no screenshot in null adapter


# ---------------------------------------------------------------------------
# ActionEngine
# ---------------------------------------------------------------------------

class ActionEngine:
    """
    Execute actions on DOM elements by DOMRef instead of raw CSS selectors.

    Usage (ref-first):
        engine = ActionEngine()
        result = engine.execute("click", ref)

    Usage (instruction-first):
        result = engine.act(snapshot, "click the Login button")

    The adapter parameter allows injecting a real browser adapter; the
    default _NullAdapter simulates execution without a browser.
    """

    SUPPORTED_ACTIONS: List[str] = ["click", "type", "scroll", "select", "hover", "wait"]

    def __init__(self, adapter=None) -> None:
        self._adapter = adapter if adapter is not None else _NullAdapter()
        self._engine = DOMSnapshotEngine()

    # ------------------------------------------------------------------
    # execute — ref-first API
    # ------------------------------------------------------------------

    def execute(
        self,
        action: str,
        ref: DOMRef,
        value: str = "",
        snapshot_before: Optional[DOMSnapshot] = None,
        snapshot_after: Optional[DOMSnapshot] = None,
    ) -> ActionResult:
        """
        Execute an action on a DOM element by DOMRef.

        Args:
            action:           one of SUPPORTED_ACTIONS
            ref:              the target DOMRef
            value:            value for type/select/scroll actions
            snapshot_before:  DOMSnapshot before action (for diff evidence)
            snapshot_after:   DOMSnapshot after action (for diff evidence)

        Returns:
            ActionResult with success flag and evidence dict
        """
        if action not in self.SUPPORTED_ACTIONS:
            return ActionResult(
                success=False,
                ref_used=ref.ref_id,
                action=action,
                evidence={},
                error=f"UNSUPPORTED_ACTION: '{action}' not in {self.SUPPORTED_ACTIONS}",
            )

        css_path = ref.path

        try:
            ok = self._dispatch(action, css_path, value)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            return ActionResult(
                success=False,
                ref_used=ref.ref_id,
                action=action,
                evidence={},
                error=f"ADAPTER_ERROR: {exc}",
            )

        # Build evidence
        evidence: Dict[str, Any] = {
            "before_dom_hash": snapshot_before.dom_hash if snapshot_before else None,
            "after_dom_hash": snapshot_after.dom_hash if snapshot_after else None,
            "diff": None,
            "screenshot": self._adapter.screenshot(),
        }

        if snapshot_before is not None and snapshot_after is not None:
            evidence["diff"] = self._engine.diff(snapshot_before, snapshot_after)

        return ActionResult(
            success=ok,
            ref_used=ref.ref_id,
            action=action,
            evidence=evidence,
            error="" if ok else "ADAPTER_RETURNED_FALSE",
        )

    # ------------------------------------------------------------------
    # act — instruction-first AI API
    # ------------------------------------------------------------------

    def act(
        self,
        snapshot: DOMSnapshot,
        instruction: str,
        snapshot_after: Optional[DOMSnapshot] = None,
    ) -> ActionResult:
        """
        AI-driven action: parse instruction, find ref, execute.

        Args:
            snapshot:       current DOMSnapshot (before action)
            instruction:    natural language: "click the Login button"
            snapshot_after: optional post-action snapshot for diff evidence

        Returns:
            ActionResult — success=False with REF_NOT_FOUND if no ref matched
        """
        action = _parse_action_from_instruction(instruction)
        value = _parse_value_from_instruction(instruction)

        ref = self._engine.find_ref(snapshot, instruction)

        if ref is None:
            return ActionResult(
                success=False,
                ref_used="",
                action=action,
                evidence={
                    "before_dom_hash": snapshot.dom_hash,
                    "after_dom_hash": None,
                    "diff": None,
                    "screenshot": None,
                },
                error=f"REF_NOT_FOUND: no DOM element matched '{instruction}'",
            )

        return self.execute(
            action=action,
            ref=ref,
            value=value,
            snapshot_before=snapshot,
            snapshot_after=snapshot_after,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _dispatch(self, action: str, css_path: str, value: str) -> bool:
        """Route action to adapter method. Returns True on success."""
        if action == "click":
            return bool(self._adapter.click(css_path))
        elif action == "type":
            return bool(self._adapter.type(css_path, value))
        elif action == "scroll":
            return bool(self._adapter.scroll(css_path, value))
        elif action == "select":
            return bool(self._adapter.select(css_path, value))
        elif action == "hover":
            return bool(self._adapter.hover(css_path))
        elif action == "wait":
            return bool(self._adapter.wait(value))
        return False
