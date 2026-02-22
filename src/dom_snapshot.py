"""
dom_snapshot.py — Dynamic DOM Snapshot System
Phase 2, BUILD 6: AI-Driven DOM Snapshot

Replaces static CSS selectors with AI-friendly ref-based DOM analysis.
Uses stdlib html.parser — no new external dependencies.

Design goals:
  - DOMRef: a stable, addressable reference to a single DOM element
  - DOMSnapshot: full page AI-friendly view (ARIA roles, interactive elements first)
  - DOMSnapshotEngine: capture, diff, find_ref, to_ai_context
  - Ref IDs are deterministic: sha256(role|name|path)[:12]

Rung: 641
"""

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# ARIA role mappings: HTML tag → ARIA role (W3C implicit mapping, condensed)
# ---------------------------------------------------------------------------

_TAG_TO_ROLE: Dict[str, str] = {
    "a": "link",
    "article": "article",
    "aside": "complementary",
    "button": "button",
    "details": "group",
    "dialog": "dialog",
    "figure": "figure",
    "footer": "contentinfo",
    "form": "form",
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "h5": "heading",
    "h6": "heading",
    "header": "banner",
    "hr": "separator",
    "img": "img",
    "input": "textbox",       # refined below by type attr
    "li": "listitem",
    "main": "main",
    "menu": "menu",
    "nav": "navigation",
    "ol": "list",
    "option": "option",
    "progress": "progressbar",
    "search": "search",
    "section": "region",
    "select": "listbox",
    "summary": "button",
    "table": "table",
    "tbody": "rowgroup",
    "td": "cell",
    "textarea": "textbox",
    "th": "columnheader",
    "thead": "rowgroup",
    "tr": "row",
    "ul": "list",
    "video": "application",
}

# Input types that map to specific ARIA roles
_INPUT_TYPE_TO_ROLE: Dict[str, str] = {
    "button": "button",
    "checkbox": "checkbox",
    "color": "textbox",
    "date": "textbox",
    "email": "textbox",
    "file": "button",
    "hidden": "none",
    "image": "button",
    "month": "textbox",
    "number": "spinbutton",
    "password": "textbox",
    "radio": "radio",
    "range": "slider",
    "reset": "button",
    "search": "searchbox",
    "submit": "button",
    "tel": "textbox",
    "text": "textbox",
    "time": "textbox",
    "url": "textbox",
    "week": "textbox",
}

# Tags that represent interactive elements (can receive user input or click)
_INTERACTIVE_TAGS = frozenset({
    "a", "button", "details", "input", "label", "option",
    "select", "summary", "textarea",
})


# ---------------------------------------------------------------------------
# DOMRef — single element reference
# ---------------------------------------------------------------------------

@dataclass
class DOMRef:
    """
    A stable reference to a DOM element found by AI analysis.

    ref_id is deterministic: sha256(role|name|path)[:12]
    """
    ref_id: str           # stable 12-char hash (sha256 of role+name+path)
    role: str             # ARIA role (button, textbox, link, etc.)
    name: str             # accessible name (aria-label > title > alt > placeholder > text)
    text: str             # visible text content (stripped)
    tag: str              # HTML tag (lowercase)
    path: str             # simplified CSS path (e.g. "form#login > input[type=email]")
    interactive: bool     # True if user can interact with this element
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DOMRef":
        return cls(
            ref_id=data["ref_id"],
            role=data["role"],
            name=data["name"],
            text=data["text"],
            tag=data["tag"],
            path=data["path"],
            interactive=data["interactive"],
            attributes=data.get("attributes", {}),
        )


# ---------------------------------------------------------------------------
# DOMSnapshot — AI-friendly page snapshot
# ---------------------------------------------------------------------------

@dataclass
class DOMSnapshot:
    """
    AI-friendly snapshot of page DOM structure.

    snapshot_id = sha256(url + "|" + timestamp + "|" + dom_hash)
    dom_hash    = sha256(serialized refs)
    """
    snapshot_id: str          # sha256(url + timestamp + dom_hash)
    url: str
    title: str
    timestamp: str            # ISO8601 UTC
    refs: List[DOMRef]        # all extracted DOM refs
    dom_hash: str             # sha256 of serialized refs (change detection)
    interactive_count: int    # count of interactive refs
    total_count: int          # total ref count

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DOMSnapshot":
        refs = [DOMRef.from_dict(r) for r in data.get("refs", [])]
        return cls(
            snapshot_id=data["snapshot_id"],
            url=data["url"],
            title=data["title"],
            timestamp=data["timestamp"],
            refs=refs,
            dom_hash=data["dom_hash"],
            interactive_count=data["interactive_count"],
            total_count=data["total_count"],
        )


# ---------------------------------------------------------------------------
# Internal HTML parser
# ---------------------------------------------------------------------------

class _DOMParser(HTMLParser):
    """
    SAX-style parser that walks the HTML tree and emits DOMRef objects.

    Strategy:
      - Maintain a path stack as we enter/leave tags
      - For each element, compute accessible name, role, text
      - Skip script/style/head/meta/link elements
      - Capture attributes that are useful to agents (href, type, value, etc.)
    """

    # Tags whose content we do NOT want as text (skip subtree text)
    _SKIP_TEXT_TAGS = frozenset({"script", "style", "noscript", "template"})

    # Tags to completely ignore (no ref emitted, but children still parsed)
    _IGNORE_TAGS = frozenset({
        "html", "head", "meta", "link", "base", "script",
        "style", "noscript", "template", "br", "hr",
        "path", "svg", "circle", "rect", "line", "polygon",
        "g", "defs", "use", "clippath", "mask",
    })

    # Void elements (no closing tag)
    _VOID_TAGS = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    })

    # Attributes to capture per element
    _CAPTURE_ATTRS = frozenset({
        "href", "src", "type", "value", "placeholder", "name", "id",
        "class", "aria-label", "aria-labelledby", "title", "alt",
        "for", "action", "method", "role", "disabled", "checked",
        "selected", "data-testid", "data-id", "aria-describedby",
    })

    def __init__(self) -> None:
        super().__init__()
        self.refs: List[DOMRef] = []
        self._path_stack: List[Tuple[str, Dict[str, str], int]] = []
        # (tag, attrs_dict, child_index_at_this_level)
        self._text_buffer: Dict[int, List[str]] = {}  # depth → collected text
        self._depth: int = 0
        self._skip_depth: Optional[int] = None   # suppress text inside this depth
        self._child_counters: List[int] = [0]   # count siblings at each depth

    # ------------------------------------------------------------------
    # HTMLParser callbacks
    # ------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attrs_dict: Dict[str, str] = {}
        for k, v in attrs:
            if k in self._CAPTURE_ATTRS:
                attrs_dict[k] = v or ""

        # Track child counters
        if len(self._child_counters) <= self._depth:
            self._child_counters.append(0)
        self._child_counters[self._depth] = self._child_counters[self._depth] + 1

        self._path_stack.append((tag, attrs_dict, self._child_counters[self._depth]))
        self._depth += 1

        # Extend child counters for next level
        if len(self._child_counters) <= self._depth:
            self._child_counters.append(0)
        else:
            self._child_counters[self._depth] = 0

        self._text_buffer[self._depth] = []

        # Track skip depth for script/style
        if tag in self._SKIP_TEXT_TAGS and self._skip_depth is None:
            self._skip_depth = self._depth

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if not self._path_stack:
            return

        # Find matching open tag (handle malformed HTML gracefully)
        close_idx = None
        for i in range(len(self._path_stack) - 1, -1, -1):
            if self._path_stack[i][0] == tag:
                close_idx = i
                break

        if close_idx is None:
            return

        # Pop any unmatched frames (handles missing close tags)
        while len(self._path_stack) > close_idx + 1:
            self._flush_element()

        self._flush_element()

    def handle_data(self, data: str) -> None:
        if self._skip_depth is not None:
            return
        text = data.strip()
        if text and self._depth in self._text_buffer:
            self._text_buffer[self._depth].append(text)

    # ------------------------------------------------------------------
    # Element flushing
    # ------------------------------------------------------------------

    def _flush_element(self) -> None:
        """Pop the top frame, build a DOMRef if warranted, emit it."""
        if not self._path_stack:
            return

        tag, attrs, child_idx = self._path_stack.pop()
        self._depth -= 1

        # Collect text from this element's own buffer
        my_text = " ".join(self._text_buffer.pop(self._depth + 1, []))

        # Bubble text up to parent
        if self._depth in self._text_buffer and my_text:
            self._text_buffer[self._depth].append(my_text)

        # Clear skip depth if we're leaving the skip block
        if self._skip_depth is not None and self._depth + 1 <= self._skip_depth:
            self._skip_depth = None

        # Skip ignored tags
        if tag in self._IGNORE_TAGS:
            return

        # Build CSS path
        path = self._build_path()

        # Compute role
        role = self._compute_role(tag, attrs)

        # Compute accessible name
        name = self._compute_name(tag, attrs, my_text)

        # Compute interactivity
        interactive = self._compute_interactive(tag, attrs)

        # Compute ref_id
        ref_id = DOMSnapshotEngine.compute_ref_id(role, name, path)

        ref = DOMRef(
            ref_id=ref_id,
            role=role,
            name=name,
            text=my_text[:500],   # cap visible text
            tag=tag,
            path=path,
            interactive=interactive,
            attributes={k: v for k, v in attrs.items()},
        )
        self.refs.append(ref)

    def _build_path(self) -> str:
        """Build a simplified CSS selector path from the current stack."""
        parts = []
        for tag, attrs, child_idx in self._path_stack:
            part = tag
            if "id" in attrs and attrs["id"]:
                part += f"#{attrs['id']}"
            elif "class" in attrs and attrs["class"]:
                cls = attrs["class"].split()[0]  # first class only
                part += f".{cls}"
            elif tag == "input" and "type" in attrs:
                part += f"[type={attrs['type']}]"
            elif tag == "input" and "name" in attrs:
                part += f"[name={attrs['name']}]"
            parts.append(part)
        return " > ".join(parts) if parts else ""

    def _compute_role(self, tag: str, attrs: Dict[str, str]) -> str:
        """Compute ARIA role: explicit aria-role > tag mapping > input-type mapping."""
        # Explicit ARIA role attribute wins
        if "role" in attrs and attrs["role"]:
            return attrs["role"]

        # Input type refinement
        if tag == "input":
            input_type = attrs.get("type", "text").lower()
            return _INPUT_TYPE_TO_ROLE.get(input_type, "textbox")

        # Tag-to-role mapping
        if tag in _TAG_TO_ROLE:
            return _TAG_TO_ROLE[tag]

        # Div/span with no role → generic
        return "generic"

    def _compute_name(self, tag: str, attrs: Dict[str, str], text: str) -> str:
        """
        Compute accessible name in priority order:
          aria-label > title > alt > placeholder > text > value > name attr
        """
        for key in ("aria-label", "title", "alt", "placeholder"):
            if key in attrs and attrs[key]:
                return attrs[key][:200]

        if text:
            # Collapse whitespace
            cleaned = " ".join(text.split())
            return cleaned[:200]

        for key in ("value", "name"):
            if key in attrs and attrs[key]:
                return attrs[key][:200]

        return ""

    def _compute_interactive(self, tag: str, attrs: Dict[str, str]) -> bool:
        """True if the element can receive user interaction."""
        if tag in _INTERACTIVE_TAGS:
            # hidden inputs are not interactive in practice
            if tag == "input" and attrs.get("type", "").lower() == "hidden":
                return False
            # disabled elements are not interactive
            if "disabled" in attrs:
                return False
            return True
        # Divs/spans with click handlers or tabindex might be interactive,
        # but we cannot detect JS listeners from static HTML — skip.
        return False

    def _finalize(self) -> None:
        """Flush all remaining open elements."""
        while self._path_stack:
            self._flush_element()

    def get_refs(self) -> List[DOMRef]:
        self._finalize()
        return self.refs


# ---------------------------------------------------------------------------
# DOMSnapshotEngine
# ---------------------------------------------------------------------------

class DOMSnapshotEngine:
    """
    Captures and analyzes DOM for AI-driven actions.

    All methods are pure / stateless (no browser required).
    The engine operates on raw HTML strings.
    """

    # ------------------------------------------------------------------
    # Static helper
    # ------------------------------------------------------------------

    @staticmethod
    def compute_ref_id(role: str, name: str, path: str) -> str:
        """
        Deterministic ref ID — sha256(role|name|path)[:12]

        Same inputs always produce the same 12-character hex string.
        """
        payload = f"{role}|{name}|{path}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

    # ------------------------------------------------------------------
    # capture
    # ------------------------------------------------------------------

    def capture(
        self,
        page_html: str,
        url: str,
        title: str,
        timestamp: Optional[str] = None,
    ) -> DOMSnapshot:
        """
        Parse HTML into an AI-friendly DOMSnapshot.

        Extracts all elements with ARIA roles and interactive elements.
        Generates stable ref_ids from role + accessible name + CSS path.

        Args:
            page_html: full HTML string (document.documentElement.outerHTML)
            url:       page URL
            title:     page title
            timestamp: ISO8601 UTC override (defaults to now)

        Returns:
            DOMSnapshot with stable ref_ids
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        parser = _DOMParser()
        try:
            parser.feed(page_html)
        except Exception:
            pass  # partial parse — use whatever refs we have
        refs = parser.get_refs()

        # Compute dom_hash from serialized refs
        dom_hash = self._compute_dom_hash(refs)

        # Compute snapshot_id
        snapshot_id = self._compute_snapshot_id(url, timestamp, dom_hash)

        interactive_count = sum(1 for r in refs if r.interactive)

        return DOMSnapshot(
            snapshot_id=snapshot_id,
            url=url,
            title=title,
            timestamp=timestamp,
            refs=refs,
            dom_hash=dom_hash,
            interactive_count=interactive_count,
            total_count=len(refs),
        )

    # ------------------------------------------------------------------
    # find_ref
    # ------------------------------------------------------------------

    def find_ref(self, snapshot: DOMSnapshot, query: str) -> Optional[DOMRef]:
        """
        Find the best matching DOMRef for a natural language query.

        Scoring (higher = better match):
          +10  role appears in query (e.g. "click the button")
          +8   name exact match (case-insensitive)
          +6   name contains query or query contains name
          +4   text exact match (case-insensitive)
          +3   text contains query token
          +2   tag appears in query
          +1   attribute value contains query token
          +5   ref_id exact match

        Returns the highest-scoring ref, or None if all scores are 0.
        """
        if not snapshot.refs:
            return None

        q = query.lower().strip()
        q_tokens = set(re.split(r"\W+", q)) - {"the", "a", "an", "on", ""}

        best_ref: Optional[DOMRef] = None
        best_score: int = 0

        for ref in snapshot.refs:
            score = 0

            # Exact ref_id match
            if ref.ref_id == q:
                score += 5

            role_lower = ref.role.lower()
            name_lower = ref.name.lower()
            text_lower = ref.text.lower()

            # Role match
            if role_lower in q or q in role_lower:
                score += 10

            # Name match
            if name_lower == q:
                score += 8
            elif name_lower and (name_lower in q or q in name_lower):
                score += 6

            # Text match
            if text_lower == q:
                score += 4
            else:
                for token in q_tokens:
                    if token and len(token) >= 2 and token in text_lower:
                        score += 3
                        break

            # Tag match
            if ref.tag in q:
                score += 2

            # Attribute value match
            for val in ref.attributes.values():
                if val and any(token in val.lower() for token in q_tokens if len(token) >= 2):
                    score += 1
                    break

            if score > best_score:
                best_score = score
                best_ref = ref

        return best_ref if best_score > 0 else None

    # ------------------------------------------------------------------
    # diff
    # ------------------------------------------------------------------

    def diff(self, old: DOMSnapshot, new: DOMSnapshot) -> Dict[str, List]:
        """
        Detect DOM changes between two snapshots.

        Compares by ref_id. A ref is "changed" if its name, text, or
        attributes changed while its ref_id stayed the same (which can
        happen when the path/role/name combination hashes the same but
        visible text differs — we track this separately via dom_hash).

        Returns:
            {
                "added":   [DOMRef, ...],   # in new but not old
                "removed": [DOMRef, ...],   # in old but not new
                "changed": [               # same ref_id, content differs
                    {"ref_id": str, "old": DOMRef, "new": DOMRef}, ...
                ],
            }
        """
        old_by_id: Dict[str, DOMRef] = {r.ref_id: r for r in old.refs}
        new_by_id: Dict[str, DOMRef] = {r.ref_id: r for r in new.refs}

        old_ids = set(old_by_id.keys())
        new_ids = set(new_by_id.keys())

        added = [new_by_id[rid] for rid in sorted(new_ids - old_ids)]
        removed = [old_by_id[rid] for rid in sorted(old_ids - new_ids)]

        changed = []
        for rid in sorted(old_ids & new_ids):
            o = old_by_id[rid]
            n = new_by_id[rid]
            if o.text != n.text or o.name != n.name or o.attributes != n.attributes:
                changed.append({"ref_id": rid, "old": o, "new": n})

        return {"added": added, "removed": removed, "changed": changed}

    # ------------------------------------------------------------------
    # to_ai_context
    # ------------------------------------------------------------------

    def to_ai_context(self, snapshot: DOMSnapshot, max_refs: int = 50) -> str:
        """
        Format snapshot for LLM context.

        Layout:
          Page: <title> (<url>)
          Refs: <interactive_count> interactive / <total_count> total
          <blank line>
          [ref_id] role "name" (text)
          ...

        Interactive elements come first, then content elements.
        Truncated to max_refs total.
        """
        interactive = [r for r in snapshot.refs if r.interactive]
        non_interactive = [r for r in snapshot.refs if not r.interactive]

        combined = interactive + non_interactive
        truncated = combined[:max_refs]

        lines = [
            f"Page: {snapshot.title} ({snapshot.url})",
            f"Refs: {snapshot.interactive_count} interactive / {snapshot.total_count} total",
            "",
        ]

        for ref in truncated:
            name_part = f'"{ref.name}"' if ref.name else '""'
            text_part = f" ({ref.text[:80]})" if ref.text and ref.text != ref.name else ""
            lines.append(f"[{ref.ref_id}] {ref.role} {name_part}{text_part}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_dom_hash(refs: List[DOMRef]) -> str:
        """sha256 of serialized ref list (ref_id|role|name|text joined)."""
        parts = [f"{r.ref_id}|{r.role}|{r.name}|{r.text}" for r in refs]
        payload = "\n".join(parts)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_snapshot_id(url: str, timestamp: str, dom_hash: str) -> str:
        """sha256(url + "|" + timestamp + "|" + dom_hash)"""
        payload = f"{url}|{timestamp}|{dom_hash}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
