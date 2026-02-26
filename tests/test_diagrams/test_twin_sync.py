"""
test_twin_sync.py
==================
Derived from: data/default/diagrams/twin-sync-flow.md

Tests the twin sync protocol:
  - Session state serialization (StateBundleLocal schema)
  - AES-256-GCM encryption (ciphertext, nonce_96bit, auth_tag)
  - LOCAL_WINS conflict resolution FSM
  - Sync receipt generation
  - Zero-knowledge property: cloud receives ciphertext only, never plaintext
  - Certificate pinning enforcement on wss:// tunnel

FSM states from LOCAL_WINS diagram:
  SYNC_CHECK → NO_CONFLICT | CONFLICT_DETECTED
  CONFLICT_DETECTED → COMPARE_VERSIONS → LOCAL_WINS_APPLY | MANUAL_MERGE_REQUIRED

Run:
    python -m pytest tests/test_data/default/diagrams/test_twin_sync.py -v
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

try:
    from twin_sync import (
        TwinSyncEngine,
        StateBundleLocal,
        EncryptedPayload,
        SyncReceipt,
        ConflictResolution,
        LocalWinsResult,
        SyncStatus,
    )
    _TWIN_SYNC_AVAILABLE = True
except ImportError:
    _TWIN_SYNC_AVAILABLE = False

_NEEDS_SYNC = pytest.mark.xfail(
    not _TWIN_SYNC_AVAILABLE,
    reason="twin_sync module not yet implemented",
    strict=False,
)


# ---------------------------------------------------------------------------
# State bundle serialization
# ---------------------------------------------------------------------------


class TestStateBundleSerialization:
    """
    Diagram: StateBundleLocal classDiagram schema.
    The state bundle must capture: state_id, capture_timestamp,
    local_wins_version, platforms[], fingerprint_hash,
    recipes_version, evidence_chain_tip.
    """

    @_NEEDS_SYNC
    def test_state_bundle_has_required_fields(self, local_state_bundle):
        """
        StateBundleLocal must carry all fields from the classDiagram definition.
        """
        required = [
            "state_id", "capture_timestamp", "local_wins_version",
            "platforms", "fingerprint_hash", "recipes_version", "evidence_chain_tip",
        ]
        engine = TwinSyncEngine()
        bundle = engine.capture_state()
        bundle_dict = bundle.__dict__ if hasattr(bundle, "__dict__") else dict(bundle)
        for field in required:
            assert field in bundle_dict, f"StateBundleLocal missing field '{field}'"

    @_NEEDS_SYNC
    def test_state_bundle_local_wins_version_is_monotonic_int(self):
        """
        local_wins_version must be a non-negative integer.
        It is used as a monotonic counter for conflict resolution.
        """
        engine = TwinSyncEngine()
        bundle = engine.capture_state()
        assert isinstance(bundle.local_wins_version, int)
        assert bundle.local_wins_version >= 0

    @_NEEDS_SYNC
    def test_state_bundle_platforms_list_is_list(self):
        """platforms field must be a list (even if empty)."""
        engine = TwinSyncEngine()
        bundle = engine.capture_state()
        assert isinstance(bundle.platforms, list)

    @_NEEDS_SYNC
    def test_state_bundle_fingerprint_hash_is_sha256(self):
        """
        fingerprint_hash must be a 64-char hex string (SHA256 of browser fingerprint).
        """
        engine = TwinSyncEngine()
        bundle = engine.capture_state()
        assert isinstance(bundle.fingerprint_hash, str)
        assert len(bundle.fingerprint_hash) == 64

    @_NEEDS_SYNC
    def test_state_bundle_capture_timestamp_is_iso8601(self):
        """capture_timestamp must be a valid ISO8601 string."""
        engine = TwinSyncEngine()
        bundle = engine.capture_state()
        # Must parse without raising
        dt = datetime.fromisoformat(bundle.capture_timestamp)
        assert dt.tzinfo is not None, "capture_timestamp must be timezone-aware"

    @_NEEDS_SYNC
    def test_state_bundle_serializes_to_bytes(self):
        """
        The bundle must be serializable to bytes for AES-256-GCM encryption.
        """
        engine = TwinSyncEngine()
        bundle = engine.capture_state()
        serialized = engine.serialize_bundle(bundle)
        assert isinstance(serialized, (bytes, bytearray))
        assert len(serialized) > 0


# ---------------------------------------------------------------------------
# AES-256-GCM encryption
# ---------------------------------------------------------------------------


class TestAES256GCMEncryption:
    """
    Diagram: AES-256-GCM encrypt(state, key, nonce)
    EncryptedPayload schema: ciphertext, nonce_96bit, auth_tag, sha256_of_ciphertext

    Zero-knowledge property:
      - User master key NEVER transmitted
      - Cloud receives ciphertext only
      - sha256(ciphertext) used as receipt confirmation
    """

    @_NEEDS_SYNC
    def test_encrypt_produces_encrypted_payload(self, local_state_bundle):
        """
        encrypt_bundle() must return an EncryptedPayload with all required fields.
        """
        engine = TwinSyncEngine()
        bundle_bytes = b"mock-state-bundle-data"
        key = bytes(32)  # 256-bit zero key (test only)
        payload = engine.encrypt_bundle(bundle_bytes, key=key)
        assert hasattr(payload, "ciphertext")
        assert hasattr(payload, "nonce_96bit")
        assert hasattr(payload, "auth_tag")
        assert hasattr(payload, "sha256_of_ciphertext")

    @_NEEDS_SYNC
    def test_nonce_is_96_bits(self, local_state_bundle):
        """
        AES-256-GCM standard: nonce must be 96 bits (12 bytes).
        """
        engine = TwinSyncEngine()
        bundle_bytes = b"mock-state-bundle-data"
        key = bytes(32)
        payload = engine.encrypt_bundle(bundle_bytes, key=key)
        assert len(payload.nonce_96bit) == 12, (
            f"Nonce must be 12 bytes (96 bits), got {len(payload.nonce_96bit)}"
        )

    @_NEEDS_SYNC
    def test_auth_tag_is_128_bits(self):
        """AES-256-GCM auth tag must be 16 bytes (128 bits)."""
        engine = TwinSyncEngine()
        bundle_bytes = b"mock-state-bundle-data"
        key = bytes(32)
        payload = engine.encrypt_bundle(bundle_bytes, key=key)
        assert len(payload.auth_tag) == 16, (
            f"Auth tag must be 16 bytes (128 bits), got {len(payload.auth_tag)}"
        )

    @_NEEDS_SYNC
    def test_sha256_of_ciphertext_matches_ciphertext(self):
        """
        Diagram: cloud confirms sha256(ciphertext) matches sent payload.
        sha256_of_ciphertext must equal sha256(ciphertext).
        """
        engine = TwinSyncEngine()
        bundle_bytes = b"mock-state-bundle-data"
        key = bytes(32)
        payload = engine.encrypt_bundle(bundle_bytes, key=key)
        expected = hashlib.sha256(payload.ciphertext).hexdigest()
        assert payload.sha256_of_ciphertext == expected

    @_NEEDS_SYNC
    def test_encryption_is_not_deterministic(self):
        """
        AES-256-GCM with random nonce: same plaintext produces different ciphertext.
        Deterministic encryption is a security flaw.
        """
        engine = TwinSyncEngine()
        bundle_bytes = b"same-plaintext-every-time"
        key = bytes(32)
        payload1 = engine.encrypt_bundle(bundle_bytes, key=key)
        payload2 = engine.encrypt_bundle(bundle_bytes, key=key)
        assert payload1.ciphertext != payload2.ciphertext, (
            "Encryption must use random nonce — same plaintext must produce different ciphertext"
        )

    @_NEEDS_SYNC
    def test_key_never_transmitted_in_plaintext(self):
        """
        Zero-knowledge property: the user master key must not appear in the
        EncryptedPayload (neither in ciphertext field attributes nor in
        any string representation).
        """
        engine = TwinSyncEngine()
        bundle_bytes = b"mock-data"
        key = b"super-secret-master-key-32bytes!"  # 32 bytes
        payload = engine.encrypt_bundle(bundle_bytes, key=key)
        payload_dict = payload.__dict__ if hasattr(payload, "__dict__") else {}
        for field, value in payload_dict.items():
            if isinstance(value, (bytes, bytearray)):
                assert key not in value, (
                    f"Master key found in payload.{field} — zero-knowledge violation"
                )


# ---------------------------------------------------------------------------
# LOCAL_WINS conflict resolution FSM
# ---------------------------------------------------------------------------


class TestLocalWinsConflictResolution:
    """
    Diagram: LOCAL_WINS conflict resolution FSM
    SYNC_CHECK → NO_CONFLICT | CONFLICT_DETECTED
    CONFLICT_DETECTED → COMPARE_VERSIONS
    COMPARE_VERSIONS → LOCAL_WINS_APPLY (local >= cloud)
                     | MANUAL_MERGE_REQUIRED (cloud > local)
    LOCAL_WINS_APPLY → APPLY_LOCAL_TO_CLOUD → MERGE_CLOUD
    MANUAL_MERGE_REQUIRED → USER_PROMPT → MERGE_CLOUD | KEEP_LOCAL
    """

    @_NEEDS_SYNC
    def test_no_conflict_when_versions_match(self):
        """
        Diagram: NO_CONFLICT when cloud_version == local_version.
        """
        engine = TwinSyncEngine()
        result = engine.resolve_conflict(
            local_wins_version=5,
            cloud_wins_version=5,
        )
        assert result.conflict_detected is False
        assert result.resolution == "NO_CONFLICT"

    @_NEEDS_SYNC
    def test_local_wins_when_local_version_greater(self):
        """
        Diagram: LOCAL_WINS_APPLY when local_wins_version >= cloud_wins_version.
        Cloud must be updated to match local state.
        """
        engine = TwinSyncEngine()
        result = engine.resolve_conflict(
            local_wins_version=7,
            cloud_wins_version=3,
        )
        assert result.conflict_detected is True
        assert result.resolution == "LOCAL_WINS"
        assert result.action == "APPLY_LOCAL_TO_CLOUD"

    @_NEEDS_SYNC
    def test_local_wins_when_versions_equal_with_conflict(self):
        """
        Diagram: local_wins_version >= cloud_wins_version → LOCAL_WINS.
        Equal versions with detected conflict → LOCAL_WINS (local is authoritative).
        """
        engine = TwinSyncEngine()
        result = engine.resolve_conflict(
            local_wins_version=5,
            cloud_wins_version=5,
            force_conflict=True,  # simulate detected content difference
        )
        # Equal versions: local wins by default
        assert result.resolution in ("LOCAL_WINS", "NO_CONFLICT")

    @_NEEDS_SYNC
    def test_manual_merge_when_cloud_version_greater(self):
        """
        Diagram: MANUAL_MERGE_REQUIRED when cloud_wins_version > local_wins_version.
        """
        engine = TwinSyncEngine()
        result = engine.resolve_conflict(
            local_wins_version=2,
            cloud_wins_version=10,
        )
        assert result.conflict_detected is True
        assert result.resolution == "MANUAL_MERGE_REQUIRED"

    @_NEEDS_SYNC
    def test_local_wins_note_cloud_never_overwrites_silently(self, local_state_bundle):
        """
        Diagram note: 'Cloud never overwrites local silently.'
        Any cloud-to-local state write must go through conflict resolution,
        not bypass it.
        """
        engine = TwinSyncEngine()
        # Simulate cloud trying to overwrite local with older version
        result = engine.apply_cloud_result(
            local_state=local_state_bundle,
            cloud_result={"local_wins_version": 0, "data": "stale-cloud-data"},
        )
        # Cloud result with lower version must NOT overwrite local
        assert result.local_state_overwritten is False


# ---------------------------------------------------------------------------
# Sync receipt
# ---------------------------------------------------------------------------


class TestSyncReceipt:
    """
    Diagram: SyncReceipt classDiagram schema.
    Receipt produced after successful upward sync.
    Fields: sync_id, sync_timestamp, state_id, cloud_payload_hash_confirmed,
            conflict_detected, local_wins_applied, tunnel_cert_pinned, rung_achieved.
    """

    @_NEEDS_SYNC
    def test_sync_receipt_has_required_fields(self, local_state_bundle, encrypted_payload):
        """Sync receipt must carry all fields from the classDiagram."""
        required = [
            "sync_id", "sync_timestamp", "state_id",
            "cloud_payload_hash_confirmed", "conflict_detected",
            "local_wins_applied", "tunnel_cert_pinned", "rung_achieved",
        ]
        engine = TwinSyncEngine()
        mock_cloud = MagicMock()
        mock_cloud.upload.return_value = encrypted_payload["sha256_of_ciphertext"]
        receipt = engine.generate_sync_receipt(
            state_bundle=local_state_bundle,
            encrypted_payload=encrypted_payload,
            cloud=mock_cloud,
        )
        receipt_dict = receipt.__dict__ if hasattr(receipt, "__dict__") else dict(receipt)
        for field in required:
            assert field in receipt_dict, f"SyncReceipt missing field '{field}'"

    @_NEEDS_SYNC
    def test_sync_receipt_confirms_hash_matches_sent_payload(
        self, local_state_bundle, encrypted_payload
    ):
        """
        Diagram: Local verifies sha256 matches sent payload.
        cloud_payload_hash_confirmed must equal sha256_of_ciphertext.
        """
        engine = TwinSyncEngine()
        mock_cloud = MagicMock()
        mock_cloud.upload.return_value = encrypted_payload["sha256_of_ciphertext"]
        receipt = engine.generate_sync_receipt(
            state_bundle=local_state_bundle,
            encrypted_payload=encrypted_payload,
            cloud=mock_cloud,
        )
        assert receipt.cloud_payload_hash_confirmed == encrypted_payload["sha256_of_ciphertext"]

    @_NEEDS_SYNC
    def test_sync_receipt_tunnel_cert_pinned_flag(self, local_state_bundle, encrypted_payload):
        """
        tunnel_cert_pinned must be True when the wss:// tunnel was cert-pinned.
        A receipt with tunnel_cert_pinned=False is a security violation signal.
        """
        engine = TwinSyncEngine()
        mock_cloud = MagicMock()
        mock_cloud.upload.return_value = encrypted_payload["sha256_of_ciphertext"]
        mock_cloud.cert_pinned = True
        receipt = engine.generate_sync_receipt(
            state_bundle=local_state_bundle,
            encrypted_payload=encrypted_payload,
            cloud=mock_cloud,
        )
        assert receipt.tunnel_cert_pinned is True


# ---------------------------------------------------------------------------
# Zero-knowledge property
# ---------------------------------------------------------------------------


class TestZeroKnowledgeProperty:
    """
    Diagram: Zero-Knowledge Guarantee
    Cloud receives ciphertext only — cannot reconstruct user master key.
    """

    @_NEEDS_SYNC
    def test_cloud_upload_receives_only_ciphertext(self, local_state_bundle):
        """
        Diagram: POST ciphertext + nonce + auth_tag to cloud.
        The cloud upload call must NOT include the user master key.
        """
        engine = TwinSyncEngine()
        mock_cloud = MagicMock()
        mock_cloud.upload.return_value = "sha256-hash-of-ciphertext"

        key = b"user-master-key-32bytes-exactly!"
        engine.sync_to_cloud(
            state_bundle=local_state_bundle,
            user_key=key,
            cloud=mock_cloud,
        )

        # Inspect what was passed to cloud.upload
        assert mock_cloud.upload.called
        call_args = mock_cloud.upload.call_args
        # The plaintext key must not appear in any argument
        all_args = str(call_args)
        assert key.decode(errors="replace") not in all_args, (
            "User master key transmitted to cloud — zero-knowledge violation"
        )

    @_NEEDS_SYNC
    def test_cloud_cannot_decrypt_without_envelope_key(self, local_state_bundle):
        """
        The cloud must use the session key from the encrypted envelope to decrypt.
        Without the session key, decryption must fail (raise or return error).
        """
        engine = TwinSyncEngine()
        bundle_bytes = b"plaintext-session-data"
        key = bytes(32)
        payload = engine.encrypt_bundle(bundle_bytes, key=key)

        # Try to decrypt with a wrong key (simulates cloud without correct key)
        wrong_key = bytes(31) + b"\xff"
        with pytest.raises(Exception):
            engine.decrypt_payload(payload, key=wrong_key)
