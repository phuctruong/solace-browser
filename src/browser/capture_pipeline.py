# Diagram: 01-triangle-architecture
"""
capture_pipeline.py — PZip Capture Pipeline for Solace Browser

Captures page content on every load event for evidence + compression.

Two modes based on auth status:
- Guest: HTML only (local, no sync, no screenshots)
- Logged-in: HTML + assets + screenshot metadata + Mermaid snapshot

Storage: ~/.solace/history/{domain}/{timestamp}_{url_slug}.ripple.json + .ripple.pz

RTC (Round-Trip Check): compress -> decompress -> compare SHA-256 hashes.
If sha256(reconstructed) != sha256(original), the ripple is NOT stored.

Cross-ref: Diagram 10 (capture-pipeline), Paper 05 (PZip Stillwater),
           Paper 06 (Part 11 Evidence)

Invariants:
  1. ALL computation is client-side (zero cloud compute)
  2. 100% RTC must pass before ripple is stored
  3. Domain exclusions enforced before capture (no localhost, no chrome://)
  4. Fallback Ban: PZip ONLY, no zlib fallback, no silent degradation

Rung: 641
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import re
import sys
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

logger = logging.getLogger("solace-browser.capture")

# ---------------------------------------------------------------------------
# PZip integration (REQUIRED — Fallback Ban: no zlib fallback)
# C++ bridge must be compiled for capture to work.
# ---------------------------------------------------------------------------

PZIP_AVAILABLE = False
pzip_compress = None  # Set by _try_pzip_import() or mocked in tests
pzip_decompress = None  # Set by _try_pzip_import() or mocked in tests


def _try_pzip_import() -> bool:
    """Try importing PZip and verify the C++ bridge works with a smoke test."""
    global pzip_compress, pzip_decompress  # noqa: PLW0603
    try:
        from pzip.pipeline import pzip_compress as _pc, pzip_decompress as _pd
        # Smoke test: compress a tiny payload to verify C++ bridge is compiled
        _test_data = b"<html>smoke</html>"
        _compressed = _pc(_test_data, filename="smoke.html")
        _restored = _pd(_compressed)
        if _restored != _test_data:
            return False
        pzip_compress = _pc
        pzip_decompress = _pd
        return True
    except (ImportError, ModuleNotFoundError, OSError, RuntimeError, TypeError, ValueError):
        return False

# Try installed pzip first
PZIP_AVAILABLE = _try_pzip_import()

# Try project path as fallback
if not PZIP_AVAILABLE:
    _pzip_project = Path("/home/phuc/projects/pzip")
    if _pzip_project.exists() and str(_pzip_project) not in sys.path:
        sys.path.insert(0, str(_pzip_project))
    PZIP_AVAILABLE = _try_pzip_import()

if not PZIP_AVAILABLE:
    logger.warning(
        "PZip C++ bridge NOT compiled — capture pipeline DISABLED. "
        "Compile: cd /home/phuc/projects/pzip && make"
    )

# ---------------------------------------------------------------------------
# Structural extractor (optional — extracts page skeleton as sidecar)
# ---------------------------------------------------------------------------

STRUCTURE_AVAILABLE = False
try:
    from structural_extractor import strip_to_structure
    STRUCTURE_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Errors — specific, never generic (Fallback Ban)
# ---------------------------------------------------------------------------

class CaptureError(Exception):
    """Base error for capture pipeline operations."""


class DomainExcludedError(CaptureError):
    """Raised when attempting to capture an excluded domain."""


class RTCVerificationError(CaptureError):
    """Raised when round-trip check fails (compressed != original)."""


class PZipUnavailableError(CaptureError):
    """Raised when PZip C++ bridge is not compiled.

    Fallback Ban: no silent degradation to zlib.
    Alert user to compile the C++ bridge.
    """


class CaptureNotFoundError(CaptureError):
    """Raised when a capture_id cannot be found in storage."""


# ---------------------------------------------------------------------------
# Domain exclusion patterns
# ---------------------------------------------------------------------------

_EXCLUDED_SCHEMES = frozenset({"chrome", "about", "data", "file"})

_EXCLUDED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0"})


def _is_private_ip(host: str) -> bool:
    """Check if a host string is a private/reserved IP address.

    Covers: 192.168.*, 10.*, 172.16-31.*, and other reserved ranges.

    Args:
        host: Hostname or IP address string.

    Returns:
        True if the host is a private/reserved IP address.
    """
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_private or addr.is_reserved or addr.is_loopback
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# URL slug generation
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-zA-Z0-9_-]")
_MULTI_DASH_RE = re.compile(r"-{2,}")


def _url_to_slug(url: str, max_length: int = 80) -> str:
    """Convert a URL path to a safe filename slug.

    Examples:
        "https://mail.google.com/inbox" -> "inbox"
        "https://github.com/org/repo/issues/42" -> "org-repo-issues-42"
        "https://example.com/" -> "root"
        "https://example.com/path?q=hello&p=1" -> "path"

    Args:
        url: Full URL string.
        max_length: Maximum slug length (truncated, not errored).

    Returns:
        Safe filename slug string. Never empty (falls back to "root").
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "root"

    # Replace path separators with dashes
    slug = path.replace("/", "-")
    # Replace unsafe characters
    slug = _SLUG_RE.sub("-", slug)
    # Collapse multiple dashes
    slug = _MULTI_DASH_RE.sub("-", slug)
    # Strip leading/trailing dashes
    slug = slug.strip("-")

    if not slug:
        return "root"

    return slug[:max_length]


# ---------------------------------------------------------------------------
# CapturePipeline
# ---------------------------------------------------------------------------

class CapturePipeline:
    """Captures page content on every load event for evidence + compression.

    Two modes based on auth status:
    - Guest: HTML only (local, no sync, no screenshots)
    - Logged-in: HTML + assets + screenshot metadata + Mermaid snapshot

    Storage: ~/.solace/history/{domain}/{timestamp}_{url_slug}.ripple.json
             ~/.solace/history/{domain}/{timestamp}_{url_slug}.ripple.pz

    Design rules (Fallback Ban):
    - PZip is the ONLY compression engine. No zlib fallback.
    - RTC must pass before storage (no storing invalid ripples)
    - Domain exclusion checked before any I/O
    - No broad except blocks
    - No silent fallback on compression failure
    - If PZip C++ bridge not compiled: raise PZipUnavailableError
    """

    def __init__(
        self,
        solace_home: Path | None = None,
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        """Initialize the capture pipeline.

        Args:
            solace_home: Base directory for capture storage.
                         Default: ~/.solace
            now_fn: Optional callable returning current UTC datetime (for testing).
        """
        self._solace_home = Path(solace_home or "~/.solace").expanduser().resolve()
        self._history_root = self._solace_home / "history"
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def capture(
        self,
        url: str,
        html_content: str,
        *,
        logged_in: bool = False,
        assets: list[dict[str, Any]] | None = None,
        screenshot_path: Path | None = None,
        session_id: str | None = None,
        skip_if_unchanged: bool = True,
    ) -> dict[str, Any]:
        """Capture a page load event.

        Produces up to three artifacts per page visit:
        1. .ripple.pz — PZip-compressed HTML (Prime Mermaid ripple)
        2. .ripple.json — manifest metadata
        3. .structure.json — structural extraction (Prime Wiki sitemap)

        Compression: PZip ONLY (C++ accelerated). No zlib fallback (Fallback Ban).
        Dedup: skips capture if HTML unchanged since last visit.

        Args:
            url: The page URL.
            html_content: The DOM HTML content.
            logged_in: Whether user is authenticated.
            assets: List of {url, type, size} for page assets (logged-in only).
            screenshot_path: Path to screenshot file (logged-in only).
            session_id: Browser session ID for evidence linking.
            skip_if_unchanged: If True, skip capture when HTML hash matches
                              the most recent capture for this URL.

        Returns:
            {
                capture_id, domain, path, size_bytes, html_hash,
                compressed, compression_ratio, compression_engine,
                mode, rtc_verified, structure_extracted,
                skipped (optional), skip_reason (optional),
            }

        Raises:
            DomainExcludedError: If the URL's domain is excluded.
            PZipUnavailableError: If PZip C++ bridge is not compiled.
            RTCVerificationError: If RTC fails after compression.
        """
        if self.check_domain_exclusion(url):
            raise DomainExcludedError(
                f"Domain excluded from capture: {url}"
            )

        capture_id = f"cap-{uuid.uuid4().hex[:12]}"
        now = self._now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        timestamp_iso = now.isoformat()

        parsed = urlparse(url)
        domain = parsed.hostname or "unknown"
        slug = _url_to_slug(url)
        mode = "authenticated" if logged_in else "guest"

        # Compute HTML hash
        html_bytes = html_content.encode("utf-8")
        html_hash = hashlib.sha256(html_bytes).hexdigest()
        html_size = len(html_bytes)

        # Dedup check: skip if HTML is unchanged since last capture
        if skip_if_unchanged:
            latest = self.find_latest_capture(url)
            if latest is not None and latest.get("html_hash") == html_hash:
                return {
                    "capture_id": latest["capture_id"],
                    "domain": domain,
                    "path": latest.get("manifest_path", ""),
                    "size_bytes": latest.get("html_size", html_size),
                    "html_hash": html_hash,
                    "compressed": True,
                    "compression_ratio": latest.get("compression_ratio", 0.0),
                    "compression_engine": latest.get("compression_engine", "pzip"),
                    "mode": mode,
                    "rtc_verified": True,
                    "structure_extracted": latest.get("structure_path") is not None,
                    "skipped": True,
                    "skip_reason": "unchanged",
                }

        # PZip compression — REQUIRED. No zlib fallback (Fallback Ban).
        if not PZIP_AVAILABLE:
            raise PZipUnavailableError(
                "PZip C++ bridge not compiled. Cannot capture without PZip. "
                "Compile the C++ bridge: cd /home/phuc/projects/pzip && make"
            )
        compression_engine = "pzip"
        compressed_data = self.compress_pzip(html_content)
        compressed_size = len(compressed_data)

        # RTC verification (mandatory — Invariant #2)
        if not self.verify_rtc(html_content, compressed_data):
            raise RTCVerificationError(
                f"Round-trip check failed for {url}. "
                f"Compressed data does not decompress to original HTML. "
                f"html_hash={html_hash[:16]}..., size={html_size}"
            )

        # Compute compression ratio
        if compressed_size > 0:
            compression_ratio = round(html_size / compressed_size, 2)
        else:
            compression_ratio = 0.0

        # Build file paths
        file_base = f"{timestamp_str}_{slug}"
        domain_dir = self._history_root / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = domain_dir / f"{file_base}.ripple.json"
        data_path = domain_dir / f"{file_base}.ripple.pz"

        # Extract page structure (Prime Wiki sitemap)
        structure_data: dict[str, Any] | None = None
        structure_path_str: str | None = None
        if STRUCTURE_AVAILABLE:
            try:
                structure_data = strip_to_structure(html_content)
                structure_path = domain_dir / f"{file_base}.structure.json"
                structure_path.write_text(
                    json.dumps(structure_data, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                structure_path_str = str(structure_path)
            except (ValueError, TypeError, OSError) as exc:
                logger.warning("Structure extraction failed for %s: %s", url, exc)

        # Build manifest
        manifest: dict[str, Any] = {
            "capture_id": capture_id,
            "url": url,
            "domain": domain,
            "timestamp": timestamp_iso,
            "mode": mode,
            "html_hash": html_hash,
            "html_size": html_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio,
            "compression_engine": compression_engine,
            "rtc_verified": True,
            "structure_path": structure_path_str,
            "assets": assets if (logged_in and assets is not None) else [],
            "screenshot_path": str(screenshot_path) if (logged_in and screenshot_path is not None) else None,
            "session_id": session_id,
        }

        # Write manifest
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # Write compressed data
        data_path.write_bytes(compressed_data)

        return {
            "capture_id": capture_id,
            "domain": domain,
            "path": str(manifest_path),
            "size_bytes": html_size,
            "html_hash": html_hash,
            "compressed": True,
            "compression_ratio": compression_ratio,
            "compression_engine": compression_engine,
            "mode": mode,
            "rtc_verified": True,
            "structure_extracted": structure_data is not None,
        }

    def compress_pzip(self, html_content: str) -> bytes:
        """Compress HTML content using PZip (C++ accelerated).

        Returns PZ01 container bytes with SHA-256 seal.
        PZip is the ONLY compression engine. No zlib fallback.

        Raises:
            PZipUnavailableError: If PZip C++ bridge is not compiled.
        """
        if not PZIP_AVAILABLE:
            raise PZipUnavailableError(
                "PZip C++ bridge not compiled. "
                "Compile: cd /home/phuc/projects/pzip && make"
            )
        return pzip_compress(html_content.encode("utf-8"), filename="page.html")

    def decompress_auto(self, data: bytes) -> str:
        """Decompress data, auto-detecting PZip vs zlib format.

        PZ01 container starts with b"PZ" magic bytes.
        Legacy zlib data is supported for reading old captures only.

        Returns:
            Decompressed HTML string.

        Raises:
            PZipUnavailableError: If PZip data detected but C++ bridge not compiled.
            zlib.error: If legacy zlib data is corrupted.
        """
        if len(data) >= 2 and data[:2] == b"PZ":
            if not PZIP_AVAILABLE:
                raise PZipUnavailableError(
                    "PZip data detected but C++ bridge not compiled. "
                    "Compile: cd /home/phuc/projects/pzip && make"
                )
            return pzip_decompress(data).decode("utf-8")
        # Legacy zlib — read-only support for old captures
        logger.info("Reading legacy zlib capture — new captures require PZip")
        return zlib.decompress(data).decode("utf-8")

    def verify_rtc(self, original: str, compressed: bytes) -> bool:
        """Round-trip check: compress -> decompress -> compare.

        Compares SHA-256 hashes of original and decompressed content.
        Auto-detects PZip vs zlib format for decompression.

        Args:
            original: The original HTML string.
            compressed: The zlib or PZip compressed bytes.

        Returns:
            True if sha256(original) == sha256(decompressed).
        """
        try:
            decompressed = self.decompress_auto(compressed)
        except (zlib.error, RuntimeError, ValueError, OSError):
            return False

        original_hash = hashlib.sha256(original.encode("utf-8")).hexdigest()
        decompressed_hash = hashlib.sha256(decompressed.encode("utf-8")).hexdigest()
        return original_hash == decompressed_hash

    def list_captures(
        self,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List recent captures, optionally filtered by domain.

        Args:
            domain: If provided, only list captures for this domain.
            limit: Maximum number of captures to return. Default: 50.

        Returns:
            [{capture_id, domain, url, timestamp, size_bytes, mode}]
            Sorted by timestamp descending (most recent first).
        """
        captures: list[dict[str, Any]] = []

        if not self._history_root.exists():
            return captures

        if domain is not None:
            domain_dirs = [self._history_root / domain]
        else:
            domain_dirs = [
                d for d in self._history_root.iterdir()
                if d.is_dir()
            ]

        for domain_dir in domain_dirs:
            if not domain_dir.exists():
                continue
            for manifest_file in domain_dir.glob("*.ripple.json"):
                manifest_text = manifest_file.read_text(encoding="utf-8")
                manifest = json.loads(manifest_text)
                captures.append({
                    "capture_id": manifest["capture_id"],
                    "domain": manifest["domain"],
                    "url": manifest["url"],
                    "timestamp": manifest["timestamp"],
                    "size_bytes": manifest["html_size"],
                    "mode": manifest["mode"],
                })

        # Sort by timestamp descending (most recent first)
        captures.sort(key=lambda c: c["timestamp"], reverse=True)
        return captures[:limit]

    def find_latest_capture(self, url: str) -> dict[str, Any] | None:
        """Find the most recent capture for a given URL.

        Searches the domain directory for manifests matching the URL.
        Used for second-visit deduplication.

        Args:
            url: The page URL to search for.

        Returns:
            Most recent manifest dict with added "manifest_path" key,
            or None if no captures exist for this URL.
        """
        parsed = urlparse(url)
        domain = parsed.hostname or "unknown"
        domain_dir = self._history_root / domain

        if not domain_dir.exists():
            return None

        best: dict[str, Any] | None = None
        best_ts = ""

        for manifest_file in domain_dir.glob("*.ripple.json"):
            manifest_text = manifest_file.read_text(encoding="utf-8")
            manifest = json.loads(manifest_text)
            if manifest.get("url") == url:
                ts = manifest.get("timestamp", "")
                if ts > best_ts:
                    best_ts = ts
                    best = manifest
                    best["manifest_path"] = str(manifest_file)

        return best

    def get_capture(self, capture_id: str) -> dict[str, Any] | None:
        """Get a specific capture's metadata and content path.

        Searches all domain directories for the capture_id.

        Args:
            capture_id: The capture ID to look up.

        Returns:
            Full manifest dict with added "manifest_path" and "data_path" keys,
            or None if not found.
        """
        if not self._history_root.exists():
            return None

        for domain_dir in self._history_root.iterdir():
            if not domain_dir.is_dir():
                continue
            for manifest_file in domain_dir.glob("*.ripple.json"):
                manifest_text = manifest_file.read_text(encoding="utf-8")
                manifest = json.loads(manifest_text)
                if manifest.get("capture_id") == capture_id:
                    # New captures always use .ripple.pz
                    # Legacy captures may use .ripple.zlib (read-only compat)
                    engine = manifest.get("compression_engine", "pzip")
                    data_ext = ".ripple.zlib" if engine == "zlib" else ".ripple.pz"
                    data_path = manifest_file.parent / manifest_file.name.replace(
                        ".ripple.json", data_ext
                    )
                    manifest["manifest_path"] = str(manifest_file)
                    manifest["data_path"] = str(data_path)
                    return manifest

        return None

    def check_domain_exclusion(self, url: str) -> bool:
        """Check if a URL's domain is in the exclusion list.

        Excluded:
        - Schemes: chrome://, about:, data:, file://
        - Hosts: localhost, 127.0.0.1, 0.0.0.0
        - Private IPs: 192.168.*, 10.*, 172.16-31.*, and other RFC 1918

        Args:
            url: The URL to check.

        Returns:
            True if excluded (should NOT capture). False if allowed.
        """
        parsed = urlparse(url)

        # Check scheme exclusions
        scheme = (parsed.scheme or "").lower()
        if scheme in _EXCLUDED_SCHEMES:
            return True

        # Check host exclusions
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return True

        if hostname in _EXCLUDED_HOSTS:
            return True

        # Check private/reserved IP ranges
        if _is_private_ip(hostname):
            return True

        return False

    def get_stats(self) -> dict[str, Any]:
        """Get capture statistics across all domains.

        Returns:
            {
                total_captures: int,
                total_bytes: int,  # sum of original HTML sizes
                domains: {domain: count},
                compression_savings_bytes: int,  # total_bytes - total_compressed
            }
        """
        total_captures = 0
        total_bytes = 0
        total_compressed = 0
        domains: dict[str, int] = {}

        if not self._history_root.exists():
            return {
                "total_captures": 0,
                "total_bytes": 0,
                "domains": {},
                "compression_savings_bytes": 0,
            }

        for domain_dir in self._history_root.iterdir():
            if not domain_dir.is_dir():
                continue
            domain_name = domain_dir.name
            count = 0
            for manifest_file in domain_dir.glob("*.ripple.json"):
                manifest_text = manifest_file.read_text(encoding="utf-8")
                manifest = json.loads(manifest_text)
                total_bytes += manifest.get("html_size", 0)
                total_compressed += manifest.get("compressed_size", 0)
                count += 1
            if count > 0:
                domains[domain_name] = count
                total_captures += count

        return {
            "total_captures": total_captures,
            "total_bytes": total_bytes,
            "domains": domains,
            "compression_savings_bytes": total_bytes - total_compressed,
        }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def history_root(self) -> Path:
        """Base directory for capture storage."""
        return self._history_root

    @property
    def solace_home(self) -> Path:
        """Solace home directory."""
        return self._solace_home
