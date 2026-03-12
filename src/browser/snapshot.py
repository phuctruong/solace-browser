"""
snapshot.py — HTML Snapshot Capture Module
Phase 2, BUILD 5: HTML Snapshot Capture

Captures full page HTML snapshots after recipe steps.
Content-addressed storage using sha256.
Compressed with zlib (stdlib, no external deps).

Rung: 641
"""

import hashlib
import json
import zlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Snapshot dataclass
# ---------------------------------------------------------------------------

@dataclass
class Snapshot:
    """
    Full-page HTML snapshot captured after a recipe step or navigation.

    Fields:
        snapshot_id     — sha256(url + timestamp + html_hash), hex string
        url             — page URL at capture time
        title           — page <title> at capture time
        timestamp       — ISO8601 UTC string
        html            — full page HTML (document.documentElement.outerHTML)
        form_state      — {css_selector: current_value} for all inputs/selects
        form_changes    — list of {selector, before, after} diffs
        network_requests— list of {url, method, response_size_bytes}
        viewport        — {width, height} in pixels
        scroll_position — {x, y} in pixels
        recipe_step     — {step_index, action, selector} — which recipe step triggered this
    """
    snapshot_id: str
    url: str
    title: str
    timestamp: str
    html: str
    form_state: Dict[str, Any] = field(default_factory=dict)
    form_changes: List[Dict[str, Any]] = field(default_factory=list)
    network_requests: List[Dict[str, Any]] = field(default_factory=list)
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})
    scroll_position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    recipe_step: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict (JSON-serializable)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """Deserialize from plain dict."""
        return cls(
            snapshot_id=data["snapshot_id"],
            url=data["url"],
            title=data["title"],
            timestamp=data["timestamp"],
            html=data["html"],
            form_state=data.get("form_state", {}),
            form_changes=data.get("form_changes", []),
            network_requests=data.get("network_requests", []),
            viewport=data.get("viewport", {"width": 1280, "height": 720}),
            scroll_position=data.get("scroll_position", {"x": 0, "y": 0}),
            recipe_step=data.get("recipe_step"),
        )


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def compute_snapshot_id(url: str, timestamp: str, html: str) -> str:
    """
    Compute a content-addressed snapshot ID.

    snapshot_id = sha256(url + "|" + timestamp + "|" + sha256(html))

    The inner sha256(html) means that two snapshots of the same URL at the
    same millisecond but with different HTML produce different IDs, while two
    snapshots with identical HTML at the same URL+timestamp are de-duplicated.

    Returns: hex string (64 chars)
    """
    html_hash = hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest()
    combined = f"{url}|{timestamp}|{html_hash}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _compute_form_changes(
    form_state_before: Optional[Dict[str, Any]],
    form_state_after: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Diff two form states and return a list of change records.

    Each change record: {selector, before, after}
    Only fields that differ (or are new) are included.
    """
    if form_state_before is None and form_state_after is None:
        return []

    before = form_state_before or {}
    after = form_state_after or {}

    changes: List[Dict[str, Any]] = []
    all_keys = set(before.keys()) | set(after.keys())

    for selector in sorted(all_keys):
        val_before = before.get(selector)
        val_after = after.get(selector)
        if val_before != val_after:
            changes.append({
                "selector": selector,
                "before": val_before,
                "after": val_after,
            })

    return changes


def capture_snapshot(
    page_html: str,
    url: str,
    title: str,
    step_info: Optional[Dict[str, Any]] = None,
    form_state_before: Optional[Dict[str, Any]] = None,
    form_state_after: Optional[Dict[str, Any]] = None,
    network_requests: Optional[List[Dict[str, Any]]] = None,
    viewport: Optional[Dict[str, int]] = None,
    scroll_position: Optional[Dict[str, int]] = None,
    timestamp: Optional[str] = None,
) -> "Snapshot":
    """
    Capture an HTML snapshot.

    Args:
        page_html           — full page HTML string
        url                 — current page URL
        title               — page title
        step_info           — {step_index, action, selector} of the recipe step
        form_state_before   — form state dict before the step (optional)
        form_state_after    — form state dict after the step (used as current form_state)
        network_requests    — list of network request dicts captured during the step
        viewport            — {width, height} override
        scroll_position     — {x, y} override
        timestamp           — ISO8601 UTC string override (defaults to now)

    Returns:
        Snapshot dataclass instance
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    snapshot_id = compute_snapshot_id(url, timestamp, page_html)

    # Use form_state_after as the captured form state (reflects the page state now)
    form_state = form_state_after if form_state_after is not None else {}

    # Compute form changes
    form_changes = _compute_form_changes(form_state_before, form_state_after)

    return Snapshot(
        snapshot_id=snapshot_id,
        url=url,
        title=title,
        timestamp=timestamp,
        html=page_html,
        form_state=form_state,
        form_changes=form_changes,
        network_requests=network_requests or [],
        viewport=viewport or {"width": 1280, "height": 720},
        scroll_position=scroll_position or {"x": 0, "y": 0},
        recipe_step=step_info,
    )


# ---------------------------------------------------------------------------
# Compression helpers (zlib, stdlib only)
# ---------------------------------------------------------------------------

def compress_snapshot(snapshot: Snapshot) -> bytes:
    """
    Serialize and compress a Snapshot to bytes using zlib (level 9).

    Returns: compressed bytes
    """
    json_bytes = json.dumps(snapshot.to_dict(), ensure_ascii=False).encode("utf-8")
    return zlib.compress(json_bytes, level=9)


def decompress_snapshot(compressed_bytes: bytes) -> Snapshot:
    """
    Decompress and deserialize a Snapshot from compressed bytes.

    Returns: Snapshot dataclass instance
    """
    json_bytes = zlib.decompress(compressed_bytes)
    data = json.loads(json_bytes.decode("utf-8"))
    return Snapshot.from_dict(data)
