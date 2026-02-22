"""
Channel-specific OAuth3 scopes — multi-channel messaging gateway layer.

All scopes follow the triple-segment convention: platform.action.resource
Platform segment: "channel"

Scope naming: channel.<platform>.<action>
  e.g. channel.telegram.read, channel.telegram.send

Risk levels:
  low    — read-only, non-sensitive (web_chat read)
  medium — read-sensitive or limited write (most reads, web_chat send)
  high   — send/write to external messaging channels (destructive, irreversible)

These scopes extend the global SCOPE_REGISTRY when register_channel_scopes() is called.

Reference: oauth3-spec-v0.1.md §2
Rung: 641
"""

from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# Channel scope definitions (triple-segment: channel.<platform>.<action>)
# ---------------------------------------------------------------------------

CHANNEL_SCOPES: Dict[str, Dict] = {

    # -------------------------------------------------------------------------
    # Telegram
    # -------------------------------------------------------------------------

    "channel.telegram.read": {
        "platform": "channel",
        "description": "Read Telegram messages",
        "risk_level": "medium",
        "destructive": False,
    },
    "channel.telegram.send": {
        "platform": "channel",
        "description": "Send Telegram messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Discord
    # -------------------------------------------------------------------------

    "channel.discord.read": {
        "platform": "channel",
        "description": "Read Discord messages",
        "risk_level": "medium",
        "destructive": False,
    },
    "channel.discord.send": {
        "platform": "channel",
        "description": "Send Discord messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Slack
    # -------------------------------------------------------------------------

    "channel.slack.read": {
        "platform": "channel",
        "description": "Read Slack messages",
        "risk_level": "medium",
        "destructive": False,
    },
    "channel.slack.send": {
        "platform": "channel",
        "description": "Send Slack messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # WhatsApp
    # -------------------------------------------------------------------------

    "channel.whatsapp.read": {
        "platform": "channel",
        "description": "Read WhatsApp messages",
        "risk_level": "high",
        "destructive": False,
    },
    "channel.whatsapp.send": {
        "platform": "channel",
        "description": "Send WhatsApp messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Signal
    # -------------------------------------------------------------------------

    "channel.signal.read": {
        "platform": "channel",
        "description": "Read Signal messages",
        "risk_level": "high",
        "destructive": False,
    },
    "channel.signal.send": {
        "platform": "channel",
        "description": "Send Signal messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Matrix
    # -------------------------------------------------------------------------

    "channel.matrix.read": {
        "platform": "channel",
        "description": "Read Matrix messages",
        "risk_level": "medium",
        "destructive": False,
    },
    "channel.matrix.send": {
        "platform": "channel",
        "description": "Send Matrix messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # IRC
    # -------------------------------------------------------------------------

    "channel.irc.read": {
        "platform": "channel",
        "description": "Read IRC messages",
        "risk_level": "medium",
        "destructive": False,
    },
    "channel.irc.send": {
        "platform": "channel",
        "description": "Send IRC messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Email (generic, distinct from gmail.*)
    # -------------------------------------------------------------------------

    "channel.email.read": {
        "platform": "channel",
        "description": "Read email messages",
        "risk_level": "medium",
        "destructive": False,
    },
    "channel.email.send": {
        "platform": "channel",
        "description": "Send email messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # SMS
    # -------------------------------------------------------------------------

    "channel.sms.read": {
        "platform": "channel",
        "description": "Read SMS messages",
        "risk_level": "medium",
        "destructive": False,
    },
    "channel.sms.send": {
        "platform": "channel",
        "description": "Send SMS messages",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Web Chat (lowest risk — in-product messaging)
    # -------------------------------------------------------------------------

    "channel.web-chat.read": {
        "platform": "channel",
        "description": "Read web chat messages",
        "risk_level": "low",
        "destructive": False,
    },
    "channel.web-chat.send": {
        "platform": "channel",
        "description": "Send web chat messages",
        "risk_level": "medium",
        "destructive": False,
    },
}


# ---------------------------------------------------------------------------
# Registration helper — merges CHANNEL_SCOPES into the global SCOPE_REGISTRY
# ---------------------------------------------------------------------------

def register_channel_scopes(scope_registry: dict = None) -> dict:
    """
    Register all channel scopes into the OAuth3 scope registry.

    When called with no argument, merges into the live global SCOPE_REGISTRY
    and updates all derived sets (HIGH_RISK_SCOPES, DESTRUCTIVE_SCOPES, etc.).

    When called with an explicit scope_registry dict, merges into that dict
    and returns it (useful for testing or isolated environments).

    Args:
        scope_registry: Optional dict to merge scopes into. If None, merges
                        into the global SCOPE_REGISTRY from oauth3.scopes.

    Returns:
        The updated scope_registry dict.
    """
    if scope_registry is not None:
        # Explicit dict mode: update and return (no side-effects on globals)
        scope_registry.update(CHANNEL_SCOPES)
        return scope_registry

    # Global registry mode: merge into ALL loaded variants of the oauth3.scopes module.
    # Both "src.oauth3.scopes" and "oauth3.scopes" may be present in sys.modules
    # simultaneously (when sys.path includes the repo root AND src/). We patch both
    # so that AgencyToken.create() always sees the channel scopes regardless of which
    # import path was used.
    import sys as _sys

    _scopes_modules = []
    for _key in ("src.oauth3.scopes", "oauth3.scopes"):
        _mod = _sys.modules.get(_key)
        if _mod is not None:
            _scopes_modules.append(_mod)

    # If neither is loaded yet, force-load src.oauth3.scopes
    if not _scopes_modules:
        import src.oauth3.scopes as _fallback
        _scopes_modules.append(_fallback)

    for _scopes_mod in _scopes_modules:
        # Update SCOPE_REGISTRY in-place so references held by importers stay valid
        for scope, meta in CHANNEL_SCOPES.items():
            if scope not in _scopes_mod.SCOPE_REGISTRY:
                _scopes_mod.SCOPE_REGISTRY[scope] = meta

        # Update SCOPES dict in-place (backward-compat alias; test_oauth3_core imports it
        # with `from oauth3.scopes import SCOPES` and holds a reference to the same dict)
        _combined = {**_scopes_mod.SCOPE_REGISTRY, **_scopes_mod._LEGACY_SCOPE_ALIASES}
        _scopes_mod.SCOPES.update(
            {s: m["description"] for s, m in _combined.items()}
        )

        # Update _COMBINED_SCOPE_REGISTRY in-place as well
        _scopes_mod._COMBINED_SCOPE_REGISTRY.update(_combined)

        # Rebuild derived frozensets (these are replaced, not mutated — immutable)
        _scopes_mod.ALL_SCOPES = frozenset(_scopes_mod.SCOPE_REGISTRY.keys())
        _scopes_mod.HIGH_RISK_SCOPES = frozenset(
            s for s, m in _combined.items() if m["risk_level"] == "high"
        )
        _scopes_mod.DESTRUCTIVE_SCOPES = frozenset(
            s for s, m in _combined.items() if m["destructive"]
        )
        _scopes_mod.STEP_UP_REQUIRED_SCOPES = sorted(_scopes_mod.HIGH_RISK_SCOPES)

    # Also patch re-exported names in both oauth3 package namespaces
    for _pkg_key in ("src.oauth3", "oauth3"):
        _pkg = _sys.modules.get(_pkg_key)
        if _pkg is not None and _scopes_modules:
            _sm = _scopes_modules[0]
            _pkg.ALL_SCOPES = _sm.ALL_SCOPES
            _pkg.HIGH_RISK_SCOPES = _sm.HIGH_RISK_SCOPES
            _pkg.DESTRUCTIVE_SCOPES = _sm.DESTRUCTIVE_SCOPES
            _pkg.SCOPE_REGISTRY = _sm.SCOPE_REGISTRY

    return _scopes_modules[0].SCOPE_REGISTRY if _scopes_modules else {}


# ---------------------------------------------------------------------------
# Convenience scope name constants
# ---------------------------------------------------------------------------

SCOPE_TELEGRAM_READ  = "channel.telegram.read"
SCOPE_TELEGRAM_SEND  = "channel.telegram.send"
SCOPE_DISCORD_READ   = "channel.discord.read"
SCOPE_DISCORD_SEND   = "channel.discord.send"
SCOPE_SLACK_READ     = "channel.slack.read"
SCOPE_SLACK_SEND     = "channel.slack.send"
SCOPE_WHATSAPP_READ  = "channel.whatsapp.read"
SCOPE_WHATSAPP_SEND  = "channel.whatsapp.send"
SCOPE_SIGNAL_READ    = "channel.signal.read"
SCOPE_SIGNAL_SEND    = "channel.signal.send"
SCOPE_MATRIX_READ    = "channel.matrix.read"
SCOPE_MATRIX_SEND    = "channel.matrix.send"
SCOPE_IRC_READ       = "channel.irc.read"
SCOPE_IRC_SEND       = "channel.irc.send"
SCOPE_EMAIL_READ     = "channel.email.read"
SCOPE_EMAIL_SEND     = "channel.email.send"
SCOPE_SMS_READ       = "channel.sms.read"
SCOPE_SMS_SEND       = "channel.sms.send"
SCOPE_WEB_CHAT_READ  = "channel.web-chat.read"
SCOPE_WEB_CHAT_SEND  = "channel.web-chat.send"
