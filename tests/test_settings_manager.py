"""Tests for SettingsManager — hot-reload watcher for ~/.solace/settings.json.

Test structure:
  TestInit             (3 tests) — constructor, custom path, default path
  TestLoadAndGet       (5 tests) — load file, get key, get missing, get_all, nested
  TestReload           (4 tests) — force reload, reload updates values, reload fires callbacks,
                                   reload raises on missing file
  TestCallbackRegistry (5 tests) — register, multiple callbacks, unregister, unregister unknown,
                                   non-callable raises TypeError
  TestFileChangeDetect (4 tests) — detect mtime change, no change no callback, file created after
                                   start, file deleted during poll
  TestStartStop        (4 tests) — start/stop lifecycle, double start raises, stop idempotent,
                                   is_running property
  TestErrorPaths       (4 tests) — invalid JSON, non-dict JSON, missing file at start,
                                   callback exception logged not propagated
  TestThreadSafety     (2 tests) — concurrent get during reload, concurrent register

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_settings_manager.py -v --tb=short

Auth: 65537 | Rung: 641
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from settings_manager import SettingsLoadError, SettingsManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def settings_dir(tmp_path: Path) -> Path:
    """Create a temporary directory structure mimicking ~/.solace/."""
    solace_dir = tmp_path / ".solace"
    solace_dir.mkdir()
    return solace_dir


@pytest.fixture
def settings_file(settings_dir: Path) -> Path:
    """Create a valid settings.json in the temp .solace directory."""
    filepath = settings_dir / "settings.json"
    data = {
        "budget_limit": 100,
        "auth_token_ttl": 3600,
        "delight_enabled": True,
        "theme": "dark",
    }
    filepath.write_text(json.dumps(data), encoding="utf-8")
    return filepath


@pytest.fixture
def manager(settings_file: Path) -> SettingsManager:
    """Create a SettingsManager with a short poll interval for testing."""
    mgr = SettingsManager(settings_path=settings_file, poll_interval=0.1)
    yield mgr
    # Ensure cleanup
    if mgr.is_running:
        mgr.stop()


# ---------------------------------------------------------------------------
# TestInit
# ---------------------------------------------------------------------------


class TestInit:
    """Constructor and initialization tests."""

    def test_init_with_custom_path(self, settings_file: Path) -> None:
        """SettingsManager stores the resolved settings path."""
        mgr = SettingsManager(settings_path=settings_file)
        assert mgr.settings_path == settings_file.resolve()

    def test_init_default_poll_interval(self, settings_file: Path) -> None:
        """Default poll interval is 5.0 seconds."""
        mgr = SettingsManager(settings_path=settings_file)
        assert mgr._poll_interval == 5.0

    def test_init_custom_poll_interval(self, settings_file: Path) -> None:
        """Custom poll interval is respected."""
        mgr = SettingsManager(settings_path=settings_file, poll_interval=2.0)
        assert mgr._poll_interval == 2.0


# ---------------------------------------------------------------------------
# TestLoadAndGet
# ---------------------------------------------------------------------------


class TestLoadAndGet:
    """Loading settings and retrieving values."""

    def test_reload_loads_file(self, manager: SettingsManager) -> None:
        """reload() reads settings from disk."""
        result = manager.reload()
        assert result["budget_limit"] == 100
        assert result["theme"] == "dark"

    def test_get_existing_key(self, manager: SettingsManager) -> None:
        """get() returns the value for an existing key."""
        manager.reload()
        assert manager.get("budget_limit") == 100

    def test_get_missing_key_returns_default(self, manager: SettingsManager) -> None:
        """get() returns default for a missing key."""
        manager.reload()
        assert manager.get("nonexistent") is None
        assert manager.get("nonexistent", 42) == 42

    def test_get_all_returns_copy(self, manager: SettingsManager) -> None:
        """get_all() returns a copy of the settings dict."""
        manager.reload()
        all_settings = manager.get_all()
        assert all_settings["budget_limit"] == 100
        # Modifying the copy does not affect the manager
        all_settings["budget_limit"] = 999
        assert manager.get("budget_limit") == 100

    def test_get_nested_values(self, settings_dir: Path) -> None:
        """Settings with nested dicts are accessible."""
        filepath = settings_dir / "settings.json"
        data = {"database": {"host": "localhost", "port": 5432}}
        filepath.write_text(json.dumps(data), encoding="utf-8")
        mgr = SettingsManager(settings_path=filepath)
        result = mgr.reload()
        db = result["database"]
        assert db["host"] == "localhost"
        assert db["port"] == 5432


# ---------------------------------------------------------------------------
# TestReload
# ---------------------------------------------------------------------------


class TestReload:
    """Force reload behavior."""

    def test_reload_returns_settings(self, manager: SettingsManager) -> None:
        """reload() returns the newly loaded settings dict."""
        result = manager.reload()
        assert isinstance(result, dict)
        assert "budget_limit" in result

    def test_reload_updates_values(
        self, manager: SettingsManager, settings_file: Path
    ) -> None:
        """reload() picks up file changes."""
        manager.reload()
        assert manager.get("budget_limit") == 100

        # Update the file
        new_data = {"budget_limit": 200, "theme": "light"}
        settings_file.write_text(json.dumps(new_data), encoding="utf-8")

        manager.reload()
        assert manager.get("budget_limit") == 200
        assert manager.get("theme") == "light"

    def test_reload_fires_callbacks(self, manager: SettingsManager) -> None:
        """reload() invokes all registered callbacks."""
        received: list[dict[str, Any]] = []
        manager.register(lambda s: received.append(s))
        manager.reload()
        assert len(received) == 1
        assert received[0]["budget_limit"] == 100

    def test_reload_raises_on_missing_file(self, settings_dir: Path) -> None:
        """reload() raises FileNotFoundError when settings file is missing."""
        missing_path = settings_dir / "nonexistent.json"
        mgr = SettingsManager(settings_path=missing_path)
        with pytest.raises(FileNotFoundError):
            mgr.reload()


# ---------------------------------------------------------------------------
# TestCallbackRegistry
# ---------------------------------------------------------------------------


class TestCallbackRegistry:
    """Callback registration and unregistration."""

    def test_register_callback(self, manager: SettingsManager) -> None:
        """register() adds a callback."""
        callback = MagicMock()
        manager.register(callback)
        assert manager.callback_count == 1

    def test_register_multiple_callbacks(self, manager: SettingsManager) -> None:
        """Multiple callbacks can be registered."""
        cb1 = MagicMock()
        cb2 = MagicMock()
        cb3 = MagicMock()
        manager.register(cb1)
        manager.register(cb2)
        manager.register(cb3)
        assert manager.callback_count == 3

        manager.reload()
        cb1.assert_called_once()
        cb2.assert_called_once()
        cb3.assert_called_once()

    def test_unregister_callback(self, manager: SettingsManager) -> None:
        """unregister() removes a callback."""
        callback = MagicMock()
        manager.register(callback)
        assert manager.callback_count == 1

        result = manager.unregister(callback)
        assert result is True
        assert manager.callback_count == 0

        # Callback should not fire after unregister
        manager.reload()
        callback.assert_not_called()

    def test_unregister_unknown_callback(self, manager: SettingsManager) -> None:
        """unregister() returns False for an unregistered callback."""
        callback = MagicMock()
        result = manager.unregister(callback)
        assert result is False

    def test_register_non_callable_raises(self, manager: SettingsManager) -> None:
        """register() raises TypeError for non-callable."""
        with pytest.raises(TypeError, match="callback must be callable"):
            manager.register("not_a_function")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestFileChangeDetect
# ---------------------------------------------------------------------------


class TestFileChangeDetect:
    """File change detection via mtime polling."""

    def test_detect_mtime_change(
        self, manager: SettingsManager, settings_file: Path
    ) -> None:
        """Polling detects mtime changes and fires callbacks."""
        received: list[dict[str, Any]] = []
        manager.register(lambda s: received.append(dict(s)))
        manager.start()

        # Wait for initial settling
        time.sleep(0.2)
        initial_count = len(received)

        # Modify the file (ensure mtime changes)
        time.sleep(0.05)
        new_data = {"budget_limit": 500, "new_key": "new_value"}
        settings_file.write_text(json.dumps(new_data), encoding="utf-8")

        # Wait for poll to detect change
        time.sleep(0.5)
        manager.stop()

        assert len(received) > initial_count
        latest = received[-1]
        assert latest["budget_limit"] == 500
        assert latest["new_key"] == "new_value"

    def test_no_change_no_callback(
        self, manager: SettingsManager, settings_file: Path
    ) -> None:
        """No callbacks fire when the file has not changed."""
        callback = MagicMock()
        manager.register(callback)
        manager.start()

        # Wait a few poll cycles without changing the file
        time.sleep(0.4)
        manager.stop()

        # The callback should not have been called (initial load does not
        # fire callbacks via polling — only reload() fires them)
        callback.assert_not_called()

    def test_file_created_after_start(self, settings_dir: Path) -> None:
        """Polling picks up a newly created settings file."""
        filepath = settings_dir / "settings.json"
        # File does not exist yet
        mgr = SettingsManager(settings_path=filepath, poll_interval=0.1)
        received: list[dict[str, Any]] = []
        mgr.register(lambda s: received.append(dict(s)))
        mgr.start()

        time.sleep(0.2)
        assert len(received) == 0  # No file yet

        # Create the file
        data = {"created_after_start": True}
        filepath.write_text(json.dumps(data), encoding="utf-8")

        time.sleep(0.4)
        mgr.stop()

        # >= 1 because polling may fire multiple times before stop(); at least one is required
        assert len(received) >= 1
        assert received[-1]["created_after_start"] is True

    def test_file_deleted_during_poll(
        self, manager: SettingsManager, settings_file: Path
    ) -> None:
        """Deleting the settings file during polling does not crash."""
        manager.start()
        time.sleep(0.2)

        # Delete the file
        settings_file.unlink()

        # Polling should continue without crashing
        time.sleep(0.4)
        manager.stop()

        # After file deletion, manager retains cached settings from initial load
        assert manager.get("budget_limit") == 100  # Cached value persists


# ---------------------------------------------------------------------------
# TestStartStop
# ---------------------------------------------------------------------------


class TestStartStop:
    """Start/stop lifecycle management."""

    def test_start_stop_lifecycle(self, manager: SettingsManager) -> None:
        """Manager can be started and stopped cleanly."""
        assert not manager.is_running
        manager.start()
        assert manager.is_running
        manager.stop()
        assert not manager.is_running

    def test_double_start_raises(self, manager: SettingsManager) -> None:
        """Starting an already-running manager raises RuntimeError."""
        manager.start()
        with pytest.raises(RuntimeError, match="already running"):
            manager.start()
        manager.stop()

    def test_stop_idempotent(self, manager: SettingsManager) -> None:
        """Calling stop() when not running does nothing."""
        manager.stop()  # Should not raise
        manager.start()
        manager.stop()
        manager.stop()  # Second stop should not raise

    def test_is_running_property(self, manager: SettingsManager) -> None:
        """is_running reflects the actual thread state."""
        assert not manager.is_running
        manager.start()
        assert manager.is_running
        manager.stop()
        assert not manager.is_running


# ---------------------------------------------------------------------------
# TestErrorPaths
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """Error handling for invalid files and callback failures."""

    def test_invalid_json_raises_on_reload(
        self, settings_dir: Path
    ) -> None:
        """reload() raises json.JSONDecodeError for invalid JSON."""
        filepath = settings_dir / "settings.json"
        filepath.write_text("{invalid json", encoding="utf-8")
        mgr = SettingsManager(settings_path=filepath)
        with pytest.raises(json.JSONDecodeError):
            mgr.reload()

    def test_non_dict_json_raises_on_reload(
        self, settings_dir: Path
    ) -> None:
        """reload() raises SettingsLoadError when JSON is not a dict."""
        filepath = settings_dir / "settings.json"
        filepath.write_text("[1, 2, 3]", encoding="utf-8")
        mgr = SettingsManager(settings_path=filepath)
        with pytest.raises(SettingsLoadError, match="must be a JSON object"):
            mgr.reload()

    def test_missing_file_at_start_continues(self, settings_dir: Path) -> None:
        """start() succeeds even when the settings file does not exist yet."""
        missing_path = settings_dir / "nonexistent.json"
        mgr = SettingsManager(settings_path=missing_path, poll_interval=0.1)
        mgr.start()  # Should not raise
        assert mgr.is_running
        assert mgr.get_all() == {}
        mgr.stop()

    def test_callback_exception_does_not_crash(
        self, manager: SettingsManager
    ) -> None:
        """A failing callback does not prevent other callbacks from running."""
        results: list[str] = []

        def good_callback_1(settings: dict[str, Any]) -> None:
            results.append("cb1")

        def bad_callback(settings: dict[str, Any]) -> None:
            raise ValueError("intentional test error")

        def good_callback_2(settings: dict[str, Any]) -> None:
            results.append("cb2")

        manager.register(good_callback_1)
        manager.register(bad_callback)
        manager.register(good_callback_2)

        manager.reload()

        # Both good callbacks should have run despite the bad one
        assert "cb1" in results
        assert "cb2" in results


# ---------------------------------------------------------------------------
# TestThreadSafety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """Thread-safety of concurrent operations."""

    def test_concurrent_get_during_reload(
        self, manager: SettingsManager, settings_file: Path
    ) -> None:
        """get() is safe to call while reload() is running."""
        manager.reload()
        errors: list[str] = []
        stop = threading.Event()

        def reader() -> None:
            while not stop.is_set():
                try:
                    manager.get("budget_limit")
                    manager.get_all()
                except RuntimeError as exc:
                    errors.append(str(exc))

        threads = [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()

        # Do multiple reloads while readers are active
        for i in range(10):
            new_data = {"budget_limit": i, "iteration": i}
            settings_file.write_text(json.dumps(new_data), encoding="utf-8")
            manager.reload()

        stop.set()
        for t in threads:
            t.join(timeout=2.0)

        assert len(errors) == 0

    def test_concurrent_register(self, manager: SettingsManager) -> None:
        """register() is safe to call from multiple threads."""
        errors: list[str] = []

        def registerer(idx: int) -> None:
            try:
                manager.register(lambda s, i=idx: None)
            except RuntimeError as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=registerer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        assert len(errors) == 0
        assert manager.callback_count == 20


# ---------------------------------------------------------------------------
# TestCallbackOrder
# ---------------------------------------------------------------------------


class TestCallbackOrder:
    """Callbacks fire in registration order."""

    def test_callbacks_fire_in_order(self, manager: SettingsManager) -> None:
        """Callbacks are invoked in the order they were registered."""
        order: list[int] = []
        for i in range(5):
            manager.register(lambda s, idx=i: order.append(idx))

        manager.reload()
        assert order == [0, 1, 2, 3, 4]
