#!/usr/bin/env python3
"""
Solace Browser RefMap Builder (Phase 3)

Extracts reference maps from Phase 2 recorded episodes. Each RefMap entry
provides multiple strategies for re-identifying DOM elements during replay,
ordered by reliability.

Architecture:
  - RefMapBuilder: stateless extraction from episode JSON
  - SemanticSelector: aria-label, data-testid, role, text, etc.
  - StructuralSelector: CSS selector, XPath, ref_path, nth-child
  - Reliability scoring: data-testid(0.98) > aria-label(0.95) > CSS(0.92) > XPath(0.85)
  - ref_id: deterministic SHA-256 hash from semantic identifiers

Integration:
  - Input: episode JSON from Phase 2 (BrowserSession.to_episode())
  - Output: RefMap JSON for Phase 4 (automated replay)
  - Dependency: snapshot_canonicalization.py for snapshot hashing

Auth: 65537 | Northstar: Phuc Forecast
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

# RefMap schema version
REFMAP_VERSION = "0.1.0"

# Reliability scores by selector type (higher = more stable across DOM changes)
RELIABILITY_SCORES = {
    "data_testid": 0.98,
    "aria_label": 0.95,
    "aria_describedby": 0.93,
    "id": 0.92,
    "name": 0.90,
    "role_text": 0.88,
    "placeholder": 0.85,
    "css_selector": 0.80,
    "xpath": 0.75,
    "ref_path": 0.70,
    "text": 0.65,
}

# Priority order for resolution (try highest reliability first)
DEFAULT_PRIORITY = [
    "data_testid",
    "id",
    "aria_label",
    "aria_describedby",
    "name",
    "role_text",
    "placeholder",
    "css_selector",
    "xpath",
    "ref_path",
    "text",
]

# Semantic attribute keys to extract from action data
SEMANTIC_KEYS = [
    "aria-label", "ariaLabel", "aria_label",
    "aria-describedby", "ariaDescribedby", "aria_describedby",
    "data-testid", "dataTestid", "data_testid", "testId",
    "data-qa", "dataQa", "data_qa",
    "placeholder",
    "alt",
    "role",
    "name",
    "type",
]


def _normalize_key(key: str) -> str:
    """Normalize attribute key to snake_case form."""
    mapping = {
        "aria-label": "aria_label",
        "ariaLabel": "aria_label",
        "aria-describedby": "aria_describedby",
        "ariaDescribedby": "aria_describedby",
        "data-testid": "data_testid",
        "dataTestid": "data_testid",
        "testId": "data_testid",
        "data-qa": "data_qa",
        "dataQa": "data_qa",
    }
    return mapping.get(key, key)


def generate_ref_id(semantic: Dict[str, Any]) -> str:
    """
    Generate deterministic ref_id from semantic identifiers.

    Uses SHA-256 hash of concatenated semantic values. Same semantic
    identifiers always produce the same ref_id.

    Args:
        semantic: dict of semantic attributes (aria_label, data_testid, etc.)

    Returns:
        ref_id string in format "ref_XXXXXXXX" (8 hex chars)
    """
    parts = []
    # Use stable ordering of keys for determinism
    for key in sorted(semantic.keys()):
        value = semantic.get(key)
        if value is not None and value != "":
            parts.append(f"{key}={value}")

    if not parts:
        parts.append("generic")

    seed = "|".join(parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"ref_{digest[:8]}"


def extract_semantic(action_data: dict) -> Dict[str, Optional[str]]:
    """
    Extract semantic selector attributes from action data.

    Looks for aria-label, data-testid, role, text, name, type,
    placeholder, and alt attributes in the action's target data.

    Args:
        action_data: the 'data' dict from an episode action

    Returns:
        dict of normalized semantic attributes (None for missing)
    """
    semantic = {}

    # Extract from top-level action data
    for raw_key in SEMANTIC_KEYS:
        value = action_data.get(raw_key)
        if value is not None and value != "":
            norm_key = _normalize_key(raw_key)
            # Don't overwrite with lower-priority variant
            if norm_key not in semantic:
                semantic[norm_key] = str(value)

    # Extract text content
    text = action_data.get("text") or action_data.get("value") or action_data.get("innerText")
    if text and "text" not in semantic:
        semantic["text"] = str(text)

    # Extract from nested 'target' or 'element' objects
    for nested_key in ("target", "element", "attributes"):
        nested = action_data.get(nested_key)
        if isinstance(nested, dict):
            for raw_key in SEMANTIC_KEYS:
                value = nested.get(raw_key)
                if value is not None and value != "":
                    norm_key = _normalize_key(raw_key)
                    if norm_key not in semantic:
                        semantic[norm_key] = str(value)
            # Also check text in nested
            nested_text = nested.get("text") or nested.get("innerText")
            if nested_text and "text" not in semantic:
                semantic["text"] = str(nested_text)

    return semantic


def extract_structural(action_data: dict) -> Dict[str, Optional[str]]:
    """
    Extract structural selector attributes from action data.

    Looks for CSS selector, XPath, ref_path, tag, id, and nth-child
    information in the action's target data.

    Args:
        action_data: the 'data' dict from an episode action

    Returns:
        dict of structural selectors (None for missing)
    """
    structural = {}

    # CSS selector
    selector = action_data.get("selector") or action_data.get("target") or action_data.get("css_selector")
    if selector and isinstance(selector, str):
        structural["css_selector"] = selector

    # XPath
    xpath = action_data.get("xpath")
    if xpath:
        structural["xpath"] = str(xpath)

    # ref_path (tag:index notation)
    ref_path = action_data.get("ref_path") or action_data.get("refPath")
    if ref_path:
        structural["ref_path"] = str(ref_path)

    # Tag name
    tag = action_data.get("tag") or action_data.get("tagName")
    if tag:
        structural["tag"] = str(tag).lower()

    # Element ID (also structural)
    elem_id = action_data.get("id")
    if elem_id:
        structural["id"] = str(elem_id)

    # nth-child index
    nth = action_data.get("nth_child") or action_data.get("nthChild") or action_data.get("index")
    if nth is not None:
        structural["nth_child"] = int(nth)

    # Extract from nested objects
    for nested_key in ("target", "element", "attributes"):
        nested = action_data.get(nested_key)
        if isinstance(nested, dict):
            if "css_selector" not in structural:
                ns = nested.get("selector") or nested.get("css_selector")
                if ns:
                    structural["css_selector"] = str(ns)
            if "xpath" not in structural:
                nx = nested.get("xpath")
                if nx:
                    structural["xpath"] = str(nx)
            if "tag" not in structural:
                nt = nested.get("tag") or nested.get("tagName")
                if nt:
                    structural["tag"] = str(nt).lower()
            if "id" not in structural:
                ni = nested.get("id")
                if ni:
                    structural["id"] = str(ni)

    # Build CSS selector from id if we have one and no CSS selector yet
    if "id" in structural and "css_selector" not in structural:
        structural["css_selector"] = f"#{structural['id']}"

    return structural


def score_reliability(semantic: dict, structural: dict) -> Dict[str, float]:
    """
    Compute reliability scores for all available selectors.

    Each selector type gets a fixed reliability score based on how
    stable it is across DOM changes.

    Args:
        semantic: semantic attribute dict
        structural: structural selector dict

    Returns:
        dict mapping selector type to reliability score (0.0-1.0)
    """
    scores = {}

    # Score semantic selectors
    if semantic.get("data_testid"):
        scores["data_testid"] = RELIABILITY_SCORES["data_testid"]
    if semantic.get("aria_label"):
        scores["aria_label"] = RELIABILITY_SCORES["aria_label"]
    if semantic.get("aria_describedby"):
        scores["aria_describedby"] = RELIABILITY_SCORES["aria_describedby"]
    if semantic.get("name"):
        scores["name"] = RELIABILITY_SCORES["name"]
    if semantic.get("placeholder"):
        scores["placeholder"] = RELIABILITY_SCORES["placeholder"]
    if semantic.get("role") and semantic.get("text"):
        scores["role_text"] = RELIABILITY_SCORES["role_text"]
    if semantic.get("text"):
        scores["text"] = RELIABILITY_SCORES["text"]

    # Score structural selectors
    if structural.get("id"):
        scores["id"] = RELIABILITY_SCORES["id"]
    if structural.get("css_selector"):
        # Adjust CSS score based on selector quality
        css = structural["css_selector"]
        if css.startswith("#"):
            scores["css_selector"] = 0.92  # ID-based CSS
        elif "[data-testid" in css:
            scores["css_selector"] = 0.90  # testid-based CSS
        else:
            scores["css_selector"] = RELIABILITY_SCORES["css_selector"]
    if structural.get("xpath"):
        scores["xpath"] = RELIABILITY_SCORES["xpath"]
    if structural.get("ref_path"):
        scores["ref_path"] = RELIABILITY_SCORES["ref_path"]

    return scores


def compute_priority(reliability: Dict[str, float]) -> List[str]:
    """
    Compute selector priority order from reliability scores.

    Sorts available selectors by reliability (highest first).

    Args:
        reliability: dict of selector type -> score

    Returns:
        list of selector types ordered by reliability (descending)
    """
    return sorted(reliability.keys(), key=lambda k: reliability[k], reverse=True)


def best_resolution_strategy(reliability: Dict[str, float]) -> str:
    """
    Determine the best resolution strategy from reliability scores.

    Args:
        reliability: dict of selector type -> score

    Returns:
        string describing the best strategy, e.g. "data_testid (0.98)"
    """
    if not reliability:
        return "none"
    best_key = max(reliability, key=reliability.get)
    return f"{best_key} ({reliability[best_key]:.2f})"


class RefMapBuilder:
    """
    Builds RefMap JSON from Phase 2 recorded episodes.

    Stateless builder: each build_refmap() call is independent.
    Given identical input, output is always identical (deterministic).

    Pipeline:
      1. Iterate episode actions
      2. Extract semantic selectors per action
      3. Extract structural selectors per action
      4. Generate deterministic ref_id from semantics
      5. Score reliability for each selector
      6. Assemble RefMap JSON with stats
    """

    def build_refmap(self, episode: dict) -> Dict[str, Any]:
        """
        Build a complete RefMap from an episode.

        Args:
            episode: episode dict with 'actions' key (Phase 2 format)

        Returns:
            RefMap JSON dict matching the Phase 3 schema

        Raises:
            ValueError: if episode is not a dict or has no actions
        """
        if not isinstance(episode, dict):
            raise ValueError("Episode must be a dict")

        actions = episode.get("actions") or []
        if not actions:
            raise ValueError("Episode has no actions")

        episode_id = episode.get("session_id") or ""
        domain = episode.get("domain") or "unknown"
        url = self._extract_source_url(episode)

        refmap_entries = {}
        semantic_only_count = 0
        structural_only_count = 0
        complete_count = 0

        for idx, action in enumerate(actions):
            action_data = action.get("data") or {}
            action_type = (action.get("type") or "unknown").upper()
            action_timestamp = action.get("timestamp") or ""

            # Extract selectors
            semantic = extract_semantic(action_data)
            structural = extract_structural(action_data)

            # Skip actions with no selectors at all (e.g. pure navigation by URL only)
            if not semantic and not structural:
                # For navigate actions, URL is structural enough
                url_val = action_data.get("url")
                if url_val:
                    structural["css_selector"] = f"url:{url_val}"
                else:
                    continue

            # Generate ref_id
            ref_id = generate_ref_id(semantic) if semantic else generate_ref_id({"structural": json.dumps(structural, sort_keys=True)})

            # Handle duplicate ref_ids (same element targeted multiple times)
            if ref_id in refmap_entries:
                # Append action to existing ref
                refmap_entries[ref_id]["actions"].append({
                    "action_index": idx,
                    "action_type": action_type,
                    "action_timestamp": action_timestamp,
                })
                continue

            # Score reliability
            reliability = score_reliability(semantic, structural)
            priority = compute_priority(reliability)
            strategy = best_resolution_strategy(reliability)

            # Categorize
            has_semantic = bool(semantic)
            has_structural = bool(structural)
            if has_semantic and has_structural:
                complete_count += 1
            elif has_semantic:
                semantic_only_count += 1
            elif has_structural:
                structural_only_count += 1

            # Build entry
            entry = {
                "semantic": semantic if semantic else {},
                "structural": structural if structural else {},
                "priority": priority,
                "reliability": reliability,
                "actions": [
                    {
                        "action_index": idx,
                        "action_type": action_type,
                        "action_timestamp": action_timestamp,
                    }
                ],
                "resolution_strategy": strategy,
            }

            refmap_entries[ref_id] = entry

        # Assemble final RefMap
        total_refs = len(refmap_entries)
        action_count = len(actions)
        pages = self._count_pages(actions)

        return {
            "version": REFMAP_VERSION,
            "episode_id": episode_id,
            "url_source": url,
            "refmap": refmap_entries,
            "stats": {
                "total_refs": total_refs,
                "action_count": action_count,
                "pages": pages,
                "semantic_only_count": semantic_only_count,
                "structural_only_count": structural_only_count,
                "complete_count": complete_count,
            },
        }

    def _extract_source_url(self, episode: dict) -> str:
        """Extract the source URL from episode (first navigate action or domain)."""
        actions = episode.get("actions") or []
        for action in actions:
            if (action.get("type") or "").lower() in ("navigate", "NAVIGATE"):
                url = (action.get("data") or {}).get("url")
                if url:
                    return url
        domain = episode.get("domain") or "unknown"
        return f"https://{domain}"

    def _count_pages(self, actions: list) -> int:
        """Count the number of distinct pages (NAVIGATE actions)."""
        urls = set()
        for action in actions:
            if (action.get("type") or "").lower() in ("navigate", "NAVIGATE"):
                url = (action.get("data") or {}).get("url")
                if url:
                    urls.add(url)
        return max(len(urls), 1)


def build_refmap_from_episode(episode: dict) -> Dict[str, Any]:
    """Convenience function: build RefMap from episode dict."""
    builder = RefMapBuilder()
    return builder.build_refmap(episode)


def build_refmap_from_file(filepath: str) -> Dict[str, Any]:
    """Convenience function: load episode from file and build RefMap."""
    with open(filepath, "r") as f:
        episode = json.load(f)
    return build_refmap_from_episode(episode)


def save_refmap(refmap: dict, filepath: str) -> None:
    """Save RefMap to JSON file."""
    with open(filepath, "w") as f:
        json.dump(refmap, f, indent=2, sort_keys=False)
