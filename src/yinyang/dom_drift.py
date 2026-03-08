"""DOM drift fingerprint — detect structural changes between page visits.

Generates a lightweight hash of a page's DOM structure (tag hierarchy + key
attributes) so the sidebar can detect when a site has changed enough to
invalidate cached recipes or app detection rules.

Usage:
    fingerprint = dom_fingerprint(html_string)
    if fingerprint != cached_fingerprint:
        # Site structure changed — recipes may need updating

Rung: 641 (local correctness)
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional


# Tags that contribute to structural fingerprint (skip inline/text nodes)
_STRUCTURAL_TAGS = frozenset({
    "html", "head", "body", "header", "footer", "nav", "main", "aside",
    "section", "article", "div", "form", "input", "select", "textarea",
    "button", "table", "thead", "tbody", "tr", "th", "td", "ul", "ol",
    "li", "a", "img", "iframe", "script", "link", "meta",
})

# Attributes that matter for structural identity
_STRUCTURAL_ATTRS = frozenset({
    "id", "name", "type", "role", "aria-label", "data-testid",
    "action", "method", "href",
})

# Regex to extract opening tags with attributes
_TAG_RE = re.compile(
    r"<(\w+)([^>]*)>",
    re.IGNORECASE,
)

# Regex to extract individual attributes
_ATTR_RE = re.compile(
    r"""(\w[\w\-]*)=["']([^"']*)["']""",
    re.IGNORECASE,
)


def dom_fingerprint(html: str, algorithm: str = "sha256") -> str:
    """Generate a structural fingerprint of HTML content.

    Args:
        html: Raw HTML string.
        algorithm: Hash algorithm (default sha256).

    Returns:
        Hex digest string representing the DOM structure.
    """
    if not html:
        return hashlib.new(algorithm, b"").hexdigest()

    parts: list[str] = []

    for match in _TAG_RE.finditer(html):
        tag = match.group(1).lower()
        if tag not in _STRUCTURAL_TAGS:
            continue

        attrs_str = match.group(2)
        # Extract structural attributes only
        attrs = {}
        for attr_match in _ATTR_RE.finditer(attrs_str):
            attr_name = attr_match.group(1).lower()
            if attr_name in _STRUCTURAL_ATTRS:
                attrs[attr_name] = attr_match.group(2)

        # Build canonical tag representation
        attr_part = ",".join(f"{k}={v}" for k, v in sorted(attrs.items()))
        parts.append(f"{tag}({attr_part})" if attr_part else tag)

    canonical = "|".join(parts)
    return hashlib.new(algorithm, canonical.encode("utf-8")).hexdigest()


def dom_drift_score(fingerprint_a: str, fingerprint_b: str) -> float:
    """Compare two fingerprints and return a drift score.

    Args:
        fingerprint_a: First fingerprint (hex digest).
        fingerprint_b: Second fingerprint (hex digest).

    Returns:
        0.0 if identical, 1.0 if completely different.
        For SHA-256 hashes, any difference means completely different structure.
    """
    if fingerprint_a == fingerprint_b:
        return 0.0
    return 1.0


def dom_structural_summary(html: str) -> dict:
    """Generate a summary of DOM structure for drift analysis.

    Returns:
        Dict with tag counts, form count, link count, etc.
    """
    tag_counts: dict[str, int] = {}
    for match in _TAG_RE.finditer(html):
        tag = match.group(1).lower()
        if tag in _STRUCTURAL_TAGS:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return {
        "tag_count": sum(tag_counts.values()),
        "unique_tags": len(tag_counts),
        "forms": tag_counts.get("form", 0),
        "inputs": tag_counts.get("input", 0),
        "links": tag_counts.get("a", 0),
        "images": tag_counts.get("img", 0),
        "tables": tag_counts.get("table", 0),
        "sections": tag_counts.get("section", 0),
        "tag_distribution": tag_counts,
    }
