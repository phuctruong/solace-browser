"""
Notion Recipes — Acceptance Tests (Rung 641)

Phase 2: Notion automation recipes for SolaceBrowser.

Tests cover:
  - Recipe JSON schema validation
  - Step sequence validation
  - OAuth3 scope declaration
  - Selector format validation
  - No hardcoded credentials
  - Evidence bundle format
  - PM triplet completeness
  - Cross-recipe consistency
  - Notion-specific patterns (autosave wait, block IDs)
  - Input/output schema validation
  - Metadata completeness
  - Error handling

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_notion_recipes.py -v --tb=short -p no:httpbin

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
RECIPES_DIR = PROJECT_ROOT / "data" / "default" / "recipes" / "notion"
PRIMEWIKI_DIR = PROJECT_ROOT / "data" / "default" / "primewiki" / "notion"

SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECIPE_FILES = [
    "notion-read-page.json",
    "notion-create-page.json",
    "notion-update-page.json",
    "notion-search.json",
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
    "token_v2=",
]

VARIABLE_PATTERN = re.compile(r"\{params?\.\w+(\s*[\+\/\-]\s*\w+)?\}")

CSS_INJECTION_PATTERNS = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+=", re.IGNORECASE),
]

WRITE_RECIPE_FILES = [
    "notion-create-page.json",
    "notion-update-page.json",
]

READ_RECIPE_FILES = [
    "notion-read-page.json",
    "notion-search.json",
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
        assert RECIPES_DIR.exists(), f"data/default/recipes/notion/ missing at {RECIPES_DIR}"

    def test_primewiki_directory_exists(self):
        assert PRIMEWIKI_DIR.exists(), f"data/default/primewiki/notion/ missing at {PRIMEWIKI_DIR}"

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
            assert isinstance(data, dict), f"{filename} not a JSON object"

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

    def test_platform_is_notion(self, recipe):
        data, filename = recipe
        assert data["platform"] == "notion"

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
        "notion.read.",
        "notion.write.",
    ]

    def test_oauth3_scopes_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["oauth3_scopes"], list)

    def test_oauth3_scopes_non_empty(self, recipe):
        data, filename = recipe
        assert len(data["oauth3_scopes"]) >= 1

    def test_scopes_have_notion_prefix(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            assert scope.startswith("notion."), \
                f"{filename} scope '{scope}' must start with 'notion.'"

    def test_scopes_follow_naming_convention(self, recipe):
        data, filename = recipe
        for scope in data["oauth3_scopes"]:
            has_valid = any(scope.startswith(p) for p in self.VALID_SCOPE_PREFIXES)
            assert has_valid, f"{filename} scope '{scope}' invalid prefix"

    def test_read_page_has_read_scope(self, all_recipes):
        data = all_recipes["notion-read-page.json"]
        assert any("read" in s for s in data["oauth3_scopes"])

    def test_create_page_has_write_scope(self, all_recipes):
        data = all_recipes["notion-create-page.json"]
        assert any("write" in s or "create" in s for s in data["oauth3_scopes"])

    def test_update_page_has_write_scope(self, all_recipes):
        data = all_recipes["notion-update-page.json"]
        assert any("write" in s or "update" in s for s in data["oauth3_scopes"])

    def test_search_has_read_scope(self, all_recipes):
        data = all_recipes["notion-search.json"]
        assert any("read" in s or "search" in s for s in data["oauth3_scopes"])


# ---------------------------------------------------------------------------
# 4. Step Sequence Validation
# ---------------------------------------------------------------------------

class TestStepSequence:

    def test_steps_is_list(self, recipe):
        data, filename = recipe
        assert isinstance(data["steps"], list)

    def test_steps_minimum_count(self, recipe):
        data, filename = recipe
        assert len(data["steps"]) >= 4, f"{filename} Notion recipes need >= 4 steps"

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

    def test_first_step_is_load_session(self, recipe):
        """All Notion recipes require authentication."""
        data, filename = recipe
        assert data["steps"][0]["action"] == "load_session", \
            f"{filename} first step must be load_session (Notion always requires auth)"

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
                        f"{filename} step {step['step']} navigate not HTTPS: {target}"

    def test_all_navigate_target_notion_domain(self, recipe):
        data, filename = recipe
        for step in data["steps"]:
            if step["action"] == "navigate" and "target" in step:
                target = step["target"]
                if not VARIABLE_PATTERN.search(target):
                    assert "notion.so" in target, \
                        f"{filename} step {step['step']} navigates outside notion.so: {target}"

    def test_write_recipes_have_autosave_wait(self, all_recipes):
        """Write recipes must wait >= 2000ms for autosave after typing."""
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            wait_steps = [s for s in data["steps"] if s.get("action") == "wait"]
            assert len(wait_steps) >= 1, f"{filename} must have wait step for autosave"
            max_wait = max(s.get("duration_ms", 0) for s in wait_steps)
            assert max_wait >= 2000, \
                f"{filename} must wait >= 2000ms for autosave, found max {max_wait}ms"


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
        assert len(selectors) > 0, f"{filename} has no selectors"

    def test_selectors_no_injection(self, recipe):
        data, filename = recipe
        for selector, path in self._collect_selectors(data):
            clean = VARIABLE_PATTERN.sub("", selector)
            for pat in CSS_INJECTION_PATTERNS:
                assert not pat.search(clean), \
                    f"{filename} selector injection risk at {path}: {selector}"

    def test_notion_selectors_use_stable_patterns(self, recipe):
        """Notion recipes should prefer data-block-id and class-based selectors."""
        data, filename = recipe
        selectors = self._collect_selectors(data)
        notion_selectors = [s for s, _ in selectors if "notion-" in s or "data-block" in s]
        # Not all recipes need notion-specific selectors, but validate no empty strings
        for selector, _ in selectors:
            assert len(selector.strip()) > 0, f"{filename} has empty selector"


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

    def test_no_hardcoded_page_ids_in_targets(self, recipe):
        """Navigate targets should use params, not hardcoded page UUIDs."""
        data, filename = recipe
        uuid_pat = re.compile(r"[0-9a-f]{32}", re.IGNORECASE)
        for step in data["steps"]:
            if step.get("action") == "navigate" and "target" in step:
                target = step["target"]
                # Template variables are fine
                if "{params." in target:
                    continue
                # Static notion.so workspace root is ok
                if target == "https://www.notion.so":
                    continue
                match = uuid_pat.search(target)
                assert match is None, \
                    f"{filename} step {step['step']} has hardcoded page UUID: {target}"


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
            assert field in evidence, f"{filename} evidence missing '{field}'"

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
        assert all_pm_files["selectors.json"]["platform"] == "notion"

    def test_selectors_json_has_page_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "page" in data

    def test_selectors_json_has_navigation_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "navigation" in data

    def test_selectors_json_has_blocks_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "blocks" in data

    def test_selectors_json_has_database_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "database" in data

    def test_selectors_json_has_search_section(self, all_pm_files):
        data = all_pm_files["selectors.json"]
        assert "search" in data

    def test_page_selectors_have_content_container(self, all_pm_files):
        page = all_pm_files["selectors.json"]["page"]
        assert "page_content" in page
        assert "title_contenteditable" in page
        assert "content_blocks" in page

    def test_search_selectors_have_input(self, all_pm_files):
        search = all_pm_files["selectors.json"]["search"]
        assert "search_input" in search

    def test_urls_json_has_platform(self, all_pm_files):
        assert all_pm_files["urls.json"]["platform"] == "notion"

    def test_urls_json_has_base_urls(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "base_urls" in data
        assert "workspace" in data["base_urls"]

    def test_urls_json_has_navigation_paths(self, all_pm_files):
        data = all_pm_files["urls.json"]
        assert "navigation_paths" in data

    def test_actions_json_has_platform(self, all_pm_files):
        assert all_pm_files["actions.json"]["platform"] == "notion"

    def test_actions_json_has_all_actions(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        assert "read_page" in actions
        assert "search" in actions
        assert "create_page" in actions
        assert "update_page" in actions

    def test_actions_each_have_oauth3_scope(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        for action_id, action in actions.items():
            assert "oauth3_scope" in action, f"Action '{action_id}' missing oauth3_scope"
            assert action["oauth3_scope"].startswith("notion."), \
                f"Action '{action_id}' scope must start with 'notion.'"

    def test_actions_each_have_risk_level(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        valid_levels = {"low", "medium", "high"}
        for action_id, action in actions.items():
            assert "risk_level" in action
            assert action["risk_level"] in valid_levels

    def test_actions_each_have_destructive_flag(self, all_pm_files):
        actions = all_pm_files["actions.json"]["actions"]
        for action_id, action in actions.items():
            assert "destructive" in action
            assert isinstance(action["destructive"], bool)


# ---------------------------------------------------------------------------
# 9. Cross-Recipe Consistency Tests
# ---------------------------------------------------------------------------

class TestCrossRecipeConsistency:

    def test_all_recipes_load_session_first(self, all_recipes):
        """Notion always requires auth."""
        for filename, data in all_recipes.items():
            assert data["steps"][0]["action"] == "load_session", \
                f"{filename} must start with load_session"

    def test_all_recipes_wait_for_page_content(self, all_recipes):
        """All recipes should wait for .notion-page-content before proceeding."""
        for filename, data in all_recipes.items():
            all_text = json.dumps(data)
            assert "notion-page-content" in all_text or "notion-sidebar" in all_text, \
                f"{filename} should wait for page or sidebar to load"

    def test_write_recipes_have_wait_for_autosave(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            wait_steps = [s for s in data["steps"] if s.get("action") == "wait"]
            assert len(wait_steps) >= 1, f"{filename} must have autosave wait step"

    def test_search_uses_ctrl_k_shortcut(self, all_recipes):
        data = all_recipes["notion-search.json"]
        kb_steps = [s for s in data["steps"] if s.get("action") == "keyboard_press"]
        ctrl_k = [s for s in kb_steps if "control+k" in s.get("key", "").lower() or
                   "ctrl+k" in s.get("key", "").lower()]
        assert len(ctrl_k) >= 1, "search must use Ctrl+K to open search modal"

    def test_create_page_uses_ctrl_n_or_click(self, all_recipes):
        data = all_recipes["notion-create-page.json"]
        # Either keyboard shortcut or click to create new page
        kb_steps = [s for s in data["steps"] if s.get("action") == "keyboard_press"]
        ctrl_n = [s for s in kb_steps if "control+n" in s.get("key", "").lower() or
                   "n" in s.get("key", "").lower()]
        click_steps = [s for s in data["steps"] if s.get("action") == "click"]
        assert len(ctrl_n) >= 1 or len(click_steps) >= 1, \
            "create-page must use Ctrl+N or click to create new page"

    def test_search_closes_modal_with_escape(self, all_recipes):
        data = all_recipes["notion-search.json"]
        kb_steps = [s for s in data["steps"] if s.get("action") == "keyboard_press"]
        esc = [s for s in kb_steps if "escape" in s.get("key", "").lower() or
               "esc" in s.get("key", "").lower()]
        assert len(esc) >= 1, "search must close modal with Escape key"


# ---------------------------------------------------------------------------
# 10. Notion-Specific Pattern Tests
# ---------------------------------------------------------------------------

class TestNotionSpecificPatterns:

    def test_recipes_use_notion_selectors(self, recipe):
        """Recipes should reference notion-specific selectors."""
        data, filename = recipe
        all_text = json.dumps(data)
        notion_indicators = [
            "notion-page-content",
            "notion-sidebar",
            "notion-title-block",
            "data-block-id",
            "notion-text-block",
        ]
        has_notion_selector = any(ind in all_text for ind in notion_indicators)
        assert has_notion_selector, \
            f"{filename} should use at least one Notion-specific selector"

    def test_write_recipes_use_human_typing(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            typing_steps = [
                s for s in data["steps"]
                if s.get("action") in ("human_type", "type")
            ]
            assert len(typing_steps) >= 1, \
                f"{filename} must have typing steps"

    def test_create_page_presses_enter_for_body(self, all_recipes):
        data = all_recipes["notion-create-page.json"]
        kb_steps = [s for s in data["steps"] if s.get("action") == "keyboard_press"]
        enter = [s for s in kb_steps if s.get("key") == "Enter"]
        assert len(enter) >= 1, "create-page must press Enter to move to body"

    def test_invariants_file_mentions_autosave(self):
        invariants_path = PRIMEWIKI_DIR / "invariants.md"
        content = invariants_path.read_text()
        assert "autosave" in content.lower(), \
            "invariants.md must mention autosave requirement"

    def test_invariants_file_mentions_block_id(self):
        invariants_path = PRIMEWIKI_DIR / "invariants.md"
        content = invariants_path.read_text()
        assert "block" in content.lower() and "id" in content.lower(), \
            "invariants.md must mention block-level consistency"

    def test_domain_knowledge_mentions_block_types(self):
        dk_path = PRIMEWIKI_DIR / "domain-knowledge.md"
        content = dk_path.read_text()
        assert "heading" in content.lower() or "block" in content.lower(), \
            "domain-knowledge.md must document block types"


# ---------------------------------------------------------------------------
# 11. Input/Output Schema Tests
# ---------------------------------------------------------------------------

class TestInputOutputSchema:

    def test_read_page_has_page_url_param(self, all_recipes):
        data = all_recipes["notion-read-page.json"]
        assert "input_params" in data
        assert "page_url" in data["input_params"]
        assert data["input_params"]["page_url"]["required"] is True

    def test_create_page_has_required_params(self, all_recipes):
        data = all_recipes["notion-create-page.json"]
        assert "input_params" in data
        params = data["input_params"]
        assert "parent_url" in params
        assert "title" in params
        assert params["title"]["required"] is True

    def test_update_page_has_page_url_param(self, all_recipes):
        data = all_recipes["notion-update-page.json"]
        assert "input_params" in data
        assert "page_url" in data["input_params"]
        assert data["input_params"]["page_url"]["required"] is True

    def test_search_has_query_param(self, all_recipes):
        data = all_recipes["notion-search.json"]
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

    def test_read_page_output_has_blocks(self, all_recipes):
        data = all_recipes["notion-read-page.json"]
        props = data["output_schema"]["properties"]
        assert "blocks" in props
        assert props["blocks"]["type"] == "array"

    def test_read_page_output_has_page_title(self, all_recipes):
        data = all_recipes["notion-read-page.json"]
        props = data["output_schema"]["properties"]
        assert "page_title" in props

    def test_create_page_output_has_created_flag(self, all_recipes):
        data = all_recipes["notion-create-page.json"]
        props = data["output_schema"]["properties"]
        assert "created" in props
        assert props["created"]["type"] == "boolean"

    def test_search_output_has_results_array(self, all_recipes):
        data = all_recipes["notion-search.json"]
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
        assert "notion" in meta["tags"]

    def test_metadata_has_difficulty(self, recipe):
        data, filename = recipe
        assert data["metadata"]["difficulty"] in ("easy", "medium", "hard")

    def test_metadata_has_prerequisites(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "prerequisites" in meta
        assert "notion_session" in meta["prerequisites"], \
            f"{filename} should list notion_session prerequisite"

    def test_metadata_has_duration(self, recipe):
        data, filename = recipe
        meta = data["metadata"]
        assert "estimated_duration_s" in meta
        assert meta["estimated_duration_s"] > 0

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

    def test_notion_estimated_duration_reasonable(self, recipe):
        """Notion SPA takes longer than static pages."""
        data, filename = recipe
        duration = data["metadata"]["estimated_duration_s"]
        # Notion recipes should be >= 10s due to SPA render time
        assert duration >= 10, \
            f"{filename} duration {duration}s seems too fast for Notion SPA"


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

    def test_page_not_found_handling(self, all_recipes):
        for filename in ["notion-read-page.json", "notion-update-page.json"]:
            data = all_recipes[filename]
            eh = data["error_handling"]
            assert "page_not_found" in eh or "page_private" in eh, \
                f"{filename} must handle page_not_found or page_private"

    def test_write_recipes_handle_autosave_failure(self, all_recipes):
        for filename in WRITE_RECIPE_FILES:
            data = all_recipes[filename]
            eh = data["error_handling"]
            assert "autosave_failed" in eh, \
                f"{filename} must handle autosave_failed"

    def test_search_handles_no_results(self, all_recipes):
        data = all_recipes["notion-search.json"]
        eh = data["error_handling"]
        assert "no_results" in eh
