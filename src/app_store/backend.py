"""Git-backed app catalog + proposal backends (file or Firestore)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Protocol
from uuid import uuid4

import yaml

from companion.apps import discover_installed_apps


PROPOSAL_ID_RE = re.compile(r"[^a-z0-9\-]+")
VALID_PROPOSAL_STATUSES = {"proposed", "triage", "accepted", "rejected"}


class AppStoreBackendConfigError(RuntimeError):
    """Raised when app-store backend env/config is invalid."""


class AppStoreProposalValidationError(ValueError):
    """Raised when proposal payload fails validation."""


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return payload


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_site(site: str) -> str:
    normalized = site.strip().lower()
    return normalized.replace("https://", "").replace("http://", "").rstrip("/")


def _slugify(value: str) -> str:
    safe = PROPOSAL_ID_RE.sub("-", value.strip().lower())
    safe = safe.strip("-")
    return safe or "proposal"


def _coerce_app_entry(entry: dict[str, Any]) -> dict[str, Any]:
    app_id = str(entry.get("id", "")).strip()
    if not app_id:
        raise ValueError("Catalog entry missing id")
    return {
        "id": app_id,
        "name": str(entry.get("name", app_id)).strip() or app_id,
        "description": str(entry.get("description", "")).strip(),
        "category": str(entry.get("category", "uncategorized")).strip() or "uncategorized",
        "status": str(entry.get("status", "available")).strip() or "available",
        "safety": str(entry.get("safety", "A")).strip() or "A",
        "site": _normalize_site(str(entry.get("site", ""))),
        "type": str(entry.get("type", "standard")).strip() or "standard",
        "scopes": entry.get("scopes", []) if isinstance(entry.get("scopes"), list) else [],
        "source": str(entry.get("source", "official_git")).strip() or "official_git",
    }


@dataclass(frozen=True)
class AppStoreCatalog:
    """Official app-store catalog from git-managed JSON, with manifest fallback."""

    catalog_path: Path
    default_apps_root: Path

    def load_catalog(self) -> dict[str, Any]:
        if self.catalog_path.exists():
            payload = _read_json(self.catalog_path)
            apps = payload.get("apps", [])
            if not isinstance(apps, list):
                raise ValueError("official-store.json must contain an apps[] list")
            normalized = sorted((_coerce_app_entry(entry) for entry in apps), key=lambda x: x["name"].lower())
            return {
                "metadata": {
                    "mode": "git",
                    "catalog_path": str(self.catalog_path),
                    "catalog_sha256": _sha256_file(self.catalog_path),
                    "generated_at": payload.get("generated_at", ""),
                },
                "apps": normalized,
            }

        generated = self._generate_from_manifests()
        manifest_digest = _sha256_bytes(
            json.dumps(generated["apps"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        return {
            "metadata": {
                "mode": "manifest_fallback",
                "catalog_path": str(self.catalog_path),
                "catalog_sha256": manifest_digest,
                "generated_at": generated["generated_at"],
            },
            "apps": generated["apps"],
        }

    def _generate_from_manifests(self) -> dict[str, Any]:
        apps: list[dict[str, Any]] = []
        for record in discover_installed_apps(self.default_apps_root):
            manifest = _read_yaml(record.app_root / "manifest.yaml")
            apps.append(
                _coerce_app_entry(
                    {
                        "id": manifest.get("id", record.app_id),
                        "name": manifest.get("name", record.app_id),
                        "description": manifest.get("description", ""),
                        "category": manifest.get("category", "uncategorized"),
                        "status": manifest.get("status", "available"),
                        "safety": manifest.get("safety", "A"),
                        "site": manifest.get("site", ""),
                        "type": manifest.get("type", "standard"),
                        "scopes": manifest.get("scopes", []),
                        "source": "manifest_fallback",
                    }
                )
            )
        apps.sort(key=lambda item: item["name"].lower())
        return {"generated_at": _now_iso(), "apps": apps}


class AppProposalStore(Protocol):
    """Backend contract for app proposals."""

    def list_proposals(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        ...

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def backend_name(self) -> str:
        ...


def validate_proposal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    site = _normalize_site(str(payload.get("site", "")))
    category = str(payload.get("category", "")).strip().lower()
    submitted_by = str(payload.get("submitted_by", "anonymous")).strip() or "anonymous"

    if not name or len(name) < 3:
        raise AppStoreProposalValidationError("name must be at least 3 characters")
    if not description or len(description) < 10:
        raise AppStoreProposalValidationError("description must be at least 10 characters")
    if not site:
        raise AppStoreProposalValidationError("site is required")
    if not category:
        raise AppStoreProposalValidationError("category is required")

    return {
        "name": name,
        "description": description,
        "site": site,
        "category": category,
        "submitted_by": submitted_by,
        "links": payload.get("links", []) if isinstance(payload.get("links"), list) else [],
    }


class FileAppProposalStore:
    """Local JSONL proposal store for development and git-driven review."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path.resolve()

    def backend_name(self) -> str:
        return "file"

    def list_proposals(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1:
            limit = 1
        if not self._file_path.exists():
            return []
        proposals: list[dict[str, Any]] = []
        for line in self._file_path.read_text(encoding="utf-8").splitlines():
            striped = line.strip()
            if not striped:
                continue
            record = json.loads(striped)
            if not isinstance(record, dict):
                continue
            record_status = str(record.get("status", "proposed"))
            if status and record_status != status:
                continue
            proposals.append(record)
        proposals.sort(key=lambda item: str(item.get("submitted_at", "")), reverse=True)
        return proposals[:limit]

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        validated = validate_proposal_payload(payload)
        proposal_id = f"prop-{_slugify(validated['name'])}-{uuid4().hex[:8]}"
        proposal = {
            "proposal_id": proposal_id,
            **validated,
            "status": "proposed",
            "source": "local_file",
            "submitted_at": _now_iso(),
        }
        record_bytes = json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode("utf-8")
        proposal["record_sha256"] = _sha256_bytes(record_bytes)

        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(proposal, sort_keys=True)
        with self._file_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return proposal


class FirestoreAppProposalStore:
    """Firestore-backed proposal store for production user submissions."""

    def __init__(self, *, collection: str, project_id: str | None = None) -> None:
        try:
            from google.cloud import firestore  # type: ignore
        except ImportError as exc:
            raise AppStoreBackendConfigError(
                "Firestore backend selected but google-cloud-firestore is not installed"
            ) from exc

        self._firestore = firestore
        self._collection = collection
        self._client = firestore.Client(project=project_id) if project_id else firestore.Client()

    def backend_name(self) -> str:
        return "firestore"

    def list_proposals(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = self._client.collection(self._collection).order_by("submitted_at", direction=self._firestore.Query.DESCENDING)
        if status:
            query = query.where("status", "==", status)
        docs = query.limit(limit).stream()
        items: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict()
            if not isinstance(data, dict):
                continue
            items.append(data)
        return items

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        validated = validate_proposal_payload(payload)
        proposal_id = f"prop-{_slugify(validated['name'])}-{uuid4().hex[:8]}"
        proposal = {
            "proposal_id": proposal_id,
            **validated,
            "status": "proposed",
            "source": "firestore",
            "submitted_at": _now_iso(),
        }
        record_bytes = json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode("utf-8")
        proposal["record_sha256"] = _sha256_bytes(record_bytes)

        self._client.collection(self._collection).document(proposal_id).set(proposal)
        return proposal


def create_proposal_store_from_env(
    *,
    repo_root: Path,
    solace_home: Path,
) -> AppProposalStore:
    backend = os.getenv("SOLACE_APP_STORE_PROPOSALS_BACKEND", "file").strip().lower()

    if backend == "file":
        default_path = repo_root / "data" / "default" / "app-store" / "proposed-apps-dev.jsonl"
        file_path = Path(os.getenv("SOLACE_APP_STORE_PROPOSALS_FILE", str(default_path))).expanduser().resolve()
        return FileAppProposalStore(file_path)

    if backend == "firestore":
        collection = os.getenv("SOLACE_APP_STORE_FIRESTORE_COLLECTION", "app_store_proposals").strip()
        project_id = os.getenv("SOLACE_APP_STORE_FIRESTORE_PROJECT", "").strip() or None
        return FirestoreAppProposalStore(collection=collection, project_id=project_id)

    if backend == "disabled":
        raise AppStoreBackendConfigError("Proposal backend is disabled")

    raise AppStoreBackendConfigError(
        f"Unsupported SOLACE_APP_STORE_PROPOSALS_BACKEND={backend!r}. Use file, firestore, or disabled."
    )

