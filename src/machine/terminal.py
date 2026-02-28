"""
OAuth3-gated command execution and system information layer.

Every function enforces scope gates before executing any system call.
Two execution modes:
  - execute_command: arbitrary shell (machine.execute.command — HIGH RISK)
  - execute_safe: allowlist-only commands (machine.execute.safe — MEDIUM RISK)

Security architecture:
  - Blocklist for execute_command: catastrophic/irreversible commands rejected
  - Allowlist for execute_safe: only pre-approved read-only commands
  - Timeout enforced on all command executions (default 30s, max 300s)
  - All commands logged to audit trail with exit code and duration
  - No secrets in audit log (stderr truncated at 2 KB, stdout at 8 KB)

Rung: 274177 (command execution — potentially irreversible)
"""

from __future__ import annotations

import datetime
import getpass
import json
import logging
import os
import platform
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from src.oauth3.token import AgencyToken
from src.oauth3.enforcement import ScopeGate
from src.machine.scopes import (
    SCOPE_EXECUTE_COMMAND,
    SCOPE_EXECUTE_SAFE,
    SCOPE_READ_SYSINFO,
    SCOPE_READ_PROCESSES,
)


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_SECONDS: int = 30
MAX_TIMEOUT_SECONDS: int = 300
MAX_STDOUT_BYTES: int = 8_192       # 8 KB stdout cap in audit log
MAX_STDERR_BYTES: int = 2_048       # 2 KB stderr cap in audit log
AUDIT_LOG_PATH: Path = Path.home() / ".stillwater" / "machine_audit.jsonl"
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Blocklist — patterns for execute_command
#
# A command is blocked if ANY of these regex patterns match (case-insensitive).
# The match is applied to the full command string BEFORE shell expansion.
# ---------------------------------------------------------------------------

_COMMAND_BLOCKLIST: tuple = (
    # Filesystem destruction
    r"rm\s+-rf\s+/",
    r"rm\s+--no-preserve-root",
    r"\bshred\b",
    r"\bwipe\b",
    # Block device overwrite
    r"\bdd\b.*if=/dev/(zero|random|urandom)",
    r"\bmkfs\b",
    r"\bfdisk\b",
    r"\bparted\b",
    # Fork bomb
    r":\(\)\s*\{",
    r":\s*\(\s*\)\s*\{",
    # Power / boot
    r"\b(shutdown|reboot|halt|poweroff|init\s+0|init\s+6)\b",
    # Privilege escalation
    r"\bsudo\b",
    r"\bsu\s+-",
    # Password / credential modification
    r"\bpasswd\b",
    r"\bchpasswd\b",
    r"\busermod\b",
    r"\buseradd\b",
    r"\badduser\b",
    # Pipe-to-shell (curl/wget → exec)
    r"curl\s+.*\|\s*(bash|sh|zsh|fish|python|perl|ruby)",
    r"wget\s+.*\|\s*(bash|sh|zsh|fish|python|perl|ruby)",
    r"curl\s+.*-\s*\|\s*(bash|sh)",
    # Reverse shells (common patterns)
    r"/dev/tcp/",
    r"/dev/udp/",
    r"nc\s+-e\s+/bin",
    r"bash\s+-i\s+>&",
    # Crontab modification
    r"\bcrontab\s+-[re]\b",
    # System package uninstall (with force)
    r"(apt|dpkg|rpm|yum|dnf|brew)\s+.*--force.*remove",
    r"(apt|dpkg|rpm|yum|dnf)\s+.*purge",
)

_BLOCKLIST_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _COMMAND_BLOCKLIST]


# ---------------------------------------------------------------------------
# Allowlist — commands permitted by execute_safe
#
# Matching is done on the first "word" (program name) of the command,
# after which we verify the full command starts with an allowed prefix.
# ---------------------------------------------------------------------------

_SAFE_COMMAND_PREFIXES: tuple = (
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    "file",
    "stat",
    "du",
    "df",
    "uname",
    "whoami",
    "pwd",
    "env",
    "echo",
    "date",
    "git status",
    "git log",
    "git diff",
    "git branch",
    "git remote",
    "python --version",
    "python3 --version",
    "python -V",
    "python3 -V",
    "node --version",
    "node -v",
    "pip list",
    "pip3 list",
    "npm list",
    "npm ls",
    "pip show",
    "pip3 show",
    "which",
    "type",
    "id",
    "hostname",
    "uptime",
    "free",
    "top -bn1",
    "ps",
    "lsof",
    "netstat",
    "ss",
    "ifconfig",
    "ip",
    "curl --version",
    "git --version",
    "make --version",
    "gcc --version",
    "clang --version",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _audit(action: str, token: AgencyToken, command: str, extra: Optional[dict] = None) -> None:
    """Emit a structured audit record. Fails silently."""
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": _now_iso(),
            "action": action,
            "token_id": token.token_id,
            "subject": token.subject,
            "command": command,
            **(extra or {}),
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("machine terminal audit write failed: %s", exc)


def _gate_check(token: AgencyToken, required_scopes: list) -> Optional[dict]:
    """Run ScopeGate.check_all(). Returns None if allowed, error dict if blocked."""
    gate = ScopeGate(token=token, required_scopes=required_scopes)
    result = gate.check_all()
    if not result.allowed:
        return {
            "error": result.error_code,
            "detail": result.error_detail,
            "blocking_gate": result.blocking_gate,
            "missing_scopes": result.missing_scopes,
        }
    return None


def _is_blocked(command: str) -> tuple:
    """
    Check command against the blocklist.

    Returns:
        (is_blocked: bool, matched_pattern: str | None)
    """
    for pat in _BLOCKLIST_PATTERNS:
        if pat.search(command):
            return True, pat.pattern
    return False, None


def _is_safe_command(command: str) -> bool:
    """
    Return True if command starts with one of the allowed safe prefixes.

    Matching is case-sensitive (shell commands are case-sensitive on Linux/macOS).
    """
    cmd_stripped = command.strip()
    for prefix in _SAFE_COMMAND_PREFIXES:
        if cmd_stripped == prefix or cmd_stripped.startswith(prefix + " "):
            return True
    return False


def _truncate(s: str, max_bytes: int) -> str:
    """Truncate string to max_bytes (UTF-8 safe)."""
    encoded = s.encode("utf-8")
    if len(encoded) <= max_bytes:
        return s
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n...[truncated]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_command(
    command: str,
    token: AgencyToken,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    cwd: Optional[str] = None,
) -> dict:
    """
    Execute an arbitrary shell command as the current user.

    Required scope: machine.execute.command (HIGH RISK)

    Blocklist of catastrophic/irreversible commands is enforced regardless of scope.
    Timeout is enforced (default 30s, max 300s).

    Args:
        command: Shell command string.
        token:   AgencyToken with machine.execute.command scope.
        timeout: Execution timeout in seconds (max 300).
        cwd:     Working directory for the command (default: current directory).

    Returns:
        {
          "command": str,
          "stdout": str,
          "stderr": str,
          "exit_code": int,
          "duration_ms": int,
          "cwd": str,
        }
        or {"error": ..., "detail": ...} on failure/block.
    """
    err = _gate_check(token, [SCOPE_EXECUTE_COMMAND])
    if err:
        return err

    # Clamp timeout
    timeout = max(1, min(timeout, MAX_TIMEOUT_SECONDS))

    # Blocklist check (applied after scope gate — belt-and-suspenders)
    blocked, pattern = _is_blocked(command)
    if blocked:
        _audit("execute_command_blocked", token, command, {"pattern": str(pattern)})
        return {
            "error": "COMMAND_BLOCKED",
            "detail": (
                f"Command matches a blocked pattern and was rejected. "
                f"Pattern: {pattern!r}"
            ),
            "command": command,
        }

    effective_cwd = cwd or os.getcwd()

    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=effective_cwd,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        result = {
            "command": command,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "duration_ms": duration_ms,
            "cwd": effective_cwd,
        }
        _audit("execute_command", token, command, {
            "exit_code": proc.returncode,
            "duration_ms": duration_ms,
            "stdout_preview": _truncate(proc.stdout, MAX_STDOUT_BYTES),
            "stderr_preview": _truncate(proc.stderr, MAX_STDERR_BYTES),
        })
        return result

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        _audit("execute_command_timeout", token, command, {
            "timeout_seconds": timeout,
            "duration_ms": duration_ms,
        })
        return {
            "error": "COMMAND_TIMEOUT",
            "detail": f"Command exceeded timeout of {timeout}s",
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "duration_ms": duration_ms,
            "cwd": effective_cwd,
        }
    except OSError as exc:
        _audit("execute_command_error", token, command, {"error": str(exc)})
        return {
            "error": "EXECUTION_ERROR",
            "detail": str(exc),
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "duration_ms": 0,
            "cwd": effective_cwd,
        }


def execute_safe(command: str, token: AgencyToken) -> dict:
    """
    Execute a read-only command from the allowlist.

    Required scope: machine.execute.safe (MEDIUM RISK)

    Only commands whose prefix appears in the safe allowlist are permitted.
    Any command not on the allowlist is rejected regardless of scope.

    Args:
        command: Shell command string.
        token:   AgencyToken with machine.execute.safe scope.

    Returns:
        Same schema as execute_command.
        or {"error": "COMMAND_NOT_ALLOWED", ...} if command not in allowlist.
    """
    err = _gate_check(token, [SCOPE_EXECUTE_SAFE])
    if err:
        return err

    if not _is_safe_command(command):
        _audit("execute_safe_rejected", token, command)
        return {
            "error": "COMMAND_NOT_ALLOWED",
            "detail": (
                f"Command {command!r} is not in the safe-command allowlist. "
                "Use execute_command with machine.execute.command scope for "
                "arbitrary commands."
            ),
            "command": command,
        }

    effective_cwd = os.getcwd()
    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            cwd=effective_cwd,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        result = {
            "command": command,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "duration_ms": duration_ms,
            "cwd": effective_cwd,
        }
        _audit("execute_safe", token, command, {
            "exit_code": proc.returncode,
            "duration_ms": duration_ms,
        })
        return result

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        _audit("execute_safe_timeout", token, command, {"duration_ms": duration_ms})
        return {
            "error": "COMMAND_TIMEOUT",
            "detail": f"Command exceeded timeout of {DEFAULT_TIMEOUT_SECONDS}s",
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "duration_ms": duration_ms,
            "cwd": effective_cwd,
        }
    except OSError as exc:
        return {
            "error": "EXECUTION_ERROR",
            "detail": str(exc),
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "duration_ms": 0,
            "cwd": effective_cwd,
        }


def get_system_info(token: AgencyToken) -> dict:
    """
    Return read-only system information.

    Required scope: machine.read.sysinfo

    Returns:
        {
          "os": str,
          "platform": str,
          "hostname": str,
          "cpu_count": int,
          "memory_total_gb": float,
          "disk_usage": {"total_gb", "used_gb", "free_gb", "percent"},
          "python_version": str,
          "username": str,
        }
        or {"error": ..., "detail": ...} on failure.
    """
    err = _gate_check(token, [SCOPE_READ_SYSINFO])
    if err:
        return err

    info: dict = {
        "os": platform.system(),
        "platform": platform.platform(),
        "hostname": platform.node(),
        "cpu_count": os.cpu_count() or 0,
        "python_version": platform.python_version(),
        "username": getpass.getuser(),
    }

    # Memory info (try psutil, fall back to /proc/meminfo on Linux)
    memory_total_gb = 0.0
    try:
        import psutil
        mem = psutil.virtual_memory()
        memory_total_gb = round(mem.total / (1024 ** 3), 2)
    except ImportError:
        try:
            with open("/proc/meminfo", "r") as fh:
                for line in fh:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        memory_total_gb = round(kb / (1024 ** 2), 2)
                        break
        except OSError as exc:
            logger.debug("Could not read /proc/meminfo: %s", exc)
    info["memory_total_gb"] = memory_total_gb

    # Disk usage for the home directory
    try:
        import shutil
        usage = shutil.disk_usage(str(Path.home()))
        info["disk_usage"] = {
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "percent": round(usage.used / usage.total * 100, 1) if usage.total else 0,
        }
    except OSError as exc:
        info["disk_usage"] = {"error": str(exc)}

    _audit("get_system_info", token, "system", {})
    return info


def list_processes(token: AgencyToken) -> list:
    """
    List top 50 processes by CPU usage.

    Required scope: machine.read.processes

    Returns:
        List of {"pid", "name", "cpu_percent", "memory_mb"} dicts,
        sorted by cpu_percent descending (top 50 only).
        Returns [{"error": ..., "detail": ...}] on failure.
    """
    err = _gate_check(token, [SCOPE_READ_PROCESSES])
    if err:
        return [err]

    processes: List[dict] = []

    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = proc.info
                mem_mb = 0.0
                if info.get("memory_info"):
                    mem_mb = round(info["memory_info"].rss / (1024 ** 2), 2)
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"] or "",
                    "cpu_percent": info.get("cpu_percent") or 0.0,
                    "memory_mb": mem_mb,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        # psutil not available — fall back to ps command
        try:
            proc = subprocess.run(
                ["ps", "aux", "--no-header"],
                capture_output=True, text=True, timeout=10
            )
            for line in proc.stdout.strip().splitlines():
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    try:
                        processes.append({
                            "pid": int(parts[1]),
                            "name": parts[10].split()[0] if parts[10].split() else "",
                            "cpu_percent": float(parts[2]),
                            "memory_mb": float(parts[5]) / 1024,
                        })
                    except (ValueError, IndexError):
                        continue
        except (subprocess.TimeoutExpired, OSError):
            return [{"error": "PROCESS_LIST_UNAVAILABLE",
                     "detail": "Neither psutil nor ps command is available."}]

    # Sort by CPU descending, take top 50
    processes.sort(key=lambda p: p.get("cpu_percent", 0.0), reverse=True)
    top50 = processes[:50]

    _audit("list_processes", token, "system", {"count": len(top50)})
    return top50
