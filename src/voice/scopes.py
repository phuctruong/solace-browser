"""
voice/scopes.py — Voice-specific OAuth3 Scope Definitions

Scope naming convention: platform.action.resource  (triple-segment, spec §2.1)

Voice scopes:
  voice.wake.listen     — activate wake word detection (local microphone access)
  voice.wake.always_on  — persistent wake listening (step-up required)
  voice.talk.command    — issue voice commands
  voice.talk.dictate    — voice-to-text dictation
  voice.tts.speak       — text-to-speech output
  voice.tts.persona     — custom TTS voice persona (step-up required)

All voice operations are local-only: no audio leaves the device.
Destructive voice commands additionally require the target recipe's own scope.

Rung: 641
"""

from __future__ import annotations

from typing import Dict, List


# ---------------------------------------------------------------------------
# Voice scope registry entry type
# ---------------------------------------------------------------------------

# Each entry: {"description": str, "risk_level": "low"|"medium"|"high",
#              "destructive": bool, "step_up_required": bool}

VOICE_SCOPE_REGISTRY: Dict[str, Dict] = {

    # -------------------------------------------------------------------------
    # Wake word detection
    # -------------------------------------------------------------------------

    "voice.wake.listen": {
        "platform": "voice",
        "description": "Activate wake word detection (local microphone, no cloud streaming)",
        "risk_level": "low",
        "destructive": False,
        "step_up_required": False,
    },

    "voice.wake.always_on": {
        "platform": "voice",
        "description": (
            "Persistent wake word listening — microphone active continuously "
            "(requires step-up consent)"
        ),
        "risk_level": "high",
        "destructive": False,
        "step_up_required": True,
    },

    # -------------------------------------------------------------------------
    # Talk mode (voice commands)
    # -------------------------------------------------------------------------

    "voice.talk.command": {
        "platform": "voice",
        "description": "Issue voice commands to control the browser agent",
        "risk_level": "medium",
        "destructive": False,
        "step_up_required": False,
    },

    "voice.talk.dictate": {
        "platform": "voice",
        "description": "Voice-to-text dictation into active form fields or editor",
        "risk_level": "low",
        "destructive": False,
        "step_up_required": False,
    },

    # -------------------------------------------------------------------------
    # Text-to-speech output
    # -------------------------------------------------------------------------

    "voice.tts.speak": {
        "platform": "voice",
        "description": "Text-to-speech output — agent speaks responses aloud",
        "risk_level": "low",
        "destructive": False,
        "step_up_required": False,
    },

    "voice.tts.persona": {
        "platform": "voice",
        "description": (
            "Custom TTS voice persona — override default system voice "
            "(requires step-up consent)"
        ),
        "risk_level": "high",
        "destructive": False,
        "step_up_required": True,
    },
}


# ---------------------------------------------------------------------------
# Derived constants for fast lookup
# ---------------------------------------------------------------------------

# All voice scope strings
VOICE_SCOPES: frozenset = frozenset(VOICE_SCOPE_REGISTRY.keys())

# Voice scopes that require step-up consent
VOICE_STEP_UP_SCOPES: frozenset = frozenset(
    scope
    for scope, meta in VOICE_SCOPE_REGISTRY.items()
    if meta.get("step_up_required", False)
)

# Voice scopes that are high-risk
VOICE_HIGH_RISK_SCOPES: frozenset = frozenset(
    scope
    for scope, meta in VOICE_SCOPE_REGISTRY.items()
    if meta["risk_level"] == "high"
)


# ---------------------------------------------------------------------------
# Registration hook — extends the main OAuth3 SCOPE_REGISTRY at import time
# ---------------------------------------------------------------------------

def register_voice_scopes() -> None:
    """
    Register voice scopes into the main OAuth3 SCOPE_REGISTRY and update
    all derived sets (HIGH_RISK_SCOPES, DESTRUCTIVE_SCOPES) across all modules
    that imported them.

    Called automatically on first import of this module.
    Idempotent: safe to call multiple times.

    Implementation note:
        frozensets are immutable, so we replace module-level names (not mutate).
        We update both oauth3.scopes AND oauth3.enforcement because enforcement.py
        imports HIGH_RISK_SCOPES by name at module load time and caches the binding.
        Replacing the module attribute in enforcement.py ensures the dynamic lookup
        inside enforce_oauth3() (which uses `scope in HIGH_RISK_SCOPES` at the
        module level) picks up the updated set.
    """
    import oauth3.scopes as _scopes_mod

    # Mutate SCOPE_REGISTRY dict in-place so validate_scopes() accepts voice scopes.
    # Also update _COMBINED_SCOPE_REGISTRY for legacy-aware lookups.
    for scope, meta in VOICE_SCOPE_REGISTRY.items():
        if scope not in _scopes_mod.SCOPE_REGISTRY:
            _scopes_mod.SCOPE_REGISTRY[scope] = meta
        # Keep _COMBINED_SCOPE_REGISTRY in sync
        if scope not in _scopes_mod._COMBINED_SCOPE_REGISTRY:
            _scopes_mod._COMBINED_SCOPE_REGISTRY[scope] = meta

    # Recompute derived frozensets from _COMBINED_SCOPE_REGISTRY (includes
    # legacy two-segment scopes like linkedin.delete_post, gmail.delete_email).
    new_high_risk = frozenset(
        s for s, m in _scopes_mod._COMBINED_SCOPE_REGISTRY.items() if m.get("risk_level") == "high"
    )
    new_destructive = frozenset(
        s for s, m in _scopes_mod._COMBINED_SCOPE_REGISTRY.items() if m.get("destructive", False)
    )

    # Update oauth3.scopes module-level names.
    _scopes_mod.HIGH_RISK_SCOPES = new_high_risk
    _scopes_mod.DESTRUCTIVE_SCOPES = new_destructive
    _scopes_mod.STEP_UP_REQUIRED_SCOPES = sorted(new_high_risk)
    _scopes_mod.ALL_SCOPES = frozenset(_scopes_mod.SCOPE_REGISTRY.keys())

    # Update oauth3.enforcement module-level HIGH_RISK_SCOPES binding so that
    # enforce_oauth3() sees the extended set (it uses `scope in HIGH_RISK_SCOPES`
    # referencing the module-level name directly).
    import oauth3.enforcement as _enforcement_mod
    _enforcement_mod.HIGH_RISK_SCOPES = new_high_risk


# ---------------------------------------------------------------------------
# Scope-level helpers
# ---------------------------------------------------------------------------

def is_voice_scope(scope: str) -> bool:
    """Return True if the scope belongs to the voice platform."""
    return scope in VOICE_SCOPE_REGISTRY


def voice_scope_requires_step_up(scope: str) -> bool:
    """
    Return True if this voice scope requires step-up consent.

    Fail-closed: unknown scopes return True.
    """
    entry = VOICE_SCOPE_REGISTRY.get(scope)
    if entry is None:
        return True  # fail-closed
    return entry.get("step_up_required", False)


def get_voice_scope_description(scope: str) -> str | None:
    """Return the human-readable description for a voice scope, or None."""
    entry = VOICE_SCOPE_REGISTRY.get(scope)
    return entry["description"] if entry else None


def get_required_scopes_for_action(action: str) -> List[str]:
    """
    Return the minimum voice scopes required for a given action name.

    action values:
      "wake_listen"  → ["voice.wake.listen"]
      "wake_always"  → ["voice.wake.listen", "voice.wake.always_on"]
      "talk_command" → ["voice.talk.command"]
      "talk_dictate" → ["voice.talk.dictate"]
      "tts_speak"    → ["voice.tts.speak"]
      "tts_persona"  → ["voice.tts.speak", "voice.tts.persona"]
      unknown        → [] (caller should treat as denied)
    """
    _action_map: Dict[str, List[str]] = {
        "wake_listen":  ["voice.wake.listen"],
        "wake_always":  ["voice.wake.listen", "voice.wake.always_on"],
        "talk_command": ["voice.talk.command"],
        "talk_dictate": ["voice.talk.dictate"],
        "tts_speak":    ["voice.tts.speak"],
        "tts_persona":  ["voice.tts.speak", "voice.tts.persona"],
    }
    return _action_map.get(action, [])


# ---------------------------------------------------------------------------
# Auto-register on import
# ---------------------------------------------------------------------------

register_voice_scopes()
