"""auto_update.py — Solace Browser Auto-Update Module

Checks for a newer release on startup, downloads, verifies SHA-256,
and prompts the user to restart.

Architecture:
  - AutoUpdateChecker: polls the version endpoint, compares semver
  - UpdateDownloader: downloads artifact + verifies SHA-256
  - UpdateBanner: signals the UI layer (via callback) when an update is ready
  - Downgrade prevention: never installs an older version over a newer one

Rung: 641 (local correctness)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Tuple

logger = logging.getLogger("solace.auto_update")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default update endpoint — override via SOLACE_UPDATE_URL env var
DEFAULT_UPDATE_URL = "https://www.solaceagi.com/api/releases/latest"

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 10

# Maximum download size guard (500 MB)
MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024

# Semver regex (strict: major.minor.patch, optional leading v)
_SEMVER_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


# ---------------------------------------------------------------------------
# Semver helpers
# ---------------------------------------------------------------------------

def parse_semver(version_str: str) -> Tuple[int, int, int, str]:
    """Parse a semver string into (major, minor, patch, pre-release).

    Raises ValueError if the string is not valid semver.
    """
    if not isinstance(version_str, str):
        raise ValueError(f"version must be a string, got {type(version_str)}")
    m = _SEMVER_RE.match(version_str.strip())
    if not m:
        raise ValueError(f"Invalid semver string: {version_str!r}")
    major = int(m.group("major"))
    minor = int(m.group("minor"))
    patch = int(m.group("patch"))
    pre   = m.group("pre") or ""
    return major, minor, patch, pre


def is_newer(candidate: str, current: str) -> bool:
    """Return True if candidate is strictly newer than current.

    Pre-release versions (e.g. 1.0.0-beta.1) are considered older than
    the corresponding release (1.0.0).

    Raises ValueError if either string is invalid semver.
    """
    c_maj, c_min, c_pat, c_pre = parse_semver(candidate)
    n_maj, n_min, n_pat, n_pre = parse_semver(current)

    # Compare numeric components first
    candidate_tuple = (c_maj, c_min, c_pat)
    current_tuple   = (n_maj, n_min, n_pat)

    if candidate_tuple > current_tuple:
        return True
    if candidate_tuple < current_tuple:
        return False

    # Same numeric version — compare pre-release
    # Release (empty pre) > pre-release (non-empty pre)
    if c_pre == "" and n_pre != "":
        return True   # candidate is the release, current is pre-release
    if c_pre != "" and n_pre == "":
        return False  # candidate is pre-release, current is release
    # Both have pre-release or both are releases with same numbers
    return False


def is_downgrade(candidate: str, current: str) -> bool:
    """Return True if candidate is strictly older than current."""
    return is_newer(current, candidate)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ReleaseInfo:
    """Parsed release metadata from the update endpoint."""
    version: str
    url: str
    sha256: str
    size_bytes: int = 0
    changelog_url: str = ""
    release_date: str = ""

    def __post_init__(self) -> None:
        # Validate semver on creation
        parse_semver(self.version)
        if not self.url:
            raise ValueError("ReleaseInfo.url must not be empty")
        if not re.match(r"^[0-9a-fA-F]{64}$", self.sha256):
            raise ValueError(f"Invalid SHA-256 hash: {self.sha256!r}")


@dataclass
class UpdateResult:
    """Result of an update check."""
    update_available: bool
    current_version: str
    latest_version: str
    release: Optional[ReleaseInfo] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# AutoUpdateChecker
# ---------------------------------------------------------------------------

class AutoUpdateChecker:
    """Checks the remote update endpoint and compares versions.

    Usage:
        checker = AutoUpdateChecker(current_version="1.0.0")
        result = checker.check()
        if result.update_available:
            print(f"New version: {result.latest_version}")
    """

    def __init__(
        self,
        current_version: str,
        update_url: str = DEFAULT_UPDATE_URL,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        # Validate current version on init
        parse_semver(current_version)
        self.current_version = current_version
        self.update_url = update_url
        self.timeout = timeout

    def _fetch_release_info(self) -> dict:
        """Fetch and parse JSON from the update endpoint."""
        req = urllib.request.Request(
            self.update_url,
            headers={
                "User-Agent": f"SolaceBrowser/{self.current_version} auto-update",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read(1024 * 1024)  # cap at 1 MB
                return json.loads(raw)
        except urllib.error.URLError as e:
            raise ConnectionError(f"Could not reach update server: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Update server returned invalid JSON: {e}") from e

    def check(self) -> UpdateResult:
        """Check for updates. Returns UpdateResult (never raises)."""
        try:
            data = self._fetch_release_info()
            release = ReleaseInfo(
                version=data["version"],
                url=data["url"],
                sha256=data["sha256"],
                size_bytes=int(data.get("size_bytes", 0)),
                changelog_url=data.get("changelog_url", ""),
                release_date=data.get("release_date", ""),
            )
            update_available = is_newer(release.version, self.current_version)
            # Downgrade prevention: never flag a downgrade as an update
            if is_downgrade(release.version, self.current_version):
                update_available = False

            return UpdateResult(
                update_available=update_available,
                current_version=self.current_version,
                latest_version=release.version,
                release=release if update_available else None,
            )
        except Exception as exc:
            logger.warning("Auto-update check failed: %s", exc)
            return UpdateResult(
                update_available=False,
                current_version=self.current_version,
                latest_version=self.current_version,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# UpdateDownloader
# ---------------------------------------------------------------------------

class UpdateDownloader:
    """Downloads a release artifact and verifies its SHA-256 checksum.

    Usage:
        downloader = UpdateDownloader()
        path = downloader.download(release)  # raises on failure
    """

    def __init__(
        self,
        dest_dir: Optional[Path] = None,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        self.dest_dir = dest_dir or Path(tempfile.gettempdir()) / "solace_updates"
        self.timeout = timeout

    def download(self, release: ReleaseInfo) -> Path:
        """Download and verify the release artifact.

        Returns the path to the verified file.
        Raises:
          ConnectionError: on network failure
          ValueError: on SHA-256 mismatch
          OSError: on disk errors
        """
        self.dest_dir.mkdir(parents=True, exist_ok=True)

        filename = os.path.basename(release.url.split("?")[0])
        dest_path = self.dest_dir / filename

        logger.info("Downloading update: %s -> %s", release.url, dest_path)

        req = urllib.request.Request(
            release.url,
            headers={"User-Agent": "SolaceBrowser auto-update"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                total = 0
                sha256 = hashlib.sha256()

                with open(dest_path, "wb") as fh:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_DOWNLOAD_BYTES:
                            dest_path.unlink(missing_ok=True)
                            raise ValueError(
                                f"Download exceeded maximum size ({MAX_DOWNLOAD_BYTES} bytes)"
                            )
                        sha256.update(chunk)
                        fh.write(chunk)

        except urllib.error.URLError as e:
            dest_path.unlink(missing_ok=True)
            raise ConnectionError(f"Download failed: {e}") from e

        # Verify SHA-256
        computed = sha256.hexdigest()
        if computed.lower() != release.sha256.lower():
            dest_path.unlink(missing_ok=True)
            raise ValueError(
                f"SHA-256 mismatch for {filename}:\n"
                f"  expected: {release.sha256}\n"
                f"  computed: {computed}"
            )

        logger.info("Download verified: %s (SHA-256 OK)", filename)
        return dest_path

    def verify_file(self, path: Path, expected_sha256: str) -> bool:
        """Verify SHA-256 of an already-downloaded file.

        Returns True if checksum matches, False otherwise.
        """
        if not path.exists():
            return False
        sha256 = hashlib.sha256()
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest().lower() == expected_sha256.lower()


# ---------------------------------------------------------------------------
# UpdateBanner
# ---------------------------------------------------------------------------

UpdateCallback = Callable[[UpdateResult], None]


class UpdateBanner:
    """Manages the update notification lifecycle.

    Calls `on_update_available(result)` when a newer version is found.
    Calls `on_no_update(result)` when the current version is up to date.
    Calls `on_error(result)` when the check fails.

    Usage:
        def show_banner(result):
            print(f"Update available: {result.latest_version}")

        banner = UpdateBanner(on_update_available=show_banner)
        banner.run_check(current_version="1.0.0")
    """

    def __init__(
        self,
        on_update_available: Optional[UpdateCallback] = None,
        on_no_update: Optional[UpdateCallback] = None,
        on_error: Optional[UpdateCallback] = None,
        update_url: str = DEFAULT_UPDATE_URL,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        self._on_update = on_update_available or (lambda r: None)
        self._on_no_update = on_no_update or (lambda r: None)
        self._on_error = on_error or (lambda r: None)
        self.update_url = update_url
        self.timeout = timeout
        self._last_result: Optional[UpdateResult] = None

    def run_check(self, current_version: str) -> UpdateResult:
        """Run the update check and invoke the appropriate callback.

        Always returns an UpdateResult. Never raises.
        """
        checker = AutoUpdateChecker(
            current_version=current_version,
            update_url=self.update_url,
            timeout=self.timeout,
        )
        result = checker.check()
        self._last_result = result

        if result.error:
            self._on_error(result)
        elif result.update_available:
            self._on_update(result)
        else:
            self._on_no_update(result)

        return result

    @property
    def last_result(self) -> Optional[UpdateResult]:
        """The result of the most recent check, or None if no check run."""
        return self._last_result


# ---------------------------------------------------------------------------
# Convenience: read current version from VERSION file
# ---------------------------------------------------------------------------

def read_version_file(project_root: Optional[Path] = None) -> str:
    """Read the current version from the VERSION file at project root.

    Falls back to "0.0.0" if the file is missing or unreadable.
    """
    if project_root is None:
        # Assume this file is in src/, so project root is one level up
        project_root = Path(__file__).parent.parent

    version_file = project_root / "VERSION"
    try:
        return version_file.read_text().strip()
    except OSError:
        logger.warning("VERSION file not found at %s, defaulting to 0.0.0", version_file)
        return "0.0.0"


# ---------------------------------------------------------------------------
# CLI entry point (for manual testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Solace Browser auto-update checker")
    parser.add_argument("--version", default=None, help="Override current version")
    parser.add_argument("--url", default=DEFAULT_UPDATE_URL, help="Update endpoint URL")
    args = parser.parse_args()

    current = args.version or read_version_file()
    print(f"Current version: {current}")
    print(f"Checking: {args.url}")

    def on_update(r: UpdateResult) -> None:
        print(f"\nUpdate available: {r.current_version} -> {r.latest_version}")
        if r.release:
            print(f"  Download: {r.release.url}")
            print(f"  SHA-256:  {r.release.sha256}")

    def on_no_update(r: UpdateResult) -> None:
        print(f"\nAlready up to date: {r.current_version}")

    def on_error(r: UpdateResult) -> None:
        print(f"\nUpdate check failed: {r.error}")

    banner = UpdateBanner(
        on_update_available=on_update,
        on_no_update=on_no_update,
        on_error=on_error,
        update_url=args.url,
    )
    banner.run_check(current)
