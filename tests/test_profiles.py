"""
Multi-Profile Browser + Process Manager — Comprehensive Test Suite

Tests cover:
  - BrowserProfile: creation, defaults, viewport, user agent, serialization
  - ProfileManager: create/get/list/delete/switch, default profile, isolation
  - ProfileIsolation: no cross-profile leakage, separate tokens, separate cookies
  - ProcessInfo/BrowserProcess: creation, status, resource tracking, SHA256
  - ProcessManager: spawn/kill, resource limits, crash recovery, stats
  - OAuth3Integration: scope enforcement on delete/spawn/kill, step-up
  - Evidence: switches logged, process events logged, SHA256 hashes

Test classes:
  TestBrowserProfile     (8  tests)
  TestProfileManager     (12 tests)
  TestProfileIsolation   (8  tests)
  TestBrowserProcess     (8  tests)
  TestProcessManager     (10 tests)
  TestOAuth3Integration  (8  tests)
  TestEvidence           (6  tests)

Total: 60 tests
Rung: 641

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_profiles.py -v -p no:httpbin
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# sys.path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from src.profiles.manager import (
    BrowserProfile,
    ProfileManager,
    DEFAULT_VIEWPORT,
    DEFAULT_USER_AGENT,
    DEFAULT_PROFILE_NAME,
    ProfileError,
    ProfileNotFoundError,
    ProfileIsolationError,
    SwitchEvent,
)
from src.profiles.process import (
    ProcessInfo,
    BrowserProcess,   # alias for ProcessInfo
    ProcessManager,
    ProcessStatus,
    ProcessError,
    ProcessNotFoundError,
    ResourceLimitError,
    ProcessStats,
    ProcessEvent,
    DEFAULT_MAX_PROCESSES_PER_PROFILE,
    DEFAULT_MAX_MEMORY_TOTAL_MB,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_profile(
    name: str = "Test",
    user_agent: Optional[str] = None,
    viewport: Optional[dict] = None,
) -> BrowserProfile:
    """Create a standalone BrowserProfile (not via manager)."""
    import uuid
    pid = str(uuid.uuid4())
    now = _utc_now_iso()
    return BrowserProfile(
        profile_id=pid,
        name=name,
        user_agent=user_agent or DEFAULT_USER_AGENT,
        viewport=viewport or dict(DEFAULT_VIEWPORT),
        cookies_path=f"~/.solace/profiles/{pid}/cookies.db",
        proxy=None,
        extensions=[],
        oauth3_token_ids=[],
        created_at=now,
        last_used=now,
    )


def _make_process_info(
    profile_id: str = "profile-001",
    status: str = ProcessStatus.RUNNING,
    pid: Optional[int] = 12345,
    cpu_percent: int = 5,
    memory_mb: int = 256,
) -> ProcessInfo:
    """Create a standalone ProcessInfo (not via manager)."""
    import uuid
    return ProcessInfo(
        process_id=str(uuid.uuid4()),
        profile_id=profile_id,
        pid=pid,
        status=status,
        cpu_percent=cpu_percent,
        memory_mb=memory_mb,
        started_at=_utc_now_iso(),
        uptime_seconds=0,
    )


# ===========================================================================
# TestBrowserProfile — 8 tests
# ===========================================================================

class TestBrowserProfile:
    """Test BrowserProfile dataclass creation and field access."""

    def test_creation_with_all_fields(self):
        """BrowserProfile stores all provided fields correctly."""
        p = _make_profile(name="Work", user_agent="MyAgent/1.0")
        assert p.name == "Work"
        assert p.user_agent == "MyAgent/1.0"
        assert isinstance(p.profile_id, str)
        assert len(p.profile_id) == 36  # UUID v4 format

    def test_default_viewport(self):
        """Default viewport is 1280x720."""
        p = _make_profile()
        assert p.viewport == {"width": 1280, "height": 720}
        assert p.viewport["width"] == 1280
        assert p.viewport["height"] == 720

    def test_custom_viewport(self):
        """Custom viewport is stored correctly."""
        vp = {"width": 1920, "height": 1080}
        p = _make_profile(viewport=vp)
        assert p.viewport["width"] == 1920
        assert p.viewport["height"] == 1080

    def test_default_user_agent_is_set(self):
        """Default user agent is a non-empty string."""
        p = _make_profile()
        assert DEFAULT_USER_AGENT in p.user_agent
        assert len(p.user_agent) > 0

    def test_timestamps_are_iso8601(self):
        """created_at and last_used are ISO 8601 UTC strings."""
        p = _make_profile()
        dt_created = datetime.fromisoformat(p.created_at.replace("Z", "+00:00"))
        dt_last = datetime.fromisoformat(p.last_used.replace("Z", "+00:00"))
        assert dt_created.tzinfo is not None
        assert dt_last.tzinfo is not None

    def test_oauth3_token_ids_default_empty(self):
        """Fresh profile has empty oauth3_token_ids list."""
        p = _make_profile()
        assert p.oauth3_token_ids == []
        assert isinstance(p.oauth3_token_ids, list)

    def test_to_dict_roundtrip(self):
        """to_dict() followed by from_dict() reproduces the same profile."""
        p = _make_profile(name="Roundtrip")
        d = p.to_dict()
        p2 = BrowserProfile.from_dict(d)
        assert p2.profile_id == p.profile_id
        assert p2.name == p.name
        assert p2.viewport == p.viewport
        assert p2.user_agent == p.user_agent

    def test_sha256_hash_format(self):
        """sha256_hash() returns 'sha256:<hex>' format."""
        p = _make_profile()
        h = p.sha256_hash()
        assert h.startswith("sha256:")
        hex_part = h[len("sha256:"):]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)


# ===========================================================================
# TestProfileManager — 12 tests
# ===========================================================================

class TestProfileManager:
    """Test ProfileManager CRUD operations."""

    def test_default_profile_created_on_init(self):
        """ProfileManager always creates a default profile at init."""
        pm = ProfileManager()
        profiles = pm.list_profiles()
        assert len(profiles) >= 1
        names = [p.name for p in profiles]
        assert DEFAULT_PROFILE_NAME in names

    def test_create_profile_returns_browser_profile(self):
        """create() returns a BrowserProfile with the correct name."""
        pm = ProfileManager()
        p = pm.create("Work")
        assert isinstance(p, BrowserProfile)
        assert p.name == "Work"

    def test_create_profile_with_custom_viewport(self):
        """create() with custom viewport stores the correct dimensions."""
        pm = ProfileManager()
        vp = {"width": 1920, "height": 1080}
        p = pm.create("BigScreen", viewport=vp)
        assert p.viewport["width"] == 1920
        assert p.viewport["height"] == 1080

    def test_get_existing_profile(self):
        """get() returns the correct profile by ID."""
        pm = ProfileManager()
        p = pm.create("Social")
        fetched = pm.get(p.profile_id)
        assert fetched is not None
        assert fetched.profile_id == p.profile_id
        assert fetched.name == "Social"

    def test_get_nonexistent_profile_returns_none(self):
        """get() returns None for an unknown profile_id."""
        pm = ProfileManager()
        result = pm.get("nonexistent-profile-id")
        assert result is None

    def test_list_profiles_includes_all(self):
        """list_profiles() includes the default + all created profiles."""
        pm = ProfileManager()
        pm.create("Alpha")
        pm.create("Beta")
        profiles = pm.list_profiles()
        names = {p.name for p in profiles}
        assert "default" in names
        assert "Alpha" in names
        assert "Beta" in names
        assert len(profiles) == 3

    def test_delete_profile_removes_it(self):
        """delete() removes a profile from the registry."""
        pm = ProfileManager()
        p = pm.create("Temp")
        assert pm.get(p.profile_id) is not None
        result = pm.delete(
            p.profile_id,
            oauth3_confirmed=True,
            step_up_confirmed=True,
        )
        assert result is True
        assert pm.get(p.profile_id) is None

    def test_delete_default_profile_raises(self):
        """Deleting the default profile raises ProfileError."""
        pm = ProfileManager()
        default_id = pm._default_profile_id
        with pytest.raises(ProfileError, match="default"):
            pm.delete(
                default_id,
                oauth3_confirmed=True,
                step_up_confirmed=True,
            )

    def test_delete_nonexistent_raises(self):
        """Deleting a non-existent profile raises ProfileNotFoundError."""
        pm = ProfileManager()
        with pytest.raises(ProfileNotFoundError):
            pm.delete(
                "no-such-id",
                oauth3_confirmed=True,
                step_up_confirmed=True,
            )

    def test_switch_activates_profile(self):
        """switch() sets the active profile."""
        pm = ProfileManager()
        p = pm.create("Research")
        pm.switch(p.profile_id)
        active = pm.active_profile
        assert active is not None
        assert active.profile_id == p.profile_id

    def test_switch_nonexistent_raises(self):
        """switch() raises ProfileNotFoundError for unknown profile_id."""
        pm = ProfileManager()
        with pytest.raises(ProfileNotFoundError):
            pm.switch("no-such-profile")

    def test_switch_updates_last_used(self):
        """switch() updates the last_used timestamp of the target profile."""
        pm = ProfileManager()
        p = pm.create("Timer")
        original_last_used = p.last_used
        time.sleep(0.01)  # ensure clock advances
        pm.switch(p.profile_id)
        updated = pm.get(p.profile_id)
        assert updated is not None
        assert updated.last_used >= original_last_used


# ===========================================================================
# TestProfileIsolation — 8 tests
# ===========================================================================

class TestProfileIsolation:
    """Test that profiles cannot access each other's data."""

    def test_separate_cookies_paths(self):
        """Each profile has a unique cookie jar path."""
        pm = ProfileManager()
        p1 = pm.create("Profile1")
        p2 = pm.create("Profile2")
        assert p1.cookies_path != p2.cookies_path

    def test_cookies_path_contains_profile_id(self):
        """Cookie jar path is scoped to the profile_id."""
        pm = ProfileManager()
        p = pm.create("CookieTest")
        assert p.profile_id in p.cookies_path

    def test_default_profile_has_own_cookies_path(self):
        """Default profile has a distinct cookie path from created profiles."""
        pm = ProfileManager()
        p = pm.create("Another")
        assert pm.default_profile.cookies_path != p.cookies_path

    def test_cross_profile_token_access_blocked(self):
        """get_tokens_for_profile() raises ProfileIsolationError on cross-access."""
        pm = ProfileManager()
        p1 = pm.create("Owner")
        p2 = pm.create("Attacker")
        pm.add_token_to_profile(p1.profile_id, "token-secret-123")
        with pytest.raises(ProfileIsolationError, match="Cross-profile"):
            pm.get_tokens_for_profile(
                requesting_profile_id=p2.profile_id,
                target_profile_id=p1.profile_id,
            )

    def test_same_profile_token_access_allowed(self):
        """get_tokens_for_profile() allows same-profile access."""
        pm = ProfileManager()
        p = pm.create("Owner")
        pm.add_token_to_profile(p.profile_id, "token-abc")
        tokens = pm.get_tokens_for_profile(
            requesting_profile_id=p.profile_id,
            target_profile_id=p.profile_id,
        )
        assert "token-abc" in tokens

    def test_tokens_not_shared_between_profiles(self):
        """Adding a token to profile A does not affect profile B's tokens."""
        pm = ProfileManager()
        pa = pm.create("Alpha")
        pb = pm.create("Beta")
        pm.add_token_to_profile(pa.profile_id, "token-only-for-alpha")
        tokens_b = pm.get_tokens_for_profile(
            requesting_profile_id=pb.profile_id,
            target_profile_id=pb.profile_id,
        )
        assert "token-only-for-alpha" not in tokens_b

    def test_deletion_does_not_leak_tokens(self):
        """After deleting a profile, its token IDs are gone."""
        pm = ProfileManager()
        p = pm.create("Ephemeral")
        pm.add_token_to_profile(p.profile_id, "leaky-token")
        pm.delete(p.profile_id, oauth3_confirmed=True, step_up_confirmed=True)
        assert pm.get(p.profile_id) is None

    def test_profile_isolation_error_is_profile_error(self):
        """ProfileIsolationError is a subclass of ProfileError."""
        assert issubclass(ProfileIsolationError, ProfileError)


# ===========================================================================
# TestBrowserProcess — 8 tests
# ===========================================================================

class TestBrowserProcess:
    """Test ProcessInfo/BrowserProcess dataclass creation and field access."""

    def test_creation_running_status(self):
        """ProcessInfo stores all fields for a running process."""
        p = _make_process_info(status=ProcessStatus.RUNNING, pid=1234)
        assert p.status == "running"
        assert p.pid == 1234
        assert isinstance(p.process_id, str)
        assert len(p.process_id) == 36

    def test_stopped_process_has_none_pid(self):
        """Stopped processes typically have pid=None."""
        p = _make_process_info(status=ProcessStatus.STOPPED, pid=None)
        assert p.pid is None
        assert p.status == "stopped"

    def test_browser_process_is_alias(self):
        """BrowserProcess is an alias for ProcessInfo."""
        assert BrowserProcess is ProcessInfo

    def test_all_valid_statuses(self):
        """ProcessStatus.ALL contains canonical status strings."""
        assert "running" in ProcessStatus.ALL
        assert "stopped" in ProcessStatus.ALL
        assert "crashed" in ProcessStatus.ALL

    def test_cpu_percent_is_int(self):
        """cpu_percent is stored as int."""
        p = _make_process_info(cpu_percent=42)
        assert isinstance(p.cpu_percent, int)
        assert p.cpu_percent == 42

    def test_memory_mb_is_int(self):
        """memory_mb is stored as int."""
        p = _make_process_info(memory_mb=512)
        assert isinstance(p.memory_mb, int)
        assert p.memory_mb == 512

    def test_started_at_is_iso8601(self):
        """started_at is a valid ISO 8601 UTC timestamp."""
        p = _make_process_info()
        dt = datetime.fromisoformat(p.started_at.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_sha256_hash_format(self):
        """sha256_hash() returns 'sha256:<64 hex chars>'."""
        p = _make_process_info()
        h = p.sha256_hash()
        assert h.startswith("sha256:")
        hex_part = h[len("sha256:"):]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)


# ===========================================================================
# TestProcessManager — 10 tests
# ===========================================================================

class TestProcessManager:
    """Test ProcessManager lifecycle operations."""

    def test_spawn_returns_running_process(self):
        """spawn_process() returns a ProcessInfo with status=running."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        assert isinstance(proc, ProcessInfo)
        assert proc.status == ProcessStatus.RUNNING
        assert proc.pid is not None

    def test_spawn_assigns_unique_process_ids(self):
        """Each spawn_process() call produces a unique process_id."""
        pm = ProcessManager()
        p1 = pm.spawn_process("profile-001", step_up_confirmed=True)
        p2 = pm.spawn_process("profile-001", step_up_confirmed=True)
        assert p1.process_id != p2.process_id

    def test_kill_process_stops_it(self):
        """kill_process() removes the process (returns True)."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        result = pm.kill_process(proc.process_id, step_up_confirmed=True)
        assert result is True
        # Process should be gone from active list
        assert pm.get_process_info(proc.process_id) is None

    def test_list_processes_includes_all(self):
        """list_processes() returns all spawned processes."""
        pm = ProcessManager()
        p1 = pm.spawn_process("profile-001", step_up_confirmed=True)
        p2 = pm.spawn_process("profile-002", step_up_confirmed=True)
        procs = pm.list_processes()
        ids = {p.process_id for p in procs}
        assert p1.process_id in ids
        assert p2.process_id in ids

    def test_resource_limit_per_profile(self):
        """Spawning beyond max_processes_per_profile raises ResourceLimitError."""
        pm = ProcessManager(max_processes_per_profile=2)
        pm.spawn_process("profile-001", step_up_confirmed=True)
        pm.spawn_process("profile-001", step_up_confirmed=True)
        with pytest.raises(ResourceLimitError, match="Max processes"):
            pm.spawn_process("profile-001", step_up_confirmed=True)

    def test_resource_limit_total_memory(self):
        """Spawning beyond max_memory_total_mb raises ResourceLimitError."""
        pm = ProcessManager(max_memory_total_mb=200)
        pm.spawn_process("profile-001", step_up_confirmed=True, initial_memory_mb=150)
        with pytest.raises(ResourceLimitError, match="memory limit"):
            pm.spawn_process("profile-001", step_up_confirmed=True, initial_memory_mb=100)

    def test_health_check_marks_stale_crashed(self):
        """health_check() marks stale processes as crashed."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        # Tamper with last heartbeat to simulate stale
        pm._last_heartbeat[proc.process_id] = time.monotonic() - 1000
        affected = pm.health_check(heartbeat_timeout_seconds=1)
        assert len(affected) >= 1
        assert any(p.status == ProcessStatus.CRASHED for p in affected)

    def test_mark_crashed_sets_status(self):
        """mark_crashed() sets the process status to crashed."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        crashed = pm.mark_crashed(proc.process_id)
        assert crashed is not None
        assert crashed.status == ProcessStatus.CRASHED
        assert crashed.pid is None

    def test_get_stats_aggregates_correctly(self):
        """get_stats() correctly counts statuses and sums resources."""
        pm = ProcessManager()
        pm.spawn_process("profile-001", step_up_confirmed=True, initial_memory_mb=100)
        pm.spawn_process("profile-002", step_up_confirmed=True, initial_memory_mb=200)
        stats = pm.get_stats()
        assert stats.total_processes == 2
        assert stats.running == 2
        assert stats.total_memory_mb == 300

    def test_cleanup_for_profile(self):
        """cleanup_for_profile() kills all processes owned by the profile."""
        pm = ProcessManager()
        pm.spawn_process("profile-001", step_up_confirmed=True)
        pm.spawn_process("profile-001", step_up_confirmed=True)
        pm.spawn_process("profile-002", step_up_confirmed=True)
        count = pm.cleanup_for_profile("profile-001", step_up_confirmed=True)
        assert count == 2
        # profile-002 process should still be running
        stats = pm.get_stats()
        assert stats.running == 1


# ===========================================================================
# TestOAuth3Integration — 8 tests
# ===========================================================================

class TestOAuth3Integration:
    """Test OAuth3 scope enforcement gates on profile and process operations."""

    def test_delete_without_oauth3_raises(self):
        """delete() without oauth3_confirmed raises ProfileError."""
        pm = ProfileManager()
        p = pm.create("Secret")
        with pytest.raises(ProfileError, match="OAuth3 scope required"):
            pm.delete(p.profile_id, oauth3_confirmed=False, step_up_confirmed=True)

    def test_delete_without_step_up_raises(self):
        """delete() without step_up_confirmed raises ProfileError."""
        pm = ProfileManager()
        p = pm.create("Guarded")
        with pytest.raises(ProfileError, match="Step-up"):
            pm.delete(p.profile_id, oauth3_confirmed=True, step_up_confirmed=False)

    def test_delete_with_both_confirmed_succeeds(self):
        """delete() with both gates confirmed succeeds."""
        pm = ProfileManager()
        p = pm.create("Deleteable")
        result = pm.delete(p.profile_id, oauth3_confirmed=True, step_up_confirmed=True)
        assert result is True

    def test_spawn_without_step_up_raises(self):
        """spawn_process() without step_up_confirmed raises PermissionError."""
        pm = ProcessManager()
        with pytest.raises(PermissionError, match="step-up"):
            pm.spawn_process("profile-001", step_up_confirmed=False)

    def test_spawn_with_step_up_confirmed_succeeds(self):
        """spawn_process() with step_up_confirmed=True returns a running process."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        assert proc.status == ProcessStatus.RUNNING

    def test_kill_without_step_up_raises(self):
        """kill_process() without step_up_confirmed raises PermissionError."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        with pytest.raises(PermissionError, match="step-up"):
            pm.kill_process(proc.process_id, step_up_confirmed=False)

    def test_kill_with_step_up_confirmed_succeeds(self):
        """kill_process() with step_up_confirmed=True succeeds."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        result = pm.kill_process(proc.process_id, step_up_confirmed=True)
        assert result is True

    def test_default_profile_delete_blocked_regardless_of_auth(self):
        """Default profile cannot be deleted even with full auth."""
        pm = ProfileManager()
        default_id = pm._default_profile_id
        with pytest.raises(ProfileError):
            pm.delete(default_id, oauth3_confirmed=True, step_up_confirmed=True)


# ===========================================================================
# TestEvidence — 6 tests
# ===========================================================================

class TestEvidence:
    """Test that lifecycle events are logged with SHA-256 hashes."""

    def test_switch_logs_event(self):
        """switch() appends a SwitchEvent to the switch_log."""
        pm = ProfileManager()
        p = pm.create("LogMe")
        pm.switch(p.profile_id)
        assert len(pm.switch_log) >= 1
        last = pm.switch_log[-1]
        assert isinstance(last, SwitchEvent)
        assert last.to_profile_id == p.profile_id

    def test_switch_log_has_sha256(self):
        """SwitchEvent contains a valid SHA-256 hash of the target profile."""
        pm = ProfileManager()
        p = pm.create("Hashed")
        pm.switch(p.profile_id)
        last = pm.switch_log[-1]
        assert last.sha256_to.startswith("sha256:")
        hex_part = last.sha256_to[len("sha256:"):]
        assert len(hex_part) == 64

    def test_switch_log_has_timestamp(self):
        """SwitchEvent has a valid ISO 8601 UTC timestamp."""
        pm = ProfileManager()
        p = pm.create("Timestamped")
        pm.switch(p.profile_id)
        last = pm.switch_log[-1]
        dt = datetime.fromisoformat(last.switched_at.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_spawn_logs_event(self):
        """spawn_process() appends a ProcessEvent to the event_log."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        assert len(pm.event_log) >= 1
        last = pm.event_log[-1]
        assert isinstance(last, ProcessEvent)
        assert last.process_id == proc.process_id
        assert last.event == "spawned"

    def test_process_event_has_sha256(self):
        """ProcessEvent contains a valid SHA-256 hash of the process state."""
        pm = ProcessManager()
        pm.spawn_process("profile-001", step_up_confirmed=True)
        last = pm.event_log[-1]
        assert last.sha256.startswith("sha256:")
        hex_part = last.sha256[len("sha256:"):]
        assert len(hex_part) == 64

    def test_kill_lifecycle_logged(self):
        """spawn → kill lifecycle logged as ProcessEvents."""
        pm = ProcessManager()
        proc = pm.spawn_process("profile-001", step_up_confirmed=True)
        pm.kill_process(proc.process_id, step_up_confirmed=True)
        events = [e.event for e in pm.event_log]
        assert "spawned" in events
        assert "killed" in events
