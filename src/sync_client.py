"""
sync_client.py — Browser-to-Cloud Sync Client

Bridges the browser vertex with solaceagi.com cloud:
  - Push/pull evidence bundles
  - Push/pull browser config
  - Heartbeat (announce browser presence)
  - Push/pull run history

Transport: aiohttp (already a project dependency).
Auth: Bearer token read from ~/.solace/vault/ or SOLACE_API_KEY env var.

NO FALLBACKS. If sync fails, the error propagates with full context.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger("solace-browser.sync")

DEFAULT_API_URL = "https://www.solaceagi.com"
DEFAULT_VAULT_DIR = Path("~/.solace/vault").expanduser()
SYNC_TIMEOUT_SECONDS = 30


class SyncError(RuntimeError):
    """Raised when a sync operation fails."""


@dataclass(frozen=True)
class SyncStatus:
    """Snapshot of current sync state."""
    connected: bool
    last_push_iso: Optional[str]
    last_pull_iso: Optional[str]
    pending_evidence_count: int
    pending_runs_count: int
    api_url: str
    auto_sync_enabled: bool
    evidence_auto_upload: bool


@dataclass
class SyncConfig:
    """Configuration for sync operations."""
    api_url: str = DEFAULT_API_URL
    api_key: str = ""
    auto_sync_interval_seconds: int = 0  # 0 = disabled
    evidence_auto_upload: bool = False  # off by default for privacy
    timeout_seconds: int = SYNC_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls, vault_dir: Optional[Path] = None) -> "SyncConfig":
        """Load sync config from environment and vault.

        Priority:
            1. SOLACE_API_KEY environment variable
            2. ~/.solace/vault/api_key file
        """
        api_url = os.environ.get("SOLACE_API_URL", DEFAULT_API_URL)
        api_key = os.environ.get("SOLACE_API_KEY", "")

        if not api_key:
            vault = vault_dir or DEFAULT_VAULT_DIR
            key_file = vault / "api_key"
            if key_file.exists():
                api_key = key_file.read_text(encoding="utf-8").strip()

        auto_sync = int(os.environ.get("SOLACE_AUTO_SYNC_INTERVAL", "0"))
        evidence_auto = os.environ.get(
            "SOLACE_EVIDENCE_AUTO_UPLOAD", ""
        ).strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            api_url=api_url,
            api_key=api_key,
            auto_sync_interval_seconds=auto_sync,
            evidence_auto_upload=evidence_auto,
        )


class SyncClient:
    """Syncs browser state with solaceagi.com cloud.

    All operations are async. Uses aiohttp.ClientSession internally.
    Session is created lazily on first request and closed explicitly via close().
    """

    def __init__(self, config: SyncConfig) -> None:
        self._config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_push_iso: Optional[str] = None
        self._last_pull_iso: Optional[str] = None

    @property
    def api_url(self) -> str:
        return self._config.api_url.rstrip("/")

    @property
    def connected(self) -> bool:
        return self._session is not None and not self._session.closed

    def get_status(self, *, pending_evidence: int = 0, pending_runs: int = 0) -> SyncStatus:
        """Return current sync status snapshot."""
        return SyncStatus(
            connected=self.connected,
            last_push_iso=self._last_push_iso,
            last_pull_iso=self._last_pull_iso,
            pending_evidence_count=pending_evidence,
            pending_runs_count=pending_runs,
            api_url=self.api_url,
            auto_sync_enabled=self._config.auto_sync_interval_seconds > 0,
            evidence_auto_upload=self._config.evidence_auto_upload,
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Create or return the existing aiohttp session."""
        if self._session is None or self._session.closed:
            headers: Dict[str, str] = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "solace-browser-sync/1.0",
            }
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"
            timeout = aiohttp.ClientTimeout(total=self._config.timeout_seconds)
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Core API methods
    # ------------------------------------------------------------------

    async def push_evidence(self, run_id: str, evidence_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Upload an evidence bundle to cloud.

        POST /api/v1/sync/evidence/upload

        Args:
            run_id: Unique identifier for the run that produced this evidence.
            evidence_bundle: The evidence bundle dict (from EvidencePipeline).

        Returns:
            Server response with upload confirmation.

        Raises:
            SyncError: If the upload fails.
        """
        payload = {
            "run_id": run_id,
            "evidence_bundle": evidence_bundle,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "bundle_hash": hashlib.sha256(
                json.dumps(evidence_bundle, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }
        result = await self._post("/api/v1/sync/evidence/upload", payload)
        self._last_push_iso = datetime.now(timezone.utc).isoformat()
        return result

    async def pull_config(self) -> Dict[str, Any]:
        """Pull latest config from cloud.

        GET /api/v1/sync/config/pull

        Returns:
            Config dict from cloud.

        Raises:
            SyncError: If the pull fails.
        """
        result = await self._get("/api/v1/sync/config/pull")
        self._last_pull_iso = datetime.now(timezone.utc).isoformat()
        return result

    async def push_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Push local browser config to cloud.

        POST /api/v1/sync/config/push

        Args:
            config: Browser configuration dict to push.

        Returns:
            Server response with confirmation.

        Raises:
            SyncError: If the push fails.
        """
        payload = {
            "config": config,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
            "config_hash": hashlib.sha256(
                json.dumps(config, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }
        result = await self._post("/api/v1/sync/config/push", payload)
        self._last_push_iso = datetime.now(timezone.utc).isoformat()
        return result

    async def heartbeat(self, client_version: str) -> Dict[str, Any]:
        """Announce browser presence to cloud.

        POST /api/v1/sync/heartbeat

        Args:
            client_version: Version string of this browser client.

        Returns:
            Server response with acknowledgement and optional directives.

        Raises:
            SyncError: If the heartbeat fails.
        """
        payload = {
            "client_version": client_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": [
                "evidence_upload",
                "config_sync",
                "run_history",
            ],
        }
        return await self._post("/api/v1/sync/heartbeat", payload)

    async def push_run(self, run_result: Dict[str, Any]) -> Dict[str, Any]:
        """Push a completed run to cloud history.

        POST /api/v1/sync/runs/push

        Args:
            run_result: The run result dict (recipe execution output).

        Returns:
            Server response with confirmation.

        Raises:
            SyncError: If the push fails.
        """
        payload = {
            "run_result": run_result,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await self._post("/api/v1/sync/runs/push", payload)
        self._last_push_iso = datetime.now(timezone.utc).isoformat()
        return result

    async def pull_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Pull run history from cloud.

        GET /api/v1/sync/runs/pull?limit={limit}

        Args:
            limit: Maximum number of runs to retrieve.

        Returns:
            List of run result dicts.

        Raises:
            SyncError: If the pull fails.
        """
        result = await self._get("/api/v1/sync/runs/pull", params={"limit": str(limit)})
        self._last_pull_iso = datetime.now(timezone.utc).isoformat()
        runs = result.get("runs")
        if not isinstance(runs, list):
            raise SyncError(
                f"Invalid response from /api/v1/sync/runs/pull: "
                f"expected 'runs' list, got {type(runs).__name__}"
            )
        return runs

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a POST request and return the parsed JSON response."""
        session = await self._ensure_session()
        url = f"{self.api_url}{path}"
        logger.info("POST %s", url)

        try:
            async with session.post(url, json=payload) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise SyncError(
                        f"POST {path} failed: HTTP {resp.status} — {body}"
                    )
                return json.loads(body)
        except aiohttp.ClientError as exc:
            raise SyncError(f"POST {path} transport error: {exc}") from exc

    async def _get(
        self, path: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send a GET request and return the parsed JSON response."""
        session = await self._ensure_session()
        url = f"{self.api_url}{path}"
        logger.info("GET %s", url)

        try:
            async with session.get(url, params=params) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise SyncError(
                        f"GET {path} failed: HTTP {resp.status} — {body}"
                    )
                return json.loads(body)
        except aiohttp.ClientError as exc:
            raise SyncError(f"GET {path} transport error: {exc}") from exc
