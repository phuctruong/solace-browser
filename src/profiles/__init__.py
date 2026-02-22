"""
SolaceBrowser Multi-Profile Browser — OAuth3-governed browser profile management.

Each profile is a fully isolated execution context:
  - Separate cookie jar (no cross-profile cookie leakage)
  - Separate OAuth3 token set (no cross-profile token access)
  - Independent process management with resource limits

Architecture:
  scopes.py   — Profile-specific OAuth3 scope definitions + registration
  manager.py  — BrowserProfile + ProfileSession + ProfileManager
  process.py  — ProcessInfo (BrowserProcess alias) + ProcessManager

OAuth3 scopes required:
  profile.read.list       — list profiles (LOW)
  profile.read.info       — read profile config (LOW)
  profile.create.profile  — create profile (MEDIUM)
  profile.delete.profile  — delete profile (HIGH — step-up required)
  profile.session.start   — start session (MEDIUM)
  profile.session.suspend — suspend session (LOW)
  profile.session.resume  — resume session (LOW)
  profile.session.terminate — terminate session (HIGH — step-up required)
  profile.session.read    — read session stats (LOW)
  profile.process.spawn   — spawn process (HIGH — step-up required)
  profile.process.kill    — kill process (HIGH — step-up required)
  profile.process.read    — list/inspect processes (LOW)

Rung: 274177 (profile/session/process lifecycle — potentially irreversible operations)
"""

from src.profiles.scopes import (
    PROFILE_SCOPES,
    register_profile_scopes,
    SCOPE_PROFILE_READ_LIST,
    SCOPE_PROFILE_READ_INFO,
    SCOPE_PROFILE_CREATE,
    SCOPE_PROFILE_DELETE,
    SCOPE_SESSION_START,
    SCOPE_SESSION_SUSPEND,
    SCOPE_SESSION_RESUME,
    SCOPE_SESSION_TERMINATE,
    SCOPE_SESSION_READ,
    SCOPE_PROCESS_SPAWN,
    SCOPE_PROCESS_KILL,
    SCOPE_PROCESS_READ,
)

from src.profiles.manager import (
    BrowserProfile,
    ProfileSession,
    ProfileManager,
    SwitchEvent,
    ProfileError,
    ProfileNotFoundError,
    ProfileIsolationError,
    DEFAULT_VIEWPORT,
    DEFAULT_USER_AGENT,
    DEFAULT_PROFILE_NAME,
    MAX_PROFILES,
)

from src.profiles.process import (
    ProcessInfo,
    BrowserProcess,  # alias for ProcessInfo (backward compat)
    ProcessManager,
    ProcessStatus,
    ProcessStats,
    ProcessEvent,
    ProcessError,
    ProcessNotFoundError,
    ResourceLimitError,
)

# ---------------------------------------------------------------------------
# Auto-register profile scopes into the global SCOPE_REGISTRY on import
# ---------------------------------------------------------------------------

register_profile_scopes()


__all__ = [
    # Scopes
    "PROFILE_SCOPES",
    "register_profile_scopes",
    "SCOPE_PROFILE_READ_LIST",
    "SCOPE_PROFILE_READ_INFO",
    "SCOPE_PROFILE_CREATE",
    "SCOPE_PROFILE_DELETE",
    "SCOPE_SESSION_START",
    "SCOPE_SESSION_SUSPEND",
    "SCOPE_SESSION_RESUME",
    "SCOPE_SESSION_TERMINATE",
    "SCOPE_SESSION_READ",
    "SCOPE_PROCESS_SPAWN",
    "SCOPE_PROCESS_KILL",
    "SCOPE_PROCESS_READ",
    # Profile manager
    "BrowserProfile",
    "ProfileSession",
    "ProfileManager",
    "SwitchEvent",
    "ProfileError",
    "ProfileNotFoundError",
    "ProfileIsolationError",
    "DEFAULT_VIEWPORT",
    "DEFAULT_USER_AGENT",
    "DEFAULT_PROFILE_NAME",
    "MAX_PROFILES",
    # Process manager
    "ProcessInfo",
    "BrowserProcess",
    "ProcessManager",
    "ProcessStatus",
    "ProcessStats",
    "ProcessEvent",
    "ProcessError",
    "ProcessNotFoundError",
    "ResourceLimitError",
]

__version__ = "0.2.0"
__rung__ = 274177
