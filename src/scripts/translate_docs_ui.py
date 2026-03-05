#!/usr/bin/env python3
"""Translate new docs UI strings for all 12 non-English locales.

Reads new keys from en.json ui section and translates only missing keys
per locale. Idempotent: skips keys that already exist in a locale file.
Batch size: 25 items max per API call.
"""
from __future__ import annotations
import json, os, re
from pathlib import Path
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCALES_DIR = REPO_ROOT / "app" / "locales" / "yinyang"
DOTENV = REPO_ROOT / ".env"

# ── load .env ─────────────────────────────────────────────────────────────────
if DOTENV.exists():
    for _line in DOTENV.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

LANGUAGES = {
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
}

# Terms that must stay exactly as-is (not translated)
PRESERVE = [
    "Solace", "Solace Browser", "OAuth3", "MCP", "Claude Code",
    "Cursor", "Codex", "Gmail", "GitHub", "YinYang", "Yinyang",
    "solaceagi.com", "LLM",
]

# New docs UI keys added to en.json — the keys we want to translate
DOCS_UI_KEYS = [
    "docs_hub_eyebrow",
    "docs_hub_h1",
    "docs_hub_lead",
    "docs_hub_card1_title",
    "docs_hub_card1_desc",
    "docs_hub_card2_title",
    "docs_hub_card2_desc",
    "docs_hub_card3_title",
    "docs_hub_card3_desc",
    "docs_hub_card4_title",
    "docs_hub_card4_desc",
    "docs_hub_card5_title",
    "docs_hub_card5_desc",
    "docs_hub_card6_title",
    "docs_hub_card6_desc",
    "docs_hub_papers_h2",
    "docs_hub_papers_copy",
    "docs_hub_paper04_title",
    "docs_hub_paper04_desc",
    "docs_hub_paper07_title",
    "docs_hub_paper07_desc",
    "docs_hub_paper09_title",
    "docs_hub_paper09_desc",
    "docs_qs_h1",
    "docs_toc_label",
    "docs_qs_install_h2",
    "docs_qs_option_a",
    "docs_qs_option_b",
    "docs_qs_option_c",
    "docs_qs_launch_h2",
    "docs_qs_first_run_h2",
    "docs_qs_approval_h2",
    "docs_qs_budget_h3",
    "docs_qs_tutorial_h2",
    "docs_qs_next_h2",
    "docs_mcp_h1",
    "docs_mcp_what_h2",
    "docs_mcp_setup_h2",
    "docs_mcp_claude_h2",
    "docs_mcp_cursor_h2",
    "docs_mcp_tools_h2",
    "docs_mcp_examples_h2",
    "docs_mcp_oauth3_h2",
    "docs_oauth3_h1",
    "docs_oauth3_what_h2",
    "docs_oauth3_approval_h2",
    "docs_oauth3_budgets_h2",
    "docs_oauth3_evidence_h2",
    "docs_oauth3_failclosed_h2",
    "docs_oauth3_revoke_h2",
    "docs_oauth3_faq_h2",
]

BATCH_SIZE = 25


def extract_json(raw: str) -> dict:
    """Robustly extract a JSON object from raw model output."""
    fenced = re.match(r"```(?:json)?\s*(.*?)\s*```", raw, re.S)
    if fenced:
        raw = fenced.group(1)
    raw = raw.strip()
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw)
        return obj
    except (json.JSONDecodeError, ValueError):
        pass
    match = re.search(r"\{.*\}", raw, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    raise ValueError(f"Could not parse JSON from model output:\n{raw[:400]}")


def translate_batch(items: dict[str, str], lang: str) -> dict[str, str]:
    """
    Translate a batch of {key: english_value} pairs to lang.
    Returns {key: translated_value}.
    Uses numeric indices internally to avoid key confusion.
    """
    keys = list(items.keys())
    values = list(items.values())
    numbered = {str(i): v for i, v in enumerate(values)}
    preserve_note = ", ".join(f'"{p}"' for p in PRESERVE)
    prompt = (
        f"Translate the values in this JSON object into {lang}. "
        f"Keep these terms exactly as-is (do not translate them): {preserve_note}. "
        "Preserve any special characters like →, ←, —, &, etc. "
        "Return ONLY a valid JSON object with the same integer string keys and translated values. "
        "No commentary, no code fences, no extra text.\n\n"
        + json.dumps(numbered, ensure_ascii=False)
    )
    resp = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct",
        max_tokens=4096,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.choices[0].message.content.strip()
    parsed = extract_json(raw)
    result = {}
    for i, key in enumerate(keys):
        translated_val = parsed.get(str(i))
        if translated_val and isinstance(translated_val, str):
            result[key] = translated_val
        else:
            # Fall back to English if model dropped the key
            result[key] = values[i]
    return result


def main() -> None:
    # Load English source
    en_data = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
    en_ui = en_data["ui"]

    # Filter to only the docs keys that actually exist in en.json
    en_docs = {k: en_ui[k] for k in DOCS_UI_KEYS if k in en_ui}
    print(f"Found {len(en_docs)} docs UI keys in en.json to translate.")

    for locale, lang_name in LANGUAGES.items():
        path = LOCALES_DIR / f"{locale}.json"
        if not path.exists():
            print(f"[{locale}] File not found, skipping.")
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        ui = data.setdefault("ui", {})

        # Find missing keys (keys in en_docs but not in locale's ui)
        missing = {k: v for k, v in en_docs.items() if k not in ui}
        if not missing:
            print(f"[{locale}] All docs UI keys already present, skipping.")
            continue

        print(f"[{locale}] Translating {len(missing)} missing keys to {lang_name}...")

        # Split into batches of BATCH_SIZE
        missing_items = list(missing.items())
        all_translated: dict[str, str] = {}

        for batch_start in range(0, len(missing_items), BATCH_SIZE):
            batch = dict(missing_items[batch_start: batch_start + BATCH_SIZE])
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(missing_items) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} items)...", end=" ", flush=True)
            try:
                translated = translate_batch(batch, lang_name)
                all_translated.update(translated)
                print("ok")
            except (ValueError, OSError, KeyError) as exc:
                print(f"FAILED: {exc}")
                # Use English fallback for this batch
                all_translated.update(batch)

        # Merge translations into locale ui section
        ui.update(all_translated)
        data["ui"] = ui

        # Save immediately after each locale
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  [{locale}] Saved {len(all_translated)} translations to {path.name}")

    print("\nDocs UI translation complete.")


if __name__ == "__main__":
    main()
