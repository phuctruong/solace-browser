"""Yinyang Chat Rail — browser-side injection for top/bottom rails + delight engine + push alerts."""
__version__ = "0.4.0"

from yinyang.alert_queue import YinyangAlertQueue
from yinyang.delight_engine import YinyangDelightEngine
from yinyang.push_alerts import (
    AlertChannel,
    AlertTrigger,
    AmbientContext,
    PushNotification,
    YinyangAsset,
    inject_push_alerts,
    send_push_notification,
)
from yinyang.support_bridge import YinyangSupportBridge

__all__ = [
    "YinyangAlertQueue",
    "YinyangDelightEngine",
    "YinyangSupportBridge",
    "AlertChannel",
    "AlertTrigger",
    "AmbientContext",
    "PushNotification",
    "YinyangAsset",
    "inject_push_alerts",
    "send_push_notification",
]
