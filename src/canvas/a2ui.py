"""
Agent-to-UI (A2UI) Communication Protocol

Structured message passing between an AI agent and the user interface.

The A2UIBridge sends typed messages (status, progress, input requests,
confirmations, results, errors) from the agent to the UI. The A2UIChannel
provides a bounded FIFO message queue with auto-expiry.

OAuth3 scope requirements:
  canvas.a2ui.communicate — all A2UI message operations
  canvas.a2ui.input       — requesting user input (step-up required)

Security rules:
  - Input requests auto-deny after 30 seconds (fail-closed)
  - High-risk confirmations cannot auto-approve
  - Message queue bounded at 100 messages (oldest dropped when full)
  - All A2UI messages logged to audit trail

Rung: 641
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, Optional

from canvas.scopes import (
    SCOPE_A2UI_COMMUNICATE,
    SCOPE_A2UI_INPUT,
    register_canvas_scopes,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_QUEUE_DEPTH: int = 100
MESSAGE_AUTO_EXPIRE_SECONDS: int = 300       # 5 minutes
INPUT_REQUEST_TIMEOUT_SECONDS: int = 30      # 30-second auto-deny (fail-closed)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MessageType(Enum):
    """Type of A2UI message."""

    STATUS = "status"
    PROGRESS = "progress"
    INPUT_REQUEST = "input_request"
    CONFIRMATION = "confirmation"
    RESULT = "result"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """
    The result of a completed agent action, sent via A2UIBridge.send_result().

    Attributes:
        action:      Name/description of the action that was executed.
        success:     True if the action succeeded.
        output:      Output value or summary (string or dict).
        error:       Error message if success is False (None otherwise).
        evidence:    Optional audit evidence dict (scope_used, token_id, etc.).
        duration_ms: Action execution time in milliseconds.
    """

    action: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    evidence: Optional[Dict] = None
    duration_ms: int = 0


@dataclass
class A2UIMessage:
    """
    A single A2UI protocol message.

    All fields are immutable after creation (use dataclass replace() for updates).

    Attributes:
        message_id:        Unique message identifier (UUID).
        message_type:      MessageType enum value.
        payload:           Message-type-specific content dict.
        timestamp:         Creation timestamp in integer milliseconds since epoch.
        sender:            "agent" or "user".
        requires_response: True if the message needs a reply (input, confirmation).
        expires_at_ms:     Expiry timestamp in milliseconds. None = no expiry.
    """

    message_id: str
    message_type: MessageType
    payload: Dict
    timestamp: int
    sender: str
    requires_response: bool
    expires_at_ms: Optional[int] = None

    def is_expired(self, now_ms: Optional[int] = None) -> bool:
        """
        Return True if this message has passed its expiry time.

        Args:
            now_ms: Current time in ms. Defaults to now.

        Returns:
            True if expired, False if still valid or no expiry set.
        """
        if self.expires_at_ms is None:
            return False
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        return now_ms >= self.expires_at_ms

    def is_from_agent(self) -> bool:
        return self.sender == "agent"

    def is_from_user(self) -> bool:
        return self.sender == "user"


def _make_message(
    message_type: MessageType,
    payload: Dict,
    sender: str,
    requires_response: bool = False,
    ttl_seconds: Optional[int] = MESSAGE_AUTO_EXPIRE_SECONDS,
) -> A2UIMessage:
    """Factory helper: create a fresh A2UIMessage with auto-generated ID + timestamp."""
    now_ms = int(time.time() * 1000)
    expires_at_ms: Optional[int] = None
    if ttl_seconds is not None:
        expires_at_ms = now_ms + ttl_seconds * 1000

    return A2UIMessage(
        message_id=f"msg-{uuid.uuid4().hex[:12]}",
        message_type=message_type,
        payload=payload,
        timestamp=now_ms,
        sender=sender,
        requires_response=requires_response,
        expires_at_ms=expires_at_ms,
    )


# ---------------------------------------------------------------------------
# A2UIChannel
# ---------------------------------------------------------------------------

class A2UIChannel:
    """
    Bounded FIFO message queue for agent↔UI communication.

    Limits:
      - Max queue depth: 100 messages.
      - Oldest message is dropped when the queue is full (ring buffer behavior).
      - Messages auto-expire after 300 seconds (MESSAGE_AUTO_EXPIRE_SECONDS).

    Thread safety: NOT thread-safe (single-threaded async model assumed).
    """

    def __init__(self, max_depth: int = MAX_QUEUE_DEPTH) -> None:
        """
        Initialize the channel.

        Args:
            max_depth: Maximum number of messages in the queue. Default 100.
        """
        if max_depth < 1:
            raise ValueError(f"max_depth must be >= 1, got {max_depth}.")
        self._max_depth = max_depth
        self._queue: Deque[A2UIMessage] = deque()

    def push(self, message: A2UIMessage) -> None:
        """
        Enqueue a message.

        If the queue is full, the oldest message is dropped to make room
        (ring buffer behavior — prevents unbounded memory growth).

        Args:
            message: A2UIMessage to enqueue.
        """
        self._evict_expired()
        if len(self._queue) >= self._max_depth:
            # Drop oldest message (ring-buffer: never block, never grow unbounded)
            self._queue.popleft()
        self._queue.append(message)

    def pop(self) -> Optional[A2UIMessage]:
        """
        Dequeue and return the oldest message, or None if empty.

        Expired messages are silently skipped.

        Returns:
            A2UIMessage or None.
        """
        self._evict_expired()
        if not self._queue:
            return None
        return self._queue.popleft()

    def peek(self) -> Optional[A2UIMessage]:
        """
        Return the oldest message without removing it, or None if empty.

        Expired messages are silently skipped.

        Returns:
            A2UIMessage or None.
        """
        self._evict_expired()
        if not self._queue:
            return None
        return self._queue[0]

    def pop_all(self) -> list:
        """
        Dequeue and return all current messages in FIFO order.

        Returns:
            List of A2UIMessage (may be empty).
        """
        self._evict_expired()
        result = list(self._queue)
        self._queue.clear()
        return result

    @property
    def depth(self) -> int:
        """Current number of messages in the queue (after TTL eviction)."""
        self._evict_expired()
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """True if the queue contains no messages."""
        return self.depth == 0

    @property
    def is_full(self) -> bool:
        """True if the queue is at capacity."""
        self._evict_expired()
        return len(self._queue) >= self._max_depth

    def clear(self) -> None:
        """Remove all messages from the queue."""
        self._queue.clear()

    def _evict_expired(self) -> None:
        """Remove all expired messages from the front of the queue."""
        now_ms = int(time.time() * 1000)
        while self._queue and self._queue[0].is_expired(now_ms):
            self._queue.popleft()


# ---------------------------------------------------------------------------
# A2UIBridge
# ---------------------------------------------------------------------------

class A2UIBridge:
    """
    Communication bridge between the agent and the user interface.

    Every method requires canvas.a2ui.communicate scope.
    Input and confirmation requests additionally require canvas.a2ui.input.

    All messages are pushed to the internal A2UIChannel for consumption by the UI.
    All messages are logged to the audit trail if an audit_logger is provided.

    Usage:
        bridge = A2UIBridge(token, audit_logger=my_logger)
        bridge.send_status("Scanning page...", level="info")
        bridge.send_progress(current=3, total=10, label="Processing items")
        answer = bridge.request_input("Enter your name:", input_type="text")
        confirmed = bridge.request_confirmation("Delete post #42", risk="high")
        bridge.send_result(ActionResult(action="click", success=True))
    """

    def __init__(
        self,
        token,
        audit_logger: Optional[Callable[[Dict], None]] = None,
        channel: Optional[A2UIChannel] = None,
    ) -> None:
        """
        Initialize the bridge.

        Args:
            token:        AgencyToken with canvas.a2ui.communicate scope.
            audit_logger: Optional callable for logging messages to audit trail.
                          Called with the message dict on each send.
            channel:      Optional A2UIChannel (default: create a new one).

        Raises:
            ValueError: If token is None.
        """
        if token is None:
            raise ValueError("AgencyToken is required for A2UIBridge (fail-closed).")
        self._token = token
        self._audit_logger = audit_logger
        self._channel = channel if channel is not None else A2UIChannel()
        # Secondary channel for user→agent responses
        self._response_channel: A2UIChannel = A2UIChannel()

    # -------------------------------------------------------------------------
    # Agent → UI: outbound messages
    # -------------------------------------------------------------------------

    def send_status(self, message: str, level: str = "info") -> A2UIMessage:
        """
        Send a status update to the UI.

        Requires: canvas.a2ui.communicate scope.

        Level values: "info", "warning", "error", "success".

        Args:
            message: Human-readable status message.
            level:   Severity / style level.

        Returns:
            The A2UIMessage that was enqueued.

        Raises:
            PermissionError: If token lacks canvas.a2ui.communicate scope.
        """
        self._require_scope(SCOPE_A2UI_COMMUNICATE)
        msg = _make_message(
            message_type=MessageType.STATUS,
            payload={"message": message, "level": level},
            sender="agent",
            requires_response=False,
        )
        self._enqueue_and_log(msg)
        return msg

    def send_progress(
        self,
        current: int,
        total: int,
        label: str = "",
    ) -> A2UIMessage:
        """
        Send a progress bar update to the UI.

        Requires: canvas.a2ui.communicate scope.

        Args:
            current: Number of completed steps (0 <= current <= total).
            total:   Total number of steps.
            label:   Optional description of what is being processed.

        Returns:
            The A2UIMessage that was enqueued.

        Raises:
            PermissionError: If token lacks canvas.a2ui.communicate scope.
            ValueError:      If current < 0, total < 1, or current > total.
        """
        self._require_scope(SCOPE_A2UI_COMMUNICATE)
        if total < 1:
            raise ValueError(f"total must be >= 1, got {total}.")
        if current < 0:
            raise ValueError(f"current must be >= 0, got {current}.")
        if current > total:
            raise ValueError(f"current ({current}) must be <= total ({total}).")

        percent = (current * 100) // total   # int arithmetic, no float
        msg = _make_message(
            message_type=MessageType.PROGRESS,
            payload={
                "current": current,
                "total": total,
                "percent": percent,
                "label": label,
            },
            sender="agent",
            requires_response=False,
        )
        self._enqueue_and_log(msg)
        return msg

    def send_result(self, result: ActionResult) -> A2UIMessage:
        """
        Send a completed action result to the UI.

        Requires: canvas.a2ui.communicate scope.

        Args:
            result: ActionResult dataclass with action outcome.

        Returns:
            The A2UIMessage that was enqueued.

        Raises:
            PermissionError: If token lacks canvas.a2ui.communicate scope.
        """
        self._require_scope(SCOPE_A2UI_COMMUNICATE)
        msg = _make_message(
            message_type=MessageType.RESULT,
            payload={
                "action": result.action,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "evidence": result.evidence,
                "duration_ms": result.duration_ms,
            },
            sender="agent",
            requires_response=False,
        )
        self._enqueue_and_log(msg)
        return msg

    def send_error(self, error: str, detail: Optional[str] = None) -> A2UIMessage:
        """
        Send an error notification to the UI.

        Requires: canvas.a2ui.communicate scope.

        Args:
            error:  Short error code or message.
            detail: Optional detailed error explanation.

        Returns:
            The A2UIMessage that was enqueued.

        Raises:
            PermissionError: If token lacks canvas.a2ui.communicate scope.
        """
        self._require_scope(SCOPE_A2UI_COMMUNICATE)
        msg = _make_message(
            message_type=MessageType.ERROR,
            payload={"error": error, "detail": detail},
            sender="agent",
            requires_response=False,
        )
        self._enqueue_and_log(msg)
        return msg

    # -------------------------------------------------------------------------
    # Agent → UI: interactive requests (require canvas.a2ui.input)
    # -------------------------------------------------------------------------

    def request_input(
        self,
        prompt: str,
        input_type: str = "text",
        options: Optional[list] = None,
        timeout_seconds: int = INPUT_REQUEST_TIMEOUT_SECONDS,
    ) -> Optional[str]:
        """
        Request user input via the A2UI channel.

        Fail-closed: if no response is received within timeout_seconds (default 30),
        the request is auto-denied and None is returned.

        Requires: canvas.a2ui.communicate AND canvas.a2ui.input scopes.

        Args:
            prompt:          Human-readable input prompt.
            input_type:      Input widget hint: "text", "password", "select", "confirm".
            options:         For "select" inputs, list of allowed option strings.
            timeout_seconds: Seconds to wait for user response before auto-deny.

        Returns:
            User-provided string response, or None if timed out / denied.

        Raises:
            PermissionError: If token lacks required scopes.
        """
        self._require_scope(SCOPE_A2UI_COMMUNICATE)
        self._require_scope(SCOPE_A2UI_INPUT)

        msg = _make_message(
            message_type=MessageType.INPUT_REQUEST,
            payload={
                "prompt": prompt,
                "input_type": input_type,
                "options": options or [],
                "timeout_seconds": timeout_seconds,
            },
            sender="agent",
            requires_response=True,
            ttl_seconds=timeout_seconds,
        )
        self._enqueue_and_log(msg)

        # Wait for response (blocking poll — used in sync context)
        deadline_ms = int(time.time() * 1000) + timeout_seconds * 1000
        return self._wait_for_response(msg.message_id, deadline_ms)

    def request_confirmation(
        self,
        action: str,
        risk: str = "low",
        detail: Optional[str] = None,
        timeout_seconds: int = INPUT_REQUEST_TIMEOUT_SECONDS,
    ) -> bool:
        """
        Ask the user to confirm a planned action.

        Fail-closed rules:
          - If no response within timeout_seconds → deny (return False).
          - High-risk actions CANNOT auto-approve (auto-deny only).
          - Risk levels: "low", "medium", "high", "critical".

        Requires: canvas.a2ui.communicate AND canvas.a2ui.input scopes.

        Args:
            action:          Human-readable description of the action.
            risk:            Risk level: "low", "medium", "high", "critical".
            detail:          Optional additional context for the user.
            timeout_seconds: Seconds to wait for confirmation before auto-deny.

        Returns:
            True if user confirmed, False if denied or timed out.

        Raises:
            PermissionError: If token lacks required scopes.
        """
        self._require_scope(SCOPE_A2UI_COMMUNICATE)
        self._require_scope(SCOPE_A2UI_INPUT)

        if risk not in ("low", "medium", "high", "critical"):
            raise ValueError(
                f"Invalid risk '{risk}'. Must be one of: low, medium, high, critical."
            )

        msg = _make_message(
            message_type=MessageType.CONFIRMATION,
            payload={
                "action": action,
                "risk": risk,
                "detail": detail,
                "timeout_seconds": timeout_seconds,
                "auto_approve_allowed": risk not in ("high", "critical"),
            },
            sender="agent",
            requires_response=True,
            ttl_seconds=timeout_seconds,
        )
        self._enqueue_and_log(msg)

        # Wait for response
        deadline_ms = int(time.time() * 1000) + timeout_seconds * 1000
        response = self._wait_for_response(msg.message_id, deadline_ms)

        # Fail-closed: only "yes" / "true" / "confirm" counts as approval
        if response is None:
            return False  # timeout → deny
        return response.strip().lower() in ("yes", "true", "confirm", "approved", "ok")

    # -------------------------------------------------------------------------
    # UI → Agent: receive responses
    # -------------------------------------------------------------------------

    def receive_response(self, message_id: str, response_value: str) -> A2UIMessage:
        """
        Submit a user response for a pending input request or confirmation.

        Called by the UI layer when the user types or clicks a response.

        Args:
            message_id:     ID of the INPUT_REQUEST or CONFIRMATION message.
            response_value: User's response string.

        Returns:
            The response A2UIMessage that was enqueued on the response channel.
        """
        msg = _make_message(
            message_type=MessageType.STATUS,
            payload={
                "in_reply_to": message_id,
                "response": response_value,
            },
            sender="user",
            requires_response=False,
            ttl_seconds=MESSAGE_AUTO_EXPIRE_SECONDS,
        )
        self._response_channel.push(msg)
        return msg

    # -------------------------------------------------------------------------
    # Channel access
    # -------------------------------------------------------------------------

    def pop_message(self) -> Optional[A2UIMessage]:
        """
        Pop the next agent→UI message from the outbound channel.

        Returns:
            A2UIMessage or None if the channel is empty.
        """
        return self._channel.pop()

    def peek_message(self) -> Optional[A2UIMessage]:
        """
        Peek at the next agent→UI message without removing it.

        Returns:
            A2UIMessage or None if the channel is empty.
        """
        return self._channel.peek()

    def pop_all_messages(self) -> list:
        """
        Pop all pending agent→UI messages in FIFO order.

        Returns:
            List of A2UIMessage (may be empty).
        """
        return self._channel.pop_all()

    @property
    def channel(self) -> A2UIChannel:
        """Direct access to the outbound message channel."""
        return self._channel

    @property
    def pending_count(self) -> int:
        """Number of pending outbound messages."""
        return self._channel.depth

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _require_scope(self, scope: str) -> None:
        """
        Assert that the token grants the required scope.

        Fail-closed: raises PermissionError if scope is absent.

        Args:
            scope: Required OAuth3 scope string.

        Raises:
            PermissionError: If the token does not contain `scope`.
        """
        if not self._token.has_scope(scope):
            raise PermissionError(
                f"OAuth3 scope required: '{scope}'. "
                f"Token scopes: {list(self._token.scopes)}"
            )

    def _enqueue_and_log(self, msg: A2UIMessage) -> None:
        """
        Push the message to the outbound channel and log it to the audit trail.

        Args:
            msg: A2UIMessage to enqueue.
        """
        self._channel.push(msg)
        if self._audit_logger is not None:
            try:
                self._audit_logger({
                    "event": "a2ui_message",
                    "message_id": msg.message_id,
                    "message_type": msg.message_type.value,
                    "sender": msg.sender,
                    "timestamp": msg.timestamp,
                    "requires_response": msg.requires_response,
                    "payload_keys": list(msg.payload.keys()),
                })
            except Exception:
                pass  # Audit log failure must never block the operation

    def _wait_for_response(
        self,
        message_id: str,
        deadline_ms: int,
    ) -> Optional[str]:
        """
        Poll the response channel for a reply to the given message_id.

        In the synchronous test model the response must be submitted via
        receive_response() before this call (or no response = timeout = None).

        In a real async runtime, this would be replaced by an asyncio.wait_for().

        Args:
            message_id:  The originating message ID to match a response against.
            deadline_ms: Absolute deadline in milliseconds since epoch.

        Returns:
            Response string, or None if no matching response found before deadline.
        """
        now_ms = int(time.time() * 1000)
        # Fast path: check current response channel contents without sleeping
        # (suitable for synchronous tests; async callers should use async bridge)
        all_responses = list(self._response_channel._queue)
        for resp_msg in all_responses:
            in_reply_to = resp_msg.payload.get("in_reply_to")
            if in_reply_to == message_id and now_ms < deadline_ms:
                # Consume it
                try:
                    self._response_channel._queue.remove(resp_msg)
                except ValueError:
                    pass
                return resp_msg.payload.get("response")
        # No matching response found → fail-closed (None = deny)
        return None
