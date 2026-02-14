#!/usr/bin/env python3
"""
Solace Browser Snapshot Canonicalization (B1)

Deterministic canonicalization of DOM snapshots for replay verification.
Produces content-addressed snapshots where identical DOM states always
yield identical hashes, regardless of capture timing or browser state.

Architecture:
  - SnapshotCanonicalizer: stateless transforms for snapshot normalization
  - Volatile removal: strips timestamps, session tokens, dynamic IDs
  - Key sorting: recursive deterministic key ordering
  - Unicode normalization: NFC normalization for cross-platform consistency
  - Landmark extraction: structural pattern detection (nav, form, list, table)

Integration:
  - Input: raw snapshots from Phase A BrowserSession.add_snapshot()
  - Output: {canonical_bytes, sha256, size_bytes} for Phase B recipe compilation
  - Consumed by: episode_to_recipe_compiler.py refmap + proof generation

Auth: 65537 | Northstar: Phuc Forecast
"""

import hashlib
import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


# Volatile patterns: keys and value patterns that change between captures
# of the same logical DOM state. These must be stripped for determinism.
VOLATILE_KEY_PATTERNS = [
    re.compile(r"^timestamp$", re.IGNORECASE),
    re.compile(r"^captured_at$", re.IGNORECASE),
    re.compile(r"^session_id$", re.IGNORECASE),
    re.compile(r"^request_id$", re.IGNORECASE),
    re.compile(r"^nonce$", re.IGNORECASE),
    re.compile(r"^csrf[_-]?token$", re.IGNORECASE),
    re.compile(r"^_t$"),
    re.compile(r"^_ts$"),
    re.compile(r"^cache[_-]?bust(er)?$", re.IGNORECASE),
    re.compile(r"^etag$", re.IGNORECASE),
    re.compile(r"^last[_-]?modified$", re.IGNORECASE),
    re.compile(r"^data-analytics", re.IGNORECASE),
    re.compile(r"^data-session", re.IGNORECASE),
    re.compile(r"^data-timestamp$", re.IGNORECASE),
    re.compile(r"^render[_-]?timestamp$", re.IGNORECASE),
    re.compile(r"^analytics[_-]?session", re.IGNORECASE),
]

VOLATILE_VALUE_PATTERNS = [
    # ISO timestamps: 2024-01-01T00:00:00.000Z
    re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"),
    # Unix timestamps (10+ digits)
    re.compile(r"^\d{10,13}$"),
    # UUIDs
    re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE),
]

# Dynamic attribute patterns in DOM elements
DYNAMIC_ATTR_PATTERNS = [
    re.compile(r"^data-reactid$"),
    re.compile(r"^data-react-checksum$"),
    re.compile(r"^data-v-[a-f0-9]+$"),
    re.compile(r"^data-ember-"),
    re.compile(r"^ng-reflect-"),
    re.compile(r"^_nghost-"),
    re.compile(r"^_ngcontent-"),
]

# Landmark detection patterns for structural fingerprinting
LANDMARK_PATTERNS = {
    "nav": {
        "tags": {"nav", "header"},
        "roles": {"navigation", "banner", "menubar"},
        "classes": re.compile(r"(nav|menu|header|topbar|sidebar)", re.IGNORECASE),
    },
    "form": {
        "tags": {"form"},
        "roles": {"form", "search"},
        "classes": re.compile(r"(form|login|signup|search|checkout|register)", re.IGNORECASE),
    },
    "list": {
        "tags": {"ul", "ol", "dl"},
        "roles": {"list", "listbox", "grid"},
        "classes": re.compile(r"(list|items|results|entries|feed)", re.IGNORECASE),
    },
    "table": {
        "tags": {"table"},
        "roles": {"table", "grid", "treegrid"},
        "classes": re.compile(r"(table|grid|datagrid|spreadsheet)", re.IGNORECASE),
    },
    "main": {
        "tags": {"main", "article"},
        "roles": {"main", "article"},
        "classes": re.compile(r"(main|content|article|body|primary)", re.IGNORECASE),
    },
    "modal": {
        "tags": {"dialog"},
        "roles": {"dialog", "alertdialog"},
        "classes": re.compile(r"(modal|dialog|overlay|popup|lightbox)", re.IGNORECASE),
    },
    "footer": {
        "tags": {"footer"},
        "roles": {"contentinfo"},
        "classes": re.compile(r"(footer|bottom|copyright)", re.IGNORECASE),
    },
}


class SnapshotCanonicalizer:
    """
    Stateless snapshot canonicalization engine.

    All methods are pure functions (no side effects, no state).
    Given identical input, output is always identical (deterministic).

    Pipeline: raw -> remove_volatiles -> sort_keys -> normalize_whitespace
              -> normalize_unicode -> json_canonicalize -> sha256
    """

    def remove_volatiles(self, snapshot: dict) -> dict:
        """
        Remove volatile keys and values from snapshot.

        Strips timestamps, session tokens, nonces, cache busters, and
        other time-dependent or session-dependent data that would cause
        identical DOM states to produce different hashes.

        Args:
            snapshot: raw snapshot dict from browser capture

        Returns:
            dict with volatile entries removed (deep copy)
        """
        return self._remove_volatiles_recursive(snapshot)

    def _remove_volatiles_recursive(self, obj: Any) -> Any:
        """Recursive volatile removal."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Skip volatile keys
                if any(pat.search(key) for pat in VOLATILE_KEY_PATTERNS):
                    continue
                # Skip volatile string values
                if isinstance(value, str) and any(
                    pat.search(value) for pat in VOLATILE_VALUE_PATTERNS
                ):
                    continue
                result[key] = self._remove_volatiles_recursive(value)
            return result
        elif isinstance(obj, list):
            return [self._remove_volatiles_recursive(item) for item in obj]
        else:
            return obj

    def prune_empty(self, obj: Any) -> Any:
        """
        Remove empty dicts and empty strings left behind by volatile stripping.

        When volatile keys are removed from a dict, the parent dict may become
        empty. This would cause structural differences between snapshots that
        never had the key vs ones that had it stripped. Pruning empties ensures
        both cases produce identical canonical form.

        Args:
            obj: any JSON-compatible value

        Returns:
            deep copy with empty dicts removed from parent dicts
        """
        if isinstance(obj, dict):
            pruned = {}
            for k, v in obj.items():
                cleaned = self.prune_empty(v)
                # Keep empty lists (they may be semantically meaningful)
                # but skip empty dicts (artifacts of volatile stripping)
                if isinstance(cleaned, dict) and len(cleaned) == 0:
                    continue
                pruned[k] = cleaned
            return pruned
        elif isinstance(obj, list):
            return [self.prune_empty(item) for item in obj]
        else:
            return obj

    def sort_keys(self, obj: Any) -> Any:
        """
        Recursively sort all dictionary keys for deterministic ordering.

        JSON object key order is not guaranteed by spec. Sorting ensures
        identical logical structures always produce identical bytes.

        Args:
            obj: any JSON-compatible value

        Returns:
            deep copy with all dict keys sorted alphabetically
        """
        if isinstance(obj, dict):
            return {k: self.sort_keys(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [self.sort_keys(item) for item in obj]
        else:
            return obj

    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text content.

        Collapses runs of whitespace to single spaces and strips
        leading/trailing whitespace. This handles browser-specific
        whitespace rendering differences.

        Args:
            text: raw text string

        Returns:
            normalized text with collapsed whitespace
        """
        if not isinstance(text, str):
            return text
        # Collapse all whitespace (including newlines, tabs) to single space
        normalized = re.sub(r"\s+", " ", text)
        return normalized.strip()

    def normalize_whitespace_deep(self, obj: Any) -> Any:
        """
        Apply whitespace normalization recursively to all string values.

        Args:
            obj: any JSON-compatible value

        Returns:
            deep copy with all string values whitespace-normalized
        """
        if isinstance(obj, str):
            return self.normalize_whitespace(obj)
        elif isinstance(obj, dict):
            return {k: self.normalize_whitespace_deep(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.normalize_whitespace_deep(item) for item in obj]
        else:
            return obj

    def normalize_unicode(self, obj: Any) -> Any:
        """
        Apply NFC unicode normalization to all string values.

        Different platforms may encode the same characters differently
        (e.g., e-acute as single codepoint vs e + combining accent).
        NFC normalization ensures byte-identical representation.

        Args:
            obj: any JSON-compatible value

        Returns:
            deep copy with all strings NFC-normalized
        """
        if isinstance(obj, str):
            return unicodedata.normalize("NFC", obj)
        elif isinstance(obj, dict):
            return {
                unicodedata.normalize("NFC", k) if isinstance(k, str) else k:
                self.normalize_unicode(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self.normalize_unicode(item) for item in obj]
        else:
            return obj

    def remove_dynamic_attrs(self, obj: Any) -> Any:
        """
        Remove framework-specific dynamic attributes from DOM elements.

        React, Vue, Angular, and Ember inject dynamic attributes that
        change on every render. These must be stripped for determinism.

        Args:
            obj: snapshot or DOM node dict

        Returns:
            deep copy with dynamic attributes removed
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if any(pat.search(key) for pat in DYNAMIC_ATTR_PATTERNS):
                    continue
                result[key] = self.remove_dynamic_attrs(value)
            return result
        elif isinstance(obj, list):
            return [self.remove_dynamic_attrs(item) for item in obj]
        else:
            return obj

    def json_canonicalize(self, obj: Any) -> str:
        """
        Produce canonical JSON string from object.

        Uses sorted keys, no trailing whitespace, consistent separators.
        This is the final serialization step before hashing.

        Args:
            obj: any JSON-serializable value

        Returns:
            canonical JSON string (deterministic byte sequence)
        """
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    def canonicalize_snapshot(self, raw: dict) -> Dict[str, Any]:
        """
        Full canonicalization pipeline.

        Applies all normalization steps in order:
        1. Remove volatiles (timestamps, tokens, nonces)
        2. Remove dynamic attrs (React, Vue, Angular)
        3. Sort keys (deterministic ordering)
        4. Normalize whitespace (collapse runs)
        5. Normalize unicode (NFC)
        6. JSON canonicalize (deterministic bytes)
        7. SHA-256 hash

        Args:
            raw: raw snapshot dict from browser capture

        Returns:
            dict with keys:
              - canonical_bytes: the canonical JSON bytes
              - sha256: hex digest of canonical bytes
              - size_bytes: length of canonical bytes
        """
        # Pipeline
        step1 = self.remove_volatiles(raw)
        step2 = self.remove_dynamic_attrs(step1)
        step2b = self.prune_empty(step2)
        step3 = self.sort_keys(step2b)
        step4 = self.normalize_whitespace_deep(step3)
        step5 = self.normalize_unicode(step4)
        canonical_json = self.json_canonicalize(step5)
        canonical_bytes = canonical_json.encode("utf-8")
        sha256_hash = hashlib.sha256(canonical_bytes).hexdigest()

        return {
            "canonical_bytes": canonical_bytes,
            "sha256": sha256_hash,
            "size_bytes": len(canonical_bytes),
        }

    def verify_determinism(self, snapshot: dict, iterations: int = 100) -> bool:
        """
        Verify that canonicalization is deterministic.

        Runs the full pipeline N times on the same input and verifies
        all hashes are identical. This is the 641-edge sanity test.

        Args:
            snapshot: raw snapshot dict
            iterations: number of times to run (default 100)

        Returns:
            True if all iterations produce identical hash, False otherwise
        """
        hashes = set()
        for _ in range(iterations):
            result = self.canonicalize_snapshot(snapshot)
            hashes.add(result["sha256"])
        return len(hashes) == 1

    def extract_landmarks(self, dom: dict) -> List[str]:
        """
        Extract structural landmarks from DOM snapshot.

        Identifies navigational, form, list, table, main content,
        modal, and footer regions. These landmarks are used for
        semantic refmap construction in the recipe compiler.

        Args:
            dom: DOM snapshot dict (may contain 'elements', 'tag',
                 'attributes', 'children', 'role', 'className' keys)

        Returns:
            list of landmark identifiers (e.g., "nav:header", "form:login")
        """
        landmarks = []
        self._extract_landmarks_recursive(dom, landmarks, depth=0)
        return sorted(set(landmarks))

    def _extract_landmarks_recursive(
        self, node: Any, landmarks: List[str], depth: int
    ) -> None:
        """Recursive landmark extraction from DOM tree."""
        if depth > 50:  # Guard against pathological nesting
            return

        if isinstance(node, dict):
            tag = (node.get("tag") or node.get("tagName") or "").lower()
            role = (node.get("role") or node.get("aria-role") or "").lower()
            class_name = node.get("className") or node.get("class") or ""
            node_id = node.get("id") or ""

            # Check attributes dict if present
            attrs = node.get("attributes") or {}
            if not role and isinstance(attrs, dict):
                role = (attrs.get("role") or "").lower()
            if not class_name and isinstance(attrs, dict):
                class_name = attrs.get("class") or ""
            if not node_id and isinstance(attrs, dict):
                node_id = attrs.get("id") or ""

            for lm_type, patterns in LANDMARK_PATTERNS.items():
                matched = False
                match_detail = ""

                # Match by tag
                if tag in patterns["tags"]:
                    matched = True
                    match_detail = f"tag:{tag}"

                # Match by ARIA role
                if not matched and role in patterns["roles"]:
                    matched = True
                    match_detail = f"role:{role}"

                # Match by class name
                if not matched and class_name and patterns["classes"].search(class_name):
                    matched = True
                    match_detail = f"class:{class_name[:30]}"

                if matched:
                    identifier = f"{lm_type}:{match_detail}"
                    if node_id:
                        identifier += f"#{node_id}"
                    landmarks.append(identifier)

            # Recurse into children
            children = node.get("children") or node.get("childNodes") or []
            if isinstance(children, list):
                for child in children:
                    self._extract_landmarks_recursive(child, landmarks, depth + 1)

            # Also recurse into 'elements' arrays (flat snapshot format)
            elements = node.get("elements") or []
            if isinstance(elements, list):
                for elem in elements:
                    self._extract_landmarks_recursive(elem, landmarks, depth + 1)

        elif isinstance(node, list):
            for item in node:
                self._extract_landmarks_recursive(item, landmarks, depth + 1)

    def fingerprint(self, snapshot: dict) -> str:
        """
        Quick fingerprint of snapshot (first 16 chars of sha256).

        Useful for logging and dedup checks without full canonicalization
        overhead (though full hash is still computed internally).

        Args:
            snapshot: raw snapshot dict

        Returns:
            16-character hex fingerprint
        """
        result = self.canonicalize_snapshot(snapshot)
        return result["sha256"][:16]

    def diff_snapshots(
        self, snap_a: dict, snap_b: dict
    ) -> Dict[str, Any]:
        """
        Compare two snapshots and return structural diff.

        Both snapshots are canonicalized first, then compared.
        Returns keys that were added, removed, or changed.

        Args:
            snap_a: first snapshot (before)
            snap_b: second snapshot (after)

        Returns:
            dict with keys:
              - same: bool (True if identical canonical hash)
              - hash_a: sha256 of snap_a
              - hash_b: sha256 of snap_b
              - added_keys: keys present in b but not a (top-level)
              - removed_keys: keys present in a but not b (top-level)
              - changed_keys: keys present in both with different values
        """
        result_a = self.canonicalize_snapshot(snap_a)
        result_b = self.canonicalize_snapshot(snap_b)

        if result_a["sha256"] == result_b["sha256"]:
            return {
                "same": True,
                "hash_a": result_a["sha256"],
                "hash_b": result_b["sha256"],
                "added_keys": [],
                "removed_keys": [],
                "changed_keys": [],
            }

        # Parse canonical bytes back for comparison
        canon_a = json.loads(result_a["canonical_bytes"])
        canon_b = json.loads(result_b["canonical_bytes"])

        keys_a = set(canon_a.keys()) if isinstance(canon_a, dict) else set()
        keys_b = set(canon_b.keys()) if isinstance(canon_b, dict) else set()

        added = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        common = keys_a & keys_b
        changed = sorted(k for k in common if canon_a[k] != canon_b[k])

        return {
            "same": False,
            "hash_a": result_a["sha256"],
            "hash_b": result_b["sha256"],
            "added_keys": added,
            "removed_keys": removed,
            "changed_keys": changed,
        }
