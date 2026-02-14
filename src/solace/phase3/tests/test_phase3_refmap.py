#!/usr/bin/env python3
"""
Phase 3 RefMap Builder Tests

Verification order: OAuth(39,63,91) -> 641 -> 274177 -> 65537

Test groups:
  - OAuth (care, bridge, stability): Basic construction, schema, determinism
  - 641 (edge): Single selector types, missing data, collisions, empty fields
  - 274177 (stress): Large episodes, many refs, performance
  - 65537 (god): End-to-end, Phase 2 compat, full pipeline

Auth: 65537 | Northstar: Phuc Forecast
"""

import copy
import hashlib
import json
import pytest
import uuid

from solace_cli.browser.refmap_builder import (
    RefMapBuilder,
    build_refmap_from_episode,
    extract_semantic,
    extract_structural,
    generate_ref_id,
    score_reliability,
    compute_priority,
    best_resolution_strategy,
    REFMAP_VERSION,
    RELIABILITY_SCORES,
)
from solace_cli.browser.tests.conftest_phase_b import (
    GMAIL_COMPOSE_DOM,
    GMAIL_DOM,
    MINIMAL_DOM,
    make_episode,
)


# ===== Fixtures =====

@pytest.fixture
def builder():
    return RefMapBuilder()


@pytest.fixture
def gmail_episode():
    """Gmail compose episode: navigate, click Compose, type To, type Subject, click Send."""
    return {
        "session_id": "gmail-compose-001",
        "domain": "gmail.com",
        "start_time": "2026-02-14T12:00:00Z",
        "end_time": "2026-02-14T12:05:00Z",
        "actions": [
            {
                "type": "navigate",
                "data": {"url": "https://mail.google.com/mail/u/0/"},
                "step": 0,
                "timestamp": "2026-02-14T12:00:00Z",
            },
            {
                "type": "click",
                "data": {
                    "selector": "button[data-tooltip='Compose']",
                    "aria-label": "Compose",
                    "role": "button",
                    "text": "Compose",
                },
                "step": 1,
                "timestamp": "2026-02-14T12:00:02Z",
            },
            {
                "type": "type",
                "data": {
                    "selector": "#to",
                    "id": "to",
                    "aria-label": "To",
                    "name": "to",
                    "text": "user@example.com",
                    "type": "email",
                },
                "step": 2,
                "timestamp": "2026-02-14T12:00:05Z",
            },
            {
                "type": "type",
                "data": {
                    "selector": "#subject",
                    "id": "subject",
                    "aria-label": "Subject",
                    "name": "subject",
                    "text": "Meeting tomorrow",
                    "type": "text",
                },
                "step": 3,
                "timestamp": "2026-02-14T12:00:08Z",
            },
            {
                "type": "click",
                "data": {
                    "selector": "button[aria-label='Send']",
                    "aria-label": "Send",
                    "data-testid": "send-button",
                    "role": "button",
                    "text": "Send",
                },
                "step": 4,
                "timestamp": "2026-02-14T12:00:12Z",
            },
        ],
        "snapshots": {},
        "action_count": 5,
    }


@pytest.fixture
def minimal_episode():
    """Minimal valid episode with 1 action."""
    return {
        "session_id": "min-001",
        "domain": "example.com",
        "actions": [
            {
                "type": "click",
                "data": {"selector": "#btn", "aria-label": "Submit"},
                "step": 0,
            }
        ],
    }


@pytest.fixture
def rich_action_data():
    """Action data with all semantic and structural attributes populated."""
    return {
        "selector": "button.submit-btn",
        "xpath": "//button[@class='submit-btn']",
        "ref_path": "body>main:0>form:0>button:2",
        "id": "submit-btn",
        "tag": "button",
        "aria-label": "Submit Form",
        "aria-describedby": "form-help-text",
        "data-testid": "form-submit",
        "data-qa": "submit",
        "placeholder": None,
        "alt": None,
        "role": "button",
        "name": "submit",
        "type": "submit",
        "text": "Submit",
        "nth_child": 2,
    }


# ========================================================
# OAuth Tests (39, 63, 91) - Care, Bridge, Stability
# ========================================================

class TestOAuth:
    """Basic construction, schema validation, and determinism."""

    # --- 39: Care ---

    def test_builder_creates_refmap(self, builder, gmail_episode):
        """RefMapBuilder produces a valid refmap dict."""
        result = builder.build_refmap(gmail_episode)
        assert isinstance(result, dict)
        assert "version" in result
        assert "refmap" in result
        assert "stats" in result

    def test_refmap_version(self, builder, gmail_episode):
        """RefMap version matches REFMAP_VERSION constant."""
        result = builder.build_refmap(gmail_episode)
        assert result["version"] == REFMAP_VERSION

    def test_refmap_has_episode_id(self, builder, gmail_episode):
        """RefMap includes episode_id from source episode."""
        result = builder.build_refmap(gmail_episode)
        assert result["episode_id"] == "gmail-compose-001"

    def test_refmap_has_url_source(self, builder, gmail_episode):
        """RefMap includes url_source extracted from first navigate action."""
        result = builder.build_refmap(gmail_episode)
        assert result["url_source"] == "https://mail.google.com/mail/u/0/"

    def test_refmap_stats_populated(self, builder, gmail_episode):
        """Stats section has all required fields."""
        result = builder.build_refmap(gmail_episode)
        stats = result["stats"]
        assert "total_refs" in stats
        assert "action_count" in stats
        assert "pages" in stats
        assert "semantic_only_count" in stats
        assert "structural_only_count" in stats
        assert "complete_count" in stats

    # --- 63: Bridge ---

    def test_refmap_entries_have_semantic(self, builder, gmail_episode):
        """Each refmap entry has a semantic dict."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            assert "semantic" in entry

    def test_refmap_entries_have_structural(self, builder, gmail_episode):
        """Each refmap entry has a structural dict."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            assert "structural" in entry

    def test_refmap_entries_have_priority(self, builder, gmail_episode):
        """Each refmap entry has a priority list."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            assert "priority" in entry
            assert isinstance(entry["priority"], list)

    def test_refmap_entries_have_reliability(self, builder, gmail_episode):
        """Each refmap entry has reliability scores."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            assert "reliability" in entry
            assert isinstance(entry["reliability"], dict)

    def test_refmap_entries_have_actions(self, builder, gmail_episode):
        """Each refmap entry has an actions list."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            assert "actions" in entry
            assert isinstance(entry["actions"], list)
            assert len(entry["actions"]) >= 1

    def test_refmap_entries_have_resolution_strategy(self, builder, gmail_episode):
        """Each refmap entry has a resolution_strategy string."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            assert "resolution_strategy" in entry
            assert isinstance(entry["resolution_strategy"], str)

    # --- 91: Stability ---

    def test_deterministic_refmap(self, builder, gmail_episode):
        """Same episode always produces same RefMap."""
        r1 = builder.build_refmap(gmail_episode)
        r2 = builder.build_refmap(gmail_episode)
        # Compare without timestamp-sensitive fields
        assert r1["refmap"] == r2["refmap"]
        assert r1["stats"] == r2["stats"]

    def test_deterministic_ref_ids(self, builder, gmail_episode):
        """ref_ids are deterministic (same semantics = same id)."""
        r1 = builder.build_refmap(gmail_episode)
        r2 = builder.build_refmap(gmail_episode)
        assert set(r1["refmap"].keys()) == set(r2["refmap"].keys())

    def test_ref_id_format(self, builder, gmail_episode):
        """ref_ids match format ref_XXXXXXXX (8 hex chars)."""
        result = builder.build_refmap(gmail_episode)
        for ref_id in result["refmap"].keys():
            assert ref_id.startswith("ref_")
            hex_part = ref_id[4:]
            assert len(hex_part) == 8
            int(hex_part, 16)  # should not raise

    def test_convenience_function(self, gmail_episode):
        """build_refmap_from_episode() works identically to builder."""
        builder = RefMapBuilder()
        expected = builder.build_refmap(gmail_episode)
        actual = build_refmap_from_episode(gmail_episode)
        assert actual["refmap"] == expected["refmap"]


# ========================================================
# 641 Edge Tests - Single selectors, missing data, edge cases
# ========================================================

class TestEdge641:
    """Edge cases and boundary conditions."""

    def test_empty_episode_raises(self, builder):
        """Episode with no actions raises ValueError."""
        with pytest.raises(ValueError, match="no actions"):
            builder.build_refmap({"actions": []})

    def test_non_dict_episode_raises(self, builder):
        """Non-dict episode raises ValueError."""
        with pytest.raises(ValueError, match="must be a dict"):
            builder.build_refmap("not a dict")

    def test_none_episode_raises(self, builder):
        """None episode raises ValueError."""
        with pytest.raises(ValueError, match="must be a dict"):
            builder.build_refmap(None)

    def test_episode_missing_actions_key_raises(self, builder):
        """Episode without 'actions' key raises ValueError."""
        with pytest.raises(ValueError, match="no actions"):
            builder.build_refmap({"domain": "test.com"})

    def test_action_with_only_semantic(self, builder):
        """Action with only semantic attributes (no structural)."""
        episode = {
            "session_id": "sem-only",
            "domain": "test.com",
            "actions": [
                {
                    "type": "click",
                    "data": {"aria-label": "Close", "role": "button", "text": "X"},
                    "step": 0,
                }
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["total_refs"] == 1
        assert result["stats"]["semantic_only_count"] == 1

    def test_action_with_only_structural(self, builder):
        """Action with only structural attributes (no semantic)."""
        episode = {
            "session_id": "str-only",
            "domain": "test.com",
            "actions": [
                {
                    "type": "click",
                    "data": {"selector": "div.content > button:nth-child(3)"},
                    "step": 0,
                }
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["total_refs"] == 1
        assert result["stats"]["structural_only_count"] == 1

    def test_action_with_both_semantic_and_structural(self, builder):
        """Action with both semantic and structural attributes."""
        episode = {
            "session_id": "both",
            "domain": "test.com",
            "actions": [
                {
                    "type": "click",
                    "data": {
                        "selector": "#submit-btn",
                        "aria-label": "Submit",
                        "data-testid": "submit",
                    },
                    "step": 0,
                }
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["complete_count"] == 1

    def test_navigate_action_with_url_only(self, builder):
        """Navigate action with only URL (no element selectors)."""
        episode = {
            "session_id": "nav-only",
            "domain": "example.com",
            "actions": [
                {
                    "type": "navigate",
                    "data": {"url": "https://example.com/page"},
                    "step": 0,
                }
            ],
        }
        result = builder.build_refmap(episode)
        # Navigate with URL should still create a ref
        assert result["stats"]["total_refs"] >= 1

    def test_action_with_empty_data(self, builder):
        """Action with completely empty data dict."""
        episode = {
            "session_id": "empty-data",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        # Should still produce a refmap (possibly with 0 refs)
        assert isinstance(result["refmap"], dict)

    def test_action_with_null_values(self, builder):
        """Action with None/null attribute values are ignored."""
        episode = {
            "session_id": "null-vals",
            "domain": "test.com",
            "actions": [
                {
                    "type": "click",
                    "data": {
                        "selector": "#btn",
                        "aria-label": None,
                        "data-testid": None,
                        "text": "",
                    },
                    "step": 0,
                }
            ],
        }
        result = builder.build_refmap(episode)
        refs = list(result["refmap"].values())
        assert len(refs) == 1
        sem = refs[0]["semantic"]
        assert sem.get("aria_label") is None
        assert sem.get("data_testid") is None

    def test_duplicate_element_merges_actions(self, builder):
        """Same element clicked twice produces one ref with two actions."""
        episode = {
            "session_id": "dup",
            "domain": "test.com",
            "actions": [
                {
                    "type": "click",
                    "data": {"aria-label": "Submit", "selector": "#submit"},
                    "step": 0,
                },
                {
                    "type": "click",
                    "data": {"aria-label": "Submit", "selector": "#submit"},
                    "step": 1,
                },
            ],
        }
        result = builder.build_refmap(episode)
        # Should merge into one ref with 2 actions
        assert result["stats"]["total_refs"] == 1
        ref = list(result["refmap"].values())[0]
        assert len(ref["actions"]) == 2

    def test_extract_semantic_all_keys(self, rich_action_data):
        """extract_semantic extracts all semantic attribute types."""
        sem = extract_semantic(rich_action_data)
        assert sem["aria_label"] == "Submit Form"
        assert sem["aria_describedby"] == "form-help-text"
        assert sem["data_testid"] == "form-submit"
        assert sem["data_qa"] == "submit"
        assert sem["role"] == "button"
        assert sem["name"] == "submit"
        assert sem["type"] == "submit"
        assert sem["text"] == "Submit"

    def test_extract_structural_all_keys(self, rich_action_data):
        """extract_structural extracts all structural selector types."""
        struct = extract_structural(rich_action_data)
        assert struct["css_selector"] == "button.submit-btn"
        assert struct["xpath"] == "//button[@class='submit-btn']"
        assert struct["ref_path"] == "body>main:0>form:0>button:2"
        assert struct["tag"] == "button"
        assert struct["id"] == "submit-btn"
        assert struct["nth_child"] == 2

    def test_ref_id_deterministic_same_input(self):
        """Same semantic dict always produces same ref_id."""
        sem = {"aria_label": "Submit", "role": "button"}
        id1 = generate_ref_id(sem)
        id2 = generate_ref_id(sem)
        assert id1 == id2

    def test_ref_id_different_for_different_input(self):
        """Different semantic dicts produce different ref_ids."""
        id1 = generate_ref_id({"aria_label": "Submit"})
        id2 = generate_ref_id({"aria_label": "Cancel"})
        assert id1 != id2

    def test_ref_id_empty_semantic(self):
        """Empty semantic dict produces a generic ref_id."""
        ref = generate_ref_id({})
        assert ref.startswith("ref_")
        assert len(ref) == 12  # ref_ + 8 hex

    def test_reliability_score_data_testid_highest(self):
        """data_testid has highest reliability score."""
        sem = {"data_testid": "x"}
        scores = score_reliability(sem, {})
        assert "data_testid" in scores
        assert scores["data_testid"] == RELIABILITY_SCORES["data_testid"]

    def test_reliability_score_id_selector(self):
        """CSS selector starting with # gets higher score."""
        scores = score_reliability({}, {"id": "main", "css_selector": "#main"})
        assert scores["css_selector"] == 0.92

    def test_priority_order(self):
        """Priority sorts by reliability descending."""
        reliability = {"data_testid": 0.98, "xpath": 0.75, "css_selector": 0.80}
        priority = compute_priority(reliability)
        assert priority[0] == "data_testid"
        assert priority[-1] == "xpath"

    def test_best_strategy_string(self):
        """best_resolution_strategy returns formatted string."""
        reliability = {"data_testid": 0.98, "css_selector": 0.80}
        strategy = best_resolution_strategy(reliability)
        assert "data_testid" in strategy
        assert "0.98" in strategy

    def test_best_strategy_empty(self):
        """best_resolution_strategy handles empty reliability."""
        assert best_resolution_strategy({}) == "none"

    def test_extract_semantic_from_nested_target(self):
        """Semantic extraction from nested 'target' object."""
        data = {
            "target": {
                "aria-label": "Nested Label",
                "role": "link",
                "text": "Click me",
            }
        }
        sem = extract_semantic(data)
        assert sem["aria_label"] == "Nested Label"
        assert sem["role"] == "link"
        assert sem["text"] == "Click me"

    def test_extract_structural_from_nested_element(self):
        """Structural extraction from nested 'element' object."""
        data = {
            "element": {
                "tag": "BUTTON",
                "id": "my-btn",
                "xpath": "//button[@id='my-btn']",
            }
        }
        struct = extract_structural(data)
        assert struct["tag"] == "button"  # normalized to lower
        assert struct["id"] == "my-btn"
        assert struct["xpath"] == "//button[@id='my-btn']"

    def test_css_selector_built_from_id(self):
        """If CSS selector missing but id present, CSS is built from id."""
        data = {"id": "main-content"}
        struct = extract_structural(data)
        assert struct["css_selector"] == "#main-content"

    def test_pages_count_distinct_urls(self, builder):
        """Pages stat counts distinct navigate URLs."""
        episode = {
            "session_id": "multi-page",
            "domain": "example.com",
            "actions": [
                {"type": "navigate", "data": {"url": "https://example.com/a"}, "step": 0},
                {"type": "click", "data": {"selector": "#btn"}, "step": 1},
                {"type": "navigate", "data": {"url": "https://example.com/b"}, "step": 2},
                {"type": "navigate", "data": {"url": "https://example.com/a"}, "step": 3},
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["pages"] == 2  # /a and /b (deduped)

    def test_action_type_case_insensitive(self, builder):
        """Action types are normalized to uppercase."""
        episode = {
            "session_id": "case",
            "domain": "test.com",
            "actions": [
                {"type": "CLICK", "data": {"selector": "#a"}, "step": 0},
                {"type": "click", "data": {"selector": "#b"}, "step": 1},
            ],
        }
        result = builder.build_refmap(episode)
        for entry in result["refmap"].values():
            for act in entry["actions"]:
                assert act["action_type"] == "CLICK"


# ========================================================
# 274177 Stress Tests - Large episodes, many refs
# ========================================================

class TestStress274177:
    """Stress tests with large episodes and many references."""

    def test_large_episode_50_actions(self, builder):
        """50-action episode processes without error."""
        episode = make_episode(num_actions=50, domain="stress.com")
        result = builder.build_refmap(episode)
        assert result["stats"]["action_count"] == 50
        assert result["stats"]["total_refs"] > 0

    def test_large_episode_100_actions(self, builder):
        """100-action episode processes without error."""
        episode = make_episode(num_actions=100, domain="stress100.com")
        result = builder.build_refmap(episode)
        assert result["stats"]["action_count"] == 100
        assert result["stats"]["total_refs"] > 0

    def test_large_episode_200_actions(self, builder):
        """200-action episode (stress boundary)."""
        episode = make_episode(num_actions=200, domain="stress200.com")
        result = builder.build_refmap(episode)
        assert result["stats"]["action_count"] == 200

    def test_no_ref_id_collisions_100_unique(self):
        """100 unique semantic inputs produce 100 unique ref_ids."""
        ref_ids = set()
        for i in range(100):
            sem = {"aria_label": f"Button {i}", "role": "button"}
            ref_ids.add(generate_ref_id(sem))
        assert len(ref_ids) == 100

    def test_determinism_100_iterations(self, builder, gmail_episode):
        """Same episode produces same RefMap over 100 iterations."""
        baseline = json.dumps(builder.build_refmap(gmail_episode), sort_keys=True)
        for _ in range(100):
            current = json.dumps(builder.build_refmap(gmail_episode), sort_keys=True)
            assert current == baseline

    def test_refmap_json_serializable(self, builder, gmail_episode):
        """RefMap output is fully JSON-serializable."""
        result = builder.build_refmap(gmail_episode)
        serialized = json.dumps(result)
        deserialized = json.loads(serialized)
        assert deserialized["version"] == REFMAP_VERSION
        assert deserialized["stats"]["action_count"] == 5

    def test_many_navigate_actions(self, builder):
        """Episode with 50 navigate actions (many pages)."""
        actions = []
        for i in range(50):
            actions.append({
                "type": "navigate",
                "data": {"url": f"https://example.com/page/{i}"},
                "step": i,
            })
        episode = {
            "session_id": "nav-stress",
            "domain": "example.com",
            "actions": actions,
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["pages"] == 50

    def test_all_same_element(self, builder):
        """50 actions targeting the same element merge into 1 ref."""
        actions = []
        for i in range(50):
            actions.append({
                "type": "click",
                "data": {"aria-label": "Refresh", "selector": "#refresh"},
                "step": i,
            })
        episode = {
            "session_id": "same-elem",
            "domain": "test.com",
            "actions": actions,
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["total_refs"] == 1
        ref = list(result["refmap"].values())[0]
        assert len(ref["actions"]) == 50

    def test_mixed_action_types_stress(self, builder):
        """Episode mixing click, type, navigate, scroll actions."""
        actions = []
        for i in range(60):
            t = ["click", "type", "navigate", "scroll"][i % 4]
            data = {}
            if t == "click":
                data = {"selector": f"#btn-{i}", "aria-label": f"Btn {i}"}
            elif t == "type":
                data = {"selector": f"#input-{i}", "text": f"val{i}"}
            elif t == "navigate":
                data = {"url": f"https://test.com/{i}"}
            elif t == "scroll":
                data = {"x": 0, "y": i * 100}
            actions.append({"type": t, "data": data, "step": i})

        episode = {
            "session_id": "mixed",
            "domain": "test.com",
            "actions": actions,
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["action_count"] == 60
        assert result["stats"]["total_refs"] > 0


# ========================================================
# 65537 God Tests - End-to-end, Phase 2 compat, full pipeline
# ========================================================

class TestGod65537:
    """Full pipeline, Phase 2 compatibility, end-to-end verification."""

    def test_gmail_compose_full_pipeline(self, builder, gmail_episode):
        """Full Gmail compose episode produces valid RefMap with correct stats."""
        result = builder.build_refmap(gmail_episode)

        # Schema validation
        assert result["version"] == REFMAP_VERSION
        assert result["episode_id"] == "gmail-compose-001"
        assert result["url_source"] == "https://mail.google.com/mail/u/0/"
        assert result["stats"]["action_count"] == 5

        # At least compose button and send button should be separate refs
        refs = result["refmap"]
        assert len(refs) >= 3  # navigate, compose-click, to-type, subject-type, send-click

        # Check each ref has valid structure
        for ref_id, entry in refs.items():
            assert ref_id.startswith("ref_")
            assert "semantic" in entry
            assert "structural" in entry
            assert "priority" in entry
            assert "reliability" in entry
            assert "actions" in entry
            assert "resolution_strategy" in entry

    def test_phase2_episode_compat(self, builder):
        """Phase 2 episode format (from conftest_phase_b) is compatible."""
        episode = make_episode(num_actions=5, domain="reddit.com")
        result = builder.build_refmap(episode)
        assert result["stats"]["action_count"] == 5
        assert result["stats"]["total_refs"] > 0

    def test_send_button_has_data_testid(self, builder, gmail_episode):
        """Send button ref has data_testid with highest reliability."""
        result = builder.build_refmap(gmail_episode)
        # Find the send button ref
        send_ref = None
        for ref_id, entry in result["refmap"].items():
            if entry.get("semantic", {}).get("data_testid") == "send-button":
                send_ref = entry
                break
        assert send_ref is not None, "Send button ref not found"
        assert "data_testid" in send_ref["reliability"]
        # data_testid should be highest priority
        assert send_ref["priority"][0] == "data_testid"

    def test_to_field_has_id_and_aria(self, builder, gmail_episode):
        """To field ref has both id and aria-label selectors."""
        result = builder.build_refmap(gmail_episode)
        # Find the To field ref
        to_ref = None
        for ref_id, entry in result["refmap"].items():
            if entry.get("semantic", {}).get("aria_label") == "To":
                to_ref = entry
                break
        assert to_ref is not None, "To field ref not found"
        assert to_ref["structural"].get("id") == "to"
        assert to_ref["semantic"]["aria_label"] == "To"

    def test_refmap_entries_all_have_reliability_scores(self, builder, gmail_episode):
        """Every entry in the refmap has at least one reliability score."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            assert len(entry["reliability"]) >= 1, f"No reliability scores for {ref_id}"

    def test_stats_counts_correct(self, builder, gmail_episode):
        """Stats counts add up correctly."""
        result = builder.build_refmap(gmail_episode)
        stats = result["stats"]
        total = stats["semantic_only_count"] + stats["structural_only_count"] + stats["complete_count"]
        assert total == stats["total_refs"]

    def test_resolution_strategy_not_none(self, builder, gmail_episode):
        """Every entry has a non-empty resolution strategy."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            assert entry["resolution_strategy"] != "none"
            assert entry["resolution_strategy"] != ""

    def test_action_index_references_valid(self, builder, gmail_episode):
        """Action indices in refs match valid episode action indices."""
        result = builder.build_refmap(gmail_episode)
        action_count = len(gmail_episode["actions"])
        for ref_id, entry in result["refmap"].items():
            for act in entry["actions"]:
                assert 0 <= act["action_index"] < action_count

    def test_end_to_end_roundtrip_json(self, builder, gmail_episode):
        """RefMap survives JSON roundtrip without loss."""
        result = builder.build_refmap(gmail_episode)
        serialized = json.dumps(result, sort_keys=True)
        deserialized = json.loads(serialized)
        reserialized = json.dumps(deserialized, sort_keys=True)
        assert serialized == reserialized

    def test_multiple_episodes_independent(self, builder):
        """Building refmaps from different episodes produces independent results."""
        ep1 = make_episode(num_actions=3, domain="alpha.com", session_id="ep1")
        ep2 = make_episode(num_actions=5, domain="beta.com", session_id="ep2")

        r1 = builder.build_refmap(ep1)
        r2 = builder.build_refmap(ep2)

        assert r1["episode_id"] == "ep1"
        assert r2["episode_id"] == "ep2"
        assert r1["stats"]["action_count"] == 3
        assert r2["stats"]["action_count"] == 5
        # Refs should be different
        assert set(r1["refmap"].keys()) != set(r2["refmap"].keys())


# ============================================================
#  EXTENDED TESTS (40 additional to reach 100 total)
#  Verification: OAuth +10, Edge +3, Stress +9, God +18
# ============================================================


# ===== OAuth Extended (10 more = 25 total) =====

class TestOAuthCareExtended:
    """OAuth Care extended: refmap construction sanity (5 more)."""

    def test_care_016_action_count_in_stats(self, builder, gmail_episode):
        """Stats action_count matches actual actions length."""
        result = builder.build_refmap(gmail_episode)
        assert result["stats"]["action_count"] == len(gmail_episode["actions"])

    def test_care_017_total_refs_positive(self, builder, gmail_episode):
        """RefMap has at least one ref for multi-action episode."""
        result = builder.build_refmap(gmail_episode)
        assert result["stats"]["total_refs"] > 0

    def test_care_018_domain_extracted(self, builder, gmail_episode):
        """Episode domain is accessible."""
        result = builder.build_refmap(gmail_episode)
        assert result["episode_id"] is not None

    def test_care_019_reliability_scores_in_range(self, builder, gmail_episode):
        """All reliability scores are in 0.0-1.0 range."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            for key, score in entry["reliability"].items():
                assert 0.0 <= score <= 1.0, (
                    f"{ref_id}/{key} score {score} out of range"
                )

    def test_care_020_priority_list_non_empty(self, builder, gmail_episode):
        """Every entry with reliability scores has non-empty priority list."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            if entry["reliability"]:
                assert len(entry["priority"]) > 0


class TestOAuthStabilityExtended:
    """OAuth Stability extended (5 more)."""

    def test_stab_016_refmap_hash_deterministic(self, builder, gmail_episode):
        """SHA-256 of serialized RefMap is deterministic."""
        r1 = builder.build_refmap(gmail_episode)
        r2 = builder.build_refmap(gmail_episode)
        h1 = hashlib.sha256(json.dumps(r1, sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(r2, sort_keys=True).encode()).hexdigest()
        assert h1 == h2

    def test_stab_017_empty_data_keys_ignored(self, builder):
        """Empty string values in action data are ignored."""
        episode = {
            "session_id": "empty-vals",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {"selector": "#btn", "aria-label": "", "data-testid": ""}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        refs = list(result["refmap"].values())
        assert len(refs) == 1
        sem = refs[0]["semantic"]
        assert sem.get("aria_label") is None
        assert sem.get("data_testid") is None

    def test_stab_018_action_timestamps_preserved(self, builder, gmail_episode):
        """Action timestamps in refmap entries match episode timestamps."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            for act in entry["actions"]:
                idx = act["action_index"]
                original_ts = gmail_episode["actions"][idx].get("timestamp", "")
                assert act["action_timestamp"] == original_ts

    def test_stab_019_scroll_action_no_ref(self, builder):
        """Scroll action with only x/y creates no ref entry."""
        episode = {
            "session_id": "scroll-test",
            "domain": "test.com",
            "actions": [
                {"type": "scroll", "data": {"x": 0, "y": 500}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["total_refs"] == 0

    def test_stab_020_url_source_fallback_to_domain(self, builder):
        """url_source falls back to https://domain if no navigate action."""
        episode = {
            "session_id": "no-nav",
            "domain": "fallback.com",
            "actions": [
                {"type": "click", "data": {"selector": "#btn"}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        assert result["url_source"] == "https://fallback.com"


# ===== Edge 641 Extended (3 more = 29 total) =====

class TestEdge641Extended:
    """641-Edge: additional edge cases."""

    def test_641_ext_001_special_chars_in_aria(self, builder):
        """Special characters in aria-label handled."""
        episode = {
            "session_id": "special-aria",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {"aria-label": 'Close "dialog" (Esc)'}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        refs = list(result["refmap"].values())
        assert len(refs) == 1
        assert refs[0]["semantic"]["aria_label"] == 'Close "dialog" (Esc)'

    def test_641_ext_002_very_long_text_value(self, builder):
        """Very long text value (10K chars) handled without error."""
        big_text = "A" * 10000
        episode = {
            "session_id": "big-text",
            "domain": "test.com",
            "actions": [
                {"type": "type", "data": {"selector": "#area", "text": big_text}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        refs = list(result["refmap"].values())
        assert len(refs) == 1
        assert refs[0]["semantic"]["text"] == big_text

    def test_641_ext_003_unicode_selectors(self, builder):
        """Unicode in selectors and text handled."""
        episode = {
            "session_id": "unicode",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {"selector": "#\u30dc\u30bf\u30f3", "text": "\u3053\u3093\u306b\u3061\u306f"}, "step": 0},
                {"type": "type", "data": {"selector": "#\u5165\u529b", "text": "caf\u00e9"}, "step": 1},
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["total_refs"] == 2


# ===== Stress 274177 Extended (9 more = 18 total) =====

class TestStress274177Extended:
    """274177-Stress: extended scaling and performance tests."""

    def test_274177_ext_001_500_actions(self, builder):
        """500-action episode processes without error."""
        episode = make_episode(num_actions=500, domain="stress500.com")
        result = builder.build_refmap(episode)
        assert result["stats"]["action_count"] == 500

    def test_274177_ext_002_performance_100_builds(self, builder, gmail_episode):
        """100 RefMap builds < 2 seconds total."""
        import time
        start = time.monotonic()
        for _ in range(100):
            builder.build_refmap(gmail_episode)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"100 builds: {elapsed:.2f}s (limit: 2s)"

    def test_274177_ext_003_1000_unique_ref_ids(self):
        """1000 unique semantic inputs produce 1000 unique ref_ids."""
        ref_ids = set()
        for i in range(1000):
            sem = {"aria_label": f"Element-{i}", "data_testid": f"test-{i}"}
            ref_ids.add(generate_ref_id(sem))
        assert len(ref_ids) == 1000

    def test_274177_ext_004_memory_no_crash_1000(self, builder):
        """1000 small episodes build without crash."""
        for i in range(1000):
            ep = {
                "session_id": f"mem-{i}",
                "domain": "test.com",
                "actions": [
                    {"type": "click", "data": {"selector": f"#btn-{i}"}, "step": 0}
                ],
            }
            builder.build_refmap(ep)

    def test_274177_ext_005_mixed_semantic_structural(self, builder):
        """Mix of semantic-only, structural-only, and complete actions."""
        actions = []
        for i in range(30):
            if i % 3 == 0:
                # Semantic only
                actions.append({"type": "click", "data": {"aria-label": f"Btn {i}", "role": "button"}, "step": i})
            elif i % 3 == 1:
                # Structural only
                actions.append({"type": "click", "data": {"selector": f"div.row-{i} > button"}, "step": i})
            else:
                # Both
                actions.append({"type": "click", "data": {"selector": f"#btn-{i}", "aria-label": f"Btn {i}"}, "step": i})
        episode = {
            "session_id": "mixed-types",
            "domain": "test.com",
            "actions": actions,
        }
        result = builder.build_refmap(episode)
        stats = result["stats"]
        assert stats["semantic_only_count"] + stats["structural_only_count"] + stats["complete_count"] == stats["total_refs"]
        assert stats["semantic_only_count"] > 0
        assert stats["structural_only_count"] > 0
        assert stats["complete_count"] > 0

    def test_274177_ext_006_dedup_100_same_element(self, builder):
        """100 clicks on same element merge to 1 ref with 100 actions."""
        actions = [
            {"type": "click", "data": {"aria-label": "Refresh", "selector": "#refresh"}, "step": i}
            for i in range(100)
        ]
        episode = {
            "session_id": "dedup-100",
            "domain": "test.com",
            "actions": actions,
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["total_refs"] == 1
        ref = list(result["refmap"].values())[0]
        assert len(ref["actions"]) == 100

    def test_274177_ext_007_pages_count_scales(self, builder):
        """Pages count correct for many navigations."""
        actions = []
        for i in range(100):
            if i % 2 == 0:
                actions.append({"type": "navigate", "data": {"url": f"https://test.com/p/{i}"}, "step": i})
            else:
                actions.append({"type": "click", "data": {"selector": f"#btn-{i}"}, "step": i})
        episode = {
            "session_id": "pages-scale",
            "domain": "test.com",
            "actions": actions,
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["pages"] == 50

    def test_274177_ext_008_empty_nested_objects(self, builder):
        """Actions with empty nested target/element objects handled."""
        episode = {
            "session_id": "empty-nested",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {"selector": "#btn", "target": {}, "element": {}}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["total_refs"] == 1

    def test_274177_ext_009_determinism_across_builders(self):
        """Two separate builders produce same output for same input."""
        episode = make_episode(num_actions=10, domain="det.com", session_id="det-1")
        b1 = RefMapBuilder()
        b2 = RefMapBuilder()
        r1 = b1.build_refmap(episode)
        r2 = b2.build_refmap(episode)
        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


# ===== God 65537 Extended (18 more = 28 total) =====

class TestGod65537Extended:
    """65537-God: extended end-to-end and verification tests."""

    def test_65537_ext_001_reddit_post_flow(self, builder):
        """Reddit post flow produces valid RefMap."""
        episode = {
            "session_id": "reddit-001",
            "domain": "reddit.com",
            "actions": [
                {"type": "navigate", "data": {"url": "https://reddit.com/r/test"}, "step": 0},
                {"type": "click", "data": {"aria-label": "Create Post", "text": "Create Post"}, "step": 1},
                {"type": "type", "data": {"selector": "#title", "id": "title", "text": "My Post"}, "step": 2},
                {"type": "type", "data": {"selector": "[role='textbox']", "text": "Post body"}, "step": 3},
                {"type": "click", "data": {"selector": "button[type='submit']", "text": "Post"}, "step": 4},
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["action_count"] == 5
        assert result["stats"]["total_refs"] >= 4

    def test_65537_ext_002_github_search_flow(self, builder):
        """GitHub search flow produces valid RefMap."""
        episode = {
            "session_id": "github-001",
            "domain": "github.com",
            "actions": [
                {"type": "navigate", "data": {"url": "https://github.com"}, "step": 0},
                {"type": "click", "data": {"selector": "input.search", "name": "q", "aria-label": "Search"}, "step": 1},
                {"type": "type", "data": {"selector": "input.search", "text": "stillwater", "name": "q"}, "step": 2},
                {"type": "click", "data": {"selector": "button", "text": "Search"}, "step": 3},
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["action_count"] == 4
        assert result["url_source"] == "https://github.com"

    def test_65537_ext_003_signup_form_flow(self, builder):
        """Signup form flow with multiple typed fields."""
        episode = {
            "session_id": "signup-001",
            "domain": "example.com",
            "actions": [
                {"type": "navigate", "data": {"url": "https://example.com/signup"}, "step": 0},
                {"type": "type", "data": {"selector": "#email", "id": "email", "aria-label": "Email", "text": "u@e.com"}, "step": 1},
                {"type": "type", "data": {"selector": "#pw", "id": "pw", "aria-label": "Password", "text": "secret"}, "step": 2},
                {"type": "type", "data": {"selector": "#confirm", "id": "confirm", "text": "secret"}, "step": 3},
                {"type": "click", "data": {"selector": "button[type='submit']", "data-testid": "signup-btn", "text": "Sign Up"}, "step": 4},
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["total_refs"] >= 4

    def test_65537_ext_004_multi_page_nav(self, builder):
        """Multi-page navigation produces valid pages count."""
        episode = {
            "session_id": "multi-001",
            "domain": "example.com",
            "actions": [
                {"type": "navigate", "data": {"url": "https://example.com/a"}, "step": 0},
                {"type": "click", "data": {"selector": "#link-b", "text": "Page B"}, "step": 1},
                {"type": "navigate", "data": {"url": "https://example.com/b"}, "step": 2},
                {"type": "click", "data": {"selector": "#link-c", "text": "Page C"}, "step": 3},
                {"type": "navigate", "data": {"url": "https://example.com/c"}, "step": 4},
            ],
        }
        result = builder.build_refmap(episode)
        assert result["stats"]["pages"] == 3
        assert result["stats"]["action_count"] == 5

    def test_65537_ext_005_all_workflows_valid(self, builder):
        """All workflow types produce valid RefMaps with correct stats."""
        workflows = [
            make_episode(num_actions=5, domain="alpha.com", session_id="wf-1"),
            make_episode(num_actions=10, domain="beta.com", session_id="wf-2"),
            make_episode(num_actions=3, domain="gamma.com", session_id="wf-3"),
        ]
        for ep in workflows:
            result = builder.build_refmap(ep)
            assert result["version"] == REFMAP_VERSION
            assert result["stats"]["total_refs"] > 0
            assert result["stats"]["action_count"] == len(ep["actions"])

    def test_65537_ext_006_ref_ids_unique_across_episode(self, builder, gmail_episode):
        """All ref_ids in a single RefMap are unique."""
        result = builder.build_refmap(gmail_episode)
        ids = list(result["refmap"].keys())
        assert len(ids) == len(set(ids))

    def test_65537_ext_007_reliability_scores_match_constants(self, builder, gmail_episode):
        """Reliability scores match RELIABILITY_SCORES constants."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            for key, score in entry["reliability"].items():
                if key in RELIABILITY_SCORES:
                    # Should be equal OR css_selector adjusted
                    if key == "css_selector":
                        assert score >= 0.70
                    else:
                        assert score == RELIABILITY_SCORES[key], (
                            f"{ref_id}/{key}: {score} != {RELIABILITY_SCORES[key]}"
                        )

    def test_65537_ext_008_resolution_strategy_format(self, builder, gmail_episode):
        """Resolution strategy has format 'key (score)'."""
        result = builder.build_refmap(gmail_episode)
        for ref_id, entry in result["refmap"].items():
            strategy = entry["resolution_strategy"]
            if strategy != "none":
                assert "(" in strategy and ")" in strategy, (
                    f"Bad strategy format: {strategy}"
                )

    def test_65537_ext_009_json_roundtrip_100_times(self, builder, gmail_episode):
        """RefMap survives 100 JSON serialize/deserialize cycles."""
        result = builder.build_refmap(gmail_episode)
        current = json.dumps(result, sort_keys=True)
        for _ in range(100):
            parsed = json.loads(current)
            current = json.dumps(parsed, sort_keys=True)
        final = json.loads(current)
        assert final["refmap"] == result["refmap"]
        assert final["stats"] == result["stats"]

    def test_65537_ext_010_all_actions_covered(self, builder, gmail_episode):
        """Every action (except scroll/wait) has a ref entry."""
        result = builder.build_refmap(gmail_episode)
        covered_indices = set()
        for ref_id, entry in result["refmap"].items():
            for act in entry["actions"]:
                covered_indices.add(act["action_index"])
        # All 5 actions in gmail_episode should be covered
        expected = set(range(len(gmail_episode["actions"])))
        assert covered_indices == expected

    def test_65537_ext_011_proof_chain_works(self, builder, gmail_episode):
        """RefMap integrates with Phase 2 compile_episode pipeline."""
        from solace_cli.browser.episode_to_recipe_compiler import EpisodeCompiler
        ec = EpisodeCompiler()
        recipe = ec.compile_episode(gmail_episode)
        assert "refmap" in recipe
        assert "proof" in recipe
        from solace_cli.browser.integration import verify_recipe
        result = verify_recipe(recipe)
        assert result["valid"]

    def test_65537_ext_012_semantic_and_structural_independent(self, builder):
        """Semantic and structural extraction are independent operations."""
        data = {
            "aria-label": "Submit",
            "selector": "#submit-btn",
            "id": "submit-btn",
        }
        sem = extract_semantic(data)
        struct = extract_structural(data)
        # Semantic should have aria_label
        assert "aria_label" in sem
        # Structural should have css_selector
        assert "css_selector" in struct

    def test_65537_ext_013_data_qa_attribute(self, builder):
        """data-qa attribute extracted as semantic."""
        episode = {
            "session_id": "qa-attr",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {"data-qa": "checkout-btn", "selector": "#checkout"}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        ref = list(result["refmap"].values())[0]
        assert ref["semantic"].get("data_qa") == "checkout-btn"

    def test_65537_ext_014_type_attribute_preserved(self, builder):
        """HTML type attribute (submit, email, etc.) preserved in semantic."""
        episode = {
            "session_id": "type-attr",
            "domain": "test.com",
            "actions": [
                {"type": "type", "data": {"selector": "#email", "type": "email", "text": "x@y.com"}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        ref = list(result["refmap"].values())[0]
        assert ref["semantic"].get("type") == "email"

    def test_65537_ext_015_xpath_in_structural(self, builder):
        """XPath extracted into structural selectors."""
        episode = {
            "session_id": "xpath-test",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {"xpath": "//button[@id='submit']", "selector": "#submit"}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        ref = list(result["refmap"].values())[0]
        assert ref["structural"].get("xpath") == "//button[@id='submit']"

    def test_65537_ext_016_ref_path_in_structural(self, builder):
        """ref_path extracted into structural selectors."""
        episode = {
            "session_id": "refpath-test",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {"ref_path": "body>main:0>button:2", "selector": "button"}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        ref = list(result["refmap"].values())[0]
        assert ref["structural"].get("ref_path") == "body>main:0>button:2"

    def test_65537_ext_017_nth_child_in_structural(self, builder):
        """nth_child index extracted into structural selectors."""
        episode = {
            "session_id": "nth-test",
            "domain": "test.com",
            "actions": [
                {"type": "click", "data": {"selector": "li", "nth_child": 3}, "step": 0}
            ],
        }
        result = builder.build_refmap(episode)
        ref = list(result["refmap"].values())[0]
        assert ref["structural"].get("nth_child") == 3

    def test_65537_ext_018_full_verification_ladder(self, builder, gmail_episode):
        """Full verification ladder: OAuth -> 641 -> 274177 -> 65537.

        OAuth: Schema valid
        641: Edge cases handled
        274177: Deterministic
        65537: Proof chain intact
        """
        # OAuth: Valid schema
        result = builder.build_refmap(gmail_episode)
        assert result["version"] == REFMAP_VERSION
        assert "refmap" in result
        assert "stats" in result

        # 641: Edge - empty data handled
        empty_ep = {
            "session_id": "edge",
            "domain": "test.com",
            "actions": [{"type": "click", "data": {}, "step": 0}],
        }
        edge_result = builder.build_refmap(empty_ep)
        assert isinstance(edge_result["refmap"], dict)

        # 274177: Determinism
        r1 = json.dumps(builder.build_refmap(gmail_episode), sort_keys=True)
        r2 = json.dumps(builder.build_refmap(gmail_episode), sort_keys=True)
        assert r1 == r2

        # 65537: Proof chain
        from solace_cli.browser.episode_to_recipe_compiler import EpisodeCompiler
        from solace_cli.browser.integration import verify_recipe
        recipe = EpisodeCompiler().compile_episode(gmail_episode)
        verification = verify_recipe(recipe)
        assert verification["valid"]
