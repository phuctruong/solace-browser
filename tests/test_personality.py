"""
tests/test_personality.py -- YinyangPersonalityManager Test Suite
SolaceBrowser T3: Personality customization for Yinyang responses

Tests (30 tests):
  TestPersonalityType        (4 tests)  -- enum values, membership, iteration
  TestGetPersonality         (5 tests)  -- default, from file, missing file, invalid, non-string
  TestSetPersonality         (4 tests)  -- write, overwrite, creates dirs, type error
  TestCustomTone             (4 tests)  -- save, read, defaults, validation
  TestFilterContent          (7 tests)  -- each personality, tag filtering, content type, minimal cap
  TestGetTone                (4 tests)  -- each personality type, custom merge, override
  TestListPersonalities      (1 test)   -- all personalities listed with descriptions
  TestSettingsPersistence    (1 test)   -- round-trip write + read

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_personality.py -v --tb=short

Rung: 274177
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from yinyang.personality import (
    InvalidPersonalityError,
    PersonalityManager,
    PersonalityType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings_path(tmp_path: Path) -> Path:
    """Return a path to a temporary settings.json (file does not exist yet)."""
    return tmp_path / ".solace" / "settings.json"


@pytest.fixture
def manager(settings_path: Path) -> PersonalityManager:
    """Create a PersonalityManager with a temporary settings path."""
    return PersonalityManager(settings_path=settings_path)


@pytest.fixture
def manager_with_friendly(settings_path: Path) -> PersonalityManager:
    """Create a manager with 'friendly' personality pre-saved."""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps({"personality": "friendly"}, indent=2) + "\n",
        encoding="utf-8",
    )
    return PersonalityManager(settings_path=settings_path)


@pytest.fixture
def sample_items() -> list[dict]:
    """Sample delight content items with various tags."""
    return [
        {"id": "j1", "text": "Programming joke", "tags": ["programming", "tech"]},
        {"id": "j2", "text": "Food joke", "tags": ["food", "humor"]},
        {"id": "j3", "text": "Science fact", "tags": ["science"]},
        {"id": "j4", "text": "No tags item"},
        {"id": "j5", "text": "Business tip", "tags": ["business"]},
        {"id": "j6", "text": "Cat joke", "tags": ["animals"]},
    ]


# ===========================================================================
# TestPersonalityType
# ===========================================================================

class TestPersonalityType:
    """Tests for the PersonalityType enum."""

    def test_all_values_exist(self) -> None:
        """All five personality types exist as enum members."""
        assert PersonalityType.PROFESSIONAL.value == "professional"
        assert PersonalityType.FRIENDLY.value == "friendly"
        assert PersonalityType.PLAYFUL.value == "playful"
        assert PersonalityType.MINIMAL.value == "minimal"
        assert PersonalityType.CUSTOM.value == "custom"

    def test_enum_count(self) -> None:
        """Exactly 5 personality types defined."""
        assert len(PersonalityType) == 5

    def test_from_value(self) -> None:
        """PersonalityType can be constructed from string value."""
        assert PersonalityType("professional") == PersonalityType.PROFESSIONAL
        assert PersonalityType("friendly") == PersonalityType.FRIENDLY
        assert PersonalityType("playful") == PersonalityType.PLAYFUL
        assert PersonalityType("minimal") == PersonalityType.MINIMAL
        assert PersonalityType("custom") == PersonalityType.CUSTOM

    def test_invalid_value_raises(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            PersonalityType("nonexistent")


# ===========================================================================
# TestGetPersonality
# ===========================================================================

class TestGetPersonality:
    """Tests for PersonalityManager.get_personality()."""

    def test_default_when_no_file(self, manager: PersonalityManager) -> None:
        """Returns FRIENDLY when settings.json does not exist."""
        result = manager.get_personality()
        assert result == PersonalityType.FRIENDLY

    def test_reads_from_file(self, settings_path: Path) -> None:
        """Reads personality from settings.json."""
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps({"personality": "professional"}) + "\n",
            encoding="utf-8",
        )
        mgr = PersonalityManager(settings_path=settings_path)
        assert mgr.get_personality() == PersonalityType.PROFESSIONAL

    def test_default_when_key_missing(self, settings_path: Path) -> None:
        """Returns FRIENDLY when settings.json exists but has no personality key."""
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps({"other_setting": "value"}) + "\n",
            encoding="utf-8",
        )
        mgr = PersonalityManager(settings_path=settings_path)
        assert mgr.get_personality() == PersonalityType.FRIENDLY

    def test_invalid_personality_raises(self, settings_path: Path) -> None:
        """Raises InvalidPersonalityError for unknown personality value."""
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps({"personality": "aggressive"}) + "\n",
            encoding="utf-8",
        )
        mgr = PersonalityManager(settings_path=settings_path)
        with pytest.raises(InvalidPersonalityError, match="Invalid personality"):
            mgr.get_personality()

    def test_non_string_personality_raises(self, settings_path: Path) -> None:
        """Raises InvalidPersonalityError when personality value is not a string."""
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps({"personality": 42}) + "\n",
            encoding="utf-8",
        )
        mgr = PersonalityManager(settings_path=settings_path)
        with pytest.raises(InvalidPersonalityError, match="must be a string"):
            mgr.get_personality()


# ===========================================================================
# TestSetPersonality
# ===========================================================================

class TestSetPersonality:
    """Tests for PersonalityManager.set_personality()."""

    def test_set_writes_to_file(
        self, manager: PersonalityManager, settings_path: Path,
    ) -> None:
        """set_personality writes the value to settings.json."""
        manager.set_personality(PersonalityType.PLAYFUL)
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert data["personality"] == "playful"

    def test_set_overwrites_existing(
        self, manager_with_friendly: PersonalityManager, settings_path: Path,
    ) -> None:
        """set_personality overwrites a previously set personality."""
        manager_with_friendly.set_personality(PersonalityType.MINIMAL)
        assert manager_with_friendly.get_personality() == PersonalityType.MINIMAL

    def test_set_creates_directories(self, tmp_path: Path) -> None:
        """set_personality creates parent directories if they do not exist."""
        deep_path = tmp_path / "a" / "b" / "c" / "settings.json"
        mgr = PersonalityManager(settings_path=deep_path)
        mgr.set_personality(PersonalityType.PROFESSIONAL)
        assert deep_path.exists()
        data = json.loads(deep_path.read_text(encoding="utf-8"))
        assert data["personality"] == "professional"

    def test_set_rejects_non_enum(self, manager: PersonalityManager) -> None:
        """set_personality raises TypeError for non-PersonalityType argument."""
        with pytest.raises(TypeError, match="must be a PersonalityType"):
            manager.set_personality("friendly")  # type: ignore[arg-type]


# ===========================================================================
# TestCustomTone
# ===========================================================================

class TestCustomTone:
    """Tests for custom tone parameters."""

    def test_set_custom_tone(
        self, manager: PersonalityManager, settings_path: Path,
    ) -> None:
        """set_custom_tone saves tone parameters to settings.json."""
        tone = {"greeting": "Ahoy!", "style": "pirate"}
        manager.set_custom_tone(tone)
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert data["custom_tone"]["greeting"] == "Ahoy!"
        assert data["custom_tone"]["style"] == "pirate"

    def test_get_custom_tone_returns_saved(
        self, manager: PersonalityManager,
    ) -> None:
        """get_custom_tone returns previously saved tone."""
        tone = {"greeting": "Salutations!", "humor": "dry"}
        manager.set_custom_tone(tone)
        result = manager.get_custom_tone()
        assert result["greeting"] == "Salutations!"
        assert result["humor"] == "dry"

    def test_get_custom_tone_defaults(self, manager: PersonalityManager) -> None:
        """get_custom_tone returns default CUSTOM tone when none saved."""
        result = manager.get_custom_tone()
        assert "greeting" in result
        assert "farewell" in result
        assert isinstance(result["greeting"], str)

    def test_set_custom_tone_rejects_empty(
        self, manager: PersonalityManager,
    ) -> None:
        """set_custom_tone raises ValueError for empty dict."""
        with pytest.raises(ValueError, match="must not be empty"):
            manager.set_custom_tone({})

    def test_set_custom_tone_rejects_non_dict(
        self, manager: PersonalityManager,
    ) -> None:
        """set_custom_tone raises TypeError for non-dict argument."""
        with pytest.raises(TypeError, match="must be a dict"):
            manager.set_custom_tone("not a dict")  # type: ignore[arg-type]

    def test_custom_tone_filters_non_string_values(
        self, manager: PersonalityManager, settings_path: Path,
    ) -> None:
        """Non-string values in custom tone are filtered out."""
        manager.set_custom_tone({
            "greeting": "Hello",
            "bad_int": 123,
            "bad_list": ["a", "b"],
            "bad_none": None,
            "farewell": "Goodbye",
        })
        tone = manager.get_custom_tone()
        # Only string values survive
        assert tone["greeting"] == "Hello"
        assert tone["farewell"] == "Goodbye"
        assert "bad_int" not in tone
        assert "bad_list" not in tone
        assert "bad_none" not in tone


# ===========================================================================
# TestFilterContent
# ===========================================================================

class TestFilterContent:
    """Tests for PersonalityManager.filter_content()."""

    def test_friendly_allows_all(
        self, manager: PersonalityManager, sample_items: list[dict],
    ) -> None:
        """FRIENDLY personality allows all items (no tag filtering)."""
        result = manager.filter_content(
            sample_items, content_type="joke",
            personality=PersonalityType.FRIENDLY,
        )
        assert len(result) == len(sample_items)

    def test_professional_filters_tags(
        self, manager: PersonalityManager, sample_items: list[dict],
    ) -> None:
        """PROFESSIONAL filters to tech, science, business, productivity tags."""
        result = manager.filter_content(
            sample_items, content_type="fact",
            personality=PersonalityType.PROFESSIONAL,
        )
        # Should keep: j1 (tech), j3 (science), j4 (no tags), j5 (business)
        ids = [item["id"] for item in result]
        assert "j1" in ids  # tech tag
        assert "j3" in ids  # science tag
        assert "j4" in ids  # no tags -> passes through
        assert "j5" in ids  # business tag
        assert "j2" not in ids  # food/humor -> filtered out
        assert "j6" not in ids  # animals -> filtered out

    def test_professional_blocks_jokes(
        self, manager: PersonalityManager, sample_items: list[dict],
    ) -> None:
        """PROFESSIONAL personality blocks joke content type entirely."""
        result = manager.filter_content(
            sample_items, content_type="joke",
            personality=PersonalityType.PROFESSIONAL,
        )
        assert result == []

    def test_minimal_caps_at_one(
        self, manager: PersonalityManager, sample_items: list[dict],
    ) -> None:
        """MINIMAL personality caps results at 1 item."""
        result = manager.filter_content(
            sample_items, content_type="fact",
            personality=PersonalityType.MINIMAL,
        )
        assert len(result) <= 1

    def test_minimal_blocks_jokes(
        self, manager: PersonalityManager, sample_items: list[dict],
    ) -> None:
        """MINIMAL personality blocks joke content type."""
        result = manager.filter_content(
            sample_items, content_type="joke",
            personality=PersonalityType.MINIMAL,
        )
        assert result == []

    def test_playful_allows_all(
        self, manager: PersonalityManager, sample_items: list[dict],
    ) -> None:
        """PLAYFUL personality allows all items (no filtering)."""
        result = manager.filter_content(
            sample_items, content_type="joke",
            personality=PersonalityType.PLAYFUL,
        )
        assert len(result) == len(sample_items)

    def test_empty_items_returns_empty(
        self, manager: PersonalityManager,
    ) -> None:
        """Filtering an empty list returns an empty list."""
        result = manager.filter_content(
            [], content_type="joke",
            personality=PersonalityType.FRIENDLY,
        )
        assert result == []

    def test_filter_reads_personality_from_settings(
        self, manager: PersonalityManager, sample_items: list[dict],
    ) -> None:
        """filter_content reads personality from settings when not overridden."""
        manager.set_personality(PersonalityType.PROFESSIONAL)
        # Without passing personality= override, should use saved PROFESSIONAL
        result = manager.filter_content(sample_items, content_type="joke")
        # PROFESSIONAL blocks jokes
        assert result == []

    def test_no_content_type_skips_type_check(
        self, manager: PersonalityManager, sample_items: list[dict],
    ) -> None:
        """When content_type is empty, only tag filtering applies."""
        result = manager.filter_content(
            sample_items, content_type="",
            personality=PersonalityType.PROFESSIONAL,
        )
        # Should only filter by tags (tech, science, business, productivity)
        ids = [item["id"] for item in result]
        assert "j1" in ids  # tech
        assert "j3" in ids  # science
        assert "j4" in ids  # no tags
        assert "j5" in ids  # business

    def test_filter_content_with_string_tags(
        self, manager: PersonalityManager,
    ) -> None:
        """String tags (not list) should not crash — item included as untagged."""
        items = [
            {"id": 1, "tags": "programming"},  # string, not list
            {"id": 2, "tags": ["tech"]},
        ]
        result = manager.filter_content(
            items, personality=PersonalityType.PROFESSIONAL,
        )
        # Item with string tags is included (treated as untagged)
        assert any(i["id"] == 1 for i in result)

    def test_filter_content_with_int_tags(
        self, manager: PersonalityManager,
    ) -> None:
        """Int tags should not crash — item included as untagged."""
        items = [
            {"id": 1, "tags": 42},  # int, not list
        ]
        result = manager.filter_content(
            items, personality=PersonalityType.PROFESSIONAL,
        )
        assert len(result) == 1

    def test_filter_content_custom_personality(
        self, manager: PersonalityManager,
    ) -> None:
        """CUSTOM personality should include all items (empty tag filter)."""
        items = [
            {"id": 1, "tags": ["tech"]},
            {"id": 2, "tags": ["humor"]},
            {"id": 3, "tags": ["personal"]},
        ]
        result = manager.filter_content(items, personality=PersonalityType.CUSTOM)
        assert len(result) == len(items)


# ===========================================================================
# TestGetTone
# ===========================================================================

class TestGetTone:
    """Tests for PersonalityManager.get_tone()."""

    def test_friendly_tone(self, manager: PersonalityManager) -> None:
        """FRIENDLY tone has warm greeting and moderate humor."""
        tone = manager.get_tone(personality=PersonalityType.FRIENDLY)
        assert tone["warmth"] == "high"
        assert tone["humor"] == "moderate"
        assert tone["style"] == "conversational"

    def test_professional_tone(self, manager: PersonalityManager) -> None:
        """PROFESSIONAL tone is formal with no humor."""
        tone = manager.get_tone(personality=PersonalityType.PROFESSIONAL)
        assert tone["warmth"] == "low"
        assert tone["humor"] == "none"
        assert tone["style"] == "formal"
        assert tone["verbosity"] == "concise"

    def test_minimal_tone(self, manager: PersonalityManager) -> None:
        """MINIMAL tone is terse with no warmth."""
        tone = manager.get_tone(personality=PersonalityType.MINIMAL)
        assert tone["warmth"] == "none"
        assert tone["style"] == "terse"
        assert tone["verbosity"] == "minimal"

    def test_playful_tone(self, manager: PersonalityManager) -> None:
        """PLAYFUL tone is enthusiastic with heavy humor."""
        tone = manager.get_tone(personality=PersonalityType.PLAYFUL)
        assert tone["warmth"] == "very_high"
        assert tone["humor"] == "heavy"
        assert tone["style"] == "enthusiastic"
        assert tone["verbosity"] == "expressive"

    def test_custom_tone_merges_saved(
        self, manager: PersonalityManager,
    ) -> None:
        """CUSTOM tone merges saved custom parameters over defaults."""
        manager.set_custom_tone({"greeting": "Yarr!", "humor": "pirate"})
        tone = manager.get_tone(personality=PersonalityType.CUSTOM)
        assert tone["greeting"] == "Yarr!"
        assert tone["humor"] == "pirate"
        # Non-overridden keys should still be present from defaults
        assert "farewell" in tone
        assert "style" in tone

    def test_tone_reads_from_settings(
        self, manager: PersonalityManager,
    ) -> None:
        """get_tone reads personality from settings when not overridden."""
        manager.set_personality(PersonalityType.MINIMAL)
        tone = manager.get_tone()
        assert tone["style"] == "terse"

    def test_tone_has_all_required_keys(
        self, manager: PersonalityManager,
    ) -> None:
        """Every tone dict has all 8 required keys."""
        required = {"greeting", "farewell", "encouragement", "error",
                     "style", "warmth", "humor", "verbosity"}
        for p in PersonalityType:
            tone = manager.get_tone(personality=p)
            assert required.issubset(tone.keys()), (
                f"{p.value} tone missing keys: {required - tone.keys()}"
            )


# ===========================================================================
# TestListPersonalities
# ===========================================================================

class TestListPersonalities:
    """Tests for PersonalityManager.list_personalities()."""

    def test_lists_all_five(self, manager: PersonalityManager) -> None:
        """list_personalities returns all 5 personality types."""
        result = manager.list_personalities()
        assert len(result) == 5
        values = {p["value"] for p in result}
        assert values == {"professional", "friendly", "playful", "minimal", "custom"}
        # Each entry has name, value, description
        for entry in result:
            assert "name" in entry
            assert "value" in entry
            assert "description" in entry
            assert len(entry["description"]) > 0


# ===========================================================================
# TestSettingsPersistence
# ===========================================================================

class TestSettingsPersistence:
    """Tests for settings.json round-trip persistence."""

    def test_round_trip(self, settings_path: Path) -> None:
        """Personality survives write -> read cycle with other settings intact."""
        mgr = PersonalityManager(settings_path=settings_path)

        # Write some other setting first
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps({"theme": "dark", "language": "en"}) + "\n",
            encoding="utf-8",
        )

        # Set personality
        mgr.set_personality(PersonalityType.PLAYFUL)

        # Read back -- personality should be set AND other keys preserved
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert data["personality"] == "playful"
        assert data["theme"] == "dark"
        assert data["language"] == "en"

        # Manager should also read it correctly
        assert mgr.get_personality() == PersonalityType.PLAYFUL

    def test_corrupt_json_raises(self, settings_path: Path) -> None:
        """Corrupt JSON in settings.json raises JSONDecodeError, not silent failure."""
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("{invalid json", encoding="utf-8")
        mgr = PersonalityManager(settings_path=settings_path)
        with pytest.raises(json.JSONDecodeError):
            mgr.get_personality()
