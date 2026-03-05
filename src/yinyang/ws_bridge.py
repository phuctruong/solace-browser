"""WebSocket bridge — relays messages between browser JS and cloud/local chat."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger("solace-browser.yinyang")

# ── Content filter (COPPA + safety baseline) ──
# Patterns that must be blocked in user-generated content.
# Kept minimal and deterministic — no external deps.
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        # Profanity / slurs (compact list — extend as needed)
        r"\b(?:f+u+c+k+|s+h+i+t+|a+s+s+h+o+l+e+|b+i+t+c+h+|d+a+m+n+|c+u+n+t+)\b",
        # Threats / violence
        r"\b(?:kill\s+(?:you|her|him|them|myself)|bomb\s+threat|shoot\s+up)\b",
        # Self-harm
        r"\b(?:how\s+to\s+(?:kill|harm)\s+(?:myself|yourself))\b",
        # PII solicitation targeting minors
        r"\b(?:what\s+is\s+your\s+(?:address|phone|school))\b",
    ]
]

# Age-gate: if user identifies as under 13, block data collection
_MINOR_PATTERN = re.compile(
    r"\b(?:i\s+am|i'm|im)\s+(\d{1,2})\s*(?:years?\s*old|yo|y\.?o\.?)\b", re.IGNORECASE
)


def _check_content(text: str) -> str | None:
    """Return a rejection reason if content violates filters, else None."""
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(text):
            return "Your message was filtered. Please keep the conversation respectful and safe."
    match = _MINOR_PATTERN.search(text)
    if match:
        age = int(match.group(1))
        if age < 13:
            return (
                "For your safety, users under 13 cannot share personal information. "
                "Please use Solace Browser with a parent or guardian."
            )
    return None

class YinyangWSBridge:
    """Local WebSocket handler for Yinyang chat relay."""

    def __init__(self, cloud_url: str = "https://www.solaceagi.com", llm_client: Any = None):
        self.cloud_url = cloud_url
        self.llm_client = llm_client
        self.sessions: dict[str, dict[str, Any]] = {}

    async def handle_ws(self, request):
        """Handle WebSocket connection from browser JS."""
        from aiohttp import web, WSMsgType

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        session_id = request.match_info.get("session_id", "default")
        self.sessions[session_id] = {"ws": ws, "messages": []}

        logger.info(f"[YY] WebSocket connected: {session_id}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        response = await self._handle_message(session_id, data)
                        if response:
                            await ws.send_json(response)
                    except json.JSONDecodeError:
                        await ws.send_json({"type": "error", "payload": {"message": "Invalid JSON"}})
                elif msg.type == WSMsgType.ERROR:
                    logger.warning(f"[YY] WS error: {ws.exception()}")
        finally:
            self.sessions.pop(session_id, None)
            logger.info(f"[YY] WebSocket disconnected: {session_id}")

        return ws

    async def _handle_message(self, session_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        msg_type = data.get("type", "")
        payload = data.get("payload", {})

        if msg_type == "chat":
            content = payload.get("content", "")
            rejection = _check_content(content)
            if rejection is not None:
                return {
                    "type": "chat",
                    "payload": {"content": rejection, "role": "assistant", "filtered": True},
                }
            response_text = self._local_response(content)
            return {
                "type": "chat",
                "payload": {"content": response_text, "role": "assistant"},
            }

        if msg_type == "heartbeat":
            return {"type": "heartbeat", "payload": {"status": "ok"}}

        return {"type": "error", "payload": {"message": f"Unknown type: {msg_type}"}}

    def _local_response(self, content: str) -> str:
        """Generate local response using keyword routing."""
        lower = content.lower()
        if any(w in lower for w in ["help", "what", "how"]):
            return "I'm Yinyang, your AI assistant. I can help you browse apps, install recipes, and automate tasks."
        if any(w in lower for w in ["app", "store", "install"]):
            return "Visit the App Store to browse available apps. Free tier includes Gmail Triage and Morning Brief."
        if any(w in lower for w in ["credit", "balance"]):
            return "Check your credits at /billing. Current balance shown in the credits panel above."
        return "I'm here to help! Ask me about apps, recipes, or automation."
