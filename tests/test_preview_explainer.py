"""
tests/test_preview_explainer.py — Preview Explainer Test Suite

Tests:
  TestPreviewExplainerInit        (6 tests)  — valid + invalid construction
  TestRenderStep                  (5 tests)  — description derivation, explicit desc, numbering
  TestEstimateTime                (6 tests)  — action buckets, empty, mixed, over 60s
  TestEstimateCost                (5 tests)  — llm steps, cpu steps, mixed, empty
  TestRenderPermissions           (5 tests)  — known scopes, unknown scopes, empty
  TestRenderApprovalPrompt        (3 tests)  — content, format
  TestRenderPreview               (5 tests)  — full integration, structure, ANSI codes
  TestEdgeCases                   (5 tests)  — boundary conditions, empty steps

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_preview_explainer.py -v

Rung: 274177
"""

import sys
import unittest
from pathlib import Path

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ui.preview_explainer import (
    PreviewExplainer,
    _derive_description,
    _format_duration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_steps(*actions) -> list:
    """Return minimal valid step dicts for the given action names."""
    return [{"action": a} for a in actions]


def _make_step(action: str, target: str = "", description: str = "") -> dict:
    """Return a step dict with optional target and description."""
    step = {"action": action}
    if target:
        step["target"] = target
    if description:
        step["description"] = description
    return step


# ---------------------------------------------------------------------------
# TestPreviewExplainerInit
# ---------------------------------------------------------------------------

class TestPreviewExplainerInit(unittest.TestCase):
    """Test PreviewExplainer.__init__ validation."""

    def test_valid_construction(self):
        """Constructs with valid name, steps, and scopes."""
        pe = PreviewExplainer(
            recipe_name="Morning Email Triage",
            steps=[{"action": "navigate", "target": "gmail.com"}],
            scopes=["gmail.read"],
        )
        self.assertEqual(pe.recipe_name, "Morning Email Triage")
        self.assertEqual(len(pe.steps), 1)
        self.assertEqual(pe.scopes, ["gmail.read"])

    def test_empty_steps_allowed(self):
        """Steps list may be empty — zero-step recipe is valid."""
        pe = PreviewExplainer(
            recipe_name="Noop Recipe",
            steps=[],
            scopes=[],
        )
        self.assertEqual(pe.steps, [])

    def test_recipe_name_stripped(self):
        """recipe_name is stripped of surrounding whitespace."""
        pe = PreviewExplainer(
            recipe_name="  Trimmed Name  ",
            steps=[],
            scopes=[],
        )
        self.assertEqual(pe.recipe_name, "Trimmed Name")

    def test_raises_type_error_for_non_string_name(self):
        """TypeError raised when recipe_name is not a str."""
        with self.assertRaises(TypeError):
            PreviewExplainer(recipe_name=42, steps=[], scopes=[])

    def test_raises_value_error_for_empty_name(self):
        """ValueError raised when recipe_name is empty or whitespace."""
        with self.assertRaises(ValueError):
            PreviewExplainer(recipe_name="   ", steps=[], scopes=[])

    def test_raises_value_error_for_step_missing_action(self):
        """ValueError raised when a step dict is missing 'action' key."""
        with self.assertRaises(ValueError):
            PreviewExplainer(
                recipe_name="Bad Recipe",
                steps=[{"target": "gmail.com"}],
                scopes=[],
            )


# ---------------------------------------------------------------------------
# TestRenderStep
# ---------------------------------------------------------------------------

class TestRenderStep(unittest.TestCase):
    """Test PreviewExplainer.render_step."""

    def setUp(self):
        self.pe = PreviewExplainer(
            recipe_name="Test Recipe",
            steps=[],
            scopes=[],
        )

    def test_uses_explicit_description_when_present(self):
        """render_step uses the 'description' field if present."""
        step = _make_step("navigate", description="Open Gmail in your browser")
        result = self.pe.render_step(1, step)
        self.assertIn("Open Gmail in your browser", result)

    def test_derives_description_from_action_and_target(self):
        """render_step derives description from action + target when none given."""
        step = _make_step("navigate", target="gmail.com")
        result = self.pe.render_step(1, step)
        self.assertIn("gmail.com", result)
        self.assertIn("Open", result)

    def test_step_number_appears_in_output(self):
        """Step number appears in the rendered line."""
        step = _make_step("click", description="Click Submit")
        result = self.pe.render_step(3, step)
        self.assertIn("3.", result)
        self.assertIn("Click Submit", result)

    def test_raises_type_error_for_non_dict_step(self):
        """TypeError raised when step is not a dict."""
        with self.assertRaises(TypeError):
            self.pe.render_step(1, "not a dict")

    def test_raises_value_error_for_step_missing_action(self):
        """ValueError raised when step dict has no 'action' key."""
        with self.assertRaises(ValueError):
            self.pe.render_step(1, {"target": "gmail.com"})


# ---------------------------------------------------------------------------
# TestEstimateTime
# ---------------------------------------------------------------------------

class TestEstimateTime(unittest.TestCase):
    """Test PreviewExplainer.estimate_time."""

    def setUp(self):
        self.pe = PreviewExplainer(
            recipe_name="Timer Test",
            steps=[],
            scopes=[],
        )

    def test_navigate_costs_5_seconds(self):
        """navigate action contributes 5 seconds."""
        steps = _make_steps("navigate")
        result = self.pe.estimate_time(steps)
        self.assertEqual(result, "~5 seconds")

    def test_click_costs_3_seconds(self):
        """click action contributes 3 seconds."""
        steps = _make_steps("click")
        result = self.pe.estimate_time(steps)
        self.assertEqual(result, "~3 seconds")

    def test_llm_call_costs_15_seconds(self):
        """llm_call action contributes 15 seconds."""
        steps = _make_steps("llm_call")
        result = self.pe.estimate_time(steps)
        self.assertEqual(result, "~15 seconds")

    def test_extract_costs_10_seconds(self):
        """extract action contributes 10 seconds."""
        steps = _make_steps("extract")
        result = self.pe.estimate_time(steps)
        self.assertEqual(result, "~10 seconds")

    def test_empty_steps_returns_zero_seconds(self):
        """Empty steps list returns ~0 seconds."""
        result = self.pe.estimate_time([])
        self.assertEqual(result, "~0 seconds")

    def test_over_60_seconds_returns_minutes(self):
        """Total >= 60 seconds returns minutes format."""
        # 5 navigate (5s each) = 25s + 3 llm_call (15s each) = 45s → 70s total → ~2 minutes
        steps = _make_steps("navigate", "navigate", "navigate", "navigate", "navigate",
                             "llm_call", "llm_call", "llm_call")
        result = self.pe.estimate_time(steps)
        self.assertIn("minutes", result)
        self.assertIn("~", result)

    def test_unknown_action_defaults_to_3_seconds(self):
        """Unknown action type defaults to 3 seconds."""
        steps = [{"action": "unknown_custom_action"}]
        result = self.pe.estimate_time(steps)
        self.assertEqual(result, "~3 seconds")

    def test_mixed_steps_sum_correctly(self):
        """Mixed steps sum to correct total (navigate 5 + click 3 = 8s)."""
        steps = _make_steps("navigate", "click")
        result = self.pe.estimate_time(steps)
        self.assertEqual(result, "~8 seconds")


# ---------------------------------------------------------------------------
# TestEstimateCost
# ---------------------------------------------------------------------------

class TestEstimateCost(unittest.TestCase):
    """Test PreviewExplainer.estimate_cost."""

    def setUp(self):
        self.pe = PreviewExplainer(
            recipe_name="Cost Test",
            steps=[],
            scopes=[],
        )

    def test_llm_step_costs_one_mill(self):
        """Single llm_call step costs $0.001."""
        steps = _make_steps("llm_call")
        result = self.pe.estimate_cost(steps)
        self.assertEqual(result, "$0.001")

    def test_cpu_step_costs_zero(self):
        """navigate step costs $0.000."""
        steps = _make_steps("navigate")
        result = self.pe.estimate_cost(steps)
        self.assertEqual(result, "$0.000")

    def test_empty_steps_costs_zero(self):
        """Empty steps list costs $0.000."""
        result = self.pe.estimate_cost([])
        self.assertEqual(result, "$0.000")

    def test_multiple_llm_steps_accumulate(self):
        """Two llm_call steps cost $0.002."""
        steps = _make_steps("llm_call", "llm_call")
        result = self.pe.estimate_cost(steps)
        self.assertEqual(result, "$0.002")

    def test_mixed_steps_only_llm_counted(self):
        """Mixed steps: only llm_call contributes to cost."""
        steps = _make_steps("navigate", "click", "extract", "llm_call")
        result = self.pe.estimate_cost(steps)
        self.assertEqual(result, "$0.001")


# ---------------------------------------------------------------------------
# TestRenderPermissions
# ---------------------------------------------------------------------------

class TestRenderPermissions(unittest.TestCase):
    """Test PreviewExplainer.render_permissions."""

    def setUp(self):
        self.pe = PreviewExplainer(
            recipe_name="Scope Test",
            steps=[],
            scopes=[],
        )

    def test_known_scope_translated_to_english(self):
        """Known scope returns plain-English description."""
        result = self.pe.render_permissions(["gmail.read"])
        self.assertIn("Read Gmail inbox", result)

    def test_unknown_scope_shown_as_is(self):
        """Unknown scope is shown verbatim."""
        result = self.pe.render_permissions(["custom.scope.xyz"])
        self.assertIn("custom.scope.xyz", result)

    def test_empty_scopes_returns_none(self):
        """Empty scope list returns 'None'."""
        result = self.pe.render_permissions([])
        self.assertEqual(result, "None")

    def test_multiple_scopes_comma_separated(self):
        """Multiple scopes are comma-separated."""
        result = self.pe.render_permissions(["gmail.read", "gmail.send"])
        self.assertIn(",", result)
        self.assertIn("Read Gmail inbox", result)
        self.assertIn("Send emails via Gmail", result)

    def test_raises_type_error_for_non_list(self):
        """TypeError raised when scopes is not a list."""
        with self.assertRaises(TypeError):
            self.pe.render_permissions("gmail.read")


# ---------------------------------------------------------------------------
# TestRenderApprovalPrompt
# ---------------------------------------------------------------------------

class TestRenderApprovalPrompt(unittest.TestCase):
    """Test PreviewExplainer.render_approval_prompt."""

    def setUp(self):
        self.pe = PreviewExplainer(
            recipe_name="Prompt Test",
            steps=[],
            scopes=[],
        )

    def test_prompt_contains_approve_text(self):
        """Approval prompt contains 'Approve?' text."""
        result = self.pe.render_approval_prompt()
        self.assertIn("Approve?", result)

    def test_prompt_shows_yn_options(self):
        """Approval prompt shows Y/n options."""
        result = self.pe.render_approval_prompt()
        self.assertIn("Y", result)
        self.assertIn("n", result)

    def test_prompt_mentions_timeout(self):
        """Approval prompt mentions auto-deny timeout."""
        result = self.pe.render_approval_prompt()
        self.assertIn("auto-denies", result)
        self.assertIn("60 seconds", result)


# ---------------------------------------------------------------------------
# TestRenderPreview
# ---------------------------------------------------------------------------

class TestRenderPreview(unittest.TestCase):
    """Test PreviewExplainer.render_preview — full integration."""

    def _make_gmail_recipe(self) -> PreviewExplainer:
        return PreviewExplainer(
            recipe_name="Morning Email Triage",
            steps=[
                {"action": "navigate", "target": "gmail.com",
                 "description": "Open Gmail in your browser"},
                {"action": "extract", "target": "inbox",
                 "description": "Read your inbox (last 24 hours)"},
                {"action": "click", "target": "flag button",
                 "description": "Flag emails from your team as important"},
                {"action": "llm_call", "target": "summary",
                 "description": "Create a summary draft"},
            ],
            scopes=["gmail.read", "gmail.send"],
        )

    def test_preview_contains_recipe_name(self):
        """render_preview includes the recipe name."""
        pe = self._make_gmail_recipe()
        result = pe.render_preview()
        self.assertIn("Morning Email Triage", result)

    def test_preview_contains_this_recipe_will(self):
        """render_preview includes 'This recipe will:' header."""
        pe = self._make_gmail_recipe()
        result = pe.render_preview()
        self.assertIn("This recipe will:", result)

    def test_preview_contains_all_step_descriptions(self):
        """render_preview includes all step descriptions."""
        pe = self._make_gmail_recipe()
        result = pe.render_preview()
        self.assertIn("Open Gmail in your browser", result)
        self.assertIn("Read your inbox (last 24 hours)", result)
        self.assertIn("Flag emails from your team as important", result)
        self.assertIn("Create a summary draft", result)

    def test_preview_contains_permissions(self):
        """render_preview includes permissions section."""
        pe = self._make_gmail_recipe()
        result = pe.render_preview()
        self.assertIn("Permissions needed:", result)
        self.assertIn("Read Gmail inbox", result)
        self.assertIn("Send emails via Gmail", result)

    def test_preview_contains_time_and_cost(self):
        """render_preview includes estimated time and cost."""
        pe = self._make_gmail_recipe()
        result = pe.render_preview()
        self.assertIn("Estimated time:", result)
        self.assertIn("Estimated cost:", result)

    def test_preview_contains_approval_prompt(self):
        """render_preview ends with approval prompt."""
        pe = self._make_gmail_recipe()
        result = pe.render_preview()
        self.assertIn("Approve?", result)

    def test_preview_contains_ansi_codes(self):
        """render_preview uses ANSI escape codes for color."""
        pe = self._make_gmail_recipe()
        result = pe.render_preview()
        # ANSI ESC character
        self.assertIn("\033[", result)


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def test_derive_description_action_only(self):
        """_derive_description returns verb-only for step without target."""
        result = _derive_description({"action": "navigate"})
        self.assertIn("Open", result)

    def test_derive_description_action_and_target(self):
        """_derive_description combines verb + target."""
        result = _derive_description({"action": "navigate", "target": "google.com"})
        self.assertIn("Open", result)
        self.assertIn("google.com", result)

    def test_format_duration_under_60_seconds(self):
        """_format_duration returns seconds format for < 60s."""
        result = _format_duration(45)
        self.assertEqual(result, "~45 seconds")

    def test_format_duration_exactly_60_seconds(self):
        """_format_duration returns minutes format for 60s."""
        result = _format_duration(60)
        self.assertEqual(result, "~1 minutes")

    def test_format_duration_rounds_up_minutes(self):
        """_format_duration rounds up to nearest minute (61s → 2 min)."""
        result = _format_duration(61)
        self.assertEqual(result, "~2 minutes")

    def test_cost_output_always_3_decimal_places(self):
        """estimate_cost always outputs 3 decimal places."""
        pe = PreviewExplainer("Test", [], [])
        result = pe.estimate_cost([])
        # Must match "$0.000" pattern
        self.assertRegex(result, r"^\$\d+\.\d{3}$")

    def test_fill_action_costs_2_seconds(self):
        """fill action (alias of input) costs 2 seconds."""
        pe = PreviewExplainer("Test", [], [])
        steps = [{"action": "fill"}]
        result = pe.estimate_time(steps)
        self.assertEqual(result, "~2 seconds")

    def test_input_action_costs_2_seconds(self):
        """input action costs 2 seconds."""
        pe = PreviewExplainer("Test", [], [])
        steps = [{"action": "input"}]
        result = pe.estimate_time(steps)
        self.assertEqual(result, "~2 seconds")

    def test_step_with_extra_keys_allowed(self):
        """Steps with extra keys beyond action/target/description are fine."""
        pe = PreviewExplainer(
            recipe_name="Extra Keys",
            steps=[{
                "action": "click",
                "target": "button",
                "description": "Click the button",
                "scope": "browser.click",
                "timeout": 5000,
            }],
            scopes=[],
        )
        result = pe.render_step(1, pe.steps[0])
        self.assertIn("Click the button", result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
