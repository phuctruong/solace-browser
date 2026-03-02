"""
tests/test_delight_engine_celebration.py — First-Success Celebration Tests
SolaceBrowser: YinyangDelightEngine extension (celebrate_first_success, celebrate_milestone,
               get_encouragement, format_celebration)

Tests (10 total, 8+ required):
  TestCelebrateFirstSuccess  (4 tests) — header, recipe name, hash abbreviation, no hash
  TestCelebrateMilestone     (3 tests) — known thresholds, unknown threshold, type error
  TestGetEncouragement       (2 tests) — streak thresholds, below-minimum streak
  TestFormatCelebration      (3 tests) — with yinyang, without yinyang, type safety

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_delight_engine_celebration.py -v

Rung: 274177
DNA: delight(first_success | milestone | streak | format) → celebration_str → Anti-Clippy
"""

import sys
import unittest
from pathlib import Path

# Ensure src/ is on sys.path (unittest does not auto-discover like pytest fixtures)
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from yinyang.delight_engine import YinyangDelightEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine() -> YinyangDelightEngine:
    """Return a delight engine using default data (no custom dir needed)."""
    return YinyangDelightEngine()


# ---------------------------------------------------------------------------
# TestCelebrateFirstSuccess
# ---------------------------------------------------------------------------

class TestCelebrateFirstSuccess(unittest.TestCase):
    """Test celebrate_first_success() — P1 Gamification + P8 Care."""

    def setUp(self) -> None:
        self.engine = _make_engine()

    def test_header_present(self) -> None:
        """celebrate_first_success() includes the required header line."""
        result = self.engine.celebrate_first_success("gmail-compose")
        self.assertIn("Your first AI task is done!", result)

    def test_recipe_name_in_output(self) -> None:
        """celebrate_first_success() includes the recipe name."""
        result = self.engine.celebrate_first_success("substack-post")
        self.assertIn("substack-post", result)

    def test_evidence_verifiable_line_present(self) -> None:
        """celebrate_first_success() always includes the verifiability statement."""
        result = self.engine.celebrate_first_success("any-recipe")
        self.assertIn("Your evidence is sealed and verifiable.", result)

    def test_yinyang_art_included(self) -> None:
        """celebrate_first_success() includes Yinyang ASCII art."""
        result = self.engine.celebrate_first_success("any-recipe")
        # The art contains "Yinyang" label
        self.assertIn("Yinyang", result)

    def test_hash_abbreviated_in_output(self) -> None:
        """celebrate_first_success() abbreviates the evidence hash to first-8...last-4."""
        fake_hash = "a" * 8 + "b" * 20 + "c" * 4
        result = self.engine.celebrate_first_success(
            "linkedin-post",
            evidence_hash=fake_hash,
        )
        # Should contain abbreviated form, not the full 32-char hash
        self.assertIn("aaaaaaaa...cccc", result)
        self.assertNotIn(fake_hash, result)

    def test_no_hash_no_bundle_line(self) -> None:
        """When evidence_hash is None, no Bundle line appears."""
        result = self.engine.celebrate_first_success("test-recipe")
        self.assertNotIn("Bundle", result)

    def test_completion_time_included_when_provided(self) -> None:
        """celebrate_first_success() includes completion_time when provided."""
        result = self.engine.celebrate_first_success(
            "gmail-compose",
            completion_time="2.4s",
        )
        self.assertIn("2.4s", result)

    def test_invalid_recipe_name_type_raises(self) -> None:
        """celebrate_first_success() raises TypeError for non-string recipe_name."""
        with self.assertRaises(TypeError):
            self.engine.celebrate_first_success(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestCelebrateMilestone
# ---------------------------------------------------------------------------

class TestCelebrateMilestone(unittest.TestCase):
    """Test celebrate_milestone() — P1 Gamification milestone messages."""

    def setUp(self) -> None:
        self.engine = _make_engine()

    def test_first_milestone(self) -> None:
        """count=1 produces 'Your first recipe!'."""
        result = self.engine.celebrate_milestone("recipe", 1)
        self.assertEqual(result, "Your first recipe!")

    def test_tenth_milestone(self) -> None:
        """count=10 produces 'Your 10th recipe!'."""
        result = self.engine.celebrate_milestone("recipe", 10)
        self.assertEqual(result, "Your 10th recipe!")

    def test_hundredth_milestone(self) -> None:
        """count=100 produces 'Your 100th run!'."""
        result = self.engine.celebrate_milestone("run", 100)
        self.assertEqual(result, "Your 100th run!")

    def test_unknown_threshold_uses_count(self) -> None:
        """A count not in milestone map falls back to '{count}th'."""
        result = self.engine.celebrate_milestone("task", 42)
        self.assertIn("42th", result)
        self.assertIn("task", result)

    def test_fifth_milestone(self) -> None:
        """count=5 produces 'Your 5th recipe!'."""
        result = self.engine.celebrate_milestone("recipe", 5)
        self.assertEqual(result, "Your 5th recipe!")

    def test_invalid_milestone_type_raises(self) -> None:
        """celebrate_milestone() raises TypeError for non-string milestone."""
        with self.assertRaises(TypeError):
            self.engine.celebrate_milestone(123, 10)  # type: ignore[arg-type]

    def test_invalid_count_type_raises(self) -> None:
        """celebrate_milestone() raises TypeError for non-int count."""
        with self.assertRaises(TypeError):
            self.engine.celebrate_milestone("recipe", "ten")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestGetEncouragement
# ---------------------------------------------------------------------------

class TestGetEncouragement(unittest.TestCase):
    """Test get_encouragement() — P8 Care streak messages."""

    def setUp(self) -> None:
        self.engine = _make_engine()

    def test_streak_3_days(self) -> None:
        """3-day streak returns a message referencing momentum."""
        result = self.engine.get_encouragement(3)
        self.assertIn("3 days", result)

    def test_streak_7_days(self) -> None:
        """7-day streak returns a message referencing one full week."""
        result = self.engine.get_encouragement(7)
        self.assertIn("7", result)

    def test_streak_30_days(self) -> None:
        """30-day streak returns a month-level message."""
        result = self.engine.get_encouragement(30)
        self.assertIn("30", result)

    def test_streak_below_minimum_returns_default(self) -> None:
        """Streak below 3 returns the generic 'Keep going!' fallback."""
        result = self.engine.get_encouragement(1)
        self.assertIn("Keep going", result)

    def test_streak_above_90_returns_90_message(self) -> None:
        """Streak above the max threshold (90) still returns the 90-day message."""
        result = self.engine.get_encouragement(120)
        self.assertIn("90", result)

    def test_invalid_streak_type_raises(self) -> None:
        """get_encouragement() raises TypeError for non-int streak_days."""
        with self.assertRaises(TypeError):
            self.engine.get_encouragement("7")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestFormatCelebration
# ---------------------------------------------------------------------------

class TestFormatCelebration(unittest.TestCase):
    """Test format_celebration() — wrapper with optional Yinyang art."""

    def setUp(self) -> None:
        self.engine = _make_engine()

    def test_with_yinyang_includes_art(self) -> None:
        """format_celebration(include_yinyang=True) prepends Yinyang art."""
        result = self.engine.format_celebration("Great job!", include_yinyang=True)
        self.assertIn("Yinyang", result)
        self.assertIn("Great job!", result)

    def test_without_yinyang_no_art(self) -> None:
        """format_celebration(include_yinyang=False) skips Yinyang art."""
        result = self.engine.format_celebration("Great job!", include_yinyang=False)
        self.assertNotIn("Yinyang", result)
        self.assertIn("Great job!", result)

    def test_default_includes_yinyang(self) -> None:
        """format_celebration() defaults to include_yinyang=True."""
        result = self.engine.format_celebration("Well done!")
        self.assertIn("Yinyang", result)

    def test_message_preserved_exactly(self) -> None:
        """format_celebration() preserves the message text verbatim."""
        msg = "You did it! Evidence: abc123"
        result = self.engine.format_celebration(msg, include_yinyang=False)
        self.assertIn(msg, result)

    def test_invalid_message_type_raises(self) -> None:
        """format_celebration() raises TypeError for non-string message."""
        with self.assertRaises(TypeError):
            self.engine.format_celebration(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestAbbreviateHash — private helper, tested via public interface
# ---------------------------------------------------------------------------

class TestAbbreviateHash(unittest.TestCase):
    """Test the hash abbreviation logic (via celebrate_first_success)."""

    def setUp(self) -> None:
        self.engine = _make_engine()

    def test_short_hash_not_abbreviated(self) -> None:
        """Hashes shorter than 12 chars are returned unchanged."""
        short_hash = "abc123"
        result = self.engine.celebrate_first_success("r", evidence_hash=short_hash)
        self.assertIn("abc123", result)
        self.assertNotIn("...", result)

    def test_full_sha256_abbreviated_correctly(self) -> None:
        """A 64-char SHA-256 digest is abbreviated to first8...last4."""
        digest = "0" * 8 + "f" * 52 + "1234"
        result = self.engine.celebrate_first_success("r", evidence_hash=digest)
        self.assertIn("00000000...1234", result)


if __name__ == "__main__":
    unittest.main()
