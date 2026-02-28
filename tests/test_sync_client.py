"""Tests for sync_client.py and evidence_upload.py."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src/ to path for imports
_SRC_PATH = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC_PATH))

from sync_client import SyncClient, SyncConfig, SyncError, DEFAULT_API_URL
from evidence_upload import (
    EvidenceCollector,
    UploadManifest,
    EvidenceCollectionError,
    upload_pending_evidence,
)


# ---------------------------------------------------------------------------
# SyncConfig tests
# ---------------------------------------------------------------------------

class TestSyncConfig:
    def test_default_values(self) -> None:
        config = SyncConfig()
        assert config.api_url == DEFAULT_API_URL
        assert config.api_key == ""
        assert config.auto_sync_interval_seconds == 0
        assert config.evidence_auto_upload is False

    def test_from_env_with_api_key(self) -> None:
        with patch.dict(os.environ, {"SOLACE_API_KEY": "test-key-123"}):
            config = SyncConfig.from_env()
            assert config.api_key == "test-key-123"

    def test_from_env_with_custom_url(self) -> None:
        with patch.dict(os.environ, {"SOLACE_API_URL": "https://custom.example.com"}):
            config = SyncConfig.from_env()
            assert config.api_url == "https://custom.example.com"

    def test_from_env_auto_sync(self) -> None:
        with patch.dict(os.environ, {"SOLACE_AUTO_SYNC_INTERVAL": "300"}):
            config = SyncConfig.from_env()
            assert config.auto_sync_interval_seconds == 300

    def test_from_env_evidence_auto_upload(self) -> None:
        with patch.dict(os.environ, {"SOLACE_EVIDENCE_AUTO_UPLOAD": "true"}):
            config = SyncConfig.from_env()
            assert config.evidence_auto_upload is True

    def test_from_env_vault_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_dir = Path(tmpdir)
            key_file = vault_dir / "api_key"
            key_file.write_text("vault-key-456")
            # Clear env so vault file is used
            env = {k: v for k, v in os.environ.items() if k != "SOLACE_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                config = SyncConfig.from_env(vault_dir=vault_dir)
                assert config.api_key == "vault-key-456"


# ---------------------------------------------------------------------------
# SyncClient tests
# ---------------------------------------------------------------------------

class TestSyncClient:
    def test_api_url_strips_trailing_slash(self) -> None:
        config = SyncConfig(api_url="https://example.com/")
        client = SyncClient(config)
        assert client.api_url == "https://example.com"

    def test_not_connected_initially(self) -> None:
        config = SyncConfig()
        client = SyncClient(config)
        assert client.connected is False

    def test_get_status(self) -> None:
        config = SyncConfig()
        client = SyncClient(config)
        status = client.get_status(pending_evidence=3, pending_runs=1)
        assert status.connected is False
        assert status.pending_evidence_count == 3
        assert status.pending_runs_count == 1
        assert status.auto_sync_enabled is False
        assert status.evidence_auto_upload is False

    def test_get_status_auto_sync_enabled(self) -> None:
        config = SyncConfig(auto_sync_interval_seconds=60)
        client = SyncClient(config)
        status = client.get_status()
        assert status.auto_sync_enabled is True


# ---------------------------------------------------------------------------
# UploadManifest tests
# ---------------------------------------------------------------------------

class TestUploadManifest:
    def test_empty_manifest(self) -> None:
        manifest = UploadManifest()
        assert manifest.is_uploaded("abc123") is False

    def test_mark_and_check(self) -> None:
        manifest = UploadManifest()
        manifest.mark_uploaded("abc123")
        assert manifest.is_uploaded("abc123") is True
        assert manifest.is_uploaded("other") is False

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.json"
            manifest = UploadManifest()
            manifest.mark_uploaded("hash1")
            manifest.mark_uploaded("hash2")
            manifest.save(path)

            loaded = UploadManifest.load(path)
            assert loaded.is_uploaded("hash1") is True
            assert loaded.is_uploaded("hash2") is True
            assert loaded.is_uploaded("hash3") is False

    def test_load_missing_file_returns_empty(self) -> None:
        path = Path("/nonexistent/manifest.json")
        manifest = UploadManifest.load(path)
        assert len(manifest.uploaded_hashes) == 0


# ---------------------------------------------------------------------------
# EvidenceCollector tests
# ---------------------------------------------------------------------------

class TestEvidenceCollector:
    def _create_audit_session(
        self, audit_root: Path, session_id: str, entries: list[Dict[str, Any]]
    ) -> None:
        """Helper: write a fake audit.jsonl under the expected directory layout."""
        session_dir = audit_root / "audit" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        audit_file = session_dir / "audit.jsonl"
        lines = [json.dumps(e, sort_keys=True) for e in entries]
        audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_no_audit_dir_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = EvidenceCollector(
                audit_dir=Path(tmpdir) / "nonexistent",
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            pending = collector.collect_pending()
            assert pending == []
            assert collector.pending_count == 0

    def test_collects_pending_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir) / "audit_root"
            self._create_audit_session(
                audit_dir,
                "session-001",
                [{"entry_id": "0", "entry_hash": "abc", "action": "navigate"}],
            )
            self._create_audit_session(
                audit_dir,
                "session-002",
                [{"entry_id": "0", "entry_hash": "def", "action": "click"}],
            )

            collector = EvidenceCollector(
                audit_dir=audit_dir,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            pending = collector.collect_pending()
            assert len(pending) == 2
            assert collector.pending_count == 2

    def test_mark_uploaded_reduces_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir) / "audit_root"
            self._create_audit_session(
                audit_dir,
                "session-001",
                [{"entry_id": "0", "entry_hash": "abc", "action": "navigate"}],
            )

            collector = EvidenceCollector(
                audit_dir=audit_dir,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            pending = collector.collect_pending()
            assert len(pending) == 1

            collector.mark_uploaded(pending[0].bundle_hash)
            pending_after = collector.collect_pending()
            assert len(pending_after) == 0

    def test_screenshots_cataloged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir) / "audit_root"
            self._create_audit_session(
                audit_dir,
                "session-001",
                [{"entry_id": "0", "entry_hash": "abc", "action": "navigate"}],
            )
            # Add a fake screenshot
            ss_dir = audit_dir / "audit" / "session-001" / "screenshots"
            ss_dir.mkdir(parents=True, exist_ok=True)
            (ss_dir / "step_0.png").write_bytes(b"fake-png-data")

            collector = EvidenceCollector(
                audit_dir=audit_dir,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            pending = collector.collect_pending()
            assert len(pending) == 1
            bundle = pending[0].bundle_data
            assert len(bundle["screenshots"]) == 1
            assert bundle["screenshots"][0]["filename"] == "step_0.png"


# ---------------------------------------------------------------------------
# upload_pending_evidence tests
# ---------------------------------------------------------------------------

class TestUploadPendingEvidence:
    def _create_audit_session(
        self, audit_root: Path, session_id: str, entries: list[Dict[str, Any]]
    ) -> None:
        session_dir = audit_root / "audit" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        audit_file = session_dir / "audit.jsonl"
        lines = [json.dumps(e, sort_keys=True) for e in entries]
        audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_nothing_to_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = EvidenceCollector(
                audit_dir=Path(tmpdir) / "empty",
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            mock_client = AsyncMock()
            result = await upload_pending_evidence(mock_client, collector)
            assert result["status"] == "nothing_to_upload"
            assert result["uploaded"] == 0

    @pytest.mark.asyncio
    async def test_successful_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir) / "audit_root"
            self._create_audit_session(
                audit_dir,
                "session-001",
                [{"entry_id": "0", "entry_hash": "abc", "action": "navigate"}],
            )

            collector = EvidenceCollector(
                audit_dir=audit_dir,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            mock_client = AsyncMock()
            mock_client.push_evidence.return_value = {"status": "ok"}

            result = await upload_pending_evidence(mock_client, collector)
            assert result["status"] == "complete"
            assert result["uploaded"] == 1
            assert result["failed"] == 0
            mock_client.push_evidence.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_uploads_fail_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir) / "audit_root"
            self._create_audit_session(
                audit_dir,
                "session-001",
                [{"entry_id": "0", "entry_hash": "abc", "action": "navigate"}],
            )

            collector = EvidenceCollector(
                audit_dir=audit_dir,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            mock_client = AsyncMock()
            mock_client.push_evidence.side_effect = SyncError("network down")

            with pytest.raises(EvidenceCollectionError, match="All 1 evidence uploads failed"):
                await upload_pending_evidence(mock_client, collector)

    @pytest.mark.asyncio
    async def test_partial_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir) / "audit_root"
            self._create_audit_session(
                audit_dir,
                "session-001",
                [{"entry_id": "0", "entry_hash": "abc", "action": "navigate"}],
            )
            self._create_audit_session(
                audit_dir,
                "session-002",
                [{"entry_id": "0", "entry_hash": "def", "action": "click"}],
            )

            collector = EvidenceCollector(
                audit_dir=audit_dir,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            mock_client = AsyncMock()
            # First call succeeds, second fails
            mock_client.push_evidence.side_effect = [
                {"status": "ok"},
                SyncError("timeout"),
            ]

            result = await upload_pending_evidence(mock_client, collector)
            assert result["status"] == "complete"
            assert result["uploaded"] == 1
            assert result["failed"] == 1
            assert len(result["errors"]) == 1
