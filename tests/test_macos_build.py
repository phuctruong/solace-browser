"""
Solace Browser — macOS Build Spec Validation Test Suite
Rung: 641 (local correctness)

Coverage:
  TestMacOSSpecFile       (10 tests) — file existence, parsing, macOS-specific fields
  TestMacOSSpecContent    (10 tests) — hidden imports, exclusions, data bundles, info_plist
  TestBuildMacScript      (13 tests) — script content, platform detection, GCS upload, SHA-256, fallback ban

Total: 33 tests
Run:
    cd /home/phuc/projects/solace-browser
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_macos_build.py -v --tb=short
"""

from __future__ import annotations

import ast
import os
import stat
import sys
import textwrap
from pathlib import Path

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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

MACOS_SPEC_FILE = _REPO_ROOT / "solace-browser-macos.spec"
LINUX_SPEC_FILE = _REPO_ROOT / "solace-browser.spec"
BUILD_MAC_SCRIPT = _REPO_ROOT / "scripts" / "build-mac.sh"
VERSION_FILE = _REPO_ROOT / "VERSION"


# ---------------------------------------------------------------------------
# Helper: parse the .spec file as Python AST
# ---------------------------------------------------------------------------

def _parse_spec_ast(spec_path: Path) -> ast.Module:
    """Parse a PyInstaller .spec file as a Python AST module."""
    source = spec_path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(spec_path))


def _find_call_by_func_name(tree: ast.Module, func_name: str) -> ast.Call | None:
    """Find the first Call node in the AST whose func is `func_name`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == func_name:
                return node
    return None


def _get_keyword_value(call: ast.Call, keyword: str) -> ast.expr | None:
    """Extract the value of a keyword argument from a Call node."""
    for kw in call.keywords:
        if kw.arg == keyword:
            return kw.value
    return None


def _ast_to_python(node: ast.expr):
    """Evaluate a simple AST literal node to a Python value."""
    return ast.literal_eval(node)


# ===========================================================================
# TestMacOSSpecFile — file-level and structural validation
# ===========================================================================

class TestMacOSSpecFile:
    """10 tests: spec file exists, is valid Python, has required top-level calls."""

    def test_spec_file_exists(self):
        assert MACOS_SPEC_FILE.exists(), f"macOS spec file not found: {MACOS_SPEC_FILE}"

    def test_spec_file_is_valid_python(self):
        """The .spec file must parse as valid Python."""
        tree = _parse_spec_ast(MACOS_SPEC_FILE)
        assert isinstance(tree, ast.Module)

    def test_spec_has_analysis_call(self):
        tree = _parse_spec_ast(MACOS_SPEC_FILE)
        call = _find_call_by_func_name(tree, "Analysis")
        assert call is not None, "spec must contain an Analysis() call"

    def test_spec_has_pyz_call(self):
        tree = _parse_spec_ast(MACOS_SPEC_FILE)
        call = _find_call_by_func_name(tree, "PYZ")
        assert call is not None, "spec must contain a PYZ() call"

    def test_spec_has_exe_call(self):
        tree = _parse_spec_ast(MACOS_SPEC_FILE)
        call = _find_call_by_func_name(tree, "EXE")
        assert call is not None, "spec must contain an EXE() call"

    def test_spec_entry_point_is_server(self):
        """Analysis must point to solace_browser_server.py as entry point."""
        tree = _parse_spec_ast(MACOS_SPEC_FILE)
        call = _find_call_by_func_name(tree, "Analysis")
        assert call is not None
        # First positional arg is a list of entry scripts
        first_arg = call.args[0]
        scripts = _ast_to_python(first_arg)
        assert "solace_browser_server.py" in scripts

    def test_spec_binary_name_is_solace_browser(self):
        tree = _parse_spec_ast(MACOS_SPEC_FILE)
        call = _find_call_by_func_name(tree, "EXE")
        assert call is not None
        name_val = _get_keyword_value(call, "name")
        assert name_val is not None
        assert _ast_to_python(name_val) == "solace-browser"

    def test_linux_spec_not_modified(self):
        """The Linux spec file must still exist and not be the same as macOS spec."""
        assert LINUX_SPEC_FILE.exists(), "Linux spec must not be deleted"
        linux_content = LINUX_SPEC_FILE.read_text(encoding="utf-8")
        macos_content = MACOS_SPEC_FILE.read_text(encoding="utf-8")
        assert linux_content != macos_content, "macOS spec must differ from Linux spec"

    def test_spec_has_comment_header(self):
        content = MACOS_SPEC_FILE.read_text(encoding="utf-8")
        assert "macos" in content.lower(), "spec file should mention macOS in comments"

    def test_spec_mentions_universal(self):
        content = MACOS_SPEC_FILE.read_text(encoding="utf-8")
        assert "universal" in content.lower(), "spec should reference universal binary"


# ===========================================================================
# TestMacOSSpecContent — macOS-specific fields and values
# ===========================================================================

class TestMacOSSpecContent:
    """10 tests: codesign, target_arch, info_plist, hidden imports, exclusions."""

    @pytest.fixture(autouse=True)
    def _load_spec(self):
        self.tree = _parse_spec_ast(MACOS_SPEC_FILE)
        self.exe_call = _find_call_by_func_name(self.tree, "EXE")
        assert self.exe_call is not None
        self.analysis_call = _find_call_by_func_name(self.tree, "Analysis")
        assert self.analysis_call is not None

    def test_codesign_identity_adhoc(self):
        """codesign_identity must be '-' for ad-hoc signing."""
        val = _get_keyword_value(self.exe_call, "codesign_identity")
        assert val is not None, "EXE must have codesign_identity keyword"
        assert _ast_to_python(val) == "-"

    def test_target_arch_universal2(self):
        """target_arch must be 'universal2' for x86_64 + arm64."""
        val = _get_keyword_value(self.exe_call, "target_arch")
        assert val is not None, "EXE must have target_arch keyword"
        assert _ast_to_python(val) == "universal2"

    def test_info_plist_present(self):
        """EXE must include an info_plist dict."""
        val = _get_keyword_value(self.exe_call, "info_plist")
        assert val is not None, "EXE must have info_plist keyword"
        plist = _ast_to_python(val)
        assert isinstance(plist, dict)

    def test_info_plist_bundle_name(self):
        val = _get_keyword_value(self.exe_call, "info_plist")
        plist = _ast_to_python(val)
        assert "CFBundleName" in plist
        assert plist["CFBundleName"] == "Solace Browser"

    def test_info_plist_bundle_identifier(self):
        val = _get_keyword_value(self.exe_call, "info_plist")
        plist = _ast_to_python(val)
        assert plist.get("CFBundleIdentifier") == "com.solaceagi.browser"

    def test_info_plist_bundle_version(self):
        val = _get_keyword_value(self.exe_call, "info_plist")
        plist = _ast_to_python(val)
        assert "CFBundleVersion" in plist
        # Must be a semver-like string
        version = plist["CFBundleVersion"]
        parts = version.split(".")
        assert len(parts) >= 2, f"CFBundleVersion must be semver-like: {version}"

    def test_info_plist_minimum_system_version(self):
        val = _get_keyword_value(self.exe_call, "info_plist")
        plist = _ast_to_python(val)
        min_ver = plist.get("LSMinimumSystemVersion", "")
        assert min_ver, "LSMinimumSystemVersion must be set"
        major = int(min_ver.split(".")[0])
        assert major >= 11, f"Minimum macOS version should be 11+ (Big Sur), got {min_ver}"

    def test_hidden_imports_match_linux(self):
        """macOS spec must include at least all hidden imports from the Linux spec."""
        linux_tree = _parse_spec_ast(LINUX_SPEC_FILE)
        linux_analysis = _find_call_by_func_name(linux_tree, "Analysis")
        assert linux_analysis is not None

        linux_imports_node = _get_keyword_value(linux_analysis, "hiddenimports")
        macos_imports_node = _get_keyword_value(self.analysis_call, "hiddenimports")

        assert linux_imports_node is not None
        assert macos_imports_node is not None

        linux_imports = set(_ast_to_python(linux_imports_node))
        macos_imports = set(_ast_to_python(macos_imports_node))

        missing = linux_imports - macos_imports
        assert not missing, f"macOS spec missing hidden imports from Linux: {missing}"

    def test_excludes_linux_modules(self):
        """macOS spec should exclude Linux-specific modules."""
        excludes_node = _get_keyword_value(self.analysis_call, "excludes")
        assert excludes_node is not None
        excludes = _ast_to_python(excludes_node)
        # Must exclude at least some Linux-specific modules beyond what Linux spec excludes
        linux_tree = _parse_spec_ast(LINUX_SPEC_FILE)
        linux_analysis = _find_call_by_func_name(linux_tree, "Analysis")
        linux_excludes_node = _get_keyword_value(linux_analysis, "excludes")
        linux_excludes = set(_ast_to_python(linux_excludes_node)) if linux_excludes_node else set()
        macos_excludes = set(excludes)
        extra_excludes = macos_excludes - linux_excludes
        assert len(extra_excludes) > 0, (
            "macOS spec should exclude additional Linux-specific modules "
            f"(e.g. systemd, dbus). Got same excludes as Linux: {macos_excludes}"
        )

    def test_datas_include_web_static_data(self):
        """Analysis datas must bundle web/, static/, and data/ directories."""
        datas_node = _get_keyword_value(self.analysis_call, "datas")
        assert datas_node is not None
        datas = _ast_to_python(datas_node)
        bundled_sources = {d[0] for d in datas}
        for required in ("web", "static", "data"):
            assert required in bundled_sources, f"datas must include '{required}' directory"


# ===========================================================================
# TestBuildMacScript — build-mac.sh content validation
# ===========================================================================

class TestBuildMacScript:
    """13 tests: script structure, platform detection, GCS upload, SHA-256, fallback ban."""

    @pytest.fixture(autouse=True)
    def _load_script(self):
        assert BUILD_MAC_SCRIPT.exists(), f"build-mac.sh not found: {BUILD_MAC_SCRIPT}"
        self.content = BUILD_MAC_SCRIPT.read_text(encoding="utf-8")

    def test_script_exists(self):
        assert BUILD_MAC_SCRIPT.exists()

    def test_script_is_executable(self):
        mode = BUILD_MAC_SCRIPT.stat().st_mode
        assert bool(mode & stat.S_IXUSR), "build-mac.sh must be user-executable"

    def test_script_has_shebang(self):
        assert self.content.startswith("#!/"), "build-mac.sh must start with a shebang line"

    def test_script_uses_strict_mode(self):
        assert "set -euo pipefail" in self.content, "Must use strict bash mode"

    def test_script_detects_macos_platform(self):
        """Script must check uname and reject non-Darwin platforms."""
        assert "uname" in self.content, "Must use uname for platform detection"
        assert "Darwin" in self.content, "Must check for Darwin (macOS)"

    def test_script_uses_macos_spec_file(self):
        """Script must reference the macOS-specific spec file."""
        assert "solace-browser-macos.spec" in self.content, \
            "Must use solace-browser-macos.spec (not the Linux spec)"

    def test_script_generates_sha256(self):
        assert "sha256" in self.content.lower(), "Must generate SHA-256 checksum"

    def test_script_references_gcs_bucket(self):
        assert "gs://solace-downloads" in self.content, \
            "Must reference GCS upload bucket"

    def test_script_references_universal_binary(self):
        assert "universal" in self.content.lower(), \
            "Must reference universal binary in output naming"

    def test_script_reads_version_file(self):
        assert "VERSION" in self.content, "Must read VERSION file for version string"

    def test_script_no_fallback_ban_violations(self):
        """build-mac.sh must not silently swallow errors."""
        # These patterns indicate silent error swallowing
        banned_patterns = ["|| true", "|| :", "set +e"]
        for pattern in banned_patterns:
            assert pattern not in self.content, (
                f"FALLBACK BAN violation: '{pattern}' found in build-mac.sh"
            )

    def test_script_verifies_sha256(self):
        """SHA-256 must be verified after generation, not just created."""
        # Must contain verification command (shasum -c or sha256sum -c)
        assert "-c" in self.content and "sha256" in self.content.lower(), (
            "build-mac.sh must verify SHA-256 checksum after generation (shasum -c)"
        )

    def test_script_verifies_universal_binary(self):
        """Script must verify the binary contains both architectures."""
        assert "lipo" in self.content, (
            "build-mac.sh must use lipo to verify universal2 binary architectures"
        )
