"""
Reverse tunnel management.

Provides two complementary implementations:

  TunnelServer (STUB):
    OAuth3-gated interface for starting/stopping a bore/frp reverse tunnel.
    scope: machine.tunnel.manage (HIGH RISK — step-up required)
    Actual tunnel creation returns a mock public URL.
    Real implementation will use `bore` or `frp` in a later phase.

  TunnelClient (WebSocket):
    Client-side persistent WebSocket reverse tunnel to tunnel.solaceagi.com.
    scope: machine.tunnel.open (HIGH RISK — step-up required)
    Lifecycle: INIT → STEP_UP_CHECK → OAUTH3_GATE → CONNECT → ACTIVE →
               HEARTBEAT_LOOP → DISCONNECT
    Security:
      - TLS required (wss:// only)
      - Zero tunnel traffic without valid OAuth3 token
      - Token pinned to user_id — cross-user relay impossible
      - Bandwidth limits enforced in real-time (100 MB free tier)
      - Evidence bundle emitted on every disconnect path

Rung: 65537 (security-critical — persistent network exposure)
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from src.oauth3.token import AgencyToken
from src.oauth3.enforcement import ScopeGate
from src.machine.scopes import SCOPE_TUNNEL_MANAGE, SCOPE_TUNNEL_OPEN

logger = logging.getLogger(__name__)

try:
    from websockets.exceptions import WebSocketException  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    class WebSocketException(Exception):
        """Fallback when websockets is unavailable."""


try:
    from httpx import HTTPError  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    class HTTPError(Exception):
        """Fallback when httpx is unavailable."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_REMOTE_HOST: str = "tunnel.solaceagi.com"
AUDIT_LOG_PATH: Path = Path.home() / ".stillwater" / "machine_audit.jsonl"


# ---------------------------------------------------------------------------
# TunnelConfig dataclass
# ---------------------------------------------------------------------------

@dataclass
class TunnelConfig:
    """
    Configuration for a reverse tunnel session.

    Fields:
        local_port:   Local TCP port to expose (e.g. 8080).
        remote_host:  Remote host to tunnel through (default: tunnel.solaceagi.com).
        tunnel_id:    UUID4 identifier for this tunnel session (auto-generated).
        auth_token:   Bearer token for authenticating with the remote host.
    """
    local_port: int
    auth_token: str
    remote_host: str = DEFAULT_REMOTE_HOST
    tunnel_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "local_port": self.local_port,
            "remote_host": self.remote_host,
            "tunnel_id": self.tunnel_id,
            "auth_token": "***",  # never log actual auth token
        }


# ---------------------------------------------------------------------------
# TunnelServer class
# ---------------------------------------------------------------------------

class TunnelServer:
    """
    OAuth3-gated reverse tunnel manager.

    All operations require machine.tunnel.manage scope (HIGH RISK).

    Usage:
        server = TunnelServer()
        result = server.start(config, token)
        # ... later ...
        server.stop(token)

    State is kept in-memory only (not persisted across restarts).
    """

    def __init__(self) -> None:
        self._running: bool = False
        self._config: Optional[TunnelConfig] = None
        self._start_time: Optional[float] = None
        self._bytes_transferred: int = 0
        self._public_url: Optional[str] = None

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _now_iso(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _audit(self, action: str, token: AgencyToken, extra: Optional[dict] = None) -> None:
        """Emit structured audit record. Fails silently."""
        try:
            AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": self._now_iso(),
                "action": action,
                "token_id": token.token_id,
                "subject": token.subject,
                "tunnel_id": self._config.tunnel_id if self._config else None,
                **(extra or {}),
            }
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("tunnel audit write failed: %s", exc)

    def _gate_check(self, token: AgencyToken) -> Optional[dict]:
        """Run full four-gate scope check. Returns None if allowed."""
        gate = ScopeGate(token=token, required_scopes=[SCOPE_TUNNEL_MANAGE])
        result = gate.check_all()
        if not result.allowed:
            return {
                "error": result.error_code,
                "detail": result.error_detail,
                "blocking_gate": result.blocking_gate,
                "missing_scopes": result.missing_scopes,
            }
        return None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def start(self, config: TunnelConfig, token: AgencyToken) -> dict:
        """
        Start a reverse tunnel from local_port to the remote host.

        Required scope: machine.tunnel.manage (HIGH RISK — step-up required)

        STUB: Returns a mock public URL. Real implementation will use
              bore (https://github.com/ekzhang/bore) or frp.

        Args:
            config: TunnelConfig with local_port, remote_host, auth_token.
            token:  AgencyToken with machine.tunnel.manage scope.

        Returns:
            {
              "started": true,
              "tunnel_id": str (UUID4),
              "local_port": int,
              "remote_host": str,
              "public_url": str,
              "started_at": str (ISO 8601),
              "stub": true,   # flag indicating this is a stub implementation
            }
            or {"error": ..., "detail": ...} on failure.
        """
        err = self._gate_check(token)
        if err:
            return err

        if self._running:
            return {
                "error": "TUNNEL_ALREADY_RUNNING",
                "detail": (
                    f"A tunnel is already active (id={self._config.tunnel_id}). "
                    "Call stop() first."
                ),
            }

        # Validate local_port range
        if not (1 <= config.local_port <= 65535):
            return {
                "error": "INVALID_PORT",
                "detail": f"local_port must be 1-65535, got {config.local_port}",
            }

        # STUB: generate a plausible mock public URL
        short_id = config.tunnel_id[:8]
        mock_url = (
            f"https://{short_id}.{config.remote_host}"
            f":{config.local_port}"
        )

        self._config = config
        self._running = True
        self._start_time = time.monotonic()
        self._bytes_transferred = 0
        self._public_url = mock_url

        started_at = self._now_iso()
        self._audit("tunnel_start", token, {
            "local_port": config.local_port,
            "remote_host": config.remote_host,
            "public_url": mock_url,
        })

        return {
            "started": True,
            "tunnel_id": config.tunnel_id,
            "local_port": config.local_port,
            "remote_host": config.remote_host,
            "public_url": mock_url,
            "started_at": started_at,
            "stub": True,
        }

    def stop(self, token: AgencyToken) -> bool:
        """
        Stop the active tunnel.

        Required scope: machine.tunnel.manage

        Args:
            token: AgencyToken with machine.tunnel.manage scope.

        Returns:
            True if tunnel was stopped. False if no tunnel was running.
            Returns {"error": ...} dict if scope check fails.
        """
        err = self._gate_check(token)
        if err:
            return err  # type: ignore[return-value]

        if not self._running:
            return False

        self._audit("tunnel_stop", token, {
            "uptime_seconds": int(time.monotonic() - (self._start_time or 0)),
            "bytes_transferred": self._bytes_transferred,
        })

        self._running = False
        self._config = None
        self._start_time = None
        self._bytes_transferred = 0
        self._public_url = None
        return True

    def status(self, token: AgencyToken) -> dict:
        """
        Return current tunnel status.

        Required scope: machine.tunnel.manage

        Returns:
            {
              "running": bool,
              "tunnel_id": str | null,
              "local_port": int | null,
              "remote_url": str | null,
              "uptime_seconds": int,
              "bytes_transferred": int,
            }
            or {"error": ..., "detail": ...} on scope failure.
        """
        err = self._gate_check(token)
        if err:
            return err

        uptime = 0
        if self._running and self._start_time is not None:
            uptime = int(time.monotonic() - self._start_time)

        return {
            "running": self._running,
            "tunnel_id": self._config.tunnel_id if self._config else None,
            "local_port": self._config.local_port if self._config else None,
            "remote_url": self._public_url,
            "uptime_seconds": uptime,
            "bytes_transferred": self._bytes_transferred,
        }

    def get_public_url(self, token: AgencyToken) -> str:
        """
        Return the public URL for the active tunnel.

        Required scope: machine.tunnel.manage

        Returns:
            Public URL string (e.g. 'https://abc123.tunnel.solaceagi.com:8080'),
            or empty string if no tunnel is running.
        """
        err = self._gate_check(token)
        if err:
            return ""

        if not self._running or not self._public_url:
            return ""

        return self._public_url


# ---------------------------------------------------------------------------
# Module-level singleton (convenience for simple use cases)
# ---------------------------------------------------------------------------

_default_server: Optional[TunnelServer] = None


def _get_default_server() -> TunnelServer:
    global _default_server
    if _default_server is None:
        _default_server = TunnelServer()
    return _default_server


# ===========================================================================
# TunnelClient — WebSocket-based persistent reverse tunnel (rung 65537)
# ===========================================================================

# Bandwidth constants (free tier = 100 MB)
BANDWIDTH_FREE_TIER_BYTES: int = 100 * 1024 * 1024        # 100 MB in bytes
BANDWIDTH_SOFT_LIMIT_RATIO: float = 0.9                   # 90 % → warning
HEARTBEAT_INTERVAL_SECONDS: int = 30
HEARTBEAT_TIMEOUT_SECONDS: int = 10
RECONNECT_MAX_RETRIES: int = 10
RECONNECT_BACKOFF_BASE_SECONDS: int = 1
RECONNECT_BACKOFF_MAX_SECONDS: int = 60

# Disconnect reason constants
REASON_USER_INITIATED = "user_initiated"
REASON_TIMEOUT = "timeout"
REASON_SERVER_CLOSED = "server_closed"
REASON_ERROR = "error"
REASON_BANDWIDTH_EXCEEDED = "bandwidth_exceeded"
REASON_TOKEN_REVOKED = "token_revoked"


@dataclass
class TunnelSession:
    """
    Immutable-ish record for a single WebSocket tunnel session.

    All bandwidth counters are integer bytes — NEVER float.
    All timestamps are ISO 8601 UTC strings.
    """

    tunnel_id: str                # uuid4
    user_id: str
    token_id: str
    started_at: str               # ISO8601 UTC
    bytes_in: int = 0             # integer only — NEVER float
    bytes_out: int = 0            # integer only — NEVER float
    connected: bool = False
    last_heartbeat: str = ""      # ISO8601 UTC or ""
    requests_proxied: int = 0
    disconnect_reason: str = ""   # user_initiated|timeout|server_closed|error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tunnel_id": self.tunnel_id,
            "user_id": self.user_id,
            "token_id": self.token_id,
            "started_at": self.started_at,
            "bytes_in": int(self.bytes_in),
            "bytes_out": int(self.bytes_out),
            "connected": self.connected,
            "last_heartbeat": self.last_heartbeat,
            "requests_proxied": int(self.requests_proxied),
            "disconnect_reason": self.disconnect_reason,
        }


class TunnelClient:
    """
    OAuth3-gated WebSocket reverse tunnel client.

    Connects to wss://tunnel.solaceagi.com and keeps a persistent session
    open so the server can relay inbound HTTP requests to the local machine.

    Security contract (non-negotiable):
      1. ZERO tunnel traffic without valid OAuth3 token (machine.tunnel.open)
      2. TLS required — wss:// only; ws:// raises ValueError at __init__
      3. Token pinned to user_id — cross-user relay impossible
      4. Bandwidth limits enforced in real-time (not post-hoc)
      5. Tunnel closes on token revocation (checked every heartbeat)
      6. Evidence bundle emitted on EVERY disconnect path

    State machine:
      INIT → STEP_UP_CHECK → OAUTH3_GATE → CONNECT → ACTIVE →
      HEARTBEAT_LOOP → DISCONNECT

    Usage (async):
        client = TunnelClient("wss://tunnel.solaceagi.com", token_dict, "user@x")
        ok = await client.connect()
        # ... later ...
        evidence = await client.disconnect()

    Rung: 65537 (security-critical)
    """

    # Scope required for the WebSocket tunnel
    REQUIRED_SCOPE: str = SCOPE_TUNNEL_OPEN

    def __init__(
        self,
        tunnel_url: str,
        oauth3_token: Dict[str, Any],
        user_id: str,
        bandwidth_limit_bytes: int = BANDWIDTH_FREE_TIER_BYTES,
    ) -> None:
        """
        Initialise TunnelClient with security validation.

        Args:
            tunnel_url:           WebSocket URL (must be wss://).
            oauth3_token:         Token dict as returned by AgencyToken.to_dict().
            user_id:              User identifier — must match token subject.
            bandwidth_limit_bytes: Hard bandwidth cap in bytes (default 100 MB).

        Raises:
            ValueError: If tunnel_url uses ws:// (TLS required).
            ValueError: If token lacks machine.tunnel.open scope.
            ValueError: If token step_up_required_for contains tunnel scope
                        (i.e. step-up has NOT been confirmed yet).
            ValueError: If user_id does not match token subject.
        """
        # Gate 1 — TLS enforcement (fail-closed)
        if tunnel_url.startswith("ws://"):
            raise ValueError(
                "TLS required: tunnel_url must use wss:// — plain ws:// is rejected. "
                f"Got: {tunnel_url!r}"
            )
        if not tunnel_url.startswith("wss://"):
            raise ValueError(
                f"tunnel_url must start with wss://, got: {tunnel_url!r}"
            )

        # Gate 2 — Scope check
        scopes = oauth3_token.get("scopes", [])
        if self.REQUIRED_SCOPE not in scopes:
            raise ValueError(
                f"OAuth3 token missing required scope: {self.REQUIRED_SCOPE!r}. "
                f"Token scopes: {scopes}"
            )

        # Gate 3 — Step-up confirmation required for high-risk scope
        step_up_required_for = oauth3_token.get("step_up_required_for", [])
        if self.REQUIRED_SCOPE in step_up_required_for:
            raise ValueError(
                f"Step-up consent required before opening tunnel. "
                f"Scope {self.REQUIRED_SCOPE!r} is in step_up_required_for. "
                "Complete step-up flow before calling TunnelClient()."
            )

        # Gate 4 — user_id binding
        token_subject = oauth3_token.get("subject") or oauth3_token.get("user_id", "")
        if token_subject and user_id and token_subject != user_id:
            raise ValueError(
                f"user_id mismatch: token subject is {token_subject!r} "
                f"but caller passed user_id={user_id!r}. "
                "Cross-user relay is forbidden."
            )

        self._tunnel_url: str = tunnel_url
        self._oauth3_token: Dict[str, Any] = oauth3_token
        self._user_id: str = user_id
        self._token_id: str = oauth3_token.get("token_id", "")
        self._bandwidth_limit_bytes: int = int(bandwidth_limit_bytes)

        # Session state
        self._session: TunnelSession = TunnelSession(
            tunnel_id=str(uuid.uuid4()),
            user_id=user_id,
            token_id=self._token_id,
            started_at=self._now_iso(),
        )
        self._ws: Any = None                   # websockets ClientConnection
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_attempt: int = 0
        self._state: str = "INIT"

    # -------------------------------------------------------------------------
    # Public async API
    # -------------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Open the WebSocket tunnel session with OAuth3 token in headers.

        State transition: INIT → STEP_UP_CHECK → OAUTH3_GATE → CONNECT → ACTIVE

        Returns:
            True if connected successfully, False on any failure.
        """
        self._state = "STEP_UP_CHECK"

        # Re-validate token is not revoked before connecting
        if self._oauth3_token.get("revoked", False):
            logger.warning("TunnelClient.connect: token is revoked — aborting")
            self._state = "OAUTH3_GATE"
            return False

        self._state = "OAUTH3_GATE"

        try:
            import websockets  # type: ignore
            from websockets.asyncio.client import connect as ws_connect  # type: ignore
        except ImportError:
            logger.error("websockets library not installed")
            return False

        headers = {
            "Authorization": f"Bearer {self._token_id}",
            "X-OAuth3-Token-Id": self._token_id,
            "X-OAuth3-User-Id": self._user_id,
            "X-OAuth3-Scope": self.REQUIRED_SCOPE,
        }

        self._state = "CONNECT"
        try:
            self._ws = await ws_connect(self._tunnel_url, additional_headers=headers)
            self._session.connected = True
            self._reconnect_attempt = 0
            self._state = "ACTIVE"

            # Start heartbeat loop as background task
            self._heartbeat_task = asyncio.get_event_loop().create_task(
                self._heartbeat_loop()
            )
            logger.info(
                "TunnelClient connected: tunnel_id=%s user_id=%s",
                self._session.tunnel_id,
                self._user_id,
            )
            return True

        except (OSError, WebSocketException) as exc:
            logger.warning("TunnelClient.connect failed: %s", exc)
            self._state = "INIT"
            self._session.connected = False
            return False

    async def disconnect(self, reason: str = REASON_USER_INITIATED) -> Dict[str, Any]:
        """
        Clean shutdown of the tunnel session.

        State transition: ACTIVE → DISCONNECT

        Args:
            reason: One of user_initiated|timeout|server_closed|error.

        Returns:
            Evidence bundle dict (always — even on error paths).
        """
        self._state = "DISCONNECT"
        self._session.disconnect_reason = reason
        self._session.connected = False

        # Cancel heartbeat task
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                logger.debug("TunnelClient heartbeat task cancelled during disconnect")
        self._heartbeat_task = None

        # Close WebSocket gracefully
        if self._ws is not None:
            try:
                await self._ws.close()
            except (OSError, RuntimeError, WebSocketException) as exc:
                logger.debug("TunnelClient.disconnect ws.close() error: %s", exc)
            self._ws = None

        evidence = self._build_evidence()
        logger.info(
            "TunnelClient disconnected: tunnel_id=%s reason=%s",
            self._session.tunnel_id,
            reason,
        )
        return evidence

    # -------------------------------------------------------------------------
    # Internal async helpers
    # -------------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """
        Send a WebSocket ping every 30 s. Disconnect if no pong within 10 s.

        State machine sub-loop: ACTIVE → HEARTBEAT_LOOP (cycling).
        """
        self._state = "HEARTBEAT_LOOP"
        try:
            while self._session.connected and self._ws is not None:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

                if not self._session.connected or self._ws is None:
                    break

                # Check token revocation on every heartbeat
                if self._oauth3_token.get("revoked", False):
                    logger.warning("TunnelClient: token revoked — closing tunnel")
                    await self.disconnect(reason=REASON_TOKEN_REVOKED)
                    return

                # Send ping and wait for pong with timeout
                try:
                    pong_waiter = await self._ws.ping()
                    await asyncio.wait_for(pong_waiter, timeout=HEARTBEAT_TIMEOUT_SECONDS)
                    self._session.last_heartbeat = self._now_iso()
                    logger.debug(
                        "TunnelClient heartbeat OK: tunnel_id=%s",
                        self._session.tunnel_id,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "TunnelClient: pong timeout after %ds — disconnecting",
                        HEARTBEAT_TIMEOUT_SECONDS,
                    )
                    await self.disconnect(reason=REASON_TIMEOUT)
                    return
                except (OSError, RuntimeError, WebSocketException) as exc:
                    logger.warning("TunnelClient heartbeat error: %s", exc)
                    await self.disconnect(reason=REASON_ERROR)
                    return

        except asyncio.CancelledError:
            logger.debug("TunnelClient heartbeat loop cancelled")

    async def _handle_relay(self, ws_message: Any) -> None:
        """
        Decode a proxied HTTP request from the server, forward to local API,
        return the response back over the WebSocket.

        Security: reject any message whose user_id does not match this client's
        user_id (cross-user relay is impossible).

        Args:
            ws_message: Raw WebSocket message (str or bytes).
        """
        # Parse message envelope
        try:
            if isinstance(ws_message, bytes):
                payload = json.loads(ws_message.decode("utf-8"))
            else:
                payload = json.loads(ws_message)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as exc:
            logger.debug("TunnelClient._handle_relay: invalid message format — ignored: %s", exc)
            return

        # Cross-user relay guard
        msg_user_id = payload.get("user_id", "")
        if msg_user_id and msg_user_id != self._user_id:
            logger.warning(
                "TunnelClient._handle_relay: CROSS_USER_REJECT — "
                "message user_id=%r, client user_id=%r",
                msg_user_id,
                self._user_id,
            )
            return

        # Extract HTTP request fields
        method = payload.get("method", "GET")
        path = payload.get("path", "/")
        headers = payload.get("headers", {})
        body = payload.get("body", "")
        request_id = payload.get("request_id", "")

        # Track inbound bandwidth
        raw_bytes = len(ws_message) if isinstance(ws_message, (str, bytes)) else 0
        self._track_bandwidth("in", raw_bytes)

        # Check bandwidth before forwarding
        if not self._check_bandwidth_limit():
            logger.warning("TunnelClient: bandwidth limit exceeded — closing tunnel")
            await self.disconnect(reason=REASON_BANDWIDTH_EXCEEDED)
            return

        # Forward to local API via httpx
        response_payload: Dict[str, Any]
        try:
            import httpx  # type: ignore
            async with httpx.AsyncClient() as http:
                local_url = f"http://localhost:8888{path}"
                req = http.build_request(method, local_url, headers=headers, content=body)
                resp = await http.send(req)
                response_payload = {
                    "request_id": request_id,
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": resp.text,
                }
        except (HTTPError, OSError, RuntimeError, ValueError) as exc:
            logger.warning("TunnelClient._handle_relay: local HTTP error: %s", exc)
            response_payload = {
                "request_id": request_id,
                "status_code": 502,
                "headers": {},
                "body": f"Local API error: {exc}",
            }

        # Send response back to server
        if self._ws is not None:
            try:
                response_bytes = json.dumps(response_payload).encode("utf-8")
                self._track_bandwidth("out", len(response_bytes))
                await self._ws.send(response_bytes)
                self._session.requests_proxied += 1
            except (OSError, RuntimeError, ValueError, WebSocketException) as exc:
                logger.warning("TunnelClient._handle_relay: send error: %s", exc)

    async def _auto_reconnect(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.

        Backoff schedule: 1, 2, 4, 8, 16, 32, 60, 60, ... seconds.
        Max retries: RECONNECT_MAX_RETRIES (10).

        Returns:
            True if reconnect succeeded, False if max retries exhausted.
        """
        while self._reconnect_attempt < RECONNECT_MAX_RETRIES:
            delay = min(
                RECONNECT_BACKOFF_BASE_SECONDS * (2 ** self._reconnect_attempt),
                RECONNECT_BACKOFF_MAX_SECONDS,
            )
            self._reconnect_attempt += 1
            logger.info(
                "TunnelClient auto-reconnect attempt %d/%d in %ds",
                self._reconnect_attempt,
                RECONNECT_MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)

            success = await self.connect()
            if success:
                self._reconnect_attempt = 0
                logger.info("TunnelClient auto-reconnect succeeded")
                return True

        logger.error(
            "TunnelClient auto-reconnect exhausted after %d attempts",
            RECONNECT_MAX_RETRIES,
        )
        return False

    # -------------------------------------------------------------------------
    # Bandwidth tracking (integer arithmetic only — NEVER float)
    # -------------------------------------------------------------------------

    def _track_bandwidth(self, direction: str, num_bytes: int) -> None:
        """
        Update bytes_in or bytes_out counter with integer arithmetic.

        Args:
            direction: "in" for inbound bytes, "out" for outbound bytes.
            num_bytes: Number of bytes to add (must be non-negative integer).
        """
        num_bytes = int(num_bytes)  # guard: ensure integer, never float
        if direction == "in":
            self._session.bytes_in += num_bytes
        elif direction == "out":
            self._session.bytes_out += num_bytes

    def _check_bandwidth_limit(self) -> bool:
        """
        Return False if total bandwidth has exceeded the hard limit.

        Soft limit (90%) logs a warning but does not disconnect.
        Hard limit (100%) triggers disconnect.

        Returns:
            True if within limit, False if hard limit exceeded.
        """
        total = self._session.bytes_in + self._session.bytes_out
        soft_limit = int(self._bandwidth_limit_bytes * BANDWIDTH_SOFT_LIMIT_RATIO)

        if total >= self._bandwidth_limit_bytes:
            logger.warning(
                "TunnelClient: HARD bandwidth limit reached: %d / %d bytes",
                total,
                self._bandwidth_limit_bytes,
            )
            return False

        if total >= soft_limit:
            logger.warning(
                "TunnelClient: SOFT bandwidth warning: %d / %d bytes (90%%)",
                total,
                self._bandwidth_limit_bytes,
            )

        return True

    # -------------------------------------------------------------------------
    # Evidence bundle
    # -------------------------------------------------------------------------

    def _build_evidence(self) -> Dict[str, Any]:
        """
        Build a complete evidence bundle for this tunnel session.

        Evidence is emitted on EVERY disconnect path (clean or error).

        Returns:
            Dict with all session fields, bandwidth as integers, timestamps as ISO8601.
        """
        return {
            "evidence_version": "1.0",
            "rung": 65537,
            "tunnel_id": self._session.tunnel_id,
            "user_id": self._session.user_id,
            "token_id": self._session.token_id,
            "started_at": self._session.started_at,
            "ended_at": self._now_iso(),
            "bytes_in": int(self._session.bytes_in),
            "bytes_out": int(self._session.bytes_out),
            "total_bytes": int(self._session.bytes_in + self._session.bytes_out),
            "requests_proxied": int(self._session.requests_proxied),
            "disconnect_reason": self._session.disconnect_reason,
            "connected": self._session.connected,
            "last_heartbeat": self._session.last_heartbeat,
            "bandwidth_limit_bytes": int(self._bandwidth_limit_bytes),
            "scope_used": self.REQUIRED_SCOPE,
        }

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        """Return current UTC time as ISO 8601 string."""
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    # -------------------------------------------------------------------------
    # Read-only session properties
    # -------------------------------------------------------------------------

    @property
    def session(self) -> TunnelSession:
        """Return the current session record (read-only reference)."""
        return self._session

    @property
    def state(self) -> str:
        """Return the current state machine state string."""
        return self._state

    @property
    def tunnel_id(self) -> str:
        """Return this session's tunnel UUID."""
        return self._session.tunnel_id
