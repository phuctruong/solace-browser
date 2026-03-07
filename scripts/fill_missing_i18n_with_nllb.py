#!/usr/bin/env python3
"""Fill English-equal locale strings with local NLLB translations.

This script only updates keys where a locale value is exactly equal to the
English source value at the same path. Existing translated strings are kept.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, NllbTokenizer
from transformers.utils import logging as hf_logging

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCALES_DIR = REPO_ROOT / "app" / "locales" / "yinyang"
MODEL_NAME = "facebook/nllb-200-distilled-600M"

# Locale files in this repo -> NLLB target language tokens.
LOCALE_TO_NLLB: dict[str, str] = {
    "am": "amh_Ethi",
    "ar": "arb_Arab",
    "bg": "bul_Cyrl",
    "bn": "ben_Beng",
    "ca": "cat_Latn",
    "cs": "ces_Latn",
    "da": "dan_Latn",
    "de": "deu_Latn",
    "el": "ell_Grek",
    "es": "spa_Latn",
    "et": "est_Latn",
    "fa": "pes_Arab",
    "fi": "fin_Latn",
    "fil": "tgl_Latn",
    "fr": "fra_Latn",
    "ha": "hau_Latn",
    "he": "heb_Hebr",
    "hi": "hin_Deva",
    "hr": "hrv_Latn",
    "hu": "hun_Latn",
    "id": "ind_Latn",
    "it": "ita_Latn",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "lt": "lit_Latn",
    "lv": "lvs_Latn",
    "ms": "zsm_Latn",
    "nl": "nld_Latn",
    "no": "nob_Latn",
    "pl": "pol_Latn",
    "pt": "por_Latn",
    "ro": "ron_Latn",
    "ru": "rus_Cyrl",
    "sk": "slk_Latn",
    "sl": "slv_Latn",
    "sr": "srp_Cyrl",
    "sv": "swe_Latn",
    "sw": "swh_Latn",
    "th": "tha_Thai",
    "tr": "tur_Latn",
    "uk": "ukr_Cyrl",
    "vi": "vie_Latn",
    "yo": "yor_Latn",
    "zh": "zho_Hans",
    "zh-hant": "zho_Hant",
    "zu": "zul_Latn",
}

PLACEHOLDER_RE = re.compile(r"\$\{[^{}]+\}|\{[^{}]+\}")
ENG_ALPHA_RE = re.compile(r"[A-Za-z]")
SENTINEL_RE = re.compile(r"@@SBPH(\d+)@@")

hf_logging.set_verbosity_error()


def _iter_english_equal_paths(
    en_node: Any, locale_node: Any, path: str = ""
) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    if isinstance(en_node, dict) and isinstance(locale_node, dict):
        for key, en_val in en_node.items():
            if key not in locale_node:
                continue
            next_path = f"{path}.{key}" if path else key
            matches.extend(_iter_english_equal_paths(en_val, locale_node[key], next_path))
        return matches
    if isinstance(en_node, list) and isinstance(locale_node, list):
        for idx, (en_val, loc_val) in enumerate(zip(en_node, locale_node)):
            next_path = f"{path}[{idx}]"
            matches.extend(_iter_english_equal_paths(en_val, loc_val, next_path))
        return matches
    if (
        isinstance(en_node, str)
        and isinstance(locale_node, str)
        and en_node == locale_node
        and en_node.strip()
        and not path.startswith("_meta.")
        and ENG_ALPHA_RE.search(en_node)
    ):
        matches.append((path, en_node))
    return matches


def _split_path(path: str) -> list[str | int]:
    parts: list[str | int] = []
    for name in path.split("."):
        if not name:
            continue
        cursor = 0
        while cursor < len(name):
            bracket = name.find("[", cursor)
            if bracket == -1:
                parts.append(name[cursor:])
                break
            if bracket > cursor:
                parts.append(name[cursor:bracket])
            end = name.find("]", bracket)
            if end == -1:
                raise ValueError(f"Invalid path segment: {name}")
            parts.append(int(name[bracket + 1 : end]))
            cursor = end + 1
    return parts


def _set_path(root: Any, path: str, value: str) -> None:
    parts = _split_path(path)
    node = root
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value


def _protect_placeholders(text: str) -> tuple[str, dict[str, str]]:
    placeholder_map: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        token = f"@@SBPH{len(placeholder_map)}@@"
        placeholder_map[token] = match.group(0)
        return token

    protected = PLACEHOLDER_RE.sub(_replace, text)
    return protected, placeholder_map


def _restore_placeholders(text: str, placeholder_map: dict[str, str]) -> str:
    restored = text
    for token, original in placeholder_map.items():
        restored = restored.replace(token, original)
    return restored


def _translate_batch(
    model: AutoModelForSeq2SeqLM,
    tokenizer: NllbTokenizer,
    texts: list[str],
    tgt_lang: str,
    device: torch.device,
    num_beams: int,
) -> list[str]:
    protected_texts: list[str] = []
    placeholder_maps: list[dict[str, str]] = []
    for text in texts:
        protected, pmap = _protect_placeholders(text)
        protected_texts.append(protected)
        placeholder_maps.append(pmap)

    tokenizer.src_lang = "eng_Latn"
    encoded = tokenizer(
        protected_texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=256,
    )
    encoded = {k: v.to(device) for k, v in encoded.items()}
    generated = model.generate(
        **encoded,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids(tgt_lang),
        max_new_tokens=160,
        num_beams=num_beams,
        use_cache=False,
        do_sample=False,
    )
    decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)

    restored: list[str] = []
    for out_text, pmap, source_text in zip(decoded, placeholder_maps, texts):
        current = _restore_placeholders(out_text, pmap)
        missing_tokens = [orig for orig in pmap.values() if orig not in current]
        if missing_tokens:
            # Fail-closed for variable-bearing strings.
            restored.append(source_text)
            continue
        if SENTINEL_RE.search(current):
            restored.append(source_text)
            continue
        restored.append(current)
    return restored


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--locales",
        nargs="*",
        default=[],
        help="Optional subset of locale codes (e.g., am bg ca). Defaults to all non-en locales.",
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda", "auto"],
        default="auto",
        help="Inference device. Use cpu for reliability if GPU memory is tight.",
    )
    parser.add_argument(
        "--num-beams",
        type=int,
        default=1,
        help="Beam size for generation. 1 is fastest/lowest memory.",
    )
    args = parser.parse_args()

    en_path = LOCALES_DIR / "en.json"
    en_data = json.loads(en_path.read_text(encoding="utf-8"))

    target_locales = sorted(LOCALE_TO_NLLB.keys())
    if args.locales:
        wanted = set(args.locales)
        target_locales = [loc for loc in target_locales if loc in wanted]

    if args.device == "cpu":
        device = torch.device("cpu")
    elif args.device == "cuda":
        device = torch.device("cuda")
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading model {MODEL_NAME} on {device}...")
    tokenizer = NllbTokenizer.from_pretrained(MODEL_NAME, src_lang="eng_Latn")
    model_kwargs: dict[str, Any] = {}
    if device.type == "cuda":
        model_kwargs["dtype"] = torch.float16
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, **model_kwargs).to(device)
    model.eval()

    for locale in target_locales:
        path = LOCALES_DIR / f"{locale}.json"
        if not path.exists():
            print(f"[{locale}] missing file, skip")
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        missing = _iter_english_equal_paths(en_data, data)
        if not missing:
            print(f"[{locale}] nothing to translate")
            continue

        print(f"[{locale}] translating {len(missing)} strings")
        translated_count = 0
        for start in range(0, len(missing), args.batch_size):
            batch = missing[start : start + args.batch_size]
            batch_paths = [path_text[0] for path_text in batch]
            batch_texts = [path_text[1] for path_text in batch]
            outputs = _translate_batch(
                model=model,
                tokenizer=tokenizer,
                texts=batch_texts,
                tgt_lang=LOCALE_TO_NLLB[locale],
                device=device,
                num_beams=args.num_beams,
            )
            for item_path, output_text in zip(batch_paths, outputs):
                _set_path(data, item_path, output_text)
                translated_count += 1

        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[{locale}] wrote {translated_count} strings")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
