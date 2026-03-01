"""
tests/test_yinyang_delight.py — YinyangDelightEngine Test Suite
SolaceBrowser B10 (original T16): Delight engine wiring

Tests (30+ required):
  TestRespond            (8 tests)  — warm_token categories, return structure, no crash
  TestCelebrate          (7 tests)  — each event type, fallback, generic
  TestHolidayTheme       (6 tests)  — Pi Day, normal day, year-wrapping, Tyson birthday
  TestKonami             (4 tests)  — correct/wrong sequence, reward, case insensitive
  TestDataLoading        (5 tests)  — custom dir, missing files, non-empty, no duplicates
  TestSessionTracking    (3 tests)  — seen tracking, reset, exhaustion cycling

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_yinyang_delight.py -v

Rung: 274177
"""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from yinyang.delight_engine import YinyangDelightEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """Create a delight engine with default data directory."""
    return YinyangDelightEngine()


@pytest.fixture
def empty_data_dir(tmp_path):
    """Create an empty data directory (no JSON files)."""
    return tmp_path / "empty_yinyang"


@pytest.fixture
def engine_empty(empty_data_dir):
    """Create a delight engine with a missing data directory (uses fallbacks)."""
    return YinyangDelightEngine(data_dir=empty_data_dir)


@pytest.fixture
def custom_data_dir(tmp_path):
    """Create a custom data directory with minimal test data."""
    data_dir = tmp_path / "custom_yinyang"
    data_dir.mkdir()

    jokes = {
        "jokes": [
            {"id": "custom_j1", "text": "Custom joke one.", "tags": ["test"]},
            {"id": "custom_j2", "text": "Custom joke two.", "tags": ["test"]},
        ]
    }
    facts = {
        "facts": [
            {"id": "custom_f1", "text": "Custom fact one.", "tags": ["test"]},
        ]
    }
    celebrations = {
        "celebrations": [
            {
                "id": "custom_c1",
                "trigger": "first_run_complete",
                "message": "Custom first run!",
                "effect": "confetti",
                "sound": "ding",
            },
            {
                "id": "custom_c2",
                "trigger": "konami_code",
                "message": "Custom konami!",
                "effect": "emoji_rain",
                "emojis": ["crown"],
                "sound": "fanfare",
            },
        ]
    }
    holidays = {
        "holidays": [
            {
                "id": "custom_h1",
                "name": "Tyson's Birthday",
                "start": "03-09",
                "end": "03-09",
                "emojis": ["cake"],
                "color": "#FF69B4",
                "greetings": ["Happy Birthday Tyson!"],
            },
            {
                "id": "custom_h2",
                "name": "Pi Day",
                "start": "03-14",
                "end": "03-14",
                "emojis": ["pie"],
                "color": "#3498DB",
                "greetings": ["Happy Pi Day! 3.14159..."],
            },
            {
                "id": "custom_h3",
                "name": "New Year",
                "start": "12-31",
                "end": "01-02",
                "emojis": ["fireworks"],
                "color": "#FFD700",
                "greetings": ["Happy New Year!"],
            },
        ]
    }
    smalltalk = {
        "greetings_first": [
            {"id": "custom_s1", "text": "Custom greeting."},
        ],
        "idle": [
            {"id": "custom_s2", "text": "Custom idle."},
        ],
        "farewell": [
            {"id": "custom_s3", "text": "Custom farewell."},
        ],
    }

    (data_dir / "jokes.json").write_text(json.dumps(jokes), encoding="utf-8")
    (data_dir / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    (data_dir / "celebrations.json").write_text(json.dumps(celebrations), encoding="utf-8")
    (data_dir / "holidays.json").write_text(json.dumps(holidays), encoding="utf-8")
    (data_dir / "smalltalk.json").write_text(json.dumps(smalltalk), encoding="utf-8")

    return data_dir


@pytest.fixture
def engine_custom(custom_data_dir):
    """Create a delight engine with custom data directory."""
    return YinyangDelightEngine(data_dir=custom_data_dir)


# ---------------------------------------------------------------------------
# TestRespond — warm_token dispatch + return structure
# ---------------------------------------------------------------------------

class TestRespond:
    """Test respond() method with various warm_tokens."""

    def test_respond_joke_returns_valid_structure(self, engine):
        """respond('joke') returns dict with type, text, source keys."""
        result = engine.respond("joke")
        assert isinstance(result, dict)
        assert "type" in result
        assert "text" in result
        assert "source" in result
        assert result["type"] == "joke"
        assert len(result["text"]) > 0

    def test_respond_fact_returns_fact(self, engine):
        """respond('fact') returns a fact entry."""
        result = engine.respond("fact")
        assert result["type"] == "fact"
        assert len(result["text"]) > 0
        assert result["source"].startswith("facts.json#")

    def test_respond_trivia_returns_fact(self, engine):
        """respond('trivia') is an alias for fact."""
        result = engine.respond("trivia")
        assert result["type"] == "fact"

    def test_respond_hello_returns_smalltalk(self, engine):
        """respond('hello') returns a greeting smalltalk."""
        result = engine.respond("hello")
        assert result["type"] == "smalltalk"
        assert len(result["text"]) > 0

    def test_respond_bye_returns_farewell(self, engine):
        """respond('bye') returns a farewell smalltalk."""
        result = engine.respond("bye")
        assert result["type"] == "smalltalk"

    def test_respond_unknown_token_returns_something(self, engine):
        """respond() with unknown token returns random joke/fact/smalltalk."""
        result = engine.respond("xyzzy_unknown_token")
        assert result["type"] in ("joke", "fact", "smalltalk")
        assert len(result["text"]) > 0

    def test_respond_case_insensitive(self, engine):
        """respond() is case-insensitive."""
        result = engine.respond("JOKE")
        assert result["type"] == "joke"

    def test_respond_whitespace_trimmed(self, engine):
        """respond() trims whitespace from warm_token."""
        result = engine.respond("  fact  ")
        assert result["type"] == "fact"


# ---------------------------------------------------------------------------
# TestCelebrate — event-based celebrations
# ---------------------------------------------------------------------------

class TestCelebrate:
    """Test celebrate() method for key moments."""

    def test_celebrate_first_run(self, engine):
        """celebrate('first_run') returns a celebration."""
        result = engine.celebrate("first_run")
        assert isinstance(result, dict)
        assert "text" in result
        assert "emoji" in result
        assert "effect" in result
        assert "sound" in result
        assert len(result["text"]) > 0

    def test_celebrate_first_run_complete(self, engine):
        """celebrate('first_run_complete') returns from celebrations.json."""
        result = engine.celebrate("first_run_complete")
        assert len(result["text"]) > 0

    def test_celebrate_streak_7_days(self, engine):
        """celebrate('streak_7_days') returns streak celebration."""
        result = engine.celebrate("streak_7_days")
        assert len(result["text"]) > 0

    def test_celebrate_konami_code(self, engine):
        """celebrate('konami_code') returns the konami celebration."""
        result = engine.celebrate("konami_code")
        assert "easter egg" in result["text"].lower() or "culture" in result["text"].lower()

    def test_celebrate_unknown_event_returns_generic(self, engine):
        """celebrate() with unknown event returns generic celebration."""
        result = engine.celebrate("totally_made_up_event_xyz")
        assert len(result["text"]) > 0
        assert result["effect"] == "sparkles"

    def test_celebrate_custom_data(self, engine_custom):
        """celebrate() uses custom data directory."""
        result = engine_custom.celebrate("first_run_complete")
        assert result["text"] == "Custom first run!"

    def test_celebrate_case_insensitive(self, engine):
        """celebrate() is case-insensitive."""
        result = engine.celebrate("KONAMI_CODE")
        assert len(result["text"]) > 0


# ---------------------------------------------------------------------------
# TestHolidayTheme — date-based holiday detection
# ---------------------------------------------------------------------------

class TestHolidayTheme:
    """Test get_holiday_theme() for special days."""

    def test_pi_day_returns_theme(self, engine):
        """March 14 returns Pi Day theme."""
        result = engine.get_holiday_theme(check_date=date(2026, 3, 14))
        assert result is not None
        assert result["name"] == "Pi Day"
        assert "theme_color" in result
        assert "greeting" in result

    def test_normal_day_returns_none(self, engine):
        """A normal day (no holiday) returns None."""
        # June 15 is not a holiday in the default dataset
        result = engine.get_holiday_theme(check_date=date(2026, 6, 15))
        assert result is None

    def test_tysons_birthday_custom(self, engine_custom):
        """March 9 returns Tyson's Birthday from custom data."""
        result = engine_custom.get_holiday_theme(check_date=date(2026, 3, 9))
        assert result is not None
        assert result["name"] == "Tyson's Birthday"
        assert result["theme_color"] == "#FF69B4"
        assert "Happy Birthday Tyson" in result["greeting"]

    def test_year_wrapping_range(self, engine_custom):
        """Year-wrapping holiday range (Dec 31 - Jan 2) detected correctly."""
        # Dec 31 should match New Year
        result = engine_custom.get_holiday_theme(check_date=date(2026, 12, 31))
        assert result is not None
        assert result["name"] == "New Year"

        # Jan 1 should also match
        result_jan1 = engine_custom.get_holiday_theme(check_date=date(2027, 1, 1))
        assert result_jan1 is not None
        assert result_jan1["name"] == "New Year"

    def test_holiday_has_emojis(self, engine):
        """Holiday theme includes emojis list."""
        result = engine.get_holiday_theme(check_date=date(2026, 3, 14))
        assert result is not None
        assert "emojis" in result
        assert isinstance(result["emojis"], list)

    def test_today_returns_valid_or_none(self, engine):
        """get_holiday_theme() with no argument checks today, returns valid or None."""
        result = engine.get_holiday_theme()
        if result is not None:
            assert "name" in result
            assert "greeting" in result
            assert "theme_color" in result


# ---------------------------------------------------------------------------
# TestKonami — Konami code detection + reward
# ---------------------------------------------------------------------------

class TestKonami:
    """Test Konami code detection and reward."""

    def test_correct_konami_sequence(self, engine):
        """Correct Konami code returns True."""
        sequence = ["up", "up", "down", "down", "left", "right", "left", "right", "b", "a"]
        assert engine.check_konami(sequence) is True

    def test_wrong_konami_sequence(self, engine):
        """Wrong sequence returns False."""
        sequence = ["up", "down", "up", "down", "left", "right", "left", "right", "b", "a"]
        assert engine.check_konami(sequence) is False

    def test_short_sequence_returns_false(self, engine):
        """Too-short sequence returns False."""
        assert engine.check_konami(["up", "up"]) is False

    def test_empty_sequence_returns_false(self, engine):
        """Empty sequence returns False."""
        assert engine.check_konami([]) is False

    def test_konami_case_insensitive(self, engine):
        """Konami code matching is case-insensitive."""
        sequence = ["UP", "Up", "DOWN", "down", "LEFT", "Right", "left", "RIGHT", "B", "A"]
        assert engine.check_konami(sequence) is True

    def test_konami_reward_returns_valid(self, engine):
        """get_konami_reward() returns a reward with expected keys."""
        reward = engine.get_konami_reward()
        assert isinstance(reward, dict)
        assert "text" in reward
        assert "effect" in reward
        assert "sound" in reward
        assert "unlocked" in reward
        assert reward["unlocked"] is True
        assert len(reward["text"]) > 0

    def test_konami_reward_custom_data(self, engine_custom):
        """get_konami_reward() uses custom data when available."""
        reward = engine_custom.get_konami_reward()
        assert reward["text"] == "Custom konami!"
        assert reward["unlocked"] is True


# ---------------------------------------------------------------------------
# TestDataLoading — custom dirs, missing files, integrity
# ---------------------------------------------------------------------------

class TestDataLoading:
    """Test data loading, fallbacks, and integrity."""

    def test_custom_data_dir_loads(self, engine_custom):
        """Engine loads data from custom directory."""
        jokes = engine_custom.get_jokes()
        assert len(jokes) == 2
        assert jokes[0]["id"] == "custom_j1"

    def test_missing_data_dir_uses_fallbacks(self, engine_empty):
        """Engine with missing data directory uses fallback data without crashing."""
        result = engine_empty.respond("joke")
        assert result["type"] == "joke"
        assert len(result["text"]) > 0

    def test_default_jokes_non_empty(self, engine):
        """Default jokes database is non-empty."""
        jokes = engine.get_jokes()
        assert len(jokes) > 0

    def test_default_facts_non_empty(self, engine):
        """Default facts database is non-empty."""
        facts = engine.get_facts()
        assert len(facts) > 0

    def test_no_duplicate_joke_ids(self, engine):
        """No duplicate IDs in jokes database."""
        jokes = engine.get_jokes()
        ids = [j.get("id") for j in jokes if j.get("id")]
        assert len(ids) == len(set(ids)), f"Duplicate joke IDs found: {[i for i in ids if ids.count(i) > 1]}"

    def test_no_duplicate_fact_ids(self, engine):
        """No duplicate IDs in facts database."""
        facts = engine.get_facts()
        ids = [f.get("id") for f in facts if f.get("id")]
        assert len(ids) == len(set(ids)), f"Duplicate fact IDs found: {[i for i in ids if ids.count(i) > 1]}"

    def test_no_duplicate_holiday_ids(self, engine):
        """No duplicate IDs in holidays database."""
        holidays = engine.get_holidays()
        ids = [h.get("id") for h in holidays if h.get("id")]
        assert len(ids) == len(set(ids)), f"Duplicate holiday IDs found"

    def test_corrupt_json_uses_fallback(self, tmp_path):
        """Corrupt JSON file triggers fallback, not crash."""
        data_dir = tmp_path / "corrupt_yinyang"
        data_dir.mkdir()
        (data_dir / "jokes.json").write_text("NOT VALID JSON {{{", encoding="utf-8")

        engine = YinyangDelightEngine(data_dir=data_dir)
        result = engine.respond("joke")
        assert result["type"] == "joke"
        assert len(result["text"]) > 0

    def test_empty_json_uses_fallback(self, tmp_path):
        """JSON file with empty list triggers fallback, not crash."""
        data_dir = tmp_path / "empty_json_yinyang"
        data_dir.mkdir()
        (data_dir / "jokes.json").write_text(json.dumps({"jokes": []}), encoding="utf-8")

        engine = YinyangDelightEngine(data_dir=data_dir)
        result = engine.respond("joke")
        assert result["type"] == "joke"
        assert len(result["text"]) > 0


# ---------------------------------------------------------------------------
# TestSessionTracking — seen tracking + reset
# ---------------------------------------------------------------------------

class TestSessionTracking:
    """Test session-based seen tracking to avoid repeats."""

    def test_jokes_avoid_repeats(self, engine_custom):
        """Within a session, jokes avoid repeats until exhausted."""
        seen_texts = set()
        # Custom data has 2 jokes, so 2 calls should give 2 unique jokes
        for _ in range(2):
            result = engine_custom.respond("joke")
            seen_texts.add(result["text"])
        assert len(seen_texts) == 2

    def test_exhausted_jokes_cycle(self, engine_custom):
        """After all jokes are seen, tracking resets and jokes repeat."""
        # Custom data has 2 jokes. 3 calls should work without error.
        results = []
        for _ in range(3):
            result = engine_custom.respond("joke")
            results.append(result["text"])
        assert len(results) == 3
        # At least one repeat
        assert len(set(results)) <= 2

    def test_reset_seen_clears_tracking(self, engine_custom):
        """reset_seen() clears all tracking sets."""
        # See both jokes
        engine_custom.respond("joke")
        engine_custom.respond("joke")
        # Reset
        engine_custom.reset_seen()
        # Should be able to get both again
        seen = set()
        for _ in range(2):
            result = engine_custom.respond("joke")
            seen.add(result["text"])
        assert len(seen) == 2


# ---------------------------------------------------------------------------
# TestAntiClippy — delight is invited, never imposed
# ---------------------------------------------------------------------------

class TestAntiClippy:
    """Verify Anti-Clippy principles in the delight engine."""

    def test_respond_requires_warm_token(self, engine):
        """respond() requires an explicit warm_token — no auto-trigger."""
        # respond() with empty string still works but doesn't crash
        result = engine.respond("")
        assert isinstance(result, dict)
        assert "type" in result

    def test_celebrate_requires_explicit_event(self, engine):
        """celebrate() requires an explicit event string."""
        result = engine.celebrate("")
        assert isinstance(result, dict)
        assert len(result["text"]) > 0

    def test_no_auto_expansion_in_engine(self, engine):
        """The engine itself never triggers UI expansion — it only returns data."""
        # The engine returns dicts, never mutates UI state
        result = engine.respond("joke")
        assert "auto_expand" not in result
        assert "auto_collapse" not in result
