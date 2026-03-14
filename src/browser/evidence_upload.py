# Diagram: 16-evidence-chain
"""
evidence_upload.py — Evidence Bundle Collector and Uploader

Collects evidence from the Part 11 audit directory (~/.solace/audit/),
packages screenshots + DOM snapshots + action logs into a bundle,
and uploads via SyncClient.

Tracks what has been uploaded to avoid re-uploading (upload manifest).

NO FALLBACKS. If upload fails, the error propagates with full context.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("solace-browser.evidence-upload")

DEFAULT_AUDIT_DIR = Path("~/.solace/audit").expanduser()
DEFAULT_MANIFEST_PATH = Path("~/.solace/sync/upload_manifest.json").expanduser()


class EvidenceCollectionError(RuntimeError):
    """Raised when evidence collection encounters an unrecoverable problem."""


@dataclass(frozen=True)
class EvidenceBundleItem:
    """A single piece of evidence ready for upload."""
    session_id: str
    bundle_path: Path
    bundle_hash: str
    bundle_data: Dict[str, Any]


@dataclass
class UploadManifest:
    """Tracks which evidence bundles have already been uploaded.

    Persisted to disk as JSON. Keyed by bundle_hash to guarantee
    idempotent uploads (never re-upload the same bundle).
    """
    uploaded_hashes: Dict[str, str] = field(default_factory=dict)
    # Maps bundle_hash -> ISO 8601 timestamp of upload

    @classmethod
    def load(cls, path: Path) -> "UploadManifest":
        """Load manifest from disk. Returns empty manifest if file missing."""
        if not path.exists():
            return cls()
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return cls(uploaded_hashes=dict(data.get("uploaded_hashes", {})))

    def save(self, path: Path) -> None:
        """Persist manifest to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"uploaded_hashes": self.uploaded_hashes}
        path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    def is_uploaded(self, bundle_hash: str) -> bool:
        return bundle_hash in self.uploaded_hashes

    def mark_uploaded(self, bundle_hash: str) -> None:
        self.uploaded_hashes[bundle_hash] = datetime.now(timezone.utc).isoformat()


class EvidenceCollector:
    """Collects evidence bundles from the Part 11 audit directory.

    Evidence layout on disk (created by audit/chain.py):
        {audit_dir}/audit/{session_id}/audit.jsonl

    Additional artifacts (screenshots, DOM snapshots) are stored in:
        {audit_dir}/audit/{session_id}/screenshots/
        {audit_dir}/audit/{session_id}/snapshots/
    """

    def __init__(
        self,
        audit_dir: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
    ) -> None:
        self._audit_dir = audit_dir or DEFAULT_AUDIT_DIR
        self._manifest_path = manifest_path or DEFAULT_MANIFEST_PATH
        self._manifest = UploadManifest.load(self._manifest_path)

    @property
    def audit_dir(self) -> Path:
        return self._audit_dir

    @property
    def pending_count(self) -> int:
        """Count of evidence bundles not yet uploaded."""
        items = self._scan_bundles()
        return sum(
            1 for item in items
            if not self._manifest.is_uploaded(item.bundle_hash)
        )

    def collect_pending(self) -> List[EvidenceBundleItem]:
        """Scan audit directory and return bundles not yet uploaded.

        Returns:
            List of EvidenceBundleItem that have not been uploaded.

        Raises:
            EvidenceCollectionError: If audit directory is inaccessible.
        """
        all_bundles = self._scan_bundles()
        pending = [
            item for item in all_bundles
            if not self._manifest.is_uploaded(item.bundle_hash)
        ]
        logger.info(
            "Evidence scan: %d total, %d pending upload",
            len(all_bundles),
            len(pending),
        )
        return pending

    def mark_uploaded(self, bundle_hash: str) -> None:
        """Mark a bundle as uploaded and persist the manifest."""
        self._manifest.mark_uploaded(bundle_hash)
        self._manifest.save(self._manifest_path)

    def _scan_bundles(self) -> List[EvidenceBundleItem]:
        """Walk the audit directory and discover all evidence bundles.

        Each session directory may contain:
            - audit.jsonl (audit chain entries)
            - screenshots/ (PNG files)
            - snapshots/ (JSON DOM snapshots)

        We package each session's audit.jsonl as a bundle, attaching
        references to screenshots and snapshots found alongside it.
        """
        audit_root = self._audit_dir / "audit"
        if not audit_root.exists():
            return []

        bundles: List[EvidenceBundleItem] = []

        for session_dir in sorted(audit_root.iterdir()):
            if not session_dir.is_dir():
                continue

            audit_file = session_dir / "audit.jsonl"
            if not audit_file.exists():
                continue

            session_id = session_dir.name
            bundle_data = self._build_bundle(session_id, session_dir, audit_file)
            # Hash only stable content (exclude collected_at which changes per scan)
            stable_content = {
                "session_id": bundle_data["session_id"],
                "entries": bundle_data["entries"],
                "screenshots": bundle_data["screenshots"],
                "dom_snapshots": bundle_data["dom_snapshots"],
                "chain_tip_hash": bundle_data["chain_tip_hash"],
            }
            bundle_hash = hashlib.sha256(
                json.dumps(stable_content, sort_keys=True).encode("utf-8")
            ).hexdigest()

            bundles.append(EvidenceBundleItem(
                session_id=session_id,
                bundle_path=audit_file,
                bundle_hash=bundle_hash,
                bundle_data=bundle_data,
            ))

        return bundles

    def _build_bundle(
        self,
        session_id: str,
        session_dir: Path,
        audit_file: Path,
    ) -> Dict[str, Any]:
        """Build an evidence bundle dict from a session directory.

        Reads the audit chain entries and catalogs any screenshots/snapshots.
        """
        # Read audit chain entries
        entries: List[Dict[str, Any]] = []
        for line in audit_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                entries.append(json.loads(line))

        # Catalog screenshots
        screenshots: List[Dict[str, str]] = []
        screenshots_dir = session_dir / "screenshots"
        if screenshots_dir.exists():
            for img_path in sorted(screenshots_dir.iterdir()):
                if img_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    file_hash = hashlib.sha256(
                        img_path.read_bytes()
                    ).hexdigest()
                    screenshots.append({
                        "filename": img_path.name,
                        "hash": file_hash,
                        "size_bytes": img_path.stat().st_size,
                    })

        # Catalog DOM snapshots
        dom_snapshots: List[Dict[str, str]] = []
        snapshots_dir = session_dir / "snapshots"
        if snapshots_dir.exists():
            for snap_path in sorted(snapshots_dir.iterdir()):
                if snap_path.suffix.lower() == ".json":
                    file_hash = hashlib.sha256(
                        snap_path.read_bytes()
                    ).hexdigest()
                    dom_snapshots.append({
                        "filename": snap_path.name,
                        "hash": file_hash,
                        "size_bytes": snap_path.stat().st_size,
                    })

        # Compute chain tip hash
        chain_tip = "0" * 64
        if entries:
            last_entry = entries[-1]
            chain_tip = last_entry.get("entry_hash", chain_tip)

        return {
            "schema_version": "1.0.0",
            "session_id": session_id,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "entry_count": len(entries),
            "entries": entries,
            "screenshots": screenshots,
            "dom_snapshots": dom_snapshots,
            "chain_tip_hash": chain_tip,
        }


async def upload_pending_evidence(
    sync_client: Any,
    collector: EvidenceCollector,
) -> Dict[str, Any]:
    """Upload all pending evidence bundles via the sync client.

    Args:
        sync_client: A SyncClient instance (from sync_client.py).
        collector: An EvidenceCollector instance.

    Returns:
        Summary dict with counts and any errors.

    Raises:
        No silent swallowing. Individual upload errors are collected
        and returned in the result dict. If ALL uploads fail, raises
        EvidenceCollectionError.
    """
    pending = collector.collect_pending()
    if not pending:
        return {
            "status": "nothing_to_upload",
            "uploaded": 0,
            "failed": 0,
            "pending_remaining": 0,
        }

    uploaded = 0
    failed = 0
    errors: List[Dict[str, str]] = []

    for item in pending:
        try:
            await sync_client.push_evidence(
                run_id=item.session_id,
                evidence_bundle=item.bundle_data,
            )
            collector.mark_uploaded(item.bundle_hash)
            uploaded += 1
            logger.info(
                "Uploaded evidence for session %s (hash=%s)",
                item.session_id,
                item.bundle_hash[:16],
            )
        except (OSError, ConnectionError, ValueError, RuntimeError) as exc:
            failed += 1
            error_msg = f"session={item.session_id}: {exc}"
            logger.error("Evidence upload failed: %s", error_msg)
            errors.append({
                "session_id": item.session_id,
                "bundle_hash": item.bundle_hash,
                "error": str(exc),
            })

    if uploaded == 0 and failed > 0:
        raise EvidenceCollectionError(
            f"All {failed} evidence uploads failed. Errors: {errors}"
        )

    return {
        "status": "complete",
        "uploaded": uploaded,
        "failed": failed,
        "errors": errors,
        "pending_remaining": collector.pending_count,
    }
