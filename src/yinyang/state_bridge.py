"""State Bridge — translates tab FSM state changes to top rail visual updates."""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("solace-browser.yinyang")


class YinyangState(str, Enum):
    """FSM states for the Yinyang assistant (mirrors Diagram 13)."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    INTENT_CLASSIFIED = "intent_classified"
    PREVIEW_GENERATING = "preview_generating"
    PREVIEW_READY = "preview_ready"
    COOLDOWN = "cooldown"
    APPROVED = "approved"
    SEALED = "sealed"
    EXECUTING = "executing"
    DONE = "done"
    BLOCKED = "blocked"
    ERROR = "error"


# FSM color map (matches top_rail.js)
STATE_COLORS: dict[YinyangState, str] = {
    YinyangState.IDLE: "#666666",
    YinyangState.LISTENING: "#4a9eff",
    YinyangState.PROCESSING: "#4a9eff",
    YinyangState.INTENT_CLASSIFIED: "#4a9eff",
    YinyangState.PREVIEW_GENERATING: "#f5a623",
    YinyangState.PREVIEW_READY: "#f5a623",
    YinyangState.COOLDOWN: "#f5a623",
    YinyangState.APPROVED: "#27ae60",
    YinyangState.SEALED: "#27ae60",
    YinyangState.EXECUTING: "#27ae60",
    YinyangState.DONE: "#27ae60",
    YinyangState.BLOCKED: "#e74c3c",
    YinyangState.ERROR: "#e74c3c",
}

# Valid state transitions (guards)
VALID_TRANSITIONS: dict[YinyangState, set[YinyangState]] = {
    YinyangState.IDLE: {YinyangState.LISTENING, YinyangState.ERROR},
    YinyangState.LISTENING: {YinyangState.PROCESSING, YinyangState.IDLE, YinyangState.ERROR},
    YinyangState.PROCESSING: {YinyangState.INTENT_CLASSIFIED, YinyangState.ERROR},
    YinyangState.INTENT_CLASSIFIED: {YinyangState.PREVIEW_GENERATING, YinyangState.ERROR},
    YinyangState.PREVIEW_GENERATING: {YinyangState.PREVIEW_READY, YinyangState.ERROR},
    YinyangState.PREVIEW_READY: {YinyangState.COOLDOWN, YinyangState.IDLE, YinyangState.ERROR},
    YinyangState.COOLDOWN: {YinyangState.APPROVED, YinyangState.IDLE, YinyangState.BLOCKED},
    YinyangState.APPROVED: {YinyangState.SEALED, YinyangState.ERROR},
    YinyangState.SEALED: {YinyangState.EXECUTING, YinyangState.ERROR},
    YinyangState.EXECUTING: {YinyangState.DONE, YinyangState.ERROR},
    YinyangState.DONE: {YinyangState.IDLE},
    YinyangState.BLOCKED: {YinyangState.IDLE},
    YinyangState.ERROR: {YinyangState.IDLE},
}


class StateBridge:
    """Bridges FSM state changes to browser top rail via postMessage."""

    def __init__(self, page: Any):
        self._page = page
        self._state = YinyangState.IDLE
        self._listeners: list[Callable[[YinyangState, YinyangState], None]] = []

    @property
    def state(self) -> YinyangState:
        return self._state

    @property
    def color(self) -> str:
        return STATE_COLORS.get(self._state, "#666666")

    def on_transition(self, callback: Callable[[YinyangState, YinyangState], None]) -> None:
        """Register a listener for state transitions."""
        self._listeners.append(callback)

    async def transition(self, new_state: YinyangState) -> bool:
        """Attempt a state transition. Returns True if valid and applied."""
        if new_state not in VALID_TRANSITIONS.get(self._state, set()):
            logger.warning(
                f"[StateBridge] Invalid transition: {self._state.value} -> {new_state.value}"
            )
            return False

        old_state = self._state
        self._state = new_state
        logger.debug(f"[StateBridge] {old_state.value} -> {new_state.value}")

        # Notify top rail via postMessage
        await self._notify_top_rail(new_state)

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(old_state, new_state)
            except Exception as exc:
                logger.warning(f"[StateBridge] Listener error: {exc}")

        return True

    async def reset(self) -> None:
        """Reset to IDLE state unconditionally."""
        self._state = YinyangState.IDLE
        await self._notify_top_rail(YinyangState.IDLE)

    async def _notify_top_rail(self, state: YinyangState) -> None:
        """Send state update to top rail via window.postMessage."""
        try:
            await self._page.evaluate(
                f"window.postMessage({{type: 'yinyang_state', state: '{state.value}'}}, '*')"
            )
        except Exception as exc:
            logger.debug(f"[StateBridge] postMessage failed: {exc}")
