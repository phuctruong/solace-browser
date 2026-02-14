#!/usr/bin/env python3
"""
Solace Browser Phase B Integration Module

Integrates snapshot canonicalization (B1) with episode-to-recipe compiler (B2)
and provides high-level APIs for the Phase C replay engine.

Usage:
    from solace_cli.browser.integration import compile_episode, verify_recipe

    recipe = compile_episode(episode_dict)
    valid = verify_recipe(recipe)

Auth: 65537 | Northstar: Phuc Forecast
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .snapshot_canonicalization import SnapshotCanonicalizer
from .episode_to_recipe_compiler import EpisodeCompiler, RefMap


LOG_DIR = Path.home() / ".solace" / "browser"


def compile_episode(episode: dict) -> Dict[str, Any]:
    """
    Compile a Phase A episode into a Phase B recipe.

    Args:
        episode: raw episode dict from BrowserSession.to_episode()

    Returns:
        compiled recipe IR dict
    """
    compiler = EpisodeCompiler()
    return compiler.compile_episode(episode)


def compile_episode_file(filepath: str) -> Dict[str, Any]:
    """
    Load and compile an episode from a JSON file.

    Args:
        filepath: path to episode JSON file

    Returns:
        compiled recipe IR dict
    """
    with open(filepath, "r") as f:
        episode = json.load(f)
    return compile_episode(episode)


def compile_all_episodes(directory: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Compile all episode files in a directory.

    Args:
        directory: path to directory with episode_*.json files
                   (default: ~/.solace/browser/)

    Returns:
        list of compiled recipe IR dicts
    """
    episode_dir = Path(directory) if directory else LOG_DIR
    recipes = []

    for filepath in sorted(episode_dir.glob("episode_*.json")):
        try:
            with open(filepath, "r") as f:
                episode = json.load(f)
            recipe = compile_episode(episode)
            recipe["_source_file"] = str(filepath)
            recipes.append(recipe)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            recipes.append({
                "_source_file": str(filepath),
                "_error": str(e),
            })

    return recipes


def verify_recipe(recipe: dict) -> Dict[str, Any]:
    """
    Verify a compiled recipe's proof chain.

    Checks:
      1. Recipe hash matches proof.recipe_hash
      2. Snapshot hashes match proof.snapshot_hashes
      3. Chain hash is correct
      4. Action count matches

    Args:
        recipe: compiled recipe IR dict with proof field

    Returns:
        dict with keys:
          - valid: bool
          - checks: dict of individual check results
          - errors: list of error descriptions
    """
    proof = recipe.get("proof")
    if not proof:
        return {
            "valid": False,
            "checks": {},
            "errors": ["No proof field in recipe"],
        }

    errors = []
    checks = {}

    # Check 1: recipe hash
    recipe_copy = {k: v for k, v in recipe.items() if k != "proof"}
    recipe_json = json.dumps(recipe_copy, sort_keys=True, separators=(",", ":"))
    computed_recipe_hash = hashlib.sha256(recipe_json.encode("utf-8")).hexdigest()
    checks["recipe_hash"] = computed_recipe_hash == proof.get("recipe_hash", "")
    if not checks["recipe_hash"]:
        errors.append(
            f"Recipe hash mismatch: computed={computed_recipe_hash[:16]}, "
            f"proof={proof.get('recipe_hash', '')[:16]}"
        )

    # Check 2: snapshot hashes
    snapshots = recipe.get("snapshots") or {}
    computed_snap_hashes = []
    for key in sorted(snapshots.keys(), key=lambda k: int(k) if k.isdigit() else 0):
        snap = snapshots[key]
        if isinstance(snap, dict):
            computed_snap_hashes.append(snap.get("sha256", ""))

    proof_snap_hashes = proof.get("snapshot_hashes", [])
    checks["snapshot_hashes"] = computed_snap_hashes == proof_snap_hashes
    if not checks["snapshot_hashes"]:
        errors.append(
            f"Snapshot hash mismatch: {len(computed_snap_hashes)} computed vs "
            f"{len(proof_snap_hashes)} in proof"
        )

    # Check 3: action count
    action_count = len(recipe.get("actions", []))
    checks["action_count"] = action_count == proof.get("action_count", -1)
    if not checks["action_count"]:
        errors.append(
            f"Action count mismatch: {action_count} vs {proof.get('action_count')}"
        )

    # Check 4: chain hash
    chain_input = (
        proof.get("episode_hash", "") +
        proof.get("recipe_hash", "") +
        "".join(proof_snap_hashes)
    )
    computed_chain = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
    checks["chain_hash"] = computed_chain == proof.get("chain_hash", "")
    if not checks["chain_hash"]:
        errors.append(
            f"Chain hash mismatch: computed={computed_chain[:16]}, "
            f"proof={proof.get('chain_hash', '')[:16]}"
        )

    return {
        "valid": len(errors) == 0,
        "checks": checks,
        "errors": errors,
    }


def canonicalize_snapshot(raw: dict) -> Dict[str, Any]:
    """
    Canonicalize a single snapshot (convenience wrapper).

    Args:
        raw: raw snapshot dict

    Returns:
        dict with canonical_bytes, sha256, size_bytes
    """
    c = SnapshotCanonicalizer()
    return c.canonicalize_snapshot(raw)
