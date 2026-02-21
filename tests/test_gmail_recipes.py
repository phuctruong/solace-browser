"""
Gmail Recipes — Acceptance Tests (Rung 641)

BUILD 7: Gmail automation recipes for SolaceBrowser.

Tests cover:
  - Recipe schema validation (all required fields present)
  - Step sequence validation (each step has action, selectors, timeouts)
  - OAuth3 scope declaration (every recipe declares required scopes)
  - Selector format validation (valid CSS selectors)
  - No hardcoded credentials in any recipe
  - Evidence bundle format (each recipe defines expected evidence outputs)
  - PM triplet completeness (selectors.json, urls.json, actions.json)
  - Cross-recipe consistency (shared selectors match PM triplet)
  - Anti-detection patterns (human typing, keyboard shortcuts)
  - Input/output schema validation

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_gmail_recipes.py -v --tb=short -p no:httpbin

Rung: 641 (local correctness — all tests must pass before shipping)
"""

import json
import re
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
RECIPES_DIR = PROJECT_ROOT / "recipes" / "gmail"
PRIMEWIKI_DIR = PROJECT_ROOT / "primewiki" / "gmail"

# Ensure src/ is importable (for potential future integration tests)
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RECIPE_FILES = [
    "gmail-read-inbox.json",
    "gmail-compose-email.json",
    "gmail-search-emails.json",
    "gmail-reply-email.json",
    "gmail-label-emails.json",
    "gmail-archive-emails.json",
]

PM_TRIPLET_FILES = [
    "selectors.json",
    "urls.json",
    "actions.json",
]

# Required top-level fields for every recipe
REQUIRED_RECIPE_FIELDS = [
    "id",
    "platform",
    "version",
    "description",
    "author",
    "rung",
    "oauth3_scopes",
    "evidence_type",
    "steps",
    "expected_evidence",
    "metadata",
]

# Required fields in every step
REQUIRED_STEP_FIELDS = ["step", "action", "description"]

# Actions that require a selector
SELECTOR_REQUIRED_ACTIONS = [
    "click",
    "human_type",
    "type",
    "wait_for_selector",
    "extract_all",
    "extract",
]

# Actions that require a timeout or wait
TIMED_ACTIONS = ["navigate", "wait_for_selector", "load_session"]

# Forbidden strings (credentials, secrets)
FORBIDDEN_STRINGS = [
    "password",
    "secret",
    "api_key",
    "apikey",
    "token=",
    "Bearer ",
    "sk-",
    "AIza",
]

# Allowed variable patterns (template variables)
VARIABLE_PATTERN = re.compile(r"\{params?\.\w+(\s*\+\s*\d+)?\}")

# CSS selector basic validation (very permissive — just checks it is not empty
# and does not contain obvious code injection)
CSS_INJECTION_PATTERNS = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+=", re.IGNORECASE),
]


@pytest.fixture
def all_recipes():
    """Load and parse all Gmail recipe JSON files."""
    recipes = {}
    for filename in RECIPE_FILES:
        filepath = RECIPES_DIR / filename
        assert filepath.exists(), f"Recipe file missing: {filepath}"
        with open(filepath, "r") as f:
            recipes[filename] = json.load(f)
    return recipes


@pytest.fixture
def all_pm_files():
    """Load and parse all Gmail PM triplet JSON files."""
    pm_files = {}
    for filename in PM_TRIPLET_FILES:
        filepath = PRIMEWIKI_DIR / filename
        assert filepath.exists(), f"PM triplet file missing: {filepath}"
        with open(filepath, "r") as f:
            pm_files[filename] = json.load(f)
    return pm_files


@pytest.fixture(params=RECIPE_FILES, ids=[f.replace(".json", "") for f in RECIPE_FILES])
def recipe(request, all_recipes):
    """Parametrize: one test run per recipe."""
    return all_recipes[request.param], request.param


# ---------------------------------------------------------------------------
# 1. Recipe File Existence Tests
# ---------------------------------------------------------------------------

class TestRecipeFileExistence:
    """Verify all 6 Gmail recipe files exist and are valid JSON."""

    def test_recipes_directory_exists(self):
        assert RECIPES_DIR.exists(), f"recipes/gmail/ directory missing at {RECIPES_DIR}"

    def test_all_six_recipes_exist(self):
        for filename in RECIPE_FILES:
            filepath = RECIPES_DIR / filename
            assert filepath.exists(), f"Missing recipe: {filename}"

    def test_all_recipes_are_valid_json(self):
        for filename in RECIPE_FILES:
            filepath = RECIPES_DIR / filename
            with open(filepath, "r") as f:
                data = json.load(f)
            assert isinstance(data, dict), f"{filename} is not a JSON object"

    def test_recipe_files_not_empty(self):
        for filename in RECIPE_FILES:
            filepath = RECIPES_DIR / filename
            assert filepath.stat().st_size > 100, f"{filename} is suspiciously small"


# ---------------------------------------------------------------------------
# 2. Recipe Schema Validation Tests
# ---------------------------------------------------------------------------

class TestRecipeSchema:
    """Verify each recipe has all required top-level fields."""

    def test_required_fields_present(self, recipe):
        data, filename = recipe
        for field in REQUIRED_RECIPE_FIELDS:
            assert field in data, f"{filename} missing required field: {field}"

    def test_platform_is_gmail(self, recipe):
        data, filename = recipe
        assert data["platform"] == "gmail", f"{filename} platform should be 'gmail'"

    def test_version_format(self, recipe):
        data, filename = recipe
        version = data["version"]
        assert re.match(r"^\d+\.\d+\.\d+$", version), \
            f"{filename} version '{version}' not semver format"

    def test_author_is_stillwater(self, recipe):
        data, filename = recipe
        assert data["author"] == "stillwater", f"{filename} author should be 'stillwater'"

    def test_rung_is_641(self, recipe):
        data, filename = recipe
        assert data["rung"] == 641, f"{filename} rung should be 641"

    def test_evidence_type_is_lane_a(self, recipe):
        data, filename = recipe
        assert data["evidence_type"] == "lane_a", f"{filename} evidence_type should be 'lane_a'"

    def test_id_matches_filename(self, recipe):
        data, filename = recipe
        expected_id = filename.replace(".json", "")
        assert data["id"] == expected_id, \
            f"{filename} id '{data['id']}' should match filename stem '{expected_id}'"

    def test_description_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["description"]) > 20, \
            f"{filename} description too short (need > 20 chars)"

    def test_has_reasoning_section(self, recipe):
        data, filename = recipe
        assert "reasoning" in data, f"{filename} missing reasoning section"
        reasoning = data["reasoning"]
        assert "research" in reasoning, f"{filename} reasoning missing 'research'"
        assert "selector_strategy" in reasoning, f"{filename} reasoning missing 'selector_strategy'"


# ---------------------------------------------------------------------------
# 3. OAuth3 Scope Validation Tests
# ---------------------------------------------------------------------------

class TestOAuth3Scopes:
    """Every recipe must declare OAuth3 scopes correctly."""

    VALID_GMAIL_SCOPE_PREFIXES = [
        "gmail.read.",
        "gmail.compose.",
        "gmail.organize.",
    ]

    def test_oauth3_scopes_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["oauth3_scopes"], list), \
            f"{filename} oauth3_scopes must be a list"

    def test_oauth3_scopes_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["oauth3_scopes"]) >= 1, \
            f"{filename} must declare at least one OAuth3 scope"

    def test_scopes_have_gmail_prefix(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            assert scope.startswith("gmail."), \
                f"{filename} scope '{scope}' must start with 'gmail.'"

    def test_scopes_follow_naming_convention(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            has_valid_prefix = any(
                scope.startswith(prefix)
                for prefix in self.VALID_GMAIL_SCOPE_PREFIXES
            )
            assert has_valid_prefix, \
                f"{filename} scope '{scope}' does not match valid prefix pattern"

    def test_read_recipes_have_read_scopes(self, all_recipes):
        read_recipe = all_recipes["gmail-read-inbox.json"]
        assert any("read" in s for s in read_recipe["oauth3_scopes"]), \
            "gmail-read-inbox must have a read scope"

    def test_compose_recipe_has_compose_scope(self, all_recipes):
        compose_recipe = all_recipes["gmail-compose-email.json"]
        assert any("compose" in s for s in compose_recipe["oauth3_scopes"]), \
            "gmail-compose-email must have a compose scope"

    def test_search_recipe_has_search_scope(self, all_recipes):
        search_recipe = all_recipes["gmail-search-emails.json"]
        scopes = search_recipe["oauth3_scopes"]
        assert any("read" in s or "search" in s for s in scopes), \
            "gmail-search-emails must have a read or search scope"

    def test_label_recipe_has_organize_scope(self, all_recipes):
        label_recipe = all_recipes["gmail-label-emails.json"]
        assert any("organize" in s for s in label_recipe["oauth3_scopes"]), \
            "gmail-label-emails must have an organize scope"

    def test_archive_recipe_has_organize_scope(self, all_recipes):
        archive_recipe = all_recipes["gmail-archive-emails.json"]
        assert any("organize" in s for s in archive_recipe["oauth3_scopes"]), \
            "gmail-archive-emails must have an organize scope"

    def test_reply_recipe_has_both_scopes(self, all_recipes):
        reply_recipe = all_recipes["gmail-reply-email.json"]
        scopes = reply_recipe["oauth3_scopes"]
        assert any("read" in s for s in scopes), \
            "gmail-reply-email must have a read scope (needs to read email first)"
        assert any("compose" in s or "reply" in s for s in scopes), \
            "gmail-reply-email must have a compose or reply scope"


# ---------------------------------------------------------------------------
# 4. Step Sequence Validation Tests
# ---------------------------------------------------------------------------

class TestStepSequence:
    """Every recipe step must have required fields and logical ordering."""

    def test_steps_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["steps"], list), f"{filename} steps must be a list"

    def test_steps_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["steps"]) >= 3, \
            f"{filename} must have at least 3 steps"

    def test_step_numbers_sequential(self, recipe):
        data, filename = recipe
        step_numbers = [s["step"] for s in data["steps"]]
        expected = list(range(1, len(step_numbers) + 1))
        assert step_numbers == expected, \
            f"{filename} step numbers not sequential: {step_numbers}"

    def test_each_step_has_required_fields(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            for field in REQUIRED_STEP_FIELDS:
                assert field in step, \
                    f"{filename} step {step.get('step', '?')} missing field: {field}"

    def test_each_step_has_action(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            assert "action" in step, \
                f"{filename} step {step['step']} missing 'action' field"
            assert isinstance(step["action"], str), \
                f"{filename} step {step['step']} action must be a string"
            assert len(step["action"]) > 0, \
                f"{filename} step {step['step']} action cannot be empty"

    def test_first_step_is_session_or_navigate(self, recipe):
        data, filename = recipe
        first_action = data["steps"][0]["action"]
        assert first_action in ("load_session", "navigate"), \
            f"{filename} first step should be load_session or navigate, got '{first_action}'"

    def test_last_step_is_return_result(self, recipe):
        data, filename = recipe
        last_action = data["steps"][-1]["action"]
        assert last_action == "return_result", \
            f"{filename} last step should be return_result, got '{last_action}'"

    def test_navigate_steps_have_target(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate":
                assert "target" in step, \
                    f"{filename} step {step['step']} navigate missing 'target'"
                assert step["target"].startswith("https://"), \
                    f"{filename} step {step['step']} navigate target must be HTTPS"

    def test_click_steps_have_selector(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "click":
                assert "selector" in step or "selector_default" in step, \
                    f"{filename} step {step['step']} click missing selector"


# ---------------------------------------------------------------------------
# 5. Selector Format Validation Tests
# ---------------------------------------------------------------------------

class TestSelectorFormat:
    """CSS selectors must be valid and free of injection."""

    def _collect_selectors(self, data):
        """Recursively collect all selector strings from a recipe."""
        selectors = []

        def _walk(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("selector", "selector_default", "selector_thread",
                               "selector_inbox", "wait_for") and isinstance(value, str):
                        selectors.append((value, path + "." + key))
                    else:
                        _walk(value, path + "." + key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _walk(item, f"{path}[{i}]")

        _walk(data)
        return selectors

    def test_selectors_not_empty(self, recipe):
        data, filename = recipe
        selectors = self._collect_selectors(data)
        assert len(selectors) > 0, f"{filename} has no selectors at all"

    def test_selectors_no_injection(self, recipe):
        data, filename = recipe
        selectors = self._collect_selectors(data)
        for selector, path in selectors:
            # Skip template variables
            if VARIABLE_PATTERN.search(selector):
                clean = VARIABLE_PATTERN.sub("", selector)
            else:
                clean = selector
            for pattern in CSS_INJECTION_PATTERNS:
                assert not pattern.search(clean), \
                    f"{filename} selector at {path} contains injection pattern: {selector}"

    def test_selectors_reasonable_length(self, recipe):
        data, filename = recipe
        selectors = self._collect_selectors(data)
        for selector, path in selectors:
            assert len(selector) < 500, \
                f"{filename} selector at {path} suspiciously long ({len(selector)} chars)"

    def test_navigate_targets_are_gmail_urls(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate" and "target" in step:
                target = step["target"]
                assert "google.com" in target or "gmail.com" in target, \
                    f"{filename} step {step['step']} navigate to non-Gmail URL: {target}"


# ---------------------------------------------------------------------------
# 6. No Hardcoded Credentials Tests
# ---------------------------------------------------------------------------

class TestNoHardcodedCredentials:
    """Ensure no recipe contains hardcoded passwords, tokens, or API keys."""

    def test_no_forbidden_strings_in_recipe(self, recipe):
        data, filename = recipe
        raw_text = json.dumps(data).lower()
        for forbidden in FORBIDDEN_STRINGS:
            # Allow "password" in field descriptions and references
            if forbidden == "password":
                # Count occurrences — all should be in description/notes context
                occurrences = raw_text.count(forbidden)
                # Check that "password" is only in descriptive text, not as a value
                password_values = []
                for step in data.get("steps", []):
                    if "text" in step and forbidden in str(step["text"]).lower():
                        password_values.append(step)
                assert len(password_values) == 0, \
                    f"{filename} has 'password' in a step text value (hardcoded?)"
            else:
                assert forbidden not in raw_text, \
                    f"{filename} contains forbidden string '{forbidden}'"

    def test_no_email_addresses_in_steps(self, recipe):
        data, filename = recipe
        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")
        for step in data["steps"]:
            if "text" in step:
                text = str(step["text"])
                # Template variables are fine
                if VARIABLE_PATTERN.match(text):
                    continue
                match = email_pattern.search(text)
                assert match is None, \
                    f"{filename} step {step['step']} has hardcoded email: {match.group()}"

    def test_no_real_urls_in_text_fields(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if "text" in step:
                text = str(step["text"])
                if VARIABLE_PATTERN.match(text):
                    continue
                assert "http" not in text.lower(), \
                    f"{filename} step {step['step']} has hardcoded URL in text field"


# ---------------------------------------------------------------------------
# 7. Evidence Bundle Format Tests
# ---------------------------------------------------------------------------

class TestEvidenceBundle:
    """Each recipe must define expected evidence outputs."""

    REQUIRED_EVIDENCE_FIELDS = [
        "screenshots",
        "html_snapshots",
        "action_log",
        "agency_token",
    ]

    def test_expected_evidence_present(self, recipe):
        data, filename = recipe
        assert "expected_evidence" in data, \
            f"{filename} missing expected_evidence"

    def test_expected_evidence_has_required_fields(self, recipe):
        data, filename = recipe
        evidence = data["expected_evidence"]
        for field in self.REQUIRED_EVIDENCE_FIELDS:
            assert field in evidence, \
                f"{filename} expected_evidence missing '{field}'"

    def test_screenshots_enabled(self, recipe):
        data, filename = recipe
        assert data["expected_evidence"]["screenshots"] is True, \
            f"{filename} should have screenshots enabled"

    def test_agency_token_in_evidence(self, recipe):
        data, filename = recipe
        assert data["expected_evidence"]["agency_token"] is True, \
            f"{filename} must include agency_token in evidence"

    def test_at_least_one_screenshot_step(self, recipe):
        data, filename = recipe
        screenshot_steps = [
            s for s in data["steps"]
            if s.get("screenshot") is True or s.get("action") == "screenshot"
        ]
        assert len(screenshot_steps) >= 1, \
            f"{filename} must have at least one step with screenshot=true"


# ---------------------------------------------------------------------------
# 8. PM Triplet Completeness Tests
# ---------------------------------------------------------------------------

class TestPMTriplet:
    """Verify Gmail PM triplet files are complete and well-formed."""

    def test_pm_directory_exists(self):
        assert PRIMEWIKI_DIR.exists(), \
            f"primewiki/gmail/ directory missing at {PRIMEWIKI_DIR}"

    def test_selectors_json_exists(self):
        filepath = PRIMEWIKI_DIR / "selectors.json"
        assert filepath.exists(), "primewiki/gmail/selectors.json missing"

    def test_urls_json_exists(self):
        filepath = PRIMEWIKI_DIR / "urls.json"
        assert filepath.exists(), "primewiki/gmail/urls.json missing"

    def test_actions_json_exists(self):
        filepath = PRIMEWIKI_DIR / "actions.json"
        assert filepath.exists(), "primewiki/gmail/actions.json missing"

    def test_selectors_json_valid(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert data["platform"] == "gmail"
        assert "inbox" in data
        assert "compose" in data
        assert "search" in data
        assert "navigation" in data

    def test_urls_json_valid(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert data["platform"] == "gmail"
        assert "base_urls" in data
        assert "inbox" in data["base_urls"]
        assert data["base_urls"]["inbox"].startswith("https://")

    def test_actions_json_valid(self, all_pm_files):
        data = all_pm_files["actions.json"]
        assert data["platform"] == "gmail"
        assert "actions" in data
        actions = data["actions"]
        assert "compose" in actions
        assert "read_inbox" in actions
        assert "search" in actions
        assert "reply" in actions
        assert "label" in actions
        assert "archive" in actions

    def test_selectors_json_has_compose_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        compose = data["compose"]
        assert "compose_button" in compose
        assert "to_field" in compose
        assert "subject_field" in compose
        assert "body_field" in compose
        assert "send_keyboard" in compose

    def test_selectors_json_has_inbox_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        inbox = data["inbox"]
        assert "main_container" in inbox
        assert "email_rows" in inbox
        assert "email_subject" in inbox
        assert "email_sender" in inbox

    def test_selectors_json_has_search_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        search = data["search"]
        assert "search_bar" in search
        assert "search_result_rows" in search

    def test_actions_each_have_oauth3_scope(self, all_pm_files):
        data = all_pm_files["actions.json"]
        for action_id, action in data["actions"].items():
            assert "oauth3_scope" in action, \
                f"Action '{action_id}' missing oauth3_scope"
            assert action["oauth3_scope"].startswith("gmail."), \
                f"Action '{action_id}' scope should start with 'gmail.'"

    def test_actions_each_have_risk_level(self, all_pm_files):
        data = all_pm_files["actions.json"]
        valid_levels = {"low", "medium", "high"}
        for action_id, action in data["actions"].items():
            assert "risk_level" in action, \
                f"Action '{action_id}' missing risk_level"
            assert action["risk_level"] in valid_levels, \
                f"Action '{action_id}' risk_level '{action['risk_level']}' not valid"


# ---------------------------------------------------------------------------
# 9. Cross-Recipe Consistency Tests
# ---------------------------------------------------------------------------

class TestCrossRecipeConsistency:
    """Recipes should use consistent selectors that match the PM triplet."""

    def test_compose_button_selector_matches_pm(self, all_recipes, all_pm_files):
        """Compose recipe must use the same compose button selector as PM triplet."""
        compose_recipe = all_recipes["gmail-compose-email.json"]
        pm_selectors = all_pm_files["selectors.json"]

        pm_compose_btn = pm_selectors["compose"]["compose_button"]["selector"]
        recipe_compose_step = None
        for step in compose_recipe["steps"]:
            if step.get("description", "").lower().startswith("click compose"):
                recipe_compose_step = step
                break
        assert recipe_compose_step is not None, \
            "compose recipe should have a 'click compose' step"
        assert recipe_compose_step["selector"] == pm_compose_btn, \
            f"compose recipe selector '{recipe_compose_step['selector']}' != PM '{pm_compose_btn}'"

    def test_search_bar_selector_matches_pm(self, all_recipes, all_pm_files):
        """Search recipe must use the same search bar selector as PM triplet."""
        search_recipe = all_recipes["gmail-search-emails.json"]
        pm_selectors = all_pm_files["selectors.json"]

        pm_search_bar = pm_selectors["search"]["search_bar"]["selector"]
        search_steps = [
            s for s in search_recipe["steps"]
            if s.get("selector") == pm_search_bar
        ]
        assert len(search_steps) > 0, \
            f"search recipe should use PM search bar selector '{pm_search_bar}'"

    def test_all_recipes_use_gmail_domain(self, all_recipes):
        """All navigate steps must target Gmail domain."""
        for filename, data in all_recipes.items():
            for step in data["steps"]:
                if step["action"] == "navigate" and "target" in step:
                    assert "mail.google.com" in step["target"] or \
                           "gmail.com" in step["target"], \
                        f"{filename} step {step['step']} navigates outside Gmail"

    def test_all_recipes_load_session_first(self, all_recipes):
        """Every recipe should start with session loading."""
        for filename, data in all_recipes.items():
            first_step = data["steps"][0]
            assert first_step["action"] == "load_session", \
                f"{filename} should load session as first step"

    def test_keyboard_shortcut_for_send(self, all_recipes):
        """Compose and reply recipes must use Ctrl+Enter for send."""
        send_recipes = ["gmail-compose-email.json", "gmail-reply-email.json"]
        for filename in send_recipes:
            data = all_recipes[filename]
            ctrl_enter_steps = [
                s for s in data["steps"]
                if s.get("key") == "Control+Enter"
            ]
            assert len(ctrl_enter_steps) > 0, \
                f"{filename} must use Ctrl+Enter for sending"


# ---------------------------------------------------------------------------
# 10. Anti-Detection Pattern Tests
# ---------------------------------------------------------------------------

class TestAntiDetection:
    """Recipes must follow anti-detection best practices from PM knowledge."""

    def test_compose_uses_human_type_for_to_field(self, all_recipes):
        """Compose recipe must use human_type (80-200ms) for To field."""
        data = all_recipes["gmail-compose-email.json"]
        human_type_steps = [
            s for s in data["steps"]
            if s.get("action") == "human_type"
        ]
        assert len(human_type_steps) >= 1, \
            "compose recipe must have at least one human_type step"
        # Check the To field step specifically
        to_field_step = [
            s for s in human_type_steps
            if "autocomplete" in s.get("selector", "")
        ]
        assert len(to_field_step) == 1, \
            "compose recipe must have human_type for autocomplete (To) field"

    def test_compose_presses_enter_after_to(self, all_recipes):
        """Compose recipe must press Enter after To field to accept autocomplete."""
        data = all_recipes["gmail-compose-email.json"]
        enter_steps = [
            s for s in data["steps"]
            if s.get("action") == "keyboard_press" and s.get("key") == "Enter"
        ]
        assert len(enter_steps) >= 1, \
            "compose recipe must press Enter after To field for autocomplete"

    def test_search_uses_human_type(self, all_recipes):
        """Search recipe must use human_type for search query."""
        data = all_recipes["gmail-search-emails.json"]
        human_type_steps = [
            s for s in data["steps"]
            if s.get("action") == "human_type"
        ]
        assert len(human_type_steps) >= 1, \
            "search recipe must use human_type for search query"

    def test_compose_has_anti_detection_section(self, all_recipes):
        """Compose recipe should have explicit anti_detection config."""
        data = all_recipes["gmail-compose-email.json"]
        assert "anti_detection" in data, \
            "compose recipe should have anti_detection section"
        ad = data["anti_detection"]
        assert ad.get("human_typing") is True
        assert ad.get("keyboard_shortcuts_preferred") is True

    def test_no_instant_fill_action(self, all_recipes):
        """No recipe should use 'fill' action (bypasses bot detection)."""
        for filename, data in all_recipes.items():
            for step in data["steps"]:
                assert step["action"] != "fill", \
                    f"{filename} step {step['step']} uses 'fill' — must use human_type or type"


# ---------------------------------------------------------------------------
# 11. Input/Output Schema Tests
# ---------------------------------------------------------------------------

class TestInputOutputSchema:
    """Recipes with inputs must declare params; all must have output schema."""

    def test_compose_has_input_params(self, all_recipes):
        data = all_recipes["gmail-compose-email.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "to" in params
        assert "subject" in params
        assert "body" in params
        assert params["to"]["required"] is True

    def test_search_has_query_param(self, all_recipes):
        data = all_recipes["gmail-search-emails.json"]
        assert "input_params" in data
        assert "query" in data["input_params"]
        assert data["input_params"]["query"]["required"] is True

    def test_reply_has_body_param(self, all_recipes):
        data = all_recipes["gmail-reply-email.json"]
        assert "input_params" in data
        assert "body" in data["input_params"]
        assert data["input_params"]["body"]["required"] is True

    def test_label_has_label_param(self, all_recipes):
        data = all_recipes["gmail-label-emails.json"]
        assert "input_params" in data
        assert "label" in data["input_params"]
        assert data["input_params"]["label"]["required"] is True

    def test_output_schema_present(self, recipe):
        data, filename = recipe
        assert "output_schema" in data, f"{filename} missing output_schema"
        schema = data["output_schema"]
        assert schema.get("type") == "object", \
            f"{filename} output_schema type should be 'object'"
        assert "properties" in schema, \
            f"{filename} output_schema missing 'properties'"
        assert "required" in schema, \
            f"{filename} output_schema missing 'required'"

    def test_output_schema_has_timestamp(self, recipe):
        data, filename = recipe
        props = data["output_schema"]["properties"]
        assert "timestamp" in props, \
            f"{filename} output_schema should include 'timestamp'"


# ---------------------------------------------------------------------------
# 12. Metadata Tests
# ---------------------------------------------------------------------------

class TestMetadata:
    """Recipe metadata must be complete and correct."""

    def test_metadata_has_tags(self, recipe):
        data, filename = recipe
        metadata = data["metadata"]
        assert "tags" in metadata
        assert isinstance(metadata["tags"], list)
        assert len(metadata["tags"]) >= 2
        assert "gmail" in metadata["tags"]

    def test_metadata_has_difficulty(self, recipe):
        data, filename = recipe
        metadata = data["metadata"]
        assert "difficulty" in metadata
        assert metadata["difficulty"] in ("easy", "medium", "hard")

    def test_metadata_has_prerequisites(self, recipe):
        data, filename = recipe
        metadata = data["metadata"]
        assert "prerequisites" in metadata
        assert isinstance(metadata["prerequisites"], list)

    def test_metadata_has_duration_estimate(self, recipe):
        data, filename = recipe
        metadata = data["metadata"]
        assert "estimated_duration_s" in metadata
        assert isinstance(metadata["estimated_duration_s"], (int, float))
        assert metadata["estimated_duration_s"] > 0

    def test_metadata_has_idempotent_flag(self, recipe):
        data, filename = recipe
        metadata = data["metadata"]
        assert "idempotent" in metadata
        assert isinstance(metadata["idempotent"], bool)

    def test_metadata_has_destructive_flag(self, recipe):
        data, filename = recipe
        metadata = data["metadata"]
        assert "destructive" in metadata
        assert isinstance(metadata["destructive"], bool)

    def test_read_recipes_are_idempotent(self, all_recipes):
        """Read-only recipes should be marked idempotent."""
        for filename in ["gmail-read-inbox.json", "gmail-search-emails.json"]:
            data = all_recipes[filename]
            assert data["metadata"]["idempotent"] is True, \
                f"{filename} is read-only and should be idempotent"

    def test_no_recipe_is_destructive(self, all_recipes):
        """None of our Gmail recipes should be marked destructive."""
        for filename, data in all_recipes.items():
            assert data["metadata"]["destructive"] is False, \
                f"{filename} should not be marked destructive"

    def test_cloud_run_ready(self, recipe):
        data, filename = recipe
        metadata = data["metadata"]
        assert "cloud_run_ready" in metadata
        assert metadata["cloud_run_ready"] is True, \
            f"{filename} should be cloud_run_ready"


# ---------------------------------------------------------------------------
# 13. Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Each recipe should define error handling strategies."""

    def test_error_handling_present(self, recipe):
        data, filename = recipe
        assert "error_handling" in data, \
            f"{filename} missing error_handling section"

    def test_session_expired_handling(self, recipe):
        data, filename = recipe
        error_handling = data["error_handling"]
        assert "session_expired" in error_handling, \
            f"{filename} must handle session_expired error"
        desc = error_handling["session_expired"].lower()
        assert "session" in desc or "accounts.google.com" in desc, \
            f"{filename} session_expired handler should mention session/redirect"
