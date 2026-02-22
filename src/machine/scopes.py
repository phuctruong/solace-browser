"""
Machine-specific OAuth3 scopes — local machine access layer.

All scopes follow the triple-segment convention: platform.action.resource
Platform segment: "machine"

Risk levels:
  low    — read-only, non-sensitive, no side-effects
  medium — read-only but sensitive, or limited write
  high   — destructive, irreversible, or system-wide impact (step-up required)

These scopes extend the global SCOPE_REGISTRY at import time.
Import this module to register machine scopes before creating tokens with them.

Reference: oauth3-spec-v0.1.md §2
Rung: 641
"""

from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# Machine scope definitions (triple-segment: machine.action.resource)
# ---------------------------------------------------------------------------

MACHINE_SCOPES: Dict[str, Dict] = {

    # -------------------------------------------------------------------------
    # File system — read
    # -------------------------------------------------------------------------

    "machine.read.files": {
        "platform": "machine",
        "description": "Read files and directories anywhere on the filesystem",
        "risk_level": "medium",
        "destructive": False,
    },
    "machine.read.home": {
        "platform": "machine",
        "description": "Read files within the user home directory only",
        "risk_level": "low",
        "destructive": False,
    },
    "machine.list.directory": {
        "platform": "machine",
        "description": "List directory contents (names, sizes, timestamps)",
        "risk_level": "low",
        "destructive": False,
    },

    # -------------------------------------------------------------------------
    # File system — write (HIGH RISK — step-up required)
    # -------------------------------------------------------------------------

    "machine.write.files": {
        "platform": "machine",
        "description": "Create and modify files on the filesystem",
        "risk_level": "high",
        "destructive": True,
    },
    "machine.delete.files": {
        "platform": "machine",
        "description": "Delete files and directories (irreversible)",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Terminal / Shell
    # -------------------------------------------------------------------------

    "machine.execute.command": {
        "platform": "machine",
        "description": "Execute arbitrary shell commands as the current user",
        "risk_level": "high",
        "destructive": True,
    },
    "machine.execute.safe": {
        "platform": "machine",
        "description": "Execute read-only commands from an allowlist (ls, cat, grep, etc.)",
        "risk_level": "medium",
        "destructive": False,
    },

    # -------------------------------------------------------------------------
    # System information (read-only, low risk)
    # -------------------------------------------------------------------------

    "machine.read.sysinfo": {
        "platform": "machine",
        "description": "Read system information: OS, CPU, memory, disk usage",
        "risk_level": "low",
        "destructive": False,
    },
    "machine.read.processes": {
        "platform": "machine",
        "description": "List running processes (pid, name, cpu, memory)",
        "risk_level": "low",
        "destructive": False,
    },
    "machine.read.network": {
        "platform": "machine",
        "description": "Read network interface and connection information",
        "risk_level": "medium",
        "destructive": False,
    },

    # -------------------------------------------------------------------------
    # Package management (HIGH RISK)
    # -------------------------------------------------------------------------

    "machine.install.package": {
        "platform": "machine",
        "description": "Install system packages (apt, brew, pip, npm, etc.)",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Git operations
    # -------------------------------------------------------------------------

    "machine.git.read": {
        "platform": "machine",
        "description": "Read git status, log, diff (non-mutating)",
        "risk_level": "low",
        "destructive": False,
    },
    "machine.git.write": {
        "platform": "machine",
        "description": "Git add, commit, push, checkout, branch (mutating)",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Reverse tunnel (HIGH RISK — step-up required)
    # -------------------------------------------------------------------------

    "machine.tunnel.manage": {
        "platform": "machine",
        "description": "Start and stop a reverse tunnel to solaceagi.com",
        "risk_level": "high",
        "destructive": True,
    },

    "machine.tunnel.open": {
        "platform": "machine",
        "description": "Open a WebSocket reverse tunnel session to solaceagi.com (persistent connection)",
        "risk_level": "high",
        "destructive": True,
    },
}


# ---------------------------------------------------------------------------
# Registration helper — merges MACHINE_SCOPES into the global SCOPE_REGISTRY
# ---------------------------------------------------------------------------

def register_machine_scopes() -> None:
    """
    Merge MACHINE_SCOPES into the global SCOPE_REGISTRY and update derived sets.

    Call this once at application startup (before creating any machine-scoped tokens).
    Importing src.machine auto-calls this via __init__.py.

    This is additive — it never removes existing scopes.
    """
    from src.oauth3.scopes import (
        SCOPE_REGISTRY,
        HIGH_RISK_SCOPES,
        DESTRUCTIVE_SCOPES,
        ALL_SCOPES,
    )

    for scope, meta in MACHINE_SCOPES.items():
        if scope not in SCOPE_REGISTRY:
            SCOPE_REGISTRY[scope] = meta

    # Rebuild the derived frozensets in-place is not possible (frozen),
    # so we update the module-level mutable references via the module object.
    import src.oauth3.scopes as _scopes_mod

    # Re-derive from the now-extended SCOPE_REGISTRY
    _scopes_mod.ALL_SCOPES = frozenset(_scopes_mod.SCOPE_REGISTRY.keys())
    # HIGH_RISK_SCOPES and DESTRUCTIVE_SCOPES include both triple-segment and
    # legacy two-segment aliases (from _LEGACY_SCOPE_ALIASES).
    _combined = {**_scopes_mod.SCOPE_REGISTRY, **_scopes_mod._LEGACY_SCOPE_ALIASES}
    _scopes_mod.HIGH_RISK_SCOPES = frozenset(
        s for s, m in _combined.items() if m["risk_level"] == "high"
    )
    _scopes_mod.DESTRUCTIVE_SCOPES = frozenset(
        s for s, m in _combined.items() if m["destructive"]
    )
    _scopes_mod.STEP_UP_REQUIRED_SCOPES = sorted(_scopes_mod.HIGH_RISK_SCOPES)
    # SCOPES includes both triple-segment (extended by machine scopes) and legacy aliases.
    _scopes_mod.SCOPES = {
        s: m["description"] for s, m in _combined.items()
    }
    # Keep _COMBINED_SCOPE_REGISTRY in sync too
    _scopes_mod._COMBINED_SCOPE_REGISTRY = _combined

    # Also patch the re-exported names in src.oauth3 package namespace
    import src.oauth3 as _oauth3_mod
    _oauth3_mod.ALL_SCOPES = _scopes_mod.ALL_SCOPES
    _oauth3_mod.HIGH_RISK_SCOPES = _scopes_mod.HIGH_RISK_SCOPES
    _oauth3_mod.DESTRUCTIVE_SCOPES = _scopes_mod.DESTRUCTIVE_SCOPES
    _oauth3_mod.SCOPE_REGISTRY = _scopes_mod.SCOPE_REGISTRY


# ---------------------------------------------------------------------------
# Convenience scope name constants (avoids magic strings in callers)
# ---------------------------------------------------------------------------

SCOPE_READ_FILES = "machine.read.files"
SCOPE_READ_HOME = "machine.read.home"
SCOPE_LIST_DIRECTORY = "machine.list.directory"
SCOPE_WRITE_FILES = "machine.write.files"
SCOPE_DELETE_FILES = "machine.delete.files"
SCOPE_EXECUTE_COMMAND = "machine.execute.command"
SCOPE_EXECUTE_SAFE = "machine.execute.safe"
SCOPE_READ_SYSINFO = "machine.read.sysinfo"
SCOPE_READ_PROCESSES = "machine.read.processes"
SCOPE_READ_NETWORK = "machine.read.network"
SCOPE_INSTALL_PACKAGE = "machine.install.package"
SCOPE_GIT_READ = "machine.git.read"
SCOPE_GIT_WRITE = "machine.git.write"
SCOPE_TUNNEL_MANAGE = "machine.tunnel.manage"
SCOPE_TUNNEL_OPEN = "machine.tunnel.open"
