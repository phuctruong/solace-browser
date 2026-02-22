"""
Multi-Channel Messaging Gateway — Test Suite
~65 tests across 7 test classes.
Rung: 641 (local correctness)

Test classes:
  TestChannelMessage    (8)  — dataclass fields, ISO8601, metadata
  TestChannelConfig     (8)  — defaults, OAuth3 scope, rate limit
  TestChannelGateway    (15) — register/unregister, pair/unpair, receive flow
  TestMessageRouting    (12) — handler calls, unpaired sender, rate limit, exceptions
  TestOAuth3Integration (10) — valid/expired/revoked/scope-mismatch tokens
  TestAuditTrail        (7)  — every event logged, append-only, timestamps, integrity
  TestChannelScopes     (5)  — scope registration, risk levels, pattern validation

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_channels.py -v
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from channels.gateway import (
    ChannelGateway,
    ChannelMessage,
    ChannelConfig,
    ChannelType,
    PairedSender,
    _now_iso8601,
    _sha256_hex,
    _pairing_key,
    _channel_send_scope,
    _channel_read_scope,
)
from channels.scopes import (
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
    SCOPE_EMAIL_READ,
    SCOPE_EMAIL_SEND,
    SCOPE_WEB_CHAT_READ,
    SCOPE_WEB_CHAT_SEND,
)
from oauth3.token import AgencyToken
from oauth3.scopes import SCOPE_REGISTRY


# ---------------------------------------------------------------------------
# Test helpers / fixtures
# ---------------------------------------------------------------------------

def _make_token(
    scopes: List[str],
    expired: bool = False,
    revoked: bool = False,
    ttl_seconds: int = 3600,
) -> AgencyToken:
    """Create an AgencyToken for testing. Registers channel scopes into global registry first."""
    # Register channel scopes into the global SCOPE_REGISTRY before token creation.
    # Calling with no args triggers the global-registry update path.
    register_channel_scopes()
    kwargs = dict(
        issuer="https://test.example.com",
        subject="test-user",
        scopes=scopes,
        intent="test delegation",
    )
    if expired:
        # expires_hours=-1 forces immediate expiry (issued in past)
        kwargs["expires_hours"] = -1
    else:
        kwargs["ttl_seconds"] = ttl_seconds
    token = AgencyToken.create(**kwargs)
    if revoked:
        token = token.revoke()
    return token


def _make_message(
    channel: ChannelType = ChannelType.TELEGRAM,
    sender_id: str = "user_001",
    sender_name: str = "Alice",
    content: str = "Hello, bot!",
    message_id: str = None,
) -> ChannelMessage:
    """Create a test ChannelMessage."""
    return ChannelMessage(
        message_id=message_id or str(uuid.uuid4()),
        channel=channel,
        sender_id=sender_id,
        sender_name=sender_name,
        content=content,
        timestamp=_now_iso8601(),
    )


def _make_gateway_with_telegram() -> tuple:
    """
    Return (gateway, token) with Telegram channel registered and a valid token added.
    """
    gw = ChannelGateway()
    token = _make_token([SCOPE_TELEGRAM_READ, SCOPE_TELEGRAM_SEND])
    gw.add_token(token)
    config = ChannelConfig(
        channel_type=ChannelType.TELEGRAM,
        enabled=True,
        oauth3_scope=SCOPE_TELEGRAM_READ,
    )
    gw.register_channel(config)
    return gw, token


# ---------------------------------------------------------------------------
# TestChannelMessage (8 tests)
# ---------------------------------------------------------------------------

class TestChannelMessage:

    def test_message_id_is_stored(self):
        mid = str(uuid.uuid4())
        msg = ChannelMessage(
            message_id=mid,
            channel=ChannelType.TELEGRAM,
            sender_id="u1",
            sender_name="Alice",
            content="hi",
        )
        assert msg.message_id == mid

    def test_channel_field_is_enum(self):
        msg = _make_message(channel=ChannelType.DISCORD)
        assert msg.channel == ChannelType.DISCORD
        assert isinstance(msg.channel, ChannelType)

    def test_all_required_fields(self):
        msg = _make_message()
        assert msg.sender_id
        assert msg.sender_name
        assert msg.content
        assert msg.channel

    def test_attachments_default_empty_list(self):
        msg = _make_message()
        assert msg.attachments == []
        assert isinstance(msg.attachments, list)

    def test_metadata_default_empty_dict(self):
        msg = _make_message()
        assert msg.metadata == {}
        assert isinstance(msg.metadata, dict)

    def test_timestamp_stored_as_string(self):
        ts = _now_iso8601()
        msg = ChannelMessage(
            message_id=str(uuid.uuid4()),
            channel=ChannelType.SLACK,
            sender_id="u2",
            sender_name="Bob",
            content="hey",
            timestamp=ts,
        )
        assert msg.timestamp == ts

    def test_thread_id_and_reply_to_defaults(self):
        msg = _make_message()
        assert msg.thread_id == ""
        assert msg.reply_to == ""

    def test_thread_id_stored(self):
        msg = ChannelMessage(
            message_id=str(uuid.uuid4()),
            channel=ChannelType.DISCORD,
            sender_id="u3",
            sender_name="Charlie",
            content="reply!",
            thread_id="thread_abc",
            reply_to="msg_xyz",
        )
        assert msg.thread_id == "thread_abc"
        assert msg.reply_to == "msg_xyz"


# ---------------------------------------------------------------------------
# TestChannelConfig (8 tests)
# ---------------------------------------------------------------------------

class TestChannelConfig:

    def test_channel_type_stored(self):
        cfg = ChannelConfig(channel_type=ChannelType.TELEGRAM)
        assert cfg.channel_type == ChannelType.TELEGRAM

    def test_enabled_default_false(self):
        cfg = ChannelConfig(channel_type=ChannelType.DISCORD)
        assert cfg.enabled is False

    def test_oauth3_scope_default_empty(self):
        cfg = ChannelConfig(channel_type=ChannelType.SLACK)
        assert cfg.oauth3_scope == ""

    def test_rate_limit_default_30(self):
        cfg = ChannelConfig(channel_type=ChannelType.EMAIL)
        assert cfg.rate_limit_per_minute == 30

    def test_allowed_senders_default_empty(self):
        cfg = ChannelConfig(channel_type=ChannelType.WHATSAPP)
        assert cfg.allowed_senders == []

    def test_webhook_url_and_api_token_defaults(self):
        cfg = ChannelConfig(channel_type=ChannelType.MATRIX)
        assert cfg.webhook_url == ""
        assert cfg.api_token == ""

    def test_custom_rate_limit(self):
        cfg = ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            rate_limit_per_minute=10,
        )
        assert cfg.rate_limit_per_minute == 10

    def test_full_config(self):
        cfg = ChannelConfig(
            channel_type=ChannelType.SLACK,
            enabled=True,
            oauth3_scope=SCOPE_SLACK_READ,
            webhook_url="https://hooks.example.com/slack",
            api_token="xoxb-secret",
            rate_limit_per_minute=60,
            allowed_senders=["user_a", "user_b"],
        )
        assert cfg.enabled is True
        assert cfg.oauth3_scope == SCOPE_SLACK_READ
        assert "user_a" in cfg.allowed_senders
        assert cfg.rate_limit_per_minute == 60


# ---------------------------------------------------------------------------
# TestChannelGateway (15 tests)
# ---------------------------------------------------------------------------

class TestChannelGateway:

    def test_register_channel_returns_true_with_scope(self):
        gw = ChannelGateway()
        cfg = ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        )
        assert gw.register_channel(cfg) is True

    def test_register_channel_fails_without_scope(self):
        gw = ChannelGateway()
        cfg = ChannelConfig(channel_type=ChannelType.TELEGRAM, oauth3_scope="")
        assert gw.register_channel(cfg) is False

    def test_registered_channel_retrievable(self):
        gw = ChannelGateway()
        cfg = ChannelConfig(
            channel_type=ChannelType.DISCORD,
            enabled=True,
            oauth3_scope=SCOPE_DISCORD_READ,
        )
        gw.register_channel(cfg)
        retrieved = gw.get_channel_config(ChannelType.DISCORD)
        assert retrieved is not None
        assert retrieved.channel_type == ChannelType.DISCORD

    def test_unregister_channel_returns_true(self):
        gw = ChannelGateway()
        cfg = ChannelConfig(
            channel_type=ChannelType.SLACK,
            enabled=True,
            oauth3_scope=SCOPE_SLACK_READ,
        )
        gw.register_channel(cfg)
        assert gw.unregister_channel(ChannelType.SLACK) is True

    def test_unregister_nonexistent_channel_returns_false(self):
        gw = ChannelGateway()
        assert gw.unregister_channel(ChannelType.IRC) is False

    def test_unregister_removes_channel_config(self):
        gw = ChannelGateway()
        cfg = ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        )
        gw.register_channel(cfg)
        gw.unregister_channel(ChannelType.TELEGRAM)
        assert gw.get_channel_config(ChannelType.TELEGRAM) is None

    def test_unregister_removes_pairings(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.unregister_channel(ChannelType.TELEGRAM)
        assert len(gw.get_paired_senders()) == 0

    def test_pair_sender_creates_record(self):
        gw, token = _make_gateway_with_telegram()
        ps = gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        assert isinstance(ps, PairedSender)
        assert ps.sender_id == "u1"
        assert ps.channel == ChannelType.TELEGRAM
        assert ps.oauth3_token_id == token.token_id

    def test_pair_sender_paired_at_is_iso8601(self):
        gw, token = _make_gateway_with_telegram()
        ps = gw.pair_sender("u2", ChannelType.TELEGRAM, token.token_id)
        # Must parse without error
        dt = datetime.fromisoformat(ps.paired_at.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_unpair_sender_returns_true(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        assert gw.unpair_sender("u1", ChannelType.TELEGRAM) is True

    def test_unpair_nonexistent_returns_false(self):
        gw = ChannelGateway()
        assert gw.unpair_sender("nobody", ChannelType.TELEGRAM) is False

    def test_receive_message_unregistered_channel(self):
        gw = ChannelGateway()
        msg = _make_message(channel=ChannelType.TELEGRAM)
        result = gw.receive_message(msg)
        assert result["status"] == "blocked"
        assert result["error_code"] == "CHANNEL_NOT_REGISTERED"

    def test_receive_message_disabled_channel(self):
        gw = ChannelGateway()
        cfg = ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=False,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        )
        gw.register_channel(cfg)
        msg = _make_message(channel=ChannelType.TELEGRAM)
        result = gw.receive_message(msg)
        assert result["status"] == "blocked"
        assert result["error_code"] == "CHANNEL_DISABLED"

    def test_receive_message_unpaired_sender(self):
        gw, token = _make_gateway_with_telegram()
        msg = _make_message(sender_id="unknown_user")
        result = gw.receive_message(msg)
        assert result["status"] == "blocked"
        assert result["paired"] is False
        assert result["error_code"] == "SENDER_NOT_PAIRED"

    def test_receive_message_paired_valid_token(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        msg = _make_message(sender_id="u1")
        result = gw.receive_message(msg)
        assert result["status"] == "ok"
        assert result["paired"] is True


# ---------------------------------------------------------------------------
# TestMessageRouting (12 tests)
# ---------------------------------------------------------------------------

class TestMessageRouting:

    def test_paired_sender_handler_called(self):
        gw, token = _make_gateway_with_telegram()
        called_with = []
        gw.register_handler(ChannelType.TELEGRAM, lambda m: called_with.append(m))
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        msg = _make_message(sender_id="u1")
        result = gw.receive_message(msg)
        assert result["response_queued"] is True
        assert len(called_with) == 1
        assert called_with[0].sender_id == "u1"

    def test_unpaired_sender_handler_not_called(self):
        gw, token = _make_gateway_with_telegram()
        called_with = []
        gw.register_handler(ChannelType.TELEGRAM, lambda m: called_with.append(m))
        msg = _make_message(sender_id="stranger")
        gw.receive_message(msg)
        assert len(called_with) == 0

    def test_no_handler_registered_response_queued_false(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        msg = _make_message(sender_id="u1")
        result = gw.receive_message(msg)
        assert result["status"] == "ok"
        assert result["response_queued"] is False

    def test_handler_exception_logged_not_raised(self):
        gw, token = _make_gateway_with_telegram()
        def bad_handler(m):
            raise RuntimeError("handler crashed")
        gw.register_handler(ChannelType.TELEGRAM, bad_handler)
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        msg = _make_message(sender_id="u1")
        result = gw.receive_message(msg)
        # Should not raise; status is still ok (message was accepted)
        assert result["status"] == "ok"
        assert "handler_error" in result

    def test_handler_exception_audit_logged(self):
        gw, token = _make_gateway_with_telegram()
        def bad_handler(m):
            raise ValueError("boom")
        gw.register_handler(ChannelType.TELEGRAM, bad_handler)
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.receive_message(_make_message(sender_id="u1"))
        events = [e["event"] for e in gw.get_audit_log()]
        assert "handler_exception" in events

    def test_rate_limit_enforced(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_READ, SCOPE_TELEGRAM_SEND])
        gw.add_token(token)
        cfg = ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
            rate_limit_per_minute=3,
        )
        gw.register_channel(cfg)
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)

        # Send 3 messages — all should pass
        results = [gw.receive_message(_make_message(sender_id="u1")) for _ in range(3)]
        for r in results:
            assert r["status"] == "ok", f"Expected ok, got {r}"

        # 4th message should be rate-limited
        r4 = gw.receive_message(_make_message(sender_id="u1"))
        assert r4["status"] == "blocked"
        assert r4["error_code"] == "RATE_LIMIT_EXCEEDED"

    def test_rate_limit_per_sender_independent(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_READ, SCOPE_TELEGRAM_SEND])
        gw.add_token(token)
        cfg = ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
            rate_limit_per_minute=2,
        )
        gw.register_channel(cfg)
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.pair_sender("u2", ChannelType.TELEGRAM, token.token_id)

        # Exhaust u1's limit
        gw.receive_message(_make_message(sender_id="u1"))
        gw.receive_message(_make_message(sender_id="u1"))

        # u2 should still be allowed
        r = gw.receive_message(_make_message(sender_id="u2"))
        assert r["status"] == "ok"

    def test_allowed_senders_allowlist_blocks_unknown(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_READ])
        gw.add_token(token)
        cfg = ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
            allowed_senders=["allowed_user"],
        )
        gw.register_channel(cfg)
        msg = _make_message(sender_id="unknown_user")
        result = gw.receive_message(msg)
        assert result["status"] == "blocked"
        assert result["error_code"] == "SENDER_NOT_ALLOWED"

    def test_allowed_senders_allowlist_permits_known(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_READ])
        gw.add_token(token)
        cfg = ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
            allowed_senders=["allowed_user"],
        )
        gw.register_channel(cfg)
        gw.pair_sender("allowed_user", ChannelType.TELEGRAM, token.token_id)
        msg = _make_message(sender_id="allowed_user")
        result = gw.receive_message(msg)
        assert result["status"] == "ok"

    def test_message_added_to_inbox_on_success(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        msg = _make_message(sender_id="u1")
        gw.receive_message(msg)
        inbox = gw.get_inbox()
        assert len(inbox) == 1
        assert inbox[0].message_id == msg.message_id

    def test_get_inbox_filter_by_channel(self):
        gw, token = _make_gateway_with_telegram()
        # Also register Discord
        discord_token = _make_token([SCOPE_DISCORD_READ])
        gw.add_token(discord_token)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.DISCORD,
            enabled=True,
            oauth3_scope=SCOPE_DISCORD_READ,
        ))
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.pair_sender("u2", ChannelType.DISCORD, discord_token.token_id)

        gw.receive_message(_make_message(channel=ChannelType.TELEGRAM, sender_id="u1"))
        gw.receive_message(_make_message(channel=ChannelType.DISCORD, sender_id="u2"))

        tg_inbox = gw.get_inbox(channel=ChannelType.TELEGRAM)
        assert len(tg_inbox) == 1
        assert tg_inbox[0].channel == ChannelType.TELEGRAM

    def test_get_inbox_limit(self):
        gw, token = _make_gateway_with_telegram()
        # Use a high rate limit so we can send many messages
        gw.unregister_channel(ChannelType.TELEGRAM)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
            rate_limit_per_minute=1000,
        ))
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        for _ in range(10):
            gw.receive_message(_make_message(sender_id="u1"))
        inbox = gw.get_inbox(limit=5)
        assert len(inbox) == 5


# ---------------------------------------------------------------------------
# TestOAuth3Integration (10 tests)
# ---------------------------------------------------------------------------

class TestOAuth3Integration:

    def test_valid_token_allows_message(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        result = gw.receive_message(_make_message(sender_id="u1"))
        assert result["status"] == "ok"
        assert result["evidence"]["gate_passed"] is True

    def test_expired_token_blocks_message(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_READ], expired=True)
        gw.add_token(token)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        ))
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        result = gw.receive_message(_make_message(sender_id="u1"))
        assert result["status"] == "blocked"
        assert result["error_code"] == "OAUTH3_TOKEN_EXPIRED"

    def test_revoked_token_blocks_message(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_READ], revoked=True)
        gw.add_token(token)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        ))
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        result = gw.receive_message(_make_message(sender_id="u1"))
        assert result["status"] == "blocked"
        assert result["error_code"] == "OAUTH3_TOKEN_REVOKED"

    def test_scope_mismatch_blocks_message(self):
        gw = ChannelGateway()
        # Token only has Discord scope, channel requires Telegram scope
        token = _make_token([SCOPE_DISCORD_READ])
        gw.add_token(token)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        ))
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        result = gw.receive_message(_make_message(sender_id="u1"))
        assert result["status"] == "blocked"
        assert result["error_code"] == "OAUTH3_SCOPE_DENIED"

    def test_unknown_token_id_blocks_message(self):
        gw, _ = _make_gateway_with_telegram()
        # Pair with a token_id that doesn't exist in gateway registry
        gw.pair_sender("u1", ChannelType.TELEGRAM, "nonexistent-token-id")
        result = gw.receive_message(_make_message(sender_id="u1"))
        assert result["status"] == "blocked"
        assert result["error_code"] == "OAUTH3_TOKEN_NOT_FOUND"

    def test_valid_token_allows_send(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_SEND])
        gw.add_token(token)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        ))
        result = gw.send_message(
            channel=ChannelType.TELEGRAM,
            recipient_id="recipient_001",
            content="Hello!",
            oauth3_token_id=token.token_id,
        )
        assert result["status"] == "ok"
        assert result["evidence"]["gate_passed"] is True

    def test_expired_token_blocks_send(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_SEND], expired=True)
        gw.add_token(token)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        ))
        result = gw.send_message(
            channel=ChannelType.TELEGRAM,
            recipient_id="r1",
            content="hi",
            oauth3_token_id=token.token_id,
        )
        assert result["status"] == "blocked"
        assert result["error_code"] == "OAUTH3_TOKEN_EXPIRED"

    def test_revoked_token_blocks_send(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_SEND], revoked=True)
        gw.add_token(token)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        ))
        result = gw.send_message(
            channel=ChannelType.TELEGRAM,
            recipient_id="r1",
            content="hi",
            oauth3_token_id=token.token_id,
        )
        assert result["status"] == "blocked"
        assert result["error_code"] == "OAUTH3_TOKEN_REVOKED"

    def test_send_scope_mismatch_blocked(self):
        gw = ChannelGateway()
        # Token has read scope only, but send requires send scope
        token = _make_token([SCOPE_TELEGRAM_READ])
        gw.add_token(token)
        gw.register_channel(ChannelConfig(
            channel_type=ChannelType.TELEGRAM,
            enabled=True,
            oauth3_scope=SCOPE_TELEGRAM_READ,
        ))
        result = gw.send_message(
            channel=ChannelType.TELEGRAM,
            recipient_id="r1",
            content="hi",
            oauth3_token_id=token.token_id,
        )
        assert result["status"] == "blocked"
        assert result["error_code"] == "OAUTH3_SCOPE_DENIED"

    def test_send_to_unregistered_channel_blocked(self):
        gw = ChannelGateway()
        token = _make_token([SCOPE_TELEGRAM_SEND])
        gw.add_token(token)
        result = gw.send_message(
            channel=ChannelType.TELEGRAM,
            recipient_id="r1",
            content="hi",
            oauth3_token_id=token.token_id,
        )
        assert result["status"] == "blocked"
        assert result["error_code"] == "CHANNEL_NOT_REGISTERED"


# ---------------------------------------------------------------------------
# TestAuditTrail (7 tests)
# ---------------------------------------------------------------------------

class TestAuditTrail:

    def test_blocked_message_is_logged(self):
        gw = ChannelGateway()
        msg = _make_message(channel=ChannelType.TELEGRAM)
        gw.receive_message(msg)  # channel not registered → blocked
        log = gw.get_audit_log()
        assert len(log) == 1
        assert log[0]["event"] == "message_blocked"

    def test_successful_message_is_logged(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.receive_message(_make_message(sender_id="u1"))
        events = [e["event"] for e in gw.get_audit_log()]
        assert "message_received" in events

    def test_audit_log_is_append_only(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.receive_message(_make_message(sender_id="u1"))
        log_before = len(gw.get_audit_log())
        gw.receive_message(_make_message(sender_id="u1"))
        log_after = len(gw.get_audit_log())
        assert log_after == log_before + 1

    def test_audit_entries_have_timestamps(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.receive_message(_make_message(sender_id="u1"))
        for entry in gw.get_audit_log():
            assert "timestamp" in entry
            # Must parse as ISO 8601
            dt = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            assert dt.tzinfo is not None

    def test_audit_entries_have_integrity_hash(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.receive_message(_make_message(sender_id="u1"))
        for entry in gw.get_audit_log():
            assert "integrity_hash" in entry
            assert entry["integrity_hash"].startswith("sha256:")

    def test_audit_preserves_sender_info(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.receive_message(_make_message(sender_id="u1", sender_name="Alice"))
        success_entries = [
            e for e in gw.get_audit_log() if e["event"] == "message_received"
        ]
        assert len(success_entries) == 1
        assert success_entries[0]["sender_id"] == "u1"
        assert success_entries[0]["sender_name"] == "Alice"

    def test_get_audit_log_returns_copy(self):
        gw, token = _make_gateway_with_telegram()
        gw.pair_sender("u1", ChannelType.TELEGRAM, token.token_id)
        gw.receive_message(_make_message(sender_id="u1"))
        log_copy = gw.get_audit_log()
        # Mutating the returned copy must not affect the internal log
        log_copy.clear()
        assert len(gw.get_audit_log()) > 0


# ---------------------------------------------------------------------------
# TestChannelScopes (5 tests)
# ---------------------------------------------------------------------------

class TestChannelScopes:

    def test_register_channel_scopes_into_provided_dict(self):
        registry = {}
        updated = register_channel_scopes(registry)
        for scope in CHANNEL_SCOPES:
            assert scope in updated, f"Expected {scope!r} in registry"

    def test_all_channel_scopes_in_channel_scopes_dict(self):
        expected_prefixes = {"channel.telegram.", "channel.discord.", "channel.slack.",
                             "channel.whatsapp.", "channel.email.", "channel.web-chat."}
        covered = set()
        for scope in CHANNEL_SCOPES:
            for prefix in expected_prefixes:
                if scope.startswith(prefix):
                    covered.add(prefix)
                    break
        assert covered == expected_prefixes, f"Missing scopes for: {expected_prefixes - covered}"

    def test_send_scopes_are_medium_or_high_risk(self):
        # All send scopes must be at least medium risk (never low).
        # External platform sends (telegram, discord, etc.) are high.
        # In-product web_chat send is medium (lower blast radius).
        send_scopes = [s for s in CHANNEL_SCOPES if s.endswith(".send")]
        assert len(send_scopes) > 0, "Expected at least one .send scope"
        for scope in send_scopes:
            meta = CHANNEL_SCOPES[scope]
            assert meta["risk_level"] in ("medium", "high"), (
                f"Send scope {scope!r} must be medium or high risk, "
                f"got {meta['risk_level']!r}"
            )
        # External platform sends must be high
        external_send = [s for s in send_scopes if "web-chat" not in s]
        for scope in external_send:
            meta = CHANNEL_SCOPES[scope]
            assert meta["risk_level"] == "high", (
                f"External send scope {scope!r} must be high risk, "
                f"got {meta['risk_level']!r}"
            )

    def test_web_chat_read_is_low_risk(self):
        assert CHANNEL_SCOPES[SCOPE_WEB_CHAT_READ]["risk_level"] == "low"

    def test_scope_names_match_triple_segment_pattern(self):
        import re
        pattern = re.compile(r"^[a-z][a-z0-9_-]+[.][a-z][a-z0-9_-]+[.][a-z][a-z0-9_-]+$")
        for scope in CHANNEL_SCOPES:
            assert pattern.match(scope), (
                f"Scope {scope!r} does not match triple-segment pattern"
            )
