"""
solace-browser machine access layer — OAuth3-gated local machine portal.

Transforms solace-browser from a web-only browser into a universal portal
that can access the local machine (files, terminal, system info) — all gated
by OAuth3 scopes with explicit user consent.

Architecture:
  scopes.py       — Machine-specific OAuth3 scope definitions + registration
  file_browser.py — OAuth3-gated filesystem access (read, write, delete, search)
  terminal.py     — OAuth3-gated command execution + system info
  tunnel.py       — Reverse tunnel management (stub, real impl uses bore/frp)
  api.py          — FastAPI router for all machine endpoints

Scope summary:
  machine.read.home       — Read files in home directory (LOW)
  machine.list.directory  — List directory contents (LOW)
  machine.read.files      — Read any file (MEDIUM)
  machine.execute.safe    — Allowlisted read-only commands (MEDIUM)
  machine.read.sysinfo    — System info (LOW)
  machine.read.processes  — Process list (LOW)
  machine.read.network    — Network info (MEDIUM)
  machine.git.read        — Git status/log/diff (LOW)
  machine.write.files     — Create/modify files (HIGH — step-up)
  machine.delete.files    — Delete files (HIGH — step-up)
  machine.execute.command — Arbitrary shell commands (HIGH — step-up)
  machine.install.package — Install packages (HIGH — step-up)
  machine.git.write       — Git add/commit/push (HIGH — step-up)
  machine.tunnel.manage   — Reverse tunnel (HIGH — step-up)

Registration:
  Machine scopes are registered into the global SCOPE_REGISTRY automatically
  when this package is imported. This allows AgencyToken.create() to accept
  machine.* scopes without ValueError.

Rung: 274177 (machine access — potentially irreversible operations)
"""

from src.machine.scopes import (
    MACHINE_SCOPES,
    register_machine_scopes,
    SCOPE_READ_FILES,
    SCOPE_READ_HOME,
    SCOPE_LIST_DIRECTORY,
    SCOPE_WRITE_FILES,
    SCOPE_DELETE_FILES,
    SCOPE_EXECUTE_COMMAND,
    SCOPE_EXECUTE_SAFE,
    SCOPE_READ_SYSINFO,
    SCOPE_READ_PROCESSES,
    SCOPE_READ_NETWORK,
    SCOPE_INSTALL_PACKAGE,
    SCOPE_GIT_READ,
    SCOPE_GIT_WRITE,
    SCOPE_TUNNEL_MANAGE,
    SCOPE_TUNNEL_OPEN,
)

from src.machine import file_browser
from src.machine import terminal
from src.machine import tunnel
from src.machine import api

# ---------------------------------------------------------------------------
# Auto-register machine scopes into the global SCOPE_REGISTRY on import
# ---------------------------------------------------------------------------

register_machine_scopes()


__all__ = [
    # Scope constants
    "MACHINE_SCOPES",
    "SCOPE_READ_FILES",
    "SCOPE_READ_HOME",
    "SCOPE_LIST_DIRECTORY",
    "SCOPE_WRITE_FILES",
    "SCOPE_DELETE_FILES",
    "SCOPE_EXECUTE_COMMAND",
    "SCOPE_EXECUTE_SAFE",
    "SCOPE_READ_SYSINFO",
    "SCOPE_READ_PROCESSES",
    "SCOPE_READ_NETWORK",
    "SCOPE_INSTALL_PACKAGE",
    "SCOPE_GIT_READ",
    "SCOPE_GIT_WRITE",
    "SCOPE_TUNNEL_MANAGE",
    "SCOPE_TUNNEL_OPEN",
    # Sub-modules
    "file_browser",
    "terminal",
    "tunnel",
    "api",
    # Registration
    "register_machine_scopes",
]

__version__ = "0.1.0"
__rung__ = 274177
