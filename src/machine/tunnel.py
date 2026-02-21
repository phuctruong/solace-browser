"""
Reverse tunnel management — stub implementation.

Provides the OAuth3-gated interface for starting/stopping a reverse tunnel
from the local machine to solaceagi.com (or any configured remote host).

CURRENT STATE: STUB
  The API contract is fully defined and scope-enforced.
  Actual tunnel creation returns a mock public URL.
  Real implementation will use `bore` or `frp` in a later phase.

OAuth3 scope: machine.tunnel.manage (HIGH RISK — step-up required)
  Starting a tunnel exposes the local machine to the internet.
  Users must explicitly grant this scope and complete step-up consent.

Rung: 274177 (network exposure — potentially irreversible session)
"""

from __future__ import annotations

import datetime
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from src.oauth3.token import AgencyToken
from src.oauth3.enforcement import ScopeGate
from src.machine.scopes import SCOPE_TUNNEL_MANAGE


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
        except Exception:
            pass

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
