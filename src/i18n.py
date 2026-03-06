"""Yinyang i18n loader.

Single entry point for all locale string lookups. Falls back to English
for any missing key or unsupported locale.

Usage:
    from src.i18n import t, get_strings, set_locale

    t("ui.approve")                    # → "Approve"
    t("personality.friendly.greeting") # → "Hey there!"
    t("delight.smalltalk.s001")        # → "What are we building today?"

    strings = get_strings("es")        # → full dict for Spanish
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("solace-browser.i18n")

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "app" / "locales" / "yinyang"
_SUPPORTED = {
    "en", "es", "vi", "zh", "pt", "fr", "ja", "de", "ar", "hi", "ko", "id", "ru",
    "zh-hant", "tr", "pl", "th", "nl", "it", "uk", "sv", "he", "fa",
}

# Locales that use right-to-left text direction
_RTL_LOCALES: set[str] = {"ar", "he", "fa"}

# Active locale for process-wide default (can be overridden per-request)
_active_locale: str = "en"


@lru_cache(maxsize=16)
def _load(locale: str) -> dict:
    """Load and cache a locale file. Returns English as fallback."""
    path = _LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        if locale != "en":
            logger.warning("Locale '%s' not found, falling back to 'en'", locale)
        return _load("en")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Strip _meta key
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        logger.error("Failed to load locale '%s': %s — using 'en'", locale, exc)
        return _load("en")


def _load_en() -> dict:
    return _load("en")


def set_locale(locale: str) -> None:
    """Set the process-wide default locale."""
    global _active_locale
    _active_locale = locale if locale in _SUPPORTED else "en"


def get_locale() -> str:
    """Return the current process-wide default locale."""
    return _active_locale


def get_strings(locale: str | None = None) -> dict:
    """Return the full locale dict (English fallback for unknown locales)."""
    loc = locale or _active_locale
    loc = loc if loc in _SUPPORTED else "en"
    strings = _load(loc)
    # Ensure English fills any missing top-level sections
    if loc != "en":
        en = _load("en")
        for section in en:
            if section not in strings:
                strings = dict(strings)
                strings[section] = en[section]
    return strings


def t(key: str, locale: str | None = None, **kwargs) -> str:
    """Translate a dotted key path. Falls back to English, then to the key itself.

    Args:
        key:    Dotted path, e.g. "ui.approve", "personality.friendly.greeting"
        locale: Override locale. Uses process default if None.
        **kwargs: Format args, e.g. amount="$1.23" for c011 budget_saved.

    Returns:
        Translated (and formatted) string, or the key if not found.
    """
    loc = locale or _active_locale
    loc = loc if loc in _SUPPORTED else "en"

    value = _lookup(key, _load(loc))
    if value is None and loc != "en":
        value = _lookup(key, _load("en"))
    if value is None:
        logger.debug("Missing i18n key: '%s' (locale: %s)", key, loc)
        return key

    if kwargs:
        try:
            value = value.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return value


def _lookup(key: str, data: dict) -> str | None:
    """Walk a dotted key path through a nested dict. Returns None if missing."""
    parts = key.split(".", 1)
    val = data.get(parts[0])
    if val is None:
        return None
    if len(parts) == 1:
        return val if isinstance(val, str) else None
    if isinstance(val, dict):
        return _lookup(parts[1], val)
    return None


def ui(key: str, locale: str | None = None) -> str:
    """Shorthand for t('ui.<key>')."""
    return t(f"ui.{key}", locale=locale)


def personality_tone(personality: str, key: str, locale: str | None = None) -> str:
    """Shorthand for t('personality.<personality>.<key>')."""
    return t(f"personality.{personality}.{key}", locale=locale)


def smalltalk(sid: str, locale: str | None = None) -> str:
    """Shorthand for t('delight.smalltalk.<sid>')."""
    return t(f"delight.smalltalk.{sid}", locale=locale)


def celebration(cid: str, locale: str | None = None, **kwargs) -> str:
    """Shorthand for t('delight.celebrations.<cid>')."""
    return t(f"delight.celebrations.{cid}", locale=locale, **kwargs)


def milestone(key: str, locale: str | None = None) -> str:
    """Shorthand for t('delight.milestones.<key>')."""
    return t(f"delight.milestones.{key}", locale=locale)


def holiday_name(hid: str, locale: str | None = None) -> str:
    """Return translated holiday name, e.g. holiday_name('h001')."""
    return t(f"delight.holidays.{hid}_name", locale=locale)


def holiday_greetings(hid: str, locale: str | None = None) -> list[str]:
    """Return list of translated holiday greeting strings."""
    loc = locale or _active_locale
    loc = loc if loc in _SUPPORTED else "en"
    data = _load(loc)
    val = _lookup(f"delight.holidays.{hid}_greetings", data)
    if isinstance(val, list):
        return val
    # Try raw lookup (list values may not be returned by _lookup)
    try:
        return data["delight"]["holidays"][f"{hid}_greetings"]
    except (KeyError, TypeError):
        pass
    # Fallback to English
    en = _load("en")
    try:
        return en["delight"]["holidays"][f"{hid}_greetings"]
    except (KeyError, TypeError):
        return []


def js_bundle(locale: str | None = None) -> str:
    """Return a JS snippet that sets window.YINYANG_I18N for the bottom rail.

    Inject this via page.add_init_script() before the bottom rail script.
    """
    loc = locale or _active_locale
    loc = loc if loc in _SUPPORTED else "en"
    strings = get_strings(loc)
    ui_strings = strings.get("ui", {})
    payload = json.dumps(ui_strings, ensure_ascii=False)
    direction = get_direction(loc)
    return f"window.YINYANG_I18N = {payload};\nwindow.YINYANG_DIR = \"{direction}\";"


def is_rtl(locale: str | None = None) -> bool:
    """Return True if the given locale uses right-to-left text direction."""
    loc = locale or _active_locale
    loc = loc if loc in _SUPPORTED else "en"
    return loc in _RTL_LOCALES


def get_direction(locale: str | None = None) -> str:
    """Return 'rtl' or 'ltr' for the given locale."""
    return "rtl" if is_rtl(locale) else "ltr"


def detect_locale(accept_language: str | None) -> str:
    """Best-effort locale detection from Accept-Language header.

    Returns a supported locale code or 'en'.
    """
    if not accept_language:
        return "en"

    # Map common language tags to supported locales
    _MAP = {
        "es": "es", "vi": "vi", "zh": "zh", "zh-hans": "zh", "zh-cn": "zh",
        "pt": "pt", "pt-br": "pt", "pt-pt": "pt", "fr": "fr", "ja": "ja", "de": "de",
        "ar": "ar", "hi": "hi", "ko": "ko", "id": "id", "ru": "ru",
        "zh-hant": "zh-hant", "zh-tw": "zh-hant", "zh-hk": "zh-hant",
        "ms": "id",
        "tr": "tr", "pl": "pl", "th": "th", "nl": "nl", "it": "it",
        "uk": "uk", "sv": "sv", "he": "he", "fa": "fa",
        "en": "en",
    }

    for tag in accept_language.replace(" ", "").split(","):
        lang = tag.split(";")[0].split("-")[0].lower()
        full = tag.split(";")[0].lower()
        if full in _MAP:
            return _MAP[full]
        if lang in _MAP:
            return _MAP[lang]
    return "en"
