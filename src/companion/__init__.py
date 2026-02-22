"""
companion/ — Companion App system for Solace Browser.

Companion apps are mini-applications that run alongside the browser agent,
all gated by OAuth3 scopes.

Public API:
    from companion.apps import (
        CompanionApp, AppRegistry, AppLifecycle, AppEvent, AppResponse,
        AppState, InvalidTransitionError, AppRegistryError, AppScopeError,
    )
    from companion.bridge import (
        AppBridge, BrowserAction, ActionResult, EventBus,
        BridgeScopeError, BridgeRateLimitError, SubscriptionLimitError,
    )
    from companion.builtin import ClipboardMonitor, SessionRecorder, TaskTracker
    from companion.scopes import COMPANION_SCOPES, ALL_COMPANION_SCOPES

Rung: 641 (local correctness)
"""

# Register companion scopes into OAuth3 registry on package import
from companion import scopes as _scopes_mod  # noqa: F401

__version__ = "1.0.0"
__rung__ = 641
