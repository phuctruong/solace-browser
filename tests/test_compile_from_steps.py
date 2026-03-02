"""Tests for compile_from_steps — JSON step recipe compilation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from recipes.recipe_compiler import (
    CompilationError,
    RecipeIR,
    compile_from_steps,
    compile_json_recipe,
)


GMAIL_STEPS = [
    {"step_id": "s001", "index": 1, "action": "session", "target": "artifacts/gmail_session.json", "description": "Load session"},
    {"step_id": "s002", "index": 2, "action": "navigate", "target": "https://mail.google.com/mail/u/0/#inbox", "description": "Open inbox"},
    {"step_id": "s003", "index": 3, "action": "verify", "target": None, "description": "Check auth"},
    {"step_id": "s004", "index": 4, "action": "wait", "target": None, "selector": "[role='row']", "description": "Wait for rows"},
    {"step_id": "s005", "index": 5, "action": "extract", "target": "[role='row']", "description": "Extract emails", "fields": {"subject": {}}},
    {"step_id": "s006", "index": 6, "action": "return", "target": None, "description": "Return result"},
]


class TestCompileFromSteps:
    def test_compiles_linear_steps_to_ir(self):
        ir = compile_from_steps("gmail-test", GMAIL_STEPS)
        assert isinstance(ir, RecipeIR)
        assert ir.recipe_id == "gmail-test"
        assert ir.initial_state == "s001"
        assert len(ir.steps) == 6

    def test_ir_has_correct_hash(self):
        ir = compile_from_steps("gmail-test", GMAIL_STEPS)
        assert len(ir.ir_hash) == 64

    def test_determinism_same_input_same_hash(self):
        ir1 = compile_from_steps("gmail-test", GMAIL_STEPS)
        ir2 = compile_from_steps("gmail-test", GMAIL_STEPS)
        assert ir1.ir_hash == ir2.ir_hash

    def test_different_seed_different_hash(self):
        ir1 = compile_from_steps("gmail-test", GMAIL_STEPS, determinism_seed=1)
        ir2 = compile_from_steps("gmail-test", GMAIL_STEPS, determinism_seed=2)
        assert ir1.ir_hash != ir2.ir_hash

    def test_empty_steps_raises(self):
        with pytest.raises(CompilationError, match="no steps"):
            compile_from_steps("empty", [])

    def test_transitions_form_linear_chain(self):
        ir = compile_from_steps("chain-test", GMAIL_STEPS)
        steps_dict = {s.step_id: s for s in ir.steps}
        # First step transitions to second
        assert steps_dict["s001"].condition_next_state[0]["next_state"] == "s002"
        # Last step transitions to [*]
        assert steps_dict["s006"].condition_next_state[0]["next_state"] == "[*]"

    def test_scopes_inferred_from_actions(self):
        ir = compile_from_steps("scope-test", GMAIL_STEPS)
        assert "browser.navigate" in ir.scopes_required
        assert "browser.verify" in ir.scopes_required

    def test_explicit_scopes_included(self):
        ir = compile_from_steps("scope-test", GMAIL_STEPS, scopes=("gmail.read.inbox",))
        assert "gmail.read.inbox" in ir.scopes_required
        assert "browser.navigate" in ir.scopes_required

    def test_params_captured_from_step_fields(self):
        ir = compile_from_steps("params-test", GMAIL_STEPS)
        steps_dict = {s.step_id: s for s in ir.steps}
        # s004 has selector in params
        assert steps_dict["s004"].params.get("selector") == "[role='row']"
        # s005 has fields in params
        assert "fields" in steps_dict["s005"].params

    def test_step_ids_auto_generated_if_missing(self):
        steps = [
            {"action": "navigate", "target": "https://example.com"},
            {"action": "click", "target": "#button"},
        ]
        ir = compile_from_steps("auto-id", steps)
        assert ir.steps[0].step_id == "s001"
        assert ir.steps[1].step_id == "s002"

    def test_ir_to_dict_roundtrip(self):
        ir = compile_from_steps("roundtrip", GMAIL_STEPS)
        d = ir.to_dict()
        assert d["recipe_id"] == "roundtrip"
        assert len(d["steps"]) == 6
        assert d["initial_state"] == "s001"

    def test_version_and_seed_in_output(self):
        ir = compile_from_steps("v-test", GMAIL_STEPS, version="2.0.0", determinism_seed=42)
        assert ir.version == "2.0.0"
        assert ir.determinism_seed == 42


class TestCompileJsonRecipe:
    def test_compiles_json_file_with_steps(self, tmp_path):
        recipe = {
            "id": "test-recipe",
            "version": "1.0.0",
            "platform": "gmail",
            "oauth3_scopes": ["gmail.read.inbox"],
            "steps": [
                {"step": 1, "action": "navigate", "target": "https://mail.google.com"},
                {"step": 2, "action": "extract_all", "selector": "[role='row']", "description": "Extract"},
                {"step": 3, "action": "return_result", "description": "Return"},
            ],
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(recipe), encoding="utf-8")
        ir = compile_json_recipe(path)
        assert ir.recipe_id == "test-recipe"
        assert len(ir.steps) >= 3

    def test_compiles_json_file_with_mermaid(self, tmp_path):
        recipe = {
            "id": "mermaid-recipe",
            "version": "1.0.0",
            "mermaid_fsm": "stateDiagram-v2\n  [*] --> NavigateHome\n  NavigateHome --> ClickButton: action_ok\n  ClickButton --> [*]: done",
            "steps": [
                {"step": 1, "action": "navigate", "target": "https://example.com"},
            ],
        }
        path = tmp_path / "mermaid.json"
        path.write_text(json.dumps(recipe), encoding="utf-8")
        ir = compile_json_recipe(path)
        assert ir.recipe_id == "mermaid-recipe"
