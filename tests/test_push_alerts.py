"""Tests for YinyangPushAlerts — push notification system with three channels.

Tests cover:
  - PushNotification creation and serialization
  - AlertChannel classification from triggers
  - AmbientContext detection and Anti-Clippy 4-gate clearance
  - Asset mapping for triggers
  - Push alert JavaScript content validation

Channel [7] — Context + Tools. Rung: 65537.
DNA: test(push_alerts) → verify(channels, gates, assets, js) → evidence(pass/fail)
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yinyang.push_alerts import (
    TRIGGER_ASSET_MAP,
    TRIGGER_CHANNEL_MAP,
    TRIGGER_PRIORITY_MAP,
    URL_APP_PATTERNS,
    AlertChannel,
    AlertTrigger,
    AmbientContext,
    PushNotification,
    SuggestionGateResult,
    YinyangAsset,
    _PUSH_ALERT_JS,
    inject_push_alerts,
    send_push_notification,
)


# ---------------------------------------------------------------------------
# PushNotification tests
# ---------------------------------------------------------------------------

class TestPushNotification:
    """Test PushNotification creation and serialization."""

    def test_create_basic_notification(self):
        n = PushNotification(
            trigger=AlertTrigger.SCHEDULED_COMPLETE,
            message="Your morning brief is ready",
        )
        assert n.trigger == AlertTrigger.SCHEDULED_COMPLETE
        assert n.message == "Your morning brief is ready"
        assert n.channel == AlertChannel.TOAST
        assert n.priority == "low"
        assert n.asset == YinyangAsset.TOP_RAIL_LOGO

    def test_create_high_priority_notification(self):
        n = PushNotification(
            trigger=AlertTrigger.BUDGET_WARNING,
            message="Budget 80% consumed",
        )
        assert n.channel == AlertChannel.POPUP
        assert n.priority == "high"
        assert n.asset == YinyangAsset.POPUP_LOGO

    def test_override_channel(self):
        n = PushNotification(
            trigger=AlertTrigger.SCHEDULED_COMPLETE,
            message="test",
            channel=AlertChannel.TAKEOVER,
        )
        assert n.channel == AlertChannel.TAKEOVER

    def test_override_priority(self):
        n = PushNotification(
            trigger=AlertTrigger.STORE_UPDATE,
            message="test",
            priority="critical",
        )
        assert n.priority == "critical"

    def test_to_dict_structure(self):
        n = PushNotification(
            trigger=AlertTrigger.DRIFT_DETECTION,
            message="Gmail UI changed",
            action_url="/apps/gmail-triage",
            action_label="Fix now",
            run_id="run-123",
            app_id="gmail-triage",
        )
        d = n.to_dict()
        assert d["type"] == "push_notification"
        payload = d["payload"]
        assert payload["trigger"] == "drift_detection"
        assert payload["message"] == "Gmail UI changed"
        assert payload["channel"] == "popup"
        assert payload["priority"] == "high"
        assert payload["asset"] == "droplet-logo-rotating_70pct_256px.gif"
        assert payload["action_url"] == "/apps/gmail-triage"
        assert payload["action_label"] == "Fix now"
        assert payload["run_id"] == "run-123"
        assert payload["app_id"] == "gmail-triage"
        assert "created_at" in payload

    def test_toast_auto_dismiss(self):
        n = PushNotification(
            trigger=AlertTrigger.LEARNING_SIGNAL,
            message="Recipe improved",
        )
        d = n.to_dict()
        assert d["payload"]["auto_dismiss_ms"] == 5000
        assert d["payload"]["auto_expand"] is False

    def test_takeover_auto_expand(self):
        n = PushNotification(
            trigger=AlertTrigger.BUDGET_WARNING,
            message="Critical budget",
            channel=AlertChannel.TAKEOVER,
        )
        d = n.to_dict()
        assert d["payload"]["auto_dismiss_ms"] == 0
        assert d["payload"]["auto_expand"] is True

    def test_popup_no_auto_dismiss(self):
        n = PushNotification(
            trigger=AlertTrigger.TOKEN_EXPIRY,
            message="Token expiring",
        )
        d = n.to_dict()
        assert d["payload"]["auto_dismiss_ms"] == 0
        assert d["payload"]["auto_expand"] is False

    def test_context_dict(self):
        ctx = {"app_id": "gmail-triage", "runs": 100}
        n = PushNotification(
            trigger=AlertTrigger.EVIDENCE_MILESTONE,
            message="100 runs",
            context=ctx,
        )
        d = n.to_dict()
        assert d["payload"]["context"]["runs"] == 100

    def test_cross_app_event_uses_merge_asset(self):
        n = PushNotification(
            trigger=AlertTrigger.CROSS_APP_EVENT,
            message="Slack mentions your Gmail draft",
        )
        assert n.asset == YinyangAsset.CROSS_APP_MERGE


# ---------------------------------------------------------------------------
# Trigger mapping tests
# ---------------------------------------------------------------------------

class TestTriggerMappings:
    """Test that all triggers have channel, priority, and asset mappings."""

    def test_all_triggers_have_channel(self):
        for trigger in AlertTrigger:
            assert trigger in TRIGGER_CHANNEL_MAP, f"Missing channel for {trigger}"

    def test_all_triggers_have_priority(self):
        for trigger in AlertTrigger:
            assert trigger in TRIGGER_PRIORITY_MAP, f"Missing priority for {trigger}"

    def test_all_triggers_have_asset(self):
        for trigger in AlertTrigger:
            assert trigger in TRIGGER_ASSET_MAP, f"Missing asset for {trigger}"

    def test_high_priority_triggers(self):
        high = [t for t, p in TRIGGER_PRIORITY_MAP.items() if p == "high"]
        assert AlertTrigger.BUDGET_WARNING in high
        assert AlertTrigger.DRIFT_DETECTION in high
        assert AlertTrigger.TOKEN_EXPIRY in high

    def test_popup_channel_triggers(self):
        popup = [t for t, c in TRIGGER_CHANNEL_MAP.items() if c == AlertChannel.POPUP]
        assert AlertTrigger.BUDGET_WARNING in popup
        assert AlertTrigger.DRIFT_DETECTION in popup


# ---------------------------------------------------------------------------
# AlertChannel tests
# ---------------------------------------------------------------------------

class TestAlertChannel:
    """Test alert channel enum values."""

    def test_three_channels(self):
        assert len(AlertChannel) == 3

    def test_channel_values(self):
        assert AlertChannel.TOAST.value == "toast"
        assert AlertChannel.POPUP.value == "popup"
        assert AlertChannel.TAKEOVER.value == "takeover"


# ---------------------------------------------------------------------------
# YinyangAsset tests
# ---------------------------------------------------------------------------

class TestYinyangAsset:
    """Test Yinyang image asset enum."""

    def test_six_assets(self):
        assert len(YinyangAsset) == 6

    def test_popup_logo(self):
        assert YinyangAsset.POPUP_LOGO.value == "droplet-logo-rotating_70pct_256px.gif"

    def test_notification_icon(self):
        assert YinyangAsset.NOTIFICATION_ICON.value == "droplet-logo-rotating_70pct_128px.gif"

    def test_loading_small(self):
        assert YinyangAsset.LOADING_SMALL.value == "yinyang-loading-128.gif"


# ---------------------------------------------------------------------------
# AmbientContext tests
# ---------------------------------------------------------------------------

class TestAmbientContext:
    """Test ambient context detection and Anti-Clippy gate checks."""

    def test_detect_gmail(self):
        ctx = AmbientContext()
        app = ctx.detect_app("https://mail.google.com/mail/u/0/#inbox")
        assert app == "gmail-triage"

    def test_detect_linkedin(self):
        ctx = AmbientContext()
        app = ctx.detect_app("https://www.linkedin.com/feed/")
        assert app == "linkedin-growth"

    def test_detect_unknown(self):
        ctx = AmbientContext()
        app = ctx.detect_app("https://random-website.com")
        assert app is None

    def test_visit_count_increments(self):
        ctx = AmbientContext()
        ctx.detect_app("https://mail.google.com/mail")
        ctx.detect_app("https://mail.google.com/mail")
        ctx.detect_app("https://mail.google.com/mail")
        assert ctx.get_visit_count("gmail-triage") == 3

    def test_suggestion_gate_passed(self):
        ctx = AmbientContext()
        result = ctx.should_suggest("gmail-triage")
        assert result == SuggestionGateResult.PASSED

    def test_suggestion_gate_blocked_by_blacklist(self):
        ctx = AmbientContext()
        ctx.blacklist_suggestion("gmail-triage")
        result = ctx.should_suggest("gmail-triage")
        assert result == SuggestionGateResult.BLOCKED_DISMISSED

    def test_suggestion_gate_blocked_by_active_task(self):
        ctx = AmbientContext()
        ctx.set_user_active(True)
        result = ctx.should_suggest("gmail-triage")
        assert result == SuggestionGateResult.BLOCKED_ACTIVE_TASK

    def test_suggestion_gate_blocked_by_cooldown(self):
        ctx = AmbientContext()
        ctx.record_suggestion("gmail-triage")
        result = ctx.should_suggest("gmail-triage")
        assert result == SuggestionGateResult.BLOCKED_COOLDOWN

    def test_suggestion_gate_blocked_by_dnd(self):
        ctx = AmbientContext()
        ctx.set_dnd(True)
        result = ctx.should_suggest("gmail-triage")
        assert result == SuggestionGateResult.BLOCKED_DND

    def test_dnd_property(self):
        ctx = AmbientContext()
        assert ctx.is_dnd is False
        ctx.set_dnd(True)
        assert ctx.is_dnd is True

    def test_gate_priority_order(self):
        """Blacklist check runs before active task check."""
        ctx = AmbientContext()
        ctx.blacklist_suggestion("test")
        ctx.set_user_active(True)
        result = ctx.should_suggest("test")
        # Should be BLOCKED_DISMISSED (gate 1) not BLOCKED_ACTIVE_TASK (gate 2)
        assert result == SuggestionGateResult.BLOCKED_DISMISSED


# ---------------------------------------------------------------------------
# URL pattern tests
# ---------------------------------------------------------------------------

class TestURLPatterns:
    """Test URL → app_id pattern mapping."""

    def test_all_patterns_have_app_ids(self):
        for pattern, app_id in URL_APP_PATTERNS.items():
            assert app_id, f"Empty app_id for pattern {pattern}"

    def test_known_patterns(self):
        assert URL_APP_PATTERNS["mail.google.com"] == "gmail-triage"
        assert URL_APP_PATTERNS["linkedin.com"] == "linkedin-growth"
        assert URL_APP_PATTERNS["slack.com"] == "slack-triage"
        assert URL_APP_PATTERNS["github.com"] == "github-triage"
        assert URL_APP_PATTERNS["calendar.google.com"] == "morning-brief"

    def test_twitter_and_x(self):
        assert URL_APP_PATTERNS["twitter.com"] == "twitter-growth"
        assert URL_APP_PATTERNS["x.com"] == "twitter-growth"


# ---------------------------------------------------------------------------
# Push alert JavaScript tests
# ---------------------------------------------------------------------------

class TestPushAlertJS:
    """Test JavaScript injection content."""

    def test_js_has_toast_function(self):
        assert "function showToast" in _PUSH_ALERT_JS

    def test_js_has_popup_function(self):
        assert "function showPopup" in _PUSH_ALERT_JS

    def test_js_prevents_double_injection(self):
        assert "__solace_push_alerts_injected" in _PUSH_ALERT_JS

    def test_js_listens_for_push_notification(self):
        assert "push_notification" in _PUSH_ALERT_JS

    def test_js_has_animations(self):
        assert "solace-toast-in" in _PUSH_ALERT_JS
        assert "solace-fade-in" in _PUSH_ALERT_JS

    def test_js_has_auto_dismiss(self):
        assert "auto_dismiss_ms" in _PUSH_ALERT_JS

    def test_js_has_img_placeholder(self):
        assert "__IMG_BASE_URL__" in _PUSH_ALERT_JS

    def test_js_handles_toast_channel(self):
        assert "channel === 'toast'" in _PUSH_ALERT_JS

    def test_js_handles_popup_channel(self):
        assert "channel === 'popup'" in _PUSH_ALERT_JS


# ---------------------------------------------------------------------------
# Async injection tests
# ---------------------------------------------------------------------------

class TestInjection:
    """Test inject_push_alerts and send_push_notification async functions."""

    @pytest.mark.asyncio
    async def test_inject_push_alerts(self):
        page = AsyncMock()
        await inject_push_alerts(page, img_base_url="/images/yinyang")
        page.add_init_script.assert_called_once()
        js_arg = page.add_init_script.call_args[0][0]
        assert "/images/yinyang" in js_arg
        assert "__IMG_BASE_URL__" not in js_arg

    @pytest.mark.asyncio
    async def test_send_push_notification(self):
        page = AsyncMock()
        n = PushNotification(
            trigger=AlertTrigger.EVIDENCE_MILESTONE,
            message="100th run captured!",
        )
        await send_push_notification(page, n)
        page.evaluate.assert_called_once()
        call_args = page.evaluate.call_args
        assert "postMessage" in call_args[0][0]
        payload = call_args[0][1]
        assert payload["type"] == "push_notification"
        assert payload["payload"]["message"] == "100th run captured!"
