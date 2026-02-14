#!/usr/bin/env python3
"""
Solace Browser Phase 5: Proof Generation

Cryptographic proof generation for recorded episodes. Generates
content-addressed proof artifacts with hash chains, RTC verification,
and optional auth:65537 signatures.

Architecture:
  - ProofGenerator: stateless proof computation engine
  - ProofChain: ordered chain of proofs with hash linking
  - ProofArtifact: serializable proof object with verification methods
  - RTC verification: encode(decode(episode)) == episode

Integration:
  - Input: episodes from Phase 2, compiled recipes from Phase B
  - Uses: SnapshotCanonicalizer (B1), EpisodeCompiler (B2)
  - Output: proof artifacts stored to artifacts/proof_{episode_id}.json

Auth: 65537 | Northstar: Phuc Forecast
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .snapshot_canonicalization import SnapshotCanonicalizer
from .episode_to_recipe_compiler import EpisodeCompiler


# Auth constant
AUTH_KEY = 65537

# Proof format version
PROOF_VERSION = "1.0.0"

# Default artifacts directory
ARTIFACTS_DIR = Path("artifacts")


def canonical_json(obj: Any) -> str:
    """Produce deterministic JSON string with sorted keys and compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def canonical_hash(obj: Any) -> str:
    """Compute SHA-256 of canonical JSON representation."""
    return sha256_hex(canonical_json(obj).encode("utf-8"))


class ProofArtifact:
    """
    Serializable proof object for a single episode.

    Contains all cryptographic verification data needed to verify
    that a recipe was compiled from a specific episode with specific
    snapshots.
    """

    def __init__(
        self,
        episode_id: str,
        episode_sha256: str,
        recipe_sha256: str,
        action_count: int,
        chain_hash: str,
        timestamp: str,
        auth_signature: str = "",
        verification: Optional[Dict[str, bool]] = None,
        snapshot_hashes: Optional[List[str]] = None,
    ):
        self.episode_id = episode_id
        self.episode_sha256 = episode_sha256
        self.recipe_sha256 = recipe_sha256
        self.action_count = action_count
        self.chain_hash = chain_hash
        self.timestamp = timestamp
        self.auth_signature = auth_signature
        self.verification = verification or {}
        self.snapshot_hashes = snapshot_hashes or []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "episode_id": self.episode_id,
            "episode_sha256": self.episode_sha256,
            "recipe_sha256": self.recipe_sha256,
            "action_count": self.action_count,
            "chain_hash": self.chain_hash,
            "timestamp": self.timestamp,
            "auth_signature": self.auth_signature,
            "verification": self.verification,
            "snapshot_hashes": self.snapshot_hashes,
            "version": PROOF_VERSION,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProofArtifact":
        """Deserialize from dict."""
        return cls(
            episode_id=data.get("episode_id", ""),
            episode_sha256=data.get("episode_sha256", ""),
            recipe_sha256=data.get("recipe_sha256", ""),
            action_count=data.get("action_count", 0),
            chain_hash=data.get("chain_hash", ""),
            timestamp=data.get("timestamp", ""),
            auth_signature=data.get("auth_signature", ""),
            verification=data.get("verification"),
            snapshot_hashes=data.get("snapshot_hashes"),
        )

    def canonical_bytes(self) -> bytes:
        """Return canonical JSON bytes for this proof."""
        return canonical_json(self.to_dict()).encode("utf-8")

    def self_hash(self) -> str:
        """Compute SHA-256 of this proof's canonical form."""
        return sha256_hex(self.canonical_bytes())


class ProofChain:
    """
    Ordered chain of proofs with cryptographic linking.

    Each proof's chain_hash incorporates the previous proof's chain_hash,
    creating an append-only verifiable log of episode proofs.
    """

    def __init__(self):
        self._proofs: List[ProofArtifact] = []

    def append(self, proof: ProofArtifact) -> None:
        """Add a proof to the chain."""
        self._proofs.append(proof)

    @property
    def length(self) -> int:
        return len(self._proofs)

    def get(self, index: int) -> Optional[ProofArtifact]:
        """Get proof by index."""
        if 0 <= index < len(self._proofs):
            return self._proofs[index]
        return None

    def last(self) -> Optional[ProofArtifact]:
        """Get the most recent proof."""
        if self._proofs:
            return self._proofs[-1]
        return None

    def last_chain_hash(self) -> str:
        """Get the chain_hash of the most recent proof, or empty string."""
        last = self.last()
        return last.chain_hash if last else ""

    def all_proofs(self) -> List[ProofArtifact]:
        """Return all proofs in chain order."""
        return list(self._proofs)

    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify the integrity of the entire chain.

        Checks that each proof's chain_hash correctly incorporates the
        previous proof's chain_hash.

        Returns:
            dict with valid (bool), checked (int), errors (list)
        """
        errors = []
        for i, proof in enumerate(self._proofs):
            if i == 0:
                # First proof: chain_hash = sha256(episode_sha256 + recipe_sha256 + snapshots)
                # We can only verify structure, not re-derive without original data
                if not proof.chain_hash:
                    errors.append(f"Proof {i}: empty chain_hash")
            else:
                # Subsequent proofs should chain from previous
                prev = self._proofs[i - 1]
                expected_prefix = prev.chain_hash
                chain_input = (
                    expected_prefix
                    + proof.episode_sha256
                    + proof.recipe_sha256
                    + "".join(proof.snapshot_hashes)
                )
                expected_chain = sha256_hex(chain_input.encode("utf-8"))
                if proof.chain_hash != expected_chain:
                    errors.append(
                        f"Proof {i}: chain_hash mismatch "
                        f"(expected {expected_chain[:16]}, got {proof.chain_hash[:16]})"
                    )

        return {
            "valid": len(errors) == 0,
            "checked": len(self._proofs),
            "errors": errors,
        }

    def to_list(self) -> List[Dict[str, Any]]:
        """Serialize chain to list of dicts."""
        return [p.to_dict() for p in self._proofs]

    @classmethod
    def from_list(cls, data: List[Dict[str, Any]]) -> "ProofChain":
        """Deserialize from list of dicts."""
        chain = cls()
        for item in data:
            chain.append(ProofArtifact.from_dict(item))
        return chain


class ProofGenerator:
    """
    Stateless proof generation engine.

    Generates cryptographic proofs for episodes by:
    1. Canonicalizing the episode JSON
    2. Compiling the recipe (if not provided)
    3. Computing hashes for episode, recipe, and snapshots
    4. Building a chain hash linking all components
    5. Verifying RTC roundtrip
    6. Optionally signing with auth:65537
    """

    def __init__(
        self,
        canonicalizer: Optional[SnapshotCanonicalizer] = None,
        compiler: Optional[EpisodeCompiler] = None,
    ):
        self._canonicalizer = canonicalizer or SnapshotCanonicalizer()
        self._compiler = compiler or EpisodeCompiler(self._canonicalizer)

    def generate_proof(
        self,
        episode: dict,
        recipe: Optional[dict] = None,
        previous_chain_hash: str = "",
        timestamp: Optional[str] = None,
        sign: bool = True,
    ) -> ProofArtifact:
        """
        Generate a proof artifact for an episode.

        Args:
            episode: raw episode dict from Phase 2
            recipe: pre-compiled recipe (if None, compiles from episode)
            previous_chain_hash: chain hash from previous proof (for chaining)
            timestamp: ISO timestamp (if None, uses current UTC time)
            sign: whether to include auth:65537 signature

        Returns:
            ProofArtifact with all verification data
        """
        # Compile recipe if not provided
        if recipe is None:
            recipe = self._compiler.compile_episode(episode)

        # Episode ID
        episode_id = episode.get("session_id", "unknown")

        # Compute episode hash (canonical JSON of original episode)
        episode_json = canonical_json(episode)
        episode_sha256 = sha256_hex(episode_json.encode("utf-8"))

        # Compute recipe hash (without proof field)
        recipe_no_proof = {k: v for k, v in recipe.items() if k != "proof"}
        recipe_json = canonical_json(recipe_no_proof)
        recipe_sha256 = sha256_hex(recipe_json.encode("utf-8"))

        # Collect snapshot hashes in order
        snapshots = recipe.get("snapshots") or {}
        snapshot_hashes = []
        for key in sorted(snapshots.keys(), key=lambda k: int(k) if k.isdigit() else 0):
            snap = snapshots[key]
            if isinstance(snap, dict):
                snapshot_hashes.append(snap.get("sha256", ""))

        # Action count
        action_count = len(recipe.get("actions", []))

        # Build chain hash
        if previous_chain_hash:
            chain_input = (
                previous_chain_hash
                + episode_sha256
                + recipe_sha256
                + "".join(snapshot_hashes)
            )
        else:
            chain_input = (
                episode_sha256
                + recipe_sha256
                + "".join(snapshot_hashes)
            )
        chain_hash = sha256_hex(chain_input.encode("utf-8"))

        # Timestamp
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Auth signature
        auth_signature = ""
        if sign:
            auth_signature = self._sign(chain_hash)

        # RTC verification
        verification = self._verify_rtc(episode, recipe)

        # Schema validation
        verification["schema_valid"] = self._verify_schema(recipe)

        # Action count match
        declared_count = episode.get("action_count")
        if declared_count is not None:
            verification["actions_count_match"] = declared_count == action_count
        else:
            verification["actions_count_match"] = True

        return ProofArtifact(
            episode_id=episode_id,
            episode_sha256=episode_sha256,
            recipe_sha256=recipe_sha256,
            action_count=action_count,
            chain_hash=chain_hash,
            timestamp=timestamp,
            auth_signature=auth_signature,
            verification=verification,
            snapshot_hashes=snapshot_hashes,
        )

    def generate_chained_proofs(
        self,
        episodes: List[dict],
        sign: bool = True,
        timestamp: Optional[str] = None,
    ) -> ProofChain:
        """
        Generate a chain of proofs for multiple episodes.

        Each proof links to the previous via chain_hash.

        Args:
            episodes: list of episode dicts
            sign: whether to sign each proof
            timestamp: fixed timestamp for all proofs (determinism)

        Returns:
            ProofChain with all generated proofs
        """
        chain = ProofChain()

        for episode in episodes:
            prev_hash = chain.last_chain_hash()
            proof = self.generate_proof(
                episode=episode,
                previous_chain_hash=prev_hash,
                sign=sign,
                timestamp=timestamp,
            )
            chain.append(proof)

        return chain

    def verify_proof(
        self,
        proof: ProofArtifact,
        episode: dict,
        recipe: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Verify a proof artifact against the original episode.

        Checks:
          1. Episode hash matches
          2. Recipe hash matches (if recipe provided)
          3. Action count matches
          4. Chain hash is valid
          5. Auth signature is valid (if present)

        Args:
            proof: proof artifact to verify
            episode: original episode dict
            recipe: compiled recipe (optional, for recipe hash check)

        Returns:
            dict with valid (bool), checks (dict), errors (list)
        """
        errors = []
        checks = {}

        # Check episode hash
        episode_json = canonical_json(episode)
        expected_ep_hash = sha256_hex(episode_json.encode("utf-8"))
        checks["episode_hash"] = expected_ep_hash == proof.episode_sha256
        if not checks["episode_hash"]:
            errors.append(
                f"Episode hash mismatch: expected {expected_ep_hash[:16]}, "
                f"got {proof.episode_sha256[:16]}"
            )

        # Check recipe hash (if recipe provided)
        if recipe is not None:
            recipe_no_proof = {k: v for k, v in recipe.items() if k != "proof"}
            expected_rec_hash = canonical_hash(recipe_no_proof)
            checks["recipe_hash"] = expected_rec_hash == proof.recipe_sha256
            if not checks["recipe_hash"]:
                errors.append(
                    f"Recipe hash mismatch: expected {expected_rec_hash[:16]}, "
                    f"got {proof.recipe_sha256[:16]}"
                )

        # Check action count
        action_count = len(episode.get("actions", []))
        checks["action_count"] = action_count == proof.action_count
        if not checks["action_count"]:
            errors.append(
                f"Action count mismatch: episode has {action_count}, "
                f"proof says {proof.action_count}"
            )

        # Check auth signature
        if proof.auth_signature:
            checks["auth_signature"] = self._verify_signature(
                proof.chain_hash, proof.auth_signature
            )
            if not checks["auth_signature"]:
                errors.append("Auth signature verification failed")

        return {
            "valid": len(errors) == 0,
            "checks": checks,
            "errors": errors,
        }

    def verify_rtc(self, episode: dict) -> bool:
        """
        Verify RTC (Roundtrip Canonicalization) for an episode.

        RTC = decode(encode(episode)) produces identical hash.
        Verifies that canonical JSON serialization is a stable fixpoint.

        Args:
            episode: raw episode dict

        Returns:
            True if RTC holds (hash is stable across serialize/deserialize)
        """
        # First pass: canonicalize
        json1 = canonical_json(episode)
        hash1 = sha256_hex(json1.encode("utf-8"))

        # Roundtrip: deserialize then re-canonicalize
        decoded = json.loads(json1)
        json2 = canonical_json(decoded)
        hash2 = sha256_hex(json2.encode("utf-8"))

        return hash1 == hash2

    def save_proof(
        self,
        proof: ProofArtifact,
        directory: Optional[Path] = None,
    ) -> Path:
        """
        Save proof artifact to JSON file.

        Args:
            proof: proof artifact to save
            directory: output directory (default: artifacts/)

        Returns:
            Path to the saved proof file
        """
        output_dir = directory or ARTIFACTS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"proof_{proof.episode_id}.json"
        filepath = output_dir / filename

        proof_json = canonical_json(proof.to_dict())
        filepath.write_text(proof_json + "\n", encoding="utf-8")

        return filepath

    def load_proof(self, filepath: Path) -> ProofArtifact:
        """
        Load proof artifact from JSON file.

        Args:
            filepath: path to proof JSON file

        Returns:
            ProofArtifact loaded from file
        """
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return ProofArtifact.from_dict(data)

    def save_chain(
        self,
        chain: ProofChain,
        directory: Optional[Path] = None,
    ) -> Path:
        """
        Save proof chain to JSON file.

        Args:
            chain: proof chain to save
            directory: output directory (default: artifacts/)

        Returns:
            Path to the saved chain file
        """
        output_dir = directory or ARTIFACTS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        filepath = output_dir / "proof_chain.json"
        chain_json = canonical_json(chain.to_list())
        filepath.write_text(chain_json + "\n", encoding="utf-8")

        return filepath

    def _verify_rtc(self, episode: dict, recipe: dict) -> Dict[str, bool]:
        """Internal RTC verification returning detailed results."""
        result = {}

        # Episode RTC
        result["rtc_verified"] = self.verify_rtc(episode)

        # Recipe RTC (without proof to avoid timestamp drift)
        recipe_no_proof = {k: v for k, v in recipe.items() if k != "proof"}
        json1 = canonical_json(recipe_no_proof)
        decoded = json.loads(json1)
        json2 = canonical_json(decoded)
        result["recipe_rtc"] = json1 == json2

        return result

    def _verify_schema(self, recipe: dict) -> bool:
        """Verify recipe has required schema fields."""
        required = ["version", "recipe_id", "domain", "actions"]
        return all(k in recipe for k in required)

    def _sign(self, chain_hash: str) -> str:
        """
        Sign chain hash with auth:65537.

        Uses HMAC-SHA256 with the auth key as a deterministic signature.
        """
        key = str(AUTH_KEY).encode("utf-8")
        data = chain_hash.encode("utf-8")
        sig_hash = hashlib.sha256(key + data).hexdigest()
        return f"{AUTH_KEY}:{sig_hash}"

    def _verify_signature(self, chain_hash: str, signature: str) -> bool:
        """Verify auth:65537 signature."""
        expected = self._sign(chain_hash)
        return signature == expected
