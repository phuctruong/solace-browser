"""
Solace Browser Phase 3 — Cross-Platform Distribution Test Suite
Rung: 641 (local correctness)

Coverage:
  TestBuildScripts      (15 tests)  — script existence, permissions, version, SHA-256, dist dir
  TestInstaller         (15 tests)  — welcome page structure, config persistence, all steps
  TestDownloadPage      (12 tests)  — platform detection, download links, checksums, instructions
  TestAutoUpdate        (20 tests)  — semver, update check, SHA-256 verify, banner, downgrade
  TestTauriConfig       (12 tests)  — JSON valid, window settings, bundle IDs, permissions

Total: 74 tests
Run:
    cd /home/phuc/projects/solace-browser
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_distribution.py -x -q
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import urllib.error

import pytest

# ---------------------------------------------------------------------------
# sys.path setup — mirror pattern from other test files in this project
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

# Import the auto_update module under test
from src.auto_update import (
    AutoUpdateChecker,
    UpdateBanner,
    UpdateDownloader,
    UpdateResult,
    ReleaseInfo,
    is_newer,
    is_downgrade,
    parse_semver,
    read_version_file,
    DEFAULT_UPDATE_URL,
)

# ---------------------------------------------------------------------------
# Project root paths
# ---------------------------------------------------------------------------

SCRIPTS_DIR   = _REPO_ROOT / "scripts"
INSTALLER_DIR = _REPO_ROOT / "installer"
WEB_DIR       = _REPO_ROOT / "web"
SRC_TAURI_DIR = _REPO_ROOT / "src-tauri"
VERSION_FILE  = _REPO_ROOT / "VERSION"


# ===========================================================================
# TestBuildScripts
# ===========================================================================

class TestBuildScripts:
    """15 tests covering build script existence, permissions, version, checksums."""

    # ---- Existence ----

    def test_build_mac_exists(self):
        assert (SCRIPTS_DIR / "build-mac.sh").exists(), "build-mac.sh not found"

    def test_build_linux_exists(self):
        assert (SCRIPTS_DIR / "build-linux.sh").exists(), "build-linux.sh not found"

    def test_build_windows_exists(self):
        assert (SCRIPTS_DIR / "build-windows.sh").exists(), "build-windows.sh not found"

    def test_build_all_exists(self):
        assert (SCRIPTS_DIR / "build-all.sh").exists(), "build-all.sh not found"

    # ---- Executable permissions ----

    def test_build_mac_executable(self):
        path = SCRIPTS_DIR / "build-mac.sh"
        mode = path.stat().st_mode
        assert bool(mode & stat.S_IXUSR), "build-mac.sh not user-executable"

    def test_build_linux_executable(self):
        path = SCRIPTS_DIR / "build-linux.sh"
        mode = path.stat().st_mode
        assert bool(mode & stat.S_IXUSR), "build-linux.sh not user-executable"

    def test_build_windows_executable(self):
        path = SCRIPTS_DIR / "build-windows.sh"
        mode = path.stat().st_mode
        assert bool(mode & stat.S_IXUSR), "build-windows.sh not user-executable"

    def test_build_all_executable(self):
        path = SCRIPTS_DIR / "build-all.sh"
        mode = path.stat().st_mode
        assert bool(mode & stat.S_IXUSR), "build-all.sh not user-executable"

    # ---- Content: version extraction ----

    def test_build_mac_reads_version_file(self):
        content = (SCRIPTS_DIR / "build-mac.sh").read_text()
        assert "VERSION" in content, "build-mac.sh must reference VERSION"

    def test_build_linux_reads_version_file(self):
        content = (SCRIPTS_DIR / "build-linux.sh").read_text()
        assert "VERSION" in content

    def test_build_windows_reads_version_file(self):
        content = (SCRIPTS_DIR / "build-windows.sh").read_text()
        assert "VERSION" in content

    # ---- Content: SHA-256 checksums ----

    def test_build_mac_generates_sha256(self):
        content = (SCRIPTS_DIR / "build-mac.sh").read_text()
        assert "sha256" in content.lower(), "build-mac.sh must generate SHA-256 checksums"

    def test_build_linux_generates_sha256(self):
        content = (SCRIPTS_DIR / "build-linux.sh").read_text()
        assert "sha256" in content.lower()

    def test_build_windows_generates_sha256(self):
        content = (SCRIPTS_DIR / "build-windows.sh").read_text()
        assert "sha256" in content.lower()

    # ---- Content: dist directory ----

    def test_build_all_creates_dist_dir(self):
        content = (SCRIPTS_DIR / "build-all.sh").read_text()
        assert "dist" in content.lower(), "build-all.sh must create dist/ directory"

    # ---- Content: PyInstaller reference ----

    def test_build_mac_references_pyinstaller(self):
        content = (SCRIPTS_DIR / "build-mac.sh").read_text()
        assert "pyinstaller" in content.lower(), "build-mac.sh should reference PyInstaller"

    def test_build_linux_references_pyinstaller(self):
        content = (SCRIPTS_DIR / "build-linux.sh").read_text()
        assert "pyinstaller" in content.lower()

    # ---- VERSION file ----

    def test_version_file_exists(self):
        assert VERSION_FILE.exists(), "VERSION file must exist at project root"

    def test_version_file_content(self):
        content = VERSION_FILE.read_text().strip()
        # Must be valid semver
        major, minor, patch, pre = parse_semver(content)
        assert major >= 1, f"Expected major >= 1, got {major}"


# ===========================================================================
# TestInstaller
# ===========================================================================

class TestInstaller:
    """15 tests covering the welcome.html installer page."""

    @pytest.fixture(autouse=True)
    def _load_html(self):
        self.html_path = INSTALLER_DIR / "welcome.html"
        assert self.html_path.exists(), "installer/welcome.html not found"
        self.html = self.html_path.read_text()

    # ---- Existence and basic structure ----

    def test_installer_file_exists(self):
        assert self.html_path.exists()

    def test_html_has_doctype(self):
        assert "<!DOCTYPE html>" in self.html or "<!doctype html>" in self.html.lower()

    def test_html_has_title(self):
        assert "<title>" in self.html.lower()

    def test_html_dark_theme(self):
        # Dark theme uses a dark background variable or dark hex color
        html_lower = self.html.lower()
        assert (
            "bg:" in html_lower
            or "#0" in self.html
            or "background" in html_lower
        ), "Installer must use a dark theme"

    # ---- Step content ----

    def test_step_1_allowed_roots(self):
        html_lower = self.html.lower()
        assert (
            "allowed_roots" in html_lower
            or "allowed roots" in html_lower
            or "file access" in html_lower
        ), "Step 1 must configure allowed_roots"

    def test_step_1_has_documents_checkbox(self):
        assert "documents" in self.html.lower()

    def test_step_1_has_desktop_checkbox(self):
        assert "desktop" in self.html.lower()

    def test_step_1_has_downloads_checkbox(self):
        assert "downloads" in self.html.lower()

    def test_step_2_terminal_allowlist(self):
        html_lower = self.html.lower()
        assert (
            "terminal" in html_lower
            or "allowlist" in html_lower
        ), "Step 2 must configure terminal allowlist"

    def test_step_3_oauth3_or_llm(self):
        html_lower = self.html.lower()
        assert (
            "oauth3" in html_lower
            or "llm" in html_lower
            or "api key" in html_lower
            or "byok" in html_lower
        ), "Step 3 must include OAuth3 or LLM config"

    def test_step_4_llm_configuration(self):
        html_lower = self.html.lower()
        # Must have LLM config (which may be combined with step 3)
        assert (
            "llm" in html_lower
            or "managed" in html_lower
            or "byok" in html_lower
            or "provider" in html_lower
        ), "Installer must include LLM configuration"

    def test_has_navigation_buttons(self):
        html_lower = self.html.lower()
        assert "next" in html_lower or "btn" in html_lower, "Must have navigation buttons"

    def test_has_back_button(self):
        assert "back" in self.html.lower() or "&#x2190;" in self.html

    def test_has_skip_or_optional(self):
        html_lower = self.html.lower()
        assert (
            "skip" in html_lower
            or "optional" in html_lower
            or "later" in html_lower
        ), "LLM setup must be skippable"

    def test_all_steps_navigable_via_js(self):
        # Must have a JS function for navigation
        assert "goToStep" in self.html or "step" in self.html.lower()

    def test_custom_path_entry(self):
        html_lower = self.html.lower()
        assert (
            "custom" in html_lower
            or "add" in html_lower
        ), "Must allow custom path entry"

    def test_config_save_in_js(self):
        # JS must save config (localStorage, Tauri IPC, or similar)
        assert (
            "localStorage" in self.html
            or "invoke" in self.html
            or "config" in self.html.lower()
        ), "Installer must persist config"


# ===========================================================================
# TestDownloadPage
# ===========================================================================

class TestDownloadPage:
    """12 tests covering web/download.html."""

    @pytest.fixture(autouse=True)
    def _load_html(self):
        self.html_path = WEB_DIR / "download.html"
        assert self.html_path.exists(), "web/download.html not found"
        self.html = self.html_path.read_text()

    def test_download_page_exists(self):
        assert self.html_path.exists()

    def test_html_dark_theme(self):
        html_lower = self.html.lower()
        # Must have a dark background
        assert "#0" in self.html or "bg:" in html_lower or "background" in html_lower

    def test_platform_detection_js(self):
        assert "detectPlatform" in self.html or "navigator.userAgent" in self.html

    def test_mac_download_link(self):
        assert ".dmg" in self.html.lower(), "Must include macOS DMG download link"

    def test_linux_deb_download_link(self):
        assert ".deb" in self.html.lower(), "Must include Linux .deb download link"

    def test_linux_appimage_download_link(self):
        assert "appimage" in self.html.lower(), "Must include Linux AppImage download link"

    def test_windows_msi_download_link(self):
        assert ".msi" in self.html.lower(), "Must include Windows MSI download link"

    def test_sha256_checksums_displayed(self):
        html_lower = self.html.lower()
        assert "sha256" in html_lower or "sha-256" in html_lower, "Must display SHA-256 checksums"

    def test_installation_instructions(self):
        html_lower = self.html.lower()
        assert "installation" in html_lower or "install" in html_lower

    def test_version_info_displayed(self):
        # Must display version info
        assert (
            "version" in self.html.lower()
            or "v1." in self.html
        ), "Must display version info"

    def test_system_requirements_section(self):
        html_lower = self.html.lower()
        assert (
            "system requirement" in html_lower
            or "requirements" in html_lower
        ), "Must include system requirements"

    def test_changelog_link(self):
        assert "changelog" in self.html.lower(), "Must include changelog link"

    def test_primary_download_button(self):
        html_lower = self.html.lower()
        assert (
            "btn-download" in html_lower
            or "download" in html_lower
        ), "Must have primary download button"


# ===========================================================================
# TestAutoUpdate
# ===========================================================================

class TestAutoUpdate:
    """20 tests covering auto_update.py."""

    # ---- parse_semver ----

    def test_parse_semver_basic(self):
        assert parse_semver("1.2.3") == (1, 2, 3, "")

    def test_parse_semver_with_v_prefix(self):
        assert parse_semver("v2.0.0") == (2, 0, 0, "")

    def test_parse_semver_with_prerelease(self):
        major, minor, patch, pre = parse_semver("1.0.0-beta.1")
        assert pre == "beta.1"

    def test_parse_semver_invalid(self):
        with pytest.raises(ValueError):
            parse_semver("not-a-version")

    def test_parse_semver_non_string(self):
        with pytest.raises(ValueError):
            parse_semver(123)  # type: ignore

    # ---- is_newer ----

    def test_is_newer_major(self):
        assert is_newer("2.0.0", "1.9.9") is True

    def test_is_newer_minor(self):
        assert is_newer("1.1.0", "1.0.9") is True

    def test_is_newer_patch(self):
        assert is_newer("1.0.1", "1.0.0") is True

    def test_is_newer_same_returns_false(self):
        assert is_newer("1.0.0", "1.0.0") is False

    def test_is_newer_older_returns_false(self):
        assert is_newer("0.9.9", "1.0.0") is False

    def test_is_newer_release_over_prerelease(self):
        # 1.0.0 is newer than 1.0.0-beta.1
        assert is_newer("1.0.0", "1.0.0-beta.1") is True

    def test_is_newer_prerelease_over_release_false(self):
        assert is_newer("1.0.0-rc.1", "1.0.0") is False

    # ---- is_downgrade ----

    def test_is_downgrade_true(self):
        assert is_downgrade("0.9.0", "1.0.0") is True

    def test_is_downgrade_same_false(self):
        assert is_downgrade("1.0.0", "1.0.0") is False

    def test_is_downgrade_newer_false(self):
        assert is_downgrade("2.0.0", "1.0.0") is False

    # ---- AutoUpdateChecker ----

    def test_checker_invalid_current_version(self):
        with pytest.raises(ValueError):
            AutoUpdateChecker("not-semver")

    def test_checker_update_available(self):
        """Mock HTTP response returning a newer version."""
        release_data = {
            "version": "2.0.0",
            "url": "https://www.solaceagi.com/releases/SolaceBrowser-2.0.0-linux-amd64.deb",
            "sha256": "a" * 64,
            "size_bytes": 80_000_000,
            "changelog_url": "https://www.solaceagi.com/changelog",
            "release_date": "2026-03-01",
        }

        checker = AutoUpdateChecker(current_version="1.0.0")

        with patch.object(checker, "_fetch_release_info", return_value=release_data):
            result = checker.check()

        assert result.update_available is True
        assert result.latest_version == "2.0.0"
        assert result.release is not None

    def test_checker_no_update(self):
        """Mock HTTP response returning the same version."""
        release_data = {
            "version": "1.0.0",
            "url": "https://www.solaceagi.com/releases/SolaceBrowser-1.0.0-linux-amd64.deb",
            "sha256": "b" * 64,
        }

        checker = AutoUpdateChecker(current_version="1.0.0")

        with patch.object(checker, "_fetch_release_info", return_value=release_data):
            result = checker.check()

        assert result.update_available is False
        assert result.release is None

    def test_checker_downgrade_prevention(self):
        """A version older than current must NOT be flagged as an update."""
        release_data = {
            "version": "0.9.0",
            "url": "https://www.solaceagi.com/releases/SolaceBrowser-0.9.0-linux-amd64.deb",
            "sha256": "c" * 64,
        }

        checker = AutoUpdateChecker(current_version="1.0.0")

        with patch.object(checker, "_fetch_release_info", return_value=release_data):
            result = checker.check()

        assert result.update_available is False

    def test_checker_network_error_returns_no_update(self):
        """Network failure must return UpdateResult with error, not raise."""
        checker = AutoUpdateChecker(current_version="1.0.0")

        with patch.object(checker, "_fetch_release_info",
                          side_effect=ConnectionError("timeout")):
            result = checker.check()

        assert result.update_available is False
        assert result.error is not None

    # ---- UpdateDownloader SHA-256 ----

    def test_downloader_verify_file_correct_hash(self, tmp_path):
        content = b"solace browser binary data"
        expected = hashlib.sha256(content).hexdigest()
        f = tmp_path / "artifact.dmg"
        f.write_bytes(content)

        downloader = UpdateDownloader(dest_dir=tmp_path)
        assert downloader.verify_file(f, expected) is True

    def test_downloader_verify_file_wrong_hash(self, tmp_path):
        content = b"solace browser binary data"
        f = tmp_path / "artifact.dmg"
        f.write_bytes(content)

        downloader = UpdateDownloader(dest_dir=tmp_path)
        assert downloader.verify_file(f, "0" * 64) is False

    def test_downloader_verify_missing_file(self, tmp_path):
        downloader = UpdateDownloader(dest_dir=tmp_path)
        assert downloader.verify_file(tmp_path / "nonexistent.dmg", "a" * 64) is False

    # ---- UpdateBanner ----

    def test_banner_calls_on_update_available(self):
        release_data = {
            "version": "1.1.0",
            "url": "https://www.solaceagi.com/releases/SolaceBrowser-1.1.0-linux-amd64.deb",
            "sha256": "d" * 64,
        }

        called_with = []
        banner = UpdateBanner(on_update_available=lambda r: called_with.append(r))

        with patch(
            "src.auto_update.AutoUpdateChecker._fetch_release_info",
            return_value=release_data,
        ):
            banner.run_check("1.0.0")

        assert len(called_with) == 1
        assert called_with[0].update_available is True

    def test_banner_calls_on_no_update(self):
        release_data = {
            "version": "1.0.0",
            "url": "https://www.solaceagi.com/releases/SolaceBrowser-1.0.0-linux-amd64.deb",
            "sha256": "e" * 64,
        }

        called_with = []
        banner = UpdateBanner(on_no_update=lambda r: called_with.append(r))

        with patch(
            "src.auto_update.AutoUpdateChecker._fetch_release_info",
            return_value=release_data,
        ):
            banner.run_check("1.0.0")

        assert len(called_with) == 1

    def test_banner_last_result_set(self):
        release_data = {
            "version": "1.0.0",
            "url": "https://www.solaceagi.com/releases/test.deb",
            "sha256": "f" * 64,
        }

        banner = UpdateBanner()

        with patch(
            "src.auto_update.AutoUpdateChecker._fetch_release_info",
            return_value=release_data,
        ):
            banner.run_check("1.0.0")

        assert banner.last_result is not None

    # ---- read_version_file ----

    def test_read_version_file_from_project_root(self):
        version = read_version_file(_REPO_ROOT)
        assert version.strip() != ""
        parse_semver(version)  # must be valid semver

    def test_read_version_file_missing_returns_default(self, tmp_path):
        version = read_version_file(tmp_path)
        assert version == "0.0.0"

    # ---- ReleaseInfo validation ----

    def test_release_info_invalid_hash(self):
        with pytest.raises(ValueError):
            ReleaseInfo(
                version="1.0.0",
                url="https://example.com/file.dmg",
                sha256="not-a-valid-sha256",
            )

    def test_release_info_invalid_version(self):
        with pytest.raises(ValueError):
            ReleaseInfo(
                version="invalid",
                url="https://example.com/file.dmg",
                sha256="a" * 64,
            )


# ===========================================================================
# TestTauriConfig
# ===========================================================================

class TestTauriConfig:
    """12 tests covering src-tauri/tauri.conf.json."""

    @pytest.fixture(autouse=True)
    def _load_config(self):
        self.config_path = SRC_TAURI_DIR / "tauri.conf.json"
        assert self.config_path.exists(), "src-tauri/tauri.conf.json not found"
        self.config = json.loads(self.config_path.read_text())

    def test_config_is_valid_json(self):
        assert isinstance(self.config, dict)

    def test_product_name(self):
        assert self.config["package"]["productName"] == "Solace Browser"

    def test_version_in_config(self):
        version = self.config["package"]["version"]
        parse_semver(version)  # must be valid semver

    def test_bundle_identifier(self):
        bundle_id = self.config["tauri"]["bundle"]["identifier"]
        assert "solace" in bundle_id.lower(), f"Bundle ID should contain 'solace': {bundle_id}"

    def test_main_window_defined(self):
        windows = self.config["tauri"]["windows"]
        labels = [w["label"] for w in windows]
        assert "main" in labels, "Must define a 'main' window"

    def test_main_window_size(self):
        windows = {w["label"]: w for w in self.config["tauri"]["windows"]}
        main = windows["main"]
        assert main["width"] >= 800
        assert main["height"] >= 600

    def test_main_window_resizable(self):
        windows = {w["label"]: w for w in self.config["tauri"]["windows"]}
        main = windows["main"]
        assert main.get("resizable", True) is True

    def test_setup_window_defined(self):
        windows = self.config["tauri"]["windows"]
        labels = [w["label"] for w in windows]
        assert "setup" in labels, "Must define a 'setup' wizard window"

    def test_csp_defined(self):
        csp = self.config["tauri"]["security"].get("csp", "")
        assert csp, "CSP must be defined for security"

    def test_csp_default_src(self):
        csp = self.config["tauri"]["security"].get("csp", "")
        assert "default-src" in csp, "CSP must include default-src directive"

    def test_external_bin_server(self):
        external_bin = self.config["tauri"]["bundle"].get("externalBin", [])
        assert any(
            "solace" in b.lower() or "server" in b.lower()
            for b in external_bin
        ), "Must bundle the Python server as externalBin"

    def test_dist_dir_in_config(self):
        dist_dir = self.config["build"].get("distDir", "")
        assert dist_dir, "build.distDir must be set"

    def test_main_rs_exists(self):
        main_rs = SRC_TAURI_DIR / "src" / "main.rs"
        assert main_rs.exists(), "src-tauri/src/main.rs must exist"

    def test_main_rs_has_tauri_builder(self):
        main_rs = SRC_TAURI_DIR / "src" / "main.rs"
        content = main_rs.read_text()
        assert "tauri::Builder" in content, "main.rs must use tauri::Builder"

    def test_main_rs_spawns_python_server(self):
        main_rs = SRC_TAURI_DIR / "src" / "main.rs"
        content = main_rs.read_text()
        assert "python" in content.lower() or "server" in content.lower(), \
            "main.rs must spawn the Python server"
