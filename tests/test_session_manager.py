"""
Tests for session_manager.py — Multi-Browser Session Manager.

Covers:
- Create session with valid profile
- Create multiple sessions simultaneously
- List sessions shows all active
- Close session updates status
- Incognito session uses temp dir
- Port allocation doesn't collide
- Session manifest written on create
- Profile resolution and validation
- Evidence chain written on create/close
- Auth proxy integration (token registration + revocation)
- Port exhaustion error
- Duplicate session error
- Close all sessions
- Thread safety for concurrent creates

Reference: Multi-browser hackathon sprint
Rung: 641
"""

from __future__ import annotations

import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from session_manager import (
    GENESIS_HASH,
    PORT_RANGE_END,
    PORT_RANGE_START,
    PRECONFIGURED_PROFILES,
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_CLOSED,
    BrowserSessionManager,
    DuplicateSessionError,
    InvalidProfileError,
    PortExhaustionError,
    SessionNotFoundError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_manager(
    tmp_path: Path,
    *,
    auth_proxy: Any = None,
    now_fn: Any = None,
) -> BrowserSessionManager:
    """Create a BrowserSessionManager rooted in a temp directory."""
    return BrowserSessionManager(
        solace_home=tmp_path / "solace-home",
        auth_proxy=auth_proxy,
        now_fn=now_fn,
    )


class _FakeAuthProxy:
    """Minimal fake AuthProxy for testing token registration and revocation."""

    def __init__(self) -> None:
        self.registered_tokens: dict[str, Any] = {}
        self.revoked_hashes: set[str] = set()

    def register_token(self, token: str, info: Any) -> str:
        import hashlib
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        self.registered_tokens[token_hash] = {"token": token, "info": info}
        return token_hash

    def revoke_token(self, token_hash: str) -> bool:
        if token_hash in self.registered_tokens:
            self.revoked_hashes.add(token_hash)
            return True
        return False


# ---------------------------------------------------------------------------
# Create session with valid profile
# ---------------------------------------------------------------------------

class TestCreateSession:
    """Creating sessions with pre-configured profiles."""

    def test_create_session_gmail(self, tmp_path: Path) -> None:
        """Create a session with phuc-gmail profile."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(
            session_id="test-gmail",
            profile="phuc-gmail",
        )
        assert result["session_id"] == "test-gmail"
        assert result["profile"] == "phuc-gmail"
        assert result["user_email"] == "user@example.com"
        assert result["status"] == SESSION_STATUS_ACTIVE
        assert PORT_RANGE_START <= result["port"] <= PORT_RANGE_END
        assert "created_at" in result
        assert result["incognito"] is False

    def test_create_session_phucnet(self, tmp_path: Path) -> None:
        """Create a session with phuc-phucnet profile."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(
            session_id="test-phucnet",
            profile="phuc-phucnet",
        )
        assert result["user_email"] == "phuc@phuc.net"
        assert result["profile"] == "phuc-phucnet"

    def test_create_session_phuclabs(self, tmp_path: Path) -> None:
        """Create a session with phuc-phuclabs profile."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(
            session_id="test-phuclabs",
            profile="phuc-phuclabs",
        )
        assert result["user_email"] == "user@work.example.com"
        assert result["profile"] == "phuc-phuclabs"

    def test_create_session_with_email_override(self, tmp_path: Path) -> None:
        """User email override takes precedence over profile default."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(
            session_id="test-override",
            profile="phuc-gmail",
            user_email="custom@example.com",
        )
        assert result["user_email"] == "custom@example.com"
        assert result["profile"] == "phuc-gmail"

    def test_create_session_invalid_profile_raises(self, tmp_path: Path) -> None:
        """Unknown profile -> InvalidProfileError, never silent fallback."""
        manager = _make_manager(tmp_path)
        with pytest.raises(InvalidProfileError, match="Unknown profile"):
            manager.create_session(
                session_id="test-bad",
                profile="nonexistent-profile",
            )

    def test_create_duplicate_session_raises(self, tmp_path: Path) -> None:
        """Duplicate session_id -> DuplicateSessionError."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="dup", profile="phuc-gmail")
        with pytest.raises(DuplicateSessionError, match="already exists"):
            manager.create_session(session_id="dup", profile="phuc-phucnet")


# ---------------------------------------------------------------------------
# Create multiple sessions simultaneously
# ---------------------------------------------------------------------------

class TestMultipleSessions:
    """Multiple concurrent sessions with unique ports and directories."""

    def test_create_three_sessions(self, tmp_path: Path) -> None:
        """Create one session per email account — all get unique ports."""
        manager = _make_manager(tmp_path)
        s1 = manager.create_session(session_id="s1", profile="phuc-gmail")
        s2 = manager.create_session(session_id="s2", profile="phuc-phucnet")
        s3 = manager.create_session(session_id="s3", profile="phuc-phuclabs")

        ports = {s1["port"], s2["port"], s3["port"]}
        assert len(ports) == 3, "Each session must get a unique port"
        assert all(PORT_RANGE_START <= p <= PORT_RANGE_END for p in ports)
        assert manager.active_session_count == 3

    def test_sessions_have_isolated_directories(self, tmp_path: Path) -> None:
        """Each session has its own user data directory."""
        manager = _make_manager(tmp_path)
        s1 = manager.create_session(session_id="s1", profile="phuc-gmail")
        s2 = manager.create_session(session_id="s2", profile="phuc-phucnet")

        dir1 = Path(s1["user_data_dir"])
        dir2 = Path(s2["user_data_dir"])
        assert dir1 != dir2
        assert dir1.exists()
        assert dir2.exists()


# ---------------------------------------------------------------------------
# List sessions
# ---------------------------------------------------------------------------

class TestListSessions:
    """List active sessions."""

    def test_list_empty(self, tmp_path: Path) -> None:
        """No sessions -> empty list."""
        manager = _make_manager(tmp_path)
        assert manager.list_sessions() == []

    def test_list_shows_all_active(self, tmp_path: Path) -> None:
        """All active sessions appear in the list."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        manager.create_session(session_id="s2", profile="phuc-phucnet")

        sessions = manager.list_sessions()
        assert len(sessions) == 2
        ids = {s["session_id"] for s in sessions}
        assert ids == {"s1", "s2"}

    def test_list_excludes_closed(self, tmp_path: Path) -> None:
        """Closed sessions do not appear in list_sessions."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        manager.create_session(session_id="s2", profile="phuc-phucnet")
        manager.close_session("s1")

        sessions = manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "s2"

    def test_list_sorted_by_created_at(self, tmp_path: Path) -> None:
        """Sessions are sorted by created_at."""
        current_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        call_count = 0

        def advancing_clock() -> datetime:
            nonlocal call_count
            call_count += 1
            return current_time + timedelta(seconds=call_count)

        manager = _make_manager(tmp_path, now_fn=advancing_clock)
        manager.create_session(session_id="second", profile="phuc-phucnet")
        manager.create_session(session_id="first", profile="phuc-gmail")

        sessions = manager.list_sessions()
        assert sessions[0]["session_id"] == "second"
        assert sessions[1]["session_id"] == "first"


# ---------------------------------------------------------------------------
# Get session
# ---------------------------------------------------------------------------

class TestGetSession:
    """Get individual session details."""

    def test_get_existing_session(self, tmp_path: Path) -> None:
        """Get a session that exists."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        result = manager.get_session("s1")
        assert result is not None
        assert result["session_id"] == "s1"
        assert result["profile"] == "phuc-gmail"

    def test_get_nonexistent_returns_none(self, tmp_path: Path) -> None:
        """Get a session that doesn't exist -> None."""
        manager = _make_manager(tmp_path)
        assert manager.get_session("nonexistent") is None

    def test_get_closed_session_still_available(self, tmp_path: Path) -> None:
        """Closed sessions can still be retrieved via get_session."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        manager.close_session("s1")
        result = manager.get_session("s1")
        assert result is not None
        assert result["status"] == SESSION_STATUS_CLOSED
        assert result["closed_at"] is not None


# ---------------------------------------------------------------------------
# Close session
# ---------------------------------------------------------------------------

class TestCloseSession:
    """Close a session and verify cleanup."""

    def test_close_updates_status(self, tmp_path: Path) -> None:
        """Close sets status to 'closed' and records closed_at."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        result = manager.close_session("s1")
        assert result["status"] == SESSION_STATUS_CLOSED
        assert result["closed_at"] is not None

    def test_close_releases_port(self, tmp_path: Path) -> None:
        """Closing a session releases its port for reuse."""
        manager = _make_manager(tmp_path)
        s1 = manager.create_session(session_id="s1", profile="phuc-gmail")
        port = s1["port"]
        manager.close_session("s1")

        assert port not in manager.allocated_ports

        # Create another session — should be able to reuse the port
        s2 = manager.create_session(session_id="s2", profile="phuc-phucnet")
        assert s2["port"] == port  # First available port is reused

    def test_close_nonexistent_raises(self, tmp_path: Path) -> None:
        """Closing a nonexistent session -> SessionNotFoundError."""
        manager = _make_manager(tmp_path)
        with pytest.raises(SessionNotFoundError, match="not found"):
            manager.close_session("nonexistent")

    def test_close_idempotent(self, tmp_path: Path) -> None:
        """Closing an already-closed session returns the closed state without error."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        manager.close_session("s1")
        result = manager.close_session("s1")  # Second close is idempotent
        assert result["status"] == SESSION_STATUS_CLOSED

    def test_close_decrements_active_count(self, tmp_path: Path) -> None:
        """Active session count decreases on close."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        manager.create_session(session_id="s2", profile="phuc-phucnet")
        assert manager.active_session_count == 2
        manager.close_session("s1")
        assert manager.active_session_count == 1


# ---------------------------------------------------------------------------
# Close all sessions
# ---------------------------------------------------------------------------

class TestCloseAll:
    """Close all active sessions at once."""

    def test_close_all_closes_everything(self, tmp_path: Path) -> None:
        """close_all closes all active sessions."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        manager.create_session(session_id="s2", profile="phuc-phucnet")
        manager.create_session(session_id="s3", profile="phuc-phuclabs")

        results = manager.close_all()
        assert len(results) == 3
        assert all(r["status"] == SESSION_STATUS_CLOSED for r in results)
        assert manager.active_session_count == 0

    def test_close_all_empty(self, tmp_path: Path) -> None:
        """close_all with no sessions returns empty list."""
        manager = _make_manager(tmp_path)
        results = manager.close_all()
        assert results == []

    def test_close_all_skips_already_closed(self, tmp_path: Path) -> None:
        """close_all only closes active sessions."""
        manager = _make_manager(tmp_path)
        manager.create_session(session_id="s1", profile="phuc-gmail")
        manager.create_session(session_id="s2", profile="phuc-phucnet")
        manager.close_session("s1")

        results = manager.close_all()
        assert len(results) == 1
        assert results[0]["session_id"] == "s2"


# ---------------------------------------------------------------------------
# Incognito sessions
# ---------------------------------------------------------------------------

class TestIncognitoSessions:
    """Incognito sessions use temp directories, cleaned up on close."""

    def test_incognito_uses_temp_dir(self, tmp_path: Path) -> None:
        """Incognito session user_data_dir is NOT under sessions_root."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(
            session_id="incog",
            profile="incognito",
        )
        assert result["incognito"] is True
        user_dir = Path(result["user_data_dir"])
        assert user_dir.exists()
        # Temp dir should NOT be under the sessions root
        assert not str(user_dir).startswith(str(manager.sessions_root))

    def test_incognito_flag_overrides_profile(self, tmp_path: Path) -> None:
        """incognito=True forces incognito behavior even with named profile."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(
            session_id="forced-incog",
            profile="phuc-gmail",
            incognito=True,
        )
        assert result["incognito"] is True
        assert result["profile"] == "incognito"

    def test_incognito_cleanup_on_close(self, tmp_path: Path) -> None:
        """Incognito temp directory is removed when session closes."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(
            session_id="incog-cleanup",
            profile="incognito",
        )
        temp_dir = Path(result["user_data_dir"])
        assert temp_dir.exists()

        manager.close_session("incog-cleanup")
        assert not temp_dir.exists(), "Incognito temp dir should be cleaned up on close"

    def test_incognito_email_is_empty(self, tmp_path: Path) -> None:
        """Incognito sessions have empty user_email by default."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(
            session_id="incog-email",
            profile="incognito",
        )
        assert result["user_email"] == ""


# ---------------------------------------------------------------------------
# Port allocation
# ---------------------------------------------------------------------------

class TestPortAllocation:
    """Port allocation from the 9230-9250 range."""

    def test_ports_dont_collide(self, tmp_path: Path) -> None:
        """All allocated ports are unique."""
        manager = _make_manager(tmp_path)
        ports = set()
        for i in range(5):
            result = manager.create_session(
                session_id=f"port-test-{i}",
                profile="phuc-gmail",
                user_email=f"test{i}@example.com",
            )
            ports.add(result["port"])
        assert len(ports) == 5

    def test_ports_in_range(self, tmp_path: Path) -> None:
        """All ports are within the configured range."""
        manager = _make_manager(tmp_path)
        for i in range(3):
            result = manager.create_session(
                session_id=f"range-test-{i}",
                profile="phuc-gmail",
                user_email=f"test{i}@example.com",
            )
            assert PORT_RANGE_START <= result["port"] <= PORT_RANGE_END

    def test_port_exhaustion_raises(self, tmp_path: Path) -> None:
        """Exceeding port range -> PortExhaustionError, no silent degradation."""
        manager = _make_manager(tmp_path)
        max_sessions = PORT_RANGE_END - PORT_RANGE_START + 1

        # Fill all ports
        for i in range(max_sessions):
            manager.create_session(
                session_id=f"exhaust-{i}",
                profile="phuc-gmail",
                user_email=f"test{i}@example.com",
            )

        # Next one should fail
        with pytest.raises(PortExhaustionError, match="All ports"):
            manager.create_session(
                session_id="one-too-many",
                profile="phuc-gmail",
                user_email="overflow@example.com",
            )

    def test_port_reuse_after_close(self, tmp_path: Path) -> None:
        """Closed session's port becomes available again."""
        manager = _make_manager(tmp_path)
        s1 = manager.create_session(session_id="reuse-1", profile="phuc-gmail")
        port1 = s1["port"]
        manager.close_session("reuse-1")

        s2 = manager.create_session(session_id="reuse-2", profile="phuc-phucnet")
        assert s2["port"] == port1  # Port is reused (first available)

    def test_sequential_port_assignment(self, tmp_path: Path) -> None:
        """Ports are assigned sequentially starting from PORT_RANGE_START."""
        manager = _make_manager(tmp_path)
        s1 = manager.create_session(session_id="seq-1", profile="phuc-gmail")
        s2 = manager.create_session(session_id="seq-2", profile="phuc-phucnet")
        s3 = manager.create_session(session_id="seq-3", profile="phuc-phuclabs")

        assert s1["port"] == PORT_RANGE_START
        assert s2["port"] == PORT_RANGE_START + 1
        assert s3["port"] == PORT_RANGE_START + 2


# ---------------------------------------------------------------------------
# Session manifest
# ---------------------------------------------------------------------------

class TestSessionManifest:
    """Session manifest (session.json) is written on create and updated on close."""

    def test_manifest_written_on_create(self, tmp_path: Path) -> None:
        """session.json exists immediately after create_session."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(session_id="manifest-test", profile="phuc-gmail")
        manifest_path = Path(result["user_data_dir"]) / "session.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["session_id"] == "manifest-test"
        assert manifest["profile"] == "phuc-gmail"
        assert manifest["status"] == SESSION_STATUS_ACTIVE
        assert manifest["user_email"] == "user@example.com"

    def test_manifest_updated_on_close(self, tmp_path: Path) -> None:
        """session.json is updated with closed status and closed_at on close."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(session_id="manifest-close", profile="phuc-gmail")
        user_data_dir = Path(result["user_data_dir"])

        manager.close_session("manifest-close")

        manifest_path = user_data_dir / "session.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == SESSION_STATUS_CLOSED
        assert manifest["closed_at"] is not None

    def test_manifest_contains_actions_list(self, tmp_path: Path) -> None:
        """Manifest includes an actions list."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(session_id="actions-test", profile="phuc-gmail")
        manifest_path = Path(result["user_data_dir"]) / "session.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "actions" in manifest
        assert isinstance(manifest["actions"], list)

    def test_manifest_has_port_info(self, tmp_path: Path) -> None:
        """Manifest records the allocated port."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(session_id="port-manifest", profile="phuc-gmail")
        manifest_path = Path(result["user_data_dir"]) / "session.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["port"] == result["port"]


# ---------------------------------------------------------------------------
# Evidence chain
# ---------------------------------------------------------------------------

class TestEvidenceChain:
    """Evidence chain is written for session lifecycle events."""

    def test_evidence_written_on_create(self, tmp_path: Path) -> None:
        """Evidence chain file exists after session creation."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(session_id="evidence-test", profile="phuc-gmail")
        evidence_path = Path(result["user_data_dir"]) / "evidence_chain.jsonl"
        assert evidence_path.exists()

        lines = evidence_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1
        entry = json.loads(lines[0])
        assert entry["event"] == "session_created"
        assert entry["detail"]["session_id"] == "evidence-test"
        assert entry["detail"]["profile"] == "phuc-gmail"

    def test_evidence_hash_chained(self, tmp_path: Path) -> None:
        """Evidence entries are hash-chained (first entry links to GENESIS_HASH)."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(session_id="chain-test", profile="phuc-gmail")
        evidence_path = Path(result["user_data_dir"]) / "evidence_chain.jsonl"
        lines = evidence_path.read_text(encoding="utf-8").strip().splitlines()
        entry = json.loads(lines[0])
        assert entry["prev_hash"] == GENESIS_HASH
        assert "entry_hash" in entry
        assert len(entry["entry_hash"]) == 64

    def test_evidence_close_event_appended(self, tmp_path: Path) -> None:
        """Closing a session appends a session_closed event to evidence."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(session_id="close-evidence", profile="phuc-gmail")
        evidence_path = Path(result["user_data_dir"]) / "evidence_chain.jsonl"

        manager.close_session("close-evidence")

        lines = evidence_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 2
        close_entry = json.loads(lines[-1])
        assert close_entry["event"] == "session_closed"
        assert close_entry["detail"]["session_id"] == "close-evidence"
        assert "duration_seconds" in close_entry["detail"]


# ---------------------------------------------------------------------------
# Auth proxy integration
# ---------------------------------------------------------------------------

class TestAuthProxyIntegration:
    """Token registration and revocation with AuthProxy."""

    def test_token_registered_on_create(self, tmp_path: Path) -> None:
        """Creating a session registers a token with the auth proxy."""
        fake_proxy = _FakeAuthProxy()
        manager = _make_manager(tmp_path, auth_proxy=fake_proxy)
        manager.create_session(session_id="auth-test", profile="phuc-gmail")

        assert len(fake_proxy.registered_tokens) == 1

    def test_token_revoked_on_close(self, tmp_path: Path) -> None:
        """Closing a session revokes the token in the auth proxy."""
        fake_proxy = _FakeAuthProxy()
        manager = _make_manager(tmp_path, auth_proxy=fake_proxy)
        manager.create_session(session_id="revoke-test", profile="phuc-gmail")
        manager.close_session("revoke-test")

        assert len(fake_proxy.revoked_hashes) == 1

    def test_no_proxy_no_token(self, tmp_path: Path) -> None:
        """Without an auth proxy, sessions work without tokens."""
        manager = _make_manager(tmp_path)
        result = manager.create_session(session_id="no-proxy", profile="phuc-gmail")
        assert result["status"] == SESSION_STATUS_ACTIVE
        # No crash, session works without proxy


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:
    """Concurrent session operations must not corrupt state."""

    def test_concurrent_creates(self, tmp_path: Path) -> None:
        """Multiple threads creating sessions simultaneously."""
        manager = _make_manager(tmp_path)
        errors: list[str] = []
        results: list[dict[str, Any]] = []
        lock = threading.Lock()

        def create(index: int) -> None:
            try:
                result = manager.create_session(
                    session_id=f"concurrent-{index}",
                    profile="phuc-gmail",
                    user_email=f"thread{index}@example.com",
                )
                with lock:
                    results.append(result)
            except Exception as exc:
                with lock:
                    errors.append(f"Thread {index}: {exc}")

        threads = [threading.Thread(target=create, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during concurrent creates: {errors}"
        assert len(results) == 10
        ports = {r["port"] for r in results}
        assert len(ports) == 10, "All ports must be unique"

    def test_concurrent_create_and_close(self, tmp_path: Path) -> None:
        """Create and close operations don't deadlock."""
        manager = _make_manager(tmp_path)

        # Pre-create some sessions
        for i in range(5):
            manager.create_session(
                session_id=f"preexist-{i}",
                profile="phuc-gmail",
                user_email=f"pre{i}@example.com",
            )

        errors: list[str] = []

        def close(index: int) -> None:
            try:
                manager.close_session(f"preexist-{index}")
            except Exception as exc:
                errors.append(f"Close thread {index}: {exc}")

        def create(index: int) -> None:
            try:
                manager.create_session(
                    session_id=f"new-{index}",
                    profile="phuc-phucnet",
                    user_email=f"new{index}@example.com",
                )
            except Exception as exc:
                errors.append(f"Create thread {index}: {exc}")

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=close, args=(i,)))
            threads.append(threading.Thread(target=create, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during concurrent ops: {errors}"


# ---------------------------------------------------------------------------
# Profile resolution
# ---------------------------------------------------------------------------

class TestProfileResolution:
    """Profile name -> (email, scopes) resolution."""

    def test_all_preconfigured_profiles_exist(self) -> None:
        """All 4 expected profiles are defined."""
        expected = {"phuc-gmail", "phuc-phucnet", "phuc-phuclabs", "incognito"}
        assert set(PRECONFIGURED_PROFILES.keys()) == expected

    def test_each_profile_has_email_and_scopes(self) -> None:
        """Each profile tuple has (email, scopes_list)."""
        for name, (email, scopes) in PRECONFIGURED_PROFILES.items():
            assert isinstance(email, str), f"{name} email must be str"
            assert isinstance(scopes, list), f"{name} scopes must be list"
            assert all(isinstance(s, str) for s in scopes), f"{name} scopes must be str list"

    def test_incognito_profile_has_empty_email(self) -> None:
        """Incognito profile has empty email string."""
        email, _ = PRECONFIGURED_PROFILES["incognito"]
        assert email == ""
