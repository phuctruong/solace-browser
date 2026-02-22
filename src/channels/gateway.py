"""
Multi-Channel Messaging Gateway — OAuth3-governed omnichannel AI agent layer.

Every inbound and outbound message is gated by OAuth3 four-gate enforcement:
  G1: Schema  — token parses, required fields present
  G2: TTL     — token not expired
  G3: Scope   — required channel scope present in token
  G4: Revocation — token not revoked

Audit trail is append-only: every message event is logged with SHA-256 hash.
No new external dependencies — this is a protocol layer only.
Actual channel adapters (Telegram Bot API, Discord SDK, etc.) plug in later
via the register_handler() interface.

Architecture:
  ChannelType     — Enum of supported messaging channels
  ChannelMessage  — Inbound message dataclass
  ChannelConfig   — Per-channel configuration + OAuth3 scope binding
  PairedSender    — Sender → OAuth3-scoped-agent pairing record
  ChannelGateway  — Orchestrator (register, pair, receive, send, audit)

Reference: solace-browser messaging gateway spec
Rung: 641 (local correctness)
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# ChannelType — supported messaging platforms
# ---------------------------------------------------------------------------

class ChannelType(Enum):
    TELEGRAM  = "telegram"
    DISCORD   = "discord"
    SLACK     = "slack"
    WHATSAPP  = "whatsapp"
    SIGNAL    = "signal"
    MATRIX    = "matrix"
    IRC       = "irc"
    EMAIL     = "email"
    SMS       = "sms"
    WEB_CHAT  = "web_chat"


# ---------------------------------------------------------------------------
# ChannelMessage — inbound message dataclass
# ---------------------------------------------------------------------------

@dataclass
class ChannelMessage:
    """
    A single message received on a channel.

    Fields:
        message_id:  UUID4 globally unique identifier.
        channel:     Which ChannelType this message came from.
        sender_id:   Platform-specific user identifier (e.g. Telegram user_id).
        sender_name: Human-readable display name.
        content:     Text body of the message.
        attachments: List of attachment dicts (url, type, size, etc.).
        timestamp:   ISO 8601 UTC timestamp of receipt.
        thread_id:   Conversation thread identifier (platform-specific).
        reply_to:    message_id of the message being replied to, or "".
        metadata:    Arbitrary platform-specific key/value data.
    """

    message_id:  str
    channel:     ChannelType
    sender_id:   str
    sender_name: str
    content:     str
    attachments: list = field(default_factory=list)
    timestamp:   str  = ""
    thread_id:   str  = ""
    reply_to:    str  = ""
    metadata:    dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ChannelConfig — per-channel configuration
# ---------------------------------------------------------------------------

@dataclass
class ChannelConfig:
    """
    Configuration for a single messaging channel.

    Fields:
        channel_type:           Which ChannelType this config governs.
        enabled:                Whether this channel is active.
        oauth3_scope:           Required OAuth3 scope for inbound messages on this channel.
        webhook_url:            URL that receives inbound webhooks from the platform.
        api_token:              Outbound API token (encrypted at rest in production).
        rate_limit_per_minute:  Max messages processed per minute per sender.
        allowed_senders:        If non-empty, only these sender_ids are accepted.
    """

    channel_type:          ChannelType
    enabled:               bool = False
    oauth3_scope:          str  = ""
    webhook_url:           str  = ""
    api_token:             str  = ""
    rate_limit_per_minute: int  = 30
    allowed_senders:       list = field(default_factory=list)


# ---------------------------------------------------------------------------
# PairedSender — sender ↔ OAuth3 agent pairing record
# ---------------------------------------------------------------------------

@dataclass
class PairedSender:
    """
    A sender paired with a specific OAuth3-scoped agent.

    The pairing binds a platform sender_id to an oauth3_token_id, so that
    every message from that sender is validated against the same token.

    Fields:
        sender_id:        Platform-specific user identifier.
        channel:          Which ChannelType this pairing covers.
        paired_at:        ISO 8601 UTC timestamp of when pairing was created.
        oauth3_token_id:  token_id of the AgencyToken granting this pairing.
        agent_id:         Identifier of the agent that handles messages from this sender.
        message_count:    Number of messages processed under this pairing.
        last_message_at:  ISO 8601 UTC timestamp of the most recent message.
    """

    sender_id:       str
    channel:         ChannelType
    paired_at:       str
    oauth3_token_id: str
    agent_id:        str = ""
    message_count:   int = 0
    last_message_at: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso8601() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(data: dict) -> str:
    """Compute SHA-256 hex digest of a canonical JSON dict."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _pairing_key(sender_id: str, channel: ChannelType) -> str:
    """Return the internal key for a (sender_id, channel) pairing."""
    return f"{channel.value}:{sender_id}"


def _channel_key(channel_type: ChannelType) -> str:
    """Return the internal key for a channel config."""
    return channel_type.value


# ---------------------------------------------------------------------------
# Rate limit tracker (simple in-memory sliding window)
# ---------------------------------------------------------------------------

@dataclass
class _RateBucket:
    """Tracks message timestamps for a single sender within a channel."""
    timestamps: List[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ChannelGateway — OAuth3-governed multi-channel messaging gateway
# ---------------------------------------------------------------------------

class ChannelGateway:
    """
    OAuth3-governed multi-channel messaging gateway.

    Every inbound receive_message() and outbound send_message() call is:
      1. Validated against a registered + enabled channel config.
      2. Checked for a valid sender pairing (for inbound).
      3. Enforced through the OAuth3 four-gate pipeline.
      4. Logged to an append-only audit trail.

    The gateway is stateful but does NOT persist to disk — for production use,
    wrap with a persistence layer.

    Token registry:
        Tokens are stored in-memory via add_token(). The gateway validates
        expiry and revocation from this registry. Pass AgencyToken objects
        directly; file-based token loading is not in scope here.

    Usage:
        gw = ChannelGateway()
        gw.add_token(token)
        gw.register_channel(ChannelConfig(channel_type=ChannelType.TELEGRAM,
                                          enabled=True,
                                          oauth3_scope="channel.telegram.read"))
        ps = gw.pair_sender("user123", ChannelType.TELEGRAM, token.token_id)
        result = gw.receive_message(msg)
    """

    def __init__(self) -> None:
        # Registered channel configs: channel_value → ChannelConfig
        self._channels: Dict[str, ChannelConfig] = {}

        # Paired senders: "<channel_value>:<sender_id>" → PairedSender
        self._paired_senders: Dict[str, PairedSender] = {}

        # Per-channel message handlers: ChannelType → callable(ChannelMessage) → Any
        self._message_handlers: Dict[ChannelType, Callable] = {}

        # Append-only audit log (list of dicts, never mutated after append)
        self._message_log: List[dict] = []

        # Inbox of validated inbound messages
        self._inbox: List[ChannelMessage] = []

        # In-memory token registry: token_id → AgencyToken
        self._tokens: Dict[str, object] = {}

        # Rate limit tracking: "<channel_value>:<sender_id>" → _RateBucket
        self._rate_buckets: Dict[str, _RateBucket] = {}

    # -------------------------------------------------------------------------
    # Token management
    # -------------------------------------------------------------------------

    def add_token(self, token: object) -> None:
        """
        Register an AgencyToken in the gateway's token registry.

        Args:
            token: AgencyToken instance. Must have .token_id attribute.
        """
        self._tokens[token.token_id] = token

    def _get_token(self, token_id: str) -> Optional[object]:
        """Retrieve a token from the registry, or None."""
        return self._tokens.get(token_id)

    def _validate_token_for_scope(self, token_id: str, required_scope: str) -> tuple:
        """
        Run full four-gate OAuth3 enforcement for (token_id, scope).

        Returns:
            (passed: bool, error_code: str, error_detail: str)
        """
        token = self._get_token(token_id)
        if token is None:
            return False, "OAUTH3_TOKEN_NOT_FOUND", f"Token {token_id!r} not in registry"

        try:
            from src.oauth3.enforcement import ScopeGate
        except ImportError:
            from oauth3.enforcement import ScopeGate

        gate = ScopeGate(token=token, required_scopes=[required_scope])
        result = gate.check_all()

        if result.allowed:
            return True, "", ""
        return False, result.error_code or "OAUTH3_BLOCKED", result.error_detail or ""

    # -------------------------------------------------------------------------
    # Channel registration
    # -------------------------------------------------------------------------

    def register_channel(self, config: ChannelConfig) -> bool:
        """
        Register a messaging channel.

        Validates that the oauth3_scope is non-empty (fail-closed).
        Does not check whether the scope exists in the global registry —
        that is enforced at token creation time.

        Args:
            config: ChannelConfig for the channel to register.

        Returns:
            True if registration succeeded, False if oauth3_scope is empty.
        """
        if not config.oauth3_scope:
            return False

        self._channels[_channel_key(config.channel_type)] = config
        return True

    def unregister_channel(self, channel_type: ChannelType) -> bool:
        """
        Unregister a channel.

        Also removes all paired senders for that channel.

        Args:
            channel_type: The channel to remove.

        Returns:
            True if the channel was registered (and now removed), False otherwise.
        """
        key = _channel_key(channel_type)
        if key not in self._channels:
            return False

        del self._channels[key]

        # Remove all pairings for this channel
        stale = [k for k in self._paired_senders if k.startswith(f"{channel_type.value}:")]
        for k in stale:
            del self._paired_senders[k]

        return True

    def get_channel_config(self, channel_type: ChannelType) -> Optional[ChannelConfig]:
        """Return the registered config for a channel, or None."""
        return self._channels.get(_channel_key(channel_type))

    # -------------------------------------------------------------------------
    # Sender pairing
    # -------------------------------------------------------------------------

    def pair_sender(
        self,
        sender_id: str,
        channel: ChannelType,
        oauth3_token_id: str,
        agent_id: str = "",
    ) -> PairedSender:
        """
        Pair an inbound sender with an OAuth3-scoped agent.

        Creates a PairedSender record binding (sender_id, channel) → oauth3_token_id.
        Overwrites any existing pairing for this (sender_id, channel) pair.

        Args:
            sender_id:       Platform-specific sender identifier.
            channel:         ChannelType of the pairing.
            oauth3_token_id: token_id of the AgencyToken granting this pairing.
            agent_id:        Optional agent identifier that handles this sender.

        Returns:
            The newly created PairedSender record.
        """
        ps = PairedSender(
            sender_id=sender_id,
            channel=channel,
            paired_at=_now_iso8601(),
            oauth3_token_id=oauth3_token_id,
            agent_id=agent_id,
            message_count=0,
            last_message_at="",
        )
        self._paired_senders[_pairing_key(sender_id, channel)] = ps
        return ps

    def unpair_sender(self, sender_id: str, channel: ChannelType) -> bool:
        """
        Remove a sender pairing.

        Args:
            sender_id: Platform-specific sender identifier.
            channel:   ChannelType of the pairing to remove.

        Returns:
            True if a pairing existed and was removed, False otherwise.
        """
        key = _pairing_key(sender_id, channel)
        if key not in self._paired_senders:
            return False
        del self._paired_senders[key]
        return True

    def get_paired_senders(self) -> List[PairedSender]:
        """List all paired senders."""
        return list(self._paired_senders.values())

    def _get_pairing(self, sender_id: str, channel: ChannelType) -> Optional[PairedSender]:
        """Return pairing for (sender_id, channel), or None."""
        return self._paired_senders.get(_pairing_key(sender_id, channel))

    # -------------------------------------------------------------------------
    # Rate limiting
    # -------------------------------------------------------------------------

    def _check_rate_limit(self, sender_id: str, channel: ChannelType) -> bool:
        """
        Check if a sender is within the channel's rate limit.

        Uses a 60-second sliding window. Returns True if within limit.
        """
        config = self.get_channel_config(channel)
        if config is None:
            return False

        key = _pairing_key(sender_id, channel)
        bucket = self._rate_buckets.setdefault(key, _RateBucket())

        now = time.monotonic()
        window = 60.0
        # Prune timestamps older than 60 seconds
        bucket.timestamps = [t for t in bucket.timestamps if now - t < window]

        if len(bucket.timestamps) >= config.rate_limit_per_minute:
            return False

        bucket.timestamps.append(now)
        return True

    # -------------------------------------------------------------------------
    # Audit trail
    # -------------------------------------------------------------------------

    def _audit_log(self, event: str, data: dict) -> dict:
        """
        Append an entry to the append-only audit trail.

        Each entry includes a SHA-256 hash of its canonical form for integrity.

        Args:
            event: Event label (e.g. "message_received", "message_blocked").
            data:  Arbitrary key/value context dict.

        Returns:
            The audit entry dict as appended.
        """
        entry = {
            "event": event,
            "timestamp": _now_iso8601(),
            **data,
        }
        entry["integrity_hash"] = _sha256_hex(entry)
        # Append only — never mutate existing entries
        self._message_log.append(entry)
        return entry

    # -------------------------------------------------------------------------
    # Message handler registration
    # -------------------------------------------------------------------------

    def register_handler(self, channel: ChannelType, handler: Callable) -> None:
        """
        Register a message handler for a channel.

        The handler is called with the ChannelMessage when a paired message
        passes all OAuth3 gates. Handler exceptions are caught and logged.

        Args:
            channel: ChannelType to handle.
            handler: Callable(ChannelMessage) → Any
        """
        self._message_handlers[channel] = handler

    # -------------------------------------------------------------------------
    # Receive message (inbound pipeline)
    # -------------------------------------------------------------------------

    def receive_message(self, message: ChannelMessage) -> dict:
        """
        Process an inbound message through the OAuth3 gate.

        Pipeline:
          1. Validate channel is registered and enabled.
          2. Check allowed_senders allowlist (if configured).
          3. Check sender rate limit.
          4. Look up sender pairing.
          5. Validate OAuth3 token (four-gate enforcement).
          6. Append to audit trail (always — even on rejection).
          7. Add to inbox on success.
          8. Route to handler if registered.

        Args:
            message: ChannelMessage received from the platform.

        Returns:
            dict with keys:
              status:          "ok" | "blocked"
              paired:          bool — True if sender was paired
              response_queued: bool — True if handler was called
              evidence:        dict with gate results and token info
              error_code:      str (present on blocked)
              error_detail:    str (present on blocked)
        """
        result: dict = {
            "status": "blocked",
            "paired": False,
            "response_queued": False,
            "evidence": {},
        }

        # Step 1: Channel registered and enabled
        config = self.get_channel_config(message.channel)
        if config is None:
            self._audit_log("message_blocked", {
                "reason": "channel_not_registered",
                "channel": message.channel.value,
                "message_id": message.message_id,
                "sender_id": message.sender_id,
            })
            result["error_code"] = "CHANNEL_NOT_REGISTERED"
            result["error_detail"] = (
                f"Channel {message.channel.value!r} is not registered."
            )
            return result

        if not config.enabled:
            self._audit_log("message_blocked", {
                "reason": "channel_disabled",
                "channel": message.channel.value,
                "message_id": message.message_id,
                "sender_id": message.sender_id,
            })
            result["error_code"] = "CHANNEL_DISABLED"
            result["error_detail"] = (
                f"Channel {message.channel.value!r} is registered but disabled."
            )
            return result

        # Step 2: Allowed senders allowlist
        if config.allowed_senders and message.sender_id not in config.allowed_senders:
            self._audit_log("message_blocked", {
                "reason": "sender_not_in_allowlist",
                "channel": message.channel.value,
                "message_id": message.message_id,
                "sender_id": message.sender_id,
            })
            result["error_code"] = "SENDER_NOT_ALLOWED"
            result["error_detail"] = (
                f"Sender {message.sender_id!r} not in allowed_senders for "
                f"channel {message.channel.value!r}."
            )
            return result

        # Step 3: Rate limit
        if not self._check_rate_limit(message.sender_id, message.channel):
            self._audit_log("message_blocked", {
                "reason": "rate_limit_exceeded",
                "channel": message.channel.value,
                "message_id": message.message_id,
                "sender_id": message.sender_id,
            })
            result["error_code"] = "RATE_LIMIT_EXCEEDED"
            result["error_detail"] = (
                f"Sender {message.sender_id!r} exceeded rate limit of "
                f"{config.rate_limit_per_minute} messages/minute on "
                f"channel {message.channel.value!r}."
            )
            return result

        # Step 4: Sender pairing
        pairing = self._get_pairing(message.sender_id, message.channel)
        if pairing is None:
            self._audit_log("message_received_unpaired", {
                "channel": message.channel.value,
                "message_id": message.message_id,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                "timestamp": message.timestamp or _now_iso8601(),
            })
            # Unpaired messages are logged but not routed
            result["status"] = "blocked"
            result["paired"] = False
            result["error_code"] = "SENDER_NOT_PAIRED"
            result["error_detail"] = (
                f"Sender {message.sender_id!r} on channel "
                f"{message.channel.value!r} has no active pairing."
            )
            return result

        result["paired"] = True

        # Step 5: OAuth3 four-gate enforcement
        passed, error_code, error_detail = self._validate_token_for_scope(
            pairing.oauth3_token_id,
            config.oauth3_scope,
        )

        if not passed:
            self._audit_log("message_blocked", {
                "reason": "oauth3_gate_failed",
                "error_code": error_code,
                "channel": message.channel.value,
                "message_id": message.message_id,
                "sender_id": message.sender_id,
                "oauth3_token_id": pairing.oauth3_token_id,
                "required_scope": config.oauth3_scope,
            })
            result["error_code"] = error_code
            result["error_detail"] = error_detail
            result["evidence"] = {
                "oauth3_token_id": pairing.oauth3_token_id,
                "required_scope": config.oauth3_scope,
                "gate_passed": False,
            }
            return result

        # Step 6: Log to audit trail (success path)
        audit_entry = self._audit_log("message_received", {
            "channel": message.channel.value,
            "message_id": message.message_id,
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "content_length": len(message.content),
            "timestamp": message.timestamp or _now_iso8601(),
            "thread_id": message.thread_id,
            "reply_to": message.reply_to,
            "oauth3_token_id": pairing.oauth3_token_id,
            "required_scope": config.oauth3_scope,
        })

        # Step 7: Add to inbox
        self._inbox.append(message)

        # Update pairing stats
        pairing.message_count += 1
        pairing.last_message_at = _now_iso8601()

        result["status"] = "ok"
        result["evidence"] = {
            "oauth3_token_id": pairing.oauth3_token_id,
            "required_scope": config.oauth3_scope,
            "gate_passed": True,
            "audit_hash": audit_entry.get("integrity_hash", ""),
        }

        # Step 8: Route to handler if registered
        handler = self._message_handlers.get(message.channel)
        if handler is not None:
            try:
                handler(message)
                result["response_queued"] = True
            except Exception as exc:
                self._audit_log("handler_exception", {
                    "channel": message.channel.value,
                    "message_id": message.message_id,
                    "error": str(exc),
                })
                result["handler_error"] = str(exc)

        return result

    # -------------------------------------------------------------------------
    # Send message (outbound pipeline)
    # -------------------------------------------------------------------------

    def send_message(
        self,
        channel: ChannelType,
        recipient_id: str,
        content: str,
        oauth3_token_id: str,
    ) -> dict:
        """
        Send an outbound message through the OAuth3 gate.

        Requires the "send" scope for the target channel (e.g.
        "channel.telegram.send"). The token must be valid, non-expired, and
        non-revoked.

        Args:
            channel:         Target ChannelType.
            recipient_id:    Platform-specific recipient identifier.
            content:         Message text to send.
            oauth3_token_id: token_id of the AgencyToken authorizing this send.

        Returns:
            dict with keys:
              status:       "ok" | "blocked"
              evidence:     dict with gate results
              error_code:   str (present on blocked)
              error_detail: str (present on blocked)
        """
        result: dict = {
            "status": "blocked",
            "evidence": {},
        }

        # Validate channel is registered and enabled
        config = self.get_channel_config(channel)
        if config is None:
            self._audit_log("send_blocked", {
                "reason": "channel_not_registered",
                "channel": channel.value,
                "recipient_id": recipient_id,
                "oauth3_token_id": oauth3_token_id,
            })
            result["error_code"] = "CHANNEL_NOT_REGISTERED"
            result["error_detail"] = f"Channel {channel.value!r} is not registered."
            return result

        if not config.enabled:
            self._audit_log("send_blocked", {
                "reason": "channel_disabled",
                "channel": channel.value,
                "recipient_id": recipient_id,
                "oauth3_token_id": oauth3_token_id,
            })
            result["error_code"] = "CHANNEL_DISABLED"
            result["error_detail"] = f"Channel {channel.value!r} is disabled."
            return result

        # Derive the send scope for this channel
        send_scope = _channel_send_scope(channel)

        # OAuth3 four-gate enforcement for send scope
        passed, error_code, error_detail = self._validate_token_for_scope(
            oauth3_token_id,
            send_scope,
        )

        if not passed:
            self._audit_log("send_blocked", {
                "reason": "oauth3_gate_failed",
                "error_code": error_code,
                "channel": channel.value,
                "recipient_id": recipient_id,
                "oauth3_token_id": oauth3_token_id,
                "required_scope": send_scope,
            })
            result["error_code"] = error_code
            result["error_detail"] = error_detail
            result["evidence"] = {
                "oauth3_token_id": oauth3_token_id,
                "required_scope": send_scope,
                "gate_passed": False,
            }
            return result

        # Log the send to audit trail
        message_id = str(uuid.uuid4())
        audit_entry = self._audit_log("message_sent", {
            "channel": channel.value,
            "message_id": message_id,
            "recipient_id": recipient_id,
            "content_length": len(content),
            "oauth3_token_id": oauth3_token_id,
            "required_scope": send_scope,
            "timestamp": _now_iso8601(),
        })

        result["status"] = "ok"
        result["message_id"] = message_id
        result["evidence"] = {
            "oauth3_token_id": oauth3_token_id,
            "required_scope": send_scope,
            "gate_passed": True,
            "audit_hash": audit_entry.get("integrity_hash", ""),
        }
        return result

    # -------------------------------------------------------------------------
    # Inbox access
    # -------------------------------------------------------------------------

    def get_inbox(
        self,
        channel: Optional[ChannelType] = None,
        limit: int = 50,
    ) -> List[ChannelMessage]:
        """
        Return inbox messages, optionally filtered by channel.

        Args:
            channel: If provided, return only messages from this channel.
            limit:   Maximum number of messages to return (most recent first).

        Returns:
            List of ChannelMessage objects.
        """
        if channel is None:
            messages = list(self._inbox)
        else:
            messages = [m for m in self._inbox if m.channel == channel]

        # Most recent first (last appended)
        return list(reversed(messages))[:limit]

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_channel_stats(self) -> dict:
        """
        Return per-channel statistics.

        Returns a dict keyed by channel value, each containing:
          - registered: bool
          - enabled: bool
          - message_count: int (messages in inbox for this channel)
          - paired_sender_count: int
          - last_activity: str (ISO 8601 of most recent inbox message, or "")
        """
        stats: dict = {}

        for channel_val, config in self._channels.items():
            channel_messages = [
                m for m in self._inbox if m.channel.value == channel_val
            ]
            paired = [
                ps for ps in self._paired_senders.values()
                if ps.channel.value == channel_val
            ]

            # Find most recent activity
            last_activity = ""
            active_senders_with_ts = [
                ps.last_message_at for ps in paired if ps.last_message_at
            ]
            if active_senders_with_ts:
                last_activity = max(active_senders_with_ts)

            stats[channel_val] = {
                "registered": True,
                "enabled": config.enabled,
                "message_count": len(channel_messages),
                "paired_sender_count": len(paired),
                "last_activity": last_activity,
            }

        return stats

    # -------------------------------------------------------------------------
    # Audit trail access
    # -------------------------------------------------------------------------

    def get_audit_log(self) -> List[dict]:
        """
        Return a copy of the append-only audit log.

        Returns a new list — callers cannot mutate the internal log.
        """
        return list(self._message_log)


# ---------------------------------------------------------------------------
# Internal: derive send scope from channel type
# ---------------------------------------------------------------------------

_CHANNEL_SEND_SCOPES: Dict[ChannelType, str] = {
    ChannelType.TELEGRAM:  "channel.telegram.send",
    ChannelType.DISCORD:   "channel.discord.send",
    ChannelType.SLACK:     "channel.slack.send",
    ChannelType.WHATSAPP:  "channel.whatsapp.send",
    ChannelType.SIGNAL:    "channel.signal.send",
    ChannelType.MATRIX:    "channel.matrix.send",
    ChannelType.IRC:       "channel.irc.send",
    ChannelType.EMAIL:     "channel.email.send",
    ChannelType.SMS:       "channel.sms.send",
    ChannelType.WEB_CHAT:  "channel.web-chat.send",
}

_CHANNEL_READ_SCOPES: Dict[ChannelType, str] = {
    ChannelType.TELEGRAM:  "channel.telegram.read",
    ChannelType.DISCORD:   "channel.discord.read",
    ChannelType.SLACK:     "channel.slack.read",
    ChannelType.WHATSAPP:  "channel.whatsapp.read",
    ChannelType.SIGNAL:    "channel.signal.read",
    ChannelType.MATRIX:    "channel.matrix.read",
    ChannelType.IRC:       "channel.irc.read",
    ChannelType.EMAIL:     "channel.email.read",
    ChannelType.SMS:       "channel.sms.read",
    ChannelType.WEB_CHAT:  "channel.web-chat.read",
}


def _channel_send_scope(channel: ChannelType) -> str:
    """Return the OAuth3 send scope for a channel type."""
    return _CHANNEL_SEND_SCOPES.get(channel, f"channel.{channel.value}.send")


def _channel_read_scope(channel: ChannelType) -> str:
    """Return the OAuth3 read scope for a channel type."""
    return _CHANNEL_READ_SCOPES.get(channel, f"channel.{channel.value}.read")
