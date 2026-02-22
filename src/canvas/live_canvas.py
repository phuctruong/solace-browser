"""
Live Canvas — Real-Time Visual Overlay System

Renders agent action overlays on the browser viewport.

The canvas is a STRICTLY READ-ONLY overlay layer — it never modifies the
actual page DOM. It injects a transparent overlay <div> and draws highlights,
paths, tooltips and annotations on top of the real page.

OAuth3 scope requirements:
  canvas.overlay.render    — required for all render operations
  canvas.overlay.interact  — required for clickable overlay elements (step-up)

Key limits (visual spam prevention):
  MAX_ELEMENTS = 50        — max simultaneous canvas elements
  DEFAULT_TTL_MS = 5000    — default element lifetime in milliseconds

Rung: 641
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from canvas.scopes import (
    SCOPE_CANVAS_INTERACT,
    SCOPE_CANVAS_RENDER,
    register_canvas_scopes,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ELEMENTS: int = 50
DEFAULT_TTL_MS: int = 5000

# Risk-level color palette (CSS color strings)
RISK_COLORS: Dict[str, str] = {
    "low": "#22c55e",       # green
    "medium": "#eab308",    # yellow
    "high": "#f97316",      # orange
    "critical": "#ef4444",  # red
}

# Default highlight color when no risk level is specified
DEFAULT_HIGHLIGHT_COLOR: str = "#3b82f6"  # blue


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ElementType(Enum):
    """Type of visual canvas element."""

    HIGHLIGHT = "highlight"
    PATH = "path"
    TOOLTIP = "tooltip"
    ANNOTATION = "annotation"
    CURSOR = "cursor"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ActionStep:
    """
    A single planned action step for path visualization.

    Attributes:
        selector:   CSS selector of the target DOM element.
        action:     Action name (e.g. "click", "type", "scroll").
        label:      Human-readable label shown in the overlay.
        risk_level: Risk classification: "low", "medium", "high", "critical".
    """

    selector: str
    action: str
    label: str
    risk_level: str = "low"

    def __post_init__(self) -> None:
        if self.risk_level not in RISK_COLORS:
            raise ValueError(
                f"Invalid risk_level '{self.risk_level}'. "
                f"Must be one of: {sorted(RISK_COLORS)}"
            )


@dataclass
class CanvasElement:
    """
    A single visual element rendered on the canvas overlay.

    Attributes:
        element_id:   Unique identifier for this canvas element.
        element_type: ElementType enum value.
        position:     (x, y) coordinate tuple in viewport pixels.
        style:        CSS/rendering style dict (color, opacity, etc.).
        ttl_ms:       Time-to-live in milliseconds. None = persistent.
        created_at_ms: Timestamp of creation (int ms since epoch).
        label:        Optional display label.
        data:         Arbitrary element-specific data dict.
    """

    element_id: str
    element_type: ElementType
    position: Tuple[int, int]
    style: Dict
    ttl_ms: Optional[int] = DEFAULT_TTL_MS
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    label: str = ""
    data: Dict = field(default_factory=dict)

    def is_expired(self, now_ms: Optional[int] = None) -> bool:
        """
        Return True if this element's TTL has elapsed.

        Args:
            now_ms: Current timestamp in milliseconds. Defaults to now.

        Returns:
            True if the element should be removed, False if still valid.
        """
        if self.ttl_ms is None:
            return False
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        return (now_ms - self.created_at_ms) >= self.ttl_ms


# ---------------------------------------------------------------------------
# CanvasRenderer
# ---------------------------------------------------------------------------

class CanvasRenderer:
    """
    Renders CanvasElement list to an overlay HTML/CSS fragment.

    The generated markup is injected into a transparent overlay <div>
    positioned absolutely over the page content. The page DOM itself is
    NEVER touched by the renderer.
    """

    # CSS transition duration for path animations (ms)
    PATH_ANIMATION_STEP_MS: int = 400

    def render(self, elements: List[CanvasElement]) -> str:
        """
        Generate overlay HTML/CSS for the given list of canvas elements.

        Args:
            elements: List of CanvasElement objects to render.

        Returns:
            HTML string representing the overlay fragment.
            The returned string is a self-contained <div> with inline styles.
        """
        if not elements:
            return self._empty_overlay()

        parts: List[str] = [self._overlay_header()]

        for elem in elements:
            if elem.element_type == ElementType.HIGHLIGHT:
                parts.append(self._render_highlight(elem))
            elif elem.element_type == ElementType.PATH:
                parts.append(self._render_path(elem))
            elif elem.element_type == ElementType.TOOLTIP:
                parts.append(self._render_tooltip(elem))
            elif elem.element_type == ElementType.ANNOTATION:
                parts.append(self._render_annotation(elem))
            elif elem.element_type == ElementType.CURSOR:
                parts.append(self._render_cursor(elem))

        parts.append(self._overlay_footer())
        return "\n".join(parts)

    # -------------------------------------------------------------------------
    # Private: element renderers
    # -------------------------------------------------------------------------

    def _empty_overlay(self) -> str:
        return (
            '<div id="solace-canvas-overlay" '
            'style="position:fixed;top:0;left:0;width:100%;height:100%;'
            'pointer-events:none;z-index:2147483647;"></div>'
        )

    def _overlay_header(self) -> str:
        return (
            '<div id="solace-canvas-overlay" '
            'style="position:fixed;top:0;left:0;width:100%;height:100%;'
            'pointer-events:none;z-index:2147483647;">'
        )

    def _overlay_footer(self) -> str:
        return "</div>"

    def _render_highlight(self, elem: CanvasElement) -> str:
        x, y = elem.position
        color = elem.style.get("color", DEFAULT_HIGHLIGHT_COLOR)
        opacity = elem.style.get("opacity", 0.35)
        width = elem.style.get("width", 120)
        height = elem.style.get("height", 40)
        border_width = elem.style.get("border_width", 3)

        label_html = ""
        if elem.label:
            label_html = (
                f'<span style="position:absolute;top:-22px;left:0;'
                f'background:{color};color:#fff;font-size:12px;'
                f'padding:2px 6px;border-radius:3px;white-space:nowrap;">'
                f'{_escape_html(elem.label)}</span>'
            )

        return (
            f'<div data-canvas-id="{_escape_attr(elem.element_id)}" '
            f'data-canvas-type="highlight" '
            f'style="position:fixed;left:{x}px;top:{y}px;'
            f'width:{width}px;height:{height}px;'
            f'border:{border_width}px solid {color};'
            f'background:rgba(0,0,0,{opacity});'
            f'border-radius:4px;pointer-events:none;">'
            f'{label_html}'
            f'</div>'
        )

    def _render_path(self, elem: CanvasElement) -> str:
        steps: List[Dict] = elem.data.get("steps", [])
        if not steps:
            return ""

        parts: List[str] = []
        for i, step in enumerate(steps):
            sx = step.get("x", 0)
            sy = step.get("y", 0)
            risk = step.get("risk_level", "low")
            color = RISK_COLORS.get(risk, RISK_COLORS["low"])
            step_label = _escape_html(step.get("label", f"Step {i + 1}"))
            delay_ms = i * self.PATH_ANIMATION_STEP_MS

            parts.append(
                f'<div data-canvas-id="{_escape_attr(elem.element_id)}-step-{i}" '
                f'data-canvas-type="path-step" '
                f'data-step-index="{i}" '
                f'style="position:fixed;left:{sx}px;top:{sy}px;'
                f'width:28px;height:28px;'
                f'border-radius:50%;'
                f'background:{color};'
                f'color:#fff;font-size:11px;font-weight:bold;'
                f'display:flex;align-items:center;justify-content:center;'
                f'pointer-events:none;'
                f'animation:solace-path-appear {self.PATH_ANIMATION_STEP_MS}ms ease {delay_ms}ms both;">'
                f'{step_label[:6]}'
                f'</div>'
            )

        # Inject keyframe styles once per path
        animation_css = (
            "<style>"
            "@keyframes solace-path-appear{"
            "from{opacity:0;transform:scale(0.5)}"
            "to{opacity:1;transform:scale(1)}"
            "}"
            "</style>"
        )
        return animation_css + "\n".join(parts)

    def _render_tooltip(self, elem: CanvasElement) -> str:
        x, y = elem.position
        text = _escape_html(elem.data.get("text", elem.label))
        bg = elem.style.get("background", "#1e293b")
        fg = elem.style.get("color", "#f8fafc")

        return (
            f'<div data-canvas-id="{_escape_attr(elem.element_id)}" '
            f'data-canvas-type="tooltip" '
            f'style="position:fixed;left:{x}px;top:{y}px;'
            f'background:{bg};color:{fg};'
            f'font-size:13px;padding:6px 10px;'
            f'border-radius:6px;max-width:280px;'
            f'box-shadow:0 4px 12px rgba(0,0,0,0.3);'
            f'pointer-events:none;'
            f'white-space:pre-wrap;word-wrap:break-word;">'
            f'{text}'
            f'</div>'
        )

    def _render_annotation(self, elem: CanvasElement) -> str:
        x, y = elem.position
        text = _escape_html(elem.data.get("text", elem.label))
        color = elem.style.get("color", "#6366f1")

        return (
            f'<div data-canvas-id="{_escape_attr(elem.element_id)}" '
            f'data-canvas-type="annotation" '
            f'style="position:fixed;left:{x}px;top:{y}px;'
            f'border-left:3px solid {color};'
            f'padding:4px 8px;'
            f'background:rgba(99,102,241,0.1);'
            f'font-size:12px;color:{color};'
            f'pointer-events:none;">'
            f'{text}'
            f'</div>'
        )

    def _render_cursor(self, elem: CanvasElement) -> str:
        x, y = elem.position
        color = elem.style.get("color", "#ef4444")

        return (
            f'<div data-canvas-id="{_escape_attr(elem.element_id)}" '
            f'data-canvas-type="cursor" '
            f'style="position:fixed;left:{x}px;top:{y}px;'
            f'width:16px;height:16px;'
            f'border-radius:50% 50% 50% 0;'
            f'background:{color};'
            f'transform:rotate(-45deg);'
            f'pointer-events:none;">'
            f'</div>'
        )

    def risk_color(self, risk_level: str) -> str:
        """Return CSS color string for the given risk level."""
        return RISK_COLORS.get(risk_level, RISK_COLORS["low"])


# ---------------------------------------------------------------------------
# LiveCanvas
# ---------------------------------------------------------------------------

class LiveCanvas:
    """
    Real-time visual overlay manager for the Solace Browser.

    Manages a bounded set of canvas elements (max 50) rendered as a
    transparent overlay on the browser viewport. The overlay is STRICTLY
    read-only — it never modifies the actual page DOM.

    OAuth3 requirements:
        canvas.overlay.render    — required for all render operations.
        canvas.overlay.interact  — required for clickable overlays (step-up).

    Usage:
        canvas = LiveCanvas(token)
        canvas.attach(page)
        canvas.highlight_element("#submit-btn", color="#22c55e", label="Click target")
        canvas.draw_action_path([ActionStep("#form", "fill", "Fill form", "low")])
        canvas.show_tooltip(400, 300, "Processing...", duration_ms=3000)
        canvas.clear()
        canvas.detach()
    """

    def __init__(self, token) -> None:
        """
        Initialize the canvas manager.

        Args:
            token: AgencyToken with canvas.overlay.render scope granted.

        Raises:
            ValueError: If token is None.
        """
        if token is None:
            raise ValueError("AgencyToken is required for LiveCanvas (fail-closed).")
        self._token = token
        self._page = None
        self._attached: bool = False
        self._elements: Dict[str, CanvasElement] = {}
        self._renderer = CanvasRenderer()

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def attach(self, page) -> None:
        """
        Attach the canvas overlay to a browser page.

        Requires: canvas.overlay.render scope.

        Args:
            page: Browser page object (Playwright Page or compatible mock).

        Raises:
            PermissionError: If token lacks canvas.overlay.render scope.
        """
        self._require_scope(SCOPE_CANVAS_RENDER)
        self._page = page
        self._attached = True

    def detach(self) -> None:
        """
        Detach the canvas overlay from the browser page.

        Clears all elements and resets attachment state.
        Safe to call even if not currently attached.
        """
        self._elements.clear()
        self._page = None
        self._attached = False

    # -------------------------------------------------------------------------
    # Element creation
    # -------------------------------------------------------------------------

    def highlight_element(
        self,
        selector: str,
        color: str = DEFAULT_HIGHLIGHT_COLOR,
        label: str = "",
        ttl_ms: Optional[int] = DEFAULT_TTL_MS,
        position: Tuple[int, int] = (0, 0),
        width: int = 120,
        height: int = 40,
    ) -> str:
        """
        Highlight a DOM element with a colored border and optional label.

        Requires: canvas.overlay.render scope.

        Args:
            selector:  CSS selector of the element to highlight.
            color:     CSS color string for the highlight border.
            label:     Optional text label displayed above the highlight.
            ttl_ms:    Time-to-live in milliseconds (default 5000).
            position:  (x, y) viewport coordinates for the highlight box.
            width:     Width of the highlight box in pixels.
            height:    Height of the highlight box in pixels.

        Returns:
            element_id string for the created canvas element.

        Raises:
            PermissionError: If token lacks canvas.overlay.render scope.
            RuntimeError:    If max element limit (50) is reached.
        """
        self._require_scope(SCOPE_CANVAS_RENDER)
        self._evict_expired()
        self._enforce_element_limit()

        element_id = _new_element_id()
        elem = CanvasElement(
            element_id=element_id,
            element_type=ElementType.HIGHLIGHT,
            position=position,
            style={"color": color, "width": width, "height": height},
            ttl_ms=ttl_ms,
            label=label,
            data={"selector": selector},
        )
        self._elements[element_id] = elem
        return element_id

    def draw_action_path(
        self,
        steps: List[ActionStep],
        ttl_ms: Optional[int] = DEFAULT_TTL_MS,
    ) -> str:
        """
        Draw a sequential visual path of planned agent actions.

        Each step is color-coded by risk level:
          low=green, medium=yellow, high=orange, critical=red.

        Requires: canvas.overlay.render scope.

        Args:
            steps:  List of ActionStep objects defining the action sequence.
            ttl_ms: Time-to-live for the entire path element.

        Returns:
            element_id string for the path canvas element.

        Raises:
            PermissionError: If token lacks canvas.overlay.render scope.
            RuntimeError:    If max element limit (50) is reached.
        """
        self._require_scope(SCOPE_CANVAS_RENDER)
        self._evict_expired()
        self._enforce_element_limit()

        element_id = _new_element_id()
        step_data = [
            {
                "selector": step.selector,
                "action": step.action,
                "label": step.label,
                "risk_level": step.risk_level,
                "x": i * 60,   # default layout; real x/y from page coordinates
                "y": 20,
            }
            for i, step in enumerate(steps)
        ]
        elem = CanvasElement(
            element_id=element_id,
            element_type=ElementType.PATH,
            position=(0, 0),
            style={},
            ttl_ms=ttl_ms,
            label=f"Action path ({len(steps)} steps)",
            data={"steps": step_data},
        )
        self._elements[element_id] = elem
        return element_id

    def show_tooltip(
        self,
        x: int,
        y: int,
        text: str,
        duration_ms: int = DEFAULT_TTL_MS,
    ) -> str:
        """
        Show a temporary floating tooltip at the given viewport coordinates.

        Requires: canvas.overlay.render scope.

        Args:
            x:           Horizontal viewport position in pixels.
            y:           Vertical viewport position in pixels.
            text:        Tooltip text content.
            duration_ms: How long the tooltip is visible (milliseconds).

        Returns:
            element_id string for the tooltip canvas element.

        Raises:
            PermissionError: If token lacks canvas.overlay.render scope.
            RuntimeError:    If max element limit (50) is reached.
        """
        self._require_scope(SCOPE_CANVAS_RENDER)
        self._evict_expired()
        self._enforce_element_limit()

        element_id = _new_element_id()
        elem = CanvasElement(
            element_id=element_id,
            element_type=ElementType.TOOLTIP,
            position=(x, y),
            style={"background": "#1e293b", "color": "#f8fafc"},
            ttl_ms=duration_ms,
            label=text,
            data={"text": text},
        )
        self._elements[element_id] = elem
        return element_id

    def add_annotation(
        self,
        x: int,
        y: int,
        text: str,
        color: str = "#6366f1",
        ttl_ms: Optional[int] = DEFAULT_TTL_MS,
    ) -> str:
        """
        Add an inline annotation text element at the given position.

        Requires: canvas.overlay.render scope.

        Args:
            x:      Horizontal viewport position in pixels.
            y:      Vertical viewport position in pixels.
            text:   Annotation text content.
            color:  CSS color string for the annotation.
            ttl_ms: Time-to-live in milliseconds.

        Returns:
            element_id string for the annotation canvas element.
        """
        self._require_scope(SCOPE_CANVAS_RENDER)
        self._evict_expired()
        self._enforce_element_limit()

        element_id = _new_element_id()
        elem = CanvasElement(
            element_id=element_id,
            element_type=ElementType.ANNOTATION,
            position=(x, y),
            style={"color": color},
            ttl_ms=ttl_ms,
            label=text,
            data={"text": text},
        )
        self._elements[element_id] = elem
        return element_id

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def render(self) -> str:
        """
        Generate the current overlay HTML string.

        Requires: canvas.overlay.render scope.

        Returns:
            HTML string for the overlay fragment.
        """
        self._require_scope(SCOPE_CANVAS_RENDER)
        self._evict_expired()
        return self._renderer.render(list(self._elements.values()))

    # -------------------------------------------------------------------------
    # Control
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        """
        Remove all canvas elements from the overlay.

        Safe to call whether attached or not.
        Does NOT require a scope — clearing is always permitted.
        """
        self._elements.clear()

    def remove_element(self, element_id: str) -> bool:
        """
        Remove a single canvas element by ID.

        Args:
            element_id: ID returned by a prior highlight/path/tooltip call.

        Returns:
            True if removed, False if element_id was not found.
        """
        if element_id in self._elements:
            del self._elements[element_id]
            return True
        return False

    # -------------------------------------------------------------------------
    # Properties / inspection
    # -------------------------------------------------------------------------

    @property
    def attached(self) -> bool:
        """True if the canvas is currently attached to a page."""
        return self._attached

    @property
    def element_count(self) -> int:
        """Current number of live canvas elements (after TTL eviction)."""
        self._evict_expired()
        return len(self._elements)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _require_scope(self, scope: str) -> None:
        """
        Assert that the token grants the required scope.

        Fail-closed: raises PermissionError if scope is absent.

        Args:
            scope: Required OAuth3 scope string.

        Raises:
            PermissionError: If the token does not contain `scope`.
        """
        if not self._token.has_scope(scope):
            raise PermissionError(
                f"OAuth3 scope required: '{scope}'. "
                f"Token scopes: {list(self._token.scopes)}"
            )

    def _evict_expired(self) -> None:
        """Remove all canvas elements whose TTL has elapsed."""
        now_ms = int(time.time() * 1000)
        expired_ids = [
            eid for eid, elem in self._elements.items()
            if elem.is_expired(now_ms)
        ]
        for eid in expired_ids:
            del self._elements[eid]

    def _enforce_element_limit(self) -> None:
        """
        Raise RuntimeError if adding another element would exceed MAX_ELEMENTS.

        This prevents visual spam from runaway agents.

        Raises:
            RuntimeError: If element count is already at MAX_ELEMENTS.
        """
        if len(self._elements) >= MAX_ELEMENTS:
            raise RuntimeError(
                f"Canvas element limit reached ({MAX_ELEMENTS}). "
                "Call clear() or wait for elements to expire before adding more."
            )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _new_element_id() -> str:
    """Return a fresh unique element ID."""
    return f"ce-{uuid.uuid4().hex[:12]}"


def _escape_html(text: str) -> str:
    """Escape HTML special characters to prevent XSS in overlay labels."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _escape_attr(text: str) -> str:
    """Escape for use in HTML attribute values."""
    return _escape_html(text)
