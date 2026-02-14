"""
Phase 4: Automated Posting - Comprehensive Test Suite (75 tests)

Tests the AutomationAPI layer that fills forms, clicks buttons, types text,
and verifies interactions via the Solace Browser extension.

Test Distribution (Verification Ladder):
  OAuth(39,63,91):   25 tests - API surface, selector resolution, basic interactions
  641 Edge:          21 tests - Missing elements, hidden elements, special chars, error cases
  274177 Stress:     18 tests - 100 field fills, 50 clicks, long text, multi-field, performance
  65537 God:         11 tests - Full form workflows, cross-platform, error recovery, E2E

Auth: 65537 | Northstar: Phuc Forecast
Verification: OAuth(39,63,91) -> 641 -> 274177 -> 65537
"""

import json
import time
import hashlib
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Mock infrastructure (no real browser needed)
# ---------------------------------------------------------------------------

class MockDOMElement:
    """Simulates a DOM element with properties matching content.js serializeElement."""

    def __init__(
        self,
        tag: str = "div",
        elem_id: str = "",
        class_name: str = "",
        text: str = "",
        role: str = "",
        aria_label: str = "",
        visible: bool = True,
        editable: bool = False,
        data_testid: str = "",
        name: str = "",
        placeholder: str = "",
        value: str = "",
    ):
        self.tag = tag.upper()
        self.id = elem_id
        self.class_name = class_name
        self.text = text
        self.role = role
        self.aria_label = aria_label
        self.visible = visible
        self.editable = editable
        self.data_testid = data_testid
        self.name = name
        self.placeholder = placeholder
        self.value = value

    def serialize(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "id": self.id,
            "class": self.class_name,
            "text": self.text[:100],
            "role": self.role,
            "aria_label": self.aria_label,
        }


class MockDOM:
    """In-memory DOM for selector resolution testing."""

    def __init__(self):
        self.elements: Dict[str, MockDOMElement] = {}
        self._by_role: Dict[str, List[MockDOMElement]] = {}
        self._by_testid: Dict[str, MockDOMElement] = {}
        self._by_name: Dict[str, MockDOMElement] = {}
        self._by_placeholder: Dict[str, MockDOMElement] = {}
        self._by_text: Dict[str, List[MockDOMElement]] = {}

    def add(self, selector: str, elem: MockDOMElement) -> "MockDOM":
        self.elements[selector] = elem
        if elem.role:
            self._by_role.setdefault(elem.role, []).append(elem)
        if elem.data_testid:
            self._by_testid[elem.data_testid] = elem
        if elem.name:
            self._by_name[elem.name] = elem
        if elem.placeholder:
            self._by_placeholder[elem.placeholder] = elem
        if elem.text:
            self._by_text.setdefault(elem.text, []).append(elem)
        return self

    def query(self, selector: str) -> Optional[MockDOMElement]:
        return self.elements.get(selector)

    def query_by_testid(self, testid: str) -> Optional[MockDOMElement]:
        return self._by_testid.get(testid)

    def query_by_role(self, role: str, name: str = "") -> Optional[MockDOMElement]:
        candidates = self._by_role.get(role, [])
        if not name:
            return candidates[0] if candidates else None
        for c in candidates:
            if c.aria_label == name or c.text == name:
                return c
        return None

    def query_by_name(self, name: str) -> Optional[MockDOMElement]:
        return self._by_name.get(name)

    def query_by_placeholder(self, placeholder: str) -> Optional[MockDOMElement]:
        return self._by_placeholder.get(placeholder)


class AutomationAPI:
    """
    Pure-logic AutomationAPI matching the Phase 4 specification.

    This class encapsulates the selector resolution, visibility checks,
    field clearing, value verification, and interaction sequencing that
    the real content.js / background.js will implement.
    """

    SELECTOR_PRIORITY = [
        "data_testid", "id", "aria_label", "name",
        "role_text", "placeholder", "css_selector", "xpath", "text",
    ]

    def __init__(self, dom: MockDOM):
        self.dom = dom
        self.interactions: List[Dict] = []

    # -- Selector resolution --------------------------------------------------

    def resolve_element(self, ref: Dict[str, Any]) -> Optional[MockDOMElement]:
        """
        Try all selector strategies in priority order until one succeeds.

        ref can contain: data_testid, id, aria_label, name, role, text,
                         placeholder, css_selector, xpath
        """
        # 1. data-testid
        testid = ref.get("data_testid")
        if testid:
            elem = self.dom.query_by_testid(testid)
            if elem:
                return elem

        # 2. id -> CSS #id
        elem_id = ref.get("id")
        if elem_id:
            elem = self.dom.query(f"#{elem_id}")
            if elem:
                return elem

        # 3. aria-label
        aria = ref.get("aria_label")
        if aria:
            for sel, el in self.dom.elements.items():
                if el.aria_label == aria:
                    return el

        # 4. name attribute
        name = ref.get("name")
        if name:
            elem = self.dom.query_by_name(name)
            if elem:
                return elem

        # 5. role + text
        role = ref.get("role")
        text = ref.get("text")
        if role:
            elem = self.dom.query_by_role(role, text or "")
            if elem:
                return elem

        # 6. placeholder
        placeholder = ref.get("placeholder")
        if placeholder:
            elem = self.dom.query_by_placeholder(placeholder)
            if elem:
                return elem

        # 7. css_selector
        css = ref.get("css_selector")
        if css:
            elem = self.dom.query(css)
            if elem:
                return elem

        # 8. xpath (mapped to css for mock)
        xpath = ref.get("xpath")
        if xpath:
            elem = self.dom.query(xpath)
            if elem:
                return elem

        return None

    # -- Visibility & scrolling -----------------------------------------------

    def ensure_visible(self, elem: MockDOMElement) -> Dict[str, Any]:
        """Check visibility and simulate scrollIntoView."""
        if not elem.visible:
            return {"success": False, "error": f"Element not visible: {elem.tag}#{elem.id}"}
        return {"success": True, "scrolled": True}

    # -- Core interactions ----------------------------------------------------

    def fill_field(self, ref: Dict, value: str) -> Dict[str, Any]:
        """Fill a form field: resolve -> visible -> focus -> clear -> type -> verify."""
        elem = self.resolve_element(ref)
        if not elem:
            return {"success": False, "error": "Element not found", "ref": ref}

        vis = self.ensure_visible(elem)
        if not vis["success"]:
            return vis

        # Check editable
        if not elem.editable and elem.tag not in ("INPUT", "TEXTAREA"):
            if elem.tag == "DIV" and elem.role != "textbox":
                return {"success": False, "error": f"Element not editable: {elem.tag}", "ref": ref}

        # Clear existing value
        old_value = elem.value
        elem.value = ""

        # Type new value
        elem.value = value

        # Verify
        if elem.value != value:
            return {
                "success": False,
                "error": f"Value mismatch: expected={value!r}, got={elem.value!r}",
                "ref": ref,
            }

        self.interactions.append({
            "type": "fill",
            "ref": ref,
            "value": value,
            "old_value": old_value,
            "element": elem.serialize(),
            "timestamp": time.time(),
        })

        return {
            "success": True,
            "typed": len(value),
            "element": elem.serialize(),
            "verified": True,
        }

    def click_button(self, ref: Dict) -> Dict[str, Any]:
        """Click a button/element: resolve -> visible -> scroll -> click."""
        elem = self.resolve_element(ref)
        if not elem:
            return {"success": False, "error": "Element not found", "ref": ref}

        vis = self.ensure_visible(elem)
        if not vis["success"]:
            return vis

        self.interactions.append({
            "type": "click",
            "ref": ref,
            "element": elem.serialize(),
            "timestamp": time.time(),
        })

        return {
            "success": True,
            "clicked": True,
            "element": elem.serialize(),
        }

    def select_option(self, ref: Dict, value: str, label: str = "") -> Dict[str, Any]:
        """Select an option from a dropdown."""
        elem = self.resolve_element(ref)
        if not elem:
            return {"success": False, "error": "Element not found", "ref": ref}

        vis = self.ensure_visible(elem)
        if not vis["success"]:
            return vis

        if elem.tag != "SELECT":
            return {"success": False, "error": f"Not a select element: {elem.tag}", "ref": ref}

        elem.value = value

        self.interactions.append({
            "type": "select",
            "ref": ref,
            "value": value,
            "label": label,
            "element": elem.serialize(),
            "timestamp": time.time(),
        })

        return {"success": True, "selected": value, "label": label, "element": elem.serialize()}

    def type_text(self, ref: Dict, text: str, clear_first: bool = True) -> Dict[str, Any]:
        """Type text character by character (supports shift for uppercase)."""
        elem = self.resolve_element(ref)
        if not elem:
            return {"success": False, "error": "Element not found", "ref": ref}

        vis = self.ensure_visible(elem)
        if not vis["success"]:
            return vis

        if clear_first:
            elem.value = ""

        # Character-by-character typing
        for ch in text:
            elem.value += ch

        if elem.value != (text if clear_first else elem.value):
            return {"success": False, "error": "Type verification failed", "ref": ref}

        self.interactions.append({
            "type": "type",
            "ref": ref,
            "text": text,
            "clear_first": clear_first,
            "element": elem.serialize(),
            "timestamp": time.time(),
        })

        return {
            "success": True,
            "typed": len(text),
            "element": elem.serialize(),
            "verified": True,
        }

    def verify_interaction(self, ref: Dict, expected_value: str = None) -> Dict[str, Any]:
        """Verify an element's state after interaction."""
        elem = self.resolve_element(ref)
        if not elem:
            return {"success": False, "error": "Element not found for verification", "ref": ref}

        result = {"success": True, "element": elem.serialize(), "found": True, "visible": elem.visible}

        if expected_value is not None:
            result["value_match"] = (elem.value == expected_value)
            result["actual_value"] = elem.value
            result["expected_value"] = expected_value
            if not result["value_match"]:
                result["success"] = False
                result["error"] = f"Value mismatch: expected={expected_value!r}, got={elem.value!r}"

        return result

    def execute_workflow(self, steps: List[Dict]) -> Dict[str, Any]:
        """Execute a sequence of interactions as a workflow."""
        results = []
        for i, step in enumerate(steps):
            action = step.get("action")
            ref = step.get("ref", {})

            if action == "fill":
                r = self.fill_field(ref, step.get("value", ""))
            elif action == "click":
                r = self.click_button(ref)
            elif action == "select":
                r = self.select_option(ref, step.get("value", ""), step.get("label", ""))
            elif action == "type":
                r = self.type_text(ref, step.get("text", ""), step.get("clear_first", True))
            elif action == "verify":
                r = self.verify_interaction(ref, step.get("expected_value"))
            else:
                r = {"success": False, "error": f"Unknown action: {action}"}

            r["step_index"] = i
            results.append(r)

            # Stop on first failure unless continue_on_error
            if not r.get("success") and not step.get("continue_on_error"):
                return {
                    "success": False,
                    "completed": i,
                    "total": len(steps),
                    "results": results,
                    "error": r.get("error"),
                }

        return {
            "success": True,
            "completed": len(steps),
            "total": len(steps),
            "results": results,
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_dom():
    return MockDOM()


@pytest.fixture
def gmail_dom():
    """Gmail compose DOM with standard elements."""
    dom = MockDOM()
    dom.add("div[aria-label='Compose']", MockDOMElement(
        tag="div", role="button", aria_label="Compose", text="Compose",
        visible=True, data_testid="compose-button",
    ))
    dom.add("textarea[aria-label='To']", MockDOMElement(
        tag="textarea", aria_label="To", visible=True, editable=True,
        name="to", placeholder="Recipients",
    ))
    dom.add("input[aria-label='Subject']", MockDOMElement(
        tag="input", aria_label="Subject", visible=True, editable=True,
        name="subject", placeholder="Subject",
    ))
    msg_body = MockDOMElement(
        tag="div", role="textbox", aria_label="Message body",
        visible=True, editable=True, elem_id="message-body",
    )
    dom.add("div[aria-label='Message body']", msg_body)
    dom.add("#message-body", msg_body)
    dom.add("[aria-label='Send']", MockDOMElement(
        tag="button", role="button", aria_label="Send", text="Send",
        visible=True, data_testid="send-button",
    ))
    dom.add("[aria-label='Discard draft']", MockDOMElement(
        tag="button", role="button", aria_label="Discard draft", text="Discard",
        visible=True,
    ))
    dom.add("input[aria-label='Cc']", MockDOMElement(
        tag="input", aria_label="Cc", visible=False, editable=True, name="cc",
    ))
    dom.add("input[aria-label='Bcc']", MockDOMElement(
        tag="input", aria_label="Bcc", visible=False, editable=True, name="bcc",
    ))
    return dom


@pytest.fixture
def reddit_dom():
    """Reddit post creation DOM."""
    dom = MockDOM()
    dom.add("#title-input", MockDOMElement(
        tag="input", elem_id="title-input", visible=True, editable=True,
        placeholder="Title", data_testid="post-title",
    ))
    dom.add("div[role='textbox']", MockDOMElement(
        tag="div", role="textbox", visible=True, editable=True,
        aria_label="Post body", data_testid="post-body",
    ))
    dom.add("button[data-testid='submit-post']", MockDOMElement(
        tag="button", role="button", text="Post", visible=True,
        data_testid="submit-post",
    ))
    dom.add("select[name='flair']", MockDOMElement(
        tag="select", name="flair", visible=True, data_testid="flair-select",
    ))
    dom.add("button[aria-label='Add image']", MockDOMElement(
        tag="button", role="button", aria_label="Add image", visible=True,
    ))
    return dom


@pytest.fixture
def github_dom():
    """GitHub issue creation DOM."""
    dom = MockDOM()
    dom.add("#issue_title", MockDOMElement(
        tag="input", elem_id="issue_title", visible=True, editable=True,
        name="issue[title]", placeholder="Title",
    ))
    dom.add("#issue_body", MockDOMElement(
        tag="textarea", elem_id="issue_body", visible=True, editable=True,
        name="issue[body]", placeholder="Leave a comment",
    ))
    dom.add("button[data-testid='submit-issue']", MockDOMElement(
        tag="button", text="Submit new issue", visible=True,
        data_testid="submit-issue",
    ))
    return dom


@pytest.fixture
def api_gmail(gmail_dom):
    return AutomationAPI(gmail_dom)


@pytest.fixture
def api_reddit(reddit_dom):
    return AutomationAPI(reddit_dom)


@pytest.fixture
def api_github(github_dom):
    return AutomationAPI(github_dom)


@pytest.fixture
def api_empty(empty_dom):
    return AutomationAPI(empty_dom)


# ============================================================================
# TIER 1: OAuth Foundation (25 tests)
# ============================================================================

class TestOAuthCare:
    """Care (39) -- 10 basic sanity tests for AutomationAPI surface."""

    def test_care_001_fill_field_returns_dict(self, api_gmail):
        """fill_field returns a dict with success key."""
        result = api_gmail.fill_field({"aria_label": "To"}, "test@example.com")
        assert isinstance(result, dict)
        assert "success" in result

    def test_care_002_click_button_returns_dict(self, api_gmail):
        """click_button returns a dict with success key."""
        result = api_gmail.click_button({"aria_label": "Compose"})
        assert isinstance(result, dict)
        assert "success" in result

    def test_care_003_select_option_returns_dict(self, api_reddit):
        """select_option returns a dict with success key."""
        result = api_reddit.select_option({"name": "flair"}, "Discussion")
        assert isinstance(result, dict)
        assert "success" in result

    def test_care_004_type_text_returns_dict(self, api_gmail):
        """type_text returns a dict with success key."""
        result = api_gmail.type_text({"aria_label": "Subject"}, "Hello")
        assert isinstance(result, dict)
        assert "success" in result

    def test_care_005_verify_interaction_returns_dict(self, api_gmail):
        """verify_interaction returns a dict with success key."""
        result = api_gmail.verify_interaction({"aria_label": "To"})
        assert isinstance(result, dict)
        assert "success" in result

    def test_care_006_resolve_element_by_aria_label(self, api_gmail):
        """resolve_element finds element by aria_label."""
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem is not None
        assert elem.tag == "INPUT"

    def test_care_007_resolve_element_by_data_testid(self, api_reddit):
        """resolve_element finds element by data-testid."""
        elem = api_reddit.resolve_element({"data_testid": "post-title"})
        assert elem is not None
        assert elem.tag == "INPUT"

    def test_care_008_resolve_element_by_name(self, api_github):
        """resolve_element finds element by name attribute."""
        elem = api_github.resolve_element({"name": "issue[title]"})
        assert elem is not None
        assert elem.tag == "INPUT"

    def test_care_009_interactions_logged(self, api_gmail):
        """Interactions are recorded in the interactions list."""
        assert len(api_gmail.interactions) == 0
        api_gmail.fill_field({"aria_label": "To"}, "test@test.com")
        assert len(api_gmail.interactions) == 1
        assert api_gmail.interactions[0]["type"] == "fill"

    def test_care_010_fill_sets_value(self, api_gmail):
        """fill_field actually sets the element value."""
        api_gmail.fill_field({"aria_label": "Subject"}, "Test Subject")
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == "Test Subject"


class TestOAuthBridge:
    """Bridge (63) -- 8 connector tests for selector priority resolution."""

    def test_bridge_001_data_testid_highest_priority(self, api_reddit):
        """data-testid is tried before other selectors."""
        elem = api_reddit.resolve_element({"data_testid": "post-title", "css_selector": "WRONG"})
        assert elem is not None
        assert elem.placeholder == "Title"

    def test_bridge_002_id_selector_resolution(self, api_github):
        """id-based resolution works via #id CSS mapping."""
        elem = api_github.resolve_element({"id": "issue_title"})
        assert elem is not None

    def test_bridge_003_name_attr_resolution(self, api_reddit):
        """name attribute resolution works."""
        elem = api_reddit.resolve_element({"name": "flair"})
        assert elem is not None
        assert elem.tag == "SELECT"

    def test_bridge_004_role_text_resolution(self, api_reddit):
        """role + text resolution works."""
        elem = api_reddit.resolve_element({"role": "button", "text": "Post"})
        assert elem is not None

    def test_bridge_005_placeholder_resolution(self, api_reddit):
        """placeholder resolution works."""
        elem = api_reddit.resolve_element({"placeholder": "Title"})
        assert elem is not None

    def test_bridge_006_css_selector_fallback(self, api_gmail):
        """css_selector is used as fallback when higher-priority selectors miss."""
        elem = api_gmail.resolve_element({"css_selector": "[aria-label='Send']"})
        assert elem is not None
        assert elem.text == "Send"

    def test_bridge_007_priority_order_respected(self, api_reddit):
        """Higher-priority selector wins when multiple match."""
        # data_testid should be tried first
        dom = MockDOM()
        dom.add("[data-testid='btn']", MockDOMElement(
            tag="button", data_testid="btn", text="Button A", visible=True,
        ))
        dom.add("button.fallback", MockDOMElement(
            tag="button", text="Button B", visible=True,
        ))
        api = AutomationAPI(dom)
        elem = api.resolve_element({"data_testid": "btn", "css_selector": "button.fallback"})
        assert elem.text == "Button A"

    def test_bridge_008_none_ref_returns_none(self, api_gmail):
        """Completely empty ref returns None."""
        elem = api_gmail.resolve_element({})
        assert elem is None


class TestOAuthStability:
    """Stability (91) -- 7 stability tests."""

    def test_stab_001_same_fill_twice_idempotent(self, api_gmail):
        """Filling the same field twice with same value is stable."""
        r1 = api_gmail.fill_field({"aria_label": "Subject"}, "Hello")
        r2 = api_gmail.fill_field({"aria_label": "Subject"}, "Hello")
        assert r1["success"] and r2["success"]
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == "Hello"

    def test_stab_002_fill_then_verify(self, api_gmail):
        """fill_field value survives verification check."""
        api_gmail.fill_field({"aria_label": "To"}, "a@b.com")
        v = api_gmail.verify_interaction({"aria_label": "To"}, expected_value="a@b.com")
        assert v["success"]
        assert v["value_match"]

    def test_stab_003_click_does_not_change_value(self, api_gmail):
        """Clicking a button doesn't alter form field values."""
        api_gmail.fill_field({"aria_label": "Subject"}, "Keep Me")
        api_gmail.click_button({"aria_label": "Send"})
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == "Keep Me"

    def test_stab_004_type_with_clear_first_replaces(self, api_gmail):
        """type_text with clear_first=True replaces existing value."""
        api_gmail.fill_field({"aria_label": "Subject"}, "Old")
        api_gmail.type_text({"aria_label": "Subject"}, "New", clear_first=True)
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == "New"

    def test_stab_005_type_without_clear_appends(self, api_gmail):
        """type_text with clear_first=False appends to existing value."""
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        elem.value = "Hello "
        api_gmail.type_text({"aria_label": "Subject"}, "World", clear_first=False)
        assert elem.value == "Hello World"

    def test_stab_006_interaction_log_order_preserved(self, api_gmail):
        """Interactions are logged in execution order."""
        api_gmail.fill_field({"aria_label": "To"}, "a@b.com")
        api_gmail.fill_field({"aria_label": "Subject"}, "Hi")
        api_gmail.click_button({"aria_label": "Send"})
        types = [i["type"] for i in api_gmail.interactions]
        assert types == ["fill", "fill", "click"]

    def test_stab_007_workflow_preserves_execution_order(self, api_gmail):
        """execute_workflow runs steps in order."""
        result = api_gmail.execute_workflow([
            {"action": "fill", "ref": {"aria_label": "To"}, "value": "x@y.com"},
            {"action": "fill", "ref": {"aria_label": "Subject"}, "value": "Hi"},
            {"action": "click", "ref": {"aria_label": "Send"}},
        ])
        assert result["success"]
        assert result["completed"] == 3


# ============================================================================
# TIER 2: 641 Edge Testing (21 tests)
# ============================================================================

class TestEdgeMissingElements:
    """Edge tests for missing/not-found elements."""

    def test_edge_001_fill_missing_element(self, api_gmail):
        """fill_field on non-existent element returns error."""
        r = api_gmail.fill_field({"aria_label": "NonExistent"}, "text")
        assert not r["success"]
        assert "not found" in r["error"].lower()

    def test_edge_002_click_missing_element(self, api_gmail):
        """click_button on non-existent element returns error."""
        r = api_gmail.click_button({"data_testid": "no-such-button"})
        assert not r["success"]
        assert "not found" in r["error"].lower()

    def test_edge_003_type_missing_element(self, api_gmail):
        """type_text on non-existent element returns error."""
        r = api_gmail.type_text({"css_selector": "input.ghost"}, "text")
        assert not r["success"]

    def test_edge_004_select_missing_element(self, api_reddit):
        """select_option on non-existent element returns error."""
        r = api_reddit.select_option({"name": "no-select"}, "val")
        assert not r["success"]

    def test_edge_005_verify_missing_element(self, api_gmail):
        """verify_interaction on non-existent element returns error."""
        r = api_gmail.verify_interaction({"id": "phantom"}, expected_value="x")
        assert not r["success"]


class TestEdgeHiddenElements:
    """Edge tests for hidden/invisible elements."""

    def test_edge_006_fill_hidden_field(self, api_gmail):
        """fill_field on hidden Cc field fails with visibility error."""
        r = api_gmail.fill_field({"aria_label": "Cc"}, "cc@example.com")
        assert not r["success"]
        assert "not visible" in r["error"].lower()

    def test_edge_007_click_hidden_element(self, api_gmail):
        """click_button on hidden element fails."""
        r = api_gmail.click_button({"aria_label": "Bcc"})
        assert not r["success"]

    def test_edge_008_type_hidden_element(self, api_gmail):
        """type_text on hidden element fails."""
        r = api_gmail.type_text({"name": "cc"}, "text")
        assert not r["success"]


class TestEdgeSpecialChars:
    """Edge tests for special characters and Unicode."""

    def test_edge_009_fill_with_special_chars(self, api_gmail):
        """fill_field handles !@#$%^&*() characters."""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        r = api_gmail.fill_field({"aria_label": "Subject"}, special)
        assert r["success"]
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == special

    def test_edge_010_fill_with_unicode(self, api_gmail):
        """fill_field handles Unicode characters."""
        unicode_text = "cafe\u0301 \u00e9l\u00e8ve \u4e16\u754c"
        r = api_gmail.fill_field({"aria_label": "Subject"}, unicode_text)
        assert r["success"]
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == unicode_text

    def test_edge_011_fill_with_emoji(self, api_gmail):
        """fill_field handles emoji characters."""
        emoji = "Hello \U0001f600 World \U0001f30d"
        r = api_gmail.fill_field({"aria_label": "Subject"}, emoji)
        assert r["success"]
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == emoji

    def test_edge_012_fill_with_newlines(self, api_gmail):
        """fill_field handles multi-line text."""
        multiline = "Line 1\nLine 2\nLine 3"
        r = api_gmail.fill_field({"aria_label": "Subject"}, multiline)
        assert r["success"]

    def test_edge_013_fill_empty_string(self, api_gmail):
        """fill_field with empty string clears field."""
        api_gmail.fill_field({"aria_label": "Subject"}, "Old Value")
        r = api_gmail.fill_field({"aria_label": "Subject"}, "")
        assert r["success"]
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == ""


class TestEdgeNonEditableElements:
    """Edge tests for non-editable elements."""

    def test_edge_014_fill_non_editable_div(self):
        """fill_field on non-editable div fails."""
        dom = MockDOM()
        dom.add("div.static", MockDOMElement(
            tag="div", visible=True, editable=False, aria_label="Static",
        ))
        api = AutomationAPI(dom)
        r = api.fill_field({"aria_label": "Static"}, "text")
        assert not r["success"]
        assert "not editable" in r["error"].lower()

    def test_edge_015_select_on_non_select_element(self, api_gmail):
        """select_option on INPUT element fails."""
        r = api_gmail.select_option({"aria_label": "Subject"}, "val")
        assert not r["success"]
        assert "not a select" in r["error"].lower()


class TestEdgeErrorCases:
    """Edge tests for error handling and recovery."""

    def test_edge_016_workflow_stops_on_failure(self, api_gmail):
        """Workflow stops at first failed step."""
        result = api_gmail.execute_workflow([
            {"action": "fill", "ref": {"aria_label": "To"}, "value": "a@b.com"},
            {"action": "click", "ref": {"aria_label": "NonExistent"}},
            {"action": "fill", "ref": {"aria_label": "Subject"}, "value": "Hi"},
        ])
        assert not result["success"]
        assert result["completed"] == 1  # Only first step completed

    def test_edge_017_verify_value_mismatch(self, api_gmail):
        """verify_interaction detects value mismatch."""
        api_gmail.fill_field({"aria_label": "Subject"}, "Actual")
        r = api_gmail.verify_interaction({"aria_label": "Subject"}, expected_value="Expected")
        assert not r["success"]
        assert not r["value_match"]

    def test_edge_018_fill_returns_ref_on_error(self, api_gmail):
        """Error responses include the ref that failed."""
        r = api_gmail.fill_field({"aria_label": "Ghost"}, "text")
        assert not r["success"]
        assert "ref" in r

    def test_edge_019_multiple_resolution_fallback(self):
        """Resolution falls through multiple strategies until one works."""
        dom = MockDOM()
        # Only reachable via css_selector (no testid, id, aria, name, role, placeholder)
        dom.add("button.special", MockDOMElement(
            tag="button", text="Special", visible=True,
        ))
        api = AutomationAPI(dom)
        elem = api.resolve_element({
            "data_testid": "wrong",
            "id": "wrong",
            "aria_label": "wrong",
            "name": "wrong",
            "css_selector": "button.special",
        })
        assert elem is not None
        assert elem.text == "Special"

    def test_edge_020_empty_value_fill(self, api_gmail):
        """Filling with empty string should succeed and clear field."""
        r = api_gmail.fill_field({"aria_label": "To"}, "")
        assert r["success"]
        assert r["typed"] == 0

    def test_edge_021_unknown_workflow_action(self, api_gmail):
        """Unknown workflow action returns error."""
        result = api_gmail.execute_workflow([
            {"action": "unknown_action", "ref": {"aria_label": "To"}},
        ])
        assert not result["success"]
        assert "Unknown action" in result["error"]


# ============================================================================
# TIER 3: 274177 Stress Testing (18 tests)
# ============================================================================

class TestStressFieldFills:
    """Stress tests for high-volume field fills."""

    def test_stress_001_fill_100_fields(self):
        """Fill 100 different fields without error."""
        dom = MockDOM()
        for i in range(100):
            dom.add(f"input.field-{i}", MockDOMElement(
                tag="input", elem_id=f"field-{i}", visible=True, editable=True,
                aria_label=f"Field {i}",
            ))
        api = AutomationAPI(dom)

        for i in range(100):
            r = api.fill_field({"aria_label": f"Field {i}"}, f"value-{i}")
            assert r["success"], f"Failed on field {i}: {r}"

        assert len(api.interactions) == 100

    def test_stress_002_fill_50_clicks(self):
        """Click 50 different buttons without error."""
        dom = MockDOM()
        for i in range(50):
            dom.add(f"button.btn-{i}", MockDOMElement(
                tag="button", data_testid=f"btn-{i}", text=f"Button {i}", visible=True,
            ))
        api = AutomationAPI(dom)

        for i in range(50):
            r = api.click_button({"data_testid": f"btn-{i}"})
            assert r["success"], f"Failed on button {i}: {r}"

        assert len(api.interactions) == 50


class TestStressLongText:
    """Stress tests for long text input."""

    def test_stress_003_fill_10k_chars(self, api_gmail):
        """Fill field with 10,000 character string."""
        long_text = "A" * 10000
        r = api_gmail.fill_field({"aria_label": "Subject"}, long_text)
        assert r["success"]
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert len(elem.value) == 10000

    def test_stress_004_fill_100k_chars(self, api_gmail):
        """Fill field with 100,000 character string."""
        long_text = "B" * 100000
        r = api_gmail.fill_field({"aria_label": "Subject"}, long_text)
        assert r["success"]
        assert r["typed"] == 100000

    def test_stress_005_type_1k_chars_char_by_char(self, api_gmail):
        """type_text processes 1,000 characters."""
        text = "x" * 1000
        r = api_gmail.type_text({"aria_label": "Subject"}, text)
        assert r["success"]
        assert r["typed"] == 1000


class TestStressMultiField:
    """Stress tests for multi-field workflows."""

    def test_stress_006_gmail_compose_full_workflow(self, api_gmail):
        """Full Gmail compose: To + Subject + Body + Send."""
        result = api_gmail.execute_workflow([
            {"action": "click", "ref": {"aria_label": "Compose"}},
            {"action": "fill", "ref": {"aria_label": "To"}, "value": "alice@example.com"},
            {"action": "fill", "ref": {"aria_label": "Subject"}, "value": "Meeting Tomorrow"},
            {"action": "fill", "ref": {"id": "message-body"}, "value": "Hi Alice,\nSee you at 3pm."},
            {"action": "click", "ref": {"aria_label": "Send"}},
        ])
        assert result["success"]
        assert result["completed"] == 5

    def test_stress_007_reddit_post_workflow(self, api_reddit):
        """Full Reddit post: Title + Flair + Body + Submit."""
        result = api_reddit.execute_workflow([
            {"action": "fill", "ref": {"data_testid": "post-title"}, "value": "My Post Title"},
            {"action": "select", "ref": {"name": "flair"}, "value": "Discussion", "label": "Discussion"},
            {"action": "fill", "ref": {"data_testid": "post-body"}, "value": "Post content here."},
            {"action": "click", "ref": {"data_testid": "submit-post"}},
        ])
        assert result["success"]
        assert result["completed"] == 4

    def test_stress_008_github_issue_workflow(self, api_github):
        """Full GitHub issue: Title + Body + Submit."""
        result = api_github.execute_workflow([
            {"action": "fill", "ref": {"id": "issue_title"}, "value": "Bug: Widget broken"},
            {"action": "fill", "ref": {"id": "issue_body"}, "value": "Steps to reproduce:\n1. Open page\n2. Click widget"},
            {"action": "click", "ref": {"data_testid": "submit-issue"}},
        ])
        assert result["success"]
        assert result["completed"] == 3

    def test_stress_009_20_field_form(self):
        """Fill a 20-field form in sequence."""
        dom = MockDOM()
        for i in range(20):
            dom.add(f"input.f-{i}", MockDOMElement(
                tag="input", elem_id=f"f-{i}", visible=True, editable=True,
                name=f"field_{i}",
            ))
        api = AutomationAPI(dom)
        steps = [
            {"action": "fill", "ref": {"name": f"field_{i}"}, "value": f"val_{i}"}
            for i in range(20)
        ]
        result = api.execute_workflow(steps)
        assert result["success"]
        assert result["completed"] == 20

    def test_stress_010_interleaved_fill_and_verify(self, api_gmail):
        """Fill field then verify, 10 times in sequence."""
        for i in range(10):
            val = f"test-{i}@example.com"
            r = api_gmail.fill_field({"aria_label": "To"}, val)
            assert r["success"]
            v = api_gmail.verify_interaction({"aria_label": "To"}, expected_value=val)
            assert v["success"]
            assert v["value_match"]


class TestStressPerformance:
    """Stress tests for performance bounds."""

    def test_stress_011_100_fills_under_1s(self):
        """100 fill_field calls complete in under 1 second."""
        dom = MockDOM()
        for i in range(100):
            dom.add(f"input.p-{i}", MockDOMElement(
                tag="input", elem_id=f"p-{i}", visible=True, editable=True,
                data_testid=f"perf-{i}",
            ))
        api = AutomationAPI(dom)

        start = time.time()
        for i in range(100):
            api.fill_field({"data_testid": f"perf-{i}"}, f"val-{i}")
        elapsed = time.time() - start
        assert elapsed < 1.0, f"100 fills took {elapsed:.3f}s (limit: 1.0s)"

    def test_stress_012_100_clicks_under_1s(self):
        """100 click_button calls complete in under 1 second."""
        dom = MockDOM()
        for i in range(100):
            dom.add(f"button.c-{i}", MockDOMElement(
                tag="button", data_testid=f"click-{i}", text=f"Btn {i}", visible=True,
            ))
        api = AutomationAPI(dom)

        start = time.time()
        for i in range(100):
            api.click_button({"data_testid": f"click-{i}"})
        elapsed = time.time() - start
        assert elapsed < 1.0, f"100 clicks took {elapsed:.3f}s (limit: 1.0s)"

    def test_stress_013_workflow_50_steps_under_1s(self):
        """50-step workflow completes in under 1 second."""
        dom = MockDOM()
        for i in range(50):
            dom.add(f"input.w-{i}", MockDOMElement(
                tag="input", elem_id=f"w-{i}", visible=True, editable=True,
                name=f"wf_{i}",
            ))
        api = AutomationAPI(dom)
        steps = [{"action": "fill", "ref": {"name": f"wf_{i}"}, "value": f"v{i}"} for i in range(50)]

        start = time.time()
        result = api.execute_workflow(steps)
        elapsed = time.time() - start
        assert result["success"]
        assert elapsed < 1.0, f"50-step workflow took {elapsed:.3f}s"

    def test_stress_014_selector_resolution_1000_elements(self):
        """Selector resolution in DOM with 1000 elements completes quickly."""
        dom = MockDOM()
        for i in range(1000):
            dom.add(f"div.el-{i}", MockDOMElement(
                tag="div", elem_id=f"el-{i}", visible=True,
                data_testid=f"tid-{i}",
            ))
        api = AutomationAPI(dom)

        start = time.time()
        # Resolve last element (worst case)
        elem = api.resolve_element({"data_testid": "tid-999"})
        elapsed = time.time() - start
        assert elem is not None
        assert elapsed < 0.1, f"Resolution took {elapsed:.3f}s"

    def test_stress_015_repeated_fill_same_field_100x(self, api_gmail):
        """Fill the same field 100 times to check for drift."""
        for i in range(100):
            r = api_gmail.fill_field({"aria_label": "Subject"}, f"Iteration {i}")
            assert r["success"]
        elem = api_gmail.resolve_element({"aria_label": "Subject"})
        assert elem.value == "Iteration 99"

    def test_stress_016_verify_100_times_deterministic(self, api_gmail):
        """verify_interaction returns same result 100 times."""
        api_gmail.fill_field({"aria_label": "To"}, "fixed@val.com")
        results = set()
        for _ in range(100):
            v = api_gmail.verify_interaction({"aria_label": "To"}, expected_value="fixed@val.com")
            results.add(v["success"])
        assert results == {True}

    def test_stress_017_mixed_operations_100(self):
        """100 mixed operations (fill, click, verify) complete."""
        dom = MockDOM()
        for i in range(50):
            dom.add(f"input.m-{i}", MockDOMElement(
                tag="input", elem_id=f"m-{i}", visible=True, editable=True,
                data_testid=f"mix-{i}",
            ))
        for i in range(50):
            dom.add(f"button.b-{i}", MockDOMElement(
                tag="button", data_testid=f"mixbtn-{i}", text=f"B{i}", visible=True,
            ))
        api = AutomationAPI(dom)

        count = 0
        for i in range(50):
            r1 = api.fill_field({"data_testid": f"mix-{i}"}, f"v{i}")
            assert r1["success"]
            count += 1
            r2 = api.click_button({"data_testid": f"mixbtn-{i}"})
            assert r2["success"]
            count += 1
        assert count == 100

    def test_stress_018_large_workflow_with_verification(self):
        """30-step workflow with interleaved verifications."""
        dom = MockDOM()
        for i in range(15):
            dom.add(f"input.lv-{i}", MockDOMElement(
                tag="input", elem_id=f"lv-{i}", visible=True, editable=True,
                name=f"lv_{i}",
            ))
        api = AutomationAPI(dom)

        steps = []
        for i in range(15):
            steps.append({"action": "fill", "ref": {"name": f"lv_{i}"}, "value": f"val_{i}"})
            steps.append({"action": "verify", "ref": {"name": f"lv_{i}"}, "expected_value": f"val_{i}"})

        result = api.execute_workflow(steps)
        assert result["success"]
        assert result["completed"] == 30


# ============================================================================
# TIER 4: 65537 God Testing (11 tests)
# ============================================================================

class TestGodFullWorkflows:
    """Full end-to-end workflow tests."""

    def test_god_001_gmail_full_compose_and_verify(self, api_gmail):
        """Full Gmail compose with verification of every field."""
        result = api_gmail.execute_workflow([
            {"action": "click", "ref": {"data_testid": "compose-button"}},
            {"action": "fill", "ref": {"aria_label": "To"}, "value": "bob@example.com"},
            {"action": "verify", "ref": {"aria_label": "To"}, "expected_value": "bob@example.com"},
            {"action": "fill", "ref": {"aria_label": "Subject"}, "value": "Quarterly Report"},
            {"action": "verify", "ref": {"aria_label": "Subject"}, "expected_value": "Quarterly Report"},
            {"action": "fill", "ref": {"id": "message-body"}, "value": "Please find attached."},
            {"action": "verify", "ref": {"id": "message-body"}, "expected_value": "Please find attached."},
            {"action": "click", "ref": {"data_testid": "send-button"}},
        ])
        assert result["success"]
        assert result["completed"] == 8

    def test_god_002_reddit_full_post_and_verify(self, api_reddit):
        """Full Reddit post with verification."""
        result = api_reddit.execute_workflow([
            {"action": "fill", "ref": {"data_testid": "post-title"}, "value": "TIL Something"},
            {"action": "verify", "ref": {"data_testid": "post-title"}, "expected_value": "TIL Something"},
            {"action": "select", "ref": {"name": "flair"}, "value": "TIL", "label": "Today I Learned"},
            {"action": "fill", "ref": {"data_testid": "post-body"}, "value": "I learned that..."},
            {"action": "verify", "ref": {"data_testid": "post-body"}, "expected_value": "I learned that..."},
            {"action": "click", "ref": {"data_testid": "submit-post"}},
        ])
        assert result["success"]
        assert result["completed"] == 6

    def test_god_003_github_issue_full_and_verify(self, api_github):
        """Full GitHub issue creation with verification."""
        result = api_github.execute_workflow([
            {"action": "fill", "ref": {"id": "issue_title"}, "value": "Feature: Dark mode"},
            {"action": "verify", "ref": {"id": "issue_title"}, "expected_value": "Feature: Dark mode"},
            {"action": "fill", "ref": {"id": "issue_body"}, "value": "Please add dark mode support."},
            {"action": "verify", "ref": {"id": "issue_body"}, "expected_value": "Please add dark mode support."},
            {"action": "click", "ref": {"data_testid": "submit-issue"}},
        ])
        assert result["success"]
        assert result["completed"] == 5


class TestGodErrorRecovery:
    """Error recovery and edge-case handling at scale."""

    def test_god_004_workflow_failure_point_reported(self, api_gmail):
        """Failed workflow reports exact step index."""
        result = api_gmail.execute_workflow([
            {"action": "fill", "ref": {"aria_label": "To"}, "value": "a@b.com"},
            {"action": "fill", "ref": {"aria_label": "Subject"}, "value": "Hi"},
            {"action": "click", "ref": {"aria_label": "NONEXISTENT"}},
            {"action": "click", "ref": {"aria_label": "Send"}},
        ])
        assert not result["success"]
        assert result["completed"] == 2  # Steps 0 and 1 succeeded
        assert len(result["results"]) == 3  # 3 steps attempted (0, 1, 2)

    def test_god_005_interaction_log_complete(self, api_gmail):
        """Interaction log captures all successful operations."""
        api_gmail.fill_field({"aria_label": "To"}, "a@b.com")
        api_gmail.fill_field({"aria_label": "Subject"}, "Test")
        api_gmail.click_button({"aria_label": "Compose"})
        api_gmail.click_button({"aria_label": "Send"})

        assert len(api_gmail.interactions) == 4
        types = [i["type"] for i in api_gmail.interactions]
        assert types == ["fill", "fill", "click", "click"]

        # Verify timestamps are ordered
        timestamps = [i["timestamp"] for i in api_gmail.interactions]
        assert timestamps == sorted(timestamps)

    def test_god_006_cross_platform_selector_consistency(self, api_gmail, api_reddit, api_github):
        """Same selector strategy works across Gmail, Reddit, GitHub."""
        # All platforms should support data_testid resolution
        g = api_gmail.resolve_element({"data_testid": "compose-button"})
        r = api_reddit.resolve_element({"data_testid": "post-title"})
        h = api_github.resolve_element({"data_testid": "submit-issue"})
        assert g is not None
        assert r is not None
        assert h is not None

    def test_god_007_fill_verify_roundtrip_deterministic(self, api_gmail):
        """fill -> verify roundtrip is deterministic across 50 iterations."""
        for i in range(50):
            value = f"deterministic-{i}@test.com"
            api_gmail.fill_field({"aria_label": "To"}, value)
            v = api_gmail.verify_interaction({"aria_label": "To"}, expected_value=value)
            assert v["success"], f"Failed at iteration {i}"
            assert v["value_match"], f"Value mismatch at iteration {i}"


class TestGodSchemaCompliance:
    """Schema and contract compliance tests."""

    def test_god_008_fill_response_schema(self, api_gmail):
        """fill_field success response has all required fields."""
        r = api_gmail.fill_field({"aria_label": "To"}, "test@test.com")
        assert r["success"] is True
        assert "typed" in r
        assert "element" in r
        assert "verified" in r
        assert isinstance(r["typed"], int)
        assert isinstance(r["element"], dict)

    def test_god_009_click_response_schema(self, api_gmail):
        """click_button success response has all required fields."""
        r = api_gmail.click_button({"aria_label": "Compose"})
        assert r["success"] is True
        assert "clicked" in r
        assert r["clicked"] is True
        assert "element" in r
        assert isinstance(r["element"], dict)

    def test_god_010_error_response_schema(self, api_gmail):
        """Error response has consistent schema."""
        r = api_gmail.fill_field({"aria_label": "Ghost"}, "text")
        assert r["success"] is False
        assert "error" in r
        assert isinstance(r["error"], str)
        assert len(r["error"]) > 0

    def test_god_011_workflow_response_schema(self, api_gmail):
        """Workflow response has all required fields."""
        result = api_gmail.execute_workflow([
            {"action": "fill", "ref": {"aria_label": "To"}, "value": "a@b.com"},
        ])
        assert "success" in result
        assert "completed" in result
        assert "total" in result
        assert "results" in result
        assert isinstance(result["results"], list)
        assert result["completed"] == result["total"]
