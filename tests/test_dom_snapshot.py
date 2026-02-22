"""
test_dom_snapshot.py — Acceptance Tests for Dynamic DOM Snapshot System
Phase 2, BUILD 6: AI-Driven DOM Snapshot + Action Engine

~60 tests across 6 test classes:
  1. TestDOMRef          (8)  — dataclass fields, ref_id, interactive flag
  2. TestDOMSnapshot     (10) — capture, refs, dom_hash, change detection
  3. TestDOMSnapshotEngine (12) — ARIA roles, interactive priority, fuzzy match, diff, context
  4. TestActionEngine    (12) — execute, unsupported action, ref resolution, evidence
  5. TestRefStability    (8)  — determinism, minor changes, collision resistance
  6. TestAIContext       (10) — interactive-first, truncation, format spec

Pure Python, no browser required, no external dependencies.

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_dom_snapshot.py -v

Rung: 641
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src/ is on sys.path for local imports
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dom_snapshot import (
    DOMRef,
    DOMSnapshot,
    DOMSnapshotEngine,
)
from action_engine import (
    ActionEngine,
    ActionResult,
    _parse_action_from_instruction,
    _parse_value_from_instruction,
)


# ===========================================================================
# Shared HTML fixtures
# ===========================================================================

LOGIN_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Login Page</title>
</head>
<body>
  <header>
    <h1>Welcome Back</h1>
    <nav>
      <a href="/home">Home</a>
      <a href="/about">About</a>
    </nav>
  </header>
  <main>
    <form id="login-form" action="/auth/login" method="POST">
      <label for="email">Email Address</label>
      <input type="email" id="email" name="email" placeholder="you@example.com" />
      <label for="password">Password</label>
      <input type="password" id="password" name="password" placeholder="••••••••" />
      <button type="submit" id="login-btn">Sign In</button>
      <a href="/forgot-password">Forgot password?</a>
    </form>
  </main>
  <footer>
    <p>© 2026 SolaceAGI</p>
  </footer>
</body>
</html>
"""

SEARCH_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Search</title></head>
<body>
  <nav>
    <a href="/">Home</a>
    <a href="/docs">Docs</a>
  </nav>
  <main>
    <form id="search-form">
      <input type="search" id="q" name="q" placeholder="Search..." />
      <button type="submit">Search</button>
    </form>
    <section>
      <h2>Results</h2>
      <ul>
        <li><a href="/result/1">First Result</a></li>
        <li><a href="/result/2">Second Result</a></li>
        <li><a href="/result/3">Third Result</a></li>
      </ul>
    </section>
  </main>
</body>
</html>
"""

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
  <header>
    <button id="menu-toggle" aria-label="Open menu">&#9776;</button>
    <h1>Dashboard</h1>
  </header>
  <main>
    <section>
      <h2>Stats</h2>
      <p>Total users: 1,234</p>
      <p>Active sessions: 56</p>
    </section>
    <section>
      <h2>Actions</h2>
      <button id="export-btn">Export CSV</button>
      <button id="refresh-btn" disabled>Refresh</button>
      <select id="period-select" name="period">
        <option value="day">Today</option>
        <option value="week">This Week</option>
        <option value="month">This Month</option>
      </select>
      <textarea id="notes" name="notes" placeholder="Add notes..."></textarea>
    </section>
  </main>
</body>
</html>
"""

EMPTY_HTML = "<html><head><title>Empty</title></head><body></body></html>"

ARIA_HTML = """\
<html>
<head><title>ARIA Test</title></head>
<body>
  <div role="button" aria-label="Custom Button">Click me</div>
  <div role="textbox" aria-label="Custom Input"></div>
  <div role="navigation" aria-label="Main Nav">
    <a href="/x">Item X</a>
  </div>
  <span role="alert">Important message</span>
</body>
</html>
"""


def make_engine() -> DOMSnapshotEngine:
    return DOMSnapshotEngine()


def make_snapshot(html: str = LOGIN_HTML, url: str = "https://example.com/login",
                  title: str = "Login Page",
                  timestamp: str = "2026-02-21T10:00:00+00:00") -> DOMSnapshot:
    engine = make_engine()
    return engine.capture(html, url, title, timestamp=timestamp)


def make_ref(
    ref_id: str = "abc123def456",
    role: str = "button",
    name: str = "Sign In",
    text: str = "Sign In",
    tag: str = "button",
    path: str = "form#login-form > button#login-btn",
    interactive: bool = True,
    attributes: dict = None,
) -> DOMRef:
    return DOMRef(
        ref_id=ref_id,
        role=role,
        name=name,
        text=text,
        tag=tag,
        path=path,
        interactive=interactive,
        attributes=attributes or {"type": "submit", "id": "login-btn"},
    )


# ===========================================================================
# 1. TestDOMRef — dataclass fields, ref_id, interactive flag
# ===========================================================================

class TestDOMRef:
    def test_domref_has_all_required_fields(self):
        ref = make_ref()
        assert hasattr(ref, "ref_id")
        assert hasattr(ref, "role")
        assert hasattr(ref, "name")
        assert hasattr(ref, "text")
        assert hasattr(ref, "tag")
        assert hasattr(ref, "path")
        assert hasattr(ref, "interactive")
        assert hasattr(ref, "attributes")

    def test_domref_field_types(self):
        ref = make_ref()
        assert isinstance(ref.ref_id, str)
        assert isinstance(ref.role, str)
        assert isinstance(ref.name, str)
        assert isinstance(ref.text, str)
        assert isinstance(ref.tag, str)
        assert isinstance(ref.path, str)
        assert isinstance(ref.interactive, bool)
        assert isinstance(ref.attributes, dict)

    def test_domref_interactive_true_for_button(self):
        ref = make_ref(tag="button", interactive=True)
        assert ref.interactive is True

    def test_domref_interactive_false_for_paragraph(self):
        ref = make_ref(tag="p", interactive=False)
        assert ref.interactive is False

    def test_compute_ref_id_is_12_chars(self):
        ref_id = DOMSnapshotEngine.compute_ref_id("button", "Sign In", "form > button")
        assert len(ref_id) == 12

    def test_compute_ref_id_is_hex(self):
        ref_id = DOMSnapshotEngine.compute_ref_id("textbox", "Email", "form > input")
        assert all(c in "0123456789abcdef" for c in ref_id)

    def test_domref_to_dict_and_from_dict_roundtrip(self):
        ref = make_ref()
        d = ref.to_dict()
        recovered = DOMRef.from_dict(d)
        assert recovered.ref_id == ref.ref_id
        assert recovered.role == ref.role
        assert recovered.name == ref.name
        assert recovered.interactive == ref.interactive
        assert recovered.attributes == ref.attributes

    def test_domref_attributes_default_empty_dict(self):
        ref = DOMRef(
            ref_id="x" * 12,
            role="generic",
            name="",
            text="",
            tag="div",
            path="div",
            interactive=False,
        )
        assert ref.attributes == {}


# ===========================================================================
# 2. TestDOMSnapshot — capture, refs, dom_hash, change detection
# ===========================================================================

class TestDOMSnapshot:
    def test_capture_returns_dom_snapshot(self):
        snap = make_snapshot()
        assert isinstance(snap, DOMSnapshot)

    def test_snapshot_has_all_fields(self):
        snap = make_snapshot()
        assert hasattr(snap, "snapshot_id")
        assert hasattr(snap, "url")
        assert hasattr(snap, "title")
        assert hasattr(snap, "timestamp")
        assert hasattr(snap, "refs")
        assert hasattr(snap, "dom_hash")
        assert hasattr(snap, "interactive_count")
        assert hasattr(snap, "total_count")

    def test_snapshot_id_is_64_chars(self):
        snap = make_snapshot()
        assert len(snap.snapshot_id) == 64

    def test_snapshot_url_preserved(self):
        snap = make_snapshot(url="https://example.com/test")
        assert snap.url == "https://example.com/test"

    def test_snapshot_title_preserved(self):
        snap = make_snapshot(title="My Title")
        assert snap.title == "My Title"

    def test_snapshot_timestamp_iso8601(self):
        snap = make_snapshot(timestamp="2026-02-21T10:00:00+00:00")
        assert "T" in snap.timestamp
        assert snap.timestamp.startswith("2026-02-21")

    def test_snapshot_refs_is_list(self):
        snap = make_snapshot()
        assert isinstance(snap.refs, list)

    def test_snapshot_refs_non_empty_for_login_html(self):
        snap = make_snapshot()
        assert len(snap.refs) > 0

    def test_snapshot_interactive_count_matches_refs(self):
        snap = make_snapshot()
        computed = sum(1 for r in snap.refs if r.interactive)
        assert snap.interactive_count == computed

    def test_snapshot_total_count_matches_refs(self):
        snap = make_snapshot()
        assert snap.total_count == len(snap.refs)


# ===========================================================================
# 3. TestDOMSnapshotEngine — ARIA parsing, interactive priority, find_ref,
#                            diff, to_ai_context, max_refs
# ===========================================================================

class TestDOMSnapshotEngine:
    def test_capture_parses_button_as_button_role(self):
        snap = make_snapshot(html=LOGIN_HTML)
        buttons = [r for r in snap.refs if r.role == "button"]
        assert len(buttons) >= 1

    def test_capture_parses_input_email_as_textbox(self):
        snap = make_snapshot(html=LOGIN_HTML)
        textboxes = [r for r in snap.refs if r.role == "textbox"]
        assert len(textboxes) >= 1

    def test_capture_parses_link_as_link_role(self):
        snap = make_snapshot(html=LOGIN_HTML)
        links = [r for r in snap.refs if r.role == "link"]
        assert len(links) >= 1

    def test_capture_parses_explicit_aria_role(self):
        """div role="button" should produce role=button, not generic."""
        snap = make_snapshot(html=ARIA_HTML, title="ARIA Test")
        roles = [r.role for r in snap.refs]
        assert "button" in roles

    def test_interactive_elements_detected(self):
        snap = make_snapshot(html=DASHBOARD_HTML, title="Dashboard")
        interactive_refs = [r for r in snap.refs if r.interactive]
        # Dashboard has buttons, select, textarea
        assert len(interactive_refs) >= 3

    def test_disabled_button_not_interactive(self):
        snap = make_snapshot(html=DASHBOARD_HTML, title="Dashboard")
        disabled = [r for r in snap.refs if "disabled" in r.attributes]
        # Disabled elements should not be interactive
        for ref in disabled:
            assert ref.interactive is False

    def test_find_ref_by_button_text(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        ref = engine.find_ref(snap, "Sign In")
        assert ref is not None
        # Should match the Sign In button or label
        assert "sign in" in ref.name.lower() or "sign in" in ref.text.lower()

    def test_find_ref_returns_none_for_no_match(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        ref = engine.find_ref(snap, "xyzzy_nonexistent_xyz_12345")
        assert ref is None

    def test_diff_detects_added_refs(self):
        engine = make_engine()
        old_snap = engine.capture(
            "<html><body><button>OK</button></body></html>",
            "https://example.com", "Old", timestamp="2026-02-21T10:00:00+00:00"
        )
        new_snap = engine.capture(
            "<html><body><button>OK</button><a href='/new'>New Link</a></body></html>",
            "https://example.com", "New", timestamp="2026-02-21T10:01:00+00:00"
        )
        result = engine.diff(old_snap, new_snap)
        assert "added" in result
        assert "removed" in result
        assert "changed" in result
        assert len(result["added"]) >= 1

    def test_diff_detects_removed_refs(self):
        engine = make_engine()
        old_snap = engine.capture(
            "<html><body><button>OK</button><a href='/old'>Old Link</a></body></html>",
            "https://example.com", "Old", timestamp="2026-02-21T10:00:00+00:00"
        )
        new_snap = engine.capture(
            "<html><body><button>OK</button></body></html>",
            "https://example.com", "New", timestamp="2026-02-21T10:01:00+00:00"
        )
        result = engine.diff(old_snap, new_snap)
        assert len(result["removed"]) >= 1

    def test_to_ai_context_returns_string(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap)
        assert isinstance(ctx, str)
        assert len(ctx) > 0

    def test_to_ai_context_max_refs_truncation(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        # If there are more refs than max_refs=2, context should have at most 2 ref lines
        ctx = engine.to_ai_context(snap, max_refs=2)
        lines = ctx.split("\n")
        # Header is 3 lines (page, refs count, blank), then ref lines
        ref_lines = [l for l in lines if l.startswith("[")]
        assert len(ref_lines) <= 2


# ===========================================================================
# 4. TestActionEngine — execute, unsupported action, ref resolution, evidence
# ===========================================================================

class TestActionEngine:
    def test_execute_click_succeeds(self):
        engine = ActionEngine()
        ref = make_ref()
        result = engine.execute("click", ref)
        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.action == "click"

    def test_execute_type_succeeds(self):
        engine = ActionEngine()
        ref = make_ref(role="textbox", tag="input", name="Email")
        result = engine.execute("type", ref, value="test@example.com")
        assert result.success is True
        assert result.action == "type"

    def test_execute_scroll_succeeds(self):
        engine = ActionEngine()
        ref = make_ref()
        result = engine.execute("scroll", ref, value="down")
        assert result.success is True
        assert result.action == "scroll"

    def test_execute_select_succeeds(self):
        engine = ActionEngine()
        ref = make_ref(role="listbox", tag="select", name="Period")
        result = engine.execute("select", ref, value="week")
        assert result.success is True
        assert result.action == "select"

    def test_execute_hover_succeeds(self):
        engine = ActionEngine()
        ref = make_ref()
        result = engine.execute("hover", ref)
        assert result.success is True
        assert result.action == "hover"

    def test_execute_wait_succeeds(self):
        engine = ActionEngine()
        ref = make_ref()
        result = engine.execute("wait", ref, value="1000")
        assert result.success is True
        assert result.action == "wait"

    def test_execute_unsupported_action_returns_failure(self):
        engine = ActionEngine()
        ref = make_ref()
        result = engine.execute("fly", ref)
        assert result.success is False
        assert "UNSUPPORTED_ACTION" in result.error

    def test_execute_ref_id_in_result(self):
        engine = ActionEngine()
        ref = make_ref(ref_id="testref00001")
        result = engine.execute("click", ref)
        assert result.ref_used == "testref00001"

    def test_execute_evidence_has_required_keys(self):
        engine = ActionEngine()
        ref = make_ref()
        result = engine.execute("click", ref)
        assert "before_dom_hash" in result.evidence
        assert "after_dom_hash" in result.evidence
        assert "screenshot" in result.evidence

    def test_act_click_login_button(self):
        engine = ActionEngine()
        snap = make_snapshot(html=LOGIN_HTML)
        result = engine.act(snap, "click the Sign In button")
        # Should find a ref and attempt click (success since NullAdapter returns True)
        assert isinstance(result, ActionResult)
        assert result.action == "click"

    def test_act_returns_ref_not_found_for_unknown_element(self):
        engine = ActionEngine()
        snap = make_snapshot(html=EMPTY_HTML)
        result = engine.act(snap, "click the nonexistent_unique_xyz button")
        assert result.success is False
        assert "REF_NOT_FOUND" in result.error

    def test_action_result_to_dict(self):
        engine = ActionEngine()
        ref = make_ref()
        result = engine.execute("click", ref)
        d = result.to_dict()
        assert "success" in d
        assert "ref_used" in d
        assert "action" in d
        assert "evidence" in d
        assert "error" in d


# ===========================================================================
# 5. TestRefStability — determinism, minor changes, collision resistance
# ===========================================================================

class TestRefStability:
    def test_same_html_produces_same_ref_ids(self):
        engine = make_engine()
        snap1 = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                                timestamp="2026-02-21T10:00:00+00:00")
        snap2 = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                                timestamp="2026-02-21T10:00:00+00:00")
        ids1 = sorted(r.ref_id for r in snap1.refs)
        ids2 = sorted(r.ref_id for r in snap2.refs)
        assert ids1 == ids2

    def test_same_inputs_produce_same_ref_id(self):
        id1 = DOMSnapshotEngine.compute_ref_id("button", "Submit", "form > button")
        id2 = DOMSnapshotEngine.compute_ref_id("button", "Submit", "form > button")
        assert id1 == id2

    def test_different_role_produces_different_ref_id(self):
        id1 = DOMSnapshotEngine.compute_ref_id("button", "Submit", "form > button")
        id2 = DOMSnapshotEngine.compute_ref_id("link", "Submit", "form > button")
        assert id1 != id2

    def test_different_name_produces_different_ref_id(self):
        id1 = DOMSnapshotEngine.compute_ref_id("button", "Submit", "form > button")
        id2 = DOMSnapshotEngine.compute_ref_id("button", "Cancel", "form > button")
        assert id1 != id2

    def test_different_path_produces_different_ref_id(self):
        id1 = DOMSnapshotEngine.compute_ref_id("button", "OK", "form#a > button")
        id2 = DOMSnapshotEngine.compute_ref_id("button", "OK", "form#b > button")
        assert id1 != id2

    def test_dom_hash_deterministic_for_same_refs(self):
        snap1 = make_snapshot(timestamp="2026-02-21T10:00:00+00:00")
        snap2 = make_snapshot(timestamp="2026-02-21T11:00:00+00:00")  # different ts
        # dom_hash should be same since HTML hasn't changed
        assert snap1.dom_hash == snap2.dom_hash

    def test_dom_hash_changes_when_html_changes(self):
        engine = make_engine()
        ts = "2026-02-21T10:00:00+00:00"
        snap1 = engine.capture(LOGIN_HTML, "https://example.com", "A", timestamp=ts)
        snap2 = engine.capture(SEARCH_HTML, "https://example.com", "B", timestamp=ts)
        assert snap1.dom_hash != snap2.dom_hash

    def test_ref_id_is_exactly_12_chars(self):
        for role, name, path in [
            ("button", "A" * 100, "body > div > button"),
            ("textbox", "", "form > input"),
            ("link", "Very Long Name " * 10, "nav > ul > li > a"),
        ]:
            ref_id = DOMSnapshotEngine.compute_ref_id(role, name, path)
            assert len(ref_id) == 12, f"Expected 12, got {len(ref_id)} for role={role}"


# ===========================================================================
# 6. TestAIContext — interactive-first ordering, truncation, format
# ===========================================================================

class TestAIContext:
    def test_ai_context_contains_page_line(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login Page",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap)
        assert "Login Page" in ctx
        assert "https://example.com/login" in ctx

    def test_ai_context_contains_refs_count_line(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap)
        assert "interactive" in ctx.lower()

    def test_ai_context_ref_format_has_bracket_id(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap)
        # Each ref line must start with [ref_id]
        ref_lines = [l for l in ctx.split("\n") if l.startswith("[")]
        assert len(ref_lines) > 0
        for line in ref_lines:
            assert line.startswith("[")
            close = line.index("]")
            ref_id = line[1:close]
            assert len(ref_id) == 12  # all ref IDs are 12 chars

    def test_ai_context_interactive_elements_appear_first(self):
        engine = make_engine()
        snap = engine.capture(DASHBOARD_HTML, "https://example.com/dashboard", "Dashboard",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap, max_refs=50)
        ref_lines = [l for l in ctx.split("\n") if l.startswith("[")]

        if len(ref_lines) < 2:
            pytest.skip("Not enough refs to test ordering")

        # Find the first non-interactive ref's position
        interactive_ids = {r.ref_id for r in snap.refs if r.interactive}
        non_interactive_ids = {r.ref_id for r in snap.refs if not r.interactive}

        positions_interactive = []
        positions_non_interactive = []
        for i, line in enumerate(ref_lines):
            close = line.index("]")
            ref_id = line[1:close]
            if ref_id in interactive_ids:
                positions_interactive.append(i)
            elif ref_id in non_interactive_ids:
                positions_non_interactive.append(i)

        if positions_interactive and positions_non_interactive:
            # All interactive positions must come before all non-interactive positions
            assert max(positions_interactive) < min(positions_non_interactive)

    def test_ai_context_max_refs_limits_output(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")

        if snap.total_count < 3:
            pytest.skip("Need at least 3 refs to test truncation")

        ctx = engine.to_ai_context(snap, max_refs=2)
        ref_lines = [l for l in ctx.split("\n") if l.startswith("[")]
        assert len(ref_lines) <= 2

    def test_ai_context_max_refs_zero_returns_header_only(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap, max_refs=0)
        ref_lines = [l for l in ctx.split("\n") if l.startswith("[")]
        assert len(ref_lines) == 0

    def test_ai_context_empty_page_shows_zero_interactive_refs(self):
        """A page with no buttons/inputs/links produces no interactive ref lines."""
        engine = make_engine()
        snap = engine.capture(EMPTY_HTML, "https://example.com/empty", "Empty",
                               timestamp="2026-02-21T10:00:00+00:00")
        interactive_refs = [r for r in snap.refs if r.interactive]
        assert len(interactive_refs) == 0

    def test_ai_context_role_appears_in_ref_line(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap)
        ref_lines = [l for l in ctx.split("\n") if l.startswith("[")]
        # At least one line should contain a known role
        all_text = " ".join(ref_lines)
        known_roles = {"button", "textbox", "link", "heading", "generic",
                       "form", "navigation", "banner", "contentinfo"}
        found = any(role in all_text for role in known_roles)
        assert found, f"Expected a known role in: {all_text[:200]}"

    def test_ai_context_name_appears_quoted(self):
        engine = make_engine()
        snap = engine.capture(LOGIN_HTML, "https://example.com/login", "Login",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap)
        # Names appear in double quotes per spec
        assert '"' in ctx

    def test_ai_context_full_page_default_50_refs(self):
        """Default max_refs=50 should return up to 50 refs for a complex page."""
        engine = make_engine()
        # Build a page with many elements
        many_links = "\n".join(
            f'<li><a href="/item/{i}">Item {i}</a></li>' for i in range(80)
        )
        big_html = f"""
        <html><head><title>Big</title></head>
        <body>
          <nav><ul>{many_links}</ul></nav>
          <button>Submit</button>
        </body></html>
        """
        snap = engine.capture(big_html, "https://example.com/big", "Big",
                               timestamp="2026-02-21T10:00:00+00:00")
        ctx = engine.to_ai_context(snap, max_refs=50)
        ref_lines = [l for l in ctx.split("\n") if l.startswith("[")]
        assert len(ref_lines) <= 50


# ===========================================================================
# Bonus: instruction parser helpers
# ===========================================================================

class TestInstructionParser:
    def test_parse_click_verb(self):
        assert _parse_action_from_instruction("click the Login button") == "click"

    def test_parse_type_verb(self):
        assert _parse_action_from_instruction("type 'hello' in the search box") == "type"

    def test_parse_scroll_verb(self):
        assert _parse_action_from_instruction("scroll down to see more") == "scroll"

    def test_parse_select_verb(self):
        assert _parse_action_from_instruction("select the This Week option") == "select"

    def test_parse_hover_verb(self):
        assert _parse_action_from_instruction("hover over the dropdown") == "hover"

    def test_parse_wait_verb(self):
        assert _parse_action_from_instruction("wait for page to load") == "wait"

    def test_parse_press_maps_to_click(self):
        assert _parse_action_from_instruction("press the submit button") == "click"

    def test_parse_fill_maps_to_type(self):
        assert _parse_action_from_instruction("fill the email field with user@test.com") == "type"

    def test_parse_unknown_verb_defaults_to_click(self):
        assert _parse_action_from_instruction("do something fancy") == "click"

    def test_parse_value_double_quoted(self):
        assert _parse_value_from_instruction('type "hello world"') == "hello world"

    def test_parse_value_single_quoted(self):
        assert _parse_value_from_instruction("type 'hello'") == "hello"

    def test_parse_value_no_quotes_returns_empty(self):
        assert _parse_value_from_instruction("click the button") == ""
