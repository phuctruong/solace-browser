"""
Profile-specific OAuth3 scopes — multi-profile browser access layer.

All scopes follow the triple-segment convention: platform.action.resource
Platform segment: "profile"

Risk levels:
  low    — read-only, non-sensitive, no side-effects
  medium — read-only but sensitive, or limited write
  high   — destructive, irreversible, or system-wide impact (step-up required)

These scopes extend the global SCOPE_REGISTRY at import time.
Import this module to register profile scopes before creating tokens with them.

OAuth3 scope format: profile.<action>
Examples: profile.create, profile.session.start, profile.process.spawn

Reference: oauth3-spec-v0.1.md §2
Rung: 641
"""

from __future__ import annotations

from typing import Dict


# ---------------------------------------------------------------------------
# Profile scope definitions (triple-segment: profile.action.resource)
# ---------------------------------------------------------------------------

PROFILE_SCOPES: Dict[str, Dict] = {

    # -------------------------------------------------------------------------
    # Profile management — read (low risk)
    # -------------------------------------------------------------------------

    "profile.read.list": {
        "platform": "profile",
        "description": "List all browser profiles",
        "risk_level": "low",
        "destructive": False,
    },
    "profile.read.info": {
        "platform": "profile",
        "description": "Read a single browser profile's configuration",
        "risk_level": "low",
        "destructive": False,
    },

    # -------------------------------------------------------------------------
    # Profile management — write (medium/high risk)
    # -------------------------------------------------------------------------

    "profile.create.profile": {
        "platform": "profile",
        "description": "Create a new browser profile",
        "risk_level": "medium",
        "destructive": False,
    },
    "profile.delete.profile": {
        "platform": "profile",
        "description": "Delete a browser profile and all its data (irreversible)",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Session lifecycle
    # -------------------------------------------------------------------------

    "profile.session.start": {
        "platform": "profile",
        "description": "Start a browsing session for a profile",
        "risk_level": "medium",
        "destructive": False,
    },
    "profile.session.suspend": {
        "platform": "profile",
        "description": "Suspend an active browsing session",
        "risk_level": "low",
        "destructive": False,
    },
    "profile.session.resume": {
        "platform": "profile",
        "description": "Resume a suspended browsing session",
        "risk_level": "low",
        "destructive": False,
    },
    "profile.session.terminate": {
        "platform": "profile",
        "description": "Terminate a browsing session (irreversible for session data)",
        "risk_level": "high",
        "destructive": True,
    },
    "profile.session.read": {
        "platform": "profile",
        "description": "Read session stats and current state",
        "risk_level": "low",
        "destructive": False,
    },

    # -------------------------------------------------------------------------
    # Process management
    # -------------------------------------------------------------------------

    "profile.process.spawn": {
        "platform": "profile",
        "description": "Spawn a browser process for a profile",
        "risk_level": "high",
        "destructive": True,
    },
    "profile.process.kill": {
        "platform": "profile",
        "description": "Kill a browser process (irreversible for process state)",
        "risk_level": "high",
        "destructive": True,
    },
    "profile.process.read": {
        "platform": "profile",
        "description": "List and inspect browser processes",
        "risk_level": "low",
        "destructive": False,
    },
}


# ---------------------------------------------------------------------------
# Registration helper — merges PROFILE_SCOPES into the global SCOPE_REGISTRY
# ---------------------------------------------------------------------------

def register_profile_scopes() -> None:
    """
    Merge PROFILE_SCOPES into the global SCOPE_REGISTRY and update derived sets.

    Call this once at application startup (before creating any profile-scoped tokens).
    Importing src.profiles auto-calls this via __init__.py.

    This is additive — it never removes existing scopes.
    """
    from src.oauth3.scopes import SCOPE_REGISTRY

    for scope, meta in PROFILE_SCOPES.items():
        if scope not in SCOPE_REGISTRY:
            SCOPE_REGISTRY[scope] = meta

    # Rebuild derived frozensets to include the new profile scopes
    import src.oauth3.scopes as _scopes_mod

    _scopes_mod.ALL_SCOPES = frozenset(_scopes_mod.SCOPE_REGISTRY.keys())
    _combined = {**_scopes_mod.SCOPE_REGISTRY, **_scopes_mod._LEGACY_SCOPE_ALIASES}
    _scopes_mod.HIGH_RISK_SCOPES = frozenset(
        s for s, m in _combined.items() if m["risk_level"] == "high"
    )
    _scopes_mod.DESTRUCTIVE_SCOPES = frozenset(
        s for s, m in _combined.items() if m["destructive"]
    )
    _scopes_mod.STEP_UP_REQUIRED_SCOPES = sorted(_scopes_mod.HIGH_RISK_SCOPES)
    _scopes_mod.SCOPES = {s: m["description"] for s, m in _combined.items()}
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

SCOPE_PROFILE_READ_LIST     = "profile.read.list"
SCOPE_PROFILE_READ_INFO     = "profile.read.info"
SCOPE_PROFILE_CREATE        = "profile.create.profile"
SCOPE_PROFILE_DELETE        = "profile.delete.profile"
SCOPE_SESSION_START         = "profile.session.start"
SCOPE_SESSION_SUSPEND       = "profile.session.suspend"
SCOPE_SESSION_RESUME        = "profile.session.resume"
SCOPE_SESSION_TERMINATE     = "profile.session.terminate"
SCOPE_SESSION_READ          = "profile.session.read"
SCOPE_PROCESS_SPAWN         = "profile.process.spawn"
SCOPE_PROCESS_KILL          = "profile.process.kill"
SCOPE_PROCESS_READ          = "profile.process.read"
