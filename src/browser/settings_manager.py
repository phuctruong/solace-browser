# Diagram: 01-triangle-architecture
"""SettingsManager — hot-reload watcher for ~/.solace/settings.json.

Watches the settings file for changes using mtime polling (every 5 seconds
by default). When a change is detected, re-reads the file and emits
settings_changed callbacks to all registered modules.

Modules that use hot-reload:
  - budget_gates: limit values
  - auth_proxy: token configuration
  - delight_engine: content preferences

Design rules:
  - Thread-safe: uses threading.Lock for callback list and settings dict
  - Background thread: daemon=True, stopped cleanly via Event
  - GRACEFUL START: missing or malformed settings file logs a warning and starts with empty settings
  - Specific exceptions only: FileNotFoundError, json.JSONDecodeError
  - pathlib.Path always, never os.path.join

Channel [7] — Context + Tools.  Rung: 641.
DNA: settings(watch, reload, emit) → {key, value} → hot-reload
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("solace-browser.settings_manager")

# Default settings file location
_DEFAULT_SETTINGS_PATH = Path("~/.solace/settings.json").expanduser()

# Default poll interval in seconds
_DEFAULT_POLL_INTERVAL = 5.0

# Default settings values — merged under user settings so get() always returns
# a sensible value even when the key is absent from settings.json.
_DEFAULT_SETTINGS: dict[str, Any] = {
    "font_size": "medium",
    "theme": "dark",
    "reduced_motion": False,
    "high_contrast": False,
}

# Schema for constrained settings keys.  Maps key → list of allowed values.
# Boolean keys are not listed here (any bool is valid).
_SETTINGS_SCHEMA: dict[str, list[str]] = {
    "font_size": ["small", "medium", "large", "xlarge"],
    "theme": ["dark", "light", "midnight"],
}


class SettingsLoadError(ValueError):
    """Raised when settings.json cannot be parsed as a valid JSON object."""


class SettingsManager:
    """Hot-reload settings manager with file-change detection via mtime polling.

    Watches ``~/.solace/settings.json`` (or a custom path) for modifications
    and notifies registered callbacks when the file changes.

    Usage:
        manager = SettingsManager(settings_path=Path("~/.solace/settings.json"))
        manager.register(lambda settings: print("Changed!", settings))
        manager.start()   # starts background polling thread
        # ... later ...
        manager.stop()    # stops background polling thread

    Thread-safety:
        All public methods are thread-safe. The internal settings dict and
        callback list are guarded by a threading.Lock.

    Args:
        settings_path: Path to the settings JSON file.
        poll_interval: Seconds between mtime checks (default 5.0).
    """

    def __init__(
        self,
        settings_path: Path | None = None,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
    ) -> None:
        self._settings_path = (
            Path(settings_path).expanduser().resolve()
            if settings_path is not None
            else _DEFAULT_SETTINGS_PATH.resolve()
        )
        self._poll_interval = poll_interval

        # Thread-safety lock for _settings, _callbacks, and _last_mtime
        self._lock = threading.Lock()

        # Current settings snapshot (seeded with defaults)
        self._settings: dict[str, Any] = dict(_DEFAULT_SETTINGS)

        # Registered callbacks
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []

        # Last known mtime (None = never loaded)
        self._last_mtime: float | None = None

        # Background thread control
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback to be invoked when settings change.

        The callback receives the full settings dict as its argument.
        Callbacks are invoked in registration order from the polling thread.

        Args:
            callback: A callable accepting a single dict argument.

        Raises:
            TypeError: If callback is not callable.
        """
        if not callable(callback):
            raise TypeError(f"callback must be callable, got {type(callback).__name__}")
        with self._lock:
            self._callbacks.append(callback)

    def unregister(self, callback: Callable[[dict[str, Any]], None]) -> bool:
        """Remove a previously registered callback.

        Args:
            callback: The callback to remove.

        Returns:
            True if the callback was found and removed, False otherwise.
        """
        with self._lock:
            try:
                self._callbacks.remove(callback)
                return True
            except ValueError:
                return False

    def start(self) -> None:
        """Start the background polling thread.

        The thread checks the settings file mtime every ``poll_interval``
        seconds. If the mtime has changed, the file is re-read and all
        registered callbacks are invoked.

        Performs an initial load of the settings file before starting
        the polling loop. If the file does not exist, the initial load
        is skipped (settings remain empty) and polling continues.

        Raises:
            RuntimeError: If the polling thread is already running.
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Settings polling thread is already running.")

        # Initial load (non-fatal if file missing)
        self._initial_load()

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="settings-manager-poll",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Settings manager started, watching %s (poll every %.1fs)",
            self._settings_path,
            self._poll_interval,
        )

    def stop(self) -> None:
        """Stop the background polling thread.

        Blocks until the thread has finished (up to poll_interval + 1s).
        Does nothing if the thread is not running.
        """
        if self._thread is None:
            return

        self._stop_event.set()
        self._thread.join(timeout=self._poll_interval + 1.0)
        if self._thread.is_alive():
            logger.error(
                "Settings polling thread did not stop within timeout; thread may be leaked"
            )
        self._thread = None
        logger.info("Settings manager stopped.")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a settings value by key.

        Thread-safe: reads from the current in-memory snapshot.

        Args:
            key: The settings key to look up.
            default: Value to return if key is not found.

        Returns:
            The value for the key, or default if not found.
        """
        with self._lock:
            return self._settings.get(key, default)

    def get_all(self) -> dict[str, Any]:
        """Get a copy of all current settings.

        Thread-safe: returns a shallow copy of the settings dict.

        Returns:
            A dict containing all current settings.
        """
        with self._lock:
            return dict(self._settings)

    def set(self, key: str, value: Any) -> None:
        """Set a settings value by key, persist to disk, and notify callbacks.

        Validates constrained keys (font_size, theme) against ``_SETTINGS_SCHEMA``.
        Boolean keys (reduced_motion, high_contrast) must receive a bool value.

        Thread-safe: updates the in-memory snapshot under lock, then writes to disk.

        Args:
            key: The settings key to update.
            value: The new value.

        Raises:
            ValueError: If the value is not allowed for a constrained key.
            TypeError: If a boolean key receives a non-bool value.
        """
        # Validate constrained string keys
        if key in _SETTINGS_SCHEMA:
            allowed = _SETTINGS_SCHEMA[key]
            if value not in allowed:
                raise ValueError(
                    f"Invalid value {value!r} for {key!r}. "
                    f"Allowed: {allowed}"
                )

        # Validate boolean keys from defaults
        if key in _DEFAULT_SETTINGS and isinstance(_DEFAULT_SETTINGS[key], bool):
            if not isinstance(value, bool):
                raise TypeError(
                    f"{key!r} must be a bool, got {type(value).__name__}"
                )

        with self._lock:
            self._settings[key] = value
            snapshot = dict(self._settings)
            callbacks = list(self._callbacks)

        # Persist to disk
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        # Update mtime tracker so the polling thread does not double-fire
        mtime = self._get_mtime()
        with self._lock:
            self._last_mtime = mtime

        self._fire_callbacks(callbacks, snapshot)

    def reload(self) -> dict[str, Any]:
        """Force reload settings from disk and notify callbacks.

        Reads the file, updates the in-memory settings, updates the
        mtime tracker, and invokes all registered callbacks.

        Returns:
            The newly loaded settings dict.

        Raises:
            FileNotFoundError: If the settings file does not exist.
            SettingsLoadError: If the file is not valid JSON or not a dict.
        """
        settings = self._read_settings_file()
        mtime = self._get_mtime()

        with self._lock:
            self._settings = settings
            self._last_mtime = mtime
            callbacks = list(self._callbacks)

        self._fire_callbacks(callbacks, settings)
        return dict(settings)

    @property
    def is_running(self) -> bool:
        """True if the background polling thread is currently running."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def settings_path(self) -> Path:
        """The resolved path to the settings file being watched."""
        return self._settings_path

    @property
    def callback_count(self) -> int:
        """Number of registered callbacks."""
        with self._lock:
            return len(self._callbacks)

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _initial_load(self) -> None:
        """Load settings on startup. Non-fatal if file is missing."""
        try:
            settings = self._read_settings_file()
            mtime = self._get_mtime()
            with self._lock:
                self._settings = settings
                self._last_mtime = mtime
            logger.info("Initial settings loaded from %s", self._settings_path)
        except FileNotFoundError:
            logger.info(
                "Settings file not found at %s, starting with empty settings",
                self._settings_path,
            )
        except (json.JSONDecodeError, SettingsLoadError) as exc:
            logger.warning(
                "Failed to parse settings file %s on startup: %s",
                self._settings_path,
                exc,
            )

    def _poll_loop(self) -> None:
        """Background polling loop. Checks mtime and reloads on change."""
        while not self._stop_event.is_set():
            try:
                self._check_for_changes()
            except FileNotFoundError:
                logger.debug(
                    "Settings file not found during poll: %s",
                    self._settings_path,
                )
            except (json.JSONDecodeError, SettingsLoadError) as exc:
                logger.warning(
                    "Failed to parse settings during poll: %s", exc
                )

            # Wait for stop_event or poll_interval, whichever comes first
            self._stop_event.wait(timeout=self._poll_interval)

    def _check_for_changes(self) -> None:
        """Check if the settings file has been modified and reload if so.

        Compares the current mtime to the last known mtime. If different,
        reloads the file and fires callbacks.

        Raises:
            FileNotFoundError: If the settings file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            SettingsLoadError: If the file content is not a JSON object.
        """
        current_mtime = self._get_mtime()

        with self._lock:
            last_mtime = self._last_mtime

        if current_mtime != last_mtime:
            settings = self._read_settings_file()
            with self._lock:
                self._settings = settings
                self._last_mtime = current_mtime
                callbacks = list(self._callbacks)

            logger.info("Settings changed, notifying %d callbacks", len(callbacks))
            self._fire_callbacks(callbacks, settings)

    def _read_settings_file(self) -> dict[str, Any]:
        """Read and parse the settings JSON file.

        Returns:
            Parsed settings as a dict.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            SettingsLoadError: If the parsed content is not a dict.
        """
        raw = self._settings_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise SettingsLoadError(
                f"settings.json must be a JSON object, got {type(parsed).__name__}"
            )
        # Merge defaults under user-supplied values so every default key is present.
        merged = dict(_DEFAULT_SETTINGS)
        merged.update(parsed)
        return merged

    def _get_mtime(self) -> float | None:
        """Get the modification time of the settings file.

        Returns:
            The file's mtime as a float, or None if the file does not exist.
        """
        try:
            return self._settings_path.stat().st_mtime
        except FileNotFoundError:
            logger.warning("Settings file not found: %s", self._settings_path)
            return None

    def _fire_callbacks(
        self,
        callbacks: list[Callable[[dict[str, Any]], None]],
        settings: dict[str, Any],
    ) -> None:
        """Invoke all callbacks with the new settings dict.

        Each callback is invoked individually. If a callback raises,
        the exception is logged and remaining callbacks still execute.
        """
        for callback in callbacks:
            try:
                callback(settings)
            except (TypeError, ValueError, KeyError, AttributeError, OSError) as exc:
                logger.error(
                    "Callback %s raised %s: %s",
                    getattr(callback, '__name__', callback),
                    type(exc).__name__,
                    exc,
                )
