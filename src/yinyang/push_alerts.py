"""YinyangPushAlerts — proactive notification system with three alert channels.

Three channels (Paper 18 / Diagram 19):
  TOAST:    Top rail pulse + dropdown (5s auto-dismiss). Low/medium priority.
  POPUP:    Animated Yinyang GIF overlay (centered). High priority.
  TAKEOVER: Bottom rail auto-expand + approve/reject. Critical priority.

Ambient awareness triggers:
  - Scheduled job completion
  - Budget warnings (80%+ consumed)
  - Evidence milestones
  - Drift detection (PrimeWiki selector change)
  - Cross-app event correlation
  - OAuth3 token expiry
  - Store updates
  - Team notifications
  - Learning signals (recipe hit rate improvement)
  - Holiday/celebration events

Anti-Clippy Law: Never auto-approve. Suggestions require 4-gate clearance.
Fallback Ban: No silent failures. Specific exceptions only.

Channel [7] — Context + Tools. Rung: 65537.
DNA: push(trigger) → classify(priority) → channel(toast|popup|takeover) → display → evidence
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("solace-browser.yinyang.push_alerts")


# ---------------------------------------------------------------------------
# Image assets (from solaceagi/web/images/yinyang/)
# ---------------------------------------------------------------------------

class YinyangAsset(Enum):
    """Animated GIF assets for push alert display."""
    POPUP_LOGO = "droplet-logo-rotating_70pct_256px.gif"
    NOTIFICATION_ICON = "droplet-logo-rotating_70pct_128px.gif"
    TOP_RAIL_LOGO = "yinyang-rotating_70pct_128px.gif"
    LOADING_SMALL = "yinyang-loading-128.gif"
    LOADING_LARGE = "yinyang-loading-256.gif"
    CROSS_APP_MERGE = "droplet-logo-merge_70pct_128px.gif"


# ---------------------------------------------------------------------------
# Alert channels
# ---------------------------------------------------------------------------

class AlertChannel(Enum):
    """Three alert delivery channels (Diagram 19)."""
    TOAST = "toast"          # Top rail pulse + dropdown (5s)
    POPUP = "popup"          # Animated GIF overlay (centered)
    TAKEOVER = "takeover"    # Bottom rail auto-expand + approve/reject


# ---------------------------------------------------------------------------
# Trigger types
# ---------------------------------------------------------------------------

class AlertTrigger(Enum):
    """10 push alert trigger types (Paper 18)."""
    SCHEDULED_COMPLETE = "scheduled_complete"
    BUDGET_WARNING = "budget_warning"
    EVIDENCE_MILESTONE = "evidence_milestone"
    DRIFT_DETECTION = "drift_detection"
    CROSS_APP_EVENT = "cross_app_event"
    TOKEN_EXPIRY = "token_expiry"
    STORE_UPDATE = "store_update"
    TEAM_NOTIFICATION = "team_notification"
    LEARNING_SIGNAL = "learning_signal"
    HOLIDAY_CELEBRATION = "holiday_celebration"


# Trigger → default channel mapping
TRIGGER_CHANNEL_MAP: dict[AlertTrigger, AlertChannel] = {
    AlertTrigger.SCHEDULED_COMPLETE: AlertChannel.TOAST,
    AlertTrigger.BUDGET_WARNING: AlertChannel.POPUP,
    AlertTrigger.EVIDENCE_MILESTONE: AlertChannel.TOAST,
    AlertTrigger.DRIFT_DETECTION: AlertChannel.POPUP,
    AlertTrigger.CROSS_APP_EVENT: AlertChannel.TOAST,
    AlertTrigger.TOKEN_EXPIRY: AlertChannel.POPUP,
    AlertTrigger.STORE_UPDATE: AlertChannel.TOAST,
    AlertTrigger.TEAM_NOTIFICATION: AlertChannel.TOAST,
    AlertTrigger.LEARNING_SIGNAL: AlertChannel.TOAST,
    AlertTrigger.HOLIDAY_CELEBRATION: AlertChannel.TOAST,
}

# Trigger → default priority
TRIGGER_PRIORITY_MAP: dict[AlertTrigger, str] = {
    AlertTrigger.SCHEDULED_COMPLETE: "low",
    AlertTrigger.BUDGET_WARNING: "high",
    AlertTrigger.EVIDENCE_MILESTONE: "low",
    AlertTrigger.DRIFT_DETECTION: "high",
    AlertTrigger.CROSS_APP_EVENT: "medium",
    AlertTrigger.TOKEN_EXPIRY: "high",
    AlertTrigger.STORE_UPDATE: "low",
    AlertTrigger.TEAM_NOTIFICATION: "medium",
    AlertTrigger.LEARNING_SIGNAL: "low",
    AlertTrigger.HOLIDAY_CELEBRATION: "low",
}

# Trigger → appropriate asset
TRIGGER_ASSET_MAP: dict[AlertTrigger, YinyangAsset] = {
    AlertTrigger.SCHEDULED_COMPLETE: YinyangAsset.TOP_RAIL_LOGO,
    AlertTrigger.BUDGET_WARNING: YinyangAsset.POPUP_LOGO,
    AlertTrigger.EVIDENCE_MILESTONE: YinyangAsset.TOP_RAIL_LOGO,
    AlertTrigger.DRIFT_DETECTION: YinyangAsset.POPUP_LOGO,
    AlertTrigger.CROSS_APP_EVENT: YinyangAsset.CROSS_APP_MERGE,
    AlertTrigger.TOKEN_EXPIRY: YinyangAsset.POPUP_LOGO,
    AlertTrigger.STORE_UPDATE: YinyangAsset.NOTIFICATION_ICON,
    AlertTrigger.TEAM_NOTIFICATION: YinyangAsset.NOTIFICATION_ICON,
    AlertTrigger.LEARNING_SIGNAL: YinyangAsset.TOP_RAIL_LOGO,
    AlertTrigger.HOLIDAY_CELEBRATION: YinyangAsset.POPUP_LOGO,
}


# ---------------------------------------------------------------------------
# Proactive suggestion Anti-Clippy gates
# ---------------------------------------------------------------------------

class SuggestionGateResult(Enum):
    """Result of Anti-Clippy 4-gate clearance check."""
    PASSED = "passed"
    BLOCKED_DISMISSED = "blocked_dismissed"
    BLOCKED_ACTIVE_TASK = "blocked_active_task"
    BLOCKED_COOLDOWN = "blocked_cooldown"
    BLOCKED_DND = "blocked_dnd"


# ---------------------------------------------------------------------------
# Push alert notification
# ---------------------------------------------------------------------------

class PushNotification:
    """A single push notification ready for display."""

    def __init__(
        self,
        trigger: AlertTrigger,
        message: str,
        *,
        channel: AlertChannel | None = None,
        priority: str | None = None,
        asset: YinyangAsset | None = None,
        action_url: str = "",
        action_label: str = "",
        run_id: str = "",
        app_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        self.trigger = trigger
        self.message = message
        self.channel = channel or TRIGGER_CHANNEL_MAP.get(trigger, AlertChannel.TOAST)
        self.priority = priority or TRIGGER_PRIORITY_MAP.get(trigger, "low")
        self.asset = asset or TRIGGER_ASSET_MAP.get(trigger, YinyangAsset.TOP_RAIL_LOGO)
        self.action_url = action_url
        self.action_label = action_label
        self.run_id = run_id
        self.app_id = app_id
        self.context = context or {}
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize for WebSocket transmission to browser JS."""
        return {
            "type": "push_notification",
            "payload": {
                "trigger": self.trigger.value,
                "message": self.message,
                "channel": self.channel.value,
                "priority": self.priority,
                "asset": self.asset.value,
                "action_url": self.action_url,
                "action_label": self.action_label,
                "run_id": self.run_id,
                "app_id": self.app_id,
                "context": self.context,
                "created_at": self.created_at,
                "auto_dismiss_ms": 5000 if self.channel == AlertChannel.TOAST else 0,
                "auto_expand": self.channel == AlertChannel.TAKEOVER,
            },
        }


# ---------------------------------------------------------------------------
# Ambient context detector
# ---------------------------------------------------------------------------

# Known app patterns — URL → app_id mapping
URL_APP_PATTERNS: dict[str, str] = {
    "mail.google.com": "gmail-triage",
    "linkedin.com": "linkedin-growth",
    "slack.com": "slack-triage",
    "calendar.google.com": "morning-brief",
    "github.com": "github-triage",
    "docs.google.com": "gdocs-writer",
    "drive.google.com": "gdrive-organizer",
    "twitter.com": "twitter-growth",
    "x.com": "twitter-growth",
}


class AmbientContext:
    """Detects browser context for proactive suggestions."""

    def __init__(self) -> None:
        self._visit_counts: dict[str, int] = {}
        self._last_suggestion_time: dict[str, datetime] = {}
        self._blacklisted_types: set[str] = set()
        self._dnd_active: bool = False
        self._user_active: bool = False

    def detect_app(self, url: str) -> str | None:
        """Detect which Solace app matches the current URL."""
        for pattern, app_id in URL_APP_PATTERNS.items():
            if pattern in url:
                self._visit_counts[app_id] = self._visit_counts.get(app_id, 0) + 1
                return app_id
        return None

    def get_visit_count(self, app_id: str) -> int:
        """Get how many times the user has visited pages matching this app."""
        return self._visit_counts.get(app_id, 0)

    def should_suggest(self, suggestion_type: str) -> SuggestionGateResult:
        """Anti-Clippy 4-gate clearance check (Diagram 19).

        Gate 1: Not previously dismissed permanently
        Gate 2: User not in active task
        Gate 3: Not suggested in last 30 minutes
        Gate 4: Do Not Disturb not active
        """
        # Gate 1: Blacklist check
        if suggestion_type in self._blacklisted_types:
            return SuggestionGateResult.BLOCKED_DISMISSED

        # Gate 2: Active task check
        if self._user_active:
            return SuggestionGateResult.BLOCKED_ACTIVE_TASK

        # Gate 3: Cooldown check (30 minutes)
        last_time = self._last_suggestion_time.get(suggestion_type)
        if last_time is not None:
            elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
            if elapsed < 1800:  # 30 minutes
                return SuggestionGateResult.BLOCKED_COOLDOWN

        # Gate 4: DND check
        if self._dnd_active:
            return SuggestionGateResult.BLOCKED_DND

        return SuggestionGateResult.PASSED

    def record_suggestion(self, suggestion_type: str) -> None:
        """Record that a suggestion was shown (starts cooldown)."""
        self._last_suggestion_time[suggestion_type] = datetime.now(timezone.utc)

    def blacklist_suggestion(self, suggestion_type: str) -> None:
        """Permanently suppress a suggestion type ("Never" clicked)."""
        self._blacklisted_types.add(suggestion_type)

    def set_user_active(self, active: bool) -> None:
        """Update whether user is actively interacting."""
        self._user_active = active

    def set_dnd(self, active: bool) -> None:
        """Toggle Do Not Disturb mode."""
        self._dnd_active = active

    @property
    def is_dnd(self) -> bool:
        """Check if Do Not Disturb is active."""
        return self._dnd_active


# ---------------------------------------------------------------------------
# Push alert JavaScript injection
# ---------------------------------------------------------------------------

# The JavaScript that handles push alerts in the browser.
# Injected via add_init_script() alongside top_rail and bottom_rail.
_PUSH_ALERT_JS = """
(function() {
    'use strict';

    // Prevent double injection
    if (window.__solace_push_alerts_injected) return;
    window.__solace_push_alerts_injected = true;

    // Image base URL (served from solaceagi.com)
    var IMG_BASE = '__IMG_BASE_URL__';

    // --- Toast notification ---
    function showToast(payload) {
        var existing = document.getElementById('solace-toast');
        if (existing) existing.remove();

        var toast = document.createElement('div');
        toast.id = 'solace-toast';
        toast.style.cssText = 'position:fixed;top:40px;right:16px;z-index:100000;' +
            'background:#1a1a2e;color:#e0e0e0;border:1px solid #333;border-radius:12px;' +
            'padding:12px 16px;max-width:360px;display:flex;align-items:center;gap:10px;' +
            'box-shadow:0 8px 32px rgba(0,0,0,0.4);font-family:system-ui,-apple-system,sans-serif;' +
            'font-size:13px;animation:solace-toast-in 0.3s ease-out;cursor:pointer;';

        var img = document.createElement('img');
        img.src = IMG_BASE + '/' + (payload.asset || 'yinyang-rotating_70pct_128px.gif');
        img.style.cssText = 'width:32px;height:32px;border-radius:50%;';
        img.alt = 'Solace';
        toast.appendChild(img);

        var textDiv = document.createElement('div');
        textDiv.style.cssText = 'flex:1;';

        var title = document.createElement('div');
        title.style.cssText = 'font-weight:600;font-size:12px;color:#8b5cf6;margin-bottom:2px;';
        title.textContent = (payload.trigger || 'notification').replace(/_/g, ' ').toUpperCase();
        textDiv.appendChild(title);

        var msg = document.createElement('div');
        msg.textContent = payload.message || '';
        textDiv.appendChild(msg);

        toast.appendChild(textDiv);

        var closeBtn = document.createElement('span');
        closeBtn.textContent = '\\u00d7';
        closeBtn.style.cssText = 'cursor:pointer;font-size:18px;color:#888;padding:0 4px;';
        closeBtn.onclick = function(e) { e.stopPropagation(); toast.remove(); };
        toast.appendChild(closeBtn);

        if (payload.action_url) {
            toast.onclick = function() { window.open(payload.action_url, '_blank'); toast.remove(); };
        }

        document.body.appendChild(toast);

        // Pulse the top rail
        var topRail = document.getElementById('solace-top-rail');
        if (topRail) {
            topRail.style.animation = 'solace-pulse 0.5s ease-in-out 3';
            setTimeout(function() { topRail.style.animation = ''; }, 1500);
        }

        // Auto-dismiss
        var dismissMs = payload.auto_dismiss_ms || 5000;
        if (dismissMs > 0) {
            setTimeout(function() { if (toast.parentNode) toast.remove(); }, dismissMs);
        }
    }

    // --- Popup notification (animated GIF overlay) ---
    function showPopup(payload) {
        var existing = document.getElementById('solace-popup-overlay');
        if (existing) existing.remove();

        var overlay = document.createElement('div');
        overlay.id = 'solace-popup-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:100001;' +
            'background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;' +
            'animation:solace-fade-in 0.3s ease-out;';

        var card = document.createElement('div');
        card.style.cssText = 'background:#1a1a2e;border:1px solid #444;border-radius:16px;' +
            'padding:24px;max-width:400px;width:90%;text-align:center;color:#e0e0e0;' +
            'font-family:system-ui,-apple-system,sans-serif;box-shadow:0 16px 64px rgba(0,0,0,0.5);';

        var img = document.createElement('img');
        img.src = IMG_BASE + '/' + (payload.asset || 'droplet-logo-rotating_70pct_256px.gif');
        img.style.cssText = 'width:128px;height:128px;margin:0 auto 16px;display:block;border-radius:50%;';
        img.alt = 'Solace Yinyang';
        card.appendChild(img);

        var titleEl = document.createElement('div');
        titleEl.style.cssText = 'font-weight:700;font-size:16px;color:#8b5cf6;margin-bottom:8px;';
        titleEl.textContent = (payload.trigger || 'alert').replace(/_/g, ' ').toUpperCase();
        card.appendChild(titleEl);

        var msgEl = document.createElement('div');
        msgEl.style.cssText = 'font-size:14px;line-height:1.5;margin-bottom:20px;';
        msgEl.textContent = payload.message || '';
        card.appendChild(msgEl);

        var btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:8px;justify-content:center;';

        if (payload.action_label && payload.action_url) {
            var actionBtn = document.createElement('button');
            actionBtn.textContent = payload.action_label;
            actionBtn.style.cssText = 'background:#8b5cf6;color:#fff;border:none;border-radius:8px;' +
                'padding:8px 20px;cursor:pointer;font-size:13px;font-weight:600;';
            actionBtn.onclick = function() { window.open(payload.action_url, '_blank'); overlay.remove(); };
            btnRow.appendChild(actionBtn);
        }

        var dismissBtn = document.createElement('button');
        dismissBtn.textContent = 'Dismiss';
        dismissBtn.style.cssText = 'background:#333;color:#e0e0e0;border:1px solid #555;border-radius:8px;' +
            'padding:8px 20px;cursor:pointer;font-size:13px;';
        dismissBtn.onclick = function() { overlay.remove(); };
        btnRow.appendChild(dismissBtn);

        card.appendChild(btnRow);
        overlay.appendChild(card);

        // Click outside to dismiss
        overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };

        document.body.appendChild(overlay);
    }

    // --- Inject CSS animations ---
    var style = document.createElement('style');
    style.textContent =
        '@keyframes solace-toast-in { from { opacity:0; transform:translateX(100px); } to { opacity:1; transform:translateX(0); } } ' +
        '@keyframes solace-fade-in { from { opacity:0; } to { opacity:1; } } ' +
        '@keyframes solace-pulse { 0%,100% { opacity:1; } 50% { opacity:0.6; } }';
    document.head.appendChild(style);

    // --- Listen for push notifications via postMessage ---
    window.addEventListener('message', function(event) {
        var data = event.data;
        if (!data || data.type !== 'push_notification') return;

        var payload = data.payload || {};
        var channel = payload.channel || 'toast';

        if (channel === 'toast') {
            showToast(payload);
        } else if (channel === 'popup') {
            showPopup(payload);
        }
        // 'takeover' is handled by bottom_rail.js (auto-expand)
    });

})();
"""


async def inject_push_alerts(page: Any, img_base_url: str = "/images/yinyang") -> None:
    """Inject push alert JavaScript into a Playwright page.

    Uses add_init_script() for persistence across navigations.

    Args:
        page: Playwright page object.
        img_base_url: Base URL for Yinyang GIF assets.
    """
    js_code = _PUSH_ALERT_JS.replace("__IMG_BASE_URL__", img_base_url)
    await page.add_init_script(js_code)
    logger.info("[Yinyang] Push alerts injected into page")


async def send_push_notification(page: Any, notification: PushNotification) -> None:
    """Send a push notification to the browser page via postMessage.

    Args:
        page: Playwright page object.
        notification: PushNotification instance.
    """
    payload = notification.to_dict()
    await page.evaluate(
        "data => window.postMessage(data, '*')",
        payload,
    )
    logger.info(
        "[Yinyang] Push notification sent: trigger=%s channel=%s",
        notification.trigger.value,
        notification.channel.value,
    )
