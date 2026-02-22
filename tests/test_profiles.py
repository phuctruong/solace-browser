"""
Multi-Profile Browser + Process Manager Test Suite

Tests for BrowserProfile, ProfileSession, ProfileManager, ProcessInfo, ProcessManager.

OAuth3 scope format: profile.<action>
All timestamps ISO 8601 UTC, all hashes sha256: prefixed hex.
No float in verification paths.

Total: 60 tests across 7 test classes + edge cases.
Rung: 274177
"""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import profiles package — auto-registers profile scopes
import src.profiles  # noqa: E402

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
    MAX_PROFILES,
    _validate_viewport,
)
from src.profiles.process import (
    ProcessInfo,
    BrowserProcess,
    ProcessManager,
    ProcessStatus,
    ProcessStats,
    ProcessEvent,
    ProcessError,
    ProcessNotFoundError,
    ResourceLimitError,
    DEFAULT_MAX_PROCESSES_PER_PROFILE,
    DEFAULT_MAX_MEMORY_TOTAL_MB,
)
from src.profiles.scopes import (
    PROFILE_SCOPES,
    SCOPE_PROFILE_CREATE,
    SCOPE_PROFILE_DELETE,
    SCOPE_SESSION_START,
    SCOPE_SESSION_TERMINATE,
    SCOPE_PROCESS_SPAWN,
    SCOPE_PROCESS_KILL,
)
from src.oauth3.scopes import SCOPE_REGISTRY, HIGH_RISK_SCOPES


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def pm() -> ProfileManager:
    """Return a fresh ProfileManager."""
    return ProfileManager()


@pytest.fixture
def proc_mgr() -> ProcessManager:
    """Return a fresh ProcessManager."""
    return ProcessManager()


@pytest.fixture
def profile(pm) -> BrowserProfile:
    """Return a test BrowserProfile."""
    return pm.create_profile("Test Profile", token_id="tok-abc")


@pytest.fixture
def session(pm, profile) -> ProfileSession:
    """Return an active test ProfileSession."""
    return pm.start_session(profile.profile_id, token_id="tok-abc")


# ===========================================================================
# TestBrowserProfile — 8 tests
# ===========================================================================

class TestBrowserProfile:
    """Test BrowserProfile dataclass creation and validation."""

    def test_create_profile_returns_browser_profile(self, pm):
        """create_profile returns a BrowserProfile instance."""
        p = pm.create_profile("Work")
        assert isinstance(p, BrowserProfile)

    def test_profile_has_uuid_profile_id(self, pm):
        """Profile ID is a valid UUID4."""
        p = pm.create_profile("Work")
        parsed = uuid.UUID(p.profile_id, version=4)
        assert str(parsed) == p.profile_id

    def test_profile_name_stored(self, pm):
        """Profile name is stored correctly."""
        p = pm.create_profile("My Work Profile")
        assert p.name == "My Work Profile"

    def test_default_user_agent_applied(self, pm):
        """Default user agent is applied when not provided."""
        p = pm.create_profile("Work")
        assert p.user_agent == DEFAULT_USER_AGENT

    def test_custom_user_agent_stored(self, pm):
        """Custom user agent is stored."""
        custom_ua = "Mozilla/5.0 CustomBrowser/1.0"
        p = pm.create_profile("Work", config={"user_agent": custom_ua})
        assert p.user_agent == custom_ua

    def test_default_viewport_applied(self, pm):
        """Default viewport is applied when not provided."""
        p = pm.create_profile("Work")
        assert p.viewport == DEFAULT_VIEWPORT

    def test_custom_viewport_stored(self, pm):
        """Custom viewport is stored with integer values."""
        vp = {"width": 1920, "height": 1080}
        p = pm.create_profile("Work", config={"viewport": vp})
        assert p.viewport == vp
        assert isinstance(p.viewport["width"], int)
        assert isinstance(p.viewport["height"], int)

    def test_proxy_stored(self, pm):
        """Proxy setting is stored."""
        p = pm.create_profile("Work", config={"proxy": "socks5://localhost:1080"})
        assert p.proxy == "socks5://localhost:1080"

    def test_cookies_enabled_default_true(self, pm):
        """cookies_enabled defaults to True."""
        p = pm.create_profile("Work")
        assert p.cookies_enabled is True

    def test_cookies_enabled_false(self, pm):
        """cookies_enabled can be set to False."""
        p = pm.create_profile("Work", config={"cookies_enabled": False})
        assert p.cookies_enabled is False

    def test_oauth3_token_id_stored(self, pm):
        """OAuth3 token_id is stored in profile."""
        p = pm.create_profile("Work", token_id="my-token-id")
        assert p.oauth3_token_id == "my-token-id"

    def test_created_at_iso8601(self, pm):
        """created_at is an ISO 8601 UTC string."""
        p = pm.create_profile("Work")
        assert "T" in p.created_at
        assert len(p.created_at) > 19

    def test_platform_credentials_stored(self, pm):
        """platform_credentials dict is stored."""
        creds = {"vault_ref": "solace://vault/linkedin/user1"}
        p = pm.create_profile("Work", config={"platform_credentials": creds})
        assert "vault_ref" in p.platform_credentials

    def test_sha256_hash_prefix(self, pm):
        """sha256_hash() returns sha256: prefixed string."""
        p = pm.create_profile("Work")
        h = p.sha256_hash()
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64

    def test_to_dict_masks_secret_keys(self, pm):
        """to_dict() masks credential dict entries with secret/password/token/key in name."""
        creds = {"api_key": "plaintext-key", "vault_ref": "ok-ref"}
        p = pm.create_profile("Work", config={"platform_credentials": creds})
        d = p.to_dict()
        assert d["platform_credentials"]["api_key"] == "***vault-ref***"
        assert d["platform_credentials"]["vault_ref"] == "ok-ref"

    def test_empty_name_raises(self, pm):
        """Empty profile name raises ValueError."""
        with pytest.raises(ValueError, match="name must not be empty"):
            pm.create_profile("")

    def test_invalid_viewport_width_raises(self, pm):
        """Invalid viewport width raises ValueError."""
        with pytest.raises(ValueError, match="viewport"):
            pm.create_profile("Work", config={"viewport": {"width": -1, "height": 720}})

    def test_float_viewport_raises(self, pm):
        """Float viewport values raise ValueError."""
        with pytest.raises(ValueError, match="viewport"):
            pm.create_profile("Work", config={"viewport": {"width": 1920.5, "height": 720}})


# ===========================================================================
# TestProfileManager — 12 tests
# ===========================================================================

class TestProfileManager:
    """Test ProfileManager CRUD operations."""

    def test_list_profiles_empty_initially(self, pm):
        """No profiles on fresh manager."""
        assert pm.list_profiles() == []

    def test_create_and_list_profile(self, pm):
        """Created profile appears in list_profiles."""
        p = pm.create_profile("Work")
        profiles = pm.list_profiles()
        assert len(profiles) == 1
        assert profiles[0].profile_id == p.profile_id

    def test_create_multiple_profiles(self, pm):
        """Multiple profiles can be created."""
        pm.create_profile("Work")
        pm.create_profile("Personal")
        pm.create_profile("Research")
        assert len(pm.list_profiles()) == 3

    def test_get_profile_by_id(self, pm):
        """get() returns the profile by ID."""
        p = pm.create_profile("Work")
        retrieved = pm.get(p.profile_id)
        assert retrieved is not None
        assert retrieved.profile_id == p.profile_id

    def test_get_nonexistent_profile_returns_none(self, pm):
        """get() returns None for unknown profile_id."""
        assert pm.get("nonexistent") is None

    def test_delete_profile_requires_step_up(self, pm):
        """delete_profile raises PermissionError without step_up_confirmed."""
        p = pm.create_profile("Work")
        with pytest.raises(PermissionError, match="step-up"):
            pm.delete_profile(p.profile_id)

    def test_delete_profile_with_step_up(self, pm):
        """delete_profile with step_up_confirmed=True removes profile."""
        p = pm.create_profile("Work")
        result = pm.delete_profile(p.profile_id, step_up_confirmed=True)
        assert result is True
        assert pm.get(p.profile_id) is None

    def test_delete_nonexistent_profile_returns_false(self, pm):
        """delete_profile returns False for nonexistent profile_id."""
        result = pm.delete_profile("nonexistent", step_up_confirmed=True)
        assert result is False

    def test_profile_ids_unique(self, pm):
        """Each created profile has a unique profile_id."""
        profiles = [pm.create_profile(f"Profile {i}") for i in range(5)]
        ids = [p.profile_id for p in profiles]
        assert len(set(ids)) == 5

    def test_create_profile_audit_log_entry(self, pm):
        """create_profile writes an audit log entry."""
        pm.create_profile("Work", token_id="tok-x")
        log = pm.get_audit_log()
        assert len(log) >= 1
        assert log[0]["event"] == "profile_created"
        assert log[0]["token_id"] == "tok-x"

    def test_delete_profile_audit_log_entry(self, pm):
        """delete_profile writes an audit log entry."""
        p = pm.create_profile("Work")
        pm.delete_profile(p.profile_id, token_id="tok-del", step_up_confirmed=True)
        log = pm.get_audit_log()
        events = [e["event"] for e in log]
        assert "profile_deleted" in events

    def test_delete_profile_terminates_its_sessions(self, pm):
        """delete_profile terminates all sessions belonging to the profile."""
        p = pm.create_profile("Work")
        s = pm.start_session(p.profile_id, token_id="tok")
        pm.delete_profile(p.profile_id, step_up_confirmed=True)
        # Session should be gone
        stats = pm.get_session_stats(s.session_id)
        assert "error" in stats


# ===========================================================================
# TestProfileSession — 10 tests
# ===========================================================================

class TestProfileSession:
    """Test ProfileSession lifecycle, isolation, scope enforcement, stats."""

    def test_start_session_requires_token_id(self, pm, profile):
        """start_session raises ValueError with empty token_id."""
        with pytest.raises(ValueError, match="token_id"):
            pm.start_session(profile.profile_id, token_id="")

    def test_start_session_nonexistent_profile_raises(self, pm):
        """start_session raises ValueError for nonexistent profile."""
        with pytest.raises(ValueError, match="not found"):
            pm.start_session("nonexistent-id", token_id="tok")

    def test_start_session_returns_active_session(self, pm, profile):
        """start_session returns a ProfileSession in 'active' status."""
        s = pm.start_session(profile.profile_id, token_id="tok")
        assert isinstance(s, ProfileSession)
        assert s.status == "active"

    def test_session_bound_to_profile(self, pm, profile):
        """Session profile_id matches the profile it was started for."""
        s = pm.start_session(profile.profile_id, token_id="tok")
        assert s.profile_id == profile.profile_id

    def test_session_pages_visited_int(self, pm, profile):
        """pages_visited is an integer (never float)."""
        s = pm.start_session(profile.profile_id, token_id="tok")
        assert isinstance(s.pages_visited, int)
        assert s.pages_visited == 0

    def test_session_scopes_include_start(self, pm, profile):
        """Session oauth3_scopes_used includes profile.session.start."""
        s = pm.start_session(profile.profile_id, token_id="tok")
        assert "profile.session.start" in s.oauth3_scopes_used

    def test_suspend_active_session(self, pm, session):
        """suspend_session changes status to 'suspended'."""
        result = pm.suspend_session(session.session_id)
        assert result is True
        assert session.status == "suspended"

    def test_resume_suspended_session(self, pm, session):
        """resume_session changes status back to 'active'."""
        pm.suspend_session(session.session_id)
        result = pm.resume_session(session.session_id)
        assert result is True
        assert session.status == "active"

    def test_terminate_session_requires_step_up(self, pm, session):
        """terminate_session raises PermissionError without step_up_confirmed."""
        with pytest.raises(PermissionError, match="step-up"):
            pm.terminate_session(session.session_id)

    def test_terminate_session_removes_from_registry(self, pm, session):
        """terminate_session removes session from registry."""
        sid = session.session_id
        pm.terminate_session(sid, step_up_confirmed=True)
        stats = pm.get_session_stats(sid)
        assert "error" in stats

    def test_get_session_stats_returns_metrics(self, pm, session):
        """get_session_stats returns dict with required fields."""
        stats = pm.get_session_stats(session.session_id)
        assert "session_id" in stats
        assert "profile_id" in stats
        assert "status" in stats
        assert "pages_visited" in stats
        assert isinstance(stats["pages_visited"], int)

    def test_get_session_stats_not_found(self, pm):
        """get_session_stats returns error dict for unknown session."""
        result = pm.get_session_stats("nonexistent")
        assert "error" in result
        assert result["error"] == "SESSION_NOT_FOUND"

    def test_session_isolation_list_by_profile(self, pm):
        """list_sessions_for_profile only returns sessions for that profile."""
        p1 = pm.create_profile("Profile 1")
        p2 = pm.create_profile("Profile 2")
        s1 = pm.start_session(p1.profile_id, token_id="tok")
        s2 = pm.start_session(p2.profile_id, token_id="tok")

        p1_sessions = pm.list_sessions_for_profile(p1.profile_id)
        assert all(s.profile_id == p1.profile_id for s in p1_sessions)
        assert s2.session_id not in [s.session_id for s in p1_sessions]


# ===========================================================================
# TestProcessManager — 10 tests
# ===========================================================================

class TestProcessManager:
    """Test ProcessManager spawn, kill, list, resource limits, auto-cleanup."""

    def test_spawn_process_requires_step_up(self, proc_mgr):
        """spawn_process raises PermissionError without step_up_confirmed."""
        with pytest.raises(PermissionError, match="step-up"):
            proc_mgr.spawn_process("profile-id")

    def test_spawn_process_returns_process_info(self, proc_mgr):
        """spawn_process returns a ProcessInfo with status=running."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        assert isinstance(p, ProcessInfo)
        assert p.status == ProcessStatus.RUNNING

    def test_process_has_integer_cpu(self, proc_mgr):
        """ProcessInfo.cpu_percent is an integer."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        assert isinstance(p.cpu_percent, int)

    def test_process_has_integer_memory(self, proc_mgr):
        """ProcessInfo.memory_mb is an integer."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        assert isinstance(p.memory_mb, int)

    def test_process_has_integer_uptime(self, proc_mgr):
        """ProcessInfo.uptime_seconds is an integer."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        assert isinstance(p.uptime_seconds, int)

    def test_kill_process_requires_step_up(self, proc_mgr):
        """kill_process raises PermissionError without step_up_confirmed."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        with pytest.raises(PermissionError, match="step-up"):
            proc_mgr.kill_process(p.process_id)

    def test_kill_process_removes_process(self, proc_mgr):
        """kill_process removes the process from registry."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        result = proc_mgr.kill_process(p.process_id, step_up_confirmed=True)
        assert result is True
        assert proc_mgr.get_process_info(p.process_id) is None

    def test_kill_nonexistent_returns_false(self, proc_mgr):
        """kill_process returns False for nonexistent process_id."""
        result = proc_mgr.kill_process("nonexistent", step_up_confirmed=True)
        assert result is False

    def test_list_processes_returns_all(self, proc_mgr):
        """list_processes returns all tracked processes."""
        proc_mgr.spawn_process("p1", step_up_confirmed=True)
        proc_mgr.spawn_process("p2", step_up_confirmed=True)
        procs = proc_mgr.list_processes()
        assert len(procs) == 2

    def test_get_process_info_returns_process(self, proc_mgr):
        """get_process_info returns ProcessInfo for known process_id."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        info = proc_mgr.get_process_info(p.process_id)
        assert info is not None
        assert info.process_id == p.process_id

    def test_get_process_info_not_found_returns_none(self, proc_mgr):
        """get_process_info returns None for unknown process_id."""
        assert proc_mgr.get_process_info("nonexistent") is None

    def test_max_processes_per_profile_enforced(self, proc_mgr):
        """ResourceLimitError raised when max_processes_per_profile exceeded."""
        for _ in range(DEFAULT_MAX_PROCESSES_PER_PROFILE):
            proc_mgr.spawn_process("same-profile", step_up_confirmed=True)
        with pytest.raises(ResourceLimitError, match="Max processes"):
            proc_mgr.spawn_process("same-profile", step_up_confirmed=True)

    def test_memory_limit_enforced(self):
        """ResourceLimitError raised when total memory limit exceeded."""
        pm = ProcessManager(max_memory_total_mb=256)
        pm.spawn_process("p1", step_up_confirmed=True, initial_memory_mb=200)
        with pytest.raises(ResourceLimitError, match="memory"):
            pm.spawn_process("p2", step_up_confirmed=True, initial_memory_mb=200)

    def test_cleanup_for_profile_kills_processes(self, proc_mgr):
        """cleanup_for_profile kills all processes owned by profile."""
        proc_mgr.spawn_process("my-profile", step_up_confirmed=True)
        proc_mgr.spawn_process("my-profile", step_up_confirmed=True)
        proc_mgr.spawn_process("other-profile", step_up_confirmed=True)
        count = proc_mgr.cleanup_for_profile("my-profile")
        assert count == 2
        remaining = [p for p in proc_mgr.list_processes()
                     if p.profile_id == "my-profile"]
        assert len(remaining) == 0

    def test_health_check_marks_stale_as_crashed(self, proc_mgr):
        """health_check marks processes that missed heartbeat as crashed."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        # Force old heartbeat by setting it far in the past
        proc_mgr._last_heartbeat[p.process_id] = time.monotonic() - 9999
        affected = proc_mgr.health_check(heartbeat_timeout_seconds=1)
        assert len(affected) >= 1
        assert affected[0].status == ProcessStatus.CRASHED

    def test_event_log_records_spawn(self, proc_mgr):
        """Spawning a process appends a 'spawned' event to event_log."""
        proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        events = [e.event for e in proc_mgr.event_log]
        assert "spawned" in events

    def test_sha256_hash_on_process(self, proc_mgr):
        """ProcessInfo.sha256_hash() returns sha256: prefixed string."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        h = p.sha256_hash()
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64


# ===========================================================================
# TestOAuth3Gate — 8 tests
# ===========================================================================

class TestOAuth3Gate:
    """Test OAuth3 gate requirements for profile and process operations."""

    def test_profile_scopes_registered_in_registry(self):
        """All PROFILE_SCOPES are in the global SCOPE_REGISTRY after import."""
        for scope in PROFILE_SCOPES:
            assert scope in SCOPE_REGISTRY, f"{scope} not in SCOPE_REGISTRY"

    def test_profile_delete_scope_is_high_risk(self):
        """profile.delete.profile is classified as HIGH risk."""
        assert SCOPE_PROFILE_DELETE in HIGH_RISK_SCOPES

    def test_session_terminate_scope_is_high_risk(self):
        """profile.session.terminate is classified as HIGH risk."""
        assert SCOPE_SESSION_TERMINATE in HIGH_RISK_SCOPES

    def test_process_spawn_scope_is_high_risk(self):
        """profile.process.spawn is classified as HIGH risk."""
        assert SCOPE_PROCESS_SPAWN in HIGH_RISK_SCOPES

    def test_process_kill_scope_is_high_risk(self):
        """profile.process.kill is classified as HIGH risk."""
        assert SCOPE_PROCESS_KILL in HIGH_RISK_SCOPES

    def test_start_session_requires_token_id_not_empty(self, pm, profile):
        """start_session enforces non-empty token_id (OAuth3 gate)."""
        with pytest.raises(ValueError, match="token_id"):
            pm.start_session(profile.profile_id, token_id="")

    def test_delete_profile_step_up_gate(self, pm):
        """delete_profile raises PermissionError when step_up_confirmed=False."""
        p = pm.create_profile("Work")
        with pytest.raises(PermissionError):
            pm.delete_profile(p.profile_id, step_up_confirmed=False)

    def test_terminate_session_step_up_gate(self, pm, session):
        """terminate_session raises PermissionError when step_up_confirmed=False."""
        with pytest.raises(PermissionError):
            pm.terminate_session(session.session_id, step_up_confirmed=False)

    def test_spawn_process_step_up_gate(self, proc_mgr):
        """spawn_process raises PermissionError when step_up_confirmed=False."""
        with pytest.raises(PermissionError):
            proc_mgr.spawn_process("profile-id", step_up_confirmed=False)

    def test_kill_process_step_up_gate(self, proc_mgr):
        """kill_process raises PermissionError when step_up_confirmed=False."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        with pytest.raises(PermissionError):
            proc_mgr.kill_process(p.process_id, step_up_confirmed=False)


# ===========================================================================
# TestEvidence — 6 tests
# ===========================================================================

class TestEvidence:
    """Test session/process logging and hash integrity."""

    def test_audit_log_has_integrity_hash(self, pm, profile):
        """Each audit log entry has an integrity_hash field."""
        log = pm.get_audit_log()
        for entry in log:
            assert "integrity_hash" in entry
            assert entry["integrity_hash"].startswith("sha256:")

    def test_session_start_logged(self, pm, profile):
        """Starting a session writes session_start to audit log."""
        pm.start_session(profile.profile_id, token_id="tok")
        log = pm.get_audit_log()
        events = [e["event"] for e in log]
        assert "session_start" in events

    def test_session_terminate_logged(self, pm, session):
        """Terminating a session writes session_terminate to audit log."""
        pm.terminate_session(session.session_id, step_up_confirmed=True)
        log = pm.get_audit_log()
        events = [e["event"] for e in log]
        assert "session_terminate" in events

    def test_profile_created_logged(self, pm):
        """Profile creation is logged."""
        pm.create_profile("Work", token_id="tok-x")
        log = pm.get_audit_log()
        assert log[0]["event"] == "profile_created"

    def test_process_event_has_sha256(self, proc_mgr):
        """ProcessEvent in event_log has sha256 hash."""
        proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        for event in proc_mgr.event_log:
            assert event.sha256.startswith("sha256:")

    def test_audit_log_is_copy(self, pm):
        """get_audit_log returns a copy (mutating it does not affect internal log)."""
        pm.create_profile("Work")
        log1 = pm.get_audit_log()
        log1.clear()
        log2 = pm.get_audit_log()
        assert len(log2) >= 1


# ===========================================================================
# TestEdgeCases — 6 tests
# ===========================================================================

class TestEdgeCases:
    """Test max profiles, session after token revoke, process crash handling."""

    def test_max_profiles_limit_enforced(self):
        """ValueError raised when MAX_PROFILES profiles exist."""
        pm = ProfileManager()
        for i in range(MAX_PROFILES):
            pm.create_profile(f"Profile {i}")
        with pytest.raises(ValueError, match="Maximum profile count"):
            pm.create_profile("One Too Many")

    def test_suspend_already_suspended_is_idempotent(self, pm, session):
        """Suspending an already-suspended session returns True (idempotent)."""
        pm.suspend_session(session.session_id)
        result = pm.suspend_session(session.session_id)
        assert result is True
        assert session.status == "suspended"

    def test_resume_already_active_is_idempotent(self, pm, session):
        """Resuming an already-active session returns True (idempotent)."""
        result = pm.resume_session(session.session_id)
        assert result is True
        assert session.status == "active"

    def test_suspend_terminated_session_returns_false(self, pm, session):
        """Suspending a terminated session returns False."""
        pm.terminate_session(session.session_id, step_up_confirmed=True)
        result = pm.suspend_session(session.session_id)
        assert result is False

    def test_process_crash_handling(self, proc_mgr):
        """mark_crashed sets status to crashed."""
        p = proc_mgr.spawn_process("profile-id", step_up_confirmed=True)
        crashed = proc_mgr.mark_crashed(p.process_id)
        assert crashed is not None
        assert crashed.status == ProcessStatus.CRASHED

    def test_process_stats_all_integers(self, proc_mgr):
        """ProcessStats fields are all integers (no float)."""
        proc_mgr.spawn_process("p1", step_up_confirmed=True)
        proc_mgr.spawn_process("p2", step_up_confirmed=True)
        stats = proc_mgr.get_stats()
        assert isinstance(stats.total_processes, int)
        assert isinstance(stats.running, int)
        assert isinstance(stats.total_cpu_percent, int)
        assert isinstance(stats.total_memory_mb, int)

    def test_browser_process_alias_works(self, proc_mgr):
        """BrowserProcess is an alias for ProcessInfo."""
        assert BrowserProcess is ProcessInfo

    def test_profile_session_to_dict_pages_is_int(self, pm, session):
        """ProfileSession.to_dict() has integer pages_visited."""
        pm.record_page_visit(session.session_id)
        d = session.to_dict()
        assert isinstance(d["pages_visited"], int)

    def test_record_page_visit_increments(self, pm, session):
        """record_page_visit increments pages_visited."""
        pm.record_page_visit(session.session_id)
        pm.record_page_visit(session.session_id)
        assert session.pages_visited == 2

    def test_list_all_sessions_returns_all(self, pm):
        """list_all_sessions returns sessions across all profiles."""
        p1 = pm.create_profile("P1")
        p2 = pm.create_profile("P2")
        pm.start_session(p1.profile_id, token_id="tok")
        pm.start_session(p2.profile_id, token_id="tok")
        pm.start_session(p1.profile_id, token_id="tok")
        sessions = pm.list_all_sessions()
        assert len(sessions) == 3
