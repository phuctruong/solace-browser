"""Tests for LLM backend factory and clients."""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm import get_llm_client
from llm.noop_client import NoopClient
from llm.claude_code_client import ClaudeCodeClient, LLMBackendError
from llm.together_client import TogetherClient


def test_factory_noop():
    client = get_llm_client("none")
    assert isinstance(client, NoopClient)


def test_factory_claude_code():
    client = get_llm_client("claude_code")
    assert isinstance(client, ClaudeCodeClient)


def test_factory_together():
    client = get_llm_client("together")
    assert isinstance(client, TogetherClient)


def test_factory_unknown_raises():
    with pytest.raises(ValueError, match="Unknown LLM backend"):
        get_llm_client("invalid_backend")


def test_noop_returns_valid_recipe():
    client = NoopClient()
    result = client({"intent": "test", "platform": "gmail", "action_type": "read"})
    assert "name" in result
    assert "steps" in result
    assert isinstance(result["steps"], list)
    assert result["llm_backend"] == "none"


def test_noop_includes_intent():
    client = NoopClient()
    result = client({"intent": "gmail-triage", "platform": "gmail", "action_type": "read"})
    assert result["name"] == "gmail-triage"


def test_claude_code_client_repr():
    client = ClaudeCodeClient()
    assert "ClaudeCodeClient" in repr(client)
    assert "127.0.0.1" in repr(client)


def test_claude_code_no_server():
    """When wrapper isn't running, should raise LLMBackendError with clear message."""
    os.environ["CLAUDE_CODE_PORT"] = "19999"  # unlikely to be running
    client = ClaudeCodeClient()
    with pytest.raises(LLMBackendError, match="Cannot connect"):
        client({"intent": "test"})
    os.environ.pop("CLAUDE_CODE_PORT", None)


def test_together_no_key():
    """Together client without API key should raise LLMBackendError."""
    os.environ.pop("TOGETHER_API_KEY", None)
    client = TogetherClient()
    with pytest.raises(LLMBackendError, match="TOGETHER_API_KEY not set"):
        client({"intent": "test"})


def test_noop_empty_intent():
    client = NoopClient()
    result = client({})
    assert result["name"] == "noop-recipe"
    assert result["estimated_tokens"] == 0
