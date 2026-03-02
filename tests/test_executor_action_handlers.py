"""Tests for extended RecipeExecutor action handlers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from browser.context import BrowserContext
from oauth3.vault import OAuth3Vault
from recipes.recipe_compiler import compile_from_steps
from recipes.recipe_executor import ExecutionError, RecipeExecutor


def _make_executor(tmp_path, scopes=None):
    vault = OAuth3Vault(
        encryption_key=b"t" * 32,
        evidence_log=tmp_path / "oauth3.jsonl",
        storage_path=tmp_path / "tokens.enc.json",
    )
    if scopes is None:
        scopes = [
            "browser.navigate", "browser.click", "browser.fill",
            "browser.screenshot", "browser.verify", "browser.session",
            "browser.read", "browser.dom",
        ]
    token = vault.issue_token(scopes, ttl_seconds=3600)
    browser = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser.jsonl",
        seed=42,
    )
    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        determinism_seed=65537,
        execution_log=tmp_path / "exec.jsonl",
    )
    return executor, browser, vault


@pytest.mark.asyncio
async def test_session_action_succeeds(tmp_path):
    executor, browser, _ = _make_executor(tmp_path)
    steps = [
        {"step_id": "s001", "action": "session", "target": "artifacts/session.json", "description": "Load session"},
    ]
    ir = compile_from_steps("session-test", steps, scopes=("browser.session",)).to_dict()
    result = await executor.execute(ir, browser)
    assert result.status == "success"
    assert result.steps_executed == 1


@pytest.mark.asyncio
async def test_wait_action_succeeds(tmp_path):
    executor, browser, _ = _make_executor(tmp_path)
    steps = [
        {"step_id": "s001", "action": "wait", "selector": "[role='row']", "timeout_ms": 5000, "description": "Wait"},
    ]
    ir = compile_from_steps("wait-test", steps, scopes=("browser.read",)).to_dict()
    result = await executor.execute(ir, browser)
    assert result.status == "success"


@pytest.mark.asyncio
async def test_wait_action_requires_selector(tmp_path):
    executor, browser, _ = _make_executor(tmp_path)
    steps = [
        {"step_id": "s001", "action": "wait", "description": "Wait for nothing"},
    ]
    ir = compile_from_steps("wait-fail", steps, scopes=("browser.read",)).to_dict()
    with pytest.raises(ExecutionError, match="wait requires selector"):
        await executor.execute(ir, browser)


@pytest.mark.asyncio
async def test_extract_action_succeeds(tmp_path):
    executor, browser, _ = _make_executor(tmp_path)
    steps = [
        {"step_id": "s001", "action": "extract", "target": "[role='row']", "fields": {"subject": {}, "sender": {}}, "description": "Extract"},
    ]
    ir = compile_from_steps("extract-test", steps, scopes=("browser.read",)).to_dict()
    result = await executor.execute(ir, browser)
    assert result.status == "success"


@pytest.mark.asyncio
async def test_extract_requires_selector(tmp_path):
    executor, browser, _ = _make_executor(tmp_path)
    steps = [
        {"step_id": "s001", "action": "extract", "description": "Extract nothing"},
    ]
    ir = compile_from_steps("extract-fail", steps, scopes=("browser.read",)).to_dict()
    with pytest.raises(ExecutionError, match="extract requires selector"):
        await executor.execute(ir, browser)


@pytest.mark.asyncio
async def test_return_action_succeeds(tmp_path):
    executor, browser, _ = _make_executor(tmp_path)
    steps = [
        {"step_id": "s001", "action": "return", "description": "Return data"},
    ]
    ir = compile_from_steps("return-test", steps, scopes=("browser.read",)).to_dict()
    result = await executor.execute(ir, browser)
    assert result.status == "success"


@pytest.mark.asyncio
async def test_scroll_action_succeeds(tmp_path):
    executor, browser, _ = _make_executor(tmp_path)
    steps = [
        {"step_id": "s001", "action": "scroll", "description": "Scroll down", "direction": "down", "amount": 500},
    ]
    ir = compile_from_steps("scroll-test", steps, scopes=("browser.read",)).to_dict()
    result = await executor.execute(ir, browser)
    assert result.status == "success"


@pytest.mark.asyncio
async def test_inspect_action_succeeds(tmp_path):
    executor, browser, _ = _make_executor(tmp_path)
    steps = [
        {"step_id": "s001", "action": "inspect", "target": "#main", "description": "Inspect"},
    ]
    ir = compile_from_steps("inspect-test", steps, scopes=("browser.read",)).to_dict()
    result = await executor.execute(ir, browser)
    assert result.status == "success"


@pytest.mark.asyncio
async def test_gmail_full_recipe_executes(tmp_path):
    """End-to-end test: all 6 Gmail recipe actions execute in sequence."""
    executor, browser, _ = _make_executor(tmp_path, scopes=[
        "browser.navigate", "browser.click", "browser.fill",
        "browser.screenshot", "browser.verify", "browser.session",
        "browser.read", "browser.dom", "gmail.read.inbox",
    ])
    steps = [
        {"step_id": "s001", "action": "session", "target": "artifacts/gmail.json", "description": "Load session"},
        {"step_id": "s002", "action": "navigate", "target": "https://mail.google.com/mail/u/0/#inbox", "description": "Open inbox"},
        {"step_id": "s003", "action": "verify", "description": "Check auth"},
        {"step_id": "s004", "action": "wait", "selector": "[role='row']", "timeout_ms": 8000, "description": "Wait"},
        {"step_id": "s005", "action": "extract", "target": "[role='row']", "fields": {"subject": {}}, "description": "Extract"},
        {"step_id": "s006", "action": "return", "description": "Return"},
    ]
    ir = compile_from_steps("gmail-full", steps, scopes=("gmail.read.inbox", "browser.session")).to_dict()
    result = await executor.execute(ir, browser)
    assert result.status == "success"
    assert result.steps_executed == 6
    assert result.final_state == "[*]"
    assert len(result.behavior_hash) == 64


@pytest.mark.asyncio
async def test_scope_denial_blocks_action(tmp_path):
    """Verify scope enforcement works for new actions."""
    vault = OAuth3Vault(
        encryption_key=b"t" * 32,
        evidence_log=tmp_path / "oauth3.jsonl",
        storage_path=tmp_path / "tokens.enc.json",
    )
    # Only grant navigate scope, not session
    token = vault.issue_token(["browser.navigate"], ttl_seconds=3600)
    browser = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser.jsonl",
        seed=42,
    )
    executor = RecipeExecutor(
        oauth3_vault=vault,
        token_id=token["token_id"],
        execution_log=tmp_path / "exec.jsonl",
    )
    steps = [
        {"step_id": "s001", "action": "session", "target": "session.json", "description": "Load session"},
    ]
    ir = compile_from_steps("scope-deny", steps, scopes=("browser.session",)).to_dict()
    with pytest.raises(ExecutionError, match="scope denied"):
        await executor.execute(ir, browser)
