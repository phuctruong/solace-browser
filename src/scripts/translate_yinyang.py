#!/usr/bin/env python3
"""Translate Yinyang locale strings via OpenRouter (Llama 3.3 70B).

Usage:
    python3 src/scripts/translate_yinyang.py es
    python3 src/scripts/translate_yinyang.py --all
    python3 src/scripts/translate_yinyang.py ar --resume
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "app" / "locales" / "yinyang" / "en.json"
OUTPUT_DIR = REPO_ROOT / "app" / "locales" / "yinyang"

_env_file = REPO_ROOT / ".env"
if _env_file.exists() and not os.environ.get("OPENROUTER_API_KEY"):
    for line in _env_file.read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            os.environ["OPENROUTER_API_KEY"] = line.split("=", 1)[1].strip().strip('"')

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

LANGUAGE_NAMES = {
    "es": "Spanish",
    "vi": "Vietnamese",
    "zh": "Simplified Chinese",
    "pt": "Portuguese",
    "fr": "French",
    "ja": "Japanese",
    "de": "German",
    "ar": "Arabic",
    "hi": "Hindi",
    "ko": "Korean",
    "id": "Indonesian",
    "ru": "Russian",
    "zh-hant": "Traditional Chinese",
    "tr": "Turkish",
    "pl": "Polish",
    "th": "Thai",
    "nl": "Dutch",
    "it": "Italian",
    "uk": "Ukrainian",
    "sv": "Swedish",
    "he": "Hebrew",
    "fa": "Farsi",
}

# Brand/tech terms never translated
PRESERVE = [
    "Solace", "Solace Browser", "Yinyang", "OAuth3", "Software 5.0",
    "Phuc Labs", "BYOK", "PZip", "Gmail", "Slack", "LinkedIn",
    "GitHub", "Notion", "Asana", "Jira",
]

BATCH_SIZE = 10


def _strip_code_fence(text: str) -> str:
    fenced = re.match(r"```(?:json)?\s*(.*)\s*```", text, re.S)
    return fenced.group(1) if fenced else text


def _call_llm(nodes: list[str], language_name: str) -> list[str]:
    preserve_note = ", ".join(f'"{p}"' for p in PRESERVE)
    n = len(nodes)
    numbered = {str(k): v for k, v in enumerate(nodes)}
    payload = json.dumps(numbered, ensure_ascii=False)
    prompt = (
        f"Translate the values in this JSON object into {language_name}. "
        f"Keep these brand/technical terms exactly as-is: {preserve_note}. "
        "Preserve punctuation, capitalisation style, emoji, and ${amount} placeholders. "
        "Keep all numeric string keys exactly as they are. "
        "Return ONLY a valid JSON object with the same keys and translated values. "
        "No commentary, no code fences.\n\n"
        f"{payload}"
    )
    response = _client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = _strip_code_fence(response.choices[0].message.content.strip())
    parsed, _ = json.JSONDecoder().raw_decode(raw.lstrip())
    if isinstance(parsed, list):
        return parsed
    return [parsed[str(k)] for k in range(n)]


def _translate_list(strings: list[str], language_name: str) -> list[str]:
    if not strings:
        return strings
    result: list[str] = []
    i = 0
    while i < len(strings):
        batch = strings[i: i + BATCH_SIZE]
        for attempt in range(3):
            try:
                translated = _call_llm(batch, language_name)
                if len(translated) == len(batch):
                    result.extend(translated)
                    i += len(batch)
                    break
                print(f"    [retry {attempt+1}] count mismatch: sent {len(batch)}, got {len(translated)}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"    [retry {attempt+1}] parse error: {e}")
        else:
            raise RuntimeError(f"Failed to translate batch at index {i} after 3 attempts")
    return result


def _flatten_section(section: dict | list, prefix: str) -> dict[str, str]:
    """Recursively flatten a nested section into {dotted.key: string} pairs."""
    out: dict[str, str] = {}
    if isinstance(section, dict):
        for k, v in section.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str):
                out[full_key] = v
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, str):
                        out[f"{full_key}[{i}]"] = item
            elif isinstance(v, dict):
                out.update(_flatten_section(v, full_key))
    return out


def _set_nested(d: dict, dotted_key: str, value: str) -> None:
    """Set a value in nested dict using a dotted key (supports list index notation)."""
    # Handle list indices like "key[0]"
    list_match = re.match(r"^(.+)\[(\d+)\]$", dotted_key)
    if list_match:
        dict_key, idx = list_match.group(1), int(list_match.group(2))
        parts = dict_key.split(".", 1)
        if len(parts) == 1:
            if dict_key not in d:
                d[dict_key] = []
            while len(d[dict_key]) <= idx:
                d[dict_key].append("")
            d[dict_key][idx] = value
        else:
            if parts[0] not in d:
                d[parts[0]] = {}
            _set_nested(d[parts[0]], f"{parts[1]}[{idx}]", value)
        return

    parts = dotted_key.split(".", 1)
    if len(parts) == 1:
        d[parts[0]] = value
    else:
        if parts[0] not in d:
            d[parts[0]] = {}
        _set_nested(d[parts[0]], parts[1], value)


def translate_locale(locale: str, resume: bool = False) -> None:
    language_name = LANGUAGE_NAMES[locale]
    output_path = OUTPUT_DIR / f"{locale}.json"

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    if resume and output_path.exists():
        output = json.loads(output_path.read_text(encoding="utf-8"))
        print(f"Resuming from existing {output_path.name}")
    else:
        output = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        output["_meta"]["locale"] = locale

    # Translate section by section
    sections_to_translate = [
        ("ui", source.get("ui", {})),
        ("personality", source.get("personality", {})),
        ("delight.milestones", source.get("delight", {}).get("milestones", {})),
        ("delight.celebrations", source.get("delight", {}).get("celebrations", {})),
        ("delight.smalltalk", source.get("delight", {}).get("smalltalk", {})),
        ("delight.holidays", source.get("delight", {}).get("holidays", {})),
    ]

    for section_key, section_data in sections_to_translate:
        flat = _flatten_section(section_data, section_key)
        if not flat:
            continue

        # Check if already translated (resume mode)
        if resume:
            # Get the same section from output and check if it differs from source
            output_flat = _flatten_section(
                _get_nested(output, section_key) or {}, section_key
            )
            source_flat = flat
            if output_flat and output_flat != source_flat:
                print(f"  [{section_key}]: already translated ({len(flat)} strings), skipping")
                continue

        keys = list(flat.keys())
        values = list(flat.values())
        print(f"  [{section_key}]: translating {len(values)} strings ...", end=" ", flush=True)

        translated_values = _translate_list(values, language_name)

        # Write back into output structure
        for k, v in zip(keys, translated_values):
            _set_nested(output, k, v)

        output_path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("done")

    print(f"\nWrote {output_path.relative_to(REPO_ROOT)} ({output_path.stat().st_size // 1024}KB)")


def _get_nested(d: dict, dotted_key: str):
    parts = dotted_key.split(".", 1)
    val = d.get(parts[0])
    if len(parts) == 1:
        return val
    if isinstance(val, dict):
        return _get_nested(val, parts[1])
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("locale", nargs="?", choices=sorted(LANGUAGE_NAMES))
    group.add_argument("--all", action="store_true", help="Translate all locales")
    parser.add_argument("--resume", action="store_true", help="Skip already-translated sections")
    args = parser.parse_args()

    locales = list(LANGUAGE_NAMES.keys()) if args.all else [args.locale]
    for locale in locales:
        print(f"\n=== {locale} ({LANGUAGE_NAMES[locale]}) ===")
        translate_locale(locale, resume=args.resume)


if __name__ == "__main__":
    main()
