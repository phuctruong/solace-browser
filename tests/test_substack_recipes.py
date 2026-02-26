"""
Substack Recipes — Acceptance Tests (Rung 641)

FIRST MOVER: Substack automation recipes for SolaceBrowser.
No competitor has Substack automation recipes.

Tests cover:
  - Recipe schema validation (all required fields present)
  - Step sequence validation (each step has action, selectors, timeouts)
  - OAuth3 scope declaration (every recipe declares required scopes)
  - Selector format validation (valid CSS selectors)
  - No hardcoded credentials in any recipe
  - Evidence bundle format (each recipe defines expected evidence outputs)
  - PM triplet completeness (selectors.json, urls.json, actions.json)
  - Cross-recipe consistency (shared selectors match PM triplet)
  - Anti-detection patterns (human typing, field clicks)
  - Input/output schema validation
  - Metadata completeness (duration, idempotent, destructive, cloud_run_ready)
  - Error handling sections (session_expired, element_not_found, rate_limited)

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_substack_recipes.py -v --tb=short -p no:httpbin

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
RECIPES_DIR = PROJECT_ROOT / "data" / "default" / "recipes" / "substack"
PRIMEWIKI_DIR = PROJECT_ROOT / "data" / "default" / "primewiki" / "substack"

SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECIPE_FILES = [
    "substack-publish-post.json",
    "substack-get-stats.json",
    "substack-schedule-post.json",
    "substack-manage-subscribers.json",
    "substack-edit-post.json",
    "substack-read-comments.json",
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

# Forbidden strings (credentials, secrets)
FORBIDDEN_STRINGS = [
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

# CSS selector injection patterns
# Note: on\w+= is intentionally scoped to event handler attribute names (onclick=, onload=, etc.)
# to avoid false positives on legitimate CSS attributes like data-component='...'.
CSS_INJECTION_PATTERNS = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    # Match JS event handler attributes: onclick=, onload=, onmouseover= etc.
    # Use word boundary after 'on' to avoid matching data-component='...' (where 'onent=' would match)
    re.compile(r"\bon(click|load|mouse\w+|key\w+|submit|focus|blur|change|input|error|scroll|resize)=", re.IGNORECASE),
]

# Valid OAuth3 scope prefixes for Substack
VALID_SUBSTACK_SCOPE_PREFIXES = [
    "substack.read_",
    "substack.write_",
    "substack.schedule",
]

# Read-only recipes that should be idempotent
READ_ONLY_RECIPES = [
    "substack-get-stats.json",
    "substack-manage-subscribers.json",
    "substack-read-comments.json",
]

# Write recipes that should NOT be idempotent
WRITE_RECIPES = [
    "substack-publish-post.json",
    "substack-schedule-post.json",
    "substack-edit-post.json",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def all_recipes():
    """Load and parse all Substack recipe JSON files."""
    recipes = {}
    for filename in RECIPE_FILES:
        filepath = RECIPES_DIR / filename
        assert filepath.exists(), f"Recipe file missing: {filepath}"
        with open(filepath, "r") as f:
            recipes[filename] = json.load(f)
    return recipes


@pytest.fixture
def all_pm_files():
    """Load and parse all Substack PM triplet JSON files."""
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
    """Verify all 6 Substack recipe files exist and are valid JSON."""

    def test_recipes_directory_exists(self):
        assert RECIPES_DIR.exists(), f"data/default/recipes/substack/ directory missing at {RECIPES_DIR}"

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

    def test_platform_is_substack(self, recipe):
        data, filename = recipe
        assert data["platform"] == "substack", f"{filename} platform should be 'substack'"

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
        assert data["evidence_type"] == "lane_a", \
            f"{filename} evidence_type should be 'lane_a'"

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
        assert "selector_strategy" in reasoning, \
            f"{filename} reasoning missing 'selector_strategy'"


# ---------------------------------------------------------------------------
# 3. OAuth3 Scope Validation Tests
# ---------------------------------------------------------------------------

class TestOAuth3Scopes:
    """Every recipe must declare OAuth3 scopes correctly."""

    def test_oauth3_scopes_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["oauth3_scopes"], list), \
            f"{filename} oauth3_scopes must be a list"

    def test_oauth3_scopes_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["oauth3_scopes"]) >= 1, \
            f"{filename} must declare at least one OAuth3 scope"

    def test_scopes_have_substack_prefix(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            assert scope.startswith("substack."), \
                f"{filename} scope '{scope}' must start with 'substack.'"

    def test_scopes_follow_naming_convention(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            has_valid_prefix = any(
                scope.startswith(prefix)
                for prefix in VALID_SUBSTACK_SCOPE_PREFIXES
            )
            assert has_valid_prefix, \
                f"{filename} scope '{scope}' does not match valid prefix pattern"

    def test_publish_recipe_has_write_scope(self, all_recipes):
        data = all_recipes["substack-publish-post.json"]
        assert any("write_post" in s for s in data["oauth3_scopes"]), \
            "substack-publish-post must have write_post scope"

    def test_stats_recipe_has_read_stats_scope(self, all_recipes):
        data = all_recipes["substack-get-stats.json"]
        assert any("read_stats" in s for s in data["oauth3_scopes"]), \
            "substack-get-stats must have read_stats scope"

    def test_schedule_recipe_has_both_scopes(self, all_recipes):
        data = all_recipes["substack-schedule-post.json"]
        scopes = data["oauth3_scopes"]
        assert any("write_post" in s for s in scopes), \
            "substack-schedule-post must have write_post scope"
        assert any("schedule" in s for s in scopes), \
            "substack-schedule-post must have schedule scope"

    def test_subscribers_recipe_has_read_subscribers_scope(self, all_recipes):
        data = all_recipes["substack-manage-subscribers.json"]
        assert any("read_subscribers" in s for s in data["oauth3_scopes"]), \
            "substack-manage-subscribers must have read_subscribers scope"

    def test_edit_recipe_has_write_scope(self, all_recipes):
        data = all_recipes["substack-edit-post.json"]
        assert any("write_post" in s for s in data["oauth3_scopes"]), \
            "substack-edit-post must have write_post scope"

    def test_comments_recipe_has_read_comments_scope(self, all_recipes):
        data = all_recipes["substack-read-comments.json"]
        assert any("read_comments" in s for s in data["oauth3_scopes"]), \
            "substack-read-comments must have read_comments scope"


# ---------------------------------------------------------------------------
# 4. Step Sequence Validation Tests
# ---------------------------------------------------------------------------

class TestRecipeSteps:
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

    def test_first_step_is_load_session(self, recipe):
        data, filename = recipe
        first_action = data["steps"][0]["action"]
        assert first_action == "load_session", \
            f"{filename} first step should be load_session, got '{first_action}'"

    def test_last_step_is_return_result(self, recipe):
        data, filename = recipe
        last_action = data["steps"][-1]["action"]
        assert last_action == "return_result", \
            f"{filename} last step should be return_result, got '{last_action}'"

    def test_navigate_steps_have_target(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate" and not step.get("optional"):
                assert "target" in step, \
                    f"{filename} step {step['step']} navigate missing 'target'"
                assert step["target"].startswith("https://"), \
                    f"{filename} step {step['step']} navigate target must be HTTPS"

    def test_click_steps_have_selector(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "click" and not step.get("optional"):
                assert "selector" in step or "fallback_selector" in step, \
                    f"{filename} step {step['step']} click missing selector"

    def test_has_check_auth_step(self, recipe):
        data, filename = recipe
        auth_steps = [s for s in data["steps"] if s["action"] == "check_auth"]
        assert len(auth_steps) >= 1, \
            f"{filename} must have at least one check_auth step"

    def test_has_screenshot_step(self, recipe):
        data, filename = recipe
        screenshot_steps = [
            s for s in data["steps"]
            if s.get("screenshot") is True or s.get("action") == "screenshot"
        ]
        assert len(screenshot_steps) >= 1, \
            f"{filename} must have at least one step with screenshot=true"


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
                    if key in ("selector", "fallback_selector", "wait_for") \
                            and isinstance(value, str):
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
            clean = VARIABLE_PATTERN.sub("", selector)
            for pattern in CSS_INJECTION_PATTERNS:
                assert not pattern.search(clean), \
                    f"{filename} selector at {path} contains injection pattern: {selector}"

    def test_selectors_reasonable_length(self, recipe):
        data, filename = recipe
        selectors = self._collect_selectors(data)
        for selector, path in selectors:
            assert len(selector) < 500, \
                f"{filename} selector at {path} suspiciously long ({len(selector)} chars)"

    def test_navigate_targets_are_substack_urls(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate" and "target" in step:
                target = step["target"]
                assert "substack.com" in target, \
                    f"{filename} step {step['step']} navigate to non-Substack URL: {target}"


# ---------------------------------------------------------------------------
# 6. No Hardcoded Credentials Tests
# ---------------------------------------------------------------------------

class TestNoHardcodedCredentials:
    """Ensure no recipe contains hardcoded passwords, tokens, or API keys."""

    def test_no_forbidden_strings_in_recipe(self, recipe):
        data, filename = recipe
        raw_text = json.dumps(data).lower()
        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in raw_text, \
                f"{filename} contains forbidden string '{forbidden}'"

    def test_no_email_addresses_in_steps(self, recipe):
        data, filename = recipe
        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")
        for step in data["steps"]:
            for field in ("text", "value"):
                if field in step:
                    text = str(step[field])
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


# ---------------------------------------------------------------------------
# 8. PM Triplet Completeness Tests
# ---------------------------------------------------------------------------

class TestPMTriplet:
    """Verify Substack PM triplet files are complete and well-formed."""

    def test_pm_directory_exists(self):
        assert PRIMEWIKI_DIR.exists(), \
            f"data/default/primewiki/substack/ directory missing at {PRIMEWIKI_DIR}"

    def test_selectors_json_exists(self):
        filepath = PRIMEWIKI_DIR / "selectors.json"
        assert filepath.exists(), "data/default/primewiki/substack/selectors.json missing"

    def test_urls_json_exists(self):
        filepath = PRIMEWIKI_DIR / "urls.json"
        assert filepath.exists(), "data/default/primewiki/substack/urls.json missing"

    def test_actions_json_exists(self):
        filepath = PRIMEWIKI_DIR / "actions.json"
        assert filepath.exists(), "data/default/primewiki/substack/actions.json missing"

    def test_selectors_json_valid(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert data["platform"] == "substack"
        assert "dashboard" in data
        assert "editor" in data
        assert "posts_list" in data
        assert "stats" in data
        assert "subscribers" in data
        assert "comments" in data
        assert "navigation" in data

    def test_selectors_json_has_editor_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        editor = data["editor"]
        assert "title_field" in editor
        assert "body_field" in editor
        assert "publish_button" in editor
        assert "confirm_publish_button" in editor
        assert "schedule_later_option" in editor

    def test_selectors_json_has_stats_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        stats = data["stats"]
        assert "subscriber_count" in stats
        assert "open_rate" in stats
        assert "click_rate" in stats

    def test_selectors_json_has_subscriber_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        subs = data["subscribers"]
        assert "subscriber_rows" in subs
        assert "subscriber_email" in subs
        assert "search_input" in subs
        assert "filter_paid_tab" in subs

    def test_selectors_json_has_comment_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        comments = data["comments"]
        assert "comment_items" in comments
        assert "commenter_name" in comments
        assert "comment_body" in comments

    def test_urls_json_valid(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert data["platform"] == "substack"
        assert "base_urls" in data
        assert "dashboard" in data["base_urls"]
        assert data["base_urls"]["dashboard"].startswith("https://")

    def test_urls_json_has_all_base_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        base = data["base_urls"]
        for required_url in ["dashboard", "new_post", "posts", "stats", "subscribers"]:
            assert required_url in base, f"urls.json missing base_url: {required_url}"

    def test_urls_json_has_auth_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "auth_urls" in data
        assert "sign_in" in data["auth_urls"]

    def test_urls_json_has_url_detection(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "url_detection" in data
        assert "login_redirect" in data["url_detection"]

    def test_actions_json_valid(self, all_pm_files):
        data = all_pm_files["actions.json"]
        assert data["platform"] == "substack"
        assert "actions" in data
        actions = data["actions"]
        for required_action in [
            "new_post", "publish", "schedule", "edit",
            "view_stats", "manage_subscribers", "read_comments"
        ]:
            assert required_action in actions, \
                f"actions.json missing action: {required_action}"

    def test_actions_each_have_oauth3_scope(self, all_pm_files):
        data = all_pm_files["actions.json"]
        for action_id, action in data["actions"].items():
            assert "oauth3_scope" in action, \
                f"Action '{action_id}' missing oauth3_scope"
            assert action["oauth3_scope"].startswith("substack."), \
                f"Action '{action_id}' scope should start with 'substack.'"

    def test_actions_each_have_risk_level(self, all_pm_files):
        data = all_pm_files["actions.json"]
        valid_levels = {"low", "medium", "high"}
        for action_id, action in data["actions"].items():
            assert "risk_level" in action, \
                f"Action '{action_id}' missing risk_level"
            assert action["risk_level"] in valid_levels, \
                f"Action '{action_id}' risk_level '{action['risk_level']}' not valid"

    def test_actions_json_has_anti_detection_rules(self, all_pm_files):
        data = all_pm_files["actions.json"]
        assert "anti_detection_rules" in data, \
            "actions.json missing anti_detection_rules section"
        rules = data["anti_detection_rules"]
        assert "typing" in rules
        assert "critical_patterns" in rules


# ---------------------------------------------------------------------------
# 9. Cross-Recipe Consistency Tests
# ---------------------------------------------------------------------------

class TestCrossRecipeConsistency:
    """Recipes should use consistent selectors that match the PM triplet."""

    def test_all_recipes_use_substack_domain(self, all_recipes):
        for filename, data in all_recipes.items():
            for step in data["steps"]:
                if step["action"] == "navigate" and "target" in step:
                    target = step["target"]
                    if not step.get("optional"):
                        assert "substack.com" in target, \
                            f"{filename} step {step['step']} navigates outside Substack: {target}"

    def test_all_recipes_load_session_first(self, all_recipes):
        for filename, data in all_recipes.items():
            first_step = data["steps"][0]
            assert first_step["action"] == "load_session", \
                f"{filename} should load session as first step"

    def test_publish_recipe_uses_pm_editor_selectors(self, all_recipes, all_pm_files):
        data = all_recipes["substack-publish-post.json"]
        pm_selectors = all_pm_files["selectors.json"]
        pm_body = pm_selectors["editor"]["body_field"]["selector"]
        body_steps = [
            s for s in data["steps"]
            if pm_body in s.get("selector", "")
        ]
        assert len(body_steps) >= 1, \
            f"publish recipe should use PM body selector '{pm_body}'"

    def test_schedule_recipe_has_datetime_input_step(self, all_recipes):
        data = all_recipes["substack-schedule-post.json"]
        fill_steps = [
            s for s in data["steps"]
            if s["action"] == "fill" and "datetime" in s.get("selector", "")
        ]
        assert len(fill_steps) >= 1, \
            "schedule recipe must have a fill step for datetime input"

    def test_stats_recipe_uses_pm_stats_selectors(self, all_recipes, all_pm_files):
        data = all_recipes["substack-get-stats.json"]
        pm_selectors = all_pm_files["selectors.json"]
        pm_sub_count = pm_selectors["stats"]["subscriber_count"]["selector"]
        extract_steps = [
            s for s in data["steps"]
            if "extract" in s["action"] and pm_sub_count in s.get("selector", "")
        ]
        assert len(extract_steps) >= 1, \
            f"stats recipe should use PM subscriber_count selector '{pm_sub_count}'"


# ---------------------------------------------------------------------------
# 10. Anti-Detection Pattern Tests
# ---------------------------------------------------------------------------

class TestAntiDetection:
    """Write recipes must follow anti-detection best practices."""

    def test_publish_uses_human_type_for_title(self, all_recipes):
        data = all_recipes["substack-publish-post.json"]
        human_type_steps = [
            s for s in data["steps"]
            if s.get("action") == "human_type"
        ]
        assert len(human_type_steps) >= 1, \
            "publish recipe must have at least one human_type step for title"

    def test_schedule_uses_human_type_for_title(self, all_recipes):
        data = all_recipes["substack-schedule-post.json"]
        human_type_steps = [
            s for s in data["steps"]
            if s.get("action") == "human_type"
        ]
        assert len(human_type_steps) >= 1, \
            "schedule recipe must have at least one human_type step"

    def test_edit_uses_human_type(self, all_recipes):
        data = all_recipes["substack-edit-post.json"]
        human_type_steps = [
            s for s in data["steps"]
            if s.get("action") == "human_type"
        ]
        assert len(human_type_steps) >= 1, \
            "edit recipe must have at least one human_type step"

    def test_write_recipes_have_anti_detection_section(self, all_recipes):
        for filename in WRITE_RECIPES:
            data = all_recipes[filename]
            assert "anti_detection" in data, \
                f"{filename} should have anti_detection section"
            ad = data["anti_detection"]
            assert ad.get("human_typing") is True, \
                f"{filename} anti_detection.human_typing must be True"
            assert ad.get("avoid_instant_fill") is True, \
                f"{filename} anti_detection.avoid_instant_fill must be True"

    def test_no_instant_fill_on_text_fields(self, all_recipes):
        """Recipes must not use 'fill' action on title/body/subtitle text fields."""
        text_selectors_patterns = [
            "post-title", "post-subtitle", "ProseMirror", "Message Body"
        ]
        for filename, data in all_recipes.items():
            for step in data["steps"]:
                if step["action"] == "fill":
                    selector = step.get("selector", "")
                    for pattern in text_selectors_patterns:
                        assert pattern not in selector, \
                            f"{filename} step {step['step']} uses fill on text field '{selector}'"


# ---------------------------------------------------------------------------
# 11. Input/Output Schema Tests
# ---------------------------------------------------------------------------

class TestInputOutputSchema:
    """Recipes with inputs must declare params; all must have output schema."""

    def test_publish_has_required_input_params(self, all_recipes):
        data = all_recipes["substack-publish-post.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "title" in params, "publish recipe must have 'title' param"
        assert "body" in params, "publish recipe must have 'body' param"
        assert params["title"]["required"] is True
        assert params["body"]["required"] is True

    def test_publish_has_audience_param(self, all_recipes):
        data = all_recipes["substack-publish-post.json"]
        params = data["input_params"]
        assert "audience" in params, "publish recipe must have 'audience' param"
        assert "enum" in params["audience"], "audience param must have enum values"
        assert "everyone" in params["audience"]["enum"]
        assert "paid" in params["audience"]["enum"]

    def test_schedule_has_datetime_param(self, all_recipes):
        data = all_recipes["substack-schedule-post.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "schedule_datetime" in params
        assert params["schedule_datetime"]["required"] is True
        assert params["schedule_datetime"].get("format") == "date-time"

    def test_stats_has_date_range_param(self, all_recipes):
        data = all_recipes["substack-get-stats.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "date_range" in params
        assert "enum" in params["date_range"]

    def test_subscribers_has_filter_param(self, all_recipes):
        data = all_recipes["substack-manage-subscribers.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "filter" in params
        assert "enum" in params["filter"]
        assert "paid" in params["filter"]["enum"]
        assert "free" in params["filter"]["enum"]

    def test_comments_has_sort_by_param(self, all_recipes):
        data = all_recipes["substack-read-comments.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "sort_by" in params
        assert "enum" in params["sort_by"]
        assert "newest" in params["sort_by"]["enum"]
        assert "oldest" in params["sort_by"]["enum"]

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
        assert "substack" in metadata["tags"]

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
        assert "substack_session" in metadata["prerequisites"]

    def test_metadata_has_duration_estimate(self, recipe):
        data, filename = recipe
        metadata = data["metadata"]
        assert "estimated_duration_s" in metadata
        assert isinstance(metadata["estimated_duration_s"], (int, float))
        assert 5 <= metadata["estimated_duration_s"] <= 120, \
            f"{filename} duration {metadata['estimated_duration_s']}s outside 5-120s range"

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

    def test_read_only_recipes_are_idempotent(self, all_recipes):
        for filename in READ_ONLY_RECIPES:
            data = all_recipes[filename]
            assert data["metadata"]["idempotent"] is True, \
                f"{filename} is read-only and should be idempotent"

    def test_write_recipes_are_not_idempotent(self, all_recipes):
        for filename in WRITE_RECIPES:
            data = all_recipes[filename]
            assert data["metadata"]["idempotent"] is False, \
                f"{filename} is a write recipe and should not be idempotent"

    def test_no_recipe_is_destructive(self, all_recipes):
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
        assert "session" in desc or "sign-in" in desc, \
            f"{filename} session_expired handler should mention session or sign-in"

    def test_element_not_found_handling(self, recipe):
        data, filename = recipe
        error_handling = data["error_handling"]
        assert "element_not_found" in error_handling, \
            f"{filename} must handle element_not_found error"

    def test_rate_limited_handling(self, recipe):
        data, filename = recipe
        error_handling = data["error_handling"]
        assert "rate_limited" in error_handling, \
            f"{filename} must handle rate_limited error"
        desc = error_handling["rate_limited"].lower()
        assert "wait" in desc or "retry" in desc, \
            f"{filename} rate_limited handler should mention wait/retry"
