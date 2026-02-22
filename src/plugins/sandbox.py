"""
Plugin Sandbox — Isolated, scope-limited execution environment for plugins.

Design principles:
  - Scope-limited: plugin can only call APIs matching its declared scopes.
  - No filesystem access outside plugin data dir.
  - No network access unless scope includes channel.* or machine.tunnel.*.
  - Resource limits: max memory (bytes), max CPU time (seconds), max output size (bytes).
  - Kill switch: sandbox.terminate() immediately stops plugin execution.
  - No exec(), no eval(), no pickle.
  - All sizes and resource limits are int (never float).

Rung: 641
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SandboxViolationError(Exception):
    """Plugin attempted to access a resource outside its declared scopes."""

    def __init__(self, plugin_name: str, violation: str) -> None:
        self.plugin_name = plugin_name
        self.violation = violation
        super().__init__(
            f"Sandbox violation by plugin '{plugin_name}': {violation}"
        )


class SandboxResourceLimitError(Exception):
    """Plugin exceeded a resource limit (memory, CPU, output size)."""

    def __init__(self, plugin_name: str, resource: str, limit: int, actual: int) -> None:
        self.plugin_name = plugin_name
        self.resource = resource
        self.limit = limit
        self.actual = actual
        super().__init__(
            f"Plugin '{plugin_name}' exceeded {resource} limit: "
            f"limit={limit}, actual={actual}."
        )


class SandboxTerminatedError(Exception):
    """Plugin execution was terminated via kill switch."""

    def __init__(self, plugin_name: str) -> None:
        self.plugin_name = plugin_name
        super().__init__(
            f"Plugin '{plugin_name}' execution was terminated by kill switch."
        )


# ---------------------------------------------------------------------------
# Resource limit defaults (all int — never float)
# ---------------------------------------------------------------------------

DEFAULT_MAX_MEMORY_BYTES: int = 64 * 1024 * 1024      # 64 MiB
DEFAULT_MAX_CPU_SECONDS: int = 30                      # 30 seconds
DEFAULT_MAX_OUTPUT_BYTES: int = 1 * 1024 * 1024        # 1 MiB

# Scope prefixes that allow network access
_NETWORK_SCOPE_PREFIXES: Tuple[str, ...] = ("channel.", "machine.tunnel.")

# Scope prefixes that allow broader filesystem access
_FS_SCOPE_PREFIXES: Tuple[str, ...] = ("machine.fs.",)


# ---------------------------------------------------------------------------
# SandboxCall — record of a single API call within the sandbox
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SandboxCall:
    """
    Immutable record of an API call made from within a sandbox.

    Fields:
        timestamp:   ISO8601 UTC timestamp.
        api_name:    Name of the API called (e.g. 'gmail.read.inbox').
        scope_used:  OAuth3 scope the call was authorized under.
        allowed:     True if the call was permitted.
        detail:      Optional detail (e.g. violation reason if denied).
    """

    timestamp: str
    api_name: str
    scope_used: Optional[str]
    allowed: bool
    detail: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return {
            "timestamp": self.timestamp,
            "api_name": self.api_name,
            "scope_used": self.scope_used,
            "allowed": self.allowed,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# PluginSandbox — isolated execution environment
# ---------------------------------------------------------------------------

class PluginSandbox:
    """
    Isolated execution environment for a SolaceBrowser plugin.

    Enforces:
      - Scope-limited API access (fail-closed: unknown scope → deny).
      - No filesystem access outside `data_dir`.
      - No network access unless scope includes channel.* or machine.tunnel.*.
      - Resource limits: max_memory_bytes, max_cpu_seconds, max_output_bytes.
      - Kill switch: terminate() stops execution immediately.

    Usage:
        sandbox = PluginSandbox(
            plugin_name="gmail-sorter",
            granted_scopes=["gmail.read.inbox", "gmail.label.apply"],
            data_dir=Path("/tmp/plugins/gmail-sorter"),
        )
        with sandbox:
            result = sandbox.call_api("gmail.read.inbox", {"limit": 10})
            sandbox.write_output(json.dumps(result).encode())
        audit = sandbox.call_log()

    Thread-safe kill switch via threading.Event.
    """

    def __init__(
        self,
        plugin_name: str,
        granted_scopes: List[str],
        data_dir: Optional[Path] = None,
        max_memory_bytes: int = DEFAULT_MAX_MEMORY_BYTES,
        max_cpu_seconds: int = DEFAULT_MAX_CPU_SECONDS,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    ) -> None:
        """
        Args:
            plugin_name:       Plugin identifier (for error messages and logging).
            granted_scopes:    OAuth3 scopes granted to this plugin instance.
            data_dir:          Plugin's private data directory. If None, no fs access.
            max_memory_bytes:  Memory limit in bytes (int — never float).
            max_cpu_seconds:   CPU time limit in seconds (int — never float).
            max_output_bytes:  Max output buffer size in bytes (int — never float).
        """
        self.plugin_name: str = plugin_name
        self._granted_scopes: List[str] = list(granted_scopes)
        self._data_dir: Optional[Path] = data_dir
        self._max_memory_bytes: int = max_memory_bytes
        self._max_cpu_seconds: int = max_cpu_seconds
        self._max_output_bytes: int = max_output_bytes

        # State
        self._terminated: threading.Event = threading.Event()
        self._call_log: List[SandboxCall] = []
        self._output_buffer: bytearray = bytearray()
        self._start_time: Optional[float] = None
        self._cpu_seconds_used: int = 0
        self._memory_bytes_used: int = 0

    # -------------------------------------------------------------------------
    # Context manager
    # -------------------------------------------------------------------------

    def __enter__(self) -> "PluginSandbox":
        """Start the sandbox session."""
        self._start_time = time.monotonic()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """
        Exit the sandbox session.

        Does NOT suppress exceptions — re-raises any exception from within.
        """
        if self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
            # Record CPU seconds used (int, rounded up)
            self._cpu_seconds_used = int(elapsed) + (1 if elapsed % 1 > 0 else 0)
        return False

    # -------------------------------------------------------------------------
    # Kill switch
    # -------------------------------------------------------------------------

    def terminate(self) -> None:
        """
        Immediately signal termination of this sandbox.

        All subsequent API calls will raise SandboxTerminatedError.
        Thread-safe: sets a threading.Event.
        """
        self._terminated.set()

    def is_terminated(self) -> bool:
        """Return True if the kill switch has been activated."""
        return self._terminated.is_set()

    # -------------------------------------------------------------------------
    # Scope checking
    # -------------------------------------------------------------------------

    def _has_scope(self, scope: str) -> bool:
        """Return True if the scope is in the granted scopes list."""
        return scope in self._granted_scopes

    def _has_network_scope(self) -> bool:
        """Return True if any granted scope allows network access."""
        return any(
            s.startswith(prefix)
            for s in self._granted_scopes
            for prefix in _NETWORK_SCOPE_PREFIXES
        )

    def _has_fs_scope(self) -> bool:
        """Return True if any granted scope allows filesystem access."""
        return any(
            s.startswith(prefix)
            for s in self._granted_scopes
            for prefix in _FS_SCOPE_PREFIXES
        )

    # -------------------------------------------------------------------------
    # Resource limit checks
    # -------------------------------------------------------------------------

    def _check_not_terminated(self) -> None:
        """Raise SandboxTerminatedError if kill switch is set."""
        if self._terminated.is_set():
            raise SandboxTerminatedError(self.plugin_name)

    def _check_cpu_limit(self) -> None:
        """Raise SandboxResourceLimitError if CPU time exceeded."""
        if self._start_time is not None:
            elapsed_int = int(time.monotonic() - self._start_time)
            if elapsed_int > self._max_cpu_seconds:
                raise SandboxResourceLimitError(
                    plugin_name=self.plugin_name,
                    resource="cpu_seconds",
                    limit=self._max_cpu_seconds,
                    actual=elapsed_int,
                )

    def _check_output_limit(self, additional_bytes: int) -> None:
        """Raise SandboxResourceLimitError if output buffer would exceed limit."""
        new_total = len(self._output_buffer) + additional_bytes
        if new_total > self._max_output_bytes:
            raise SandboxResourceLimitError(
                plugin_name=self.plugin_name,
                resource="output_bytes",
                limit=self._max_output_bytes,
                actual=new_total,
            )

    def _check_memory_limit(self, additional_bytes: int) -> None:
        """Raise SandboxResourceLimitError if memory usage would exceed limit."""
        new_total = self._memory_bytes_used + additional_bytes
        if new_total > self._max_memory_bytes:
            raise SandboxResourceLimitError(
                plugin_name=self.plugin_name,
                resource="memory_bytes",
                limit=self._max_memory_bytes,
                actual=new_total,
            )

    # -------------------------------------------------------------------------
    # API call interface
    # -------------------------------------------------------------------------

    def call_api(
        self,
        api_scope: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Attempt to call an API that requires the given scope.

        Checks (in order):
          1. Kill switch — SandboxTerminatedError if set.
          2. CPU limit — SandboxResourceLimitError if exceeded.
          3. Scope gate — SandboxViolationError if scope not granted.

        Args:
            api_scope: OAuth3 scope required for this API call.
            params:    Optional parameters to pass to the API (not executed here;
                       this sandbox records the call only — actual execution is
                       handled by the platform's API layer).

        Returns:
            Dict with {"status": "allowed", "scope": api_scope, ...} on success.

        Raises:
            SandboxTerminatedError:    If kill switch is active.
            SandboxResourceLimitError: If CPU time limit exceeded.
            SandboxViolationError:     If scope not granted.
        """
        self._check_not_terminated()
        self._check_cpu_limit()

        timestamp = _now_iso8601()

        if not self._has_scope(api_scope):
            call = SandboxCall(
                timestamp=timestamp,
                api_name=api_scope,
                scope_used=None,
                allowed=False,
                detail=f"Scope '{api_scope}' not in granted scopes: {self._granted_scopes}",
            )
            self._call_log.append(call)
            raise SandboxViolationError(
                plugin_name=self.plugin_name,
                violation=f"scope '{api_scope}' not granted.",
            )

        call = SandboxCall(
            timestamp=timestamp,
            api_name=api_scope,
            scope_used=api_scope,
            allowed=True,
            detail=None,
        )
        self._call_log.append(call)
        return {"status": "allowed", "scope": api_scope, "params": params or {}}

    def request_network(self, url: str, scope: str) -> Dict[str, Any]:
        """
        Attempt a network request under a specific scope.

        Network is only allowed if:
          - The scope is in granted_scopes AND
          - The scope starts with a network-allowed prefix (channel.* or machine.tunnel.*)

        Args:
            url:   Target URL (not actually fetched; sandbox records the intent).
            scope: OAuth3 scope authorizing the network request.

        Returns:
            Dict with {"status": "allowed", ...} on success.

        Raises:
            SandboxTerminatedError: If kill switch is active.
            SandboxViolationError:  If scope not granted or scope not network-enabled.
        """
        self._check_not_terminated()
        self._check_cpu_limit()

        timestamp = _now_iso8601()

        # Must have the scope AND scope must allow network
        scope_granted = self._has_scope(scope)
        network_allowed = scope_granted and any(
            scope.startswith(prefix) for prefix in _NETWORK_SCOPE_PREFIXES
        )

        if not network_allowed:
            if not scope_granted:
                violation = f"scope '{scope}' not granted."
            else:
                violation = (
                    f"scope '{scope}' does not allow network access. "
                    f"Network requires channel.* or machine.tunnel.* scopes."
                )
            call = SandboxCall(
                timestamp=timestamp,
                api_name=f"network:{url}",
                scope_used=None,
                allowed=False,
                detail=violation,
            )
            self._call_log.append(call)
            raise SandboxViolationError(
                plugin_name=self.plugin_name,
                violation=violation,
            )

        call = SandboxCall(
            timestamp=timestamp,
            api_name=f"network:{url}",
            scope_used=scope,
            allowed=True,
            detail=None,
        )
        self._call_log.append(call)
        return {"status": "allowed", "url": url, "scope": scope}

    def read_file(self, relative_path: str) -> bytes:
        """
        Read a file from the plugin's data directory.

        Only files within `data_dir` are allowed. Path traversal is blocked.

        Args:
            relative_path: Path relative to data_dir (e.g. 'config.json').

        Returns:
            File contents as bytes.

        Raises:
            SandboxTerminatedError: If kill switch is active.
            SandboxViolationError:  If data_dir is None, path escapes data_dir,
                                    or file does not exist.
        """
        self._check_not_terminated()

        if self._data_dir is None:
            raise SandboxViolationError(
                plugin_name=self.plugin_name,
                violation="No data_dir configured — filesystem access is not allowed.",
            )

        # Resolve and validate the path stays within data_dir
        try:
            target = (self._data_dir / relative_path).resolve()
            data_dir_resolved = self._data_dir.resolve()
            if not str(target).startswith(str(data_dir_resolved)):
                raise SandboxViolationError(
                    plugin_name=self.plugin_name,
                    violation=(
                        f"Path traversal blocked: '{relative_path}' resolves to "
                        f"'{target}', which is outside data_dir '{data_dir_resolved}'."
                    ),
                )
        except (OSError, ValueError) as e:
            raise SandboxViolationError(
                plugin_name=self.plugin_name,
                violation=f"Path resolution error: {e}",
            )

        if not target.exists():
            raise SandboxViolationError(
                plugin_name=self.plugin_name,
                violation=f"File not found: '{relative_path}' in data_dir.",
            )

        content = target.read_bytes()
        self._check_memory_limit(len(content))
        self._memory_bytes_used += len(content)
        return content

    def write_file(self, relative_path: str, content: bytes) -> int:
        """
        Write a file to the plugin's data directory.

        Only files within `data_dir` are allowed. Path traversal is blocked.

        Args:
            relative_path: Path relative to data_dir (e.g. 'output.json').
            content:       Bytes to write.

        Returns:
            Number of bytes written.

        Raises:
            SandboxTerminatedError:    If kill switch is active.
            SandboxResourceLimitError: If memory limit would be exceeded.
            SandboxViolationError:     If data_dir is None or path escapes data_dir.
        """
        self._check_not_terminated()
        self._check_memory_limit(len(content))

        if self._data_dir is None:
            raise SandboxViolationError(
                plugin_name=self.plugin_name,
                violation="No data_dir configured — filesystem access is not allowed.",
            )

        try:
            target = (self._data_dir / relative_path).resolve()
            data_dir_resolved = self._data_dir.resolve()
            if not str(target).startswith(str(data_dir_resolved)):
                raise SandboxViolationError(
                    plugin_name=self.plugin_name,
                    violation=(
                        f"Path traversal blocked: '{relative_path}' resolves outside "
                        f"data_dir '{data_dir_resolved}'."
                    ),
                )
        except (OSError, ValueError) as e:
            raise SandboxViolationError(
                plugin_name=self.plugin_name,
                violation=f"Path resolution error: {e}",
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        self._memory_bytes_used += len(content)
        return len(content)

    def write_output(self, data: bytes) -> int:
        """
        Write data to the sandbox output buffer.

        Args:
            data: Bytes to append to the output buffer.

        Returns:
            Total output buffer size after this write.

        Raises:
            SandboxTerminatedError:    If kill switch is active.
            SandboxResourceLimitError: If output limit would be exceeded.
        """
        self._check_not_terminated()
        self._check_output_limit(len(data))
        self._output_buffer.extend(data)
        return len(self._output_buffer)

    def get_output(self) -> bytes:
        """Return the current output buffer contents."""
        return bytes(self._output_buffer)

    # -------------------------------------------------------------------------
    # Audit log
    # -------------------------------------------------------------------------

    def call_log(self) -> List[SandboxCall]:
        """Return a copy of the API call log."""
        return list(self._call_log)

    def allowed_calls(self) -> List[SandboxCall]:
        """Return only the allowed calls from the audit log."""
        return [c for c in self._call_log if c.allowed]

    def denied_calls(self) -> List[SandboxCall]:
        """Return only the denied (violation) calls from the audit log."""
        return [c for c in self._call_log if not c.allowed]

    # -------------------------------------------------------------------------
    # Resource usage
    # -------------------------------------------------------------------------

    @property
    def memory_bytes_used(self) -> int:
        """Return memory bytes currently tracked as used."""
        return self._memory_bytes_used

    @property
    def output_bytes_used(self) -> int:
        """Return current output buffer size in bytes."""
        return len(self._output_buffer)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso8601() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def compute_plugin_hash(content: bytes) -> str:
    """
    Compute SHA256 hash of plugin content.

    Args:
        content: Plugin content bytes.

    Returns:
        'sha256:<hex_digest>'
    """
    digest = hashlib.sha256(content).hexdigest()
    return f"sha256:{digest}"
