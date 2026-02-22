"""
voice — Hands-free browser control for Solace Browser

Provides wake word detection, talk mode voice commands, and TTS output,
all gated behind OAuth3 agency token scopes.

Modules:
  scopes  — Voice-specific OAuth3 scope definitions and registration
  wake    — WakeWordDetector + WakeConfig + AudioBuffer
  talk    — TalkMode + IntentParser + VoiceAction + ActionResult

Quick start:
    from voice.scopes import WAKE_SCOPE_LISTEN, TALK_SCOPE_COMMAND
    from voice.wake import WakeWordDetector, WakeConfig
    from voice.talk import TalkMode, IntentParser, VoiceAction

Rung: 641
"""

from voice.scopes import (
    VOICE_SCOPE_REGISTRY,
    VOICE_SCOPES,
    VOICE_STEP_UP_SCOPES,
    VOICE_HIGH_RISK_SCOPES,
    register_voice_scopes,
    is_voice_scope,
    voice_scope_requires_step_up,
)

from voice.wake import (
    WakeWordDetector,
    WakeConfig,
    AudioBuffer,
    AudioBackend,
    NoOpAudioBackend,
    WAKE_SCOPE_LISTEN,
    WAKE_SCOPE_ALWAYS_ON,
    MAX_BUFFER_SECONDS,
)

from voice.talk import (
    TalkMode,
    IntentParser,
    VoiceAction,
    ActionResult,
    RecipeExecutor,
    NoOpRecipeExecutor,
    TALK_SCOPE_COMMAND,
    AUTO_EXECUTE_THRESHOLD,
    SILENCE_TIMEOUT_SECONDS,
)

__all__ = [
    # scopes
    "VOICE_SCOPE_REGISTRY",
    "VOICE_SCOPES",
    "VOICE_STEP_UP_SCOPES",
    "VOICE_HIGH_RISK_SCOPES",
    "register_voice_scopes",
    "is_voice_scope",
    "voice_scope_requires_step_up",
    # wake
    "WakeWordDetector",
    "WakeConfig",
    "AudioBuffer",
    "AudioBackend",
    "NoOpAudioBackend",
    "WAKE_SCOPE_LISTEN",
    "WAKE_SCOPE_ALWAYS_ON",
    "MAX_BUFFER_SECONDS",
    # talk
    "TalkMode",
    "IntentParser",
    "VoiceAction",
    "ActionResult",
    "RecipeExecutor",
    "NoOpRecipeExecutor",
    "TALK_SCOPE_COMMAND",
    "AUTO_EXECUTE_THRESHOLD",
    "SILENCE_TIMEOUT_SECONDS",
]
