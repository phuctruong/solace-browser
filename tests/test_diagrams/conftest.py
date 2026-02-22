"""
conftest.py — Shared fixtures for diagram-derived test suite.

Every fixture here models one of the core data structures defined in the
solace-browser diagrams.  Fixtures are intentionally minimal — they carry
only the fields required for the test contracts.  Implementation modules may
add richer behaviour; these fixtures just define the interface shape.

Diagrams covered:
  browser-multi-layer-architecture.md
  oauth3-enforcement-flow.md
  recipe-engine-fsm.md
  twin-sync-flow.md
  evidence-pipeline.md
  browser-action-lifecycle.md
  solace-browser-full-stack.md
  part11-alcoa-mapping.md
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ISSUER = "https://www.solaceagi.com"
SUBJECT = "user:testuser@example.com"
PLATFORM_LINKEDIN = "linkedin"
PLATFORM_GMAIL = "gmail"
SCOPE_LINKEDIN_CREATE = "linkedin.create_post"
SCOPE_LINKEDIN_READ = "linkedin.read.feed"
SCOPE_GMAIL_SEND = "gmail.compose.send"
SCOPE_GMAIL_READ = "gmail.read.inbox"
SCOPE_DESTRUCTIVE_DELETE = "linkedin.delete_post"
SCOPE_MACHINE_EXECUTE = "machine.execute_command"
SCOPE_TUNNEL_CONNECT = "tunnel.connect"

ALCOA_REQUIRED_FIELDS = [
    "schema_version",
    "bundle_id",
    "action_id",
    "action_type",
    "platform",
    "before_snapshot_pzip_hash",
    "after_snapshot_pzip_hash",
    "diff_hash",
    "oauth3_token_id",
    "timestamp_iso8601",
    "sha256_chain_link",
    "signature",
    "alcoa_fields",
    "rung_achieved",
]

ALCOA_DIMENSIONS = [
    "attributable",
    "legible",
    "contemporaneous",
    "original",
    "accurate",
    "complete",
    "consistent",
    "enduring",
    "available",
]

# ---------------------------------------------------------------------------
# OAuth3 token fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_oauth3_token() -> Dict[str, Any]:
    """A valid, non-expired OAuth3 token with LinkedIn read scope."""
    now = datetime.now(timezone.utc)
    return {
        "token_id": str(uuid.uuid4()),
        "issuer": ISSUER,
        "subject": SUBJECT,
        "scopes": [SCOPE_LINKEDIN_READ, SCOPE_GMAIL_READ],
        "intent": "Read LinkedIn feed for daily digest",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "revoked": False,
        "revoked_at": None,
    }


@pytest.fixture
def valid_oauth3_token_with_create(valid_oauth3_token) -> Dict[str, Any]:
    """Token with create (non-destructive write) scope."""
    token = dict(valid_oauth3_token)
    token["scopes"] = [SCOPE_LINKEDIN_CREATE, SCOPE_GMAIL_SEND]
    token["intent"] = "Create LinkedIn posts and send Gmail"
    return token


@pytest.fixture
def valid_oauth3_token_destructive(valid_oauth3_token) -> Dict[str, Any]:
    """Token with a destructive scope that triggers step-up (G4)."""
    token = dict(valid_oauth3_token)
    token["scopes"] = [SCOPE_DESTRUCTIVE_DELETE]
    token["intent"] = "Delete LinkedIn posts"
    return token


@pytest.fixture
def expired_oauth3_token(valid_oauth3_token) -> Dict[str, Any]:
    """Token whose expires_at is in the past."""
    token = dict(valid_oauth3_token)
    now = datetime.now(timezone.utc)
    token["issued_at"] = (now - timedelta(hours=3)).isoformat()
    token["expires_at"] = (now - timedelta(hours=2)).isoformat()
    return token


@pytest.fixture
def revoked_oauth3_token(valid_oauth3_token) -> Dict[str, Any]:
    """Token that has been explicitly revoked."""
    token = dict(valid_oauth3_token)
    token["revoked"] = True
    token["revoked_at"] = datetime.now(timezone.utc).isoformat()
    return token


@pytest.fixture
def token_vault(valid_oauth3_token) -> Dict[str, Dict[str, Any]]:
    """Minimal in-memory token vault: token_id → token dict."""
    return {valid_oauth3_token["token_id"]: valid_oauth3_token}


# ---------------------------------------------------------------------------
# Recipe fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_recipe() -> Dict[str, Any]:
    """A minimal valid recipe with required CLOSURE fields."""
    return {
        "recipe_id": str(uuid.uuid4()),
        "version": "1.0.0",
        "intent": "post to linkedin",
        "platform": PLATFORM_LINKEDIN,
        "action_type": "create_post",
        "oauth3_scopes_required": [SCOPE_LINKEDIN_CREATE],
        "max_steps": 10,
        "timeout_ms": 30000,
        "portals": ["https://www.linkedin.com/feed/"],
        "steps": [
            {
                "step_number": 1,
                "action": "click",
                "selector": "[aria-label='Start a post']",
                "checkpoint": True,
                "rollback": None,
                "max_retry": 3,
                "timeout_ms": 5000,
            }
        ],
        "output_schema": "post_created",
    }


@pytest.fixture
def recipe_cache_key(minimal_recipe) -> str:
    """SHA256 cache key for the minimal recipe."""
    normalized = (
        minimal_recipe["intent"].lower().strip()
        + minimal_recipe["platform"]
        + minimal_recipe["action_type"]
    )
    return hashlib.sha256(normalized.encode()).hexdigest()


@pytest.fixture
def recipe_store(minimal_recipe, recipe_cache_key) -> Dict[str, Dict[str, Any]]:
    """An in-memory recipe store with one cached recipe."""
    return {recipe_cache_key: minimal_recipe}


# ---------------------------------------------------------------------------
# Evidence bundle fixtures
# ---------------------------------------------------------------------------


def _make_sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


@pytest.fixture
def alcoa_fields() -> Dict[str, Any]:
    """A fully-populated ALCOAFields dict (all 9 dimensions)."""
    return {
        "attributable": SUBJECT,
        "legible": True,
        "contemporaneous": datetime.now(timezone.utc).isoformat(),
        "original": True,
        "accurate": True,
        "complete": True,
        "consistent": True,
        "enduring": True,
        "available": True,
    }


@pytest.fixture
def evidence_bundle(valid_oauth3_token, alcoa_fields) -> Dict[str, Any]:
    """A fully-populated evidence bundle dict matching EvidenceBundle schema."""
    bundle_id = _make_sha256(str(uuid.uuid4()))
    prev_bundle_id = _make_sha256("genesis")
    action_id = str(uuid.uuid4())
    return {
        "schema_version": "1.0.0",
        "bundle_id": bundle_id,
        "action_id": action_id,
        "action_type": "create_post",
        "platform": PLATFORM_LINKEDIN,
        "before_snapshot_pzip_hash": _make_sha256("before-html-content"),
        "after_snapshot_pzip_hash": _make_sha256("after-html-content"),
        "diff_hash": _make_sha256("diff-content"),
        "oauth3_token_id": valid_oauth3_token["token_id"],
        "timestamp_iso8601": datetime.now(timezone.utc).isoformat(),
        "sha256_chain_link": prev_bundle_id,
        "signature": _make_sha256("aes-256-gcm-signature-stub"),
        "alcoa_fields": alcoa_fields,
        "rung_achieved": 641,
        "created_by": "test-agent",
    }


@pytest.fixture
def genesis_bundle() -> Dict[str, Any]:
    """A genesis bundle (chain_link = None) to start a chain."""
    bundle_id = _make_sha256("genesis-action-id")
    return {
        "schema_version": "1.0.0",
        "bundle_id": bundle_id,
        "action_id": "genesis",
        "action_type": "genesis",
        "platform": "system",
        "before_snapshot_pzip_hash": _make_sha256("empty"),
        "after_snapshot_pzip_hash": _make_sha256("empty"),
        "diff_hash": _make_sha256("empty"),
        "oauth3_token_id": "genesis",
        "timestamp_iso8601": "2026-01-01T00:00:00+00:00",
        "sha256_chain_link": None,
        "signature": _make_sha256("genesis-signature"),
        "alcoa_fields": {d: True for d in ALCOA_DIMENSIONS},
        "rung_achieved": 641,
        "created_by": "system",
    }


# ---------------------------------------------------------------------------
# Twin sync fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def local_state_bundle() -> Dict[str, Any]:
    """A local state bundle as defined in StateBundleLocal diagram schema."""
    return {
        "state_id": str(uuid.uuid4()),
        "capture_timestamp": datetime.now(timezone.utc).isoformat(),
        "local_wins_version": 1,
        "platforms": [
            {
                "platform": PLATFORM_LINKEDIN,
                "session_active": True,
                "storage_state_hash": _make_sha256("linkedin-cookies"),
                "cookies_count": 5,
                "session_age_days": 2,
            }
        ],
        "fingerprint_hash": _make_sha256("browser-fingerprint"),
        "recipes_version": "1.4.0",
        "evidence_chain_tip": _make_sha256("latest-bundle"),
    }


@pytest.fixture
def encrypted_payload() -> Dict[str, Any]:
    """A mock AES-256-GCM encrypted payload (ciphertext is bytes-like)."""
    plaintext = b"mock-state-bundle-data"
    return {
        "ciphertext": b"\xde\xad\xbe\xef" * 8,
        "nonce_96bit": b"\x00" * 12,
        "auth_tag": b"\xff" * 16,
        "sha256_of_ciphertext": _make_sha256("mock-ciphertext"),
    }


@pytest.fixture
def sync_receipt(local_state_bundle, encrypted_payload) -> Dict[str, Any]:
    """A sync receipt produced after successful cloud sync."""
    return {
        "sync_id": str(uuid.uuid4()),
        "sync_timestamp": datetime.now(timezone.utc).isoformat(),
        "state_id": local_state_bundle["state_id"],
        "cloud_payload_hash_confirmed": encrypted_payload["sha256_of_ciphertext"],
        "conflict_detected": False,
        "local_wins_applied": False,
        "tunnel_cert_pinned": True,
        "rung_achieved": 641,
    }


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm():
    """A mock LLM callable that returns a minimal recipe JSON string."""
    m = MagicMock()
    m.return_value = '{"steps": [], "portals": ["https://www.linkedin.com/"]}'
    return m


@pytest.fixture
def mock_browser():
    """A mock browser / Playwright page object."""
    page = MagicMock()
    page.url = "https://www.linkedin.com/feed/"
    page.title.return_value = "LinkedIn"
    page.content.return_value = (
        "<!DOCTYPE html><html><body>mock content</body></html>"
    )
    return page


@pytest.fixture
def mock_pzip():
    """
    A mock PZip engine.
    compress(data) -> bytes with deterministic output (sha256 of input).
    decompress(compressed) -> original data (identity mock).
    """
    pzip = MagicMock()
    pzip.compress.side_effect = lambda data: (
        hashlib.sha256(data if isinstance(data, bytes) else data.encode()).digest()
    )
    pzip.decompress.side_effect = lambda compressed: b"decompressed-html-content"
    pzip.hash.side_effect = lambda data: _make_sha256(
        data if isinstance(data, str) else data.decode(errors="replace")
    )
    return pzip
