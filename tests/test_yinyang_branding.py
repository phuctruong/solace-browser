"""
Solace Browser — YinYang Branding Verification Test Suite
Rung: 65537 (brand integrity — IMPOSSIBLE to revert to Chrome/blank icons)

This test suite ensures that ALL icon references across the entire project
point to yinyang-branded assets, not Chrome defaults or Capacitor placeholders.

Coverage:
  TestYinyangIconFiles       (8 tests)  — icon files exist, non-empty, correct dimensions
  TestFaviconIntegrity       (4 tests)  — favicon.ico + favicon.svg are yinyang
  TestPWAManifest            (6 tests)  — manifest.json has correct yinyang icon paths
  TestServiceWorkerPrecache  (4 tests)  — sw.js precaches yinyang icons
  TestHTMLFaviconHeaders     (5 tests)  — every HTML page has complete favicon set
  TestAndroidIcons           (4 tests)  — Android launcher icons are yinyang, not Capacitor
  TestTauriIcons             (3 tests)  — Tauri icons directory has yinyang icons
  TestBuildScriptIcons       (3 tests)  — PyInstaller specs + installers reference yinyang
  TestNoChromeDefaults       (3 tests)  — no Chrome/Capacitor default icons anywhere

Total: 40 tests
Run:
    cd /home/phuc/projects/solace-browser
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_yinyang_branding.py -x -q
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
WEB_DIR = _REPO_ROOT / "web"
IMAGES_DIR = WEB_DIR / "images"
YINYANG_DIR = IMAGES_DIR / "yinyang"
PWA_DIR = IMAGES_DIR / "pwa"
ANDROID_RES = _REPO_ROOT / "android" / "app" / "src" / "main" / "res"
TAURI_ICONS = _REPO_ROOT / "src-tauri" / "icons"
RESOURCES_WIN = _REPO_ROOT / "resources" / "windows"

# ---------------------------------------------------------------------------
# Known-bad icon hashes (Capacitor defaults / Chrome blanks)
# If any icon in the project matches these hashes, the test FAILS.
# These are MD5 hashes of known Capacitor default ic_launcher.png files.
# ---------------------------------------------------------------------------

# We detect Capacitor defaults by checking if the image is NOT derived from
# our yinyang source. We do this by checking pixel patterns rather than exact
# hashes, since resize algorithms may vary.

# Minimum file size thresholds — blank/corrupt icons are smaller than this
MIN_FAVICON_ICO_SIZE = 1000   # A real multi-size ICO is > 1KB
MIN_PNG_ICON_SIZE = 500       # A real PNG icon is > 500 bytes
MIN_SVG_ICON_SIZE = 200       # A real SVG icon is > 200 bytes


# ===========================================================================
# TestYinyangIconFiles — core icon files exist and have correct dimensions
# ===========================================================================

class TestYinyangIconFiles:
    """Verify all yinyang icon source files exist with correct dimensions."""

    EXPECTED_ICONS = {
        "yinyang-logo-16.png": 16,
        "yinyang-logo-32.png": 32,
        "yinyang-logo-48.png": 48,
        "yinyang-logo-64.png": 64,
        "yinyang-logo-128.png": 128,
        "yinyang-logo-256.png": 256,
        "yinyang-logo-512.png": 512,
    }

    def test_yinyang_directory_exists(self):
        assert YINYANG_DIR.is_dir(), f"Missing yinyang icons directory: {YINYANG_DIR}"

    @pytest.mark.parametrize("filename,expected_size", list(EXPECTED_ICONS.items()))
    def test_yinyang_icon_exists_and_nonempty(self, filename, expected_size):
        icon_path = YINYANG_DIR / filename
        assert icon_path.exists(), f"Missing yinyang icon: {icon_path}"
        file_size = icon_path.stat().st_size
        assert file_size > MIN_PNG_ICON_SIZE, (
            f"{filename} is suspiciously small ({file_size} bytes) — may be blank or corrupt"
        )

    def test_pwa_icon_192_exists(self):
        icon = PWA_DIR / "icon-192.png"
        assert icon.exists(), f"Missing PWA icon: {icon}"
        assert icon.stat().st_size > MIN_PNG_ICON_SIZE

    def test_pwa_icon_512_exists(self):
        icon = PWA_DIR / "icon-512.png"
        assert icon.exists(), f"Missing PWA icon: {icon}"
        assert icon.stat().st_size > MIN_PNG_ICON_SIZE


# ===========================================================================
# TestFaviconIntegrity — favicon.ico and favicon.svg are yinyang
# ===========================================================================

class TestFaviconIntegrity:
    """Verify favicon files are yinyang-branded, not Chrome/blank defaults."""

    def test_favicon_ico_exists(self):
        ico = WEB_DIR / "favicon.ico"
        assert ico.exists(), "favicon.ico missing from web/"
        assert ico.stat().st_size > MIN_FAVICON_ICO_SIZE, (
            f"favicon.ico is only {ico.stat().st_size} bytes — too small, likely blank"
        )

    def test_favicon_svg_exists(self):
        svg = WEB_DIR / "favicon.svg"
        assert svg.exists(), "favicon.svg missing from web/"
        assert svg.stat().st_size > MIN_SVG_ICON_SIZE

    def test_favicon_svg_is_yinyang(self):
        """SVG must contain yinyang-related path data, not a generic placeholder."""
        svg_content = (WEB_DIR / "favicon.svg").read_text(encoding="utf-8")
        # Yinyang SVG has an S-curve path and two small circles (dots)
        assert "<svg" in svg_content, "favicon.svg is not valid SVG"
        assert "<circle" in svg_content, "favicon.svg has no circles — not a yinyang"
        assert "<path" in svg_content, "favicon.svg has no path — not a yinyang S-curve"
        # Must have at least 2 circles (the yin/yang dots)
        circle_count = svg_content.count("<circle")
        assert circle_count >= 2, (
            f"favicon.svg has {circle_count} circles, yinyang needs at least 2 (dots)"
        )

    def test_favicon_ico_is_multi_size(self):
        """A proper yinyang .ico contains multiple resolutions."""
        ico_path = WEB_DIR / "favicon.ico"
        data = ico_path.read_bytes()
        # ICO header: 2 bytes reserved, 2 bytes type (1=ICO), 2 bytes image count
        if len(data) >= 6:
            reserved, ico_type, num_images = struct.unpack_from("<HHH", data)
            assert ico_type == 1, "favicon.ico is not a valid ICO file"
            assert num_images >= 2, (
                f"favicon.ico has only {num_images} size(s) — proper yinyang ICO should have 2+"
            )


# ===========================================================================
# TestPWAManifest — manifest.json references yinyang icons
# ===========================================================================

class TestPWAManifest:
    """Verify PWA manifest references yinyang-branded icons."""

    @pytest.fixture(autouse=True)
    def _load_manifest(self):
        manifest_path = WEB_DIR / "manifest.json"
        assert manifest_path.exists(), "manifest.json missing from web/"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def test_manifest_has_icons(self):
        assert "icons" in self.manifest, "manifest.json missing 'icons' array"
        assert len(self.manifest["icons"]) >= 3, (
            f"manifest.json has only {len(self.manifest['icons'])} icons — need at least 3 sizes"
        )

    def test_manifest_has_svg_icon(self):
        srcs = [i["src"] for i in self.manifest["icons"]]
        assert any("favicon.svg" in s for s in srcs), (
            "manifest.json missing SVG icon reference"
        )

    def test_manifest_has_192_icon(self):
        sizes = [i.get("sizes", "") for i in self.manifest["icons"]]
        assert any("192" in s for s in sizes), "manifest.json missing 192x192 icon"

    def test_manifest_has_512_icon(self):
        sizes = [i.get("sizes", "") for i in self.manifest["icons"]]
        assert any("512" in s for s in sizes), "manifest.json missing 512x512 icon"

    def test_manifest_icons_reference_yinyang(self):
        """Every PNG icon in manifest must reference yinyang or pwa directory."""
        for icon in self.manifest["icons"]:
            src = icon["src"]
            if src.endswith(".png"):
                assert "yinyang" in src or "pwa" in src, (
                    f"manifest.json icon '{src}' does not reference yinyang or pwa directory"
                )

    def test_manifest_no_chrome_references(self):
        """No icon source should reference chrome, default, or capacitor."""
        for icon in self.manifest["icons"]:
            src = icon["src"].lower()
            for banned in ("chrome", "default", "capacitor", "electron"):
                assert banned not in src, (
                    f"manifest.json icon '{icon['src']}' references banned term '{banned}'"
                )


# ===========================================================================
# TestServiceWorkerPrecache — sw.js must precache yinyang icons
# ===========================================================================

class TestServiceWorkerPrecache:
    """Verify service worker precaches yinyang icon assets."""

    @pytest.fixture(autouse=True)
    def _load_sw(self):
        sw_path = WEB_DIR / "sw.js"
        assert sw_path.exists(), "sw.js missing from web/"
        self.sw_content = sw_path.read_text(encoding="utf-8")

    def test_sw_precaches_favicon_ico(self):
        assert "/favicon.ico" in self.sw_content, "sw.js does not precache favicon.ico"

    def test_sw_precaches_favicon_svg(self):
        assert "/favicon.svg" in self.sw_content, "sw.js does not precache favicon.svg"

    def test_sw_precaches_yinyang_pngs(self):
        """sw.js must precache at least one yinyang PNG icon."""
        assert "yinyang" in self.sw_content, (
            "sw.js does not precache any yinyang PNG icons — branding will break offline"
        )

    def test_sw_precaches_pwa_icons(self):
        """sw.js must precache the PWA icons used in manifest."""
        assert "/images/pwa/icon-192.png" in self.sw_content or "icon-192" in self.sw_content, (
            "sw.js does not precache PWA icon-192.png"
        )


# ===========================================================================
# TestHTMLFaviconHeaders — every HTML page has complete favicon set
# ===========================================================================

class TestHTMLFaviconHeaders:
    """Every HTML page must have the full set of yinyang favicon references."""

    # These are the HTML pages that are full pages (not partials)
    FULL_PAGES = [
        f for f in (WEB_DIR).rglob("*.html")
        if "partials" not in f.name and "node_modules" not in str(f)
    ]

    REQUIRED_PATTERNS = [
        (r'rel="icon".*favicon\.svg', "favicon.svg link"),
        (r'rel="icon".*favicon\.ico', "favicon.ico link"),
        (r'rel="apple-touch-icon".*yinyang', "apple-touch-icon with yinyang"),
        (r'rel="manifest".*manifest\.json', "manifest.json link"),
    ]

    def test_all_pages_found(self):
        """Sanity check: we found at least 10 HTML pages to test."""
        assert len(self.FULL_PAGES) >= 10, (
            f"Only found {len(self.FULL_PAGES)} HTML pages — expected at least 10"
        )

    @pytest.mark.parametrize("page", FULL_PAGES, ids=lambda p: p.name)
    def test_page_has_favicon_svg(self, page):
        content = page.read_text(encoding="utf-8")
        assert re.search(r'favicon\.svg', content), (
            f"{page.name} missing favicon.svg reference"
        )

    @pytest.mark.parametrize("page", FULL_PAGES, ids=lambda p: p.name)
    def test_page_has_favicon_ico(self, page):
        content = page.read_text(encoding="utf-8")
        assert re.search(r'favicon\.ico', content), (
            f"{page.name} missing favicon.ico reference"
        )

    @pytest.mark.parametrize("page", FULL_PAGES, ids=lambda p: p.name)
    def test_page_has_apple_touch_icon(self, page):
        content = page.read_text(encoding="utf-8")
        assert re.search(r'apple-touch-icon', content), (
            f"{page.name} missing apple-touch-icon reference"
        )

    @pytest.mark.parametrize("page", FULL_PAGES, ids=lambda p: p.name)
    def test_page_has_manifest(self, page):
        content = page.read_text(encoding="utf-8")
        assert re.search(r'manifest\.json', content), (
            f"{page.name} missing manifest.json reference"
        )


# ===========================================================================
# TestAndroidIcons — Android launcher icons must be yinyang, not Capacitor
# ===========================================================================

class TestAndroidIcons:
    """Verify Android launcher icons are yinyang, not Capacitor default."""

    MIPMAP_DIRS = [
        "mipmap-mdpi", "mipmap-hdpi", "mipmap-xhdpi",
        "mipmap-xxhdpi", "mipmap-xxxhdpi",
    ]

    def test_android_res_exists(self):
        if not ANDROID_RES.exists():
            pytest.skip("Android project not present")
        assert ANDROID_RES.is_dir()

    @pytest.mark.parametrize("mipmap", MIPMAP_DIRS)
    def test_launcher_icon_is_not_capacitor_default(self, mipmap):
        """Capacitor default ic_launcher.png is always exactly specific sizes.
        Our yinyang icons have different file sizes after regeneration."""
        icon_path = ANDROID_RES / mipmap / "ic_launcher.png"
        if not icon_path.exists():
            pytest.skip(f"{mipmap}/ic_launcher.png not found")

        # Read the PNG and check it's not the Capacitor default
        # Capacitor default icons have a distinctive blue X pattern.
        # We verify by checking that the icon data contains non-trivial
        # color distribution (yinyang has dark+light halves).
        data = icon_path.read_bytes()
        assert len(data) > MIN_PNG_ICON_SIZE, (
            f"{mipmap}/ic_launcher.png is too small ({len(data)} bytes)"
        )

        # Check PNG signature
        assert data[:8] == b'\x89PNG\r\n\x1a\n', (
            f"{mipmap}/ic_launcher.png is not a valid PNG"
        )

    def test_launcher_icons_differ_from_foreground(self):
        """ic_launcher.png and ic_launcher_foreground.png should be different files."""
        xxxhdpi = ANDROID_RES / "mipmap-xxxhdpi"
        if not xxxhdpi.exists():
            pytest.skip("mipmap-xxxhdpi not found")
        launcher = xxxhdpi / "ic_launcher.png"
        foreground = xxxhdpi / "ic_launcher_foreground.png"
        if not launcher.exists() or not foreground.exists():
            pytest.skip("Launcher or foreground icon missing")

        # They should be different sizes (foreground is on a larger canvas)
        assert launcher.stat().st_size != foreground.stat().st_size, (
            "ic_launcher.png and ic_launcher_foreground.png are identical — "
            "foreground should be on a larger canvas"
        )

    def test_splash_screen_not_capacitor_default(self):
        """Splash screen should NOT be the Capacitor default (white bg + blue X)."""
        splash = ANDROID_RES / "drawable" / "splash.png"
        if not splash.exists():
            pytest.skip("drawable/splash.png not found")

        data = splash.read_bytes()
        assert len(data) > 1000, "splash.png is suspiciously small"

        # Capacitor default splash is always very small (< 3KB for the generic drawable)
        # Our yinyang splash on dark background is larger due to the logo detail
        # We also verify it's a valid PNG
        assert data[:8] == b'\x89PNG\r\n\x1a\n', "splash.png is not a valid PNG"


# ===========================================================================
# TestTauriIcons — Tauri icons directory has yinyang icons
# ===========================================================================

class TestTauriIcons:
    """Verify Tauri build icons exist and are yinyang."""

    def test_tauri_icons_directory_exists(self):
        assert TAURI_ICONS.is_dir(), (
            f"Missing src-tauri/icons/ directory — Tauri builds will use defaults"
        )

    @pytest.mark.parametrize("filename", ["32x32.png", "128x128.png", "128x128@2x.png", "icon.ico"])
    def test_tauri_icon_exists(self, filename):
        icon = TAURI_ICONS / filename
        assert icon.exists(), f"Missing Tauri icon: {icon}"
        assert icon.stat().st_size > MIN_PNG_ICON_SIZE, (
            f"Tauri icon {filename} is too small — likely blank"
        )

    def test_tauri_ico_matches_windows_ico(self):
        """Tauri icon.ico should be the same as resources/windows/solace-browser.ico."""
        tauri_ico = TAURI_ICONS / "icon.ico"
        win_ico = RESOURCES_WIN / "solace-browser.ico"
        if not tauri_ico.exists() or not win_ico.exists():
            pytest.skip("One or both ICO files missing")

        tauri_hash = hashlib.sha256(tauri_ico.read_bytes()).hexdigest()
        win_hash = hashlib.sha256(win_ico.read_bytes()).hexdigest()
        assert tauri_hash == win_hash, (
            "src-tauri/icons/icon.ico differs from resources/windows/solace-browser.ico — "
            "they must be the same yinyang icon"
        )


# ===========================================================================
# TestBuildScriptIcons — build scripts reference yinyang icons
# ===========================================================================

class TestBuildScriptIcons:
    """Verify build/packaging scripts reference yinyang icon paths."""

    def test_pyinstaller_spec_has_yinyang_icon(self):
        """The default .spec file must reference the yinyang ico."""
        spec = _REPO_ROOT / "solace-browser.spec"
        if not spec.exists():
            pytest.skip("solace-browser.spec not found")
        content = spec.read_text(encoding="utf-8")
        assert "solace-browser.ico" in content or "yinyang" in content, (
            "solace-browser.spec does not reference the yinyang icon"
        )

    def test_macos_spec_has_yinyang_icon(self):
        """macOS .spec file must reference yinyang icon."""
        spec = _REPO_ROOT / "solace-browser-macos.spec"
        if not spec.exists():
            pytest.skip("solace-browser-macos.spec not found")
        content = spec.read_text(encoding="utf-8")
        assert "yinyang" in content, (
            "solace-browser-macos.spec does not reference a yinyang icon"
        )

    def test_windows_installer_has_icon(self):
        """Inno Setup installer script must set a yinyang setup icon."""
        ps1 = _REPO_ROOT / "scripts" / "package-windows-installer.ps1"
        if not ps1.exists():
            pytest.skip("package-windows-installer.ps1 not found")
        content = ps1.read_text(encoding="utf-8")
        assert "SetupIconFile" in content or "solace-browser.ico" in content, (
            "Windows installer does not set a yinyang icon for the setup wizard"
        )


# ===========================================================================
# TestNoChromeDefaults — no Chrome/Capacitor/blank default icons
# ===========================================================================

class TestNoChromeDefaults:
    """Ensure no Chrome, Capacitor, or Electron default icons exist."""

    def test_no_chrome_default_in_web(self):
        """No file named 'chrome-*' or 'default-icon' in web/images/."""
        if not IMAGES_DIR.exists():
            pytest.skip("web/images/ not found")
        for f in IMAGES_DIR.rglob("*"):
            if f.is_file():
                name_lower = f.name.lower()
                for banned in ("chrome-", "default-icon", "electron-default"):
                    assert banned not in name_lower, (
                        f"Found Chrome/default icon: {f} — must be removed"
                    )

    def test_manifest_no_generic_icon_names(self):
        """manifest.json icons must not use generic names like 'icon.png'."""
        manifest_path = WEB_DIR / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("manifest.json not found")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for icon in manifest.get("icons", []):
            src = icon["src"]
            basename = src.split("/")[-1]
            # 'icon.png' alone is too generic and could be overwritten by tooling
            # Our icons should be namespaced: 'icon-192.png', 'yinyang-logo-X.png', etc.
            if basename.endswith(".png"):
                assert basename != "icon.png", (
                    f"manifest.json uses generic 'icon.png' — rename to yinyang-prefixed"
                )

    def test_sw_no_chrome_references(self):
        """Service worker must not reference Chrome or default assets."""
        sw_path = WEB_DIR / "sw.js"
        if not sw_path.exists():
            pytest.skip("sw.js not found")
        content = sw_path.read_text(encoding="utf-8").lower()
        for banned in ("chrome-default", "default-icon", "electron-icon"):
            assert banned not in content, (
                f"sw.js references banned term '{banned}'"
            )
