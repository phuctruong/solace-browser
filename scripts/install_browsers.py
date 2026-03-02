#!/usr/bin/env python3
"""Playwright browser auto-installer for Solace Browser.

The PyInstaller binary (~267MB) cannot bundle Playwright browser binaries.
This script runs post-install to download and verify browsers.

Usage:
    python scripts/install_browsers.py                 # install all browsers
    python scripts/install_browsers.py --browser chromium  # chromium only
    python scripts/install_browsers.py --check         # verify installation
    python scripts/install_browsers.py --dry-run       # show what would happen

Auth: 65537 | Rung: 641
"""

from __future__ import annotations

import logging
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TextIO


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_BROWSERS: list[str] = ["chromium", "firefox", "webkit"]

PLATFORM_BROWSER_SUPPORT: dict[str, list[str]] = {
    "Linux": ["chromium", "firefox", "webkit"],
    "Darwin": ["chromium", "firefox", "webkit"],
    "Windows": ["chromium", "firefox"],
}

# ANSI color codes for terminal output
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class InstallStatus(Enum):
    """Status of a browser installation attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ALREADY_INSTALLED = "already_installed"


@dataclass
class BrowserInstallResult:
    """Result of installing a single browser."""
    browser: str
    status: InstallStatus
    message: str
    duration_seconds: float = 0.0


@dataclass
class InstallReport:
    """Full report from an installation run."""
    platform_name: str
    results: list[BrowserInstallResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0

    @property
    def success_count(self) -> int:
        return sum(
            1 for r in self.results
            if r.status in (InstallStatus.SUCCESS, InstallStatus.ALREADY_INSTALLED)
        )

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if r.status == InstallStatus.FAILED)

    @property
    def all_succeeded(self) -> bool:
        return self.failure_count == 0 and len(self.results) > 0


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platform() -> str:
    """Detect the current operating system.

    Returns:
        One of 'Linux', 'Darwin', or 'Windows'.

    Raises:
        RuntimeError: If the platform is not supported.
    """
    system = platform.system()
    if system not in PLATFORM_BROWSER_SUPPORT:
        raise RuntimeError(
            f"Unsupported platform: {system!r}. "
            f"Supported: {', '.join(sorted(PLATFORM_BROWSER_SUPPORT.keys()))}"
        )
    return system


def get_supported_browsers(platform_name: str) -> list[str]:
    """Return the list of browsers supported on the given platform.

    Args:
        platform_name: One of 'Linux', 'Darwin', or 'Windows'.

    Raises:
        ValueError: If the platform name is not recognized.
    """
    if platform_name not in PLATFORM_BROWSER_SUPPORT:
        raise ValueError(
            f"Unknown platform: {platform_name!r}. "
            f"Known: {', '.join(sorted(PLATFORM_BROWSER_SUPPORT.keys()))}"
        )
    return list(PLATFORM_BROWSER_SUPPORT[platform_name])


def filter_browsers(
    requested: list[str],
    platform_name: str,
) -> tuple[list[str], list[str]]:
    """Filter requested browsers against platform support.

    Returns:
        A tuple of (installable, skipped) browser names.
    """
    supported = set(get_supported_browsers(platform_name))
    installable: list[str] = []
    skipped: list[str] = []
    for browser in requested:
        if browser in supported:
            installable.append(browser)
        else:
            skipped.append(browser)
    return installable, skipped


# ---------------------------------------------------------------------------
# Progress indication
# ---------------------------------------------------------------------------

class ProgressIndicator:
    """Simple spinner/progress indicator for terminal output."""

    SPINNER_CHARS = ["|", "/", "-", "\\"]

    def __init__(self, stream: TextIO = sys.stdout) -> None:
        self._stream = stream
        self._tick = 0

    def update(self, message: str) -> None:
        """Print a progress update with a spinner character."""
        char = self.SPINNER_CHARS[self._tick % len(self.SPINNER_CHARS)]
        self._stream.write(f"\r  {CYAN}[{char}]{RESET} {message}")
        self._stream.flush()
        self._tick += 1

    def finish(self, message: str) -> None:
        """Clear the spinner line and print a final status message."""
        self._stream.write(f"\r  {GREEN}[OK]{RESET} {message}\n")
        self._stream.flush()

    def fail(self, message: str) -> None:
        """Clear the spinner line and print a failure message."""
        self._stream.write(f"\r  {RED}[FAIL]{RESET} {message}\n")
        self._stream.flush()


# ---------------------------------------------------------------------------
# Playwright subprocess interface
# ---------------------------------------------------------------------------

def build_install_command(browser: str) -> list[str]:
    """Build the subprocess command to install a specific browser.

    Args:
        browser: Browser name (e.g. 'chromium', 'firefox', 'webkit').

    Returns:
        The command list for subprocess.run.

    Raises:
        ValueError: If the browser name is not recognized.
    """
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(
            f"Unknown browser: {browser!r}. "
            f"Supported: {', '.join(SUPPORTED_BROWSERS)}"
        )
    return [sys.executable, "-m", "playwright", "install", browser]


def build_install_deps_command(browser: str) -> list[str]:
    """Build the subprocess command to install system dependencies for a browser.

    Args:
        browser: Browser name (e.g. 'chromium', 'firefox', 'webkit').

    Returns:
        The command list for subprocess.run.
    """
    return [sys.executable, "-m", "playwright", "install-deps", browser]


def run_browser_install(
    browser: str,
    *,
    timeout_seconds: int = 600,
    progress: ProgressIndicator | None = None,
    install_deps: bool = False,
) -> BrowserInstallResult:
    """Install a single Playwright browser via subprocess.

    Args:
        browser: Browser name to install.
        timeout_seconds: Maximum time to wait for the install.
        progress: Optional progress indicator for UI feedback.
        install_deps: Whether to also install system dependencies (requires sudo on Linux).

    Returns:
        A BrowserInstallResult with the outcome.
    """
    start = time.monotonic()

    if progress:
        progress.update(f"Installing {browser}...")

    cmd = build_install_command(browser)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        if progress:
            progress.fail(f"{browser}: timed out after {timeout_seconds}s")
        return BrowserInstallResult(
            browser=browser,
            status=InstallStatus.FAILED,
            message=f"Installation timed out after {timeout_seconds} seconds",
            duration_seconds=duration,
        )
    except FileNotFoundError:
        duration = time.monotonic() - start
        if progress:
            progress.fail(f"{browser}: playwright CLI not found")
        return BrowserInstallResult(
            browser=browser,
            status=InstallStatus.FAILED,
            message="Playwright CLI not found. Install with: pip install playwright",
            duration_seconds=duration,
        )
    except OSError as exc:
        duration = time.monotonic() - start
        if progress:
            progress.fail(f"{browser}: OS error — {exc}")
        return BrowserInstallResult(
            browser=browser,
            status=InstallStatus.FAILED,
            message=f"OS error during installation: {exc}",
            duration_seconds=duration,
        )

    duration = time.monotonic() - start

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if progress:
            progress.fail(f"{browser}: install failed (exit {result.returncode})")
        return BrowserInstallResult(
            browser=browser,
            status=InstallStatus.FAILED,
            message=f"Install failed (exit {result.returncode}): {stderr}",
            duration_seconds=duration,
        )

    # Optionally install system dependencies (Linux only, may need sudo)
    if install_deps:
        if progress:
            progress.update(f"Installing system deps for {browser}...")
        deps_cmd = build_install_deps_command(browser)
        try:
            deps_result = subprocess.run(
                deps_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            if deps_result.returncode != 0:
                # Dependencies are optional — warn but don't fail
                if progress:
                    progress.update(
                        f"{browser}: browser installed but system deps failed "
                        f"(may need sudo)"
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            logger.warning(
                "System dependency installation failed for %s: %s",
                browser, exc,
            )
            if progress:
                progress.update(
                    f"{browser}: browser installed but system deps failed ({exc})"
                )

    if progress:
        progress.finish(f"{browser} installed ({duration:.1f}s)")

    return BrowserInstallResult(
        browser=browser,
        status=InstallStatus.SUCCESS,
        message=f"Successfully installed {browser}",
        duration_seconds=duration,
    )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_browser_installed(browser: str, *, timeout_seconds: int = 30) -> bool:
    """Check whether a specific Playwright browser is installed.

    Uses `playwright install --dry-run` output parsing. Falls back to
    attempting a browser launch check.

    Args:
        browser: Browser name to check.
        timeout_seconds: Maximum wait time.

    Returns:
        True if the browser appears to be installed, False otherwise.

    Raises:
        ValueError: If the browser name is not in SUPPORTED_BROWSERS or
            contains non-alphanumeric characters (prevents injection).
    """
    # Validate browser name to prevent injection
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(f"Unknown browser: {browser!r}")
    # Use only the validated name (alphanumeric only)
    if not browser.isalnum():
        raise ValueError(f"Invalid browser name: {browser!r}")

    # Try running a minimal script that checks if the browser can be launched
    check_script = (
        f"from playwright.sync_api import sync_playwright; "
        f"p = sync_playwright().start(); "
        f"b = p.{browser}.launch(headless=True); "
        f"b.close(); p.stop(); "
        f"print('OK')"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", check_script],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return result.returncode == 0 and "OK" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def verify_all_browsers(
    browsers: list[str],
    *,
    timeout_seconds: int = 30,
) -> dict[str, bool]:
    """Verify that each browser in the list is installed.

    Returns:
        A dict mapping browser name to True/False.
    """
    return {
        browser: verify_browser_installed(browser, timeout_seconds=timeout_seconds)
        for browser in browsers
    }


# ---------------------------------------------------------------------------
# High-level installer
# ---------------------------------------------------------------------------

def install_browsers(
    browsers: list[str] | None = None,
    *,
    dry_run: bool = False,
    install_deps: bool = False,
    timeout_seconds: int = 600,
    stream: TextIO = sys.stdout,
) -> InstallReport:
    """Install Playwright browsers with progress indication.

    Args:
        browsers: List of browser names to install. None means all supported.
        dry_run: If True, report what would be done without doing it.
        install_deps: If True, also install system dependencies.
        timeout_seconds: Max time per browser install.
        stream: Output stream for progress messages.

    Returns:
        An InstallReport summarizing the results.
    """
    total_start = time.monotonic()
    platform_name = detect_platform()
    progress = ProgressIndicator(stream=stream)

    stream.write(f"\n{BOLD}Solace Browser — Playwright Browser Installer{RESET}\n")
    stream.write(f"{DIM}Platform: {platform_name} ({platform.machine()}){RESET}\n\n")

    # Determine which browsers to install
    if browsers is None:
        requested = get_supported_browsers(platform_name)
    else:
        requested = browsers

    installable, skipped = filter_browsers(requested, platform_name)

    report = InstallReport(platform_name=platform_name)

    # Report skipped browsers
    for browser in skipped:
        result = BrowserInstallResult(
            browser=browser,
            status=InstallStatus.SKIPPED,
            message=f"{browser} is not supported on {platform_name}",
        )
        report.results.append(result)
        stream.write(
            f"  {YELLOW}[SKIP]{RESET} {browser}: "
            f"not supported on {platform_name}\n"
        )

    # Install each browser
    for browser in installable:
        if dry_run:
            cmd = build_install_command(browser)
            stream.write(
                f"  {DIM}[DRY-RUN]{RESET} Would run: {' '.join(cmd)}\n"
            )
            report.results.append(BrowserInstallResult(
                browser=browser,
                status=InstallStatus.SKIPPED,
                message=f"Dry run — would install {browser}",
            ))
        else:
            result = run_browser_install(
                browser,
                timeout_seconds=timeout_seconds,
                progress=progress,
                install_deps=install_deps,
            )
            report.results.append(result)

    report.total_duration_seconds = time.monotonic() - total_start

    # Summary
    stream.write(f"\n{BOLD}Summary:{RESET}\n")
    stream.write(
        f"  Installed: {report.success_count}  "
        f"Failed: {report.failure_count}  "
        f"Time: {report.total_duration_seconds:.1f}s\n\n"
    )

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> dict[str, object]:
    """Parse command-line arguments.

    Returns:
        A dict with parsed argument values.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Install Playwright browsers for Solace Browser.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/install_browsers.py                    # all browsers\n"
            "  python scripts/install_browsers.py --browser chromium # chromium only\n"
            "  python scripts/install_browsers.py --check            # verify install\n"
            "  python scripts/install_browsers.py --dry-run          # preview only\n"
        ),
    )
    parser.add_argument(
        "--browser",
        action="append",
        dest="browsers",
        choices=SUPPORTED_BROWSERS,
        help="Browser to install (can be repeated). Defaults to all supported.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that browsers are installed instead of installing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually installing.",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Also install system dependencies (may require sudo on Linux).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds per browser install (default: 600, min: 1).",
    )

    args = parser.parse_args(argv)
    if args.timeout < 1:
        parser.error("--timeout must be at least 1 second")
    return {
        "browsers": args.browsers,
        "check": args.check,
        "dry_run": args.dry_run,
        "install_deps": args.install_deps,
        "timeout": args.timeout,
    }


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    args = parse_args(argv)

    if args["check"]:
        # Verification mode
        platform_name = detect_platform()
        browsers = args["browsers"] or get_supported_browsers(platform_name)
        print(f"\n{BOLD}Checking Playwright browser installation...{RESET}\n")
        results = verify_all_browsers(browsers)
        all_ok = True
        for browser, installed in results.items():
            if installed:
                print(f"  {GREEN}[OK]{RESET} {browser}")
            else:
                print(f"  {RED}[MISSING]{RESET} {browser}")
                all_ok = False
        print()
        return 0 if all_ok else 1

    # Install mode
    report = install_browsers(
        browsers=args["browsers"],
        dry_run=bool(args["dry_run"]),
        install_deps=bool(args["install_deps"]),
        timeout_seconds=int(args["timeout"]),  # type: ignore[arg-type]
    )

    return 0 if report.all_succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
