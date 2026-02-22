"""
solace-browser channels package — OAuth3-governed multi-channel messaging gateway.

Adds omnichannel AI agent messaging to SolaceBrowser, gated by OAuth3
consent-bound delegation per channel.

Architecture:
  gateway.py — ChannelGateway, ChannelMessage, ChannelConfig, PairedSender, ChannelType
  scopes.py  — Channel-specific OAuth3 scope definitions + registration helper

Supported channels:
  Telegram, Discord, Slack, WhatsApp, Signal, Matrix, IRC, Email, SMS, WebChat

OAuth3 scope pattern: channel.<platform>.<action>
  Examples: channel.telegram.read, channel.telegram.send

Registration:
  Channel scopes are NOT auto-registered on import (unlike machine/).
  Call register_channel_scopes() explicitly at application startup:

    from src.channels import register_channel_scopes
    register_channel_scopes()

Reference: solace-browser messaging gateway spec
Rung: 641 (local correctness)
"""

from src.channels.gateway import (
    ChannelGateway,
    ChannelMessage,
    ChannelConfig,
    ChannelType,
    PairedSender,
)
from src.channels.scopes import (
    CHANNEL_SCOPES,
    register_channel_scopes,
    SCOPE_TELEGRAM_READ,
    SCOPE_TELEGRAM_SEND,
    SCOPE_DISCORD_READ,
    SCOPE_DISCORD_SEND,
    SCOPE_SLACK_READ,
    SCOPE_SLACK_SEND,
    SCOPE_WHATSAPP_READ,
    SCOPE_WHATSAPP_SEND,
    SCOPE_SIGNAL_READ,
    SCOPE_SIGNAL_SEND,
    SCOPE_MATRIX_READ,
    SCOPE_MATRIX_SEND,
    SCOPE_IRC_READ,
    SCOPE_IRC_SEND,
    SCOPE_EMAIL_READ,
    SCOPE_EMAIL_SEND,
    SCOPE_SMS_READ,
    SCOPE_SMS_SEND,
    SCOPE_WEB_CHAT_READ,
    SCOPE_WEB_CHAT_SEND,
)

__all__ = [
    # Core classes
    "ChannelGateway",
    "ChannelMessage",
    "ChannelConfig",
    "ChannelType",
    "PairedSender",
    # Scopes
    "CHANNEL_SCOPES",
    "register_channel_scopes",
    "SCOPE_TELEGRAM_READ",
    "SCOPE_TELEGRAM_SEND",
    "SCOPE_DISCORD_READ",
    "SCOPE_DISCORD_SEND",
    "SCOPE_SLACK_READ",
    "SCOPE_SLACK_SEND",
    "SCOPE_WHATSAPP_READ",
    "SCOPE_WHATSAPP_SEND",
    "SCOPE_SIGNAL_READ",
    "SCOPE_SIGNAL_SEND",
    "SCOPE_MATRIX_READ",
    "SCOPE_MATRIX_SEND",
    "SCOPE_IRC_READ",
    "SCOPE_IRC_SEND",
    "SCOPE_EMAIL_READ",
    "SCOPE_EMAIL_SEND",
    "SCOPE_SMS_READ",
    "SCOPE_SMS_SEND",
    "SCOPE_WEB_CHAT_READ",
    "SCOPE_WEB_CHAT_SEND",
]

__version__ = "0.1.0"
__rung__ = 641
