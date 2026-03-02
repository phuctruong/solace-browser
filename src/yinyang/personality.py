"""YinyangPersonalityManager -- user-selectable personality for Yinyang responses.

Personalities shape how Yinyang communicates:
  - Professional: concise, formal, no humor
  - Friendly: warm, encouraging, moderate humor (DEFAULT)
  - Playful: enthusiastic, heavy humor, emojis
  - Minimal: terse, data-only, no flair
  - Custom: user-defined tone parameters

Stored in ~/.solace/settings.json under the "personality" key.
Affects delight_engine content selection, support_bridge tone, warm_token style.

Anti-Clippy: Personality changes are explicit user actions. Never auto-switch.
Fallback Ban: No silent failures. Specific exceptions only. No broad catches.

Channel [7] -- Context + Tools.  Rung: 65537.
DNA: personality(get | set | filter | tone) -> {type, params} -> Anti-Clippy
"""
from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("solace-browser.yinyang.personality")

_DEFAULT_SOLACE_HOME = Path("~/.solace").expanduser()
_SETTINGS_FILENAME = "settings.json"
_PERSONALITY_KEY = "personality"
_CUSTOM_TONE_KEY = "custom_tone"

# Default personality
_DEFAULT_PERSONALITY = "friendly"


class PersonalityType(Enum):
    """User-selectable personality types for Yinyang responses."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    PLAYFUL = "playful"
    MINIMAL = "minimal"
    CUSTOM = "custom"


# Tag allowlists per personality -- controls which content tags are permitted.
# Items with tags NOT in the allowlist are filtered out.
# An empty set means "allow all tags" (no filtering).
_PERSONALITY_TAG_FILTERS: dict[PersonalityType, set[str]] = {
    PersonalityType.PROFESSIONAL: {"tech", "science", "business", "productivity"},
    PersonalityType.FRIENDLY: set(),  # allow all
    PersonalityType.PLAYFUL: set(),  # allow all
    PersonalityType.MINIMAL: {"tech", "science"},
    PersonalityType.CUSTOM: set(),  # allow all by default
}

# Content-type allowlists per personality -- controls which delight categories appear.
_PERSONALITY_CONTENT_TYPES: dict[PersonalityType, set[str]] = {
    PersonalityType.PROFESSIONAL: {"fact", "celebration"},
    PersonalityType.FRIENDLY: {"joke", "fact", "smalltalk", "celebration", "holiday"},
    PersonalityType.PLAYFUL: {"joke", "fact", "smalltalk", "celebration", "holiday"},
    PersonalityType.MINIMAL: {"fact"},
    PersonalityType.CUSTOM: {"joke", "fact", "smalltalk", "celebration", "holiday"},
}

# Tone parameters per personality -- used by support_bridge and delight_engine.
_PERSONALITY_TONES: dict[PersonalityType, dict[str, str]] = {
    PersonalityType.PROFESSIONAL: {
        "greeting": "Hello.",
        "farewell": "Goodbye.",
        "encouragement": "Task completed successfully.",
        "error": "An error occurred. Details follow.",
        "style": "formal",
        "warmth": "low",
        "humor": "none",
        "verbosity": "concise",
    },
    PersonalityType.FRIENDLY: {
        "greeting": "Hey there!",
        "farewell": "See you next time!",
        "encouragement": "Great work! You're making real progress.",
        "error": "Oops, something went wrong. Let's figure it out.",
        "style": "conversational",
        "warmth": "high",
        "humor": "moderate",
        "verbosity": "normal",
    },
    PersonalityType.PLAYFUL: {
        "greeting": "Heyyy! Ready to build something awesome?",
        "farewell": "Catch you later, superstar!",
        "encouragement": "You're on fire! Keep that momentum going!",
        "error": "Whoops! Hit a bump. No worries, we got this!",
        "style": "enthusiastic",
        "warmth": "very_high",
        "humor": "heavy",
        "verbosity": "expressive",
    },
    PersonalityType.MINIMAL: {
        "greeting": "Ready.",
        "farewell": "Done.",
        "encouragement": "Done.",
        "error": "Error.",
        "style": "terse",
        "warmth": "none",
        "humor": "none",
        "verbosity": "minimal",
    },
    PersonalityType.CUSTOM: {
        "greeting": "Hey there!",
        "farewell": "See you next time!",
        "encouragement": "Great work!",
        "error": "Something went wrong.",
        "style": "conversational",
        "warmth": "high",
        "humor": "moderate",
        "verbosity": "normal",
    },
}


class InvalidPersonalityError(Exception):
    """Raised when an invalid personality value is encountered."""


class PersonalityManager:
    """Manages user-selectable personality for Yinyang responses.

    Reads and writes personality preference to ~/.solace/settings.json.
    Provides filtering for delight content and tone parameters for other modules.

    Anti-Clippy: Personality is never changed without explicit user action.
    """

    def __init__(self, settings_path: Path | None = None) -> None:
        """Initialize with optional path to settings.json.

        Args:
            settings_path: Full path to settings.json. If None, uses
                           ~/.solace/settings.json.
        """
        if settings_path is not None:
            self._settings_path = Path(settings_path)
        else:
            self._settings_path = _DEFAULT_SOLACE_HOME / _SETTINGS_FILENAME

    def get_personality(self) -> PersonalityType:
        """Read the current personality from settings.json.

        Returns PersonalityType.FRIENDLY if the file is missing or the key
        is absent. Raises InvalidPersonalityError if the stored value is
        not a valid PersonalityType.
        """
        settings = self._read_settings()
        raw = settings.get(_PERSONALITY_KEY)
        if raw is None:
            return PersonalityType.FRIENDLY

        if not isinstance(raw, str):
            raise InvalidPersonalityError(
                f"Personality value must be a string, got {type(raw).__name__}"
            )

        try:
            return PersonalityType(raw)
        except ValueError:
            valid = ", ".join(p.value for p in PersonalityType)
            raise InvalidPersonalityError(
                f"Invalid personality '{raw}'. Valid options: {valid}"
            )

    def set_personality(self, personality: PersonalityType) -> None:
        """Write the personality preference to settings.json.

        Creates the settings file and parent directories if they do not exist.

        Args:
            personality: The PersonalityType to save.

        Raises:
            TypeError: If personality is not a PersonalityType.
        """
        if not isinstance(personality, PersonalityType):
            raise TypeError(
                f"personality must be a PersonalityType, got {type(personality).__name__}"
            )

        settings = self._read_settings()
        settings[_PERSONALITY_KEY] = personality.value
        self._write_settings(settings)
        logger.info("Personality set to %s", personality.value)

    def set_custom_tone(self, tone: dict[str, str]) -> None:
        """Save custom tone parameters for the CUSTOM personality.

        Args:
            tone: Dictionary of tone keys (greeting, farewell, encouragement,
                  error, style, warmth, humor, verbosity).

        Raises:
            TypeError: If tone is not a dict.
            ValueError: If tone is empty.
        """
        if not isinstance(tone, dict):
            raise TypeError(f"tone must be a dict, got {type(tone).__name__}")
        if not tone:
            raise ValueError("tone must not be empty")

        settings = self._read_settings()
        settings[_CUSTOM_TONE_KEY] = tone
        self._write_settings(settings)
        logger.info("Custom tone parameters saved (%d keys)", len(tone))

    def get_custom_tone(self) -> dict[str, str]:
        """Read custom tone parameters from settings.json.

        Returns the stored custom tone, or the default CUSTOM tone if
        no custom tone has been set.
        """
        settings = self._read_settings()
        custom = settings.get(_CUSTOM_TONE_KEY)
        if isinstance(custom, dict) and custom:
            # Validate all values are strings — reject non-string types
            validated = {
                k: v for k, v in custom.items()
                if isinstance(k, str) and isinstance(v, str)
            }
            if validated:
                return validated
        return dict(_PERSONALITY_TONES[PersonalityType.CUSTOM])

    def filter_content(
        self,
        items: list[dict[str, Any]],
        content_type: str = "",
        personality: PersonalityType | None = None,
    ) -> list[dict[str, Any]]:
        """Filter delight content items based on the active personality.

        Filtering rules:
        1. If the personality disallows the content_type, return empty list.
        2. If the personality has tag filters, keep only items whose tags
           intersect with the allowed tags. Items without tags are kept.
        3. For MINIMAL, limit results to at most 1 item.

        Args:
            items: List of content dicts (each may have "tags": list[str]).
            content_type: The type of content ("joke", "fact", "smalltalk", etc.).
            personality: Override personality. If None, reads from settings.

        Returns:
            Filtered list of content items.
        """
        if personality is None:
            personality = self.get_personality()

        # Step 1: Check if content type is allowed
        allowed_types = _PERSONALITY_CONTENT_TYPES.get(personality, set())
        if content_type and allowed_types and content_type not in allowed_types:
            return []

        # Step 2: Tag filtering
        allowed_tags = _PERSONALITY_TAG_FILTERS.get(personality, set())
        if allowed_tags:
            filtered = []
            for item in items:
                item_tags = item.get("tags", [])
                if not isinstance(item_tags, list):
                    # Non-list tags are treated as untagged — include the item
                    filtered.append(item)
                    continue
                if not item_tags:
                    # Items without tags pass through
                    filtered.append(item)
                elif set(item_tags) & allowed_tags:
                    # At least one tag matches
                    filtered.append(item)
            result = filtered
        else:
            result = list(items)

        # Step 3: MINIMAL caps at 1 result
        if personality == PersonalityType.MINIMAL and len(result) > 1:
            result = result[:1]

        return result

    def get_tone(self, personality: PersonalityType | None = None) -> dict[str, str]:
        """Get tone parameters for the active personality.

        For CUSTOM personality, merges saved custom tone over defaults.

        Args:
            personality: Override personality. If None, reads from settings.

        Returns:
            Dict with keys: greeting, farewell, encouragement, error,
            style, warmth, humor, verbosity.
        """
        if personality is None:
            personality = self.get_personality()

        base_tone = dict(_PERSONALITY_TONES.get(personality, _PERSONALITY_TONES[PersonalityType.FRIENDLY]))

        if personality == PersonalityType.CUSTOM:
            custom = self.get_custom_tone()
            base_tone.update(custom)

        return base_tone

    def list_personalities(self) -> list[dict[str, str]]:
        """List all available personalities with descriptions.

        Returns:
            List of dicts: [{name, value, description}, ...]
        """
        descriptions: dict[PersonalityType, str] = {
            PersonalityType.PROFESSIONAL: "Concise, formal, no humor. Business-ready.",
            PersonalityType.FRIENDLY: "Warm, encouraging, moderate humor. Default.",
            PersonalityType.PLAYFUL: "Enthusiastic, heavy humor, expressive.",
            PersonalityType.MINIMAL: "Terse, data-only, no flair.",
            PersonalityType.CUSTOM: "User-defined tone parameters.",
        }
        return [
            {
                "name": p.name,
                "value": p.value,
                "description": descriptions.get(p, ""),
            }
            for p in PersonalityType
        ]

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _read_settings(self) -> dict[str, Any]:
        """Read settings.json, returning empty dict if missing."""
        if not self._settings_path.exists():
            return {}
        try:
            raw = json.loads(self._settings_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
            logger.warning(
                "settings.json is not a JSON object, treating as empty: %s",
                self._settings_path,
            )
            return {}
        except json.JSONDecodeError as exc:
            logger.warning(
                "Failed to parse settings.json at %s: %s",
                self._settings_path,
                exc,
            )
            raise
        except PermissionError as exc:
            logger.warning(
                "Permission denied reading settings.json at %s: %s",
                self._settings_path,
                exc,
            )
            raise

    def _write_settings(self, settings: dict[str, Any]) -> None:
        """Write settings to settings.json, creating directories as needed."""
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(settings, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
