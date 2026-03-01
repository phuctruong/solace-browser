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
    YinyangStateBridge,
    STATE_COLOR_MAP,
    AUTO_EXPAND_STATES,
    AUTO_COLLAPSE_STATES,
)
from execution_lifecycle import ExecutionState


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
    def test_all_execution_states_have_colors(self):
        """Every ExecutionState should have a color in STATE_COLOR_MAP."""
        for state in ExecutionState:
            assert state in STATE_COLOR_MAP, f"Missing color for {state}"

    def test_auto_expand_states_are_valid(self):
        """Auto-expand states should be valid ExecutionState values."""
        for state in AUTO_EXPAND_STATES:
            assert isinstance(state, ExecutionState)

    def test_auto_collapse_states_are_valid(self):
        """Auto-collapse states should be valid ExecutionState values."""
        for state in AUTO_COLLAPSE_STATES:
            assert isinstance(state, ExecutionState)

    def test_preview_ready_auto_expands(self):
        assert ExecutionState.PREVIEW_READY in AUTO_EXPAND_STATES

    def test_blocked_auto_expands(self):
        assert ExecutionState.BLOCKED in AUTO_EXPAND_STATES

    def test_failed_auto_expands(self):
        assert ExecutionState.FAILED in AUTO_EXPAND_STATES

    def test_done_auto_collapses(self):
        assert ExecutionState.DONE in AUTO_COLLAPSE_STATES

    def test_sealed_abort_auto_collapses(self):
        assert ExecutionState.SEALED_ABORT in AUTO_COLLAPSE_STATES

    def test_done_is_green(self):
        assert STATE_COLOR_MAP[ExecutionState.DONE] == "green"

    def test_blocked_is_red(self):
        assert STATE_COLOR_MAP[ExecutionState.BLOCKED] == "red"

    def test_executing_is_blue(self):
        assert STATE_COLOR_MAP[ExecutionState.EXECUTING] == "blue"

    def test_no_overlap_expand_collapse(self):
        """No state should be in both auto-expand and auto-collapse."""
        assert AUTO_EXPAND_STATES.isdisjoint(AUTO_COLLAPSE_STATES)


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
