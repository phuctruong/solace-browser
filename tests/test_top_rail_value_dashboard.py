"""
Harsh QA tests for top rail value dashboard.

Tests: delight pool content, stat rendering, message types,
color mapping, rotation logic, value display elements.
"""
from __future__ import annotations

from pathlib import Path

import pytest


TOP_RAIL_JS = Path(__file__).parent.parent / "static" / "top_rail.js"


class TestTopRailFileExists:
    def test_static_js_exists(self):
        assert TOP_RAIL_JS.exists(), "static/top_rail.js must exist"

    def test_static_js_not_empty(self):
        content = TOP_RAIL_JS.read_text(encoding="utf-8")
        assert len(content) > 100, "top_rail.js must have meaningful content"


class TestTopRailValueElements:
    """Verify the value dashboard elements are present in JS."""

    @pytest.fixture
    def js(self):
        return TOP_RAIL_JS.read_text(encoding="utf-8")

    def test_value_display_element(self, js):
        assert "solace-value-display" in js

    def test_page_indicator_element(self, js):
        assert "solace-page-indicator" in js

    def test_state_dot_element(self, js):
        assert "solace-state-dot" in js

    def test_state_text_element(self, js):
        assert "solace-state-text" in js

    def test_app_label_element(self, js):
        assert "solace-app-label" in js


class TestDelightContent:
    """Verify delight pool has diverse content types."""

    @pytest.fixture
    def js(self):
        return TOP_RAIL_JS.read_text(encoding="utf-8")

    def test_has_facts(self, js):
        assert "type:'fact'" in js

    def test_has_tips(self, js):
        assert "type:'tip'" in js

    def test_has_quotes(self, js):
        assert "type:'quote'" in js

    def test_has_updates(self, js):
        assert "type:'update'" in js

    def test_delight_pool_exists(self, js):
        assert "DELIGHT_POOL" in js

    def test_bruce_lee_quote(self, js):
        assert "Bruce Lee" in js

    def test_sw5_reference(self, js):
        assert "SW5.0" in js or "Software 5.0" in js

    def test_recipe_replay_economics(self, js):
        assert "0.001" in js, "Should mention $0.001 recipe replay cost"

    def test_pzip_compression(self, js):
        assert "66:1" in js, "Should mention PZip 66:1 compression"

    def test_sealed_store_safety(self, js):
        assert "0% malware" in js or "sealed store" in js.lower()

    def test_oauth3_mention(self, js):
        assert "OAuth3" in js

    def test_part11_mention(self, js):
        assert "Part 11" in js

    def test_esign_mention(self, js):
        assert "esign" in js.lower() or "e-sign" in js.lower()

    def test_download_mention(self, js):
        assert "download" in js.lower()


class TestStatTracking:
    """Verify stat fields are tracked."""

    @pytest.fixture
    def js(self):
        return TOP_RAIL_JS.read_text(encoding="utf-8")

    def test_pages_visited_stat(self, js):
        assert "pages_visited" in js

    def test_llm_calls_stat(self, js):
        assert "llm_calls" in js

    def test_tokens_used_stat(self, js):
        assert "tokens_used" in js

    def test_cost_usd_stat(self, js):
        assert "cost_usd" in js

    def test_tokens_saved_stat(self, js):
        assert "tokens_saved" in js

    def test_savings_pct_stat(self, js):
        assert "savings_pct" in js

    def test_recipes_replayed_stat(self, js):
        assert "recipes_replayed" in js

    def test_evidence_captured_stat(self, js):
        assert "evidence_captured" in js

    def test_session_duration_tracked(self, js):
        assert "session_start" in js


class TestMessageTypes:
    """Verify postMessage types are handled."""

    @pytest.fixture
    def js(self):
        return TOP_RAIL_JS.read_text(encoding="utf-8")

    def test_yinyang_state_message(self, js):
        assert "yinyang_state" in js

    def test_yinyang_stats_message(self, js):
        assert "yinyang_stats" in js

    def test_message_listener(self, js):
        assert "addEventListener" in js
        assert "'message'" in js


class TestColorMapping:
    """Verify all FSM states have colors."""

    @pytest.fixture
    def js(self):
        return TOP_RAIL_JS.read_text(encoding="utf-8")

    def test_done_green(self, js):
        assert "DONE:'#27ae60'" in js

    def test_failed_red(self, js):
        assert "FAILED:'#e74c3c'" in js

    def test_executing_blue(self, js):
        assert "EXECUTING:'#4a9eff'" in js

    def test_preview_ready_yellow(self, js):
        assert "PREVIEW_READY:'#f5a623'" in js

    def test_idle_gray(self, js):
        assert "idle:'#666'" in js

    def test_blocked_red(self, js):
        assert "BLOCKED:'#e74c3c'" in js


class TestPulseAnimation:
    """Verify pulse animation on active states."""

    @pytest.fixture
    def js(self):
        return TOP_RAIL_JS.read_text(encoding="utf-8")

    def test_pulse_states_defined(self, js):
        assert "PULSE_STATES" in js

    def test_executing_pulses(self, js):
        assert "'EXECUTING'" in js

    def test_pulse_keyframes(self, js):
        assert "solace-pulse" in js

    def test_animation_toggle(self, js):
        assert "animation = 'none'" in js or "animation='none'" in js


class TestRotation:
    """Verify stats/delight rotation."""

    @pytest.fixture
    def js(self):
        return TOP_RAIL_JS.read_text(encoding="utf-8")

    def test_rotation_interval(self, js):
        assert "setInterval" in js

    def test_8_second_interval(self, js):
        assert "8000" in js, "Should rotate every 8 seconds"

    def test_showing_stats_toggle(self, js):
        assert "showingStats" in js

    def test_render_stats_function(self, js):
        assert "renderStats" in js


class TestFormatFunctions:
    """Verify formatting helpers."""

    @pytest.fixture
    def js(self):
        return TOP_RAIL_JS.read_text(encoding="utf-8")

    def test_format_cost_function(self, js):
        assert "formatCost" in js

    def test_format_tokens_function(self, js):
        assert "formatTokens" in js

    def test_session_duration_function(self, js):
        assert "sessionDuration" in js

    def test_million_abbreviation(self, js):
        assert "1000000" in js, "Should handle million token counts"

    def test_thousand_abbreviation(self, js):
        assert "1000" in js, "Should handle thousand token counts"
