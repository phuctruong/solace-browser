"""
voice/talk.py — Talk Mode: Voice-to-Action Pipeline

Handles the full pipeline from speech utterance to recipe execution:
  1. Activate talk mode (after wake word)
  2. Receive transcribed utterance
  3. Parse utterance into VoiceAction (IntentParser)
  4. Enforce OAuth3 scope for the target action
  5. Request confirmation if action is destructive or confidence is low
  6. Execute via recipe system (pluggable RecipeExecutor)
  7. Log to audit trail (text only, no audio)
  8. Auto-deactivate after 60 seconds of silence

OAuth3 scope requirements:
  voice.talk.command  — required for all voice commands
  target recipe scope — additionally required per action (e.g. gmail.send.email)

Step-up auth required for destructive actions (delete, send, archive, financial).

All voice commands are logged to audit trail (text only).
No raw audio is ever stored or transmitted.

Rung: 641
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from oauth3.token import AgencyToken
from oauth3.enforcement import enforce_oauth3

# Ensure voice scopes are registered
import voice.scopes as _voice_scopes  # noqa: F401 (side-effect: registration)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TALK_SCOPE_COMMAND = "voice.talk.command"

# Confidence thresholds
AUTO_EXECUTE_THRESHOLD = 0.7     # >= this → auto-execute
CONFIRM_THRESHOLD = 0.0          # >= this (but < AUTO_EXECUTE_THRESHOLD) → ask user
REJECT_THRESHOLD = 0.0           # < CONFIRM_THRESHOLD → reject (currently same)

# Talk mode auto-deactivation after silence
SILENCE_TIMEOUT_SECONDS: int = 60

# Destructive intents that always require confirmation regardless of confidence
_DESTRUCTIVE_INTENTS = frozenset({
    "gmail-delete-email",
    "gmail-send-email",
    "gmail-archive-email",
    "linkedin-delete-post",
    "linkedin-send-message",
    "reddit-delete-post",
    "reddit-post-text",
    "github-merge-pr",
    "github-delete-branch",
})

# Financial actions require confirmation
_FINANCIAL_INTENTS = frozenset({
    "payment-send",
    "payment-confirm",
})

_ALL_CONFIRM_REQUIRED = _DESTRUCTIVE_INTENTS | _FINANCIAL_INTENTS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VoiceAction — parsed intent + routing info
# ---------------------------------------------------------------------------

@dataclass
class VoiceAction:
    """
    Parsed voice command ready for execution.

    Attributes:
        intent:                  Recipe name / action identifier.
                                 e.g. "gmail-read-inbox", "gmail-send-email".
        platform:                Target platform (e.g. "gmail", "linkedin").
        parameters:              Key-value parameters extracted from utterance.
        confidence:              Parser confidence in [0.0, 1.0].
        requires_confirmation:   True if user must explicitly confirm before execution.
        required_scopes:         OAuth3 scopes the action needs (including voice scope).
        utterance:               Original spoken text (for audit log).
    """

    intent: str
    platform: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    requires_confirmation: bool = False
    required_scopes: List[str] = field(default_factory=list)
    utterance: str = ""

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not isinstance(self.intent, str) or not self.intent.strip():
            raise ValueError("VoiceAction.intent must be a non-empty string.")
        if not isinstance(self.platform, str) or not self.platform.strip():
            raise ValueError("VoiceAction.platform must be a non-empty string.")
        if not isinstance(self.confidence, (int, float)):
            raise TypeError("VoiceAction.confidence must be numeric.")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                f"VoiceAction.confidence must be in [0.0, 1.0], got {self.confidence}."
            )
        if not isinstance(self.parameters, dict):
            raise TypeError("VoiceAction.parameters must be a dict.")
        if not isinstance(self.required_scopes, list):
            raise TypeError("VoiceAction.required_scopes must be a list.")

    @property
    def is_destructive(self) -> bool:
        """True if this intent is in the destructive/financial confirmation set."""
        return self.intent in _ALL_CONFIRM_REQUIRED

    @property
    def will_auto_execute(self) -> bool:
        """
        True if the action will execute without user confirmation.

        Auto-execute requires: confidence >= threshold AND not destructive.
        """
        return (
            float(self.confidence) >= AUTO_EXECUTE_THRESHOLD
            and not self.requires_confirmation
        )


# ---------------------------------------------------------------------------
# ActionResult — outcome of executing a VoiceAction
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """
    Result of executing a VoiceAction via the recipe system.

    Attributes:
        success:          True if the action completed without error.
        action:           The VoiceAction that was executed.
        output:           Human-readable result string (for TTS or UI).
        error:            Error message if success=False, else empty string.
        confirmation_required: True if the action was not executed and needs
                               user confirmation first.
        audit_entry:      Dict written to the audit log.
    """

    success: bool
    action: VoiceAction
    output: str = ""
    error: str = ""
    confirmation_required: bool = False
    audit_entry: Dict[str, Any] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        """True if the action was blocked (not executed at all)."""
        return not self.success and not self.confirmation_required

    @property
    def pending_confirmation(self) -> bool:
        """True if execution is deferred pending user confirmation."""
        return self.confirmation_required


# ---------------------------------------------------------------------------
# Intent → recipe mapping table
# ---------------------------------------------------------------------------

# Pattern: (intent_phrase_fragment, intent_id, platform, required_scope)
# Phrases are matched case-insensitively as substrings of the utterance.
_INTENT_PATTERNS: List[Tuple[str, str, str, str]] = [

    # Gmail
    ("read my email",       "gmail-read-inbox",    "gmail",    "gmail.read.inbox"),
    ("read my emails",      "gmail-read-inbox",    "gmail",    "gmail.read.inbox"),
    ("check my email",      "gmail-read-inbox",    "gmail",    "gmail.read.inbox"),
    ("check my inbox",      "gmail-read-inbox",    "gmail",    "gmail.read.inbox"),
    ("open gmail",          "gmail-read-inbox",    "gmail",    "gmail.read.inbox"),
    ("search email",        "gmail-search",        "gmail",    "gmail.search.messages"),
    ("search my email",     "gmail-search",        "gmail",    "gmail.search.messages"),
    ("send email",          "gmail-send-email",    "gmail",    "gmail.send.email"),
    ("send an email",       "gmail-send-email",    "gmail",    "gmail.send.email"),
    ("delete email",        "gmail-delete-email",  "gmail",    "gmail.delete.email"),
    ("delete this email",   "gmail-delete-email",  "gmail",    "gmail.delete.email"),
    ("archive email",       "gmail-archive-email", "gmail",    "gmail.label.apply"),
    ("create draft",        "gmail-create-draft",  "gmail",    "gmail.draft.create"),
    ("write a draft",       "gmail-create-draft",  "gmail",    "gmail.draft.create"),

    # LinkedIn
    ("read linkedin",       "linkedin-read-feed",     "linkedin", "linkedin.read.feed"),
    ("check linkedin",      "linkedin-read-feed",     "linkedin", "linkedin.read.feed"),
    ("linkedin messages",   "linkedin-read-messages", "linkedin", "linkedin.read.messages"),
    ("linkedin inbox",      "linkedin-read-messages", "linkedin", "linkedin.read.messages"),
    ("post on linkedin",    "linkedin-post-text",     "linkedin", "linkedin.post.text"),
    ("delete linkedin",     "linkedin-delete-post",   "linkedin", "linkedin.delete.post"),
    ("send linkedin",       "linkedin-send-message",  "linkedin", "linkedin.send.message"),

    # Reddit
    ("read reddit",         "reddit-read-feed",  "reddit", "reddit.read.feed"),
    ("check reddit",        "reddit-read-feed",  "reddit", "reddit.read.feed"),
    ("post on reddit",      "reddit-post-text",  "reddit", "reddit.post.text"),
    ("delete reddit post",  "reddit-delete-post","reddit", "reddit.delete.post"),

    # GitHub
    ("read github",         "github-read-issues",  "github", "github.read.issues"),
    ("check github",        "github-read-issues",  "github", "github.read.issues"),
    ("github issues",       "github-read-issues",  "github", "github.read.issues"),
    ("merge pull request",  "github-merge-pr",     "github", "github.merge.pr"),
    ("delete branch",       "github-delete-branch","github", "github.delete.branch"),

    # HackerNews
    ("read hacker news",    "hackernews-read",  "hackernews", "hackernews.read.feed"),
    ("check hacker news",   "hackernews-read",  "hackernews", "hackernews.read.feed"),
    ("open hacker news",    "hackernews-read",  "hackernews", "hackernews.read.feed"),
]


# ---------------------------------------------------------------------------
# IntentParser
# ---------------------------------------------------------------------------

class IntentParser:
    """
    Maps spoken natural-language utterances to VoiceAction objects.

    Matching algorithm:
      1. Normalize utterance (lowercase, strip).
      2. Find all pattern phrases that are substrings of the normalized text.
      3. Pick the longest / most specific match (most words in phrase).
      4. Compute confidence based on match specificity + uniqueness.
      5. If multiple equally-specific matches exist → ambiguous → low confidence.
      6. If no match → unknown intent with confidence=0.0.

    Confidence scoring:
      - Exact single match:               0.90
      - Single match (substring):         0.75
      - Multiple matches, one dominant:   0.70
      - Multiple equally-specific matches: 0.45 (ambiguous)
      - No match:                         0.0
    """

    def __init__(
        self,
        custom_patterns: Optional[List[Tuple[str, str, str, str]]] = None,
    ) -> None:
        """
        Initialize with default patterns plus any custom additions.

        Args:
            custom_patterns: List of (phrase, intent_id, platform, scope) tuples
                             to add to the built-in patterns.
        """
        self._patterns = list(_INTENT_PATTERNS)
        if custom_patterns:
            self._patterns.extend(custom_patterns)

    def parse(self, utterance: str) -> VoiceAction:
        """
        Parse a spoken utterance into a VoiceAction.

        Args:
            utterance: Raw transcribed text from voice input.

        Returns:
            VoiceAction with intent, platform, confidence, required_scopes.
            For unknown/ambiguous utterances, intent="unknown", confidence < 0.7.
        """
        if not utterance or not utterance.strip():
            return self._unknown_action(utterance, confidence=0.0)

        normalized = utterance.strip().lower()

        # Find all matching patterns
        matches: List[Tuple[str, str, str, str]] = []
        for phrase, intent_id, platform, scope in self._patterns:
            if phrase.lower() in normalized:
                matches.append((phrase, intent_id, platform, scope))

        if not matches:
            return self._unknown_action(utterance, confidence=0.0)

        # Pick the most specific match (longest phrase)
        matches.sort(key=lambda m: len(m[0]), reverse=True)
        best = matches[0]
        best_len = len(best[0])

        # Check for ambiguity: multiple matches with the same phrase length
        top_matches = [m for m in matches if len(m[0]) == best_len]

        if len(top_matches) > 1:
            # Multiple equally-specific matches → ambiguous
            # Use the first one but signal low confidence
            phrase, intent_id, platform, scope = top_matches[0]
            confidence = 0.45
        elif len(matches) == 1:
            # Single unique match
            phrase, intent_id, platform, scope = best
            # Higher confidence if the utterance is mostly the phrase
            ratio = len(phrase) / max(len(normalized), 1)
            confidence = 0.90 if ratio >= 0.8 else 0.75
        else:
            # Single best match (longer than others)
            phrase, intent_id, platform, scope = best
            confidence = 0.70

        requires_confirmation = (
            intent_id in _ALL_CONFIRM_REQUIRED
            or confidence < AUTO_EXECUTE_THRESHOLD
        )

        return VoiceAction(
            intent=intent_id,
            platform=platform,
            parameters={},
            confidence=confidence,
            requires_confirmation=requires_confirmation,
            required_scopes=[TALK_SCOPE_COMMAND, scope],
            utterance=utterance,
        )

    # ------------------------------------------------------------------

    def _unknown_action(self, utterance: str, confidence: float) -> VoiceAction:
        return VoiceAction(
            intent="unknown",
            platform="unknown",
            parameters={},
            confidence=confidence,
            requires_confirmation=True,
            required_scopes=[TALK_SCOPE_COMMAND],
            utterance=utterance,
        )


# ---------------------------------------------------------------------------
# RecipeExecutor — pluggable execution backend (dependency injection)
# ---------------------------------------------------------------------------

class RecipeExecutor:
    """
    Abstract recipe execution interface.

    Subclass to connect TalkMode to the real recipe replay engine.
    The default implementation is a safe no-op stub.
    """

    def execute(
        self,
        intent: str,
        platform: str,
        parameters: Dict[str, Any],
        token: Optional[AgencyToken],
    ) -> Tuple[bool, str]:
        """
        Execute a recipe action.

        Args:
            intent:     Recipe name / action identifier.
            platform:   Target platform.
            parameters: Action parameters from IntentParser.
            token:      OAuth3 agency token (for scope enforcement inside executor).

        Returns:
            (success: bool, output: str)
        """
        return False, "RecipeExecutor.execute() not implemented."


class NoOpRecipeExecutor(RecipeExecutor):
    """Safe stub that always returns success=True for testing."""

    def execute(
        self,
        intent: str,
        platform: str,
        parameters: Dict[str, Any],
        token: Optional[AgencyToken],
    ) -> Tuple[bool, str]:
        return True, f"Executed: {intent} on {platform}"


# ---------------------------------------------------------------------------
# TalkMode — main voice interaction handler
# ---------------------------------------------------------------------------

class TalkMode:
    """
    Voice interaction handler: speech utterance → intent → recipe execution.

    Lifecycle:
      1. activate()           — enter talk mode; starts silence timer
      2. process_utterance()  — parse speech into VoiceAction
      3. execute_action()     — enforce OAuth3, confirm if needed, execute
      4. deactivate()         — exit talk mode (or auto-deactivated on silence)

    OAuth3:
      voice.talk.command      — required for all voice commands
      target recipe scope     — additionally required per action

    Security:
      - All voice commands logged to audit trail (text only, no audio)
      - Destructive actions require explicit confirmation
      - Auto-deactivates after SILENCE_TIMEOUT_SECONDS of inactivity
    """

    def __init__(
        self,
        token: Optional[AgencyToken] = None,
        parser: Optional[IntentParser] = None,
        executor: Optional[RecipeExecutor] = None,
        silence_timeout: int = SILENCE_TIMEOUT_SECONDS,
        confirmation_callback: Optional[Callable[[VoiceAction], bool]] = None,
    ) -> None:
        """
        Create a TalkMode instance.

        Args:
            token:                 OAuth3 agency token.
            parser:                IntentParser instance (default: IntentParser()).
            executor:              RecipeExecutor instance (default: NoOpRecipeExecutor()).
            silence_timeout:       Seconds of silence before auto-deactivation (default 60).
            confirmation_callback: Called when confirmation is needed. Returns True to
                                   proceed, False to cancel. If None, always cancels
                                   (safe default — callers must supply their own).
        """
        self._token = token
        self._parser = parser or IntentParser()
        self._executor = executor or NoOpRecipeExecutor()
        self._silence_timeout = silence_timeout
        self._confirmation_callback = confirmation_callback

        self._active = False
        self._last_utterance_time: Optional[float] = None
        self._audit_log: List[dict] = []

    # ------------------------------------------------------------------
    # Lifecycle

    def activate(self) -> None:
        """
        Enter talk mode.

        OAuth3 gate: voice.talk.command must be in token scopes.

        Raises:
            PermissionError: If OAuth3 gate fails.
            RuntimeError:    If already active.
        """
        if self._active:
            raise RuntimeError("TalkMode is already active.")

        # Gate — voice.talk.command (low-risk scope, no step-up required)
        self._enforce_scope(TALK_SCOPE_COMMAND, step_up_confirmed=False)

        self._active = True
        self._last_utterance_time = time.monotonic()
        self._log_audit("talk_mode_activated", utterance="", intent="", success=True)

    def deactivate(self) -> None:
        """
        Exit talk mode.

        Safe to call even when not active (no-op).
        """
        if not self._active:
            return
        self._active = False
        self._last_utterance_time = None
        self._log_audit("talk_mode_deactivated", utterance="", intent="", success=True)

    @property
    def is_active(self) -> bool:
        """Return True if talk mode is currently active."""
        return self._active

    def check_silence_timeout(self) -> bool:
        """
        Check whether the silence timeout has been exceeded.

        If exceeded, auto-deactivates and returns True.

        Returns:
            True if auto-deactivated due to silence, False otherwise.
        """
        if not self._active:
            return False
        if self._last_utterance_time is None:
            return False
        elapsed = time.monotonic() - self._last_utterance_time
        if elapsed >= self._silence_timeout:
            self._log_audit(
                "talk_mode_silence_timeout",
                utterance="",
                intent="",
                success=True,
            )
            self._active = False
            return True
        return False

    # ------------------------------------------------------------------
    # Utterance processing

    def process_utterance(self, text: str) -> VoiceAction:
        """
        Parse a spoken utterance into a VoiceAction.

        Updates last-utterance timestamp to reset silence timer.

        Args:
            text: Transcribed utterance text.

        Returns:
            VoiceAction with intent, confidence, required_scopes, etc.

        Raises:
            RuntimeError: If talk mode is not active.
        """
        if not self._active:
            raise RuntimeError(
                "TalkMode.process_utterance() called but talk mode is not active. "
                "Call activate() first."
            )

        # Reset silence timer
        self._last_utterance_time = time.monotonic()

        action = self._parser.parse(text)
        return action

    # ------------------------------------------------------------------
    # Action execution

    def execute_action(self, action: VoiceAction) -> ActionResult:
        """
        Enforce OAuth3 and execute a VoiceAction via the recipe system.

        Pipeline:
          1. Validate talk mode is active.
          2. OAuth3 gate: voice.talk.command + target scope.
          3. Confidence check: below 0.7 → requires_confirmation = True.
          4. Destructive/financial intent → requires_confirmation = True.
          5. If confirmation needed: invoke confirmation_callback.
             - None callback or callback returns False → blocked.
          6. Execute via RecipeExecutor.
          7. Log to audit trail (text only).

        Args:
            action: VoiceAction from process_utterance().

        Returns:
            ActionResult with success flag, output, and audit entry.
        """
        if not self._active:
            return ActionResult(
                success=False,
                action=action,
                error="TalkMode is not active.",
            )

        # OAuth3 gate for voice.talk.command
        try:
            self._enforce_scope(TALK_SCOPE_COMMAND, step_up_confirmed=False)
        except PermissionError as exc:
            result = ActionResult(
                success=False,
                action=action,
                error=str(exc),
            )
            self._log_audit(
                "action_blocked_oauth3",
                utterance=action.utterance,
                intent=action.intent,
                success=False,
                error=str(exc),
            )
            return result

        # Confirmation gate (checked BEFORE scope enforcement for destructive actions).
        #
        # Rationale: For destructive intents (send, delete, etc.) the target recipe
        # scope is high-risk, which means enforce_oauth3() would block with
        # "step_up_required" when step_up_confirmed=False.  The voice layer's
        # user-confirmation dialog IS the step-up mechanism — when the user says
        # "yes", we treat that as step-up confirmed and pass step_up_confirmed=True
        # to the scope enforcement below.
        #
        # If confirmation is denied (or no callback), we return pending_confirmation
        # BEFORE attempting scope enforcement.
        user_confirmed = False
        if action.requires_confirmation or action.is_destructive:
            if not self._request_confirmation(action):
                result = ActionResult(
                    success=False,
                    action=action,
                    confirmation_required=True,
                    output="Action requires confirmation.",
                )
                self._log_audit(
                    "action_pending_confirmation",
                    utterance=action.utterance,
                    intent=action.intent,
                    success=False,
                )
                return result
            user_confirmed = True

        # OAuth3 gate for target recipe scope (if distinct from voice scope).
        # For destructive/high-risk scopes, use step_up_confirmed=user_confirmed
        # so that voice-layer confirmation satisfies the step-up requirement.
        for scope in action.required_scopes:
            if scope == TALK_SCOPE_COMMAND:
                continue  # Already checked above
            try:
                self._enforce_scope(scope, step_up_confirmed=user_confirmed)
            except PermissionError as exc:
                result = ActionResult(
                    success=False,
                    action=action,
                    error=str(exc),
                )
                self._log_audit(
                    "action_blocked_scope",
                    utterance=action.utterance,
                    intent=action.intent,
                    success=False,
                    error=str(exc),
                )
                return result

        # Execute
        success, output = self._executor.execute(
            intent=action.intent,
            platform=action.platform,
            parameters=action.parameters,
            token=self._token,
        )

        error = "" if success else output
        if not success:
            output = ""

        audit_entry = self._log_audit(
            "action_executed",
            utterance=action.utterance,
            intent=action.intent,
            success=success,
            error=error,
        )

        return ActionResult(
            success=success,
            action=action,
            output=output,
            error=error,
            audit_entry=audit_entry,
        )

    # ------------------------------------------------------------------
    # Introspection

    @property
    def audit_log(self) -> List[dict]:
        """Read-only list of audit log entries (text only, no audio)."""
        return list(self._audit_log)

    # ------------------------------------------------------------------
    # Internal

    def _enforce_scope(
        self,
        scope: str,
        step_up_confirmed: bool = False,
    ) -> None:
        """
        Run OAuth3 enforcement gate for scope.

        Raises:
            PermissionError: If gate fails.
        """
        if self._token is None:
            raise PermissionError(
                f"OAuth3 scope '{scope}' required but no token provided."
            )
        passed, details = enforce_oauth3(
            self._token,
            required_scope=scope,
            step_up_confirmed=step_up_confirmed,
        )
        if not passed:
            error = details.get("error", "unknown_error")
            raise PermissionError(
                f"OAuth3 gate denied for scope '{scope}': {error}."
            )

    def _request_confirmation(self, action: VoiceAction) -> bool:
        """
        Invoke the confirmation_callback.

        Returns True to proceed, False to cancel.
        Default (no callback): always cancel (fail-closed).
        """
        if self._confirmation_callback is None:
            return False
        try:
            return bool(self._confirmation_callback(action))
        except (RuntimeError, TypeError, ValueError) as exc:
            logger.warning("Voice confirmation callback failed for %s: %s", action.intent, exc)
            return False

    def _log_audit(
        self,
        event: str,
        utterance: str,
        intent: str,
        success: bool,
        error: str = "",
    ) -> dict:
        """Append a text-only entry to the audit log and return it."""
        entry: dict = {
            "event": event,
            "utterance": utterance,
            "intent": intent,
            "success": success,
            "timestamp": time.time(),
        }
        if error:
            entry["error"] = error
        self._audit_log.append(entry)
        return entry
