"""
ScopeDisplay — Acceptance Tests
SolaceBrowser | Belt: Yellow | Rung: 641

Tests (18 total):
  T01  test_describe_scope_registered_low
  T02  test_describe_scope_registered_medium
  T03  test_describe_scope_registered_high
  T04  test_describe_scope_unregistered_fallback
  T05  test_describe_scope_type_error
  T06  test_describe_scope_empty_raises
  T07  test_risk_level_low_scope
  T08  test_risk_level_medium_scope
  T09  test_risk_level_high_scope
  T10  test_risk_level_unknown_scope_fails_closed
  T11  test_categorize_scopes_groups_by_platform
  T12  test_categorize_scopes_empty_list
  T13  test_categorize_scopes_type_error
  T14  test_render_scope_modal_contains_recipe_name
  T15  test_render_scope_modal_contains_english_descriptions
  T16  test_render_scope_modal_contains_risk_labels
  T17  test_render_scope_modal_empty_scopes
  T18  test_render_scope_modal_overall_risk_highest
  T19  test_render_scope_modal_type_errors
  T20  test_render_scope_modal_plain_no_ansi
  T21  test_render_scope_diff_added_scopes
  T22  test_render_scope_diff_removed_scopes
  T23  test_render_scope_diff_unchanged_scopes
  T24  test_render_scope_diff_empty_lists
  T25  test_render_scope_diff_type_errors
  T26  test_render_scope_diff_plain_no_ansi
  T27  test_module_level_functions_proxy_to_class
  T28  test_overall_risk_precedence

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_scope_display.py -v

Rung: 641
"""

import sys
import unittest
from pathlib import Path

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ui.scope_display import (
    ScopeDisplay,
    describe_scope,
    categorize_scopes,
    render_scope_modal,
    render_scope_diff,
)


# ---------------------------------------------------------------------------
# Helper: strip all ANSI escape codes from a string for plain-text assertions
# ---------------------------------------------------------------------------

import re as _re

_ANSI_RE = _re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    return _ANSI_RE.sub("", text)


# ---------------------------------------------------------------------------
# T01-T06: describe_scope
# ---------------------------------------------------------------------------

class TestDescribeScopeRegisteredLow(unittest.TestCase):
    """T01 — registered low-risk scope returns registry description."""

    def test_gmail_read_inbox_description(self):
        desc = describe_scope("gmail.read.inbox")
        self.assertIsInstance(desc, str)
        self.assertTrue(len(desc) > 0)
        # Description should mention reading / inbox (registry value)
        lower = desc.lower()
        self.assertTrue(
            "read" in lower or "inbox" in lower,
            f"Expected 'read' or 'inbox' in: {desc!r}",
        )

    def test_linkedin_read_messages_description(self):
        desc = describe_scope("linkedin.read.messages")
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)


class TestDescribeScopeMediumScope(unittest.TestCase):
    """T02 — medium-risk scope returns a non-empty description."""

    def test_github_create_issue(self):
        desc = describe_scope("github.create.issue")
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)

    def test_github_comment_issue(self):
        desc = describe_scope("github.comment.issue")
        lower = desc.lower()
        self.assertTrue(
            "comment" in lower or "github" in lower,
            f"Expected relevant keyword in: {desc!r}",
        )


class TestDescribeScopeRegisteredHigh(unittest.TestCase):
    """T03 — registered high-risk scope returns registry description."""

    def test_gmail_delete_email_description(self):
        desc = describe_scope("gmail.delete.email")
        self.assertIsInstance(desc, str)
        lower = desc.lower()
        self.assertTrue(
            "delete" in lower or "email" in lower or "permanent" in lower,
            f"Expected destructive keyword in: {desc!r}",
        )

    def test_linkedin_delete_post_description(self):
        desc = describe_scope("linkedin.delete.post")
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)


class TestDescribeScopeUnregisteredFallback(unittest.TestCase):
    """T04 — unregistered scope returns a fallback description (never empty)."""

    def test_unknown_scope_returns_string(self):
        desc = describe_scope("custom.read.data")
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)

    def test_completely_unknown_scope_non_empty(self):
        desc = describe_scope("xyzzy.frobnicate.widget")
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)

    def test_browser_navigate_fallback(self):
        # browser.navigate is in the legacy aliases; result should be non-empty
        desc = describe_scope("browser.navigate")
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)


class TestDescribeScopeTypeError(unittest.TestCase):
    """T05 — non-string input raises TypeError (Fallback Ban: no silent swallow)."""

    def test_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            ScopeDisplay.describe_scope(None)  # type: ignore[arg-type]

    def test_integer_raises_type_error(self):
        with self.assertRaises(TypeError):
            ScopeDisplay.describe_scope(42)  # type: ignore[arg-type]

    def test_list_raises_type_error(self):
        with self.assertRaises(TypeError):
            ScopeDisplay.describe_scope(["gmail.read.inbox"])  # type: ignore[arg-type]


class TestDescribeScopeEmptyRaises(unittest.TestCase):
    """T06 — empty string raises ValueError."""

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            ScopeDisplay.describe_scope("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            ScopeDisplay.describe_scope("   ")


# ---------------------------------------------------------------------------
# T07-T10: risk_level
# ---------------------------------------------------------------------------

class TestRiskLevelLowScope(unittest.TestCase):
    """T07 — read-only scopes classified as LOW."""

    def test_gmail_read_inbox_is_low(self):
        self.assertEqual(ScopeDisplay.risk_level("gmail.read.inbox"), "low")

    def test_hackernews_read_feed_is_low(self):
        self.assertEqual(ScopeDisplay.risk_level("hackernews.read.feed"), "low")

    def test_linkedin_read_messages_is_low(self):
        self.assertEqual(ScopeDisplay.risk_level("linkedin.read.messages"), "low")


class TestRiskLevelMediumScope(unittest.TestCase):
    """T08 — write scopes classified as MEDIUM."""

    def test_github_create_issue_is_medium(self):
        self.assertEqual(ScopeDisplay.risk_level("github.create.issue"), "medium")

    def test_github_comment_issue_is_medium(self):
        self.assertEqual(ScopeDisplay.risk_level("github.comment.issue"), "medium")


class TestRiskLevelHighScope(unittest.TestCase):
    """T09 — admin/delete scopes classified as HIGH."""

    def test_gmail_delete_email_is_high(self):
        self.assertEqual(ScopeDisplay.risk_level("gmail.delete.email"), "high")

    def test_gmail_send_email_is_high(self):
        self.assertEqual(ScopeDisplay.risk_level("gmail.send.email"), "high")

    def test_linkedin_delete_post_is_high(self):
        self.assertEqual(ScopeDisplay.risk_level("linkedin.delete.post"), "high")


class TestRiskLevelUnknownFailsClosed(unittest.TestCase):
    """T10 — unknown scope → HIGH (fail-closed, Fallback Ban)."""

    def test_unknown_scope_is_high(self):
        self.assertEqual(ScopeDisplay.risk_level("xyzzy.frobnicate.widget"), "high")

    def test_partial_scope_unknown_is_high(self):
        self.assertEqual(ScopeDisplay.risk_level("notaplatform.action.resource"), "high")

    def test_type_error_raised_for_non_string(self):
        with self.assertRaises(TypeError):
            ScopeDisplay.risk_level(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# T11-T13: categorize_scopes
# ---------------------------------------------------------------------------

class TestCategorizeScopesGroupsByPlatform(unittest.TestCase):
    """T11 — scopes grouped by app with human-readable platform labels."""

    def test_gmail_scopes_grouped_under_gmail(self):
        result = categorize_scopes(["gmail.read.inbox", "gmail.send.email"])
        self.assertIn("Gmail", result)
        self.assertIn("gmail.read.inbox", result["Gmail"])
        self.assertIn("gmail.send.email", result["Gmail"])

    def test_linkedin_scopes_grouped(self):
        result = categorize_scopes(["linkedin.read.messages", "linkedin.post.text"])
        self.assertIn("LinkedIn", result)

    def test_mixed_platforms_grouped_separately(self):
        result = categorize_scopes([
            "gmail.read.inbox",
            "linkedin.read.messages",
        ])
        # Both platforms should be keys
        labels = list(result.keys())
        self.assertTrue(any("Gmail" in k for k in labels))
        self.assertTrue(any("LinkedIn" in k for k in labels))

    def test_github_platform_label(self):
        result = categorize_scopes(["github.read.issues", "github.create.issue"])
        self.assertIn("GitHub", result)


class TestCategorizeScopesEmptyList(unittest.TestCase):
    """T12 — empty scopes list returns empty dict."""

    def test_empty_list_returns_empty_dict(self):
        result = categorize_scopes([])
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)


class TestCategorizeScopesTypeError(unittest.TestCase):
    """T13 — non-list input raises TypeError."""

    def test_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            ScopeDisplay.categorize_scopes(None)  # type: ignore[arg-type]

    def test_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            ScopeDisplay.categorize_scopes("gmail.read.inbox")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# T14-T20: render_scope_modal
# ---------------------------------------------------------------------------

class TestRenderScopeModalContainsRecipeName(unittest.TestCase):
    """T14 — modal output includes the recipe name."""

    def test_recipe_name_appears_in_output(self):
        output = render_scope_modal(["gmail.read.inbox"], "Send Morning Report")
        plain = _strip_ansi(output)
        self.assertIn("Send Morning Report", plain)

    def test_recipe_name_with_special_chars(self):
        output = render_scope_modal(["gmail.read.inbox"], "my-recipe-v2")
        plain = _strip_ansi(output)
        self.assertIn("my-recipe-v2", plain)


class TestRenderScopeModalContainsEnglishDescriptions(unittest.TestCase):
    """T15 — modal output shows plain-English scope descriptions."""

    def test_shows_english_not_raw_scope_string(self):
        output = render_scope_modal(["gmail.read.inbox"], "Test Recipe")
        plain = _strip_ansi(output)
        # The description from the registry should appear, not just the raw scope key
        # "Read inbox messages" or similar
        self.assertTrue(
            "inbox" in plain.lower() or "read" in plain.lower(),
            f"Expected English description in modal, got:\n{plain}",
        )

    def test_multiple_scopes_all_described(self):
        scopes = ["gmail.read.inbox", "linkedin.read.messages"]
        output = render_scope_modal(scopes, "Multi Scope Recipe")
        plain = _strip_ansi(output)
        # Both scopes should produce descriptions
        self.assertTrue(len(plain) > 100, "Modal seems too short for 2 scopes")

    def test_preamble_line_present(self):
        output = render_scope_modal(["gmail.read.inbox"], "Test")
        plain = _strip_ansi(output)
        self.assertIn("This recipe needs permission to:", plain)


class TestRenderScopeModalContainsRiskLabels(unittest.TestCase):
    """T16 — modal output includes risk labels (LOW, MEDIUM, HIGH)."""

    def test_low_risk_label_present(self):
        output = render_scope_modal(["gmail.read.inbox"], "Test")
        plain = _strip_ansi(output)
        self.assertIn("LOW", plain)

    def test_high_risk_label_present(self):
        output = render_scope_modal(["gmail.delete.email"], "Test")
        plain = _strip_ansi(output)
        self.assertIn("HIGH", plain)

    def test_overall_risk_line_present(self):
        output = render_scope_modal(["gmail.read.inbox"], "Test")
        plain = _strip_ansi(output)
        self.assertIn("Overall risk:", plain)


class TestRenderScopeModalEmptyScopes(unittest.TestCase):
    """T17 — empty scope list renders a modal with explicit no-permissions message."""

    def test_empty_scopes_renders_without_error(self):
        output = render_scope_modal([], "Empty Recipe")
        plain = _strip_ansi(output)
        self.assertIn("Empty Recipe", plain)
        self.assertIn("no permissions", plain.lower())


class TestRenderScopeModalOverallRiskHighest(unittest.TestCase):
    """T18 — overall risk is the highest risk among all scopes."""

    def test_mixed_risk_shows_highest(self):
        # low + high → overall should be HIGH
        scopes = ["gmail.read.inbox", "gmail.delete.email"]
        output = render_scope_modal(scopes, "Test")
        plain = _strip_ansi(output)
        # Overall risk must be HIGH (because delete.email is high)
        self.assertIn("HIGH", plain)

    def test_all_low_shows_low(self):
        scopes = ["gmail.read.inbox", "linkedin.read.messages"]
        output = render_scope_modal(scopes, "Test")
        plain = _strip_ansi(output)
        self.assertIn("Overall risk:", plain)
        # LOW badge present somewhere after "Overall risk:"
        idx = plain.index("Overall risk:")
        after = plain[idx:]
        self.assertIn("LOW", after)


class TestRenderScopeModalTypeErrors(unittest.TestCase):
    """T19 — invalid argument types raise TypeError or ValueError."""

    def test_none_scopes_raises(self):
        with self.assertRaises(TypeError):
            render_scope_modal(None, "Recipe")  # type: ignore[arg-type]

    def test_none_recipe_name_raises(self):
        with self.assertRaises(TypeError):
            render_scope_modal([], None)  # type: ignore[arg-type]

    def test_empty_recipe_name_raises(self):
        with self.assertRaises(ValueError):
            render_scope_modal([], "")

    def test_whitespace_recipe_name_raises(self):
        with self.assertRaises(ValueError):
            render_scope_modal([], "   ")


class TestRenderScopeModalPlainNoAnsi(unittest.TestCase):
    """T20 — plain=True strips all ANSI escape codes."""

    def test_plain_output_has_no_ansi_codes(self):
        output = render_scope_modal(["gmail.read.inbox"], "Test", plain=True)
        # If plain mode is correct, stripping ANSI gives the same string
        self.assertEqual(output, _strip_ansi(output))

    def test_plain_output_still_contains_recipe_name(self):
        output = render_scope_modal(["gmail.read.inbox"], "My Recipe", plain=True)
        self.assertIn("My Recipe", output)

    def test_plain_output_contains_risk_label(self):
        output = render_scope_modal(["gmail.read.inbox"], "Test", plain=True)
        self.assertIn("LOW", output)


# ---------------------------------------------------------------------------
# T21-T26: render_scope_diff
# ---------------------------------------------------------------------------

class TestRenderScopeDiffAddedScopes(unittest.TestCase):
    """T21 — added scopes shown with + prefix."""

    def test_added_scope_has_plus_prefix(self):
        output = render_scope_diff([], ["gmail.read.inbox"], plain=True)
        self.assertIn("+", output)

    def test_added_scope_description_present(self):
        output = render_scope_diff([], ["gmail.read.inbox"], plain=True)
        plain = _strip_ansi(output)
        self.assertTrue(
            "inbox" in plain.lower() or "read" in plain.lower(),
            f"Expected English desc in diff: {plain}",
        )

    def test_summary_shows_added_count(self):
        output = render_scope_diff([], ["gmail.read.inbox", "linkedin.read.messages"], plain=True)
        self.assertIn("+2 added", output)


class TestRenderScopeDiffRemovedScopes(unittest.TestCase):
    """T22 — removed scopes shown with - prefix."""

    def test_removed_scope_has_minus_prefix(self):
        output = render_scope_diff(["gmail.read.inbox"], [], plain=True)
        self.assertIn("-", output)

    def test_summary_shows_removed_count(self):
        output = render_scope_diff(["gmail.read.inbox", "linkedin.read.messages"], [], plain=True)
        self.assertIn("-2 removed", output)


class TestRenderScopeDiffUnchangedScopes(unittest.TestCase):
    """T23 — unchanged scopes shown with = prefix."""

    def test_unchanged_scope_has_equals_prefix(self):
        output = render_scope_diff(
            ["gmail.read.inbox"],
            ["gmail.read.inbox", "linkedin.read.messages"],
            plain=True,
        )
        self.assertIn("=", output)

    def test_summary_shows_unchanged_count(self):
        output = render_scope_diff(
            ["gmail.read.inbox"],
            ["gmail.read.inbox"],
            plain=True,
        )
        self.assertIn("=1 unchanged", output)


class TestRenderScopeDiffEmptyLists(unittest.TestCase):
    """T24 — both empty lists renders a minimal diff without error."""

    def test_both_empty_renders_without_error(self):
        output = render_scope_diff([], [], plain=True)
        self.assertIsInstance(output, str)
        self.assertIn("Scope Changes:", output)

    def test_both_empty_shows_no_scopes_message(self):
        output = render_scope_diff([], [], plain=True)
        self.assertIn("no scopes", output.lower())


class TestRenderScopeDiffTypeErrors(unittest.TestCase):
    """T25 — non-list inputs raise TypeError."""

    def test_none_old_raises(self):
        with self.assertRaises(TypeError):
            render_scope_diff(None, [])  # type: ignore[arg-type]

    def test_none_new_raises(self):
        with self.assertRaises(TypeError):
            render_scope_diff([], None)  # type: ignore[arg-type]

    def test_string_old_raises(self):
        with self.assertRaises(TypeError):
            render_scope_diff("gmail.read.inbox", [])  # type: ignore[arg-type]


class TestRenderScopeDiffPlainNoAnsi(unittest.TestCase):
    """T26 — plain=True strips all ANSI codes from diff output."""

    def test_plain_diff_has_no_ansi_codes(self):
        output = render_scope_diff(["gmail.read.inbox"], ["linkedin.read.messages"], plain=True)
        self.assertEqual(output, _strip_ansi(output))

    def test_plain_diff_contains_readable_labels(self):
        output = render_scope_diff([], ["gmail.delete.email"], plain=True)
        self.assertIn("HIGH", output)


# ---------------------------------------------------------------------------
# T27: Module-level functions proxy to ScopeDisplay class
# ---------------------------------------------------------------------------

class TestModuleLevelFunctionsProxyToClass(unittest.TestCase):
    """T27 — module-level convenience functions match ScopeDisplay class methods."""

    def test_describe_scope_matches_class(self):
        scope = "gmail.read.inbox"
        self.assertEqual(describe_scope(scope), ScopeDisplay.describe_scope(scope))

    def test_categorize_scopes_matches_class(self):
        scopes = ["gmail.read.inbox", "linkedin.read.messages"]
        self.assertEqual(categorize_scopes(scopes), ScopeDisplay.categorize_scopes(scopes))

    def test_render_scope_modal_matches_class(self):
        scopes = ["gmail.read.inbox"]
        recipe = "Test"
        self.assertEqual(
            render_scope_modal(scopes, recipe, plain=True),
            ScopeDisplay.render_scope_modal(scopes, recipe, plain=True),
        )

    def test_render_scope_diff_matches_class(self):
        old = ["gmail.read.inbox"]
        new = ["linkedin.read.messages"]
        self.assertEqual(
            render_scope_diff(old, new, plain=True),
            ScopeDisplay.render_scope_diff(old, new, plain=True),
        )


# ---------------------------------------------------------------------------
# T28: Overall risk precedence
# ---------------------------------------------------------------------------

class TestOverallRiskPrecedence(unittest.TestCase):
    """T28 — _overall_risk returns highest risk from a mixed list."""

    def test_high_dominates_low(self):
        risk = ScopeDisplay._overall_risk(["gmail.read.inbox", "gmail.delete.email"])
        self.assertEqual(risk, "high")

    def test_high_dominates_medium(self):
        risk = ScopeDisplay._overall_risk(["github.create.issue", "gmail.delete.email"])
        self.assertEqual(risk, "high")

    def test_medium_dominates_low(self):
        risk = ScopeDisplay._overall_risk(["gmail.read.inbox", "github.create.issue"])
        self.assertEqual(risk, "medium")

    def test_all_low_returns_low(self):
        risk = ScopeDisplay._overall_risk(["gmail.read.inbox", "linkedin.read.messages"])
        self.assertEqual(risk, "low")

    def test_empty_list_returns_low(self):
        risk = ScopeDisplay._overall_risk([])
        self.assertEqual(risk, "low")

    def test_unknown_scope_treated_as_high(self):
        # fail-closed: unknown scope in list → overall is HIGH
        risk = ScopeDisplay._overall_risk(["xyzzy.frobnicate.widget"])
        self.assertEqual(risk, "high")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
