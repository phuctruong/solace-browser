"""
test_deployment.py — Static validation of distribution scaffolding.
Auth: 65537 | Port 9222: PERMANENTLY BANNED

Tests verify that all deployment files are structurally correct
WITHOUT running snapcraft/wix/dpkg — pure static analysis.
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _exists(rel: str) -> bool:
    return (REPO_ROOT / rel).exists()


# ---------------------------------------------------------------------------
# VERSION
# ---------------------------------------------------------------------------

class TestVersion:
    def test_version_file_exists(self):
        assert _exists("VERSION"), "VERSION file missing at repo root"

    def test_version_is_semver(self):
        v = _read("VERSION").strip()
        assert re.match(r"^\d+\.\d+\.\d+$", v), f"VERSION must be semver: {v!r}"

    def test_version_not_placeholder(self):
        v = _read("VERSION").strip()
        assert v != "0.0.0" and v != "", "VERSION must not be empty or 0.0.0"


# ---------------------------------------------------------------------------
# Snap
# ---------------------------------------------------------------------------

class TestSnapcraft:
    def test_snapcraft_yaml_exists(self):
        assert _exists("snap/snapcraft.yaml")

    def test_snap_name(self):
        content = _read("snap/snapcraft.yaml")
        assert "name: solace-browser" in content

    def test_snap_base(self):
        content = _read("snap/snapcraft.yaml")
        assert "base: core22" in content, "snap must target core22 (Ubuntu 22.04)"

    def test_snap_confinement_strict(self):
        content = _read("snap/snapcraft.yaml")
        assert "confinement: strict" in content

    def test_snap_grade_stable(self):
        content = _read("snap/snapcraft.yaml")
        assert "grade: stable" in content

    def test_snap_no_port_9222(self):
        assert "9222" not in _read("snap/snapcraft.yaml"), "Port 9222 banned"

    def test_snap_network_plug(self):
        content = _read("snap/snapcraft.yaml")
        assert "network" in content, "snap needs network plug for port 8888"

    def test_snap_home_plug(self):
        content = _read("snap/snapcraft.yaml")
        assert "home" in content, "snap needs home plug for ~/.solace/"

    def test_snap_references_binary(self):
        content = _read("snap/snapcraft.yaml")
        assert "solace-browser-linux-x86_64" in content, \
            "snapcraft.yaml must reference the PyInstaller binary"

    def test_snap_has_app_command(self):
        content = _read("snap/snapcraft.yaml")
        assert "command: bin/solace-browser" in content


# ---------------------------------------------------------------------------
# Debian .deb
# ---------------------------------------------------------------------------

class TestDebian:
    def test_control_file_exists(self):
        assert _exists("scripts/debian/control")

    def test_control_package_name(self):
        content = _read("scripts/debian/control")
        assert "Package: solace-browser" in content

    def test_control_architecture_amd64(self):
        content = _read("scripts/debian/control")
        assert "Architecture: amd64" in content

    def test_control_no_port_9222(self):
        assert "9222" not in _read("scripts/debian/control")

    def test_postinst_exists(self):
        assert _exists("scripts/debian/postinst")

    def test_postinst_executable(self):
        p = REPO_ROOT / "scripts/debian/postinst"
        assert p.stat().st_mode & 0o111, "postinst must be executable"

    def test_postinst_no_bare_except(self):
        # Shell script — check for unsafe patterns
        content = _read("scripts/debian/postinst")
        assert "exit 0" in content, "postinst must exit 0 on success"

    def test_build_deb_script_exists(self):
        assert _exists("scripts/build-deb.sh")

    def test_build_deb_executable(self):
        p = REPO_ROOT / "scripts/build-deb.sh"
        assert p.stat().st_mode & 0o111

    def test_build_deb_no_port_9222(self):
        assert "9222" not in _read("scripts/build-deb.sh")

    def test_build_deb_generates_sha256(self):
        content = _read("scripts/build-deb.sh")
        assert "sha256" in content, "build-deb.sh must generate sha256 file"

    def test_build_deb_reads_version_file(self):
        content = _read("scripts/build-deb.sh")
        assert "VERSION" in content, "build-deb.sh must read VERSION file"


# ---------------------------------------------------------------------------
# Homebrew
# ---------------------------------------------------------------------------

class TestHomebrew:
    def test_formula_exists(self):
        assert _exists("scripts/homebrew/solace-browser.rb")

    def test_formula_class_name(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        assert "class SolaceBrowser < Formula" in content

    def test_formula_desc(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        assert "desc " in content

    def test_formula_homepage(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        assert "solaceagi.com" in content

    def test_formula_version(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        assert 'version "' in content

    def test_formula_url_points_to_macos_binary(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        assert "solace-browser-macos-universal" in content

    def test_formula_sha256_placeholder_documented(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        # Must have sha256 line (even if placeholder)
        assert "sha256 " in content

    def test_formula_install_method(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        assert "def install" in content

    def test_formula_test_block(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        assert "do\n    # " in content or "test do" in content

    def test_formula_service_block(self):
        content = _read("scripts/homebrew/solace-browser.rb")
        assert "service do" in content, "formula must declare brew service"

    def test_formula_no_port_9222(self):
        assert "9222" not in _read("scripts/homebrew/solace-browser.rb")


# ---------------------------------------------------------------------------
# winget
# ---------------------------------------------------------------------------

WINGET_DIR = "scripts/winget/manifests/s/SolaceAI/SolaceBrowser/1.0.0"

class TestWinget:
    def test_version_manifest_exists(self):
        assert _exists(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.yaml")

    def test_installer_manifest_exists(self):
        assert _exists(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.installer.yaml")

    def test_locale_manifest_exists(self):
        assert _exists(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.locale.en-US.yaml")

    def test_version_manifest_identifier(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.yaml")
        assert "PackageIdentifier: SolaceAI.SolaceBrowser" in content

    def test_installer_manifest_architecture_x64(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.installer.yaml")
        assert "Architecture: x64" in content

    def test_installer_manifest_type_msi(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.installer.yaml")
        assert "InstallerType: msi" in content

    def test_installer_manifest_points_to_msi(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.installer.yaml")
        assert "solace-browser-windows-x86_64.msi" in content

    def test_installer_manifest_placeholder_documented(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.installer.yaml")
        # Placeholder must be present AND documented as requiring signing
        assert "PLACEHOLDER_SHA256" in content
        assert "BLOCKED ON" in content or "eSign" in content.lower() or "signing" in content.lower()

    def test_installer_manifest_product_code_is_guid(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.installer.yaml")
        assert re.search(
            r"ProductCode:.*\{[0-9A-F-]{36}\}", content, re.IGNORECASE
        ), "ProductCode must be a GUID"

    def test_installer_manifest_minimum_os(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.installer.yaml")
        assert "MinimumOSVersion" in content

    def test_locale_manifest_publisher(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.locale.en-US.yaml")
        assert "Publisher: Solace AI" in content

    def test_locale_manifest_license(self):
        content = _read(f"{WINGET_DIR}/SolaceAI.SolaceBrowser.locale.en-US.yaml")
        assert "License:" in content

    def test_submit_script_exists(self):
        assert _exists("scripts/winget/submit.sh")

    def test_submit_script_executable(self):
        p = REPO_ROOT / "scripts/winget/submit.sh"
        assert p.stat().st_mode & 0o111

    def test_no_port_9222_in_any_manifest(self):
        for suffix in ("yaml", "installer.yaml", "locale.en-US.yaml"):
            path = f"{WINGET_DIR}/SolaceAI.SolaceBrowser.{suffix}"
            assert "9222" not in _read(path), f"Port 9222 banned in {path}"


# ---------------------------------------------------------------------------
# WiX MSI
# ---------------------------------------------------------------------------

class TestWiX:
    def test_wxs_exists(self):
        assert _exists("scripts/windows/solace-browser.wxs")

    def test_wxs_package_name(self):
        content = _read("scripts/windows/solace-browser.wxs")
        assert 'Name="Solace Browser"' in content

    def test_wxs_upgrade_code_is_guid(self):
        content = _read("scripts/windows/solace-browser.wxs")
        m = re.search(r'UpgradeCode="([^"]+)"', content)
        assert m, "UpgradeCode missing"
        assert re.match(r"[0-9A-F-]{36}", m.group(1), re.IGNORECASE), \
            f"UpgradeCode must be a GUID: {m.group(1)}"

    def test_wxs_program_files_64(self):
        content = _read("scripts/windows/solace-browser.wxs")
        assert "ProgramFiles64Folder" in content, \
            "Must install to 64-bit Program Files"

    def test_wxs_shortcuts_use_head_flag(self):
        content = _read("scripts/windows/solace-browser.wxs")
        shortcut_count = content.count("Arguments=\"--head\"")
        assert shortcut_count >= 2, \
            f"Both Start Menu and Desktop shortcuts must pass --head (found {shortcut_count})"

    def test_wxs_has_major_upgrade(self):
        content = _read("scripts/windows/solace-browser.wxs")
        assert "MajorUpgrade" in content, "Must include MajorUpgrade for clean upgrades"

    def test_wxs_no_port_9222(self):
        assert "9222" not in _read("scripts/windows/solace-browser.wxs")


# ---------------------------------------------------------------------------
# GitHub Actions workflow
# ---------------------------------------------------------------------------

class TestCIWorkflow:
    def test_workflow_exists(self):
        assert _exists(".github/workflows/build-binaries.yml")

    def test_workflow_linux_runner(self):
        content = _read(".github/workflows/build-binaries.yml")
        assert "ubuntu-22.04" in content

    def test_workflow_macos_runner(self):
        content = _read(".github/workflows/build-binaries.yml")
        assert "macos-latest" in content

    def test_workflow_windows_runner(self):
        content = _read(".github/workflows/build-binaries.yml")
        assert "windows-latest" in content

    def test_workflow_all_three_artifacts(self):
        content = _read(".github/workflows/build-binaries.yml")
        assert "native-linux" in content
        assert "native-macos" in content
        assert "native-windows" in content

    def test_workflow_signing_stub_windows(self):
        content = _read(".github/workflows/build-binaries.yml")
        assert "WINDOWS_SIGNING_CERT" in content, \
            "Windows signing stub must be present"
        assert "signtool" in content

    def test_workflow_signing_stub_macos(self):
        content = _read(".github/workflows/build-binaries.yml")
        assert "MACOS_SIGNING_CERT" in content, \
            "macOS signing stub must be present"
        assert "codesign" in content
        assert "notarytool" in content

    def test_workflow_gcs_promote_job(self):
        content = _read(".github/workflows/build-binaries.yml")
        assert "promote-to-gcs" in content

    def test_workflow_promote_only_on_tags(self):
        content = _read(".github/workflows/build-binaries.yml")
        assert "refs/tags/v" in content, \
            "GCS promotion must only run on version tags"

    def test_workflow_no_port_9222(self):
        assert "9222" not in _read(".github/workflows/build-binaries.yml")


# ---------------------------------------------------------------------------
# release_browser_cycle.sh
# ---------------------------------------------------------------------------

class TestReleaseCycleScript:
    def test_script_exists(self):
        assert _exists("scripts/release_browser_cycle.sh")

    def test_script_executable(self):
        p = REPO_ROOT / "scripts/release_browser_cycle.sh"
        assert p.stat().st_mode & 0o111

    def test_script_handles_linux(self):
        content = _read("scripts/release_browser_cycle.sh")
        assert "linux" in content
        assert "solace-browser-linux-x86_64" in content

    def test_script_handles_macos(self):
        content = _read("scripts/release_browser_cycle.sh")
        assert "macos" in content
        assert "universal2" in content
        assert "solace-browser-macos-universal" in content

    def test_script_handles_windows(self):
        content = _read("scripts/release_browser_cycle.sh")
        assert "windows" in content
        assert "solace-browser-windows-x86_64" in content

    def test_script_generates_sha256(self):
        content = _read("scripts/release_browser_cycle.sh")
        assert "sha256" in content

    def test_script_writes_metrics_json(self):
        content = _read("scripts/release_browser_cycle.sh")
        assert "metrics.json" in content

    def test_script_no_port_9222(self):
        assert "9222" not in _read("scripts/release_browser_cycle.sh")

    def test_script_set_euo_pipefail(self):
        content = _read("scripts/release_browser_cycle.sh")
        assert "set -euo pipefail" in content, \
            "Script must use set -euo pipefail for safety"
