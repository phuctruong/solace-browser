"""
canvas — Live Canvas + Agent-to-UI (A2UI) for Solace Browser

Real-time visual overlay system and structured agent↔UI communication protocol.
All operations are OAuth3 scope-gated.

Architecture:
  scopes.py      — Canvas-specific OAuth3 scope definitions
  live_canvas.py — LiveCanvas overlay manager + CanvasRenderer
  a2ui.py        — A2UIBridge + A2UIChannel message protocol

OAuth3 scopes:
  canvas.overlay.render    — render visual overlay (read-only)
  canvas.overlay.interact  — clickable overlay elements (step-up required)
  canvas.a2ui.communicate  — agent→UI status/progress/result messages
  canvas.a2ui.input        — request user input (step-up required)
  canvas.screenshot.capture — capture canvas state

Rung: 641
"""

from canvas.scopes import (
    CANVAS_SCOPES,
    ALL_CANVAS_SCOPES,
    CANVAS_STEP_UP_SCOPES,
    SCOPE_CANVAS_RENDER,
    SCOPE_CANVAS_INTERACT,
    SCOPE_A2UI_COMMUNICATE,
    SCOPE_A2UI_INPUT,
    SCOPE_SCREENSHOT_CAPTURE,
    register_canvas_scopes,
)

from canvas.live_canvas import (
    LiveCanvas,
    CanvasElement,
    CanvasRenderer,
    ActionStep,
    ElementType,
    MAX_ELEMENTS,
    DEFAULT_TTL_MS,
    RISK_COLORS,
)

from canvas.a2ui import (
    A2UIBridge,
    A2UIChannel,
    A2UIMessage,
    ActionResult,
    MessageType,
    MAX_QUEUE_DEPTH,
    MESSAGE_AUTO_EXPIRE_SECONDS,
    INPUT_REQUEST_TIMEOUT_SECONDS,
)

__all__ = [
    # Scopes
    "CANVAS_SCOPES",
    "ALL_CANVAS_SCOPES",
    "CANVAS_STEP_UP_SCOPES",
    "SCOPE_CANVAS_RENDER",
    "SCOPE_CANVAS_INTERACT",
    "SCOPE_A2UI_COMMUNICATE",
    "SCOPE_A2UI_INPUT",
    "SCOPE_SCREENSHOT_CAPTURE",
    "register_canvas_scopes",
    # LiveCanvas
    "LiveCanvas",
    "CanvasElement",
    "CanvasRenderer",
    "ActionStep",
    "ElementType",
    "MAX_ELEMENTS",
    "DEFAULT_TTL_MS",
    "RISK_COLORS",
    # A2UI
    "A2UIBridge",
    "A2UIChannel",
    "A2UIMessage",
    "ActionResult",
    "MessageType",
    "MAX_QUEUE_DEPTH",
    "MESSAGE_AUTO_EXPIRE_SECONDS",
    "INPUT_REQUEST_TIMEOUT_SECONDS",
]

__version__ = "0.1.0"
__rung__ = 641
