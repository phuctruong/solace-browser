"""Tests for Yinyang chat rails."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from yinyang.ws_bridge import YinyangWSBridge
from yinyang.top_rail import _INLINE_TOP_RAIL_JS
from yinyang.bottom_rail import _INLINE_BOTTOM_RAIL_JS


def test_top_rail_js_valid():
    """Top rail JS should be valid JavaScript (basic check)."""
    assert "solace-top-rail" in _INLINE_TOP_RAIL_JS
    assert "yinyang_state" in _INLINE_TOP_RAIL_JS


def test_bottom_rail_js_valid():
    """Bottom rail JS should be valid JavaScript."""
    assert "solace-bottom-rail" in _INLINE_BOTTOM_RAIL_JS
    assert "__WS_URL__" in _INLINE_BOTTOM_RAIL_JS


def test_ws_bridge_init():
    bridge = YinyangWSBridge()
    assert bridge.cloud_url == "https://www.solaceagi.com"
    assert bridge.sessions == {}


def test_ws_bridge_local_response_help():
    bridge = YinyangWSBridge()
    resp = bridge._local_response("help me")
    assert "Yinyang" in resp


def test_ws_bridge_local_response_apps():
    bridge = YinyangWSBridge()
    resp = bridge._local_response("list apps available")
    assert "App Store" in resp


def test_ws_bridge_local_response_credits():
    bridge = YinyangWSBridge()
    resp = bridge._local_response("check my credits")
    assert "credit" in resp.lower()


def test_ws_bridge_local_response_default():
    bridge = YinyangWSBridge()
    resp = bridge._local_response("random input xyz")
    assert len(resp) > 0
