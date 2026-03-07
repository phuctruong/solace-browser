"""Harsh QA for i18n locale consistency across all 47 locales."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
LOCALES_DIR = REPO_ROOT / "app" / "locales" / "yinyang"
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")


def _flatten_strings(node: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            if key.startswith("_"):
                continue
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str):
                out[path] = value
            else:
                out.update(_flatten_strings(value, path))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            path = f"{prefix}[{i}]"
            if isinstance(value, str):
                out[path] = value
            else:
                out.update(_flatten_strings(value, path))
    return out


def _load_locale(locale_file: Path) -> dict[str, Any]:
    return json.loads(locale_file.read_text(encoding="utf-8"))


class TestTranslationParity:
    """Ensure locale files stay structurally aligned and interpolation-safe."""

    def test_all_47_locale_files_present(self) -> None:
        locale_files = sorted(LOCALES_DIR.glob("*.json"))
        assert len(locale_files) == 47, "Expected 47 locale files"

    def test_locale_key_paths_match_english_exactly(self) -> None:
        en = _flatten_strings(_load_locale(LOCALES_DIR / "en.json"))
        for locale_file in sorted(LOCALES_DIR.glob("*.json")):
            locale = locale_file.stem
            if locale == "en":
                continue
            localized = _flatten_strings(_load_locale(locale_file))
            missing = sorted(set(en) - set(localized))
            extra = sorted(set(localized) - set(en))
            assert not missing, f"{locale}: missing {len(missing)} keys"
            assert not extra, f"{locale}: extra {len(extra)} keys"

    def test_placeholder_sets_match_english(self) -> None:
        en = _flatten_strings(_load_locale(LOCALES_DIR / "en.json"))
        for locale_file in sorted(LOCALES_DIR.glob("*.json")):
            locale = locale_file.stem
            if locale == "en":
                continue
            localized = _flatten_strings(_load_locale(locale_file))
            for key, en_text in en.items():
                translated_text = localized[key]
                en_placeholders = set(PLACEHOLDER_RE.findall(en_text))
                tr_placeholders = set(PLACEHOLDER_RE.findall(translated_text))
                assert en_placeholders == tr_placeholders, (
                    f"{locale}: placeholder mismatch at {key} "
                    f"(en={sorted(en_placeholders)} tr={sorted(tr_placeholders)})"
                )
