"""Together.ai LLM client."""
from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger("solace-browser.llm")

class TogetherClient:
    """Calls Together.ai API for recipe generation."""

    def __init__(self):
        self.api_key = os.getenv("TOGETHER_API_KEY", "")
        self.model = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
        self.base_url = "https://api.together.xyz/v1"
        self.timeout = int(os.getenv("TOGETHER_TIMEOUT", "30"))

    def __call__(self, intent_dict: dict[str, Any]) -> dict[str, Any]:
        """Generate recipe from intent via Together.ai."""
        if not self.api_key:
            from llm.claude_code_client import LLMBackendError
            raise LLMBackendError("TOGETHER_API_KEY not set. Set it or use --llm-backend claude_code")

        prompt = self._build_prompt(intent_dict)
        try:
            req = Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps({
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2000,
                }).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            with urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
        except URLError as exc:
            from llm.claude_code_client import LLMBackendError
            raise LLMBackendError(f"Together.ai API error: {exc}") from exc

        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        return self._parse_recipe(content, intent_dict)

    def _build_prompt(self, intent_dict: dict[str, Any]) -> str:
        intent = intent_dict.get("intent", "unknown")
        platform = intent_dict.get("platform", "web")
        action_type = intent_dict.get("action_type", "navigate")
        return (
            f"Generate a Solace Browser recipe as JSON for:\n"
            f"Intent: {intent}\nPlatform: {platform}\nAction: {action_type}\n\n"
            f"Return valid JSON: {{name, steps: [{{action, target, value}}], evidence_mode, estimated_tokens}}"
        )

    def _parse_recipe(self, text: str, intent_dict: dict[str, Any]) -> dict[str, Any]:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
        return {
            "name": intent_dict.get("intent", "generated-recipe"),
            "steps": [{"action": intent_dict.get("action_type", "navigate"), "target": intent_dict.get("platform", ""), "value": ""}],
            "evidence_mode": "screenshot",
            "estimated_tokens": len(text.split()),
        }

    def __repr__(self) -> str:
        return f"TogetherClient(model={self.model})"
