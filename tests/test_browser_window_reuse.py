# Diagram: 05-solace-runtime-architecture
"""Tests for browser window reuse (Task: fix duplicate windows bug).

Verifies that:
1. _find_existing_controlled_session uses PID liveness, not a time window
2. _find_live_session_for_profile finds any alive session for a profile
3. reuse_window=True (default) opens new tab in existing window instead of spawning
4. reuse_window=False falls through to spawn a new window
5. Dead sessions (PID not alive) are skipped by both finders
"""
import os
import sys
import json
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "c" * 64


class FakeServer:
    cloud_twin_mode = False


class FakeHandler(ys.YinyangHandler):
    def __init__(self, token=VALID_TOKEN):
        self._responses = []
        self._body = b""
        self._token = token
        self.headers = {"content-length": "0", "Authorization": f"Bearer {token}"}
        self.server = FakeServer()

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _tracker_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass

    def _resolve_local_browser_binary(self):
        from pathlib import Path
        return Path("/usr/bin/chromium-browser")


# ── helpers ──────────────────────────────────────────────────────────────────

def _seed_session(session_id, pid, profile="default", url="https://example.com",
                  mode="standard", head_hidden=False, started_ago=0):
    ys._SESSIONS[session_id] = {
        "url": url,
        "profile": profile,
        "pid": pid,
        "started_at": int(time.time()) - started_ago,
        "mode": mode,
        "head_hidden": head_hidden,
        "source": "test",
        "user_data_dir": f"/tmp/test-session-{session_id}",
    }


def _clear_sessions():
    ys._SESSIONS.clear()
    ys._RECENT_BROWSER_LAUNCHES.clear()
    ys._INFLIGHT_BROWSER_LAUNCHES.clear()


# ── _find_existing_controlled_session ────────────────────────────────────────

class TestFindExistingControlledSession:
    """Dedup by exact URL — must use PID liveness, not time window."""

    def test_returns_alive_session_regardless_of_age(self):
        _clear_sessions()
        _seed_session("s1", pid=12345, url="https://example.com", started_ago=3600)
        h = FakeHandler()
        with patch.object(h, "_is_session_alive", return_value=True):
            result = h._find_existing_controlled_session(
                url="https://example.com", profile="default",
                mode="standard", head_hidden=False,
            )
        assert result is not None
        assert result[0] == "s1"

    def test_skips_dead_session_even_if_recently_started(self):
        _clear_sessions()
        _seed_session("s2", pid=99999, url="https://example.com", started_ago=0)
        h = FakeHandler()
        with patch.object(h, "_is_session_alive", return_value=False):
            result = h._find_existing_controlled_session(
                url="https://example.com", profile="default",
                mode="standard", head_hidden=False,
            )
        assert result is None

    def test_no_match_on_different_url(self):
        _clear_sessions()
        _seed_session("s3", pid=12345, url="https://other.com", started_ago=1)
        h = FakeHandler()
        with patch.object(h, "_is_session_alive", return_value=True):
            result = h._find_existing_controlled_session(
                url="https://example.com", profile="default",
                mode="standard", head_hidden=False,
            )
        assert result is None


# ── _find_live_session_for_profile ───────────────────────────────────────────

class TestFindLiveSessionForProfile:
    """Find any alive session for a profile regardless of URL."""

    def test_finds_alive_session_with_different_url(self):
        _clear_sessions()
        _seed_session("s10", pid=55555, url="https://google.com", profile="work")
        h = FakeHandler()
        with patch.object(h, "_is_session_alive", return_value=True):
            result = h._find_live_session_for_profile("work")
        assert result is not None
        assert result[0] == "s10"

    def test_skips_dead_session(self):
        _clear_sessions()
        _seed_session("s11", pid=99998, url="https://google.com", profile="work")
        h = FakeHandler()
        with patch.object(h, "_is_session_alive", return_value=False):
            result = h._find_live_session_for_profile("work")
        assert result is None

    def test_profile_mismatch_returns_none(self):
        _clear_sessions()
        _seed_session("s12", pid=44444, url="https://example.com", profile="personal")
        h = FakeHandler()
        with patch.object(h, "_is_session_alive", return_value=True):
            result = h._find_live_session_for_profile("work")
        assert result is None


# ── _open_url_in_existing_window ─────────────────────────────────────────────

class TestOpenUrlInExistingWindow:
    """Should launch browser with user_data_dir but NO --new-window."""

    def test_no_new_window_flag(self):
        h = FakeHandler()
        session = {
            "profile": "default",
            "user_data_dir": "/tmp/test-ud",
            "pid": 1234,
        }
        launched_args = []
        def fake_popen(args, **kwargs):
            launched_args.extend(args)
            m = MagicMock()
            m.pid = 9999
            return m

        with patch("subprocess.Popen", side_effect=fake_popen):
            h._open_url_in_existing_window(session, "https://new-tab.com")

        assert "https://new-tab.com" in launched_args
        assert "--new-window" not in launched_args

    def test_user_data_dir_passed(self):
        h = FakeHandler()
        session = {
            "profile": "work",
            "user_data_dir": "/tmp/myprofile",
            "pid": 1234,
        }
        launched_args = []
        def fake_popen(args, **kwargs):
            launched_args.extend(args)
            m = MagicMock()
            m.pid = 9999
            return m

        with patch("subprocess.Popen", side_effect=fake_popen):
            h._open_url_in_existing_window(session, "https://example.com")

        assert any("--user-data-dir=/tmp/myprofile" in a for a in launched_args)
        assert "--profile-directory=work" in launched_args


# ── reuse_window integration ──────────────────────────────────────────────────

class TestReuseWindowIntegration:
    """_launch_controlled_browser_session with reuse_window=True should
    open a new tab in an existing window rather than spawning a new one."""

    def test_reuse_window_true_calls_open_in_existing(self):
        _clear_sessions()
        _seed_session("s20", pid=77777, profile="default", url="https://existing.com")
        h = FakeHandler()

        opened_in_existing = []

        def fake_open_in_existing(session, url):
            opened_in_existing.append(url)

        with patch.object(h, "_is_session_alive", return_value=True), \
             patch.object(h, "_open_url_in_existing_window",
                          side_effect=fake_open_in_existing):
            h._launch_controlled_browser_session(
                url="https://new-page.com",
                profile="default",
                mode="standard",
                session_name_raw="",
                head_hidden=False,
                source="test",
                reuse_window=True,
            )

        assert "https://new-page.com" in opened_in_existing
        assert len(h._responses) == 1
        code, body = h._responses[0]
        assert code == 200
        assert body.get("reused_window") is True
        assert body.get("session_id") == "s20"

    def test_reuse_window_false_spawns_new_window(self):
        _clear_sessions()
        _seed_session("s21", pid=77778, profile="default", url="https://existing.com")
        h = FakeHandler()

        spawned = []

        def fake_spawn(url, profile, **kwargs):
            spawned.append(url)
            return {"pid": 88888, "head_hidden": False,
                    "xvfb_pid": None, "hidden_display": None}

        with patch.object(h, "_is_session_alive", return_value=True), \
             patch.object(h, "_spawn_browser_session", side_effect=fake_spawn):
            h._launch_controlled_browser_session(
                url="https://brand-new.com",
                profile="default",
                mode="standard",
                session_name_raw="",
                head_hidden=False,
                source="test",
                reuse_window=False,
                allow_duplicate=False,
            )

        assert "https://brand-new.com" in spawned

    def test_reuse_window_true_no_live_session_spawns_new(self):
        """When no live session exists, reuse_window still spawns a new window."""
        _clear_sessions()
        h = FakeHandler()

        spawned = []

        def fake_spawn(url, profile, **kwargs):
            spawned.append(url)
            return {"pid": 88889, "head_hidden": False,
                    "xvfb_pid": None, "hidden_display": None}

        with patch.object(h, "_is_session_alive", return_value=False), \
             patch.object(h, "_spawn_browser_session", side_effect=fake_spawn):
            h._launch_controlled_browser_session(
                url="https://first-window.com",
                profile="default",
                mode="standard",
                session_name_raw="",
                head_hidden=False,
                source="test",
                reuse_window=True,
            )

        assert "https://first-window.com" in spawned


class TestSessionPersistence:
    """Session persistence survives server restart — prevents N-browser spawns."""

    def test_persist_sessions_writes_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ys, "_SESSIONS_PERSIST_PATH", tmp_path / "sessions.json")
        _clear_sessions()
        _seed_session("persist-s1", pid=os.getpid(), url="https://x.com")
        ys._persist_sessions()
        data = json.loads((tmp_path / "sessions.json").read_text())
        assert "persist-s1" in data

    def test_load_sessions_from_disk_restores_alive(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ys, "_SESSIONS_PERSIST_PATH", tmp_path / "sessions.json")
        alive_pid = os.getpid()
        snapshot = {
            "s-alive": {"pid": alive_pid, "url": "https://a.com", "profile": "default",
                        "mode": "standard", "head_hidden": False, "started_at": 1},
        }
        (tmp_path / "sessions.json").write_text(json.dumps(snapshot))
        _clear_sessions()
        ys._load_sessions_from_disk()
        with ys._SESSIONS_LOCK:
            assert "s-alive" in ys._SESSIONS

    def test_load_sessions_from_disk_drops_dead(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ys, "_SESSIONS_PERSIST_PATH", tmp_path / "sessions.json")
        snapshot = {
            "s-dead": {"pid": 9999999, "url": "https://b.com", "profile": "default",
                       "mode": "standard", "head_hidden": False, "started_at": 1},
        }
        (tmp_path / "sessions.json").write_text(json.dumps(snapshot))
        _clear_sessions()
        ys._load_sessions_from_disk()
        with ys._SESSIONS_LOCK:
            assert "s-dead" not in ys._SESSIONS
