"""Claude Code Wrapper client — calls stillwater wrapper at localhost:8080."""
from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger("solace-browser.llm")

class LLMBackendError(Exception):
    """Raised when LLM backend is unavailable or returns invalid response."""
    pass

class ClaudeCodeClient:
    """Calls Claude Code wrapper (Ollama-compatible HTTP API)."""

    def __init__(self):
        self.host = os.getenv("CLAUDE_CODE_HOST", "127.0.0.1")
        self.port = int(os.getenv("CLAUDE_CODE_PORT", "8080"))
        self.timeout = int(os.getenv("CLAUDE_CODE_TIMEOUT", "30"))
        self.base_url = f"http://{self.host}:{self.port}"

    def __call__(self, intent_dict: dict[str, Any]) -> dict[str, Any]:
        """Generate recipe from intent via Claude Code wrapper."""
        prompt = self._build_prompt(intent_dict)
        try:
            req = Request(
                f"{self.base_url}/api/generate",
                data=json.dumps({
                    "model": "claude",
                    "prompt": prompt,
                    "stream": False,
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
        except URLError as exc:
            raise LLMBackendError(
                f"Cannot connect to Claude Code wrapper at {self.base_url}: {exc}. "
                f"Start it with: python3 stillwater/src/cli/src/claude_code_wrapper.py"
            ) from exc
        except TimeoutError as exc:
            raise LLMBackendError(
                f"Claude Code wrapper timed out after {self.timeout}s"
            ) from exc

        response_text = body.get("response", "")
        return self._parse_recipe(response_text, intent_dict)

    def _build_prompt(self, intent_dict: dict[str, Any]) -> str:
        intent = intent_dict.get("intent", "unknown")
        platform = intent_dict.get("platform", "web")
        action_type = intent_dict.get("action_type", "navigate")
        return (
            f"Generate a Solace Browser recipe as JSON for:\n"
            f"Intent: {intent}\n"
            f"Platform: {platform}\n"
            f"Action: {action_type}\n\n"
            f"Return valid JSON with fields: name, steps (array of {{action, target, value}}), "
            f"evidence_mode, estimated_tokens."
        )

    def _parse_recipe(self, text: str, intent_dict: dict[str, Any]) -> dict[str, Any]:
        """Parse LLM response into recipe dict."""
        # Try to extract JSON from response
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

        # Fallback: return structured recipe from intent
        return {
            "name": intent_dict.get("intent", "generated-recipe"),
            "steps": [{"action": intent_dict.get("action_type", "navigate"), "target": intent_dict.get("platform", ""), "value": ""}],
            "evidence_mode": "screenshot",
            "estimated_tokens": len(text.split()),
            "raw_response": text,
        }

    def health_check(self) -> dict[str, Any]:
        """Check if Claude Code wrapper is running."""
        try:
            req = Request(f"{self.base_url}/", method="GET")
            with urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            return {"available": False, "error": str(exc)}

    def __repr__(self) -> str:
        return f"ClaudeCodeClient(url={self.base_url})"
