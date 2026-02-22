"""
Canvas OAuth3 Scope Definitions — Live Canvas + Agent-to-UI

Canvas-specific scopes for the LiveCanvas overlay system and A2UI protocol.
All canvas operations are OAuth3 scope-gated.

Naming convention: platform.action.resource (triple-segment, spec §2.1)

Scopes:
  canvas.overlay.render    — render visual overlay on page (read-only)
  canvas.overlay.interact  — clickable overlay elements (step-up required)
  canvas.a2ui.communicate  — agent↔UI message passing
  canvas.a2ui.input        — request user input via A2UI (step-up required)
  canvas.screenshot.capture — capture canvas state as screenshot

Reference: oauth3-spec-v0.1.md §2
Rung: 641
"""

from __future__ import annotations

from typing import Dict


# ---------------------------------------------------------------------------
# Canvas scope definitions
# ---------------------------------------------------------------------------

CANVAS_SCOPES: Dict[str, Dict] = {

    "canvas.overlay.render": {
        "platform": "canvas",
        "description": (
            "Render a read-only visual overlay on the browser viewport. "
            "Never modifies the actual page DOM."
        ),
        "risk_level": "low",
        "destructive": False,
        "step_up_required": False,
    },

    "canvas.overlay.interact": {
        "platform": "canvas",
        "description": (
            "Render clickable overlay elements on the browser viewport. "
            "Requires step-up authorization — agents can trigger UI actions."
        ),
        "risk_level": "high",
        "destructive": True,
        "step_up_required": True,
    },

    "canvas.a2ui.communicate": {
        "platform": "canvas",
        "description": (
            "Agent-to-UI communication: send status updates, progress bars, "
            "results, and error messages to the user interface."
        ),
        "risk_level": "low",
        "destructive": False,
        "step_up_required": False,
    },

    "canvas.a2ui.input": {
        "platform": "canvas",
        "description": (
            "Request user input via Agent-to-UI channel. "
            "Requires step-up authorization — agent can solicit user responses."
        ),
        "risk_level": "high",
        "destructive": False,
        "step_up_required": True,
    },

    "canvas.screenshot.capture": {
        "platform": "canvas",
        "description": (
            "Capture the current canvas overlay state as a screenshot "
            "for audit trail inclusion."
        ),
        "risk_level": "medium",
        "destructive": False,
        "step_up_required": False,
    },
}

# ---------------------------------------------------------------------------
# Convenience constants
# ---------------------------------------------------------------------------

SCOPE_CANVAS_RENDER = "canvas.overlay.render"
SCOPE_CANVAS_INTERACT = "canvas.overlay.interact"
SCOPE_A2UI_COMMUNICATE = "canvas.a2ui.communicate"
SCOPE_A2UI_INPUT = "canvas.a2ui.input"
SCOPE_SCREENSHOT_CAPTURE = "canvas.screenshot.capture"

# Scopes that require step-up authorization
CANVAS_STEP_UP_SCOPES: frozenset = frozenset(
    scope for scope, meta in CANVAS_SCOPES.items()
    if meta["step_up_required"]
)

# All canvas scope strings
ALL_CANVAS_SCOPES: frozenset = frozenset(CANVAS_SCOPES.keys())


def register_canvas_scopes() -> None:
    """
    Register canvas scopes into the global OAuth3 SCOPE_REGISTRY.

    Must be called at application startup before any canvas operation
    attempts to validate scopes via AgencyToken.create().

    Canvas scopes follow the same triple-segment format (platform.action.resource)
    as all other OAuth3 scopes. They are registered dynamically (like machine.*)
    rather than hard-coded in oauth3/scopes.py, keeping the canvas module
    self-contained.
    """
    from oauth3.scopes import SCOPE_REGISTRY, HIGH_RISK_SCOPES, DESTRUCTIVE_SCOPES

    for scope, meta in CANVAS_SCOPES.items():
        if scope not in SCOPE_REGISTRY:
            SCOPE_REGISTRY[scope] = {
                "platform": meta["platform"],
                "description": meta["description"],
                "risk_level": meta["risk_level"],
                "destructive": meta["destructive"],
            }
