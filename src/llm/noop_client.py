"""Noop LLM client — returns stub recipes for testing/offline mode."""
from __future__ import annotations

from typing import Any

class NoopClient:
    """Returns stub recipe JSON. Used for SOLACE_LLM_BACKEND=none."""

    def __call__(self, intent_dict: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": intent_dict.get("intent", "noop-recipe"),
            "steps": [
                {
                    "action": "noop",
                    "target": intent_dict.get("platform", ""),
                    "value": "stub-no-llm",
                }
            ],
            "evidence_mode": "screenshot",
            "estimated_tokens": 0,
            "llm_backend": "none",
        }

    def __repr__(self) -> str:
        return "NoopClient()"
