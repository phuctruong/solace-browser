"""
test_capture_pipeline.py — Tests for PZip Capture Pipeline

Covers:
  1. Capture guest mode (HTML only)
  2. Capture authenticated mode (HTML + assets + screenshot metadata)
  3. Domain exclusion for localhost, chrome://, internal IPs
  4. Compression produces smaller output
  5. RTC verification passes for valid data
  6. RTC verification fails for corrupted data
  7. Storage in correct directory structure
  8. List captures returns recent
  9. List captures filtered by domain
 10. Get capture by ID
 11. Stats counting
 12. URL slug generation (safe filenames)
 13. Large HTML capture (100KB+)
 14. Empty HTML capture
 15. Special characters in URL handled safely

Cross-ref: Diagram 10 (capture-pipeline), Paper 05 (PZip Stillwater)

Pure Python, no browser required, no external dependencies.

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_capture_pipeline.py -v

Rung: 641
"""

from __future__ import annotations

import json
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# Ensure src/ is on sys.path for local imports
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from capture_pipeline import (
    CapturePipeline,
    CaptureError,
    DomainExcludedError,
    RTCVerificationError,
    CaptureNotFoundError,
    _url_to_slug,
    _is_private_ip,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Test Page</title></head>
<body><h1>Hello World</h1><p>This is a test page.</p></body>
</html>"""

LARGE_HTML_PREFIX = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Large Page</title></head>
<body>
"""
LARGE_HTML_SUFFIX = "</body></html>"


def _make_pipeline(
    tmp_path: Path,
    *,
    now_fn: Any = None,
) -> CapturePipeline:
    """Create a CapturePipeline rooted in a temp directory."""
    return CapturePipeline(
        solace_home=tmp_path / "solace-home",
        now_fn=now_fn,
    )


def _fixed_now() -> datetime:
    """Return a fixed datetime for deterministic tests."""
    return datetime(2026, 3, 2, 8, 0, 0, tzinfo=timezone.utc)


def _make_large_html(target_bytes: int = 120_000) -> str:
    """Generate HTML content that exceeds target_bytes in size."""
    paragraph = "<p>" + ("Lorem ipsum dolor sit amet. " * 20) + "</p>\n"
    body_lines = []
    current_size = len(LARGE_HTML_PREFIX) + len(LARGE_HTML_SUFFIX)
    while current_size < target_bytes:
        body_lines.append(paragraph)
        current_size += len(paragraph)
    return LARGE_HTML_PREFIX + "".join(body_lines) + LARGE_HTML_SUFFIX


# ===========================================================================
# Test: URL Slug Generation
# ===========================================================================

class TestURLSlug:
    """Test URL-to-slug conversion for safe filenames."""

    def test_simple_path(self) -> None:
        assert _url_to_slug("https://mail.google.com/inbox") == "inbox"

    def test_nested_path(self) -> None:
        assert _url_to_slug("https://github.com/org/repo/issues/42") == "org-repo-issues-42"

    def test_root_path(self) -> None:
        assert _url_to_slug("https://example.com/") == "root"

    def test_empty_path(self) -> None:
        assert _url_to_slug("https://example.com") == "root"

    def test_query_params_stripped(self) -> None:
        slug = _url_to_slug("https://example.com/search?q=hello&page=1")
        assert "?" not in slug
        assert "=" not in slug
        assert slug == "search"

    def test_special_characters_replaced(self) -> None:
        slug = _url_to_slug("https://example.com/path%20with%20spaces/page.html")
        # Percent-encoded characters become dashes
        assert " " not in slug
        assert "%" not in slug

    def test_max_length_enforced(self) -> None:
        long_path = "/a" * 100
        slug = _url_to_slug(f"https://example.com{long_path}", max_length=20)
        assert len(slug) <= 20

    def test_unicode_in_path(self) -> None:
        slug = _url_to_slug("https://example.com/caf\u00e9/menu")
        # Should produce a non-empty slug without crashing
        assert len(slug) > 0
        assert "/" not in slug


# ===========================================================================
# Test: Domain Exclusion
# ===========================================================================

class TestDomainExclusion:
    """Test domain exclusion logic for capture filtering."""

    def test_localhost_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("http://localhost:3000/") is True

    def test_127_0_0_1_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("http://127.0.0.1:8080/api") is True

    def test_0_0_0_0_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("http://0.0.0.0:5000/") is True

    def test_192_168_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("http://192.168.1.100/admin") is True

    def test_10_x_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("http://10.0.0.1/") is True

    def test_172_16_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("http://172.16.0.1/") is True

    def test_172_31_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("http://172.31.255.255/") is True

    def test_chrome_scheme_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("chrome://settings/") is True

    def test_about_scheme_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("about:blank") is True

    def test_data_scheme_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("data:text/html,<h1>test</h1>") is True

    def test_file_scheme_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("file:///home/user/test.html") is True

    def test_public_domain_allowed(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("https://google.com/") is False

    def test_public_ip_allowed(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.check_domain_exclusion("http://8.8.8.8/") is False

    def test_empty_url_excluded(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        # Empty string has no hostname -> excluded
        assert pipeline.check_domain_exclusion("") is True

    def test_capture_raises_on_excluded_domain(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        with pytest.raises(DomainExcludedError, match="Domain excluded"):
            pipeline.capture("http://localhost:3000/", SIMPLE_HTML)


# ===========================================================================
# Test: Compression
# ===========================================================================

class TestCompression:
    """Test zlib compression and decompression."""

    def test_compress_produces_smaller_output(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        compressed = pipeline.compress(SIMPLE_HTML)
        assert len(compressed) < len(SIMPLE_HTML.encode("utf-8"))

    def test_compress_returns_bytes(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        compressed = pipeline.compress(SIMPLE_HTML)
        assert isinstance(compressed, bytes)

    def test_decompress_returns_original(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        compressed = pipeline.compress(SIMPLE_HTML)
        decompressed = pipeline.decompress(compressed)
        assert decompressed == SIMPLE_HTML

    def test_compress_with_custom_level(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        compressed_fast = pipeline.compress(SIMPLE_HTML, level=1)
        compressed_best = pipeline.compress(SIMPLE_HTML, level=9)
        # Both should decompress to the same content
        assert pipeline.decompress(compressed_fast) == SIMPLE_HTML
        assert pipeline.decompress(compressed_best) == SIMPLE_HTML
        # Best compression should be equal or smaller
        assert len(compressed_best) <= len(compressed_fast)

    def test_decompress_invalid_data_raises(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        with pytest.raises(zlib.error):
            pipeline.decompress(b"this is not zlib data")


# ===========================================================================
# Test: RTC Verification
# ===========================================================================

class TestRTCVerification:
    """Test round-trip check (compress -> decompress -> compare)."""

    def test_rtc_passes_for_valid_data(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        compressed = pipeline.compress(SIMPLE_HTML)
        assert pipeline.verify_rtc(SIMPLE_HTML, compressed) is True

    def test_rtc_fails_for_corrupted_data(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        compressed = pipeline.compress(SIMPLE_HTML)
        # Corrupt the compressed data by flipping bytes
        corrupted = bytearray(compressed)
        if len(corrupted) > 4:
            corrupted[4] ^= 0xFF
            corrupted[5] ^= 0xFF
        result = pipeline.verify_rtc(SIMPLE_HTML, bytes(corrupted))
        assert result is False

    def test_rtc_fails_for_wrong_original(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        compressed = pipeline.compress(SIMPLE_HTML)
        # Compare with different original
        different_html = "<html><body>Different content</body></html>"
        assert pipeline.verify_rtc(different_html, compressed) is False

    def test_rtc_passes_for_empty_content(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        compressed = pipeline.compress("")
        assert pipeline.verify_rtc("", compressed) is True

    def test_rtc_passes_for_large_content(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        large_html = _make_large_html(150_000)
        compressed = pipeline.compress(large_html)
        assert pipeline.verify_rtc(large_html, compressed) is True


# ===========================================================================
# Test: Guest Mode Capture
# ===========================================================================

class TestGuestCapture:
    """Test capturing in guest mode (HTML only)."""

    def test_guest_capture_returns_expected_keys(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/page", SIMPLE_HTML)

        assert "capture_id" in result
        assert result["capture_id"].startswith("cap-")
        assert result["domain"] == "example.com"
        assert result["mode"] == "guest"
        assert result["rtc_verified"] is True
        assert result["compressed"] is True
        assert isinstance(result["compression_ratio"], float)
        assert result["compression_ratio"] > 1.0
        assert isinstance(result["size_bytes"], int)
        assert result["size_bytes"] > 0
        assert isinstance(result["html_hash"], str)
        assert len(result["html_hash"]) == 64  # SHA-256 hex

    def test_guest_capture_stores_manifest_file(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/page", SIMPLE_HTML)

        manifest_path = Path(result["path"])
        assert manifest_path.exists()
        assert manifest_path.suffix == ".json"
        assert ".ripple" in manifest_path.name

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["capture_id"] == result["capture_id"]
        assert manifest["mode"] == "guest"
        assert manifest["assets"] == []
        assert manifest["screenshot_path"] is None

    def test_guest_capture_stores_compressed_data(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/page", SIMPLE_HTML)

        manifest_path = Path(result["path"])
        # Data file should be alongside manifest with .zlib extension
        data_path = manifest_path.parent / manifest_path.name.replace(
            ".ripple.json", ".ripple.zlib"
        )
        assert data_path.exists()

        # Decompress and verify content matches
        compressed_data = data_path.read_bytes()
        decompressed = pipeline.decompress(compressed_data)
        assert decompressed == SIMPLE_HTML

    def test_guest_ignores_assets(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        assets = [{"url": "https://example.com/style.css", "type": "css", "size": 1024}]
        result = pipeline.capture(
            "https://example.com/page", SIMPLE_HTML,
            assets=assets,
            logged_in=False,
        )
        manifest_path = Path(result["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Guest mode ignores assets
        assert manifest["assets"] == []

    def test_guest_ignores_screenshot(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://example.com/page", SIMPLE_HTML,
            screenshot_path=Path("/tmp/screenshot.png"),
            logged_in=False,
        )
        manifest_path = Path(result["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["screenshot_path"] is None


# ===========================================================================
# Test: Authenticated Mode Capture
# ===========================================================================

class TestAuthenticatedCapture:
    """Test capturing in authenticated mode (HTML + assets + screenshot)."""

    def test_authenticated_mode_label(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://mail.google.com/inbox", SIMPLE_HTML,
            logged_in=True,
        )
        assert result["mode"] == "authenticated"

    def test_authenticated_includes_assets(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        assets = [
            {"url": "https://mail.google.com/style.css", "type": "css", "size": 2048},
            {"url": "https://mail.google.com/app.js", "type": "js", "size": 8192},
        ]
        result = pipeline.capture(
            "https://mail.google.com/inbox", SIMPLE_HTML,
            logged_in=True,
            assets=assets,
        )
        manifest_path = Path(result["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(manifest["assets"]) == 2
        assert manifest["assets"][0]["type"] == "css"
        assert manifest["assets"][1]["type"] == "js"

    def test_authenticated_includes_screenshot_path(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        screenshot = tmp_path / "screenshot.png"
        screenshot.write_bytes(b"fake png data")
        result = pipeline.capture(
            "https://mail.google.com/inbox", SIMPLE_HTML,
            logged_in=True,
            screenshot_path=screenshot,
        )
        manifest_path = Path(result["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["screenshot_path"] == str(screenshot)

    def test_authenticated_includes_session_id(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://mail.google.com/inbox", SIMPLE_HTML,
            logged_in=True,
            session_id="sess-abc-123",
        )
        manifest_path = Path(result["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["session_id"] == "sess-abc-123"


# ===========================================================================
# Test: Storage Directory Structure
# ===========================================================================

class TestStorageStructure:
    """Test that captures are stored in the correct directory hierarchy."""

    def test_captures_stored_under_domain_directory(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        pipeline.capture("https://github.com/issues", SIMPLE_HTML)

        domain_dir = pipeline.history_root / "github.com"
        assert domain_dir.exists()
        assert domain_dir.is_dir()

    def test_manifest_and_data_in_same_directory(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://github.com/issues", SIMPLE_HTML)

        manifest_path = Path(result["path"])
        data_path = manifest_path.parent / manifest_path.name.replace(
            ".ripple.json", ".ripple.zlib"
        )
        assert manifest_path.parent == data_path.parent
        assert manifest_path.exists()
        assert data_path.exists()

    def test_multiple_domains_create_separate_dirs(self, tmp_path: Path) -> None:
        counter = [0]

        def incrementing_now() -> datetime:
            counter[0] += 1
            return datetime(2026, 3, 2, 8, 0, counter[0], tzinfo=timezone.utc)

        pipeline = _make_pipeline(tmp_path, now_fn=incrementing_now)

        pipeline.capture("https://github.com/issues", SIMPLE_HTML)
        pipeline.capture("https://mail.google.com/inbox", SIMPLE_HTML)

        assert (pipeline.history_root / "github.com").exists()
        assert (pipeline.history_root / "mail.google.com").exists()

    def test_filename_contains_timestamp_and_slug(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://github.com/org/repo/issues", SIMPLE_HTML)

        manifest_path = Path(result["path"])
        filename = manifest_path.name
        # Should contain the timestamp portion
        assert "20260302_080000" in filename
        # Should contain the slug
        assert "org-repo-issues" in filename
        # Should end with .ripple.json
        assert filename.endswith(".ripple.json")


# ===========================================================================
# Test: List Captures
# ===========================================================================

class TestListCaptures:
    """Test listing recent captures."""

    def test_list_empty_returns_empty(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.list_captures() == []

    def test_list_returns_captures_after_capture(self, tmp_path: Path) -> None:
        counter = [0]

        def incrementing_now() -> datetime:
            counter[0] += 1
            return datetime(2026, 3, 2, 8, 0, counter[0], tzinfo=timezone.utc)

        pipeline = _make_pipeline(tmp_path, now_fn=incrementing_now)
        pipeline.capture("https://example.com/page1", SIMPLE_HTML)
        pipeline.capture("https://example.com/page2", SIMPLE_HTML)

        captures = pipeline.list_captures()
        assert len(captures) == 2

    def test_list_sorted_by_timestamp_descending(self, tmp_path: Path) -> None:
        counter = [0]

        def incrementing_now() -> datetime:
            counter[0] += 1
            return datetime(2026, 3, 2, 8, 0, counter[0], tzinfo=timezone.utc)

        pipeline = _make_pipeline(tmp_path, now_fn=incrementing_now)
        pipeline.capture("https://example.com/first", SIMPLE_HTML)
        pipeline.capture("https://example.com/second", SIMPLE_HTML)

        captures = pipeline.list_captures()
        # Most recent (second) should come first
        assert captures[0]["url"] == "https://example.com/second"
        assert captures[1]["url"] == "https://example.com/first"

    def test_list_respects_limit(self, tmp_path: Path) -> None:
        counter = [0]

        def incrementing_now() -> datetime:
            counter[0] += 1
            return datetime(2026, 3, 2, 8, 0, counter[0], tzinfo=timezone.utc)

        pipeline = _make_pipeline(tmp_path, now_fn=incrementing_now)
        for i in range(5):
            pipeline.capture(f"https://example.com/page{i}", SIMPLE_HTML)

        captures = pipeline.list_captures(limit=3)
        assert len(captures) == 3

    def test_list_filtered_by_domain(self, tmp_path: Path) -> None:
        counter = [0]

        def incrementing_now() -> datetime:
            counter[0] += 1
            return datetime(2026, 3, 2, 8, 0, counter[0], tzinfo=timezone.utc)

        pipeline = _make_pipeline(tmp_path, now_fn=incrementing_now)
        pipeline.capture("https://github.com/issues", SIMPLE_HTML)
        pipeline.capture("https://example.com/page", SIMPLE_HTML)
        pipeline.capture("https://github.com/pulls", SIMPLE_HTML)

        github_captures = pipeline.list_captures(domain="github.com")
        assert len(github_captures) == 2
        for cap in github_captures:
            assert cap["domain"] == "github.com"

    def test_list_domain_filter_no_match(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        pipeline.capture("https://example.com/page", SIMPLE_HTML)

        captures = pipeline.list_captures(domain="nonexistent.com")
        assert len(captures) == 0

    def test_list_contains_expected_fields(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        pipeline.capture("https://example.com/page", SIMPLE_HTML)

        captures = pipeline.list_captures()
        assert len(captures) == 1
        cap = captures[0]
        assert "capture_id" in cap
        assert "domain" in cap
        assert "url" in cap
        assert "timestamp" in cap
        assert "size_bytes" in cap
        assert "mode" in cap


# ===========================================================================
# Test: Get Capture by ID
# ===========================================================================

class TestGetCapture:
    """Test retrieving a specific capture by its ID."""

    def test_get_existing_capture(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/page", SIMPLE_HTML)

        fetched = pipeline.get_capture(result["capture_id"])
        assert fetched is not None
        assert fetched["capture_id"] == result["capture_id"]
        assert fetched["url"] == "https://example.com/page"
        assert "manifest_path" in fetched
        assert "data_path" in fetched

    def test_get_nonexistent_capture_returns_none(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.get_capture("cap-nonexistent") is None

    def test_get_capture_data_path_points_to_zlib(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/page", SIMPLE_HTML)

        fetched = pipeline.get_capture(result["capture_id"])
        assert fetched is not None
        data_path = Path(fetched["data_path"])
        assert data_path.name.endswith(".ripple.zlib")


# ===========================================================================
# Test: Stats
# ===========================================================================

class TestStats:
    """Test capture statistics."""

    def test_stats_empty(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        stats = pipeline.get_stats()
        assert stats["total_captures"] == 0
        assert stats["total_bytes"] == 0
        assert stats["domains"] == {}
        assert stats["compression_savings_bytes"] == 0

    def test_stats_after_captures(self, tmp_path: Path) -> None:
        counter = [0]

        def incrementing_now() -> datetime:
            counter[0] += 1
            return datetime(2026, 3, 2, 8, 0, counter[0], tzinfo=timezone.utc)

        pipeline = _make_pipeline(tmp_path, now_fn=incrementing_now)
        pipeline.capture("https://github.com/issues", SIMPLE_HTML)
        pipeline.capture("https://github.com/pulls", SIMPLE_HTML)
        pipeline.capture("https://example.com/page", SIMPLE_HTML)

        stats = pipeline.get_stats()
        assert stats["total_captures"] == 3
        assert stats["total_bytes"] > 0
        assert stats["domains"]["github.com"] == 2
        assert stats["domains"]["example.com"] == 1
        assert stats["compression_savings_bytes"] > 0

    def test_stats_compression_savings_positive(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        pipeline.capture("https://example.com/page", SIMPLE_HTML)

        stats = pipeline.get_stats()
        # Compressed should be smaller, so savings > 0
        assert stats["compression_savings_bytes"] > 0


# ===========================================================================
# Test: Large HTML Capture
# ===========================================================================

class TestLargeCapture:
    """Test capturing large HTML content (100KB+)."""

    def test_large_html_capture_succeeds(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        large_html = _make_large_html(120_000)
        assert len(large_html.encode("utf-8")) >= 100_000

        result = pipeline.capture("https://example.com/large-page", large_html)
        assert result["rtc_verified"] is True
        assert result["size_bytes"] >= 100_000
        assert result["compression_ratio"] > 1.0

    def test_large_html_compresses_well(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        large_html = _make_large_html(120_000)
        compressed = pipeline.compress(large_html)
        original_size = len(large_html.encode("utf-8"))
        # Repetitive HTML should compress very well (10x+)
        assert len(compressed) < original_size / 5

    def test_large_html_rtc_passes(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        large_html = _make_large_html(150_000)
        compressed = pipeline.compress(large_html)
        assert pipeline.verify_rtc(large_html, compressed) is True


# ===========================================================================
# Test: Empty HTML Capture
# ===========================================================================

class TestEmptyCapture:
    """Test capturing empty HTML content."""

    def test_empty_html_capture_succeeds(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/empty", "")

        assert result["rtc_verified"] is True
        assert result["size_bytes"] == 0
        assert result["mode"] == "guest"

    def test_empty_html_compressed_data_exists(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/empty", "")

        manifest_path = Path(result["path"])
        data_path = manifest_path.parent / manifest_path.name.replace(
            ".ripple.json", ".ripple.zlib"
        )
        assert data_path.exists()
        # Decompress should return empty string
        decompressed = pipeline.decompress(data_path.read_bytes())
        assert decompressed == ""


# ===========================================================================
# Test: Special Characters in URL
# ===========================================================================

class TestSpecialCharacterURL:
    """Test that special characters in URLs are handled safely."""

    def test_url_with_query_params(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://example.com/search?q=hello+world&lang=en",
            SIMPLE_HTML,
        )
        assert result["domain"] == "example.com"
        assert result["rtc_verified"] is True

    def test_url_with_fragment(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://example.com/docs#section-3",
            SIMPLE_HTML,
        )
        assert result["rtc_verified"] is True

    def test_url_with_port(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://example.com:8443/api/data",
            SIMPLE_HTML,
        )
        assert result["domain"] == "example.com"

    def test_url_with_encoded_characters(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://example.com/path%2Fwith%2Fencoded",
            SIMPLE_HTML,
        )
        assert result["rtc_verified"] is True
        # Verify the manifest file was written without errors
        manifest_path = Path(result["path"])
        assert manifest_path.exists()

    def test_url_with_unicode(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://example.com/caf\u00e9/p\u00e2tisserie",
            SIMPLE_HTML,
        )
        assert result["rtc_verified"] is True


# ===========================================================================
# Test: Private IP Detection
# ===========================================================================

class TestPrivateIP:
    """Test the _is_private_ip helper function."""

    def test_192_168_is_private(self) -> None:
        assert _is_private_ip("192.168.0.1") is True
        assert _is_private_ip("192.168.255.255") is True

    def test_10_x_is_private(self) -> None:
        assert _is_private_ip("10.0.0.1") is True
        assert _is_private_ip("10.255.255.255") is True

    def test_172_16_31_is_private(self) -> None:
        assert _is_private_ip("172.16.0.1") is True
        assert _is_private_ip("172.31.255.255") is True

    def test_172_32_is_not_private(self) -> None:
        assert _is_private_ip("172.32.0.1") is False

    def test_loopback_is_private(self) -> None:
        assert _is_private_ip("127.0.0.1") is True

    def test_public_ip_is_not_private(self) -> None:
        assert _is_private_ip("8.8.8.8") is False
        assert _is_private_ip("142.250.80.46") is False

    def test_hostname_returns_false(self) -> None:
        # Non-IP hostnames should return False (not raise)
        assert _is_private_ip("google.com") is False
        assert _is_private_ip("mail.example.org") is False


# ===========================================================================
# Test: Manifest Content
# ===========================================================================

class TestManifestContent:
    """Test that manifest JSON contains all required fields."""

    def test_manifest_has_all_fields(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture(
            "https://mail.google.com/inbox", SIMPLE_HTML,
            logged_in=True,
            assets=[{"url": "https://mail.google.com/style.css", "type": "css", "size": 1024}],
            session_id="sess-test",
        )

        manifest_path = Path(result["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        required_fields = [
            "capture_id", "url", "domain", "timestamp", "mode",
            "html_hash", "html_size", "compressed_size", "compression_ratio",
            "rtc_verified", "assets", "screenshot_path", "session_id",
        ]
        for field_name in required_fields:
            assert field_name in manifest, f"Missing field: {field_name}"

    def test_manifest_html_hash_is_sha256(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/page", SIMPLE_HTML)

        manifest_path = Path(result["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Verify the hash matches independently computed SHA-256
        import hashlib
        expected_hash = hashlib.sha256(SIMPLE_HTML.encode("utf-8")).hexdigest()
        assert manifest["html_hash"] == expected_hash

    def test_manifest_compression_ratio_correct(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/page", SIMPLE_HTML)

        manifest_path = Path(result["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        expected_ratio = round(
            manifest["html_size"] / manifest["compressed_size"], 2
        )
        assert manifest["compression_ratio"] == expected_ratio

    def test_manifest_is_valid_json(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path, now_fn=_fixed_now)
        result = pipeline.capture("https://example.com/page", SIMPLE_HTML)

        manifest_path = Path(result["path"])
        # Should not raise
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert isinstance(manifest, dict)
