"""
test_snapshot.py — Acceptance Tests for HTML Snapshot Capture
Phase 2, BUILD 5: HTML Snapshot Capture

12 tests covering snapshot.py and history.py.
Pure Python, no server required.

Rung: 641

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_snapshot.py -v
"""

import json
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Ensure src/ is on sys.path for local imports
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from snapshot import (
    Snapshot,
    capture_snapshot,
    compute_snapshot_id,
    compress_snapshot,
    decompress_snapshot,
)
from history import (
    BrowsingSession,
    get_snapshot,
    list_sessions,
    load_session,
    save_session,
)

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

SAMPLE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Test Page</title>
  <link rel="stylesheet" href="/static/main.css">
  <style>body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }</style>
</head>
<body>
  <header><h1>Welcome to Test Page</h1></header>
  <main>
    <p>This is a paragraph with some content.</p>
    <form id="login-form">
      <label for="email">Email:</label>
      <input type="email" id="email" name="email" placeholder="you@example.com">
      <label for="password">Password:</label>
      <input type="password" id="password" name="password">
      <button type="submit">Sign In</button>
    </form>
  </main>
  <footer><p>&copy; 2026 Test Page</p></footer>
</body>
</html>
"""

LARGE_HTML = SAMPLE_HTML * 200  # ~100KB — for compression ratio test


def make_snapshot(
    url: str = "https://example.com/page",
    title: str = "Test Page",
    html: str = SAMPLE_HTML,
    step_info: dict = None,
    form_state_before: dict = None,
    form_state_after: dict = None,
    timestamp: str = None,
) -> Snapshot:
    return capture_snapshot(
        page_html=html,
        url=url,
        title=title,
        step_info=step_info or {"step_index": 0, "action": "navigate", "selector": None},
        form_state_before=form_state_before,
        form_state_after=form_state_after,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Test 1: capture_snapshot creates a valid Snapshot
# ---------------------------------------------------------------------------

class TestCaptureSnapshot:
    def test_capture_snapshot_creates_valid_snapshot(self):
        snap = make_snapshot()

        assert isinstance(snap, Snapshot)
        assert snap.snapshot_id != ""
        assert len(snap.snapshot_id) == 64  # sha256 hex
        assert snap.url == "https://example.com/page"
        assert snap.title == "Test Page"
        assert snap.html == SAMPLE_HTML
        assert isinstance(snap.timestamp, str) and "T" in snap.timestamp
        assert isinstance(snap.form_state, dict)
        assert isinstance(snap.form_changes, list)
        assert isinstance(snap.viewport, dict)
        assert isinstance(snap.scroll_position, dict)
        assert snap.recipe_step is not None


# ---------------------------------------------------------------------------
# Test 2: snapshot_id is deterministic (same inputs → same sha256)
# ---------------------------------------------------------------------------

class TestSnapshotIdDeterminism:
    def test_snapshot_id_is_deterministic(self):
        ts = "2026-02-21T10:00:00+00:00"
        id1 = compute_snapshot_id("https://example.com", ts, SAMPLE_HTML)
        id2 = compute_snapshot_id("https://example.com", ts, SAMPLE_HTML)
        assert id1 == id2

    def test_snapshot_id_changes_with_different_html(self):
        ts = "2026-02-21T10:00:00+00:00"
        url = "https://example.com"
        id1 = compute_snapshot_id(url, ts, "<html>version 1</html>")
        id2 = compute_snapshot_id(url, ts, "<html>version 2</html>")
        assert id1 != id2

    def test_snapshot_id_changes_with_different_url(self):
        ts = "2026-02-21T10:00:00+00:00"
        id1 = compute_snapshot_id("https://site-a.com", ts, SAMPLE_HTML)
        id2 = compute_snapshot_id("https://site-b.com", ts, SAMPLE_HTML)
        assert id1 != id2


# ---------------------------------------------------------------------------
# Test 3: form state is captured
# ---------------------------------------------------------------------------

class TestFormState:
    def test_form_state_captured(self):
        form_state = {
            "input#email": "alice@example.com",
            "input#password": "",
            "select#country": "US",
        }
        snap = make_snapshot(form_state_after=form_state)
        assert snap.form_state == form_state

    def test_form_state_empty_when_not_provided(self):
        snap = make_snapshot()
        assert snap.form_state == {}


# ---------------------------------------------------------------------------
# Test 4: form changes are computed
# ---------------------------------------------------------------------------

class TestFormChanges:
    def test_form_changes_computed(self):
        before = {
            "input#email": "",
            "input#password": "",
        }
        after = {
            "input#email": "alice@example.com",
            "input#password": "secret",
        }
        snap = capture_snapshot(
            page_html=SAMPLE_HTML,
            url="https://example.com/login",
            title="Login",
            step_info={"step_index": 1, "action": "fill", "selector": "input#email"},
            form_state_before=before,
            form_state_after=after,
        )
        assert len(snap.form_changes) == 2

        changes_by_selector = {c["selector"]: c for c in snap.form_changes}
        assert changes_by_selector["input#email"]["before"] == ""
        assert changes_by_selector["input#email"]["after"] == "alice@example.com"
        assert changes_by_selector["input#password"]["before"] == ""
        assert changes_by_selector["input#password"]["after"] == "secret"

    def test_form_changes_empty_when_no_diff(self):
        state = {"input#email": "same@example.com"}
        snap = capture_snapshot(
            page_html=SAMPLE_HTML,
            url="https://example.com",
            title="Test",
            form_state_before=state,
            form_state_after=state,
        )
        assert snap.form_changes == []

    def test_form_changes_includes_new_fields(self):
        """A field present in after but not in before should appear as a change."""
        before = {}
        after = {"input#email": "new@example.com"}
        snap = capture_snapshot(
            page_html=SAMPLE_HTML,
            url="https://example.com",
            title="Test",
            form_state_before=before,
            form_state_after=after,
        )
        assert len(snap.form_changes) == 1
        assert snap.form_changes[0]["selector"] == "input#email"
        assert snap.form_changes[0]["before"] is None
        assert snap.form_changes[0]["after"] == "new@example.com"


# ---------------------------------------------------------------------------
# Test 5: compress / decompress round trip
# ---------------------------------------------------------------------------

class TestCompression:
    def test_compress_decompress_round_trip(self):
        snap = make_snapshot()
        compressed = compress_snapshot(snap)
        recovered = decompress_snapshot(compressed)

        assert isinstance(compressed, bytes)
        assert len(compressed) > 0
        assert recovered.snapshot_id == snap.snapshot_id
        assert recovered.url == snap.url
        assert recovered.html == snap.html
        assert recovered.form_state == snap.form_state
        assert recovered.form_changes == snap.form_changes

    def test_compression_ratio_greater_than_2x(self):
        """HTML should compress at least 2x with zlib level 9."""
        snap = make_snapshot(html=LARGE_HTML)
        original_bytes = json.dumps(snap.to_dict()).encode("utf-8")
        compressed = compress_snapshot(snap)
        ratio = len(original_bytes) / len(compressed)
        assert ratio > 2.0, (
            f"Expected compression ratio > 2x, got {ratio:.2f}x "
            f"(original={len(original_bytes)}, compressed={len(compressed)})"
        )


# ---------------------------------------------------------------------------
# Test 6: Snapshot to_dict / from_dict round trip
# ---------------------------------------------------------------------------

class TestSnapshotSerialization:
    def test_snapshot_to_dict_from_dict_round_trip(self):
        before = {"input#q": ""}
        after = {"input#q": "solace browser"}
        step = {"step_index": 3, "action": "fill", "selector": "input#q"}
        snap = capture_snapshot(
            page_html=SAMPLE_HTML,
            url="https://example.com/search",
            title="Search",
            step_info=step,
            form_state_before=before,
            form_state_after=after,
            viewport={"width": 1920, "height": 1080},
            scroll_position={"x": 0, "y": 250},
        )

        d = snap.to_dict()
        assert isinstance(d, dict)
        assert d["snapshot_id"] == snap.snapshot_id
        assert d["html"] == SAMPLE_HTML

        recovered = Snapshot.from_dict(d)
        assert recovered.snapshot_id == snap.snapshot_id
        assert recovered.url == snap.url
        assert recovered.html == snap.html
        assert recovered.form_state == after
        assert recovered.viewport == {"width": 1920, "height": 1080}
        assert recovered.scroll_position == {"x": 0, "y": 250}
        assert recovered.recipe_step == step


# ---------------------------------------------------------------------------
# Test 7: Session persistence — save / load
# ---------------------------------------------------------------------------

class TestSessionPersistence:
    def test_save_session_creates_index(self, tmp_path):
        session = BrowsingSession.create(task_id="test-task", recipe_id="linkedin-post")
        snap1 = make_snapshot(url="https://example.com/1", title="Page 1")
        snap2 = make_snapshot(url="https://example.com/2", title="Page 2")
        session.add_snapshot(snap1)
        session.add_snapshot(snap2)

        save_session(session, base_dir=tmp_path)

        session_dir = tmp_path / session.session_id
        assert session_dir.is_dir()

        index_path = session_dir / "index.jsonl"
        assert index_path.exists()

        lines = [l for l in index_path.read_text().splitlines() if l.strip()]
        # 1 header + 2 snapshot lines
        assert len(lines) == 3

        # Each snapshot file must exist
        assert (session_dir / f"{snap1.snapshot_id}.snap").exists()
        assert (session_dir / f"{snap2.snapshot_id}.snap").exists()

    def test_load_session_returns_correct_snapshots(self, tmp_path):
        session = BrowsingSession.create(task_id="load-test")
        snap1 = make_snapshot(
            url="https://example.com/a",
            title="Page A",
            timestamp="2026-02-21T10:00:00+00:00",
        )
        snap2 = make_snapshot(
            url="https://example.com/b",
            title="Page B",
            timestamp="2026-02-21T10:01:00+00:00",
        )
        session.add_snapshot(snap1)
        session.add_snapshot(snap2)

        save_session(session, base_dir=tmp_path)

        loaded = load_session(session.session_id, base_dir=tmp_path)

        assert loaded.session_id == session.session_id
        assert loaded.task_id == "load-test"
        assert len(loaded.snapshots) == 2
        assert loaded.snapshots[0].url == "https://example.com/a"
        assert loaded.snapshots[1].url == "https://example.com/b"
        assert loaded.snapshots[0].html == SAMPLE_HTML

    def test_list_sessions_returns_all(self, tmp_path):
        for i in range(3):
            session = BrowsingSession.create(task_id=f"task-{i}")
            snap = make_snapshot(url=f"https://example.com/{i}", title=f"Page {i}")
            session.add_snapshot(snap)
            save_session(session, base_dir=tmp_path)

        sessions = list_sessions(base_dir=tmp_path)

        assert len(sessions) == 3
        task_ids = {s["task_id"] for s in sessions}
        assert task_ids == {"task-0", "task-1", "task-2"}
        # Each session should report 1 snapshot
        for s in sessions:
            assert s["snapshot_count"] == 1

    def test_get_snapshot_decompresses(self, tmp_path):
        session = BrowsingSession.create(task_id="decompress-test")
        snap = make_snapshot(
            url="https://example.com/target",
            title="Target Page",
            timestamp="2026-02-21T12:00:00+00:00",
        )
        session.add_snapshot(snap)
        save_session(session, base_dir=tmp_path)

        recovered = get_snapshot(session.session_id, snap.snapshot_id, base_dir=tmp_path)

        assert recovered.snapshot_id == snap.snapshot_id
        assert recovered.url == "https://example.com/target"
        assert recovered.html == SAMPLE_HTML
        assert recovered.title == "Target Page"

    def test_load_session_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_session("nonexistent-session-id", base_dir=tmp_path)

    def test_list_sessions_empty_dir_returns_empty_list(self, tmp_path):
        sessions = list_sessions(base_dir=tmp_path)
        assert sessions == []
