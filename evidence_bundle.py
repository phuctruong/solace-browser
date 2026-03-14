# Diagram: 16-evidence-chain
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
import uuid
from typing import Any, Optional


RUNG_ACHIEVED = 274177
SCHEMA_VERSION = "1.0"
PLATFORM = "solace-browser"
GENESIS_CHAIN_SEED = "GENESIS"
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
ALCOA_REQUIRED_FIELDS = [
    "schema_version",
    "bundle_id",
    "action_id",
    "action_type",
    "platform",
    "before_snapshot_hash",
    "after_snapshot_hash",
    "diff_hash",
    "oauth3_token_id",
    "timestamp_iso8601",
    "sha256_chain_link",
    "alcoa_fields",
    "rung_achieved",
]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ISO8601_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class ALCOAError(Exception):
    """Raised when an ALCOA+ bundle cannot be generated safely."""


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"


@dataclass(frozen=True)
class ALCOACheckResult:
    passed: bool
    failure_reason: str = ""


@dataclass(frozen=True)
class ChainValidationResult:
    chain_valid: bool
    broken_at_index: Optional[int] = None


@dataclass(frozen=True)
class FrozenALCOABundle:
    schema_version: str
    bundle_id: str
    action_id: str
    action_type: str
    platform: str
    before_snapshot_hash: str
    after_snapshot_hash: str
    diff_hash: str
    oauth3_token_id: str
    timestamp_iso8601: str
    sha256_chain_link: str
    alcoa_fields: dict[str, dict[str, Any]]
    rung_achieved: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_hash(value: Any) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if _SHA256_RE.fullmatch(lowered):
            return lowered
        if lowered:
            return _sha256_hex(lowered)
    if value is None:
        return ""
    return _sha256_hex(_canonical_json(value))


def _required_fields_present(bundle: dict[str, Any]) -> bool:
    for field in ALCOA_REQUIRED_FIELDS:
        value = bundle.get(field)
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
    alcoa_fields = bundle.get("alcoa_fields")
    if not isinstance(alcoa_fields, dict):
        return False
    for dimension in ALCOA_DIMENSIONS:
        dimension_payload = alcoa_fields.get(dimension)
        if not isinstance(dimension_payload, dict):
            return False
        if "passed" not in dimension_payload:
            return False
    return True


class ALCOABundle:
    """ALCOA+ compliant evidence record for FDA Part 11."""

    @staticmethod
    def _bundle_payload_for_hash(bundle: dict[str, Any]) -> dict[str, Any]:
        payload = dict(bundle)
        payload.pop("sha256_chain_link", None)
        return payload

    @staticmethod
    def bundle_sha256(bundle: dict[str, Any]) -> str:
        return _sha256_hex(_canonical_json(ALCOABundle._bundle_payload_for_hash(bundle)))

    @staticmethod
    def create_bundle(
        action_type: Any,
        before_state: Any,
        after_state: Any,
        oauth3_token_id: Any,
        user_id: Any,
        *,
        previous_bundle_sha256: Optional[str] = None,
    ) -> dict[str, Any]:
        timestamp_iso8601 = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        before_snapshot_hash = _normalize_hash(before_state)
        after_snapshot_hash = _normalize_hash(after_state)
        normalized_action_type = action_type.strip() if isinstance(action_type, str) else ""
        normalized_token_id = oauth3_token_id.strip() if isinstance(oauth3_token_id, str) else ""
        normalized_user_id = user_id.strip() if isinstance(user_id, str) else ""
        diff_hash = _sha256_hex(
            _canonical_json(
                {
                    "action_type": normalized_action_type,
                    "before_snapshot_hash": before_snapshot_hash,
                    "after_snapshot_hash": after_snapshot_hash,
                }
            )
        )
        previous_hash = ""
        if previous_bundle_sha256:
            lowered_previous_hash = previous_bundle_sha256.strip().lower()
            if not _SHA256_RE.fullmatch(lowered_previous_hash):
                raise ALCOAError("previous bundle sha256 must be a 64-character hex digest")
            previous_hash = lowered_previous_hash
        alcoa_fields = {
            "attributable": {
                "passed": bool(normalized_user_id) and bool(normalized_token_id),
                "user_id": normalized_user_id,
                "oauth3_token_id": normalized_token_id,
            },
            "legible": {"passed": True, "representation": "sha256-json-hashes"},
            "contemporaneous": {"passed": True, "timestamp_iso8601": timestamp_iso8601},
            "original": {
                "passed": bool(before_snapshot_hash) and bool(after_snapshot_hash),
                "before_snapshot_hash": before_snapshot_hash,
                "after_snapshot_hash": after_snapshot_hash,
            },
            "accurate": {"passed": bool(diff_hash), "diff_hash": diff_hash},
            "complete": {"passed": False},
            "consistent": {"passed": True, "previous_bundle_sha256": previous_hash or GENESIS_CHAIN_SEED},
            "enduring": {"passed": True, "storage_class": "append-only-jsonl"},
            "available": {"passed": True, "platform": PLATFORM},
        }
        bundle_payload = FrozenALCOABundle(
            schema_version=SCHEMA_VERSION,
            bundle_id=str(uuid.uuid4()),
            action_id=str(uuid.uuid4()),
            action_type=normalized_action_type,
            platform=PLATFORM,
            before_snapshot_hash=before_snapshot_hash,
            after_snapshot_hash=after_snapshot_hash,
            diff_hash=diff_hash,
            oauth3_token_id=normalized_token_id,
            timestamp_iso8601=timestamp_iso8601,
            sha256_chain_link="",
            alcoa_fields=alcoa_fields,
            rung_achieved=RUNG_ACHIEVED,
        ).to_dict()
        bundle_payload["alcoa_fields"]["complete"]["passed"] = _required_fields_present(
            {**bundle_payload, "sha256_chain_link": "pending-chain-link"}
        )
        current_bundle_sha256 = ALCOABundle.bundle_sha256(bundle_payload)
        chain_seed = previous_hash or GENESIS_CHAIN_SEED
        final_bundle = FrozenALCOABundle(
            schema_version=SCHEMA_VERSION,
            bundle_id=bundle_payload["bundle_id"],
            action_id=bundle_payload["action_id"],
            action_type=normalized_action_type,
            platform=PLATFORM,
            before_snapshot_hash=before_snapshot_hash,
            after_snapshot_hash=after_snapshot_hash,
            diff_hash=diff_hash,
            oauth3_token_id=normalized_token_id,
            timestamp_iso8601=timestamp_iso8601,
            sha256_chain_link=_sha256_hex(f"{chain_seed}{current_bundle_sha256}"),
            alcoa_fields=bundle_payload["alcoa_fields"],
            rung_achieved=RUNG_ACHIEVED,
        )
        return final_bundle.to_dict()

    @staticmethod
    def validate_chain(bundles: list[dict[str, Any]]) -> ChainValidationResult:
        previous_bundle_sha256 = ""
        for index, bundle in enumerate(bundles):
            current_bundle_sha256 = ALCOABundle.bundle_sha256(bundle)
            chain_seed = previous_bundle_sha256 or GENESIS_CHAIN_SEED
            expected_chain_link = _sha256_hex(f"{chain_seed}{current_bundle_sha256}")
            actual_chain_link = str(bundle.get("sha256_chain_link") or "").lower()
            if actual_chain_link != expected_chain_link:
                return ChainValidationResult(chain_valid=False, broken_at_index=index)
            previous_bundle_sha256 = current_bundle_sha256
        return ChainValidationResult(chain_valid=True, broken_at_index=None)

    @staticmethod
    def verify_chain(bundles: list[dict[str, Any]]) -> bool:
        return ALCOABundle.validate_chain(bundles).chain_valid

    @staticmethod
    def check_compliance(bundle: dict[str, Any]) -> ComplianceStatus:
        if not isinstance(bundle, dict):
            return ComplianceStatus.NON_COMPLIANT
        if not _required_fields_present(bundle):
            return ComplianceStatus.NON_COMPLIANT
        if bundle.get("schema_version") != SCHEMA_VERSION:
            return ComplianceStatus.NON_COMPLIANT
        if bundle.get("platform") != PLATFORM:
            return ComplianceStatus.NON_COMPLIANT
        if bundle.get("rung_achieved") != RUNG_ACHIEVED:
            return ComplianceStatus.NON_COMPLIANT
        if not _ISO8601_UTC_RE.fullmatch(str(bundle.get("timestamp_iso8601", ""))):
            return ComplianceStatus.NON_COMPLIANT
        for field in ("before_snapshot_hash", "after_snapshot_hash", "diff_hash", "sha256_chain_link"):
            if not _SHA256_RE.fullmatch(str(bundle.get(field, "")).lower()):
                return ComplianceStatus.NON_COMPLIANT
        alcoa_fields = bundle.get("alcoa_fields", {})
        passed_dimensions = 0
        for dimension in ALCOA_DIMENSIONS:
            dimension_payload = alcoa_fields.get(dimension)
            if not isinstance(dimension_payload, dict):
                return ComplianceStatus.NON_COMPLIANT
            if not isinstance(dimension_payload.get("passed"), bool):
                return ComplianceStatus.NON_COMPLIANT
            if dimension_payload.get("passed"):
                passed_dimensions += 1
        if passed_dimensions == len(ALCOA_DIMENSIONS):
            return ComplianceStatus.COMPLIANT
        if passed_dimensions > 0:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        return ComplianceStatus.NON_COMPLIANT
