# Diagram: 01-triangle-architecture
"""
history.py — Browsing Session History
Phase 2, BUILD 5: HTML Snapshot Capture

Manages ordered lists of Snapshots within a BrowsingSession.
Persists sessions to ~/.solace/history/ using content-addressed compressed files.

Directory layout:
    ~/.solace/history/
        {session_id}/
            index.jsonl           — one JSON line per snapshot (metadata only)
            {snapshot_id}.snap    — zlib-compressed full snapshot JSON

Rung: 641
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from snapshot import Snapshot, compress_snapshot, decompress_snapshot

# Default base directory for session storage
_DEFAULT_BASE_DIR = Path.home() / ".solace" / "history"


# ---------------------------------------------------------------------------
# BrowsingSession dataclass
# ---------------------------------------------------------------------------

@dataclass
class BrowsingSession:
    """
    Ordered collection of Snapshots for a single browsing task.

    Fields:
        session_id  — UUID4 string
        task_id     — optional task identifier (e.g. recipe task name)
        recipe_id   — optional recipe identifier
        started_at  — ISO8601 UTC string
        snapshots   — ordered list of Snapshot objects
    """
    session_id: str
    task_id: Optional[str] = None
    recipe_id: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    snapshots: List[Snapshot] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        task_id: Optional[str] = None,
        recipe_id: Optional[str] = None,
    ) -> "BrowsingSession":
        """Factory: create a new BrowsingSession with a fresh UUID4 session_id."""
        return cls(
            session_id=str(uuid.uuid4()),
            task_id=task_id,
            recipe_id=recipe_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            snapshots=[],
        )

    def add_snapshot(self, snapshot: Snapshot) -> None:
        """Append a Snapshot to this session (in order)."""
        self.snapshots.append(snapshot)

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)


# ---------------------------------------------------------------------------
# Index entry helpers
# ---------------------------------------------------------------------------

def _snapshot_to_index_entry(snapshot: Snapshot, compressed_size_bytes: int) -> Dict[str, Any]:
    """Build an index-line dict (lightweight metadata, no html)."""
    return {
        "snapshot_id": snapshot.snapshot_id,
        "url": snapshot.url,
        "title": snapshot.title,
        "timestamp": snapshot.timestamp,
        "compressed_size_bytes": compressed_size_bytes,
    }


def _session_to_header(session: BrowsingSession) -> Dict[str, Any]:
    """Build the session header line written to index.jsonl line 0."""
    return {
        "__type": "session_header",
        "session_id": session.session_id,
        "task_id": session.task_id,
        "recipe_id": session.recipe_id,
        "started_at": session.started_at,
    }


# ---------------------------------------------------------------------------
# Persistence: save / load
# ---------------------------------------------------------------------------

def save_session(
    session: BrowsingSession,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Persist a BrowsingSession to disk.

    Layout:
        {base_dir}/{session_id}/index.jsonl    — metadata lines (header + one per snapshot)
        {base_dir}/{session_id}/{snap_id}.snap — compressed snapshot blob

    Returns:
        Path to the session directory.
    """
    if base_dir is None:
        base_dir = _DEFAULT_BASE_DIR

    session_dir = Path(base_dir) / session.session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    index_path = session_dir / "index.jsonl"

    lines: List[str] = []

    # Line 0: session header
    lines.append(json.dumps(_session_to_header(session), ensure_ascii=False))

    for snapshot in session.snapshots:
        # Compress and write the snapshot blob
        compressed = compress_snapshot(snapshot)
        snap_path = session_dir / f"{snapshot.snapshot_id}.snap"
        snap_path.write_bytes(compressed)

        # Append index line
        entry = _snapshot_to_index_entry(snapshot, len(compressed))
        lines.append(json.dumps(entry, ensure_ascii=False))

    # Write index atomically (overwrite)
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return session_dir


def load_session(
    session_id: str,
    base_dir: Optional[Path] = None,
) -> BrowsingSession:
    """
    Load a BrowsingSession from disk (lazy: decompresses each snapshot).

    Raises:
        FileNotFoundError — if the session directory or index does not exist.

    Returns:
        BrowsingSession with all snapshots loaded (decompressed).
    """
    if base_dir is None:
        base_dir = _DEFAULT_BASE_DIR

    session_dir = Path(base_dir) / session_id
    index_path = session_dir / "index.jsonl"

    if not index_path.exists():
        raise FileNotFoundError(f"Session not found: {session_id} (looked in {session_dir})")

    lines = [
        line.strip()
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError(f"Session index is empty: {index_path}")

    # First line: session header
    header = json.loads(lines[0])
    if header.get("__type") != "session_header":
        raise ValueError(f"First line of index is not a session_header: {index_path}")

    session = BrowsingSession(
        session_id=header["session_id"],
        task_id=header.get("task_id"),
        recipe_id=header.get("recipe_id"),
        started_at=header.get("started_at", ""),
        snapshots=[],
    )

    # Remaining lines: snapshot index entries
    for line in lines[1:]:
        entry = json.loads(line)
        snap_id = entry["snapshot_id"]
        snap_path = session_dir / f"{snap_id}.snap"

        if not snap_path.exists():
            # Missing blob — skip with a warning rather than crashing
            continue

        snapshot = decompress_snapshot(snap_path.read_bytes())
        session.snapshots.append(snapshot)

    return session


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def list_sessions(
    base_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    List all sessions in base_dir.

    Returns:
        List of dicts: {session_id, task_id, recipe_id, started_at, snapshot_count}
        Sorted by started_at descending (most recent first).
    """
    if base_dir is None:
        base_dir = _DEFAULT_BASE_DIR

    base_dir = Path(base_dir)
    if not base_dir.exists():
        return []

    results: List[Dict[str, Any]] = []

    for session_dir in base_dir.iterdir():
        if not session_dir.is_dir():
            continue

        index_path = session_dir / "index.jsonl"
        if not index_path.exists():
            continue

        lines = [
            line.strip()
            for line in index_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        try:
            header = json.loads(lines[0])
        except (json.JSONDecodeError, IndexError):
            continue

        if header.get("__type") != "session_header":
            continue

        # Count snapshot lines (skip header line)
        snapshot_count = len(lines) - 1

        results.append({
            "session_id": header.get("session_id", session_dir.name),
            "task_id": header.get("task_id"),
            "recipe_id": header.get("recipe_id"),
            "started_at": header.get("started_at", ""),
            "snapshot_count": snapshot_count,
        })

    # Most recent first
    results.sort(key=lambda r: r["started_at"], reverse=True)
    return results


def get_snapshot(
    session_id: str,
    snapshot_id: str,
    base_dir: Optional[Path] = None,
) -> Snapshot:
    """
    Retrieve and decompress a single Snapshot from a session.

    Raises:
        FileNotFoundError — if session directory or snapshot blob is missing.

    Returns:
        Decompressed Snapshot.
    """
    if base_dir is None:
        base_dir = _DEFAULT_BASE_DIR

    snap_path = Path(base_dir) / session_id / f"{snapshot_id}.snap"

    if not snap_path.exists():
        raise FileNotFoundError(
            f"Snapshot not found: session={session_id} snapshot={snapshot_id}"
        )

    return decompress_snapshot(snap_path.read_bytes())


def list_session_snapshots(
    session_id: str,
    base_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Return metadata list for all snapshots in a session (reads index only, no decompression).

    Returns:
        List of {snapshot_id, url, title, timestamp, compressed_size_bytes}

    Raises:
        FileNotFoundError — if session not found.
    """
    if base_dir is None:
        base_dir = _DEFAULT_BASE_DIR

    session_dir = Path(base_dir) / session_id
    index_path = session_dir / "index.jsonl"

    if not index_path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")

    lines = [
        line.strip()
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Skip header line (line 0)
    snapshots_meta = []
    for line in lines[1:]:
        try:
            entry = json.loads(line)
            snapshots_meta.append(entry)
        except json.JSONDecodeError:
            continue

    return snapshots_meta
