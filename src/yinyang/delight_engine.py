"""YinyangDelightEngine — warmth, humor, and personality for Yinyang interactions.

Anti-Clippy: Never interrupts. Never auto-expands. Never presumes.
Only responds when invited via warm_token or celebrate().

Loads joke/fact/smalltalk/celebration/holiday databases from
data/default/yinyang/ JSON files. Falls back to minimal built-in
defaults if files are missing — never crashes on missing data.

Channel [7] — Context + Tools.  Rung: 65537.
DNA: delight(warm_token | celebrate | holiday | konami) → {type, text, source} → Anti-Clippy
"""
from __future__ import annotations

import json
import logging
import random
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("solace-browser.yinyang.delight")

# Default data directory (relative to project root)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_DATA_DIR = _PROJECT_ROOT / "data" / "default" / "yinyang"

# Konami code sequence
_KONAMI_SEQUENCE = [
    "up", "up", "down", "down",
    "left", "right", "left", "right",
    "b", "a",
]

# Minimal built-in fallback data (used only when JSON files are missing)
_FALLBACK_JOKES = [
    {"id": "j001", "text": "Why do programmers prefer dark mode? Because light attracts bugs.", "tags": ["programming"]},
]

_FALLBACK_FACTS = [
    {"id": "f001", "text": "The first computer bug was a real moth found in a Harvard Mark II in 1947.", "tags": ["tech"]},
]

_FALLBACK_SMALLTALK: dict[str, list[dict[str, str]]] = {
    "greetings_first": [{"id": "s001", "text": "What are we building today?"}],
    "greetings_return": [{"id": "s010", "text": "Welcome back."}],
    "idle": [{"id": "s020", "text": "Still here. Still ready."}],
    "curiosity": [{"id": "s030", "text": "Did you know the first webcam was invented just to check if a coffee pot was empty?"}],
    "playful": [{"id": "s040", "text": "I'd tell you a joke, but my humor module is still in beta."}],
    "encouragement": [{"id": "s070", "text": "You're making good progress. Seriously."}],
    "farewell": [{"id": "s080", "text": "See you next time. I'll be here."}],
}

_FALLBACK_CELEBRATIONS: dict[str, dict[str, str]] = {
    "first_run": {"text": "Your first app run! Welcome to the Solace family.", "emoji": "party_popper"},
    "app_installed": {"text": "New app installed! Your AI worker is growing.", "emoji": "package"},
    "run_complete": {"text": "Run complete! Evidence sealed and verified.", "emoji": "check_mark"},
    "streak_3": {"text": "3 runs in a row! You're building momentum.", "emoji": "fire"},
    "streak_7": {"text": "7-day streak! Consistency is the secret.", "emoji": "star"},
}

_FALLBACK_HOLIDAYS: list[dict[str, Any]] = [
    {"id": "h010", "name": "Pi Day", "start": "03-14", "end": "03-14",
     "emojis": ["pi"], "color": "#4169E1",
     "greetings": ["Happy Pi Day! 3.14159..."]},
]

# Warm token categories that map to data sources
_WARM_TOKEN_MAP: dict[str, str] = {
    "joke": "joke",
    "humor": "joke",
    "funny": "joke",
    "laugh": "joke",
    "fact": "fact",
    "learn": "fact",
    "trivia": "fact",
    "did_you_know": "fact",
    "hello": "smalltalk",
    "hi": "smalltalk",
    "greet": "smalltalk",
    "greeting": "smalltalk",
    "welcome": "smalltalk",
    "idle": "smalltalk",
    "bored": "smalltalk",
    "encourage": "smalltalk",
    "bye": "smalltalk",
    "farewell": "smalltalk",
    "celebrate": "celebration",
    "holiday": "holiday",
}


class YinyangDelightEngine:
    """Delight engine that adds warmth, humor, and personality to Yinyang interactions.

    Anti-Clippy: Never interrupts. Never auto-expands. Never presumes.
    Only responds when invited via warm_token or celebrate().
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        """Load joke/fact/smalltalk/celebration/holiday databases from data_dir or defaults."""
        self._data_dir = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR
        self._jokes: list[dict[str, Any]] = []
        self._facts: list[dict[str, Any]] = []
        self._smalltalk: dict[str, list[dict[str, Any]]] = {}
        self._celebrations: list[dict[str, Any]] = []
        self._holidays: list[dict[str, Any]] = []
        self._seen_joke_ids: set[str] = set()
        self._seen_fact_ids: set[str] = set()
        self._seen_smalltalk_ids: set[str] = set()

        self._load_data()

    def _load_data(self) -> None:
        """Load all JSON databases, falling back to built-in defaults on missing files."""
        self._jokes = self._load_json_list("jokes.json", "jokes", _FALLBACK_JOKES)
        self._facts = self._load_json_list("facts.json", "facts", _FALLBACK_FACTS)
        self._celebrations = self._load_json_list("celebrations.json", "celebrations", [])
        self._holidays = self._load_json_list("holidays.json", "holidays", _FALLBACK_HOLIDAYS)
        self._smalltalk = self._load_smalltalk()

    def _load_json_list(
        self, filename: str, key: str, fallback: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Load a list from a JSON file under data_dir. Falls back on missing/corrupt file."""
        filepath = self._data_dir / filename
        try:
            raw = json.loads(filepath.read_text(encoding="utf-8"))
            items = raw.get(key, [])
            if isinstance(items, list) and len(items) > 0:
                return items
            logger.warning("Empty or invalid key '%s' in %s, using fallback", key, filepath)
            return list(fallback)
        except FileNotFoundError:
            logger.info("Data file not found: %s, using fallback", filepath)
            return list(fallback)
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("Failed to parse %s: %s, using fallback", filepath, exc)
            return list(fallback)

    def _load_smalltalk(self) -> dict[str, list[dict[str, Any]]]:
        """Load smalltalk database with category-keyed structure."""
        filepath = self._data_dir / "smalltalk.json"
        try:
            raw = json.loads(filepath.read_text(encoding="utf-8"))
            result: dict[str, list[dict[str, Any]]] = {}
            for category in [
                "greetings_first", "greetings_return", "idle", "curiosity",
                "playful", "task_starters", "time_of_day", "encouragement", "farewell",
            ]:
                items = raw.get(category, [])
                if isinstance(items, list) and len(items) > 0:
                    result[category] = items
            if result:
                return result
            logger.warning("Empty smalltalk in %s, using fallback", filepath)
            return dict(_FALLBACK_SMALLTALK)
        except FileNotFoundError:
            logger.info("Smalltalk file not found: %s, using fallback", filepath)
            return dict(_FALLBACK_SMALLTALK)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse %s: %s, using fallback", filepath, exc)
            return dict(_FALLBACK_SMALLTALK)

    def respond(self, warm_token: str) -> dict[str, str]:
        """Generate a warm response to a user interaction.

        The warm_token selects the response type:
          - "joke", "humor", "funny", "laugh" -> joke from jokes.json
          - "fact", "learn", "trivia", "did_you_know" -> fact from facts.json
          - "hello", "hi", "greet", "greeting", "welcome" -> greeting smalltalk
          - "idle", "bored" -> idle smalltalk
          - "encourage" -> encouragement smalltalk
          - "bye", "farewell" -> farewell smalltalk
          - anything else -> random selection from joke/fact/smalltalk

        Returns: {type: "joke"|"fact"|"smalltalk", text: str, source: str}
        """
        token_lower = warm_token.strip().lower()
        category = _WARM_TOKEN_MAP.get(token_lower)

        if category == "joke":
            return self._pick_joke()
        elif category == "fact":
            return self._pick_fact()
        elif category == "smalltalk":
            return self._pick_smalltalk(token_lower)
        elif category == "celebration":
            return self._respond_as_celebration()
        elif category == "holiday":
            theme = self.get_holiday_theme()
            if theme is not None:
                return {
                    "type": "holiday",
                    "text": theme["greeting"],
                    "source": f"holidays.json#{theme['name']}",
                }
            return self._pick_fact()
        else:
            # Unknown token: pick randomly from joke, fact, or smalltalk
            return self._pick_random()

    def celebrate(self, event: str) -> dict[str, Any]:
        """Generate a celebration for a key moment.

        Supported events (matched by trigger field in celebrations.json):
          - "first_run", "first_run_complete"
          - "app_installed", "first_app_installed"
          - "run_complete"
          - "streak_3", "streak_7", "streak_7_days", "streak_30", "streak_30_days"
          - "konami_code"
          - Any other trigger defined in celebrations.json

        Falls back to a generic celebration if the event is not found.

        Returns: {text: str, emoji: str, effect: str, sound: str | None}
        """
        # Normalize event name for matching
        event_lower = event.strip().lower()

        # Build alias map for common event variations
        aliases: dict[str, str] = {
            "first_run": "first_run_complete",
            "app_installed": "first_app_installed",
            "streak_3": "milestone_10_runs",  # fallback
            "streak_7": "streak_7_days",
            "streak_30": "streak_30_days",
        }

        # Search celebrations by trigger
        celebration = self._find_celebration(event_lower)
        if celebration is None and event_lower in aliases:
            celebration = self._find_celebration(aliases[event_lower])

        if celebration is not None:
            return {
                "text": celebration.get("message", ""),
                "emoji": celebration.get("emojis", [""])[0] if "emojis" in celebration else "",
                "effect": celebration.get("effect", "sparkles"),
                "sound": celebration.get("sound") if celebration.get("sound") != "none" else None,
            }

        # Fallback to built-in celebration data
        fallback = _FALLBACK_CELEBRATIONS.get(event_lower)
        if fallback is not None:
            return {
                "text": fallback["text"],
                "emoji": fallback["emoji"],
                "effect": "sparkles",
                "sound": "ding",
            }

        # Generic fallback for unknown events
        return {
            "text": f"Milestone reached: {event}",
            "emoji": "star",
            "effect": "sparkles",
            "sound": "ding",
        }

    def get_holiday_theme(self, check_date: date | None = None) -> dict[str, Any] | None:
        """Check if today (or check_date) is a special day.

        Returns: {name: str, greeting: str, theme_color: str, emojis: list[str]} or None
        """
        today = check_date if check_date is not None else date.today()
        today_mmdd = f"{today.month:02d}-{today.day:02d}"

        for holiday in self._holidays:
            start = holiday.get("start", "")
            end = holiday.get("end", "")

            if not start or not end:
                continue

            if self._date_in_range(today_mmdd, start, end):
                greetings = holiday.get("greetings", [])
                greeting = random.choice(greetings) if greetings else holiday.get("name", "")
                return {
                    "name": holiday["name"],
                    "greeting": greeting,
                    "theme_color": holiday.get("color", "#FFFFFF"),
                    "emojis": holiday.get("emojis", []),
                }

        return None

    def check_konami(self, key_sequence: list[str]) -> bool:
        """Check if the key sequence matches the Konami code.

        The Konami code is: Up Up Down Down Left Right Left Right B A
        Case-insensitive matching.
        """
        if len(key_sequence) != len(_KONAMI_SEQUENCE):
            return False
        normalized = [k.strip().lower() for k in key_sequence]
        return normalized == _KONAMI_SEQUENCE

    def get_konami_reward(self) -> dict[str, Any]:
        """Return the easter egg reward for Konami code.

        Searches celebrations.json for the "konami_code" trigger.
        Falls back to a built-in reward if not found.
        """
        celebration = self._find_celebration("konami_code")
        if celebration is not None:
            return {
                "text": celebration.get("message", "You found the easter egg!"),
                "effect": celebration.get("effect", "emoji_rain"),
                "emojis": celebration.get("emojis", ["trophy", "crown", "star", "video_game"]),
                "sound": celebration.get("sound", "fanfare"),
                "unlocked": True,
            }
        return {
            "text": "You found the easter egg! You're clearly a person of culture.",
            "effect": "emoji_rain",
            "emojis": ["trophy", "crown", "star", "video_game"],
            "sound": "fanfare",
            "unlocked": True,
        }

    def get_jokes(self) -> list[dict[str, Any]]:
        """Return all loaded jokes. For inspection/testing."""
        return list(self._jokes)

    def get_facts(self) -> list[dict[str, Any]]:
        """Return all loaded facts. For inspection/testing."""
        return list(self._facts)

    def get_smalltalk(self) -> dict[str, list[dict[str, Any]]]:
        """Return all loaded smalltalk categories. For inspection/testing."""
        return dict(self._smalltalk)

    def get_celebrations(self) -> list[dict[str, Any]]:
        """Return all loaded celebrations. For inspection/testing."""
        return list(self._celebrations)

    def get_holidays(self) -> list[dict[str, Any]]:
        """Return all loaded holidays. For inspection/testing."""
        return list(self._holidays)

    def reset_seen(self) -> None:
        """Reset the seen-tracking sets (new session)."""
        self._seen_joke_ids.clear()
        self._seen_fact_ids.clear()
        self._seen_smalltalk_ids.clear()

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _pick_joke(self) -> dict[str, str]:
        """Pick a random joke, avoiding repeats within session."""
        item = self._pick_unseen(self._jokes, self._seen_joke_ids)
        return {
            "type": "joke",
            "text": item.get("text", ""),
            "source": f"jokes.json#{item.get('id', 'unknown')}",
        }

    def _pick_fact(self) -> dict[str, str]:
        """Pick a random fact, avoiding repeats within session."""
        item = self._pick_unseen(self._facts, self._seen_fact_ids)
        return {
            "type": "fact",
            "text": item.get("text", ""),
            "source": f"facts.json#{item.get('id', 'unknown')}",
        }

    def _pick_smalltalk(self, token: str) -> dict[str, str]:
        """Pick smalltalk based on the warm_token category."""
        # Map tokens to smalltalk categories
        category_map: dict[str, str] = {
            "hello": "greetings_first",
            "hi": "greetings_first",
            "greet": "greetings_first",
            "greeting": "greetings_first",
            "welcome": "greetings_first",
            "idle": "idle",
            "bored": "idle",
            "encourage": "encouragement",
            "bye": "farewell",
            "farewell": "farewell",
        }
        category = category_map.get(token, "greetings_first")
        items = self._smalltalk.get(category, [])
        if not items:
            # Fall back to any category with content
            for cat_items in self._smalltalk.values():
                if cat_items:
                    items = cat_items
                    break
        if not items:
            return {
                "type": "smalltalk",
                "text": "Hello.",
                "source": "fallback",
            }
        item = self._pick_unseen(items, self._seen_smalltalk_ids)
        return {
            "type": "smalltalk",
            "text": item.get("text", ""),
            "source": f"smalltalk.json#{item.get('id', 'unknown')}",
        }

    def _respond_as_celebration(self) -> dict[str, str]:
        """Pick a celebration as a respond() result."""
        if self._celebrations:
            item = random.choice(self._celebrations)
            return {
                "type": "celebration",
                "text": item.get("message", ""),
                "source": f"celebrations.json#{item.get('id', 'unknown')}",
            }
        return {
            "type": "celebration",
            "text": "Something worth celebrating!",
            "source": "fallback",
        }

    def _pick_random(self) -> dict[str, str]:
        """Pick randomly from joke, fact, or smalltalk."""
        choice = random.choice(["joke", "fact", "smalltalk"])
        if choice == "joke":
            return self._pick_joke()
        elif choice == "fact":
            return self._pick_fact()
        else:
            # Pick from a random smalltalk category
            categories = list(self._smalltalk.keys())
            if categories:
                cat = random.choice(categories)
                items = self._smalltalk[cat]
                if items:
                    item = self._pick_unseen(items, self._seen_smalltalk_ids)
                    return {
                        "type": "smalltalk",
                        "text": item.get("text", ""),
                        "source": f"smalltalk.json#{item.get('id', 'unknown')}",
                    }
            return self._pick_fact()

    def _pick_unseen(
        self, items: list[dict[str, Any]], seen_set: set[str]
    ) -> dict[str, Any]:
        """Pick a random item not yet seen in this session.

        If all items have been seen, resets the tracking and picks fresh.
        """
        unseen = [item for item in items if item.get("id", "") not in seen_set]
        if not unseen:
            # All seen — reset and allow repeats
            seen_set.clear()
            unseen = list(items)
        if not unseen:
            return {"id": "fallback", "text": "Hello."}
        choice = random.choice(unseen)
        item_id = choice.get("id", "")
        if item_id:
            seen_set.add(item_id)
        return choice

    def _find_celebration(self, trigger: str) -> dict[str, Any] | None:
        """Find a celebration by its trigger field."""
        for c in self._celebrations:
            if c.get("trigger", "").lower() == trigger:
                return c
        return None

    # -----------------------------------------------------------------------
    # First-success celebration (P1 Gamification + P8 Care)
    # -----------------------------------------------------------------------

    # ASCII Yinyang art — 5 lines, pure ASCII, no external deps
    _YINYANG_ART: str = (
        "    .oOo.\n"
        "   (  (  )\n"
        "   (o  o )\n"
        "    `oOo'\n"
        "  ~ Yinyang ~"
    )

    # Milestone thresholds + labels (P1 Gamification)
    _MILESTONE_MAP: dict[int, str] = {
        1: "first",
        5: "5th",
        10: "10th",
        25: "25th",
        50: "50th",
        100: "100th",
        500: "500th",
        1000: "1000th",
    }

    # Streak thresholds + messages (P8 Care)
    _STREAK_MAP: dict[int, str] = {
        3:  "3 days in a row — you're building momentum.",
        7:  "7-day streak! One full week of consistency.",
        14: "14 days — two weeks of discipline. You're for real.",
        30: "30-day streak! A month of daily practice.",
        60: "60 days — two months. This is a habit now.",
        90: "90 days — mastery is forming. Keep going.",
    }

    def celebrate_first_success(
        self,
        recipe_name: str,
        completion_time: str | None = None,
        evidence_hash: str | None = None,
    ) -> str:
        """Return a first-success celebration message for a completed recipe.

        Includes:
          - Header with yinyang art
          - Recipe name and optional completion time
          - Abbreviated evidence bundle hash
          - Verifiability statement

        Args:
            recipe_name:     Name of the recipe that completed.
            completion_time: Human-readable elapsed time (e.g. "1.3s"). Optional.
            evidence_hash:   Full SHA-256 hex digest of the evidence bundle. Optional.

        Returns:
            Multi-line celebration string suitable for terminal output.
        """
        if not isinstance(recipe_name, str):
            raise TypeError(f"recipe_name must be str, got {type(recipe_name).__name__}")

        lines: list[str] = []
        lines.append(self._YINYANG_ART)
        lines.append("")
        lines.append("Your first AI task is done!")
        lines.append("")
        lines.append(f"  Recipe : {recipe_name}")

        if completion_time is not None:
            lines.append(f"  Time   : {completion_time}")

        if evidence_hash is not None:
            # Abbreviate: first 8 + "..." + last 4 characters
            abbrev = self._abbreviate_hash(evidence_hash)
            lines.append(f"  Bundle : {abbrev}")

        lines.append("")
        lines.append("Your evidence is sealed and verifiable.")

        return "\n".join(lines)

    def celebrate_milestone(self, milestone: str, count: int) -> str:
        """Return a milestone celebration message.

        Milestone thresholds: 1, 5, 10, 25, 50, 100, 500, 1000.
        Picks the highest threshold not exceeding count, or uses count
        verbatim if it does not match any known milestone.

        Args:
            milestone: Category label (e.g. "recipe", "run", "task").
            count:     Number of completions.

        Returns:
            Celebration string (e.g. "Your 10th recipe!").
        """
        if not isinstance(milestone, str):
            raise TypeError(f"milestone must be str, got {type(milestone).__name__}")
        if not isinstance(count, int):
            raise TypeError(f"count must be int, got {type(count).__name__}")

        # Find the highest known threshold that matches exactly
        ordinal = self._MILESTONE_MAP.get(count)
        if ordinal is None:
            # Not a recognised threshold — use plain count
            ordinal = f"{count}th"

        label = milestone.strip() or "task"
        return f"Your {ordinal} {label}!"

    def get_encouragement(self, streak_days: int) -> str:
        """Return a streak-based encouragement message.

        Streak thresholds: 3, 7, 14, 30, 60, 90 days.
        Returns the message for the highest threshold not exceeding streak_days.
        Returns a neutral "Keep going!" for streaks below the lowest threshold.

        Args:
            streak_days: Number of consecutive days of activity.

        Returns:
            Encouragement string.
        """
        if not isinstance(streak_days, int):
            raise TypeError(f"streak_days must be int, got {type(streak_days).__name__}")

        best_threshold = 0
        best_message = "Keep going! Every day builds momentum."

        for threshold, message in self._STREAK_MAP.items():
            if streak_days >= threshold and threshold >= best_threshold:
                best_threshold = threshold
                best_message = message

        return best_message

    def format_celebration(
        self,
        message: str,
        include_yinyang: bool = True,
    ) -> str:
        """Wrap an arbitrary celebration message with optional ASCII Yinyang art.

        Args:
            message:         The celebration message to wrap.
            include_yinyang: When True (default), prepend the Yinyang ASCII art.

        Returns:
            Formatted string ready for terminal display.
        """
        if not isinstance(message, str):
            raise TypeError(f"message must be str, got {type(message).__name__}")

        parts: list[str] = []
        if include_yinyang:
            parts.append(self._YINYANG_ART)
            parts.append("")
        parts.append(message)
        return "\n".join(parts)

    # -----------------------------------------------------------------------
    # Private helper — hash abbreviation
    # -----------------------------------------------------------------------

    @staticmethod
    def _abbreviate_hash(digest: str) -> str:
        """Shorten a hex digest to first-8 + '...' + last-4 characters.

        If digest is shorter than 12 characters, returns it unchanged.
        """
        if len(digest) < 12:
            return digest
        return f"{digest[:8]}...{digest[-4:]}"

    @staticmethod
    def _date_in_range(today_mmdd: str, start_mmdd: str, end_mmdd: str) -> bool:
        """Check if today (MM-DD) falls within [start, end] range.

        Handles year-wrapping ranges (e.g., start=12-31, end=01-02).
        """
        if start_mmdd <= end_mmdd:
            # Normal range within same year
            return start_mmdd <= today_mmdd <= end_mmdd
        else:
            # Wraps around year boundary (e.g., Dec 31 - Jan 2)
            return today_mmdd >= start_mmdd or today_mmdd <= end_mmdd
