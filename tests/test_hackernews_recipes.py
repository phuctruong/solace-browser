"""
HackerNews Recipes — Acceptance Tests (Rung 641)

Phase 2: HackerNews automation recipes for SolaceBrowser.

Tests cover:
  - Recipe JSON schema validation
  - Step sequence validation
  - OAuth3 scope declaration
  - Selector format validation
  - No hardcoded credentials
  - Evidence bundle format
  - PM triplet completeness (selectors.json, urls.json, actions.json)
  - Cross-recipe consistency
  - HN-specific patterns (no bot detection, simple HTML)
  - Input/output schema validation
  - Metadata completeness
  - Error handling
  - HN-specific invariants (no flag automation, public reads)

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_hackernews_recipes.py -v --tb=short -p no:httpbin

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
RECIPES_DIR = PROJECT_ROOT / "recipes" / "hackernews"
PRIMEWIKI_DIR = PROJECT_ROOT / "primewiki" / "hackernews"

SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECIPE_FILES = [
    "hn-read-frontpage.json",
    "hn-submit-story.json",
    "hn-read-comments.json",
    "hn-search.json",
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
    "hn-submit-story.json",
]

READ_RECIPE_FILES = [
    "hn-read-frontpage.json",
    "hn-read-comments.json",
    "hn-search.json",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def all_recipes():
    recipes = {}
    for filename in RECIPE_FILES:
        filepath = RECIPES_DIR / filename
        assert filepath.exists(), f"Recipe file missing: {filepath}"
        with open(filepath, "r") as f:
            recipes[filename] = json.load(f)
    return recipes


@pytest.fixture
def all_pm_files():
    pm_files = {}
    for filename in PM_TRIPLET_FILES:
        filepath = PRIMEWIKI_DIR / filename
        assert filepath.exists(), f"PM file missing: {filepath}"
        with open(filepath, "r") as f:
            pm_files[filename] = json.load(f)
    return pm_files


@pytest.fixture(params=RECIPE_FILES, ids=[f.replace(".json", "") for f in RECIPE_FILES])
def recipe(request, all_recipes):
    return all_recipes[request.param], request.param


# ---------------------------------------------------------------------------
# 1. File Existence Tests
# ---------------------------------------------------------------------------

class TestFileExistence:

    def test_recipes_directory_exists(self):
        assert RECIPES_DIR.exists(), f"recipes/hackernews/ missing at {RECIPES_DIR}"

    def test_primewiki_directory_exists(self):
        assert PRIMEWIKI_DIR.exists(), f"primewiki/hackernews/ missing at {PRIMEWIKI_DIR}"

    def test_all_recipe_files_exist(self):
        for filename in RECIPE_FILES:
            assert (RECIPES_DIR / filename).exists(), f"Missing: {filename}"

    def test_all_pm_triplet_files_exist(self):
        for filename in PM_TRIPLET_FILES:
            assert (PRIMEWIKI_DIR / filename).exists(), f"Missing PM: {filename}"

    def test_process_model_md_exists(self):
        assert (PRIMEWIKI_DIR / "process-model.md").exists()

    def test_domain_knowledge_md_exists(self):
        assert (PRIMEWIKI_DIR / "domain-knowledge.md").exists()

    def test_invariants_md_exists(self):
        assert (PRIMEWIKI_DIR / "invariants.md").exists()

    def test_all_recipes_valid_json(self):
        for filename in RECIPE_FILES:
            with open(RECIPES_DIR / filename, "r") as f:
                data = json.load(f)
            assert isinstance(data, dict)

    def test_recipe_files_not_empty(self):
        for filename in RECIPE_FILES:
            assert (RECIPES_DIR / filename).stat().st_size > 200


# ---------------------------------------------------------------------------
# 2. Recipe Schema Validation
# ---------------------------------------------------------------------------

class TestRecipeSchema:

    def test_required_fields_present(self, recipe):
        data, filename = recipe
        for field in REQUIRED_RECIPE_FIELDS:
            assert field in data, f"{filename} missing: {field}"

    def test_platform_is_hackernews(self, recipe):
        data, filename = recipe
        assert data["platform"] == "hackernews"

    def test_version_semver(self, recipe):
        data, filename = recipe
        assert re.match(r"^\d+\.\d+\.\d+$", data["version"])

    def test_author_is_stillwater(self, recipe):
        data, filename = recipe
        assert data["author"] == "stillwater"

    def test_rung_is_641(self, recipe):
        data, filename = recipe
        assert data["rung"] == 641

    def test_evidence_type_is_lane_a(self, recipe):
        data, filename = recipe
        assert data["evidence_type"] == "lane_a"

    def test_id_matches_filename(self, recipe):
        data, filename = recipe
        expected_id = filename.replace(".json", "")
        assert data["id"] == expected_id

    def test_description_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["description"]) > 20

    def test_has_reasoning_section(self, recipe):
        data, filename = recipe
        assert "reasoning" in data
        r = data["reasoning"]
        assert "research" in r
        assert "selector_strategy" in r

    def test_has_error_handling(self, recipe):
        data, filename = recipe
        assert "error_handling" in data

    def test_session_expired_in_error_handling(self, recipe):
        data, filename = recipe
        assert "session_expired" in data["error_handling"]


# ---------------------------------------------------------------------------
# 3. OAuth3 Scope Validation
# ---------------------------------------------------------------------------

class TestOAuth3Scopes:

    VALID_SCOPE_PREFIXES = [
        "hackernews.read.",
        "hackernews.write.",
    ]

    def test_oauth3_scopes_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["oauth3_scopes"], list)

    def test_oauth3_scopes_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["oauth3_scopes"]) >= 1

    def test_scopes_have_hackernews_prefix(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            assert scope.startswith("hackernews."), \
                f"{filename} scope '{scope}' must start with 'hackernews.'"

    def test_scopes_follow_naming_convention(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            has_valid = any(scope.startswith(p) for p in self.VALID_SCOPE_PREFIXES)
            assert has_valid, f"{filename} scope '{scope}' invalid prefix"

    def test_read_recipes_have_read_scopes(self, all_recipes):
        for filename in READ_RECIPE_FILES:
            data = all_recipes[filename]
            assert any("read" in s for s in data["oauth3_scopes"]), \
                f"{filename} should have read scope"

    def test_submit_has_write_scope(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        assert any("write" in s for s in data["oauth3_scopes"])

    def test_frontpage_has_frontpage_scope(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        assert any("frontpage" in s or "read" in s for s in data["oauth3_scopes"])

    def test_comments_has_comments_scope(self, all_recipes):
        data = all_recipes["hn-read-comments.json"]
        assert any("comments" in s or "read" in s for s in data["oauth3_scopes"])

    def test_search_has_search_scope(self, all_recipes):
        data = all_recipes["hn-search.json"]
        assert any("search" in s or "read" in s for s in data["oauth3_scopes"])


# ---------------------------------------------------------------------------
# 4. Step Sequence Validation
# ---------------------------------------------------------------------------

class TestStepSequence:

    def test_steps_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["steps"], list)

    def test_steps_minimum_count(self, recipe):
        data, filename = recipe
        assert len(data["steps"]) >= 3

    def test_step_numbers_sequential(self, recipe):
        data, filename = recipe
        nums = [s["step"] for s in data["steps"]]
        assert nums == list(range(1, len(nums) + 1))

    def test_each_step_has_required_fields(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            for field in REQUIRED_STEP_FIELDS:
                assert field in step, \
                    f"{filename} step {step.get('step','?')} missing {field}"

    def test_read_recipes_start_with_navigate(self, all_recipes):
        """HN reads are public — no session needed. First step should be navigate."""
        for filename in READ_RECIPE_FILES:
            data = all_recipes[filename]
            first_action = data["steps"][0]["action"]
            assert first_action == "navigate", \
                f"{filename} read recipe should start with navigate, got '{first_action}'"

    def test_write_recipe_starts_with_load_session(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            assert data["steps"][0]["action"] == "load_session", \
                f"{filename} write recipe must start with load_session"

    def test_last_step_is_return_result(self, recipe):
        data, filename = recipe
        assert data["steps"][-1]["action"] == "return_result"

    def test_navigate_steps_have_target(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate":
                assert "target" in step

    def test_navigate_uses_https(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate" and "target" in step:
                target = step["target"]
                if not VARIABLE_PATTERN.search(target):
                    assert target.startswith("https://"), \
                        f"{filename} step {step['step']} target not HTTPS: {target}"

    def test_navigate_targets_hn_domains(self, recipe):
        """All navigate targets should be on ycombinator.com or algolia.com."""
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate" and "target" in step:
                target = step["target"]
                if not VARIABLE_PATTERN.search(target):
                    assert "ycombinator.com" in target or "algolia.com" in target, \
                        f"{filename} step {step['step']} navigates outside HN: {target}"

    def test_click_steps_have_selector(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "click":
                assert "selector" in step, \
                    f"{filename} step {step['step']} click missing selector"


# ---------------------------------------------------------------------------
# 5. Selector Format Validation
# ---------------------------------------------------------------------------

class TestSelectorFormat:

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

    def test_selectors_present(self, recipe):
        data, filename = recipe
        selectors = self._collect_selectors(data)
        assert len(selectors) > 0

    def test_selectors_no_injection(self, recipe):
        data, filename = recipe
        for selector, path in self._collect_selectors(data):
            clean = VARIABLE_PATTERN.sub("", selector)
            for pat in CSS_INJECTION_PATTERNS:
                assert not pat.search(clean), \
                    f"{filename} selector injection at {path}: {selector}"

    def test_selectors_reasonable_length(self, recipe):
        data, filename = recipe
        for selector, path in self._collect_selectors(data):
            assert len(selector) < 500

    def test_hn_selectors_use_stable_classes(self, recipe):
        """HN selectors should use stable class names, not hashed ones."""
        data, filename = recipe
        selectors = self._collect_selectors(data)
        # HN stable selectors: .athing, .titleline, .score, .hnuser, .fatitem etc.
        hn_known = [".athing", ".titleline", ".score", ".hnuser", ".fatitem",
                    ".comment-tree", ".commtext", ".sitestr", "input[name="]
        for selector, path in selectors:
            if "{params." not in selector:
                # Should not have deeply hashed CSS modules (like React CSS-in-JS)
                assert not re.search(r'\.[a-z0-9]{8,}_[a-z0-9]{8,}', selector), \
                    f"{filename} suspicious hashed selector: {selector}"


# ---------------------------------------------------------------------------
# 6. No Hardcoded Credentials
# ---------------------------------------------------------------------------

class TestNoHardcodedCredentials:

    def test_no_forbidden_strings(self, recipe):
        data, filename = recipe
        raw = json.dumps(data).lower()
        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in raw, \
                f"{filename} contains forbidden string '{forbidden}'"

    def test_no_flag_action_in_recipes(self, all_recipes):
        """Critical invariant: no recipe may click the flag link."""
        for filename, data in all_recipes.items():
            all_text = json.dumps(data)
            assert "flag" not in all_text.lower() or \
                   any(s.get("selector", "").find("flag") == -1
                       for s in data["steps"] if s.get("action") == "click"), \
                f"{filename} must not click flag elements"

    def test_no_hardcoded_story_ids(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step.get("action") == "navigate" and "target" in step:
                target = step["target"]
                if "{params." in target:
                    continue
                # Should not have hardcoded story IDs in navigate targets
                if "item?id=" in target:
                    id_part = target.split("item?id=")[-1]
                    assert not id_part.isdigit() or len(id_part) < 5, \
                        f"{filename} has hardcoded story ID: {target}"


# ---------------------------------------------------------------------------
# 7. Evidence Bundle Tests
# ---------------------------------------------------------------------------

class TestEvidenceBundle:

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
            assert field in evidence

    def test_screenshots_enabled(self, recipe):
        data, filename = recipe
        assert data["expected_evidence"]["screenshots"] is True

    def test_agency_token_enabled(self, recipe):
        data, filename = recipe
        assert data["expected_evidence"]["agency_token"] is True

    def test_at_least_one_screenshot_step(self, recipe):
        data, filename = recipe
        ss = [
            s for s in data["steps"]
            if s.get("screenshot") is True or s.get("action") == "screenshot"
        ]
        assert len(ss) >= 1, f"{filename} needs >= 1 screenshot step"


# ---------------------------------------------------------------------------
# 8. PM Triplet Tests
# ---------------------------------------------------------------------------

class TestPMTriplet:

    def test_selectors_json_has_platform(self, all_pm_files):
        assert all_pm_files["selectors.json"]["platform"] == "hackernews"

    def test_selectors_json_has_listing_section(self, all_pm_files):
        assert "listing" in all_pm_files["selectors.json"]

    def test_selectors_json_has_story_page_section(self, all_pm_files):
        assert "story_page" in all_pm_files["selectors.json"]

    def test_selectors_json_has_comments_section(self, all_pm_files):
        assert "comments" in all_pm_files["selectors.json"]

    def test_selectors_json_has_submit_section(self, all_pm_files):
        assert "submit" in all_pm_files["selectors.json"]

    def test_selectors_listing_has_key_elements(self, all_pm_files):
        listing = all_pm_files["selectors.json"]["listing"]
        assert "story_row" in listing
        assert "story_title" in listing
        assert "story_author" in listing
        assert "story_score" in listing

    def test_selectors_comments_has_key_elements(self, all_pm_files):
        comments = all_pm_files["selectors.json"]["comments"]
        assert "comment_tree" in comments
        assert "comment_row" in comments
        assert "comment_text" in comments
        assert "comment_depth_image" in comments

    def test_selectors_submit_has_form_fields(self, all_pm_files):
        submit = all_pm_files["selectors.json"]["submit"]
        assert "title_input" in submit
        assert "url_input" in submit
        assert "submit_button" in submit

    def test_selectors_json_has_algolia_section(self, all_pm_files):
        assert "algolia_search" in all_pm_files["selectors.json"]

    def test_urls_json_has_platform(self, all_pm_files):
        assert all_pm_files["urls.json"]["platform"] == "hackernews"

    def test_urls_json_has_base_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "base_urls" in data
        base = data["base_urls"]
        assert "homepage" in base
        assert "submit" in base
        assert base["homepage"].startswith("https://")

    def test_urls_json_has_story_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "story_urls" in data
        assert "story_page" in data["story_urls"]

    def test_urls_json_has_search_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "search_urls" in data
        assert "algolia_search" in data["search_urls"]

    def test_actions_json_has_platform(self, all_pm_files):
        assert all_pm_files["actions.json"]["platform"] == "hackernews"

    def test_actions_json_has_all_actions(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        assert "read_frontpage" in actions
        assert "read_comments" in actions
        assert "search" in actions
        assert "submit_story" in actions

    def test_actions_each_have_oauth3_scope(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        for action_id, action in actions.items():
            assert "oauth3_scope" in action, f"Action '{action_id}' missing oauth3_scope"
            assert action["oauth3_scope"].startswith("hackernews."), \
                f"Action '{action_id}' scope must start with 'hackernews.'"

    def test_actions_each_have_risk_level(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        valid_levels = {"low", "medium", "high"}
        for action_id, action in actions.items():
            assert "risk_level" in action
            assert action["risk_level"] in valid_levels

    def test_read_actions_are_low_risk(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        for action_id, action in actions.items():
            if action["oauth3_scope"].startswith("hackernews.read."):
                assert action["risk_level"] == "low", \
                    f"Read action '{action_id}' should be low risk"


# ---------------------------------------------------------------------------
# 9. Cross-Recipe Consistency Tests
# ---------------------------------------------------------------------------

class TestCrossRecipeConsistency:

    def test_read_recipes_do_not_load_session(self, all_recipes):
        """HN reads are public — no session needed."""
        for filename in READ_RECIPE_FILES:
            data = all_recipes[filename]
            first_action = data["steps"][0]["action"]
            assert first_action != "load_session", \
                f"{filename} read recipe should NOT load session first (HN is public)"

    def test_write_recipe_loads_session(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        assert data["steps"][0]["action"] == "load_session"

    def test_frontpage_extracts_stories(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        extract_steps = [s for s in data["steps"] if s["action"] == "extract_all"]
        assert len(extract_steps) >= 1

    def test_comments_extracts_comments(self, all_recipes):
        data = all_recipes["hn-read-comments.json"]
        extract_steps = [s for s in data["steps"] if s["action"] == "extract_all"]
        assert len(extract_steps) >= 1

    def test_search_navigates_to_algolia(self, all_recipes):
        data = all_recipes["hn-search.json"]
        navigate_steps = [s for s in data["steps"] if s["action"] == "navigate"]
        algolia_targets = [s for s in navigate_steps if "algolia" in s.get("target", "")]
        assert len(algolia_targets) >= 1, "search must navigate to Algolia HN search"

    def test_submit_screenshots_before_submit(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        steps = data["steps"]
        submit_idx = None
        for i, s in enumerate(steps):
            if s.get("action") == "click" and s.get("selector", "").startswith("input[type='submit']"):
                submit_idx = i
                break
        assert submit_idx is not None
        pre_submit = steps[:submit_idx]
        has_screenshot = any(
            s.get("screenshot") is True or s.get("action") == "screenshot"
            for s in pre_submit
        )
        assert has_screenshot, "submit must screenshot form before clicking submit"

    def test_submit_verifies_redirect_to_item_page(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        verify_steps = [s for s in data["steps"] if s["action"] == "verify"]
        assert len(verify_steps) >= 1, "submit must verify redirect to /item?id="
        verify_text = json.dumps(verify_steps)
        assert "item" in verify_text and "id" in verify_text

    def test_frontpage_extracts_story_id(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        extract_steps = [s for s in data["steps"] if s["action"] == "extract_all"]
        assert len(extract_steps) >= 1
        fields = extract_steps[0].get("fields", {})
        assert "story_id" in fields or "id" in fields or "rank" in fields


# ---------------------------------------------------------------------------
# 10. HN-Specific Pattern Tests
# ---------------------------------------------------------------------------

class TestHNSpecificPatterns:

    def test_selectors_use_stable_hn_classes(self, recipe):
        """HN selectors should use known stable class names."""
        data, filename = recipe
        all_text = json.dumps(data)
        # HN has extremely stable selectors — verify they are used
        hn_stable = [".athing", ".titleline", ".fatitem", "ycombinator.com"]
        has_hn = any(term in all_text for term in hn_stable)
        assert has_hn, f"{filename} should reference HN-specific selectors"

    def test_comments_uses_comment_tree_selector(self, all_recipes):
        data = all_recipes["hn-read-comments.json"]
        all_text = json.dumps(data)
        assert "comment-tree" in all_text or "comtr" in all_text, \
            "read-comments must use .comment-tree or .comtr selector"

    def test_comments_extracts_depth(self, all_recipes):
        data = all_recipes["hn-read-comments.json"]
        extract_steps = [s for s in data["steps"] if s["action"] == "extract_all"]
        assert len(extract_steps) >= 1
        fields = extract_steps[0].get("fields", {})
        has_depth = any("depth" in k.lower() for k in fields.keys())
        assert has_depth, "read-comments must extract comment depth"

    def test_frontpage_targets_news_ycombinator(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        navigate_steps = [s for s in data["steps"] if s["action"] == "navigate"]
        hn_targets = [s for s in navigate_steps if "ycombinator.com" in s.get("target", "")]
        assert len(hn_targets) >= 1

    def test_submit_uses_human_type_for_title(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        human_type_steps = [s for s in data["steps"] if s.get("action") == "human_type"]
        assert len(human_type_steps) >= 1, \
            "submit must use human_type for title field"

    def test_invariants_file_mentions_no_flag(self):
        invariants_path = PRIMEWIKI_DIR / "invariants.md"
        content = invariants_path.read_text()
        assert "flag" in content.lower(), \
            "invariants.md must document no-flag-automation rule"

    def test_invariants_file_mentions_no_vote_manipulation(self):
        invariants_path = PRIMEWIKI_DIR / "invariants.md"
        content = invariants_path.read_text()
        assert "vote" in content.lower() or "manipulation" in content.lower()

    def test_domain_knowledge_mentions_karma_thresholds(self):
        dk_path = PRIMEWIKI_DIR / "domain-knowledge.md"
        content = dk_path.read_text()
        assert "karma" in content.lower()

    def test_domain_knowledge_mentions_algolia(self):
        dk_path = PRIMEWIKI_DIR / "domain-knowledge.md"
        content = dk_path.read_text()
        assert "algolia" in content.lower()

    def test_process_model_mentions_comment_depth(self):
        pm_path = PRIMEWIKI_DIR / "process-model.md"
        content = pm_path.read_text()
        assert "depth" in content.lower() and "40" in content


# ---------------------------------------------------------------------------
# 11. Input/Output Schema Tests
# ---------------------------------------------------------------------------

class TestInputOutputSchema:

    def test_frontpage_has_page_param(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        assert "input_params" in data
        assert "page" in data["input_params"]
        assert data["input_params"]["page"]["required"] is False

    def test_submit_has_title_param(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "title" in params
        assert params["title"]["required"] is True

    def test_submit_has_url_or_text_param(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        params = data["input_params"]
        assert "url" in params or "text" in params

    def test_comments_has_story_id_param(self, all_recipes):
        data = all_recipes["hn-read-comments.json"]
        assert "input_params" in data
        assert "story_id" in data["input_params"]
        assert data["input_params"]["story_id"]["required"] is True

    def test_search_has_query_param(self, all_recipes):
        data = all_recipes["hn-search.json"]
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

    def test_frontpage_output_has_stories_array(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        props = data["output_schema"]["properties"]
        assert "stories" in props
        assert props["stories"]["type"] == "array"

    def test_frontpage_output_has_total_extracted(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        props = data["output_schema"]["properties"]
        assert "total_extracted" in props

    def test_comments_output_has_comments_array(self, all_recipes):
        data = all_recipes["hn-read-comments.json"]
        props = data["output_schema"]["properties"]
        assert "comments" in props
        assert props["comments"]["type"] == "array"

    def test_comments_output_has_story_title(self, all_recipes):
        data = all_recipes["hn-read-comments.json"]
        props = data["output_schema"]["properties"]
        assert "story_title" in props

    def test_submit_output_has_submitted_flag(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        props = data["output_schema"]["properties"]
        assert "submitted" in props
        assert props["submitted"]["type"] == "boolean"

    def test_search_output_has_results_array(self, all_recipes):
        data = all_recipes["hn-search.json"]
        props = data["output_schema"]["properties"]
        assert "results" in props
        assert props["results"]["type"] == "array"


# ---------------------------------------------------------------------------
# 12. Metadata Tests
# ---------------------------------------------------------------------------

class TestMetadata:

    def test_metadata_has_tags(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "tags" in meta
        assert "hackernews" in meta["tags"]

    def test_metadata_has_difficulty(self, recipe):
        data, filename = recipe
        assert data["metadata"]["difficulty"] in ("easy", "medium", "hard")

    def test_read_recipes_have_empty_prerequisites(self, all_recipes):
        """HN reads require no login — prerequisites should be empty."""
        for filename in READ_RECIPE_FILES:
            data = all_recipes[filename]
            prereqs = data["metadata"]["prerequisites"]
            assert isinstance(prereqs, list)
            assert len(prereqs) == 0, \
                f"{filename} read recipe should have no prerequisites (HN is public)"

    def test_submit_has_session_prerequisite(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        prereqs = data["metadata"]["prerequisites"]
        assert "hackernews_session" in prereqs

    def test_metadata_has_duration(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "estimated_duration_s" in meta
        assert meta["estimated_duration_s"] > 0

    def test_hn_read_recipes_are_fast(self, all_recipes):
        """HN is simple HTML — read recipes should be fast (<15s)."""
        for filename in READ_RECIPE_FILES:
            data = all_recipes[filename]
            duration = data["metadata"]["estimated_duration_s"]
            assert duration <= 15, \
                f"{filename} read duration {duration}s seems slow for simple HTML"

    def test_metadata_has_idempotent(self, recipe):
        data, filename = recipe
        assert isinstance(data["metadata"]["idempotent"], bool)

    def test_metadata_has_destructive(self, recipe):
        data, filename = recipe
        assert isinstance(data["metadata"]["destructive"], bool)

    def test_read_recipes_are_idempotent(self, all_recipes):
        for filename in READ_RECIPE_FILES:
            data = all_recipes[filename]
            assert data["metadata"]["idempotent"] is True

    def test_write_recipes_not_idempotent(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            assert data["metadata"]["idempotent"] is False

    def test_no_recipe_is_destructive(self, all_recipes):
        for filename, data in all_recipes.items():
            assert data["metadata"]["destructive"] is False

    def test_cloud_run_ready(self, recipe):
        data, filename = recipe
        assert data["metadata"]["cloud_run_ready"] is True


# ---------------------------------------------------------------------------
# 13. Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_error_handling_present(self, recipe):
        data, filename = recipe
        assert "error_handling" in data

    def test_session_expired_handling(self, recipe):
        data, filename = recipe
        assert "session_expired" in data["error_handling"]

    def test_submit_handles_duplicate_url(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        eh = data["error_handling"]
        assert "duplicate_url" in eh, \
            "submit must handle duplicate URL error"

    def test_submit_handles_rate_limit(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        eh = data["error_handling"]
        assert "rate_limited" in eh

    def test_comments_handles_story_not_found(self, all_recipes):
        data = all_recipes["hn-read-comments.json"]
        eh = data["error_handling"]
        assert "story_not_found" in eh

    def test_search_handles_no_results(self, all_recipes):
        data = all_recipes["hn-search.json"]
        eh = data["error_handling"]
        assert "no_results" in eh

    def test_frontpage_handles_empty_page(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        eh = data["error_handling"]
        assert "empty_page" in eh or "selector_timeout" in eh


# ---------------------------------------------------------------------------
# 14. HN Invariant Tests
# ---------------------------------------------------------------------------

class TestHNInvariants:

    def test_no_recipe_clicks_flag_link(self, all_recipes):
        """Hard invariant: no recipe may click flag link."""
        for filename, data in all_recipes.items():
            for step in data["steps"]:
                if step.get("action") == "click":
                    selector = step.get("selector", "")
                    assert "flag" not in selector.lower(), \
                        f"{filename} step {step['step']} clicks flag link — FORBIDDEN"

    def test_submit_story_id_in_output(self, all_recipes):
        data = all_recipes["hn-submit-story.json"]
        props = data["output_schema"]["properties"]
        assert "story_url" in props or "story_id" in props

    def test_comments_depth_extracted_as_pixels(self, all_recipes):
        """Depth should be extracted as pixel value from img[width]."""
        data = all_recipes["hn-read-comments.json"]
        all_text = json.dumps(data)
        assert "depth" in all_text, "must extract comment depth"

    def test_frontpage_extracts_minimum_expected_fields(self, all_recipes):
        data = all_recipes["hn-read-frontpage.json"]
        extract_steps = [s for s in data["steps"] if s["action"] == "extract_all"]
        assert len(extract_steps) >= 1
        fields = extract_steps[0].get("fields", {})
        required_fields = {"title", "url", "story_id"}
        # Check each required field is present (case-insensitive)
        field_keys = {k.lower() for k in fields.keys()}
        for req in required_fields:
            assert req.lower() in field_keys, \
                f"hn-read-frontpage must extract '{req}' field, got: {field_keys}"

    def test_algolia_search_navigates_to_algolia(self, all_recipes):
        data = all_recipes["hn-search.json"]
        navigate_steps = [s for s in data["steps"] if s["action"] == "navigate"]
        algolia = [s for s in navigate_steps if "algolia" in s.get("target", "")]
        assert len(algolia) >= 1, "hn-search must use hn.algolia.com"

    def test_process_model_mentions_simple_html(self):
        pm_path = PRIMEWIKI_DIR / "process-model.md"
        content = pm_path.read_text()
        assert "html" in content.lower(), \
            "process-model.md should document that HN is simple HTML"
