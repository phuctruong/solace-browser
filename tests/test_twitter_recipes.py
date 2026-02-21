"""
Twitter/X Recipes — Acceptance Tests (Rung 641)

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
    python -m pytest tests/test_twitter_recipes.py -v --tb=short -p no:httpbin

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
RECIPES_DIR = PROJECT_ROOT / "recipes" / "twitter"
PRIMEWIKI_DIR = PROJECT_ROOT / "primewiki" / "twitter"

SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECIPE_FILES = [
    "twitter-post-tweet.json",
    "twitter-read-timeline.json",
    "twitter-read-notifications.json",
    "twitter-search-tweets.json",
    "twitter-send-dm.json",
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

# Valid OAuth3 scope prefixes for Twitter
VALID_TWITTER_SCOPE_PREFIXES = [
    "twitter.read_",
    "twitter.write_",
]

# Read-only recipes that should be idempotent
READ_ONLY_RECIPES = [
    "twitter-read-timeline.json",
    "twitter-read-notifications.json",
    "twitter-search-tweets.json",
]

# Write recipes that should NOT be idempotent
WRITE_RECIPES = [
    "twitter-post-tweet.json",
    "twitter-send-dm.json",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def all_recipes():
    """Load and parse all Twitter recipe JSON files."""
    recipes = {}
    for filename in RECIPE_FILES:
        filepath = RECIPES_DIR / filename
        assert filepath.exists(), f"Recipe file missing: {filepath}"
        with open(filepath, "r") as f:
            recipes[filename] = json.load(f)
    return recipes


@pytest.fixture
def all_pm_files():
    """Load and parse all Twitter PM triplet JSON files."""
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
    """Verify all 5 Twitter recipe files exist and are valid JSON."""

    def test_recipes_directory_exists(self):
        assert RECIPES_DIR.exists(), f"recipes/twitter/ directory missing at {RECIPES_DIR}"

    def test_all_five_recipes_exist(self):
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

    def test_platform_is_twitter(self, recipe):
        data, filename = recipe
        assert data["platform"] == "twitter", f"{filename} platform should be 'twitter'"

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

    def test_scopes_have_twitter_prefix(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            assert scope.startswith("twitter."), \
                f"{filename} scope '{scope}' must start with 'twitter.'"

    def test_scopes_follow_naming_convention(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            has_valid_prefix = any(
                scope.startswith(prefix)
                for prefix in VALID_TWITTER_SCOPE_PREFIXES
            )
            assert has_valid_prefix, \
                f"{filename} scope '{scope}' does not match valid prefix pattern"

    def test_post_tweet_recipe_has_write_tweet_scope(self, all_recipes):
        data = all_recipes["twitter-post-tweet.json"]
        assert any("write_tweet" in s for s in data["oauth3_scopes"]), \
            "twitter-post-tweet must have write_tweet scope"

    def test_read_timeline_recipe_has_read_timeline_scope(self, all_recipes):
        data = all_recipes["twitter-read-timeline.json"]
        assert any("read_timeline" in s for s in data["oauth3_scopes"]), \
            "twitter-read-timeline must have read_timeline scope"

    def test_read_notifications_recipe_has_read_notifications_scope(self, all_recipes):
        data = all_recipes["twitter-read-notifications.json"]
        assert any("read_notifications" in s for s in data["oauth3_scopes"]), \
            "twitter-read-notifications must have read_notifications scope"

    def test_search_tweets_recipe_has_read_search_scope(self, all_recipes):
        data = all_recipes["twitter-search-tweets.json"]
        assert any("read_search" in s for s in data["oauth3_scopes"]), \
            "twitter-search-tweets must have read_search scope"

    def test_send_dm_recipe_has_write_dm_scope(self, all_recipes):
        data = all_recipes["twitter-send-dm.json"]
        assert any("write_dm" in s for s in data["oauth3_scopes"]), \
            "twitter-send-dm must have write_dm scope"


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

    def test_navigate_targets_are_twitter_urls(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate" and "target" in step \
                    and not step.get("optional"):
                target = step["target"]
                assert "x.com" in target or "twitter.com" in target, \
                    f"{filename} step {step['step']} navigate to non-Twitter URL: {target}"


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
    """Verify Twitter PM triplet files are complete and well-formed."""

    def test_pm_directory_exists(self):
        assert PRIMEWIKI_DIR.exists(), \
            f"primewiki/twitter/ directory missing at {PRIMEWIKI_DIR}"

    def test_selectors_json_exists(self):
        filepath = PRIMEWIKI_DIR / "selectors.json"
        assert filepath.exists(), "primewiki/twitter/selectors.json missing"

    def test_urls_json_exists(self):
        filepath = PRIMEWIKI_DIR / "urls.json"
        assert filepath.exists(), "primewiki/twitter/urls.json missing"

    def test_actions_json_exists(self):
        filepath = PRIMEWIKI_DIR / "actions.json"
        assert filepath.exists(), "primewiki/twitter/actions.json missing"

    def test_selectors_json_valid(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert data["platform"] == "twitter"
        assert "home" in data
        assert "compose" in data
        assert "tweet_card" in data
        assert "notifications" in data
        assert "messages" in data
        assert "search" in data
        assert "navigation" in data

    def test_selectors_json_has_compose_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        compose = data["compose"]
        assert "tweet_textarea" in compose
        assert "post_button_inline" in compose
        assert "char_counter" in compose

    def test_selectors_json_has_tweet_card_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        card = data["tweet_card"]
        assert "tweet_article" in card
        assert "tweet_text" in card
        assert "author_handle_link" in card
        assert "tweet_timestamp" in card
        assert "like_button" in card
        assert "retweet_button" in card
        assert "reply_button" in card

    def test_selectors_json_has_messages_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        msgs = data["messages"]
        assert "dm_drawer" in msgs
        assert "new_dm_button" in msgs
        assert "recipient_search_input" in msgs
        assert "dm_composer_input" in msgs
        assert "dm_send_button" in msgs

    def test_selectors_json_has_notifications_selectors(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        notifs = data["notifications"]
        assert "notification_cell" in notifs
        assert "notification_context" in notifs

    def test_urls_json_valid(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert data["platform"] == "twitter"
        assert "base_urls" in data
        assert "home" in data["base_urls"]
        assert data["base_urls"]["home"].startswith("https://")

    def test_urls_json_has_all_base_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        base = data["base_urls"]
        for required_url in ["home", "compose", "notifications", "messages", "search"]:
            assert required_url in base, f"urls.json missing base_url: {required_url}"

    def test_urls_json_has_auth_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "auth_urls" in data
        assert "login" in data["auth_urls"]

    def test_urls_json_has_url_detection(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "url_detection" in data
        assert "login_redirect" in data["url_detection"]

    def test_urls_json_has_dynamic_patterns(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "dynamic_patterns" in data
        assert "tweet_permalink" in data["dynamic_patterns"]
        assert "search_top" in data["dynamic_patterns"]
        assert "search_latest" in data["dynamic_patterns"]

    def test_actions_json_valid(self, all_pm_files):
        data = all_pm_files["actions.json"]
        assert data["platform"] == "twitter"
        assert "actions" in data
        actions = data["actions"]
        for required_action in [
            "compose_tweet", "send_tweet", "like_tweet",
            "retweet", "reply_to_tweet", "send_dm"
        ]:
            assert required_action in actions, \
                f"actions.json missing action: {required_action}"

    def test_actions_each_have_oauth3_scope(self, all_pm_files):
        data = all_pm_files["actions.json"]
        for action_id, action in data["actions"].items():
            assert "oauth3_scope" in action, \
                f"Action '{action_id}' missing oauth3_scope"
            assert action["oauth3_scope"].startswith("twitter."), \
                f"Action '{action_id}' scope should start with 'twitter.'"

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

    def test_all_recipes_use_twitter_domain(self, all_recipes):
        for filename, data in all_recipes.items():
            for step in data["steps"]:
                if step["action"] == "navigate" and "target" in step \
                        and not step.get("optional"):
                    target = step["target"]
                    assert "x.com" in target or "twitter.com" in target, \
                        f"{filename} step {step['step']} navigates outside Twitter: {target}"

    def test_all_recipes_load_session_first(self, all_recipes):
        for filename, data in all_recipes.items():
            first_step = data["steps"][0]
            assert first_step["action"] == "load_session", \
                f"{filename} should load session as first step"

    def test_post_tweet_recipe_uses_pm_compose_selector(self, all_recipes, all_pm_files):
        data = all_recipes["twitter-post-tweet.json"]
        pm_selectors = all_pm_files["selectors.json"]
        pm_textarea = pm_selectors["compose"]["tweet_textarea"]["selector"]
        textarea_steps = [
            s for s in data["steps"]
            if pm_textarea in s.get("selector", "")
        ]
        assert len(textarea_steps) >= 1, \
            f"post-tweet recipe should use PM compose textarea selector '{pm_textarea}'"

    def test_send_dm_recipe_uses_pm_dm_composer_selector(self, all_recipes, all_pm_files):
        data = all_recipes["twitter-send-dm.json"]
        pm_selectors = all_pm_files["selectors.json"]
        pm_composer = pm_selectors["messages"]["dm_composer_input"]["selector"]
        composer_steps = [
            s for s in data["steps"]
            if pm_composer in s.get("selector", "")
        ]
        assert len(composer_steps) >= 1, \
            f"send-dm recipe should use PM dm_composer_input selector '{pm_composer}'"

    def test_search_recipe_uses_url_pattern(self, all_recipes, all_pm_files):
        data = all_recipes["twitter-search-tweets.json"]
        pm_urls = all_pm_files["urls.json"]
        search_base = "x.com/search"
        navigate_steps = [
            s for s in data["steps"]
            if s["action"] == "navigate" and not s.get("optional")
        ]
        assert any(search_base in s.get("target", "") for s in navigate_steps), \
            f"search-tweets recipe must navigate to x.com/search"


# ---------------------------------------------------------------------------
# 10. Anti-Detection Pattern Tests
# ---------------------------------------------------------------------------

class TestAntiDetection:
    """Write recipes must follow anti-detection best practices."""

    def test_post_tweet_uses_human_type(self, all_recipes):
        data = all_recipes["twitter-post-tweet.json"]
        human_type_steps = [
            s for s in data["steps"]
            if s.get("action") == "human_type"
        ]
        assert len(human_type_steps) >= 1, \
            "post-tweet recipe must have at least one human_type step"

    def test_send_dm_uses_human_type(self, all_recipes):
        data = all_recipes["twitter-send-dm.json"]
        human_type_steps = [
            s for s in data["steps"]
            if s.get("action") == "human_type"
        ]
        assert len(human_type_steps) >= 2, \
            "send-dm recipe must have at least two human_type steps (recipient + message)"

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

    def test_no_instant_fill_on_tweet_text_fields(self, all_recipes):
        """Recipes must not use 'fill' action on tweet compose or DM text fields."""
        text_selector_patterns = [
            "tweetTextarea_0", "dmComposerTextInput"
        ]
        for filename, data in all_recipes.items():
            for step in data["steps"]:
                if step["action"] == "fill":
                    selector = step.get("selector", "")
                    for pattern in text_selector_patterns:
                        assert pattern not in selector, \
                            f"{filename} step {step['step']} uses fill on text field '{selector}'"


# ---------------------------------------------------------------------------
# 11. Input/Output Schema Tests
# ---------------------------------------------------------------------------

class TestInputOutputSchema:
    """Recipes with inputs must declare params; all must have output schema."""

    def test_post_tweet_has_required_input_params(self, all_recipes):
        data = all_recipes["twitter-post-tweet.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "text" in params, "post-tweet recipe must have 'text' param"
        assert params["text"]["required"] is True

    def test_post_tweet_has_optional_media_and_reply_params(self, all_recipes):
        data = all_recipes["twitter-post-tweet.json"]
        params = data["input_params"]
        assert "media_urls" in params, "post-tweet recipe must have 'media_urls' param"
        assert "reply_to_id" in params, "post-tweet recipe must have 'reply_to_id' param"
        assert params["media_urls"]["required"] is False
        assert params["reply_to_id"]["required"] is False

    def test_read_timeline_has_count_param(self, all_recipes):
        data = all_recipes["twitter-read-timeline.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "count" in params
        assert params["count"].get("default") == 20

    def test_read_timeline_has_filter_param(self, all_recipes):
        data = all_recipes["twitter-read-timeline.json"]
        params = data["input_params"]
        assert "filter" in params
        assert "enum" in params["filter"]
        assert "all" in params["filter"]["enum"]
        assert "following" in params["filter"]["enum"]

    def test_read_notifications_has_filter_param(self, all_recipes):
        data = all_recipes["twitter-read-notifications.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "filter" in params
        assert "enum" in params["filter"]
        assert "all" in params["filter"]["enum"]
        assert "mentions" in params["filter"]["enum"]

    def test_search_tweets_has_required_query_param(self, all_recipes):
        data = all_recipes["twitter-search-tweets.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "query" in params
        assert params["query"]["required"] is True

    def test_search_tweets_has_sort_param(self, all_recipes):
        data = all_recipes["twitter-search-tweets.json"]
        params = data["input_params"]
        assert "sort" in params
        assert "enum" in params["sort"]
        assert "relevance" in params["sort"]["enum"]
        assert "latest" in params["sort"]["enum"]

    def test_send_dm_has_required_params(self, all_recipes):
        data = all_recipes["twitter-send-dm.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "recipient_handle" in params
        assert "message_text" in params
        assert params["recipient_handle"]["required"] is True
        assert params["message_text"]["required"] is True

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
        assert "twitter" in metadata["tags"]

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
        assert "twitter_session" in metadata["prerequisites"]

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
        assert "session" in desc or "login" in desc, \
            f"{filename} session_expired handler should mention session or login"

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
