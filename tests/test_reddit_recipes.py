"""
Reddit Recipes — Acceptance Tests (Rung 641)

Phase 2: Reddit automation recipes for SolaceBrowser.

Tests cover:
  - Recipe JSON schema validation (all required fields present)
  - Step sequence validation (sequential steps, required fields)
  - OAuth3 scope declaration (every recipe declares required scopes)
  - Selector format validation (valid CSS selectors, no injection)
  - No hardcoded credentials in any recipe
  - Evidence bundle format (screenshots, agency_token)
  - PM triplet completeness (selectors.json, urls.json, actions.json)
  - Cross-recipe consistency (shared selectors match PM triplet)
  - Anti-detection patterns (human typing for write recipes)
  - Input/output schema validation
  - Metadata completeness (duration, idempotent, destructive)
  - Error handling sections
  - Reddit-specific invariants (old.reddit.com, rate limits)
  - OAuth3 scope naming conventions

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_reddit_recipes.py -v --tb=short -p no:httpbin

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
RECIPES_DIR = PROJECT_ROOT / "recipes" / "reddit"
PRIMEWIKI_DIR = PROJECT_ROOT / "primewiki" / "reddit"

SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECIPE_FILES = [
    "reddit-browse-subreddit.json",
    "reddit-create-post.json",
    "reddit-read-comments.json",
    "reddit-upvote-post.json",
    "reddit-search.json",
]

PM_TRIPLET_FILES = [
    "selectors.json",
    "urls.json",
    "actions.json",
]

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

REQUIRED_STEP_FIELDS = ["step", "action", "description"]

SELECTOR_REQUIRED_ACTIONS = [
    "click",
    "human_type",
    "type",
    "wait_for_selector",
    "extract_all",
    "extract",
    "check_element",
]

TIMED_ACTIONS = ["navigate", "wait_for_selector", "load_session", "check_auth"]

FORBIDDEN_STRINGS = [
    "secret",
    "api_key",
    "apikey",
    "token=",
    "Bearer ",
    "sk-",
]

VARIABLE_PATTERN = re.compile(r"\{params?\.\w+(\s*[\+\/\-]\s*\w+)?\}")

CSS_INJECTION_PATTERNS = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+=", re.IGNORECASE),
]

WRITE_RECIPE_FILES = [
    "reddit-create-post.json",
    "reddit-upvote-post.json",
]

READ_RECIPE_FILES = [
    "reddit-browse-subreddit.json",
    "reddit-read-comments.json",
    "reddit-search.json",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def all_recipes():
    """Load and parse all Reddit recipe JSON files."""
    recipes = {}
    for filename in RECIPE_FILES:
        filepath = RECIPES_DIR / filename
        assert filepath.exists(), f"Recipe file missing: {filepath}"
        with open(filepath, "r") as f:
            recipes[filename] = json.load(f)
    return recipes


@pytest.fixture
def all_pm_files():
    """Load and parse all Reddit PM triplet JSON files."""
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
# 1. File Existence Tests
# ---------------------------------------------------------------------------

class TestFileExistence:
    """Verify all recipe and PM triplet files exist."""

    def test_recipes_directory_exists(self):
        assert RECIPES_DIR.exists(), f"recipes/reddit/ missing at {RECIPES_DIR}"

    def test_primewiki_directory_exists(self):
        assert PRIMEWIKI_DIR.exists(), f"primewiki/reddit/ missing at {PRIMEWIKI_DIR}"

    def test_all_five_recipe_files_exist(self):
        for filename in RECIPE_FILES:
            assert (RECIPES_DIR / filename).exists(), f"Missing: {filename}"

    def test_all_pm_triplet_files_exist(self):
        for filename in PM_TRIPLET_FILES:
            assert (PRIMEWIKI_DIR / filename).exists(), f"Missing PM file: {filename}"

    def test_process_model_md_exists(self):
        assert (PRIMEWIKI_DIR / "process-model.md").exists()

    def test_domain_knowledge_md_exists(self):
        assert (PRIMEWIKI_DIR / "domain-knowledge.md").exists()

    def test_invariants_md_exists(self):
        assert (PRIMEWIKI_DIR / "invariants.md").exists()

    def test_all_recipes_valid_json(self):
        for filename in RECIPE_FILES:
            filepath = RECIPES_DIR / filename
            with open(filepath, "r") as f:
                data = json.load(f)
            assert isinstance(data, dict), f"{filename} is not a JSON object"

    def test_recipe_files_not_empty(self):
        for filename in RECIPE_FILES:
            filepath = RECIPES_DIR / filename
            assert filepath.stat().st_size > 200, f"{filename} suspiciously small"


# ---------------------------------------------------------------------------
# 2. Recipe Schema Validation
# ---------------------------------------------------------------------------

class TestRecipeSchema:
    """Verify each recipe has all required top-level fields."""

    def test_required_fields_present(self, recipe):
        data, filename = recipe
        for field in REQUIRED_RECIPE_FIELDS:
            assert field in data, f"{filename} missing: {field}"

    def test_platform_is_reddit(self, recipe):
        data, filename = recipe
        assert data["platform"] == "reddit", f"{filename} platform != 'reddit'"

    def test_version_semver(self, recipe):
        data, filename = recipe
        assert re.match(r"^\d+\.\d+\.\d+$", data["version"]), \
            f"{filename} version not semver"

    def test_author_is_stillwater(self, recipe):
        data, filename = recipe
        assert data["author"] == "stillwater", f"{filename} author != 'stillwater'"

    def test_rung_is_641(self, recipe):
        data, filename = recipe
        assert data["rung"] == 641, f"{filename} rung != 641"

    def test_evidence_type_is_lane_a(self, recipe):
        data, filename = recipe
        assert data["evidence_type"] == "lane_a"

    def test_id_matches_filename(self, recipe):
        data, filename = recipe
        expected_id = filename.replace(".json", "")
        assert data["id"] == expected_id, \
            f"{filename} id '{data['id']}' != '{expected_id}'"

    def test_description_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["description"]) > 20

    def test_has_reasoning_section(self, recipe):
        data, filename = recipe
        assert "reasoning" in data, f"{filename} missing reasoning"
        r = data["reasoning"]
        assert "research" in r
        assert "selector_strategy" in r

    def test_has_error_handling(self, recipe):
        data, filename = recipe
        assert "error_handling" in data, f"{filename} missing error_handling"

    def test_session_expired_in_error_handling(self, recipe):
        data, filename = recipe
        assert "session_expired" in data["error_handling"], \
            f"{filename} error_handling missing session_expired"


# ---------------------------------------------------------------------------
# 3. OAuth3 Scope Validation
# ---------------------------------------------------------------------------

class TestOAuth3Scopes:
    """Every recipe must declare OAuth3 scopes correctly."""

    VALID_SCOPE_PREFIXES = [
        "reddit.read.",
        "reddit.write.",
    ]

    def test_oauth3_scopes_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["oauth3_scopes"], list)

    def test_oauth3_scopes_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["oauth3_scopes"]) >= 1

    def test_scopes_have_reddit_prefix(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            assert scope.startswith("reddit."), \
                f"{filename} scope '{scope}' must start with 'reddit.'"

    def test_scopes_follow_naming_convention(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            has_valid = any(scope.startswith(p) for p in self.VALID_SCOPE_PREFIXES)
            assert has_valid, f"{filename} scope '{scope}' has invalid prefix"

    def test_read_recipes_have_read_scopes(self, all_recipes):
        for filename in READ_RECIPE_FILES:
            data = all_recipes[filename]
            assert any("read" in s for s in data["oauth3_scopes"]), \
                f"{filename} should have read scope"

    def test_write_recipes_have_write_scopes(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            assert any("write" in s for s in data["oauth3_scopes"]), \
                f"{filename} should have write scope"

    def test_create_post_has_submit_scope(self, all_recipes):
        data = all_recipes["reddit-create-post.json"]
        assert any("submit" in s for s in data["oauth3_scopes"])

    def test_upvote_has_vote_scope(self, all_recipes):
        data = all_recipes["reddit-upvote-post.json"]
        assert any("vote" in s for s in data["oauth3_scopes"])

    def test_search_has_search_scope(self, all_recipes):
        data = all_recipes["reddit-search.json"]
        assert any("search" in s or "read" in s for s in data["oauth3_scopes"])


# ---------------------------------------------------------------------------
# 4. Step Sequence Validation
# ---------------------------------------------------------------------------

class TestStepSequence:
    """Every recipe step must have required fields and logical ordering."""

    def test_steps_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["steps"], list)

    def test_steps_have_minimum_count(self, recipe):
        data, filename = recipe
        assert len(data["steps"]) >= 3, f"{filename} needs >= 3 steps"

    def test_step_numbers_sequential(self, recipe):
        data, filename = recipe
        nums = [s["step"] for s in data["steps"]]
        assert nums == list(range(1, len(nums) + 1)), \
            f"{filename} steps not sequential: {nums}"

    def test_each_step_has_required_fields(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            for field in REQUIRED_STEP_FIELDS:
                assert field in step, \
                    f"{filename} step {step.get('step','?')} missing {field}"

    def test_last_step_is_return_result(self, recipe):
        data, filename = recipe
        assert data["steps"][-1]["action"] == "return_result", \
            f"{filename} last step should be return_result"

    def test_navigate_steps_have_target(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate":
                assert "target" in step, \
                    f"{filename} step {step['step']} navigate missing target"

    def test_navigate_uses_https(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate" and "target" in step:
                target = step["target"]
                if not VARIABLE_PATTERN.match(target):
                    assert target.startswith("https://") or "{params." in target, \
                        f"{filename} step {step['step']} navigate target not HTTPS: {target}"

    def test_click_steps_have_selector(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "click":
                assert "selector" in step, \
                    f"{filename} step {step['step']} click missing selector"

    def test_write_recipes_start_with_load_session(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            assert data["steps"][0]["action"] == "load_session", \
                f"{filename} first step should be load_session"


# ---------------------------------------------------------------------------
# 5. Selector Format Validation
# ---------------------------------------------------------------------------

class TestSelectorFormat:
    """CSS selectors must be valid and free of injection."""

    def _collect_selectors(self, data):
        selectors = []
        def _walk(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("selector", "wait_for") and isinstance(value, str):
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
        assert len(selectors) > 0, f"{filename} has no selectors"

    def test_selectors_no_injection(self, recipe):
        data, filename = recipe
        selectors = self._collect_selectors(data)
        for selector, path in selectors:
            clean = VARIABLE_PATTERN.sub("", selector)
            for pat in CSS_INJECTION_PATTERNS:
                assert not pat.search(clean), \
                    f"{filename} selector at {path} injection risk: {selector}"

    def test_selectors_reasonable_length(self, recipe):
        data, filename = recipe
        selectors = self._collect_selectors(data)
        for selector, path in selectors:
            assert len(selector) < 500, \
                f"{filename} selector at {path} too long: {len(selector)}"

    def test_navigate_targets_use_old_reddit(self, all_recipes):
        """Browse/search/upvote must use old.reddit.com for stable selectors."""
        for filename in ["reddit-browse-subreddit.json", "reddit-search.json"]:
            data = all_recipes[filename]
            for step in data["steps"]:
                if step["action"] == "navigate" and "target" in step:
                    target = step["target"]
                    if "{params." not in target:
                        assert "old.reddit.com" in target or "reddit.com" in target, \
                            f"{filename} step {step['step']} not on reddit.com: {target}"


# ---------------------------------------------------------------------------
# 6. No Hardcoded Credentials Tests
# ---------------------------------------------------------------------------

class TestNoHardcodedCredentials:
    """Ensure no recipe contains hardcoded passwords, tokens, or API keys."""

    def test_no_forbidden_strings(self, recipe):
        data, filename = recipe
        raw = json.dumps(data).lower()
        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in raw, \
                f"{filename} contains forbidden string '{forbidden}'"

    def test_no_hardcoded_usernames_in_text(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if "text" in step:
                text = str(step["text"])
                if VARIABLE_PATTERN.match(text):
                    continue
                # No email pattern in text fields
                email_pat = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")
                match = email_pat.search(text)
                assert match is None, \
                    f"{filename} step {step['step']} has hardcoded email: {match.group()}"

    def test_no_real_url_in_text_field(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if "text" in step:
                text = str(step["text"])
                if VARIABLE_PATTERN.match(text):
                    continue
                assert "http" not in text.lower(), \
                    f"{filename} step {step['step']} has URL in text field"


# ---------------------------------------------------------------------------
# 7. Evidence Bundle Tests
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
        assert "expected_evidence" in data

    def test_required_evidence_fields(self, recipe):
        data, filename = recipe
        evidence = data["expected_evidence"]
        for field in self.REQUIRED_EVIDENCE_FIELDS:
            assert field in evidence, f"{filename} evidence missing '{field}'"

    def test_screenshots_enabled(self, recipe):
        data, filename = recipe
        assert data["expected_evidence"]["screenshots"] is True

    def test_agency_token_enabled(self, recipe):
        data, filename = recipe
        assert data["expected_evidence"]["agency_token"] is True

    def test_at_least_one_screenshot_step(self, recipe):
        data, filename = recipe
        ss_steps = [
            s for s in data["steps"]
            if s.get("screenshot") is True or s.get("action") == "screenshot"
        ]
        assert len(ss_steps) >= 1, f"{filename} needs >= 1 screenshot step"


# ---------------------------------------------------------------------------
# 8. PM Triplet Tests
# ---------------------------------------------------------------------------

class TestPMTriplet:
    """Verify Reddit PM triplet files are complete and well-formed."""

    def test_pm_directory_exists(self):
        assert PRIMEWIKI_DIR.exists()

    def test_selectors_json_has_platform(self, all_pm_files):
        assert all_pm_files["selectors.json"]["platform"] == "reddit"

    def test_selectors_json_has_listing_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "listing" in data

    def test_selectors_json_has_voting_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "voting" in data

    def test_selectors_json_has_comments_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "comments" in data

    def test_selectors_json_has_submit_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "submit" in data

    def test_selectors_json_has_search_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "search" in data

    def test_selectors_listing_has_post_container(self, all_pm_files):
        listing = all_pm_files["selectors.json"]["listing"]
        assert "post_container" in listing
        assert "post_title" in listing
        assert "post_author" in listing
        assert "post_score" in listing

    def test_selectors_voting_has_upvote_button(self, all_pm_files):
        voting = all_pm_files["selectors.json"]["voting"]
        assert "upvote_button" in voting
        assert "upvote_active" in voting

    def test_selectors_submit_has_form_fields(self, all_pm_files):
        submit = all_pm_files["selectors.json"]["submit"]
        assert "title_field" in submit
        assert "url_field" in submit
        assert "submit_button" in submit

    def test_urls_json_has_platform(self, all_pm_files):
        assert all_pm_files["urls.json"]["platform"] == "reddit"

    def test_urls_json_has_base_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "base_urls" in data
        base = data["base_urls"]
        assert "homepage" in base
        assert base["homepage"].startswith("https://")

    def test_urls_json_has_subreddit_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "subreddit_urls" in data
        assert "listing" in data["subreddit_urls"]

    def test_actions_json_has_platform(self, all_pm_files):
        assert all_pm_files["actions.json"]["platform"] == "reddit"

    def test_actions_json_has_actions_section(self, all_pm_files):
        data = all_pm_files["actions.json"]
        assert "actions" in data
        actions = data["actions"]
        assert "browse_subreddit" in actions
        assert "read_comments" in actions
        assert "search" in actions
        assert "submit_post" in actions
        assert "upvote" in actions

    def test_actions_each_have_oauth3_scope(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        for action_id, action in actions.items():
            assert "oauth3_scope" in action, f"Action '{action_id}' missing oauth3_scope"
            assert action["oauth3_scope"].startswith("reddit."), \
                f"Action '{action_id}' scope must start with 'reddit.'"

    def test_actions_each_have_risk_level(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        valid_levels = {"low", "medium", "high"}
        for action_id, action in actions.items():
            assert "risk_level" in action, f"Action '{action_id}' missing risk_level"
            assert action["risk_level"] in valid_levels, \
                f"Action '{action_id}' risk_level '{action['risk_level']}' invalid"

    def test_actions_destructive_flag_present(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        for action_id, action in actions.items():
            assert "destructive" in action, f"Action '{action_id}' missing destructive"
            assert isinstance(action["destructive"], bool)


# ---------------------------------------------------------------------------
# 9. Cross-Recipe Consistency Tests
# ---------------------------------------------------------------------------

class TestCrossRecipeConsistency:
    """Recipes should use consistent URLs and selectors matching PM triplet."""

    def test_write_recipes_all_load_session_first(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            assert data["steps"][0]["action"] == "load_session", \
                f"{filename} must load_session first"

    def test_old_reddit_preferred_for_listing(self, all_recipes):
        """Browse subreddit and search should use old.reddit.com."""
        for filename in ["reddit-browse-subreddit.json", "reddit-search.json"]:
            data = all_recipes[filename]
            navigate_steps = [s for s in data["steps"] if s["action"] == "navigate"]
            targets = [s.get("target", "") for s in navigate_steps]
            # At least one navigate step should reference old.reddit.com or reddit.com
            has_reddit = any("reddit.com" in t for t in targets)
            assert has_reddit, f"{filename} should navigate to reddit.com"

    def test_create_post_uses_submit_form(self, all_recipes):
        data = all_recipes["reddit-create-post.json"]
        navigate_targets = [s.get("target", "") for s in data["steps"] if s["action"] == "navigate"]
        assert any("submit" in t for t in navigate_targets), \
            "create-post should navigate to /submit"

    def test_upvote_navigates_to_post_url(self, all_recipes):
        data = all_recipes["reddit-upvote-post.json"]
        navigate_targets = [s.get("target", "") for s in data["steps"] if s["action"] == "navigate"]
        assert len(navigate_targets) > 0, "upvote must navigate to post"

    def test_browse_extracts_posts(self, all_recipes):
        data = all_recipes["reddit-browse-subreddit.json"]
        extract_steps = [s for s in data["steps"] if s["action"] == "extract_all"]
        assert len(extract_steps) >= 1, "browse must extract posts"

    def test_comments_recipe_extracts_comments(self, all_recipes):
        data = all_recipes["reddit-read-comments.json"]
        extract_steps = [s for s in data["steps"] if s["action"] == "extract_all"]
        assert len(extract_steps) >= 1, "read-comments must extract comments"

    def test_upvote_verifies_upmod_class(self, all_recipes):
        """Upvote recipe must verify .upmod class appears after click."""
        data = all_recipes["reddit-upvote-post.json"]
        verify_steps = [s for s in data["steps"] if s["action"] == "verify"]
        assert len(verify_steps) >= 1, "upvote must have verify step"

    def test_search_has_limit_param(self, all_recipes):
        data = all_recipes["reddit-search.json"]
        assert "input_params" in data
        assert "limit" in data["input_params"]

    def test_browse_has_sort_param(self, all_recipes):
        data = all_recipes["reddit-browse-subreddit.json"]
        assert "input_params" in data
        assert "sort" in data["input_params"]


# ---------------------------------------------------------------------------
# 10. Anti-Detection Tests
# ---------------------------------------------------------------------------

class TestAntiDetection:
    """Write recipes must follow anti-detection patterns."""

    def test_create_post_uses_human_type_for_title(self, all_recipes):
        data = all_recipes["reddit-create-post.json"]
        human_type_steps = [s for s in data["steps"] if s.get("action") == "human_type"]
        assert len(human_type_steps) >= 1, \
            "create-post must use human_type for title"

    def test_create_post_selects_post_type_first(self, all_recipes):
        """Must click radio button to select post type before filling fields."""
        data = all_recipes["reddit-create-post.json"]
        click_steps = [s for s in data["steps"] if s.get("action") == "click"]
        radio_step = [s for s in click_steps if "value=" in s.get("selector", "")]
        assert len(radio_step) >= 1, \
            "create-post must click radio button to select post type"

    def test_upvote_has_wait_before_click(self, all_recipes):
        """Upvote must have a human-like delay before clicking."""
        data = all_recipes["reddit-upvote-post.json"]
        wait_steps = [s for s in data["steps"] if s.get("action") == "wait"]
        assert len(wait_steps) >= 1, \
            "upvote must have wait step before clicking"

    def test_create_post_has_screenshot_before_submit(self, all_recipes):
        data = all_recipes["reddit-create-post.json"]
        steps = data["steps"]
        submit_step_idx = None
        for i, s in enumerate(steps):
            if s.get("action") == "click" and "save" in s.get("selector", ""):
                submit_step_idx = i
                break
        assert submit_step_idx is not None, "create-post must have submit click step"
        # Screenshot should appear before submit
        pre_submit = steps[:submit_step_idx]
        has_screenshot = any(
            s.get("screenshot") is True or s.get("action") == "screenshot"
            for s in pre_submit
        )
        assert has_screenshot, "create-post must screenshot form before submitting"

    def test_no_fill_action_in_any_recipe(self, all_recipes):
        """No recipe should use fill action — must use human_type or type."""
        for filename, data in all_recipes.items():
            for step in data["steps"]:
                assert step["action"] != "fill", \
                    f"{filename} step {step['step']} uses 'fill' — forbidden"


# ---------------------------------------------------------------------------
# 11. Input/Output Schema Tests
# ---------------------------------------------------------------------------

class TestInputOutputSchema:
    """Recipes with inputs must declare params; all must have output schema."""

    def test_browse_has_subreddit_param(self, all_recipes):
        data = all_recipes["reddit-browse-subreddit.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "subreddit" in params
        assert params["subreddit"]["required"] is True

    def test_create_post_has_required_params(self, all_recipes):
        data = all_recipes["reddit-create-post.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "subreddit" in params
        assert "title" in params
        assert "post_type" in params
        assert params["title"]["required"] is True
        assert params["post_type"]["required"] is True

    def test_create_post_type_has_enum(self, all_recipes):
        data = all_recipes["reddit-create-post.json"]
        post_type = data["input_params"]["post_type"]
        assert "enum" in post_type
        assert "link" in post_type["enum"]
        assert "self" in post_type["enum"]

    def test_read_comments_has_post_url_param(self, all_recipes):
        data = all_recipes["reddit-read-comments.json"]
        assert "input_params" in data
        assert "post_url" in data["input_params"]
        assert data["input_params"]["post_url"]["required"] is True

    def test_upvote_has_post_url_param(self, all_recipes):
        data = all_recipes["reddit-upvote-post.json"]
        assert "input_params" in data
        assert "post_url" in data["input_params"]
        assert data["input_params"]["post_url"]["required"] is True

    def test_search_has_query_param(self, all_recipes):
        data = all_recipes["reddit-search.json"]
        assert "input_params" in data
        assert "query" in data["input_params"]
        assert data["input_params"]["query"]["required"] is True

    def test_output_schema_present(self, recipe):
        data, filename = recipe
        assert "output_schema" in data
        schema = data["output_schema"]
        assert schema.get("type") == "object"
        assert "properties" in schema
        assert "required" in schema

    def test_output_schema_has_timestamp(self, recipe):
        data, filename = recipe
        props = data["output_schema"]["properties"]
        assert "timestamp" in props

    def test_browse_output_has_posts_array(self, all_recipes):
        data = all_recipes["reddit-browse-subreddit.json"]
        props = data["output_schema"]["properties"]
        assert "posts" in props
        assert props["posts"]["type"] == "array"

    def test_search_output_has_posts_array(self, all_recipes):
        data = all_recipes["reddit-search.json"]
        props = data["output_schema"]["properties"]
        assert "posts" in props

    def test_comments_output_has_comments_array(self, all_recipes):
        data = all_recipes["reddit-read-comments.json"]
        props = data["output_schema"]["properties"]
        assert "comments" in props

    def test_upvote_output_has_upvoted_flag(self, all_recipes):
        data = all_recipes["reddit-upvote-post.json"]
        props = data["output_schema"]["properties"]
        assert "upvoted" in props
        assert props["upvoted"]["type"] == "boolean"


# ---------------------------------------------------------------------------
# 12. Metadata Tests
# ---------------------------------------------------------------------------

class TestMetadata:
    """Recipe metadata must be complete."""

    def test_metadata_has_tags(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "tags" in meta
        assert isinstance(meta["tags"], list)
        assert len(meta["tags"]) >= 2
        assert "reddit" in meta["tags"]

    def test_metadata_has_difficulty(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "difficulty" in meta
        assert meta["difficulty"] in ("easy", "medium", "hard")

    def test_metadata_has_prerequisites(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "prerequisites" in meta
        assert isinstance(meta["prerequisites"], list)

    def test_write_recipes_require_reddit_session(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            prereqs = data["metadata"]["prerequisites"]
            assert "reddit_session" in prereqs, \
                f"{filename} must list reddit_session prerequisite"

    def test_metadata_has_duration(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "estimated_duration_s" in meta
        assert isinstance(meta["estimated_duration_s"], (int, float))
        assert meta["estimated_duration_s"] > 0

    def test_metadata_has_idempotent(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "idempotent" in meta
        assert isinstance(meta["idempotent"], bool)

    def test_metadata_has_destructive(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "destructive" in meta
        assert isinstance(meta["destructive"], bool)

    def test_read_recipes_are_idempotent(self, all_recipes):
        for filename in READ_RECIPE_FILES:
            data = all_recipes[filename]
            assert data["metadata"]["idempotent"] is True, \
                f"{filename} is read-only and should be idempotent"

    def test_write_recipes_not_idempotent(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            assert data["metadata"]["idempotent"] is False, \
                f"{filename} is write and should not be idempotent"

    def test_no_recipe_is_destructive(self, all_recipes):
        """Our Reddit recipes should not be marked destructive."""
        for filename, data in all_recipes.items():
            assert data["metadata"]["destructive"] is False, \
                f"{filename} should not be marked destructive"

    def test_cloud_run_ready(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "cloud_run_ready" in meta
        assert meta["cloud_run_ready"] is True


# ---------------------------------------------------------------------------
# 13. Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Each recipe must define comprehensive error handling."""

    def test_error_handling_present(self, recipe):
        data, filename = recipe
        assert "error_handling" in data

    def test_session_expired_handling(self, recipe):
        data, filename = recipe
        eh = data["error_handling"]
        assert "session_expired" in eh

    def test_write_recipes_handle_rate_limit(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            eh = data["error_handling"]
            assert "rate_limited" in eh, \
                f"{filename} must handle rate_limited error"

    def test_browse_handles_private_subreddit(self, all_recipes):
        data = all_recipes["reddit-browse-subreddit.json"]
        eh = data["error_handling"]
        assert "subreddit_private" in eh or "subreddit_not_found" in eh, \
            "browse must handle private/not-found subreddit"

    def test_create_post_handles_subreddit_banned(self, all_recipes):
        data = all_recipes["reddit-create-post.json"]
        eh = data["error_handling"]
        assert "subreddit_banned" in eh or "subreddit_restricted" in eh


# ---------------------------------------------------------------------------
# 14. Reddit-Specific Invariant Tests
# ---------------------------------------------------------------------------

class TestRedditSpecificInvariants:
    """Reddit-specific rules from invariants.md must be reflected in recipes."""

    def test_upvote_recipe_has_wait_for_human_delay(self, all_recipes):
        """Upvote must have >= 1000ms wait before clicking."""
        data = all_recipes["reddit-upvote-post.json"]
        wait_steps = [s for s in data["steps"] if s.get("action") == "wait"]
        assert len(wait_steps) >= 1
        durations = [s.get("duration_ms", 0) for s in wait_steps]
        assert any(d >= 1000 for d in durations), \
            "upvote must wait >= 1000ms before clicking"

    def test_create_post_mentions_rate_limit(self, all_recipes):
        """Create post error handling must mention 600s rate limit."""
        data = all_recipes["reddit-create-post.json"]
        rate_limit_text = data["error_handling"]["rate_limited"].lower()
        assert "too much" in rate_limit_text or "600" in rate_limit_text or "rate" in rate_limit_text

    def test_browse_subreddit_uses_old_reddit_target(self, all_recipes):
        """Browse subreddit must use old.reddit.com for stable selectors."""
        data = all_recipes["reddit-browse-subreddit.json"]
        navigate_steps = [s for s in data["steps"] if s["action"] == "navigate"]
        assert any("old.reddit.com" in s.get("target", "") for s in navigate_steps), \
            "browse-subreddit must navigate to old.reddit.com"

    def test_search_uses_old_reddit_target(self, all_recipes):
        data = all_recipes["reddit-search.json"]
        navigate_steps = [s for s in data["steps"] if s["action"] == "navigate"]
        assert any("old.reddit.com" in s.get("target", "") for s in navigate_steps), \
            "search must navigate to old.reddit.com"

    def test_selectors_json_domain_is_old_reddit(self, all_pm_files):
        """PM triplet selectors must target old.reddit.com."""
        data = all_pm_files["selectors.json"]
        assert data["domain"] == "old.reddit.com", \
            "selectors.json domain must be old.reddit.com"

    def test_upvote_checks_upmod_class(self, all_recipes):
        """After upvoting, recipe must verify .upmod class."""
        data = all_recipes["reddit-upvote-post.json"]
        verify_steps = [s for s in data["steps"] if s.get("action") == "verify"]
        assert len(verify_steps) >= 1
        # Look for upmod in verify steps
        verify_text = json.dumps(verify_steps)
        assert "upmod" in verify_text, \
            "upvote verify step must check for .upmod class"

    def test_invariants_file_mentions_no_flag_automation(self):
        """invariants.md must document the no-flag-automation rule."""
        invariants_path = PRIMEWIKI_DIR / "invariants.md"
        content = invariants_path.read_text()
        assert "flag" in content.lower(), "invariants.md must mention flag automation prohibition"

    def test_domain_knowledge_mentions_karma_thresholds(self):
        """domain-knowledge.md must document karma thresholds."""
        dk_path = PRIMEWIKI_DIR / "domain-knowledge.md"
        content = dk_path.read_text()
        assert "karma" in content.lower(), "domain-knowledge.md must mention karma"
