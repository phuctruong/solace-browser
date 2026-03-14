# Diagram: 01-triangle-architecture
"""
primewiki_client.py — Prime Wiki cloud sync client.

Pushes structural snapshots to solaceagi.com Firestore.
Pulls community snapshots for recipe generation.

Ported from: solace-cli/scratch/prime_wiki_extractor.py
Rung: 641
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

import aiohttp

logger = logging.getLogger("solace-browser.primewiki")

DEFAULT_API_BASE = "https://solaceagi-mfjzxmegpq-uc.a.run.app"

# Deduplication: skip push if same URL was pushed within this window (seconds)
_DEDUP_WINDOW_SEC = 3600


def normalize_url(url: str) -> str:
    """Normalize URL for consistent hashing (strip query, fragment, trailing slash)."""
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path.rstrip("/") or "/", "", "", ""))


def url_hash(url: str) -> str:
    """SHA-256 hash of normalized URL."""
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def compress_snapshot(data: dict[str, Any]) -> tuple[bytes, str, str, int, int]:
    """Compress snapshot dict with gzip.

    Returns: (compressed_bytes, sha256_original, sha256_compressed,
              original_size, compressed_size)
    """
    orig = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    sha_orig = hashlib.sha256(orig).hexdigest()
    comp = gzip.compress(orig, compresslevel=9)
    sha_comp = hashlib.sha256(comp).hexdigest()
    return comp, sha_orig, sha_comp, len(orig), len(comp)


def verify_rtc(comp: bytes, data: dict[str, Any]) -> bool:
    """Round-trip check: decompress and verify SHA-256 matches original."""
    decomp = gzip.decompress(comp)
    orig = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(decomp).hexdigest() == hashlib.sha256(orig).hexdigest()


class PrimeWikiClient:
    """Async client for Prime Wiki cloud API."""

    def __init__(self, api_base: str = DEFAULT_API_BASE) -> None:
        self._api_base = api_base.rstrip("/")
        self._push_times: dict[str, float] = {}  # url_hash -> timestamp

    def _should_push(self, uhash: str) -> bool:
        """Check dedup window — skip if pushed recently."""
        last = self._push_times.get(uhash, 0.0)
        return (time.time() - last) > _DEDUP_WINDOW_SEC

    async def push(
        self,
        url: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Push a Prime Wiki snapshot to the cloud API.

        Args:
            url: Page URL.
            schema: Structural extraction result (from strip_to_structure).

        Returns:
            Response dict with ok, status, result, sizes.
        """
        uhash = url_hash(url)

        if not self._should_push(uhash):
            return {
                "ok": True,
                "skipped": True,
                "reason": "dedup_window",
                "url_hash": uhash,
            }

        comp, sha_o, sha_c, orig_sz, comp_sz = compress_snapshot(schema)
        rtc_ok = verify_rtc(comp, schema)
        b64 = base64.b64encode(comp).decode()

        payload = {
            "url_hash": uhash,
            "url_display": normalize_url(url)[:200],
            "snapshot_b64": b64,
            "original_size": orig_sz,
            "compressed_size": comp_sz,
            "schema_version": "prime-wiki-v1",
            "page_type": schema.get("page_type", "other"),
            "rtc_verified": rtc_ok,
            "sha256_original": sha_o,
            "sha256_compressed": sha_c,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._api_base}/api/v1/prime-wiki/push",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                result = await resp.json()
                if resp.status < 400:
                    self._push_times[uhash] = time.time()
                return {
                    "ok": resp.status < 400,
                    "status": resp.status,
                    "result": result,
                    "rtc_verified": rtc_ok,
                    "original_size": orig_sz,
                    "compressed_size": comp_sz,
                }

    async def pull(self, url: str) -> dict[str, Any] | None:
        """Pull a Prime Wiki snapshot from the cloud API.

        Returns: Decompressed snapshot dict, or None if not found.
        """
        uhash = url_hash(url)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._api_base}/api/v1/prime-wiki/pull",
                params={"url_hash": uhash},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 404:
                    return None
                data = await resp.json()
                snapshot_b64 = data.get("snapshot", {}).get("snapshot_b64") or data.get("snapshot_b64")
                if not snapshot_b64:
                    return None
                return json.loads(gzip.decompress(base64.b64decode(snapshot_b64)))

    async def stats(self) -> dict[str, Any]:
        """Get Prime Wiki index statistics."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._api_base}/api/v1/prime-wiki/stats",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return await resp.json()
