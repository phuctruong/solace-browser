#!/usr/bin/env python3
"""Translate tutorial + oauth3_confirm + notifications sections to all 12 locales."""
from __future__ import annotations
import json, os, re, sys
from pathlib import Path
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "app" / "locales" / "yinyang" / "en.json"
LOCALES_DIR = REPO_ROOT / "app" / "locales" / "yinyang"

_env_file = REPO_ROOT / ".env"
if _env_file.exists() and not os.environ.get("OPENROUTER_API_KEY"):
    for line in _env_file.read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            os.environ["OPENROUTER_API_KEY"] = line.split("=", 1)[1].strip().strip('"')

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])

LANGUAGES = {
    "es": "Spanish", "vi": "Vietnamese", "zh": "Simplified Chinese",
    "pt": "Portuguese", "fr": "French", "ja": "Japanese", "de": "German",
    "ar": "Arabic", "hi": "Hindi", "ko": "Korean", "id": "Indonesian", "ru": "Russian",
}
PRESERVE = ["Solace", "Solace Browser", "Yinyang", "OAuth3", "MCP", "Claude", "Cursor", "Codex",
            "Gmail", "Slack", "LinkedIn", "GitHub", "npx solace-browser --mcp",
            "solaceagi.com/agents", "localhost:9222", "localhost:8791"]


def extract_json(raw: str) -> dict:
    """Robustly extract a JSON object from raw model output."""
    # Strip code fences
    fenced = re.match(r"```(?:json)?\s*(.*?)\s*```", raw, re.S)
    if fenced:
        raw = fenced.group(1)
    raw = raw.strip()
    # Try direct parse
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw)
        return obj
    except (json.JSONDecodeError, ValueError):
        pass
    # Try to find first { ... } block
    match = re.search(r"\{.*\}", raw, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    raise ValueError(f"Could not parse JSON from model output: {raw[:300]}")


def translate_batch(texts: list[str], lang: str) -> list[str]:
    preserve = ", ".join(f'"{p}"' for p in PRESERVE)
    numbered = {str(i): v for i, v in enumerate(texts)}
    prompt = (
        f"Translate the values in this JSON object into {lang}. "
        f"Keep these terms exactly as-is: {preserve}. "
        "Preserve HTML tags like <a href=...>, emoji, and {placeholder} variables exactly. "
        "Return ONLY a valid JSON object with the same integer keys and translated values. No commentary.\n\n"
        + json.dumps(numbered, ensure_ascii=False)
    )
    resp = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.choices[0].message.content.strip()
    parsed = extract_json(raw)
    return [parsed.get(str(i), texts[i]) for i in range(len(texts))]


def main():
    en = json.loads(SOURCE.read_text(encoding="utf-8"))
    tutorial_en = en["delight"]["tutorial"]
    oauth3_en = en["delight"]["oauth3_confirm"]
    notif_en = en["delight"]["notifications"]

    locales = [l for l in LANGUAGES if (LOCALES_DIR / f"{l}.json").exists()]

    for locale in locales:
        lang = LANGUAGES[locale]
        path = LOCALES_DIR / f"{locale}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        delight = data.setdefault("delight", {})
        changed = False

        # Tutorial
        if "tutorial" not in delight:
            print(f"[{locale}] Translating tutorial ({len(tutorial_en)} keys)...", end=" ", flush=True)
            keys = list(tutorial_en.keys())
            values = list(tutorial_en.values())
            try:
                translated = translate_batch(values, lang)
                delight["tutorial"] = dict(zip(keys, translated))
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("ok")
                changed = True
            except (ValueError, OSError, KeyError) as e:
                print(f"FAILED: {e}")
        else:
            print(f"[{locale}] tutorial already done, skipping")

        # OAuth3 confirm
        if "oauth3_confirm" not in delight:
            print(f"[{locale}] Translating oauth3_confirm ({len(oauth3_en)} keys)...", end=" ", flush=True)
            flat_keys, flat_vals = [], []
            for k, v in oauth3_en.items():
                if isinstance(v, str):
                    flat_keys.append(k); flat_vals.append(v)
                elif isinstance(v, list):
                    for i, s in enumerate(v):
                        flat_keys.append(f"{k}[{i}]"); flat_vals.append(s)
            try:
                trans_flat = translate_batch(flat_vals, lang)
                oauth3_translated: dict = {}
                for k, v in zip(flat_keys, trans_flat):
                    m = re.match(r"^(.+)\[(\d+)\]$", k)
                    if m:
                        base, idx = m.group(1), int(m.group(2))
                        oauth3_translated.setdefault(base, [])
                        while len(oauth3_translated[base]) <= idx:
                            oauth3_translated[base].append("")
                        oauth3_translated[base][idx] = v
                    else:
                        oauth3_translated[k] = v
                delight["oauth3_confirm"] = oauth3_translated
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("ok")
                changed = True
            except (ValueError, OSError, KeyError) as e:
                print(f"FAILED: {e}")
        else:
            print(f"[{locale}] oauth3_confirm already done, skipping")

        # Notifications
        if "notifications" not in delight:
            print(f"[{locale}] Translating notifications ({len(notif_en)} keys)...", end=" ", flush=True)
            nkeys = list(notif_en.keys())
            nvals = list(notif_en.values())
            try:
                ntrans = translate_batch(nvals, lang)
                delight["notifications"] = dict(zip(nkeys, ntrans))
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("ok")
                changed = True
            except (ValueError, OSError, KeyError) as e:
                print(f"FAILED: {e}")
        else:
            print(f"[{locale}] notifications already done, skipping")

        if changed:
            print(f"[{locale}] Written to {path.name}")

    print("\nDone!")


if __name__ == "__main__":
    main()
