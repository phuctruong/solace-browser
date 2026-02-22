"""
tests/test_voice.py — Voice Module Test Suite

Coverage:
  1.  WakeConfig              — validation, defaults, bounds
  2.  AudioBuffer             — append, size, clear, purge, thread-safety
  3.  WakeWordDetector        — lifecycle (start/stop), callback registration,
                                OAuth3 scope enforcement, buffer limits, auto-purge
  4.  TalkMode                — activate/deactivate lifecycle, OAuth3 enforcement,
                                utterance processing, action execution, auto-deactivate,
                                audit logging
  5.  IntentParser            — natural-language → recipe mapping, unknown commands,
                                ambiguous commands, confidence scoring
  6.  VoiceAction             — dataclass validation, confirmation requirements
  7.  ActionResult            — success/error states, pending_confirmation property
  8.  OAuth3 integration      — scope requirements, step-up for always_on,
                                destructive actions, expired/revoked tokens
  9.  Security                — no raw audio storage, buffer size limits,
                                auto-purge verification
  10. Scopes                  — voice scope registry contents, step-up flags,
                                registration into main oauth3 registry

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_voice.py -v -p no:httpbin

Rung: 641 (local correctness)
"""

from __future__ import annotations

import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# ── OAuth3 imports ──────────────────────────────────────────────────────────
from oauth3.token import AgencyToken
from oauth3.scopes import SCOPE_REGISTRY
import oauth3.scopes as _oauth3_scopes

# ── Voice imports ───────────────────────────────────────────────────────────
from voice.scopes import (
    VOICE_SCOPE_REGISTRY,
    VOICE_SCOPES,
    VOICE_STEP_UP_SCOPES,
    VOICE_HIGH_RISK_SCOPES,
    register_voice_scopes,
    is_voice_scope,
    voice_scope_requires_step_up,
    get_voice_scope_description,
    get_required_scopes_for_action,
)
from voice.wake import (
    WakeWordDetector,
    WakeConfig,
    AudioBuffer,
    AudioBackend,
    NoOpAudioBackend,
    WAKE_SCOPE_LISTEN,
    WAKE_SCOPE_ALWAYS_ON,
    MAX_BUFFER_SECONDS,
    DEFAULT_WAKE_WORD,
    SENSITIVITY_MIN,
    SENSITIVITY_MAX,
)
from voice.talk import (
    TalkMode,
    IntentParser,
    VoiceAction,
    ActionResult,
    RecipeExecutor,
    NoOpRecipeExecutor,
    TALK_SCOPE_COMMAND,
    AUTO_EXECUTE_THRESHOLD,
    SILENCE_TIMEOUT_SECONDS,
    _DESTRUCTIVE_INTENTS,
    _ALL_CONFIRM_REQUIRED,
)


# ===========================================================================
# Helpers / Fixtures
# ===========================================================================

def _make_token(
    scopes: List[str],
    *,
    expired: bool = False,
    revoked: bool = False,
) -> AgencyToken:
    """Create a test AgencyToken with the given scopes."""
    import dataclasses
    from datetime import datetime, timezone, timedelta

    # Ensure all scopes are registered (voice scopes auto-register on import,
    # but run again to be safe in case of import ordering)
    register_voice_scopes()

    ttl = -60 if expired else 3600

    token = AgencyToken.create(
        issuer="https://test.solaceagi.com",
        subject="test-user@example.com",
        scopes=scopes,
        intent="test delegation",
        ttl_seconds=abs(ttl),
    )

    if expired:
        # Patch expires_at to the past using dataclasses.replace
        past = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        token = dataclasses.replace(token, expires_at=past)

    if revoked:
        token = token.revoke()

    return token


class ScriptedAudioBackend(AudioBackend):
    """
    Test double: emits pre-scripted audio chunks then becomes silent.

    chunks: list of bytes or str. str chunks are returned as is for transcription.
    """

    def __init__(self, chunks: List[Any]) -> None:
        self._chunks = list(chunks)
        self._index = 0
        self._running = False
        self._transcriptions: Dict[bytes, str] = {}

    def add_transcription(self, audio: bytes, text: str) -> None:
        """Register what transcribe() returns for a given raw chunk."""
        self._transcriptions[audio] = text

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def read_chunk(self) -> Optional[bytes]:
        if self._index >= len(self._chunks):
            return None
        chunk = self._chunks[self._index]
        self._index += 1
        if isinstance(chunk, str):
            return chunk.encode("utf-8")
        return chunk

    def transcribe(self, audio_bytes: bytes) -> str:
        text = audio_bytes.decode("utf-8", errors="replace")
        return self._transcriptions.get(audio_bytes, text)


class SucceedingExecutor(RecipeExecutor):
    """Always succeeds, records calls."""

    def __init__(self) -> None:
        self.calls: List[dict] = []

    def execute(self, intent, platform, parameters, token):
        self.calls.append({"intent": intent, "platform": platform, "parameters": parameters})
        return True, f"ok:{intent}"


class FailingExecutor(RecipeExecutor):
    """Always fails."""

    def execute(self, intent, platform, parameters, token):
        return False, "executor-error"


# ===========================================================================
# 1. Voice Scopes
# ===========================================================================

class TestVoiceScopes:

    def test_registry_has_all_six_scopes(self):
        assert "voice.wake.listen" in VOICE_SCOPE_REGISTRY
        assert "voice.wake.always_on" in VOICE_SCOPE_REGISTRY
        assert "voice.talk.command" in VOICE_SCOPE_REGISTRY
        assert "voice.talk.dictate" in VOICE_SCOPE_REGISTRY
        assert "voice.tts.speak" in VOICE_SCOPE_REGISTRY
        assert "voice.tts.persona" in VOICE_SCOPE_REGISTRY

    def test_voice_scopes_frozenset_size(self):
        assert len(VOICE_SCOPES) == 6

    def test_step_up_scopes_are_always_on_and_persona(self):
        assert "voice.wake.always_on" in VOICE_STEP_UP_SCOPES
        assert "voice.tts.persona" in VOICE_STEP_UP_SCOPES
        # Non-step-up scopes must NOT be in the set
        assert "voice.wake.listen" not in VOICE_STEP_UP_SCOPES
        assert "voice.talk.command" not in VOICE_STEP_UP_SCOPES
        assert "voice.talk.dictate" not in VOICE_STEP_UP_SCOPES
        assert "voice.tts.speak" not in VOICE_STEP_UP_SCOPES

    def test_high_risk_scopes_match_step_up(self):
        # High-risk ↔ step-up required
        assert VOICE_HIGH_RISK_SCOPES == VOICE_STEP_UP_SCOPES

    def test_is_voice_scope_true_for_known(self):
        for scope in VOICE_SCOPES:
            assert is_voice_scope(scope) is True

    def test_is_voice_scope_false_for_unknown(self):
        assert is_voice_scope("gmail.read.inbox") is False
        assert is_voice_scope("unknown.scope.here") is False

    def test_voice_scope_requires_step_up_true_for_high_risk(self):
        assert voice_scope_requires_step_up("voice.wake.always_on") is True
        assert voice_scope_requires_step_up("voice.tts.persona") is True

    def test_voice_scope_requires_step_up_false_for_low_risk(self):
        assert voice_scope_requires_step_up("voice.wake.listen") is False
        assert voice_scope_requires_step_up("voice.talk.command") is False
        assert voice_scope_requires_step_up("voice.tts.speak") is False

    def test_voice_scope_requires_step_up_fail_closed_unknown(self):
        # Unknown scope → fail-closed → True
        assert voice_scope_requires_step_up("unknown.scope.xyz") is True

    def test_get_voice_scope_description_returns_string(self):
        desc = get_voice_scope_description("voice.wake.listen")
        assert isinstance(desc, str) and len(desc) > 0

    def test_get_voice_scope_description_none_for_unknown(self):
        assert get_voice_scope_description("not.a.scope") is None

    def test_register_voice_scopes_adds_to_main_registry(self):
        register_voice_scopes()
        for scope in VOICE_SCOPES:
            assert scope in SCOPE_REGISTRY, f"{scope} missing from SCOPE_REGISTRY"

    def test_register_voice_scopes_idempotent(self):
        register_voice_scopes()
        register_voice_scopes()
        # No duplicate errors; count stable
        count_before = len(SCOPE_REGISTRY)
        register_voice_scopes()
        assert len(SCOPE_REGISTRY) == count_before

    def test_get_required_scopes_for_wake_listen(self):
        assert get_required_scopes_for_action("wake_listen") == ["voice.wake.listen"]

    def test_get_required_scopes_for_wake_always(self):
        scopes = get_required_scopes_for_action("wake_always")
        assert "voice.wake.listen" in scopes
        assert "voice.wake.always_on" in scopes

    def test_get_required_scopes_unknown_returns_empty(self):
        assert get_required_scopes_for_action("nonexistent_action") == []

    def test_voice_scopes_have_triple_segment_format(self):
        import re
        pattern = re.compile(r"^[a-z][a-z0-9_-]+[.][a-z][a-z0-9_-]+[.][a-z][a-z0-9_-]+$")
        for scope in VOICE_SCOPES:
            assert pattern.match(scope), f"Scope '{scope}' not triple-segment format"

    def test_platform_field_is_voice_for_all(self):
        for scope, meta in VOICE_SCOPE_REGISTRY.items():
            assert meta["platform"] == "voice", f"{scope} has platform {meta['platform']}"


# ===========================================================================
# 2. WakeConfig
# ===========================================================================

class TestWakeConfig:

    def test_defaults(self):
        cfg = WakeConfig()
        assert cfg.wake_word == DEFAULT_WAKE_WORD
        assert cfg.sensitivity == 0.5
        assert cfg.timeout_seconds == 60
        assert cfg.language == "en-US"
        assert cfg.always_on is False

    def test_custom_values(self):
        cfg = WakeConfig(
            wake_word="hey solace",
            sensitivity=0.8,
            timeout_seconds=30,
            language="fr-FR",
            always_on=False,
        )
        assert cfg.wake_word == "hey solace"
        assert cfg.sensitivity == 0.8
        assert cfg.timeout_seconds == 30
        assert cfg.language == "fr-FR"

    def test_empty_wake_word_raises(self):
        with pytest.raises(ValueError, match="wake_word"):
            WakeConfig(wake_word="")

    def test_whitespace_wake_word_raises(self):
        with pytest.raises(ValueError, match="wake_word"):
            WakeConfig(wake_word="   ")

    def test_sensitivity_below_zero_raises(self):
        with pytest.raises(ValueError, match="sensitivity"):
            WakeConfig(sensitivity=-0.1)

    def test_sensitivity_above_one_raises(self):
        with pytest.raises(ValueError, match="sensitivity"):
            WakeConfig(sensitivity=1.1)

    def test_sensitivity_at_bounds_ok(self):
        cfg_low = WakeConfig(sensitivity=SENSITIVITY_MIN)
        cfg_high = WakeConfig(sensitivity=SENSITIVITY_MAX)
        assert cfg_low.sensitivity == 0.0
        assert cfg_high.sensitivity == 1.0

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_seconds"):
            WakeConfig(timeout_seconds=-1)

    def test_zero_timeout_is_valid(self):
        cfg = WakeConfig(timeout_seconds=0)
        assert cfg.timeout_seconds == 0

    def test_empty_language_raises(self):
        with pytest.raises(ValueError, match="language"):
            WakeConfig(language="")


# ===========================================================================
# 3. AudioBuffer
# ===========================================================================

class TestAudioBuffer:

    def test_starts_empty(self):
        buf = AudioBuffer()
        assert buf.size() == 0
        assert buf.total_bytes() == 0

    def test_append_increments_size(self):
        buf = AudioBuffer()
        buf.append(b"hello")
        assert buf.size() == 1
        assert buf.total_bytes() == 5

    def test_clear_removes_all(self):
        buf = AudioBuffer()
        buf.append(b"audio1")
        buf.append(b"audio2")
        buf.clear()
        assert buf.size() == 0
        assert buf.total_bytes() == 0

    def test_purge_removes_old_chunks(self):
        buf = AudioBuffer()
        # Manually inject a stale entry by monkeypatching _chunks
        buf._chunks.append((time.monotonic() - MAX_BUFFER_SECONDS - 5, b"old"))
        buf._chunks.append((time.monotonic(), b"new"))
        buf.purge()
        assert buf.size() == 1

    def test_purge_keeps_recent_chunks(self):
        buf = AudioBuffer()
        buf.append(b"recent1")
        buf.append(b"recent2")
        buf.purge()
        assert buf.size() == 2

    def test_append_auto_purges_stale(self):
        buf = AudioBuffer()
        # Inject stale entry directly
        buf._chunks.append((time.monotonic() - MAX_BUFFER_SECONDS - 10, b"stale"))
        # Append new entry which triggers auto-purge
        buf.append(b"fresh")
        assert buf.size() == 1

    def test_buffer_max_is_30_seconds(self):
        assert MAX_BUFFER_SECONDS == 30


# ===========================================================================
# 4. WakeWordDetector — OAuth3 and lifecycle
# ===========================================================================

class TestWakeWordDetectorOAuth3:

    def test_start_without_token_raises_permission_error(self):
        detector = WakeWordDetector(token=None)
        with pytest.raises(PermissionError, match="voice.wake.listen"):
            detector.start_listening()

    def test_start_with_wrong_scope_raises_permission_error(self):
        token = _make_token(["gmail.read.inbox"])
        detector = WakeWordDetector(token=token)
        with pytest.raises(PermissionError):
            detector.start_listening()

    def test_start_with_correct_scope_succeeds(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector.start_listening()
        assert detector.is_listening is True
        detector.stop_listening()

    def test_start_with_expired_token_raises(self):
        token = _make_token([WAKE_SCOPE_LISTEN], expired=True)
        detector = WakeWordDetector(token=token)
        with pytest.raises(PermissionError):
            detector.start_listening()

    def test_start_with_revoked_token_raises(self):
        token = _make_token([WAKE_SCOPE_LISTEN], revoked=True)
        detector = WakeWordDetector(token=token)
        with pytest.raises(PermissionError):
            detector.start_listening()

    def test_always_on_without_always_on_scope_raises(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        config = WakeConfig(always_on=True)
        detector = WakeWordDetector(config=config, token=token)
        # voice.wake.always_on is missing → PermissionError
        with pytest.raises(PermissionError):
            detector.start_listening()

    def test_always_on_scope_present_but_no_step_up_raises(self):
        # voice.wake.always_on is high-risk → step-up required
        # Without step_up_nonce, enforcement should deny it
        token = _make_token([WAKE_SCOPE_LISTEN, WAKE_SCOPE_ALWAYS_ON])
        config = WakeConfig(always_on=True)
        detector = WakeWordDetector(config=config, token=token)
        with pytest.raises(PermissionError):
            detector.start_listening(step_up_nonce=None)

    def test_always_on_with_step_up_nonce_proceeds(self):
        token = _make_token([WAKE_SCOPE_LISTEN, WAKE_SCOPE_ALWAYS_ON])
        config = WakeConfig(always_on=True)
        detector = WakeWordDetector(config=config, token=token)
        # step_up_nonce provided → step_up_confirmed=True in enforcement
        detector.start_listening(step_up_nonce="fake-nonce-accepted")
        assert detector.is_listening is True
        detector.stop_listening()


class TestWakeWordDetectorLifecycle:

    def test_is_listening_false_before_start(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        assert detector.is_listening is False

    def test_is_listening_true_after_start(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector.start_listening()
        assert detector.is_listening is True
        detector.stop_listening()

    def test_is_listening_false_after_stop(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector.start_listening()
        detector.stop_listening()
        assert detector.is_listening is False

    def test_stop_when_not_listening_is_noop(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector.stop_listening()  # should not raise
        assert detector.is_listening is False

    def test_double_start_raises_runtime_error(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector.start_listening()
        with pytest.raises(RuntimeError, match="already listening"):
            detector.start_listening()
        detector.stop_listening()

    def test_buffer_cleared_on_stop(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        backend = ScriptedAudioBackend([b"chunk1", b"chunk2"])
        detector = WakeWordDetector(token=token, backend=backend)
        # Manually add to buffer
        detector._buffer.append(b"test-data")
        detector.start_listening()
        detector.stop_listening()
        assert detector.buffer.size() == 0


class TestWakeWordDetectorCallbacks:

    def test_on_wake_registers_callable(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        called = []
        detector.on_wake(lambda: called.append(1))
        assert len(detector._callbacks) == 1

    def test_on_wake_non_callable_raises(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        with pytest.raises(TypeError):
            detector.on_wake("not-a-function")

    def test_multiple_callbacks_registered(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector.on_wake(lambda: None)
        detector.on_wake(lambda: None)
        assert len(detector._callbacks) == 2

    def test_callback_fired_on_wake_word_detection(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        called = []

        backend = ScriptedAudioBackend([b"solace please wake up"])
        detector = WakeWordDetector(token=token, backend=backend)
        detector.on_wake(lambda: called.append(True))

        # Directly invoke internal check (no thread needed for unit test)
        detector._check_wake_word("hey solace wake up")

        assert len(called) == 1

    def test_no_callback_on_non_wake_word(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        called = []

        detector = WakeWordDetector(token=token)
        detector.on_wake(lambda: called.append(True))

        detector._check_wake_word("this does not contain the magic phrase")

        assert len(called) == 0

    def test_wake_word_detection_case_insensitive(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        called = []

        detector = WakeWordDetector(token=token)
        detector.on_wake(lambda: called.append(True))

        detector._check_wake_word("SOLACE activate")

        assert len(called) == 1

    def test_wake_log_populated_on_detection(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)

        detector._check_wake_word("hey solace")
        log = detector.wake_log
        assert len(log) == 1
        assert log[0]["event"] == "wake_detected"
        assert "solace" in log[0]["matched_text"].lower()

    def test_wake_log_contains_no_raw_audio(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector._check_wake_word("solace")

        log = detector.wake_log
        for entry in log:
            # No audio bytes in log
            for v in entry.values():
                assert not isinstance(v, bytes), "Raw audio bytes found in wake log!"

    def test_buffer_cleared_after_wake_detection(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector._buffer.append(b"audio-chunk")
        assert detector.buffer.size() == 1

        detector._check_wake_word("solace now")
        assert detector.buffer.size() == 0


# ===========================================================================
# 5. IntentParser
# ===========================================================================

class TestIntentParser:

    def setup_method(self):
        self.parser = IntentParser()

    def test_read_emails_maps_to_gmail_read_inbox(self):
        action = self.parser.parse("read my emails")
        assert action.intent == "gmail-read-inbox"
        assert action.platform == "gmail"

    def test_check_inbox_maps_to_gmail_read_inbox(self):
        action = self.parser.parse("check my inbox")
        assert action.intent == "gmail-read-inbox"

    def test_send_email_maps_correctly(self):
        action = self.parser.parse("send email to John")
        assert action.intent == "gmail-send-email"
        assert action.platform == "gmail"

    def test_delete_email_maps_correctly(self):
        action = self.parser.parse("delete email now")
        assert action.intent == "gmail-delete-email"

    def test_post_on_linkedin_maps_correctly(self):
        action = self.parser.parse("post on linkedin today")
        assert action.intent == "linkedin-post-text"
        assert action.platform == "linkedin"

    def test_read_reddit_maps_correctly(self):
        action = self.parser.parse("read reddit please")
        assert action.intent == "reddit-read-feed"

    def test_github_issues_maps_correctly(self):
        action = self.parser.parse("github issues please")
        assert action.intent == "github-read-issues"

    def test_hacker_news_maps_correctly(self):
        action = self.parser.parse("read hacker news")
        assert action.intent == "hackernews-read"

    def test_unknown_utterance_returns_unknown_intent(self):
        action = self.parser.parse("do something magical with bananas")
        assert action.intent == "unknown"
        assert action.confidence == 0.0

    def test_empty_utterance_returns_unknown(self):
        action = self.parser.parse("")
        assert action.intent == "unknown"
        assert action.confidence == 0.0

    def test_whitespace_only_returns_unknown(self):
        action = self.parser.parse("   ")
        assert action.intent == "unknown"

    def test_confidence_high_for_single_exact_match(self):
        action = self.parser.parse("read my emails")
        assert action.confidence >= AUTO_EXECUTE_THRESHOLD

    def test_confidence_below_threshold_sets_requires_confirmation(self):
        # Ambiguous utterance should have low confidence
        action = self.parser.parse("xyzzy unknown command here")
        assert action.requires_confirmation is True

    def test_destructive_intent_requires_confirmation(self):
        action = self.parser.parse("delete email")
        assert action.requires_confirmation is True

    def test_send_email_requires_confirmation(self):
        action = self.parser.parse("send email to boss")
        assert action.requires_confirmation is True

    def test_read_inbox_does_not_require_confirmation_if_confident(self):
        action = self.parser.parse("read my emails")
        # read my emails is non-destructive AND should be high confidence
        # so requires_confirmation should be False
        assert action.intent == "gmail-read-inbox"
        assert action.confidence >= AUTO_EXECUTE_THRESHOLD
        assert action.requires_confirmation is False

    def test_required_scopes_contains_talk_scope(self):
        action = self.parser.parse("read my emails")
        assert TALK_SCOPE_COMMAND in action.required_scopes

    def test_required_scopes_contains_target_scope(self):
        action = self.parser.parse("read my emails")
        assert "gmail.read.inbox" in action.required_scopes

    def test_utterance_preserved_in_action(self):
        text = "please read my emails now"
        action = self.parser.parse(text)
        assert action.utterance == text

    def test_case_insensitive_matching(self):
        action = self.parser.parse("READ MY EMAILS")
        assert action.intent == "gmail-read-inbox"

    def test_custom_patterns_extend_defaults(self):
        custom = [("fly to mars", "space-travel", "nasa", "agent.dispatch.task")]
        parser = IntentParser(custom_patterns=custom)
        action = parser.parse("fly to mars please")
        assert action.intent == "space-travel"
        assert action.platform == "nasa"


# ===========================================================================
# 6. VoiceAction
# ===========================================================================

class TestVoiceAction:

    def test_basic_creation(self):
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
        )
        assert action.intent == "gmail-read-inbox"
        assert action.platform == "gmail"
        assert action.confidence == 0.9

    def test_default_fields(self):
        action = VoiceAction(intent="test-intent", platform="test")
        assert action.parameters == {}
        assert action.confidence == 0.0
        assert action.requires_confirmation is False
        assert action.required_scopes == []
        assert action.utterance == ""

    def test_empty_intent_raises(self):
        with pytest.raises(ValueError, match="intent"):
            VoiceAction(intent="", platform="gmail")

    def test_empty_platform_raises(self):
        with pytest.raises(ValueError, match="platform"):
            VoiceAction(intent="gmail-read", platform="")

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            VoiceAction(intent="test", platform="test", confidence=-0.1)

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            VoiceAction(intent="test", platform="test", confidence=1.1)

    def test_non_numeric_confidence_raises(self):
        with pytest.raises(TypeError):
            VoiceAction(intent="test", platform="test", confidence="high")

    def test_non_dict_parameters_raises(self):
        with pytest.raises(TypeError):
            VoiceAction(intent="test", platform="test", parameters=["not", "a", "dict"])

    def test_non_list_required_scopes_raises(self):
        with pytest.raises(TypeError):
            VoiceAction(intent="test", platform="test", required_scopes="single-scope")

    def test_is_destructive_true_for_delete_email(self):
        action = VoiceAction(intent="gmail-delete-email", platform="gmail", confidence=0.9)
        assert action.is_destructive is True

    def test_is_destructive_true_for_send_email(self):
        action = VoiceAction(intent="gmail-send-email", platform="gmail", confidence=0.9)
        assert action.is_destructive is True

    def test_is_destructive_false_for_read(self):
        action = VoiceAction(intent="gmail-read-inbox", platform="gmail", confidence=0.9)
        assert action.is_destructive is False

    def test_will_auto_execute_true_when_confident_and_not_destructive(self):
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
            requires_confirmation=False,
        )
        assert action.will_auto_execute is True

    def test_will_auto_execute_false_when_requires_confirmation(self):
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
            requires_confirmation=True,
        )
        assert action.will_auto_execute is False

    def test_will_auto_execute_false_when_low_confidence(self):
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.3,
            requires_confirmation=False,
        )
        assert action.will_auto_execute is False


# ===========================================================================
# 7. ActionResult
# ===========================================================================

class TestActionResult:

    def _make_action(self, intent="gmail-read-inbox", platform="gmail", confidence=0.9):
        return VoiceAction(intent=intent, platform=platform, confidence=confidence)

    def test_success_result(self):
        action = self._make_action()
        result = ActionResult(success=True, action=action, output="Done.")
        assert result.success is True
        assert result.blocked is False
        assert result.pending_confirmation is False

    def test_failure_result(self):
        action = self._make_action()
        result = ActionResult(success=False, action=action, error="scope denied")
        assert result.success is False
        assert result.blocked is True
        assert result.pending_confirmation is False

    def test_confirmation_required_result(self):
        action = self._make_action()
        result = ActionResult(
            success=False,
            action=action,
            confirmation_required=True,
            output="Please confirm.",
        )
        assert result.success is False
        assert result.blocked is False
        assert result.pending_confirmation is True

    def test_default_fields(self):
        action = self._make_action()
        result = ActionResult(success=True, action=action)
        assert result.output == ""
        assert result.error == ""
        assert result.confirmation_required is False
        assert result.audit_entry == {}


# ===========================================================================
# 8. TalkMode — OAuth3 and lifecycle
# ===========================================================================

class TestTalkModeOAuth3:

    def test_activate_without_token_raises_permission_error(self):
        talk = TalkMode(token=None)
        with pytest.raises(PermissionError, match="voice.talk.command"):
            talk.activate()

    def test_activate_with_wrong_scope_raises(self):
        token = _make_token(["gmail.read.inbox"])
        talk = TalkMode(token=token)
        with pytest.raises(PermissionError):
            talk.activate()

    def test_activate_with_correct_scope_succeeds(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        assert talk.is_active is True
        talk.deactivate()

    def test_activate_with_expired_token_raises(self):
        token = _make_token([TALK_SCOPE_COMMAND], expired=True)
        talk = TalkMode(token=token)
        with pytest.raises(PermissionError):
            talk.activate()

    def test_activate_with_revoked_token_raises(self):
        token = _make_token([TALK_SCOPE_COMMAND], revoked=True)
        talk = TalkMode(token=token)
        with pytest.raises(PermissionError):
            talk.activate()


class TestTalkModeLifecycle:

    def test_is_active_false_before_activate(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        assert talk.is_active is False

    def test_is_active_true_after_activate(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        assert talk.is_active is True
        talk.deactivate()

    def test_is_active_false_after_deactivate(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        talk.deactivate()
        assert talk.is_active is False

    def test_deactivate_when_inactive_is_noop(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.deactivate()  # should not raise
        assert talk.is_active is False

    def test_double_activate_raises_runtime_error(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        with pytest.raises(RuntimeError, match="already active"):
            talk.activate()
        talk.deactivate()

    def test_process_utterance_when_inactive_raises(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        with pytest.raises(RuntimeError, match="not active"):
            talk.process_utterance("read my emails")

    def test_execute_action_when_inactive_returns_failure(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        action = VoiceAction(intent="gmail-read-inbox", platform="gmail", confidence=0.9)
        result = talk.execute_action(action)
        assert result.success is False
        assert "not active" in result.error.lower()


class TestTalkModeUtterance:

    def test_process_utterance_returns_voice_action(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        action = talk.process_utterance("read my emails")
        assert isinstance(action, VoiceAction)
        talk.deactivate()

    def test_process_utterance_resets_silence_timer(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        time.sleep(0.05)
        t_before = talk._last_utterance_time
        time.sleep(0.05)
        talk.process_utterance("check inbox")
        t_after = talk._last_utterance_time
        assert t_after > t_before
        talk.deactivate()

    def test_auto_deactivate_on_silence_timeout(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token, silence_timeout=1)
        talk.activate()
        time.sleep(1.1)
        auto_deactivated = talk.check_silence_timeout()
        assert auto_deactivated is True
        assert talk.is_active is False

    def test_no_auto_deactivate_before_timeout(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token, silence_timeout=60)
        talk.activate()
        auto_deactivated = talk.check_silence_timeout()
        assert auto_deactivated is False
        assert talk.is_active is True
        talk.deactivate()

    def test_check_silence_timeout_false_when_inactive(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        result = talk.check_silence_timeout()
        assert result is False


class TestTalkModeExecution:

    def _active_talk(self, extra_scopes=None, executor=None, confirmation_cb=None):
        scopes = [TALK_SCOPE_COMMAND] + (extra_scopes or [])
        token = _make_token(scopes)
        talk = TalkMode(
            token=token,
            executor=executor or SucceedingExecutor(),
            confirmation_callback=confirmation_cb,
        )
        talk.activate()
        return talk, token

    def test_execute_non_destructive_action_succeeds(self):
        talk, _ = self._active_talk(extra_scopes=["gmail.read.inbox"])
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.read.inbox"],
        )
        result = talk.execute_action(action)
        assert result.success is True
        talk.deactivate()

    def test_execute_destructive_action_without_confirmation_blocked(self):
        talk, _ = self._active_talk(extra_scopes=["gmail.send.email"])
        action = VoiceAction(
            intent="gmail-send-email",
            platform="gmail",
            confidence=0.9,
            requires_confirmation=True,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.send.email"],
        )
        result = talk.execute_action(action)
        # confirmation_callback is None → fail-closed → pending
        assert result.success is False
        assert result.confirmation_required is True
        talk.deactivate()

    def test_execute_destructive_with_confirmation_proceeds(self):
        talk, _ = self._active_talk(
            extra_scopes=["gmail.send.email"],
            confirmation_cb=lambda action: True,
        )
        action = VoiceAction(
            intent="gmail-send-email",
            platform="gmail",
            confidence=0.9,
            requires_confirmation=True,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.send.email"],
        )
        result = talk.execute_action(action)
        assert result.success is True
        talk.deactivate()

    def test_execute_action_blocked_on_missing_scope(self):
        token = _make_token([TALK_SCOPE_COMMAND])  # no gmail.send.email
        talk = TalkMode(token=token, executor=SucceedingExecutor())
        talk.activate()
        action = VoiceAction(
            intent="gmail-send-email",
            platform="gmail",
            confidence=0.9,
            requires_confirmation=False,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.send.email"],
        )
        result = talk.execute_action(action)
        assert result.success is False
        talk.deactivate()

    def test_executor_failure_propagates(self):
        talk, _ = self._active_talk(
            extra_scopes=["gmail.read.inbox"],
            executor=FailingExecutor(),
        )
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.read.inbox"],
        )
        result = talk.execute_action(action)
        assert result.success is False
        assert result.error == "executor-error"
        talk.deactivate()

    def test_low_confidence_action_requires_confirmation(self):
        talk, _ = self._active_talk(
            extra_scopes=["gmail.read.inbox"],
            confirmation_cb=lambda a: False,
        )
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.4,
            requires_confirmation=True,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.read.inbox"],
        )
        result = talk.execute_action(action)
        assert result.confirmation_required is True
        talk.deactivate()


# ===========================================================================
# 9. Audit Logging
# ===========================================================================

class TestAuditLogging:

    def test_audit_log_empty_on_init(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        assert talk.audit_log == []

    def test_audit_log_records_activation(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        log = talk.audit_log
        assert any(e["event"] == "talk_mode_activated" for e in log)
        talk.deactivate()

    def test_audit_log_records_deactivation(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        talk.deactivate()
        log = talk.audit_log
        assert any(e["event"] == "talk_mode_deactivated" for e in log)

    def test_audit_log_records_action_executed(self):
        token = _make_token([TALK_SCOPE_COMMAND, "gmail.read.inbox"])
        talk = TalkMode(token=token, executor=SucceedingExecutor())
        talk.activate()
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.read.inbox"],
        )
        talk.execute_action(action)
        log = talk.audit_log
        assert any(e["event"] == "action_executed" for e in log)
        talk.deactivate()

    def test_audit_log_contains_utterance_text(self):
        token = _make_token([TALK_SCOPE_COMMAND, "gmail.read.inbox"])
        talk = TalkMode(token=token, executor=SucceedingExecutor())
        talk.activate()
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.read.inbox"],
            utterance="read my emails please",
        )
        talk.execute_action(action)
        log = talk.audit_log
        executed = [e for e in log if e["event"] == "action_executed"]
        assert len(executed) == 1
        assert executed[0]["utterance"] == "read my emails please"
        talk.deactivate()

    def test_audit_log_contains_no_raw_audio(self):
        token = _make_token([TALK_SCOPE_COMMAND, "gmail.read.inbox"])
        talk = TalkMode(token=token, executor=SucceedingExecutor())
        talk.activate()
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.read.inbox"],
            utterance="read my emails",
        )
        talk.execute_action(action)
        for entry in talk.audit_log:
            for v in entry.values():
                assert not isinstance(v, bytes), "Raw audio bytes found in audit log!"
        talk.deactivate()

    def test_audit_log_records_blocked_oauth3(self):
        # Use a non-destructive intent that still requires a scope the token lacks.
        # gmail-search is not in _ALL_CONFIRM_REQUIRED so it bypasses confirmation
        # and goes straight to scope enforcement.
        token = _make_token([TALK_SCOPE_COMMAND])  # missing gmail.search.messages
        talk = TalkMode(token=token, executor=SucceedingExecutor())
        talk.activate()
        action = VoiceAction(
            intent="gmail-search",
            platform="gmail",
            confidence=0.9,
            requires_confirmation=False,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.search.messages"],
        )
        talk.execute_action(action)
        log = talk.audit_log
        assert any(e["event"] == "action_blocked_scope" for e in log)
        talk.deactivate()

    def test_audit_log_has_timestamp(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        for entry in talk.audit_log:
            assert "timestamp" in entry
            assert isinstance(entry["timestamp"], float)
        talk.deactivate()

    def test_audit_log_is_copy(self):
        token = _make_token([TALK_SCOPE_COMMAND])
        talk = TalkMode(token=token)
        talk.activate()
        log1 = talk.audit_log
        log2 = talk.audit_log
        assert log1 is not log2  # returned as copy each time
        talk.deactivate()


# ===========================================================================
# 10. Security Tests
# ===========================================================================

class TestSecurity:

    def test_no_raw_audio_in_wake_log(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector._check_wake_word("hey solace do it")
        for entry in detector.wake_log:
            for v in entry.values():
                assert not isinstance(v, bytes)

    def test_audio_buffer_cleared_on_wake_detection(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector._buffer.append(b"audio-sample-1")
        detector._buffer.append(b"audio-sample-2")
        assert detector.buffer.size() == 2
        detector._check_wake_word("solace please")
        assert detector.buffer.size() == 0

    def test_audio_buffer_cleared_on_stop(self):
        token = _make_token([WAKE_SCOPE_LISTEN])
        detector = WakeWordDetector(token=token)
        detector.start_listening()
        detector._buffer.append(b"audio-data")
        detector.stop_listening()
        assert detector.buffer.size() == 0

    def test_buffer_max_30_seconds_constant(self):
        assert MAX_BUFFER_SECONDS == 30

    def test_stale_audio_auto_purged(self):
        buf = AudioBuffer()
        stale_ts = time.monotonic() - (MAX_BUFFER_SECONDS + 5)
        buf._chunks.append((stale_ts, b"stale-audio"))
        buf.append(b"new-audio")
        assert buf.size() == 1

    def test_talk_mode_no_audio_in_audit(self):
        token = _make_token([TALK_SCOPE_COMMAND, "gmail.read.inbox"])
        talk = TalkMode(token=token, executor=SucceedingExecutor())
        talk.activate()
        action = VoiceAction(
            intent="gmail-read-inbox",
            platform="gmail",
            confidence=0.9,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.read.inbox"],
            utterance="read my emails",
        )
        talk.execute_action(action)
        for entry in talk.audit_log:
            for v in entry.values():
                assert not isinstance(v, bytes)
        talk.deactivate()

    def test_default_confirmation_callback_is_fail_closed(self):
        """No confirmation callback → destructive actions always blocked."""
        token = _make_token([TALK_SCOPE_COMMAND, "gmail.send.email"])
        talk = TalkMode(token=token, executor=SucceedingExecutor(), confirmation_callback=None)
        talk.activate()
        action = VoiceAction(
            intent="gmail-send-email",
            platform="gmail",
            confidence=0.9,
            requires_confirmation=True,
            required_scopes=[TALK_SCOPE_COMMAND, "gmail.send.email"],
        )
        result = talk.execute_action(action)
        # Fail-closed: no callback → blocked/pending
        assert result.success is False
        talk.deactivate()

    def test_destructive_intent_set_covers_key_operations(self):
        assert "gmail-send-email" in _DESTRUCTIVE_INTENTS
        assert "gmail-delete-email" in _DESTRUCTIVE_INTENTS
        assert "linkedin-delete-post" in _DESTRUCTIVE_INTENTS
        assert "linkedin-send-message" in _DESTRUCTIVE_INTENTS
        assert "reddit-delete-post" in _DESTRUCTIVE_INTENTS
        assert "github-merge-pr" in _DESTRUCTIVE_INTENTS
        assert "github-delete-branch" in _DESTRUCTIVE_INTENTS

    def test_always_on_scope_is_high_risk(self):
        # Use module-level attribute lookup (not the pre-bound local name) so that
        # register_voice_scopes() patching is reflected.
        register_voice_scopes()
        assert "voice.wake.always_on" in _oauth3_scopes.HIGH_RISK_SCOPES

    def test_tts_persona_scope_is_high_risk(self):
        register_voice_scopes()
        assert "voice.tts.persona" in _oauth3_scopes.HIGH_RISK_SCOPES

    def test_wake_listen_scope_is_not_high_risk(self):
        register_voice_scopes()
        assert "voice.wake.listen" not in _oauth3_scopes.HIGH_RISK_SCOPES
