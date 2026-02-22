"""
companion/scopes.py — Companion-specific OAuth3 scope definitions.

Registers companion scopes into the central SCOPE_REGISTRY so that
AgencyToken.create() and validate_scopes() accept them.

Scope convention: companion.<action>.<resource>  (triple-segment, per spec §2.1)

Step-up scopes (risk_level="high"):
  companion.app.system_access   — system-level companion access
  companion.recorder.replay     — session replay (irreversible play-back)

Rung: 641 (local correctness)
"""

from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# Companion scope definitions
# ---------------------------------------------------------------------------

COMPANION_SCOPES: Dict[str, Dict] = {
    # Core companion runtime
    "companion.app.run": {
        "platform": "companion",
        "description": "Run a companion app alongside the browser agent",
        "risk_level": "low",
        "destructive": False,
    },
    "companion.app.system_access": {
        "platform": "companion",
        "description": "System-level companion access — elevated privileges (step-up required)",
        "risk_level": "high",
        "destructive": True,
    },
    # Bridge / communication
    "companion.bridge.communicate": {
        "platform": "companion",
        "description": "Cross-boundary communication between companion apps and the browser",
        "risk_level": "medium",
        "destructive": False,
    },
    # Clipboard monitoring
    "companion.clipboard.monitor": {
        "platform": "companion",
        "description": "Monitor clipboard for URLs and text to suggest actions",
        "risk_level": "low",
        "destructive": False,
    },
    # Session recording / replay
    "companion.recorder.capture": {
        "platform": "companion",
        "description": "Record browser sessions for later replay",
        "risk_level": "low",
        "destructive": False,
    },
    "companion.recorder.replay": {
        "platform": "companion",
        "description": "Replay a recorded browser session (step-up required)",
        "risk_level": "high",
        "destructive": True,
    },
    # Task tracking
    "companion.tracker.manage": {
        "platform": "companion",
        "description": "Create and manage multi-step task tracking",
        "risk_level": "low",
        "destructive": False,
    },
}

# ---------------------------------------------------------------------------
# Register companion scopes into the central registry on import
# ---------------------------------------------------------------------------

def _register_companion_scopes() -> None:
    """
    Inject companion scopes into the central OAuth3 SCOPE_REGISTRY.

    Also updates _COMBINED_SCOPE_REGISTRY (used by get_scope_risk_level,
    get_scope_description) and refreshes the derived HIGH_RISK_SCOPES /
    DESTRUCTIVE_SCOPES frozensets.

    Called once at module import.  Idempotent (safe to call multiple times).
    """
    import oauth3.scopes as _scopes_mod

    for scope, meta in COMPANION_SCOPES.items():
        if scope not in _scopes_mod.SCOPE_REGISTRY:
            _scopes_mod.SCOPE_REGISTRY[scope] = meta
        # _COMBINED_SCOPE_REGISTRY is a plain dict — update it in place so that
        # helper functions like get_scope_risk_level() see the new scopes.
        if scope not in _scopes_mod._COMBINED_SCOPE_REGISTRY:
            _scopes_mod._COMBINED_SCOPE_REGISTRY[scope] = meta

    # Refresh derived frozensets — we replace the module-level names in place.
    _scopes_mod.HIGH_RISK_SCOPES = frozenset(
        s for s, m in _scopes_mod._COMBINED_SCOPE_REGISTRY.items()
        if m["risk_level"] == "high"
    )
    _scopes_mod.DESTRUCTIVE_SCOPES = frozenset(
        s for s, m in _scopes_mod._COMBINED_SCOPE_REGISTRY.items()
        if m["destructive"]
    )


# Register on import — any module that imports companion.scopes automatically
# makes companion.* scopes visible to AgencyToken.create().
_register_companion_scopes()

# ---------------------------------------------------------------------------
# Convenience sets
# ---------------------------------------------------------------------------

# All companion scope strings
ALL_COMPANION_SCOPES: frozenset = frozenset(COMPANION_SCOPES.keys())

# Companion scopes that require step-up authentication
COMPANION_STEP_UP_SCOPES: frozenset = frozenset(
    s for s, m in COMPANION_SCOPES.items() if m["risk_level"] == "high"
)

# Base scope required by every companion app
COMPANION_BASE_SCOPE: str = "companion.app.run"
