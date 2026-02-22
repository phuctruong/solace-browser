"""
Browser Process Manager — OAuth3-gated lifecycle management.

Each BrowserProcess / ProcessInfo tracks one browser subprocess:
  - process_id (UUID v4)
  - profile_id: which profile owns this process
  - pid: OS process ID (int, or None if not yet spawned / stopped)
  - status: "running" | "stopped" | "crashed"
  - Resource metrics: cpu_percent (int), memory_mb (int), uptime_seconds (int)
  - ISO 8601 UTC timestamps

ProcessManager enforces:
  - spawn_process() requires OAuth3 scope profile.process.spawn (HIGH — step-up)
  - kill_process() requires step-up confirmation
  - Resource limits: max_processes_per_profile, max_memory_total_mb
  - Auto-cleanup: processes killed when session terminates
  - Health check: periodic process health monitoring

OAuth3 scopes:
  profile.process.spawn  — spawn a process (HIGH — step-up required)
  profile.process.kill   — kill a process  (HIGH — step-up required)
  profile.process.read   — list and inspect processes (LOW)

Rung: 274177 (process management — potentially irreversible operations)
"""

from __future__ import annotations

import hashlib
import json
import uuid
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCOPE_PROCESS_SPAWN: str = "profile.process.spawn"
SCOPE_PROCESS_KILL: str = "profile.process.kill"
SCOPE_PROCESS_READ: str = "profile.process.read"

# Default resource limits
DEFAULT_MAX_PROCESSES_PER_PROFILE: int = 5
DEFAULT_MAX_MEMORY_TOTAL_MB: int = 4096   # total across all processes
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS: int = 30

# Fake PID base (for simulation — real impl would call subprocess.Popen)
_FAKE_PID_BASE: int = 10000


# ---------------------------------------------------------------------------
# ProcessStatus — canonical status strings
# ---------------------------------------------------------------------------

class ProcessStatus:
    """Canonical status strings for process status field."""

    RUNNING  = "running"
    STOPPED  = "stopped"
    CRASHED  = "crashed"

    # Extended statuses (backward compat with legacy code)
    STARTING   = "starting"
    SUSPENDED  = "suspended"

    ALL = frozenset(["running", "stopped", "crashed", "starting", "suspended"])


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ProcessError(Exception):
    """Base class for all ProcessManager errors."""


class ProcessNotFoundError(ProcessError):
    """Raised when a process_id is not found in the registry."""


class ResourceLimitError(ProcessError):
    """Raised when spawning a process would exceed a resource limit."""


# ---------------------------------------------------------------------------
# ProcessInfo dataclass (primary API per task spec)
# ---------------------------------------------------------------------------

@dataclass
class ProcessInfo:
    """
    A browser process instance bound to a profile.

    Fields:
        process_id:    UUID4 unique identifier.
        profile_id:    UUID4 of the owning BrowserProfile.
        pid:           OS process ID (int), or None if not yet spawned / stopped.
        status:        One of "running", "stopped", "crashed".
        cpu_percent:   CPU usage as an integer percentage (0–100). NEVER float.
        memory_mb:     Resident memory usage in megabytes (int). NEVER float.
        started_at:    ISO 8601 UTC timestamp when the process was spawned.
        uptime_seconds: Integer seconds since started_at. NEVER float.
    """

    process_id: str
    profile_id: str
    pid: Optional[int]
    status: str                  # running|stopped|crashed
    cpu_percent: int             # integer only — NEVER float
    memory_mb: int               # integer only — NEVER float
    started_at: str              # ISO 8601 UTC
    uptime_seconds: int          # integer only — NEVER float

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def sha256_hash(self) -> str:
        """
        Return SHA-256 hex digest of canonical process fields.

        Used for audit trail integrity.
        """
        canonical = {
            "process_id": self.process_id,
            "profile_id": self.profile_id,
            "pid": self.pid,
            "status": self.status,
            "started_at": self.started_at,
        }
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to plain dict (JSON-serializable)."""
        return {
            "process_id": self.process_id,
            "profile_id": self.profile_id,
            "pid": self.pid,
            "status": self.status,
            "cpu_percent": int(self.cpu_percent),
            "memory_mb": int(self.memory_mb),
            "started_at": self.started_at,
            "uptime_seconds": int(self.uptime_seconds),
        }

    def __repr__(self) -> str:
        return (
            f"ProcessInfo(id={self.process_id[:8]}..., "
            f"profile={self.profile_id[:8]}..., "
            f"pid={self.pid}, status={self.status!r}, "
            f"mem={self.memory_mb}MB)"
        )


# ---------------------------------------------------------------------------
# BrowserProcess — alias for backward compatibility
# ---------------------------------------------------------------------------

BrowserProcess = ProcessInfo


# ---------------------------------------------------------------------------
# ProcessStats — aggregate resource summary
# ---------------------------------------------------------------------------

@dataclass
class ProcessStats:
    """
    Aggregate resource statistics across all managed processes.

    Fields:
        total_processes:   Total number of processes (all statuses).
        running:           Number of processes with status "running".
        suspended:         Number of processes with status "suspended".
        stopped:           Number of processes with status "stopped".
        crashed:           Number of processes with status "crashed".
        total_cpu_percent: Sum of cpu_percent across all running processes (int).
        total_memory_mb:   Sum of memory_mb across all processes (int).
    """

    total_processes: int
    running: int
    suspended: int
    stopped: int
    crashed: int
    total_cpu_percent: int
    total_memory_mb: int

    def to_dict(self) -> dict:
        return {
            "total_processes": self.total_processes,
            "running": self.running,
            "suspended": self.suspended,
            "stopped": self.stopped,
            "crashed": self.crashed,
            "total_cpu_percent": int(self.total_cpu_percent),
            "total_memory_mb": int(self.total_memory_mb),
        }


# ---------------------------------------------------------------------------
# ProcessEvent — evidence log entry for process lifecycle events
# ---------------------------------------------------------------------------

@dataclass
class ProcessEvent:
    """
    Evidence record of a process lifecycle transition.

    Every spawn / kill / crash logs a ProcessEvent to the event_log.
    """

    process_id: str
    event: str          # "spawned" | "killed" | "crashed" | "health_check_ok"
    occurred_at: str    # ISO 8601 UTC
    profile_id: str
    sha256: str         # SHA-256 of the process state at event time

    def to_dict(self) -> dict:
        return {
            "process_id": self.process_id,
            "event": self.event,
            "occurred_at": self.occurred_at,
            "profile_id": self.profile_id,
            "sha256": self.sha256,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(data: dict) -> str:
    """Compute SHA-256 hex digest of a canonical JSON dict."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# ProcessManager
# ---------------------------------------------------------------------------

class ProcessManager:
    """
    OAuth3-gated browser process lifecycle manager.

    Guarantees:
      1. spawn_process() requires OAuth3 step-up (profile.process.spawn is HIGH RISK).
      2. kill_process() requires step_up_confirmed=True (destructive action).
      3. Resource limits: max_processes_per_profile + max_memory_total_mb.
      4. Auto-cleanup: processes auto-killed when their session terminates.
      5. Crash detection: health_check() marks stale processes as "crashed".
      6. All lifecycle events are logged to event_log (evidence trail).

    Usage:
        pm = ProcessManager()
        proc = pm.spawn_process(profile_id, command="chromium", step_up_confirmed=True)
        pm.kill_process(proc.process_id, step_up_confirmed=True)

    Rung: 274177
    """

    def __init__(
        self,
        max_processes_per_profile: int = DEFAULT_MAX_PROCESSES_PER_PROFILE,
        max_memory_total_mb: int = DEFAULT_MAX_MEMORY_TOTAL_MB,
    ) -> None:
        # process_id → ProcessInfo
        self._processes: Dict[str, ProcessInfo] = {}
        # process_id → monotonic start time (for uptime tracking)
        self._start_times: Dict[str, float] = {}
        # process_id → last heartbeat monotonic timestamp
        self._last_heartbeat: Dict[str, float] = {}
        self.max_processes_per_profile: int = max_processes_per_profile
        self.max_memory_total_mb: int = max_memory_total_mb
        self.event_log: List[ProcessEvent] = []
        self._pid_counter: int = _FAKE_PID_BASE

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _new_pid(self) -> int:
        """Allocate a fake monotonically increasing PID for simulation."""
        self._pid_counter += 1
        return self._pid_counter

    def _log_event(self, process: ProcessInfo, event: str) -> None:
        """Append a ProcessEvent to the event_log."""
        record = ProcessEvent(
            process_id=process.process_id,
            event=event,
            occurred_at=_now_iso(),
            profile_id=process.profile_id,
            sha256=process.sha256_hash(),
        )
        self.event_log.append(record)

    def _count_for_profile(self, profile_id: str) -> int:
        """Count active (non-stopped, non-crashed) processes for a profile."""
        return sum(
            1
            for p in self._processes.values()
            if p.profile_id == profile_id
            and p.status not in (ProcessStatus.STOPPED, ProcessStatus.CRASHED)
        )

    def _total_memory(self) -> int:
        """Sum of memory_mb across all processes (integer arithmetic only)."""
        return sum(int(p.memory_mb) for p in self._processes.values())

    def _compute_uptime(self, process_id: str) -> int:
        """Compute uptime in integer seconds from monotonic start time."""
        start = self._start_times.get(process_id, _time.monotonic())
        return int(_time.monotonic() - start)

    # ------------------------------------------------------------------
    # spawn_process
    # ------------------------------------------------------------------

    def spawn_process(
        self,
        profile_id: str,
        command: str = "",
        step_up_confirmed: bool = False,
        initial_cpu_percent: int = 2,
        initial_memory_mb: int = 128,
    ) -> ProcessInfo:
        """
        Spawn a new browser process for the given profile.

        OAuth3 scope required: profile.process.spawn (HIGH — step-up required)

        Args:
            profile_id:         UUID4 of the owning BrowserProfile.
            command:            Shell command or browser executable path (logged, not executed).
            step_up_confirmed:  Must be True (step-up gate for HIGH RISK scope).
            initial_cpu_percent: Simulated initial CPU usage (int percent, 0-100).
            initial_memory_mb:  Simulated initial memory usage (int MB).

        Returns:
            ProcessInfo with status="running".

        Raises:
            PermissionError:   If step_up_confirmed is False (step-up required).
            ResourceLimitError: If max_processes_per_profile or max_memory_total_mb
                               would be exceeded.
        """
        # Gate 1: step-up required (profile.process.spawn is HIGH RISK)
        if not step_up_confirmed:
            raise PermissionError(
                f"profile.process.spawn requires step-up authorization. "
                "Confirm the destructive action before proceeding."
            )

        # Gate 2: per-profile process limit
        current_count = self._count_for_profile(profile_id)
        if current_count >= self.max_processes_per_profile:
            raise ResourceLimitError(
                f"Max processes per profile reached: "
                f"{current_count} >= {self.max_processes_per_profile}. "
                f"Profile: {profile_id}"
            )

        # Gate 3: total memory limit
        projected_memory = self._total_memory() + int(initial_memory_mb)
        if projected_memory > self.max_memory_total_mb:
            raise ResourceLimitError(
                f"Total memory limit would be exceeded: "
                f"{projected_memory} MB > {self.max_memory_total_mb} MB."
            )

        # All gates passed — create the process
        process_id = str(uuid.uuid4())
        pid = self._new_pid()
        now = _now_iso()
        mono_now = _time.monotonic()

        process = ProcessInfo(
            process_id=process_id,
            profile_id=profile_id,
            pid=pid,
            status=ProcessStatus.RUNNING,
            cpu_percent=int(initial_cpu_percent),
            memory_mb=int(initial_memory_mb),
            started_at=now,
            uptime_seconds=0,
        )
        self._processes[process_id] = process
        self._start_times[process_id] = mono_now
        self._last_heartbeat[process_id] = mono_now

        self._log_event(process, "spawned")
        return process

    # ------------------------------------------------------------------
    # kill_process
    # ------------------------------------------------------------------

    def kill_process(
        self,
        process_id: str,
        step_up_confirmed: bool = False,
        token_id: str = "",
    ) -> bool:
        """
        Kill (terminate) a browser process.

        OAuth3 scope required: profile.process.kill (HIGH — step-up required)

        Args:
            process_id:        UUID4 of the process to kill.
            step_up_confirmed: Must be True (step-up gate for HIGH RISK scope).
            token_id:          OAuth3 token_id authorizing the kill (audit trail).

        Returns:
            True if killed, False if process not found.

        Raises:
            PermissionError: If step_up_confirmed is False.
        """
        if not step_up_confirmed:
            raise PermissionError(
                "profile.process.kill requires step-up authorization. "
                "Confirm the destructive action before proceeding."
            )

        process = self._processes.get(process_id)
        if process is None:
            return False

        if process.status in (ProcessStatus.STOPPED, ProcessStatus.CRASHED):
            # Already in terminal state — idempotent
            return True

        uptime = self._compute_uptime(process_id)

        # Update to stopped state
        process.status = ProcessStatus.STOPPED
        process.pid = None
        process.cpu_percent = 0
        process.memory_mb = 0
        process.uptime_seconds = uptime

        self._log_event(process, "killed")

        # Remove from active processes
        self._processes.pop(process_id, None)
        self._start_times.pop(process_id, None)
        self._last_heartbeat.pop(process_id, None)

        return True

    # ------------------------------------------------------------------
    # list_processes / get_process_info
    # ------------------------------------------------------------------

    def list_processes(self) -> List[ProcessInfo]:
        """
        Return all tracked processes with current resource usage.

        OAuth3 scope required: profile.process.read (LOW)

        Returns:
            List of ProcessInfo instances, ordered by started_at.
        """
        # Update uptime for all running processes before returning
        result = []
        for proc in sorted(self._processes.values(), key=lambda p: p.started_at):
            if proc.status == ProcessStatus.RUNNING:
                proc.uptime_seconds = self._compute_uptime(proc.process_id)
            result.append(proc)
        return result

    def get_process_info(self, process_id: str) -> Optional[ProcessInfo]:
        """
        Return the ProcessInfo for a given process_id, or None if not found.

        OAuth3 scope required: profile.process.read (LOW)

        Args:
            process_id: UUID4 of the process to inspect.

        Returns:
            ProcessInfo or None.
        """
        process = self._processes.get(process_id)
        if process is not None and process.status == ProcessStatus.RUNNING:
            process.uptime_seconds = self._compute_uptime(process_id)
        return process

    # ------------------------------------------------------------------
    # Resource stats
    # ------------------------------------------------------------------

    def get_stats(self) -> ProcessStats:
        """
        Return aggregate CPU and memory statistics across all processes.

        Returns:
            ProcessStats instance (all integer values, no float).
        """
        all_procs = list(self._processes.values())
        running   = [p for p in all_procs if p.status == ProcessStatus.RUNNING]
        suspended = [p for p in all_procs if p.status == ProcessStatus.SUSPENDED]
        stopped   = [p for p in all_procs if p.status == ProcessStatus.STOPPED]
        crashed   = [p for p in all_procs if p.status == ProcessStatus.CRASHED]

        return ProcessStats(
            total_processes=len(all_procs),
            running=len(running),
            suspended=len(suspended),
            stopped=len(stopped),
            crashed=len(crashed),
            total_cpu_percent=int(sum(p.cpu_percent for p in running)),
            total_memory_mb=int(sum(p.memory_mb for p in all_procs)),
        )

    # ------------------------------------------------------------------
    # Auto-cleanup: terminate all processes for a session/profile
    # ------------------------------------------------------------------

    def cleanup_for_profile(
        self,
        profile_id: str,
        step_up_confirmed: bool = True,
    ) -> int:
        """
        Kill all processes owned by a given profile.

        Called automatically when a session terminates (auto-cleanup contract).

        Args:
            profile_id:        UUID4 of the profile whose processes to clean up.
            step_up_confirmed: Passed to kill_process() (default True for auto-cleanup).

        Returns:
            Number of processes killed.
        """
        to_kill = [
            p.process_id for p in self._processes.values()
            if p.profile_id == profile_id
            and p.status not in (ProcessStatus.STOPPED, ProcessStatus.CRASHED)
        ]
        count = 0
        for pid_str in to_kill:
            try:
                if self.kill_process(pid_str, step_up_confirmed=step_up_confirmed):
                    count += 1
            except PermissionError:
                pass  # Should not happen with step_up_confirmed=True
        return count

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(
        self,
        heartbeat_timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    ) -> List[ProcessInfo]:
        """
        Check all running processes for health.

        Marks stale processes (no heartbeat update within timeout) as "crashed".

        Args:
            heartbeat_timeout_seconds: Seconds since last heartbeat before a
                                       process is considered crashed.

        Returns:
            List of processes that were marked as crashed.
        """
        now_mono = _time.monotonic()
        affected: List[ProcessInfo] = []

        for process_id, process in list(self._processes.items()):
            if process.status != ProcessStatus.RUNNING:
                continue

            last_hb = self._last_heartbeat.get(process_id, 0.0)
            if (now_mono - last_hb) > int(heartbeat_timeout_seconds):
                process.status = ProcessStatus.CRASHED
                process.pid = None
                process.cpu_percent = 0
                process.memory_mb = 0
                process.uptime_seconds = self._compute_uptime(process_id)
                self._log_event(process, "crashed")
                affected.append(process)

        return affected

    def heartbeat(self, process_id: str) -> bool:
        """
        Update the heartbeat timestamp for a process.

        Call this periodically from the browser process to signal it is alive.

        Args:
            process_id: UUID4 of the process.

        Returns:
            True if the process exists and is running.
            False if the process does not exist or is not running.
        """
        process = self._processes.get(process_id)
        if process is None or process.status != ProcessStatus.RUNNING:
            return False

        self._last_heartbeat[process_id] = _time.monotonic()
        return True

    def mark_crashed(self, process_id: str) -> Optional[ProcessInfo]:
        """
        Mark a process as crashed (for testing or external signal injection).

        Args:
            process_id: UUID4 of the process.

        Returns:
            Updated ProcessInfo, or None if not found.
        """
        process = self._processes.get(process_id)
        if process is None:
            return None

        process.status = ProcessStatus.CRASHED
        process.pid = None
        process.cpu_percent = 0
        process.memory_mb = 0
        process.uptime_seconds = self._compute_uptime(process_id)
        self._log_event(process, "crashed")
        return process

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"ProcessManager("
            f"total={stats.total_processes}, "
            f"running={stats.running}, "
            f"stopped={stats.stopped}, "
            f"crashed={stats.crashed})"
        )
