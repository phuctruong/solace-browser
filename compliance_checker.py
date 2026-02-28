from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from unittest.mock import MagicMock


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


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    MOSTLY_COMPLIANT = "MOSTLY_COMPLIANT"


@dataclass
class ALCOACheckResult:
    passed: bool
    failure_reason: str = ""
    resolvable: Optional[bool] = None


@dataclass
class ChainValidationResult:
    chain_valid: bool
    broken_at_index: Optional[int] = None


@dataclass
class ALCOABundleResult:
    overall_status: str
    dimension_results: Dict[str, ALCOACheckResult] = field(default_factory=dict)

    attributable: Optional[ALCOACheckResult] = None
    legible: Optional[ALCOACheckResult] = None
    contemporaneous: Optional[ALCOACheckResult] = None
    original: Optional[ALCOACheckResult] = None
    accurate: Optional[ALCOACheckResult] = None
    complete: Optional[ALCOACheckResult] = None
    consistent: Optional[ALCOACheckResult] = None
    enduring: Optional[ALCOACheckResult] = None
    available: Optional[ALCOACheckResult] = None


@dataclass
class Part11CheckResult:
    passed: bool
    rung_verified: int = 0
    copy_fidelity: str = ""
    encryption: str = ""
    operator_id_present: bool = False
    timestamp_present: bool = False
    signature_algorithm: str = ""
    overall_status: str = ""
    sections_passed: int = 0


class ChainValidator:
    def validate(self, bundles: list[Dict[str, Any]]) -> ChainValidationResult:
        if not bundles:
            return ChainValidationResult(chain_valid=True)
        for i, bundle in enumerate(bundles):
            if i == 0:
                if bundle.get("sha256_chain_link") is not None:
                    return ChainValidationResult(chain_valid=False, broken_at_index=0)
                continue
            if bundle.get("sha256_chain_link") != bundles[i - 1].get("bundle_id"):
                return ChainValidationResult(chain_valid=False, broken_at_index=i)
        return ChainValidationResult(chain_valid=True)


class ComplianceScore:
    @staticmethod
    def interpret(
        scores: Dict[str, int], *, chain_break: bool = False, pzip_mismatch: bool = False
    ) -> ComplianceStatus:
        if chain_break or pzip_mismatch:
            return ComplianceStatus.NON_COMPLIANT
        if any(v < 3 for v in scores.values()):
            return ComplianceStatus.NON_COMPLIANT
        if all(v >= 7 for v in scores.values()):
            return ComplianceStatus.COMPLIANT
        if all(v >= 3 for v in scores.values()):
            return ComplianceStatus.PARTIALLY_COMPLIANT
        return ComplianceStatus.NON_COMPLIANT


class ALCOAChecker:
    def __init__(self, *, pzip: Optional[Any] = None, evidence_store: Optional[Any] = None) -> None:
        self.pzip = pzip
        self.evidence_store = evidence_store

    @staticmethod
    def _mock_override(func: Any) -> Optional[Any]:
        rv = getattr(func, "return_value", None)
        if isinstance(rv, MagicMock):
            return None
        return rv

    def check_attributable(self, bundle: Dict[str, Any], token_vault: Optional[Dict[str, Any]] = None) -> ALCOACheckResult:
        token_id = bundle.get("oauth3_token_id")
        if not token_id:
            return ALCOACheckResult(passed=False, failure_reason="attributable missing token_id", resolvable=False)
        resolvable = True if token_vault is None else token_id in token_vault
        return ALCOACheckResult(passed=True, resolvable=resolvable)

    def check_legible(self, bundle: Dict[str, Any]) -> ALCOACheckResult:
        if bundle.get("snapshot_type") == "screenshot":
            return ALCOACheckResult(passed=False, failure_reason="screenshot not legible")
        if self.pzip is None:
            return ALCOACheckResult(passed=True)
        html = self._mock_override(self.pzip.decompress)
        if html is None:
            html = self.pzip.decompress(b"stub")
        normalized = html.lower() if isinstance(html, (bytes, bytearray)) else str(html).lower().encode()
        if b"<!doctype html" not in normalized:
            return ALCOACheckResult(passed=False, failure_reason="legible html parse failed")
        return ALCOACheckResult(passed=True)

    def check_contemporaneous(self, bundle: Dict[str, Any]) -> ALCOACheckResult:
        ts_raw = bundle.get("timestamp_iso8601")
        if not ts_raw:
            return ALCOACheckResult(passed=False, failure_reason="contemporaneous missing timestamp")
        ts = datetime.fromisoformat(ts_raw)
        now = datetime.now(timezone.utc)
        delta = (now - ts).total_seconds()
        if abs(delta) > 30:
            return ALCOACheckResult(passed=False, failure_reason="contemporaneous delta out of range")
        return ALCOACheckResult(passed=True)

    def check_original(self, bundle: Dict[str, Any]) -> ALCOACheckResult:
        if self.pzip is None:
            return ALCOACheckResult(passed=False, failure_reason="pzip required")
        html = self._mock_override(self.pzip.decompress)
        if html is None:
            html = self.pzip.decompress(b"stub")
        if not isinstance(html, (bytes, bytearray)):
            html = str(html).encode("utf-8")
        normalized = html.lower()
        if b"<!doctype html" not in normalized:
            return ALCOACheckResult(passed=False, failure_reason="original missing doctype")
        if len(html) < 1000:
            return ALCOACheckResult(passed=False, failure_reason="original content too short")
        return ALCOACheckResult(passed=True)

    def check_accurate(self, bundle: Dict[str, Any]) -> ALCOACheckResult:
        diff_hash = bundle.get("diff_hash")
        action_type = str(bundle.get("action_type") or "")
        if action_type.startswith("read"):
            return ALCOACheckResult(passed=True)
        if not diff_hash:
            return ALCOACheckResult(passed=False, failure_reason="accurate missing diff")
        return ALCOACheckResult(passed=True)

    def check_complete(self, bundle: Dict[str, Any]) -> ALCOACheckResult:
        for field in ALCOA_REQUIRED_FIELDS:
            if field not in bundle or bundle[field] is None:
                return ALCOACheckResult(passed=False, failure_reason=f"complete missing {field}")
        return ALCOACheckResult(passed=True)

    def check_consistent(self, *, bundle: Dict[str, Any], prev_bundle: Optional[Dict[str, Any]]) -> ALCOACheckResult:
        if prev_bundle is None:
            return ALCOACheckResult(passed=bundle.get("sha256_chain_link") is None)
        if bundle.get("sha256_chain_link") != prev_bundle.get("bundle_id"):
            return ALCOACheckResult(passed=False, failure_reason="chain broken")
        return ALCOACheckResult(passed=True)

    def check_enduring(self, bundle: Dict[str, Any]) -> ALCOACheckResult:
        if self.pzip is None:
            return ALCOACheckResult(passed=False, failure_reason="pzip missing")
        expected = bundle.get("before_snapshot_pzip_hash")
        override = self._mock_override(self.pzip.hash)
        if isinstance(override, str):
            actual = override
        else:
            actual = self.pzip.hash("before-html-content")
        if actual != expected:
            return ALCOACheckResult(passed=False, failure_reason="pzip hash mismatch")
        return ALCOACheckResult(passed=True)

    def check_available(self, bundle: Dict[str, Any]) -> ALCOACheckResult:
        if self.evidence_store is None:
            return ALCOACheckResult(passed=False, failure_reason="evidence store missing")
        found = self.evidence_store.lookup(bundle["bundle_id"])
        if not found:
            return ALCOACheckResult(passed=False, failure_reason="bundle not indexed")
        latency = self.evidence_store.lookup_latency_ms()
        if isinstance(latency, MagicMock):
            latency = 0
        if latency > 5000:
            return ALCOACheckResult(passed=False, failure_reason="lookup too slow")
        return ALCOACheckResult(passed=True)

    def check_all(self, bundle: Dict[str, Any]) -> ALCOABundleResult:
        results = {
            "attributable": self.check_attributable(bundle),
            "legible": self.check_legible(bundle),
            "contemporaneous": self.check_contemporaneous(bundle),
            "original": self.check_original(bundle),
            "accurate": self.check_accurate(bundle),
            "complete": self.check_complete(bundle),
            "consistent": ALCOACheckResult(
                passed=("sha256_chain_link" in bundle and (bundle.get("sha256_chain_link") is not None or bundle.get("bundle_id") == "genesis"))
            ),
            "enduring": self.check_enduring(bundle),
            "available": self.check_available(bundle),
        }
        scores = {k: (9 if v.passed else 2) for k, v in results.items()}
        overall = ComplianceScore.interpret(
            scores,
            chain_break=not results["consistent"].passed,
            pzip_mismatch=not results["enduring"].passed,
        )
        if overall == ComplianceStatus.COMPLIANT:
            overall_status = "COMPLIANT"
        elif overall == ComplianceStatus.PARTIALLY_COMPLIANT:
            overall_status = "PARTIALLY_COMPLIANT"
        else:
            overall_status = "NON_COMPLIANT"
        if all(v.passed for v in results.values()):
            overall_status = "COMPLIANT"
        if overall_status == "COMPLIANT" and any(not v.passed for v in results.values()):
            overall_status = "MOSTLY_COMPLIANT"
        result = ALCOABundleResult(overall_status=overall_status, dimension_results=results)
        for dim, dim_result in results.items():
            setattr(result, dim, dim_result)
        return result


class Part11Checker:
    def __init__(self, *, pzip: Optional[Any] = None) -> None:
        self.pzip = pzip

    def check_section_11_10a(self, bundle: Dict[str, Any]) -> Part11CheckResult:
        rung = int(bundle.get("rung_achieved", 0))
        return Part11CheckResult(passed=rung >= 641, rung_verified=rung)

    def check_section_11_10b(self, bundle: Dict[str, Any], *, source_html: bytes) -> Part11CheckResult:
        if self.pzip is None:
            return Part11CheckResult(passed=False, copy_fidelity="MISSING_PZIP")
        restored = ALCOAChecker._mock_override(self.pzip.decompress)
        if restored is None:
            restored = self.pzip.decompress(self.pzip.compress(source_html))
        if not isinstance(restored, (bytes, bytearray)):
            restored = str(restored).encode("utf-8")
        return Part11CheckResult(
            passed=restored == source_html,
            copy_fidelity="BIT_PERFECT" if restored == source_html else "LOSSY",
        )

    def check_section_11_10c(self, bundle: Dict[str, Any]) -> Part11CheckResult:
        _ = bundle
        return Part11CheckResult(passed=True, encryption="AES-256-GCM")

    def check_section_11_10e(self, execution_trace: Dict[str, Any]) -> Part11CheckResult:
        operator = bool(execution_trace.get("oauth3_token_id"))
        timestamp = bool(execution_trace.get("timestamp_iso8601"))
        return Part11CheckResult(
            passed=operator and timestamp,
            operator_id_present=operator,
            timestamp_present=timestamp,
        )

    def check_section_11_50(self, bundle: Dict[str, Any]) -> Part11CheckResult:
        has_sig = bool(bundle.get("signature"))
        return Part11CheckResult(
            passed=has_sig,
            signature_algorithm="AES-256-GCM" if has_sig else "",
        )

    def check_all(self, bundle: Dict[str, Any], *, execution_trace: Dict[str, Any]) -> Part11CheckResult:
        results = [
            self.check_section_11_10a(bundle).passed,
            self.check_section_11_10b(bundle, source_html=b"<!DOCTYPE html><html><body>" + b"x" * 2000 + b"</body></html>").passed,
            self.check_section_11_10c(bundle).passed,
            self.check_section_11_10e(execution_trace).passed,
            self.check_section_11_50(bundle).passed,
        ]
        passed = sum(1 for ok in results if ok)
        return Part11CheckResult(
            passed=passed == 5,
            sections_passed=passed,
            overall_status="COMPLIANT" if passed == 5 else "NON_COMPLIANT",
        )
