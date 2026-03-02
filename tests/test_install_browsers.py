"""Tests for the Playwright browser auto-installer.

Tests cover:
  - Platform detection (Linux, macOS, Windows, unsupported)
  - Browser filtering per platform
  - Subprocess command construction
  - Installation success/failure/timeout paths
  - Verification logic
  - Progress indicator output
  - CLI argument parsing
  - End-to-end install_browsers() with mocked subprocess
  - Dry-run mode
  - System deps installation

All subprocess calls are mocked — no actual browser downloads occur.

Auth: 65537 | Rung: 641
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup — ensure scripts/ is importable
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from install_browsers import (
    PLATFORM_BROWSER_SUPPORT,
    SUPPORTED_BROWSERS,
    BrowserInstallResult,
    InstallReport,
    InstallStatus,
    ProgressIndicator,
    build_install_command,
    build_install_deps_command,
    detect_platform,
    filter_browsers,
    find_playwright_cli,
    get_supported_browsers,
    install_browsers,
    main,
    parse_args,
    run_browser_install,
    verify_all_browsers,
    verify_browser_installed,
)


# ===========================================================================
# Platform detection tests
# ===========================================================================

class TestDetectPlatform:
    """Tests for detect_platform()."""

    @patch("install_browsers.platform")
    def test_linux_detected(self, mock_platform: MagicMock) -> None:
        mock_platform.system.return_value = "Linux"
        assert detect_platform() == "Linux"

    @patch("install_browsers.platform")
    def test_darwin_detected(self, mock_platform: MagicMock) -> None:
        mock_platform.system.return_value = "Darwin"
        assert detect_platform() == "Darwin"

    @patch("install_browsers.platform")
    def test_windows_detected(self, mock_platform: MagicMock) -> None:
        mock_platform.system.return_value = "Windows"
        assert detect_platform() == "Windows"

    @patch("install_browsers.platform")
    def test_unsupported_platform_raises(self, mock_platform: MagicMock) -> None:
        mock_platform.system.return_value = "FreeBSD"
        with pytest.raises(RuntimeError, match="Unsupported platform.*FreeBSD"):
            detect_platform()


# ===========================================================================
# Browser support tests
# ===========================================================================

class TestGetSupportedBrowsers:
    """Tests for get_supported_browsers()."""

    def test_linux_has_all_three(self) -> None:
        result = get_supported_browsers("Linux")
        assert result == ["chromium", "firefox", "webkit"]

    def test_darwin_has_all_three(self) -> None:
        result = get_supported_browsers("Darwin")
        assert result == ["chromium", "firefox", "webkit"]

    def test_windows_no_webkit(self) -> None:
        result = get_supported_browsers("Windows")
        assert "webkit" not in result
        assert "chromium" in result
        assert "firefox" in result

    def test_unknown_platform_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown platform.*Solaris"):
            get_supported_browsers("Solaris")

    def test_returns_copy_not_reference(self) -> None:
        """Ensure modification of result does not affect the source."""
        result = get_supported_browsers("Linux")
        result.append("custom-browser")
        assert "custom-browser" not in PLATFORM_BROWSER_SUPPORT["Linux"]


class TestFilterBrowsers:
    """Tests for filter_browsers()."""

    def test_all_supported(self) -> None:
        installable, skipped = filter_browsers(
            ["chromium", "firefox"], "Linux"
        )
        assert installable == ["chromium", "firefox"]
        assert skipped == []

    def test_webkit_skipped_on_windows(self) -> None:
        installable, skipped = filter_browsers(
            ["chromium", "webkit"], "Windows"
        )
        assert installable == ["chromium"]
        assert skipped == ["webkit"]

    def test_empty_list(self) -> None:
        installable, skipped = filter_browsers([], "Linux")
        assert installable == []
        assert skipped == []


# ===========================================================================
# Command construction tests
# ===========================================================================

class TestBuildInstallCommand:
    """Tests for build_install_command()."""

    def test_chromium_command(self) -> None:
        cmd = build_install_command("chromium")
        assert cmd == [sys.executable, "-m", "playwright", "install", "chromium"]

    def test_firefox_command(self) -> None:
        cmd = build_install_command("firefox")
        assert cmd[-1] == "firefox"

    def test_webkit_command(self) -> None:
        cmd = build_install_command("webkit")
        assert cmd[-1] == "webkit"

    def test_invalid_browser_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown browser.*opera"):
            build_install_command("opera")


class TestBuildInstallDepsCommand:
    """Tests for build_install_deps_command()."""

    def test_deps_command_structure(self) -> None:
        cmd = build_install_deps_command("chromium")
        assert cmd == [
            sys.executable, "-m", "playwright", "install-deps", "chromium"
        ]


# ===========================================================================
# Browser installation tests (subprocess mocked)
# ===========================================================================

class TestRunBrowserInstall:
    """Tests for run_browser_install()."""

    @patch("install_browsers.subprocess.run")
    def test_successful_install(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Downloading chromium...\nDone\n", stderr=""
        )
        result = run_browser_install("chromium")
        assert result.status == InstallStatus.SUCCESS
        assert result.browser == "chromium"
        assert result.duration_seconds >= 0.0
        mock_run.assert_called_once()

    @patch("install_browsers.subprocess.run")
    def test_failed_install_nonzero_exit(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="ERROR: network failure"
        )
        result = run_browser_install("firefox")
        assert result.status == InstallStatus.FAILED
        assert "network failure" in result.message

    @patch("install_browsers.subprocess.run")
    def test_timeout_during_install(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="playwright install chromium", timeout=600
        )
        result = run_browser_install("chromium", timeout_seconds=600)
        assert result.status == InstallStatus.FAILED
        assert "timed out" in result.message

    @patch("install_browsers.subprocess.run")
    def test_file_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("No such file")
        result = run_browser_install("chromium")
        assert result.status == InstallStatus.FAILED
        assert "not found" in result.message

    @patch("install_browsers.subprocess.run")
    def test_os_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("Permission denied")
        result = run_browser_install("chromium")
        assert result.status == InstallStatus.FAILED
        assert "OS error" in result.message

    @patch("install_browsers.subprocess.run")
    def test_progress_indicator_called(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        progress = MagicMock(spec=ProgressIndicator)
        result = run_browser_install("chromium", progress=progress)
        assert result.status == InstallStatus.SUCCESS
        progress.update.assert_called()
        progress.finish.assert_called_once()

    @patch("install_browsers.subprocess.run")
    def test_progress_indicator_fail_on_error(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="bad"
        )
        progress = MagicMock(spec=ProgressIndicator)
        result = run_browser_install("chromium", progress=progress)
        assert result.status == InstallStatus.FAILED
        progress.fail.assert_called_once()

    @patch("install_browsers.subprocess.run")
    def test_install_with_deps(self, mock_run: MagicMock) -> None:
        """When install_deps=True, two subprocess calls are made."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        result = run_browser_install("chromium", install_deps=True)
        assert result.status == InstallStatus.SUCCESS
        assert mock_run.call_count == 2  # install + install-deps

    @patch("install_browsers.subprocess.run")
    def test_deps_failure_does_not_fail_install(self, mock_run: MagicMock) -> None:
        """System deps failure is best-effort; browser install still succeeds."""
        def side_effect(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list) and "install-deps" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=1, stdout="", stderr="sudo required"
                )
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="OK\n", stderr=""  # type: ignore[arg-type]
            )

        mock_run.side_effect = side_effect
        result = run_browser_install("chromium", install_deps=True)
        assert result.status == InstallStatus.SUCCESS


# ===========================================================================
# Verification tests
# ===========================================================================

class TestVerifyBrowserInstalled:
    """Tests for verify_browser_installed()."""

    @patch("install_browsers.subprocess.run")
    def test_browser_is_installed(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        assert verify_browser_installed("chromium") is True

    @patch("install_browsers.subprocess.run")
    def test_browser_not_installed(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="browser not found"
        )
        assert verify_browser_installed("chromium") is False

    @patch("install_browsers.subprocess.run")
    def test_verification_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="check", timeout=30)
        assert verify_browser_installed("chromium") is False

    @patch("install_browsers.subprocess.run")
    def test_verification_file_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        assert verify_browser_installed("chromium") is False

    @patch("install_browsers.subprocess.run")
    def test_verification_os_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("disk error")
        assert verify_browser_installed("firefox") is False


class TestVerifyAllBrowsers:
    """Tests for verify_all_browsers()."""

    @patch("install_browsers.subprocess.run")
    def test_all_verified(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        results = verify_all_browsers(["chromium", "firefox"])
        assert results == {"chromium": True, "firefox": True}

    @patch("install_browsers.subprocess.run")
    def test_partial_verification(self, mock_run: MagicMock) -> None:
        call_count = [0]

        def side_effect(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            call_count[0] += 1
            if call_count[0] == 1:
                return subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="OK\n", stderr=""
                )
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="not found"
            )

        mock_run.side_effect = side_effect
        results = verify_all_browsers(["chromium", "firefox"])
        assert results["chromium"] is True
        assert results["firefox"] is False


# ===========================================================================
# Progress indicator tests
# ===========================================================================

class TestProgressIndicator:
    """Tests for ProgressIndicator output."""

    def test_update_writes_spinner(self) -> None:
        stream = io.StringIO()
        progress = ProgressIndicator(stream=stream)
        progress.update("downloading...")
        output = stream.getvalue()
        assert "downloading..." in output
        assert "[|]" in output or "[/]" in output or "[-]" in output or "[\\]" in output

    def test_finish_writes_ok(self) -> None:
        stream = io.StringIO()
        progress = ProgressIndicator(stream=stream)
        progress.finish("done!")
        output = stream.getvalue()
        assert "[OK]" in output
        assert "done!" in output

    def test_fail_writes_fail(self) -> None:
        stream = io.StringIO()
        progress = ProgressIndicator(stream=stream)
        progress.fail("broken")
        output = stream.getvalue()
        assert "[FAIL]" in output
        assert "broken" in output

    def test_spinner_cycles(self) -> None:
        stream = io.StringIO()
        progress = ProgressIndicator(stream=stream)
        # The spinner should cycle through 4 characters
        for i in range(5):
            stream.truncate(0)
            stream.seek(0)
            progress.update(f"step {i}")
        assert progress._tick == 5


# ===========================================================================
# InstallReport data structure tests
# ===========================================================================

class TestInstallReport:
    """Tests for InstallReport properties."""

    def test_success_count(self) -> None:
        report = InstallReport(platform_name="Linux", results=[
            BrowserInstallResult("chromium", InstallStatus.SUCCESS, "ok"),
            BrowserInstallResult("firefox", InstallStatus.FAILED, "nope"),
            BrowserInstallResult("webkit", InstallStatus.ALREADY_INSTALLED, "ok"),
        ])
        assert report.success_count == 2
        assert report.failure_count == 1
        assert report.all_succeeded is False

    def test_all_succeeded(self) -> None:
        report = InstallReport(platform_name="Linux", results=[
            BrowserInstallResult("chromium", InstallStatus.SUCCESS, "ok"),
        ])
        assert report.all_succeeded is True

    def test_empty_report_not_succeeded(self) -> None:
        report = InstallReport(platform_name="Linux")
        assert report.all_succeeded is False


# ===========================================================================
# High-level install_browsers() tests
# ===========================================================================

class TestInstallBrowsers:
    """Integration-level tests for install_browsers() with mocked subprocess."""

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_install_all_linux(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        stream = io.StringIO()
        report = install_browsers(stream=stream)
        assert report.platform_name == "Linux"
        assert report.success_count == 3
        assert report.all_succeeded is True
        output = stream.getvalue()
        assert "Playwright Browser Installer" in output

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_install_specific_browser(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        stream = io.StringIO()
        report = install_browsers(browsers=["chromium"], stream=stream)
        assert report.success_count == 1
        assert len(report.results) == 1
        assert report.results[0].browser == "chromium"

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_dry_run_does_not_install(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"
        stream = io.StringIO()
        report = install_browsers(dry_run=True, stream=stream)
        mock_run.assert_not_called()
        output = stream.getvalue()
        assert "DRY-RUN" in output
        # All should be SKIPPED in dry-run
        assert all(r.status == InstallStatus.SKIPPED for r in report.results)

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_webkit_skipped_on_windows(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Windows"
        mock_platform.machine.return_value = "AMD64"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        stream = io.StringIO()
        report = install_browsers(
            browsers=["chromium", "webkit"], stream=stream
        )
        # chromium should succeed, webkit should be skipped
        statuses = {r.browser: r.status for r in report.results}
        assert statuses["chromium"] == InstallStatus.SUCCESS
        assert statuses["webkit"] == InstallStatus.SKIPPED

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_partial_failure(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        call_count = [0]

        def side_effect(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            call_count[0] += 1
            if call_count[0] == 2:
                return subprocess.CompletedProcess(
                    args=[], returncode=1, stdout="", stderr="download failed"
                )
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout="OK\n", stderr=""
            )

        mock_run.side_effect = side_effect
        stream = io.StringIO()
        report = install_browsers(stream=stream)
        assert report.failure_count == 1
        assert report.success_count == 2
        assert report.all_succeeded is False


# ===========================================================================
# CLI argument parsing tests
# ===========================================================================

class TestParseArgs:
    """Tests for parse_args()."""

    def test_defaults(self) -> None:
        args = parse_args([])
        assert args["browsers"] is None
        assert args["check"] is False
        assert args["dry_run"] is False
        assert args["install_deps"] is False
        assert args["timeout"] == 600

    def test_single_browser(self) -> None:
        args = parse_args(["--browser", "chromium"])
        assert args["browsers"] == ["chromium"]

    def test_multiple_browsers(self) -> None:
        args = parse_args(["--browser", "chromium", "--browser", "firefox"])
        assert args["browsers"] == ["chromium", "firefox"]

    def test_check_flag(self) -> None:
        args = parse_args(["--check"])
        assert args["check"] is True

    def test_dry_run_flag(self) -> None:
        args = parse_args(["--dry-run"])
        assert args["dry_run"] is True

    def test_install_deps_flag(self) -> None:
        args = parse_args(["--install-deps"])
        assert args["install_deps"] is True

    def test_custom_timeout(self) -> None:
        args = parse_args(["--timeout", "120"])
        assert args["timeout"] == 120


# ===========================================================================
# CLI main() tests
# ===========================================================================

class TestMain:
    """Tests for the main() entry point."""

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_main_install_success(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        exit_code = main(["--browser", "chromium"])
        assert exit_code == 0

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_main_install_failure(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="network error"
        )
        exit_code = main(["--browser", "chromium"])
        assert exit_code == 1

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_main_check_mode_all_ok(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK\n", stderr=""
        )
        exit_code = main(["--check", "--browser", "chromium"])
        assert exit_code == 0

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_main_check_mode_missing(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="not found"
        )
        exit_code = main(["--check", "--browser", "chromium"])
        assert exit_code == 1

    @patch("install_browsers.subprocess.run")
    @patch("install_browsers.platform")
    def test_main_dry_run(
        self, mock_platform: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        exit_code = main(["--dry-run"])
        # Dry-run: all SKIPPED, but all_succeeded is False because
        # SKIPPED is not counted as success
        # Actually, dry run produces SKIPPED which has failure_count 0
        # and success_count 0 — so all_succeeded is False (empty results check)
        # The exit code reflects this
        mock_run.assert_not_called()


# ===========================================================================
# find_playwright_cli tests
# ===========================================================================

class TestFindPlaywrightCli:
    """Tests for find_playwright_cli()."""

    @patch("install_browsers.subprocess.run")
    def test_found_via_python_module(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Version 1.57.0\n", stderr=""
        )
        result = find_playwright_cli()
        assert result == Path(sys.executable)

    @patch("install_browsers.subprocess.run")
    def test_not_found_raises(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("not found")
        with pytest.raises(FileNotFoundError, match="Playwright is not installed"):
            find_playwright_cli()

    @patch("install_browsers.subprocess.run")
    def test_timeout_raises(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="check", timeout=30)
        with pytest.raises(FileNotFoundError, match="timed out"):
            find_playwright_cli()

    @patch("install_browsers.subprocess.run")
    def test_nonzero_exit_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error"
        )
        with pytest.raises(FileNotFoundError, match="not found"):
            find_playwright_cli()
