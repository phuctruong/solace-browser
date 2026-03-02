#!/usr/bin/env python3
"""Translate new ui nav/page strings for all 12 non-English locales."""
import json, os, sys
from pathlib import Path
from openai import OpenAI

REPO = Path(__file__).parent.parent.parent
LOCALES_DIR = REPO / "app" / "locales" / "yinyang"
DOTENV = REPO / ".env"

def load_env():
    if DOTENV.exists():
        for line in DOTENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])

LANGUAGES = {
    "es": "Spanish", "vi": "Vietnamese", "zh": "Simplified Chinese",
    "pt": "Portuguese", "fr": "French", "ja": "Japanese", "de": "German",
    "ar": "Arabic", "hi": "Hindi", "ko": "Korean", "id": "Indonesian", "ru": "Russian",
}

# Nav strings that should NOT be translated (proper nouns, technical terms)
PRESERVE = ["OAuth3", "MCP", "Agents →", "IDLE"]

def translate_batch(texts: dict, lang: str) -> dict:
    """Translate a batch of UI strings. texts = {key: english_string}"""
    items = "\n".join(f'{k}|||{v}' for k, v in texts.items())
    preserve_note = f"Do NOT translate these terms: {', '.join(PRESERVE)}"
    prompt = f"""Translate these UI strings to {lang}. Keep translations short and natural for navigation/UI.
{preserve_note}
Return ONLY the translations in the same format KEY|||TRANSLATION, one per line.
Keep brand names (Solace, Yinyang) as-is.

{items}"""
    
    resp = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )
    result = {}
    for line in resp.choices[0].message.content.strip().splitlines():
        if "|||" in line:
            k, _, v = line.partition("|||")
            k = k.strip()
            v = v.strip()
            if k in texts:
                result[k] = v
    return result

# New UI nav strings to translate (from en.json ui section additions)
NEW_UI_KEYS = [
    "nav_home", "nav_apps", "nav_machine", "nav_tunnel", "nav_settings",
    "nav_full_product", "nav_docs_back", "nav_quick_start", "nav_mcp_guide",
    "nav_oauth3", "menu_surfaces", "menu_documentation", "menu_platform",
    "menu_home", "menu_app_store", "menu_machine", "menu_tunnel", "menu_settings",
    "menu_docs_hub", "menu_quick_start", "menu_mcp_agents_guide", "menu_oauth3_safety",
    "menu_full_product", "menu_download", "auth_signed_in", "auth_sign_in",
]

en = json.loads((LOCALES_DIR / "en.json").read_text())
en_ui = en["ui"]
texts_to_translate = {k: en_ui[k] for k in NEW_UI_KEYS if k in en_ui}

for locale, lang_name in LANGUAGES.items():
    path = LOCALES_DIR / f"{locale}.json"
    data = json.loads(path.read_text())
    ui = data.setdefault("ui", {})
    
    # Find keys that need translation (missing or same as English)
    missing = {k: v for k, v in texts_to_translate.items() if k not in ui}
    if not missing:
        print(f"  [{locale}]: all nav strings already present, skipping")
        continue
    
    print(f"  [{locale}]: translating {len(missing)} nav strings ...", end=" ", flush=True)
    translated = translate_batch(missing, lang_name)
    ui.update(translated)
    data["ui"] = ui
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"done ({len(translated)} strings)")

print("Nav translation complete.")
