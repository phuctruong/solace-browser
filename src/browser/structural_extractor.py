"""
structural_extractor.py — CPU-only page structure extraction.

No LLM required. Regex-based. Runs on every page load.
Extracts: title, meta, canonical, headings, nav links, CTAs, page_type.
Output: lightweight JSON (~500 bytes per page).

Ported from: solace-cli/scratch/prime_wiki_extractor.py strip_to_structure()
Rung: 641
"""

from __future__ import annotations

import re
from typing import Any


def strip_to_structure(html: str) -> dict[str, Any]:
    """Extract structural elements from HTML using regex (no LLM).

    Returns dict with: title, meta_description, canonical, headings,
    nav_links, ctas, page_type.
    """
    result: dict[str, Any] = {}

    # Title
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    result["title"] = m.group(1).strip() if m else ""

    # Meta description
    m = re.search(
        r'name=["\']description["\'][^>]+content=["\']([^"\']{10,})["\']',
        html,
        re.I,
    )
    result["meta_description"] = m.group(1).strip()[:200] if m else ""

    # Canonical
    m = re.search(
        r'href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']'
        r'|rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    result["canonical"] = (m.group(1) or m.group(2)).strip() if m else ""

    # Headings (h1-h3, max 10)
    headings: list[str] = []
    for tag in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.I | re.S)[:10]:
        clean = re.sub(r"<[^>]+>", "", tag).strip()
        if clean:
            headings.append(clean[:100])
    result["headings"] = headings

    # Nav links (max 8)
    nav_links: list[dict[str, str]] = []
    for href, text in re.findall(
        r'href=["\']([^"\']{2,})["\'][^>]*>([^<]{2,40})</', html
    )[:8]:
        t = text.strip()
        if t and not t.startswith("{"):
            nav_links.append({"text": t, "href": href[:80]})
    result["nav_links"] = nav_links

    # CTAs (buttons with btn class, max 5)
    ctas: list[str] = []
    for btn in re.findall(
        r'class=["\'][^"\']*btn[^"\']*["\'][^>]*>([^<]{3,40})</', html, re.I
    )[:5]:
        b = btn.strip()
        if b:
            ctas.append(b)
    result["ctas"] = ctas

    # Page type classification
    result["page_type"] = _classify_page_type(html, result)

    return result


def _classify_page_type(html: str, structure: dict[str, Any]) -> str:
    """Classify page type from structural signals."""
    html_lower = html.lower()
    if re.search(r"<form[^>]*login|sign.?in|log.?in", html_lower):
        return "auth"
    if re.search(r"price|pricing|plan|tier|subscription", html_lower) and len(
        structure.get("ctas", [])
    ) >= 2:
        return "landing"
    if re.search(r"<article|<time|published|author", html_lower):
        return "blog"
    if re.search(r"<code|api|endpoint|parameter|returns", html_lower):
        return "docs"
    return "other"


def structure_to_text(structure: dict[str, Any]) -> str:
    """Serialize structure to text format for Prime Wiki."""
    lines: list[str] = []
    if structure.get("title"):
        lines.append(f"TITLE: {structure['title']}")
    if structure.get("meta_description"):
        lines.append(f"META: {structure['meta_description']}")
    if structure.get("canonical"):
        lines.append(f"CANONICAL: {structure['canonical']}")
    for h in structure.get("headings", []):
        lines.append(f"H: {h}")
    for link in structure.get("nav_links", []):
        lines.append(f"LINK: {link['text']} -> {link['href']}")
    for cta in structure.get("ctas", []):
        lines.append(f"CTA: {cta}")
    lines.append(f"TYPE: {structure.get('page_type', 'other')}")
    return "\n".join(lines)
