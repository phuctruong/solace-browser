"""LLM client factory — abstracts backend selection."""
from __future__ import annotations
from typing import Any, Callable

def get_llm_client(backend: str = "none") -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return an LLM client callable based on backend name.

    Args:
        backend: One of "claude_code", "together", "none"

    Returns:
        Callable that takes intent_dict and returns recipe dict

    Raises:
        ValueError: If backend is unknown
    """
    if backend == "claude_code":
        from llm.claude_code_client import ClaudeCodeClient
        return ClaudeCodeClient()
    elif backend == "together":
        from llm.together_client import TogetherClient
        return TogetherClient()
    elif backend == "none":
        from llm.noop_client import NoopClient
        return NoopClient()
    else:
        raise ValueError(f"Unknown LLM backend: {backend!r}. Must be one of: claude_code, together, none")
