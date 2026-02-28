"""Comprehensive integration tests for Yinyang chat rail system."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from yinyang import __version__
from yinyang.top_rail import _INLINE_TOP_RAIL_JS, TOP_RAIL_JS
from yinyang.bottom_rail import _INLINE_BOTTOM_RAIL_JS, BOTTOM_RAIL_JS
from yinyang.ws_bridge import YinyangWSBridge
from yinyang.highlighter import YinyangHighlighter
from yinyang.state_bridge import (
    StateBridge,
    YinyangState,
    STATE_COLORS,
    VALID_TRANSITIONS,
)


class TestYinyangModule:
    def test_version_exists(self):
        assert __version__ is not None
        assert isinstance(__version__, str)


class TestTopRail:
    def test_inline_js_creates_rail_element(self):
        assert "solace-top-rail" in _INLINE_TOP_RAIL_JS

    def test_inline_js_has_state_listener(self):
        assert "yinyang_state" in _INLINE_TOP_RAIL_JS

    def test_inline_js_has_state_colors(self):
        assert "#4a9eff" in _INLINE_TOP_RAIL_JS  # listening/processing
        assert "#27ae60" in _INLINE_TOP_RAIL_JS  # done/executing
        assert "#e74c3c" in _INLINE_TOP_RAIL_JS  # error/blocked

    def test_rail_js_path_is_absolute(self):
        assert TOP_RAIL_JS.is_absolute()


class TestBottomRail:
    def test_inline_js_creates_rail_element(self):
        assert "solace-bottom-rail" in _INLINE_BOTTOM_RAIL_JS

    def test_inline_js_has_ws_placeholder(self):
        assert "__WS_URL__" in _INLINE_BOTTOM_RAIL_JS

    def test_inline_js_has_toggle(self):
        assert "toggleRail" in _INLINE_BOTTOM_RAIL_JS

    def test_inline_js_has_send(self):
        assert "sendMessage" in _INLINE_BOTTOM_RAIL_JS

    def test_inline_js_has_credits(self):
        assert "credits" in _INLINE_BOTTOM_RAIL_JS.lower()

    def test_rail_js_path_is_absolute(self):
        assert BOTTOM_RAIL_JS.is_absolute()


class TestHighlighter:
    def test_highlight_color_has_rgba(self):
        assert "r" in YinyangHighlighter.HIGHLIGHT_COLOR
        assert "a" in YinyangHighlighter.HIGHLIGHT_COLOR
        assert 0 < YinyangHighlighter.HIGHLIGHT_COLOR["a"] < 1

    def test_outline_color_has_rgba(self):
        assert "r" in YinyangHighlighter.OUTLINE_COLOR
        assert YinyangHighlighter.OUTLINE_COLOR["a"] > YinyangHighlighter.HIGHLIGHT_COLOR["a"]


class TestStateBridge:
    def test_all_states_have_colors(self):
        for state in YinyangState:
            assert state in STATE_COLORS, f"Missing color for {state}"

    def test_all_states_have_transitions(self):
        for state in YinyangState:
            assert state in VALID_TRANSITIONS, f"Missing transitions for {state}"

    def test_idle_is_initial_state(self):
        # Can't instantiate without a page, but verify the enum
        assert YinyangState.IDLE.value == "idle"

    def test_error_returns_to_idle(self):
        assert YinyangState.IDLE in VALID_TRANSITIONS[YinyangState.ERROR]

    def test_blocked_returns_to_idle(self):
        assert YinyangState.IDLE in VALID_TRANSITIONS[YinyangState.BLOCKED]

    def test_done_returns_to_idle(self):
        assert YinyangState.IDLE in VALID_TRANSITIONS[YinyangState.DONE]

    def test_full_happy_path_transitions(self):
        """Verify the complete happy path: IDLE -> ... -> DONE -> IDLE."""
        happy_path = [
            YinyangState.IDLE,
            YinyangState.LISTENING,
            YinyangState.PROCESSING,
            YinyangState.INTENT_CLASSIFIED,
            YinyangState.PREVIEW_GENERATING,
            YinyangState.PREVIEW_READY,
            YinyangState.COOLDOWN,
            YinyangState.APPROVED,
            YinyangState.SEALED,
            YinyangState.EXECUTING,
            YinyangState.DONE,
            YinyangState.IDLE,
        ]
        for i in range(len(happy_path) - 1):
            current = happy_path[i]
            next_state = happy_path[i + 1]
            assert next_state in VALID_TRANSITIONS[current], \
                f"Transition {current.value} -> {next_state.value} not in VALID_TRANSITIONS"

    def test_every_state_can_reach_idle(self):
        """Every state should be able to reach IDLE (directly or via ERROR)."""
        for state in YinyangState:
            if state == YinyangState.IDLE:
                continue
            targets = VALID_TRANSITIONS[state]
            can_reach_idle = (
                YinyangState.IDLE in targets
                or YinyangState.ERROR in targets  # ERROR -> IDLE
            )
            assert can_reach_idle, f"{state.value} cannot reach IDLE"


class TestWSBridge:
    def test_default_cloud_url(self):
        bridge = YinyangWSBridge()
        assert "solaceagi.com" in bridge.cloud_url

    def test_custom_cloud_url(self):
        bridge = YinyangWSBridge(cloud_url="http://localhost:8000")
        assert bridge.cloud_url == "http://localhost:8000"

    def test_sessions_initially_empty(self):
        bridge = YinyangWSBridge()
        assert len(bridge.sessions) == 0

    def test_local_response_not_empty(self):
        bridge = YinyangWSBridge()
        for query in ["help", "apps", "credits", "random"]:
            resp = bridge._local_response(query)
            assert len(resp) > 0, f"Empty response for: {query}"
