"""
voice/wake.py — Wake Word Detector

Hands-free activation for the Solace Browser voice pipeline.

Responsibilities:
  - Listen for a configurable wake word (default: "solace")
  - Gate microphone access behind OAuth3 scope voice.wake.listen
  - Require step-up auth for persistent (always-on) listening
  - Buffer at most 30 seconds of audio; auto-purge after processing
  - Never store or transmit raw audio — only transcribed text after wake word
  - Register callbacks invoked when the wake word is detected

Architecture note:
  The actual audio capture / ASR engine is injected via AudioBackend.
  The default NoOpAudioBackend is a safe stub used in tests and CI.
  Production implementations plug in a real microphone interface by
  subclassing AudioBackend and passing it to WakeWordDetector.

OAuth3 scope requirements:
  voice.wake.listen     — required to start listening
  voice.wake.always_on  — additionally required for persistent mode (step-up)

All voice scope definitions live in voice.scopes.

Rung: 641
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from oauth3.token import AgencyToken
from oauth3.enforcement import enforce_oauth3

# Ensure voice scopes are registered into the main scope registry
import voice.scopes as _voice_scopes  # noqa: F401 (side-effect: registration)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WAKE_SCOPE_LISTEN = "voice.wake.listen"
WAKE_SCOPE_ALWAYS_ON = "voice.wake.always_on"

# Audio buffer policy (spec: max 30 seconds retention)
MAX_BUFFER_SECONDS: int = 30

# Default wake word
DEFAULT_WAKE_WORD = "solace"

# Sensitivity bounds
SENSITIVITY_MIN = 0.0
SENSITIVITY_MAX = 1.0
SENSITIVITY_DEFAULT = 0.5

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WakeConfig — configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class WakeConfig:
    """
    Configuration for wake word detection.

    Attributes:
        wake_word:        The phrase to listen for (case-insensitive). Default: "solace".
        sensitivity:      Detection sensitivity in [0.0, 1.0].
                          Higher → fewer misses, more false positives.
                          Lower  → fewer false positives, more misses.
                          Default: 0.5.
        timeout_seconds:  After activation, how many seconds of silence before
                          auto-deactivation. 0 means never time out. Default: 60.
        language:         BCP-47 language tag for speech recognition. Default: "en-US".
        always_on:        If True, microphone stays active permanently.
                          Requires OAuth3 scope voice.wake.always_on (step-up).
                          Default: False.
    """

    wake_word: str = DEFAULT_WAKE_WORD
    sensitivity: float = SENSITIVITY_DEFAULT
    timeout_seconds: int = 60
    language: str = "en-US"
    always_on: bool = False

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not isinstance(self.wake_word, str) or not self.wake_word.strip():
            raise ValueError("wake_word must be a non-empty string.")
        if not (SENSITIVITY_MIN <= self.sensitivity <= SENSITIVITY_MAX):
            raise ValueError(
                f"sensitivity must be in [{SENSITIVITY_MIN}, {SENSITIVITY_MAX}], "
                f"got {self.sensitivity}."
            )
        if not isinstance(self.timeout_seconds, int) or self.timeout_seconds < 0:
            raise ValueError("timeout_seconds must be a non-negative integer.")
        if not isinstance(self.language, str) or not self.language.strip():
            raise ValueError("language must be a non-empty BCP-47 string.")


# ---------------------------------------------------------------------------
# AudioBackend — pluggable audio interface (dependency injection)
# ---------------------------------------------------------------------------

class AudioBackend:
    """
    Abstract audio capture interface.

    Subclass this to provide real microphone access.
    The default implementation (NoOpAudioBackend) is a safe stub.
    """

    def start(self) -> None:
        """Begin audio capture."""

    def stop(self) -> None:
        """Stop audio capture and release hardware resources."""

    def read_chunk(self) -> Optional[bytes]:
        """
        Return the next audio chunk, or None if no data is available.

        Called in a tight loop by WakeWordDetector._listen_loop().
        Must not block for more than ~100 ms.
        """
        return None

    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Convert a raw audio chunk to text.

        Production implementations call a local ASR engine.
        Must NOT send audio to any cloud service — local-only requirement.

        Returns:
            Transcribed text string (possibly empty on silence or error).
        """
        return ""


class NoOpAudioBackend(AudioBackend):
    """
    Safe no-op stub used in tests and CI.
    Never opens a microphone or makes network calls.
    """

    def __init__(self) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def read_chunk(self) -> Optional[bytes]:
        # Return None so the listen loop idles without blocking
        return None

    def transcribe(self, audio_bytes: bytes) -> str:
        return ""


# ---------------------------------------------------------------------------
# AudioBuffer — bounded rolling buffer with auto-purge
# ---------------------------------------------------------------------------

class AudioBuffer:
    """
    Thread-safe audio buffer with a hard cap of MAX_BUFFER_SECONDS.

    Chunks are appended with a creation timestamp.
    purge() removes all chunks older than MAX_BUFFER_SECONDS.
    clear() drops all data immediately (called after wake word processing).

    No raw audio is stored beyond MAX_BUFFER_SECONDS at any time.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # List of (timestamp_float, audio_bytes)
        self._chunks: List[tuple] = []

    # ------------------------------------------------------------------

    def append(self, audio_bytes: bytes) -> None:
        """Append a chunk to the buffer and auto-purge stale data."""
        with self._lock:
            self._chunks.append((time.monotonic(), audio_bytes))
            self._purge_locked()

    def clear(self) -> None:
        """Drop all buffered audio (called after wake word detected)."""
        with self._lock:
            self._chunks.clear()

    def purge(self) -> None:
        """Remove chunks older than MAX_BUFFER_SECONDS."""
        with self._lock:
            self._purge_locked()

    def size(self) -> int:
        """Return number of buffered chunks."""
        with self._lock:
            return len(self._chunks)

    def total_bytes(self) -> int:
        """Return total bytes currently in the buffer."""
        with self._lock:
            return sum(len(chunk) for _, chunk in self._chunks)

    # ------------------------------------------------------------------
    # Internal (must be called with _lock held)

    def _purge_locked(self) -> None:
        cutoff = time.monotonic() - MAX_BUFFER_SECONDS
        self._chunks = [
            (ts, data) for ts, data in self._chunks if ts >= cutoff
        ]


# ---------------------------------------------------------------------------
# WakeWordDetector — main class
# ---------------------------------------------------------------------------

class WakeWordDetector:
    """
    Detects a configurable wake word and fires registered callbacks.

    Usage:
        config  = WakeConfig(wake_word="solace", sensitivity=0.7)
        token   = AgencyToken.create(scopes=["voice.wake.listen"], ...)
        detector = WakeWordDetector(config=config, token=token)
        detector.on_wake(lambda: print("Wake word detected!"))
        detector.start_listening()
        ...
        detector.stop_listening()

    OAuth3 requirements:
        voice.wake.listen   — required to start any listening.
        voice.wake.always_on — additionally required when config.always_on=True.

    Security:
        - Raw audio never persisted or transmitted.
        - Buffer auto-purges to MAX_BUFFER_SECONDS = 30 s.
        - Buffer is cleared immediately after wake word processing.
    """

    def __init__(
        self,
        config: Optional[WakeConfig] = None,
        token: Optional[AgencyToken] = None,
        backend: Optional[AudioBackend] = None,
    ) -> None:
        self._config = config or WakeConfig()
        self._token = token
        self._backend = backend or NoOpAudioBackend()
        self._buffer = AudioBuffer()
        self._callbacks: List[Callable[[], None]] = []
        self._lock = threading.Lock()
        self._listening = False
        self._thread: Optional[threading.Thread] = None
        # Audit log of wake events (text only, no audio)
        self._wake_log: List[dict] = []

    # ------------------------------------------------------------------
    # Callback registration

    def on_wake(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to invoke when the wake word is detected.

        Multiple callbacks may be registered; all are called in order.

        Args:
            callback: Zero-argument callable.
        """
        if not callable(callback):
            raise TypeError("callback must be callable.")
        with self._lock:
            self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # Lifecycle

    def start_listening(
        self,
        step_up_nonce: Optional[str] = None,
    ) -> None:
        """
        Begin wake word detection.

        OAuth3 gate:
          - voice.wake.listen is always required.
          - voice.wake.always_on additionally required (with step-up) when
            config.always_on is True.

        Args:
            step_up_nonce: Step-up nonce for always_on mode (required when
                           config.always_on=True).

        Raises:
            PermissionError: If OAuth3 gate fails (missing scope, expired token,
                             revoked token, or step-up required but not provided).
            RuntimeError:    If already listening.
        """
        with self._lock:
            if self._listening:
                raise RuntimeError("WakeWordDetector is already listening.")

        # OAuth3 gate — voice.wake.listen
        self._enforce_scope(WAKE_SCOPE_LISTEN, step_up_confirmed=False)

        # Always-on requires additional scope + step-up
        if self._config.always_on:
            self._enforce_scope(
                WAKE_SCOPE_ALWAYS_ON,
                step_up_confirmed=(step_up_nonce is not None),
            )

        # Start backend
        self._backend.start()

        with self._lock:
            self._listening = True

        # Spawn listener thread
        self._thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name="WakeWordDetector-listener",
        )
        self._thread.start()

    def stop_listening(self) -> None:
        """
        Stop wake word detection and release the audio backend.

        Safe to call even when not currently listening (no-op).
        Blocks until the listener thread exits.
        """
        with self._lock:
            if not self._listening:
                return
            self._listening = False

        self._backend.stop()
        self._buffer.clear()  # Purge remaining audio on stop

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    @property
    def is_listening(self) -> bool:
        """Return True if currently listening."""
        with self._lock:
            return self._listening

    # ------------------------------------------------------------------
    # Internal

    def _enforce_scope(
        self,
        scope: str,
        step_up_confirmed: bool = False,
    ) -> None:
        """
        Run the OAuth3 enforcement gate for the given scope.

        Raises:
            PermissionError: If the gate fails for any reason.
        """
        if self._token is None:
            raise PermissionError(
                f"OAuth3 scope '{scope}' required but no token provided."
            )
        passed, details = enforce_oauth3(
            self._token,
            required_scope=scope,
            step_up_confirmed=step_up_confirmed,
        )
        if not passed:
            error = details.get("error", "unknown_error")
            raise PermissionError(
                f"OAuth3 gate denied for scope '{scope}': {error}. "
                f"Details: {details}"
            )

    def _listen_loop(self) -> None:
        """
        Main listener thread: reads chunks, transcribes, matches wake word.

        Runs until _listening is set to False.
        Periodically purges the buffer to enforce the 30-second retention cap.
        """
        while True:
            with self._lock:
                if not self._listening:
                    break

            chunk = self._backend.read_chunk()
            if chunk is None:
                # No audio available; small sleep to avoid busy-spin
                time.sleep(0.05)
                # Purge stale audio on idle cycles
                self._buffer.purge()
                continue

            # Append chunk to rolling buffer
            self._buffer.append(chunk)

            # Transcribe the chunk (local only, no cloud)
            text = self._backend.transcribe(chunk)
            if text:
                self._check_wake_word(text)

    def _check_wake_word(self, text: str) -> None:
        """
        Compare transcribed text against the configured wake word.

        If matched: log event, clear buffer, fire callbacks.
        Matching is case-insensitive and tolerates surrounding words.
        """
        normalized_text = text.strip().lower()
        wake_word_lower = self._config.wake_word.strip().lower()

        if wake_word_lower in normalized_text:
            # Purge buffer immediately — no raw audio retained after detection
            self._buffer.clear()
            self._log_wake_event(text)
            self._fire_callbacks()

    def _log_wake_event(self, matched_text: str) -> None:
        """Append a text-only entry to the wake event log."""
        entry = {
            "event": "wake_detected",
            "wake_word": self._config.wake_word,
            "matched_text": matched_text,
            "timestamp": time.time(),
        }
        self._wake_log.append(entry)

    def _fire_callbacks(self) -> None:
        """Invoke all registered on-wake callbacks in registration order."""
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb()
            except (RuntimeError, TypeError, ValueError) as exc:
                logger.warning("Wake callback failed: %s", exc)

    # ------------------------------------------------------------------
    # Introspection (for tests)

    @property
    def wake_log(self) -> List[dict]:
        """Read-only list of wake event log entries (text only)."""
        return list(self._wake_log)

    @property
    def buffer(self) -> AudioBuffer:
        """Expose audio buffer for testing / introspection."""
        return self._buffer
