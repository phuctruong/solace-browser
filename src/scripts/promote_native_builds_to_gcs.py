#!/usr/bin/env python3
"""
Promote native build artifacts from a GitHub Actions run into GCS.

Flow:
1) Read private GitHub credentials from `git credential fill`.
2) Download `native-linux`, `native-macos`, `native-windows` artifact bundles.
3) Verify binary headers (ELF/Mach-O/PE) and Windows installer marker.
4) Upload binaries + sha256 files to versioned and latest GCS paths.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


REPO_OWNER = "phuctruong"
REPO_NAME = "solace-browser"
WORKFLOW_NAME = "build-binaries"


def _resolve_gcloud_cli() -> str:
    candidates = ["gcloud"]
    if os.name == "nt":
        candidates = ["gcloud.cmd", "gcloud.exe", "gcloud"]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError("gcloud CLI not found on PATH.")


GCLOUD_CLI = _resolve_gcloud_cli()


@dataclass(frozen=True)
class PlatformSpec:
    artifact_name: str
    object_name: str
    target_os: str


PLATFORMS: tuple[PlatformSpec, ...] = (
    PlatformSpec("native-linux", "solace-browser-linux-x86_64", "linux"),
    PlatformSpec("native-macos", "solace-browser-macos-universal", "macos"),
    PlatformSpec("native-windows", "solace-browser-windows-x86_64.msi", "windows"),
)


def _read_version(project_root: Path) -> str:
    version_path = project_root / "VERSION"
    return version_path.read_text(encoding="utf-8").strip()


def _github_credentials() -> tuple[str, str]:
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input=b"protocol=https\nhost=github.com\n\n",
        capture_output=True,
        check=True,
    )
    values: dict[str, str] = {}
    for line in proc.stdout.decode("utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    username = values.get("username", "")
    password = values.get("password", "")
    if not username or not password:
        raise RuntimeError("Missing github.com credentials from `git credential fill`.")
    return username, password


def _github_api_get(path: str, username: str, password: str) -> dict[str, Any]:
    url = f"https://api.github.com{path}"
    request = urllib.request.Request(url)
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    request.add_header("Authorization", f"Basic {token}")
    request.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _github_download(url: str, destination: Path, username: str, password: str) -> None:
    request = urllib.request.Request(url)
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    request.add_header("Authorization", f"Basic {token}")
    request.add_header("Accept", "application/vnd.github+json")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=120) as response:
            destination.write_bytes(response.read())
            return
    except urllib.error.HTTPError as exc:
        if exc.code not in {301, 302, 303, 307, 308}:
            raise
        location = exc.headers.get("Location")
        if not location:
            raise RuntimeError(f"GitHub artifact redirect missing Location header for {url}.")
        with urllib.request.urlopen(location, timeout=120) as response:
            destination.write_bytes(response.read())


def _resolve_run_id(tag: str | None, run_id: int | None, username: str, password: str) -> int:
    if run_id is not None:
        return run_id
    if not tag:
        raise RuntimeError("Provide --run-id or --tag.")
    encoded_owner = urllib.parse.quote(REPO_OWNER)
    encoded_repo = urllib.parse.quote(REPO_NAME)
    data = _github_api_get(
        f"/repos/{encoded_owner}/{encoded_repo}/actions/runs?per_page=30",
        username,
        password,
    )
    for run in data.get("workflow_runs", []):
        if run.get("name") != WORKFLOW_NAME:
            continue
        if run.get("head_branch") != tag:
            continue
        return int(run["id"])
    raise RuntimeError(f"No workflow run found for tag '{tag}'.")


def _verify_run_success(run_id: int, username: str, password: str) -> dict[str, Any]:
    encoded_owner = urllib.parse.quote(REPO_OWNER)
    encoded_repo = urllib.parse.quote(REPO_NAME)
    run = _github_api_get(
        f"/repos/{encoded_owner}/{encoded_repo}/actions/runs/{run_id}",
        username,
        password,
    )
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status != "completed" or conclusion != "success":
        raise RuntimeError(
            f"Run {run_id} is not successful: status={status} conclusion={conclusion}"
        )
    return run


def _find_file(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if not matches:
        raise RuntimeError(f"Could not find '{name}' in extracted artifact {root}.")
    return matches[0]


def _is_elf(blob: bytes) -> bool:
    return blob.startswith(b"\x7fELF")


def _is_macho(blob: bytes) -> bool:
    return blob[:4] in {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    }


def _is_pe(file_path: Path) -> bool:
    data = file_path.read_bytes()
    if len(data) < 0x40 or not data.startswith(b"MZ"):
        return False
    pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]
    return pe_offset + 4 <= len(data) and data[pe_offset:pe_offset + 4] == b"PE\x00\x00"


def _verify_binary(target_os: str, binary_path: Path) -> None:
    data = binary_path.read_bytes()
    head = data[:64]
    if target_os == "linux" and not _is_elf(head):
        raise RuntimeError(f"{binary_path} is not an ELF binary.")
    if target_os == "macos" and not _is_macho(head):
        raise RuntimeError(f"{binary_path} is not a Mach-O binary.")
    if target_os == "windows":
        data_full = binary_path.read_bytes()
        ole2_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        if data_full.startswith(ole2_header):
            # MSI format (OLE2 Compound Document)
            pass
        elif _is_pe(binary_path):
            # Legacy Inno Setup installer (PE format)
            if b"Inno Setup Setup Data" not in data_full:
                raise RuntimeError(
                    f"{binary_path} is PE but not an Inno Setup installer (marker missing)."
                )
        else:
            raise RuntimeError(
                f"{binary_path} is not a valid Windows installer (neither MSI nor PE)."
            )


def _gcloud_cp(source: Path, destination: str, cache_control: str | None = None) -> None:
    cmd = [GCLOUD_CLI, "storage", "cp"]
    if cache_control:
        cmd.append(f"--cache-control={cache_control}")
    cmd.extend([str(source), destination])
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote native GH Actions artifacts to GCS.")
    parser.add_argument("--run-id", type=int, default=None, help="GitHub Actions run id")
    parser.add_argument("--tag", default=None, help="Tag name used for the build run (e.g. v1.0.0-native2)")
    parser.add_argument("--bucket", default="solace-downloads", help="GCS bucket")
    parser.add_argument("--object-prefix", default="solace-browser", help="GCS object prefix")
    parser.add_argument("--version", default=None, help="Version override (default: VERSION file)")
    parser.add_argument("--project-root", default=None, help="Project root override")
    parser.add_argument(
        "--versioned-cache-control",
        default="public,max-age=31536000,immutable",
        help="Cache-Control for versioned objects",
    )
    parser.add_argument(
        "--latest-cache-control",
        default="no-store,max-age=0,must-revalidate",
        help="Cache-Control for latest objects",
    )
    args = parser.parse_args()

    project_root = (
        Path(args.project_root).resolve()
        if args.project_root
        else Path(__file__).resolve().parents[2]
    )
    version = args.version or _read_version(project_root)

    username, password = _github_credentials()
    run_id = _resolve_run_id(args.tag, args.run_id, username, password)
    run_meta = _verify_run_success(run_id, username, password)

    encoded_owner = urllib.parse.quote(REPO_OWNER)
    encoded_repo = urllib.parse.quote(REPO_NAME)
    artifacts_data = _github_api_get(
        f"/repos/{encoded_owner}/{encoded_repo}/actions/runs/{run_id}/artifacts?per_page=100",
        username,
        password,
    )
    artifacts_by_name = {
        artifact["name"]: artifact for artifact in artifacts_data.get("artifacts", [])
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = project_root / "scratch" / "native-promotion" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    promotion_summary: dict[str, Any] = {
        "run_id": run_id,
        "run_url": run_meta.get("html_url"),
        "version": version,
        "bucket": args.bucket,
        "object_prefix": args.object_prefix,
        "versioned_cache_control": args.versioned_cache_control,
        "latest_cache_control": args.latest_cache_control,
        "platforms": [],
    }

    with tempfile.TemporaryDirectory(prefix="solace-native-artifacts-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        validated: list[tuple[PlatformSpec, Path, Path]] = []

        # Fail-closed gate: verify all artifacts before uploading any object to GCS.
        for spec in PLATFORMS:
            artifact = artifacts_by_name.get(spec.artifact_name)
            if artifact is None:
                raise RuntimeError(f"Missing artifact '{spec.artifact_name}' in run {run_id}.")
            zip_path = temp_dir / f"{spec.artifact_name}.zip"
            _github_download(artifact["archive_download_url"], zip_path, username, password)
            extract_dir = temp_dir / spec.artifact_name
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(extract_dir)

            binary = _find_file(extract_dir, spec.object_name)
            checksum = _find_file(extract_dir, f"{spec.object_name}.sha256")
            _verify_binary(spec.target_os, binary)
            validated.append((spec, binary, checksum))

        for spec, binary, checksum in validated:
            versioned_binary = (
                f"gs://{args.bucket}/{args.object_prefix}/v{version}/{spec.object_name}"
            )
            latest_binary = (
                f"gs://{args.bucket}/{args.object_prefix}/latest/{spec.object_name}"
            )
            versioned_sha = versioned_binary + ".sha256"
            latest_sha = latest_binary + ".sha256"

            _gcloud_cp(binary, versioned_binary, cache_control=args.versioned_cache_control)
            _gcloud_cp(binary, latest_binary, cache_control=args.latest_cache_control)
            _gcloud_cp(checksum, versioned_sha, cache_control=args.versioned_cache_control)
            _gcloud_cp(checksum, latest_sha, cache_control=args.latest_cache_control)

            promotion_summary["platforms"].append(
                {
                    "target_os": spec.target_os,
                    "artifact_name": spec.object_name,
                    "versioned_binary": versioned_binary,
                    "latest_binary": latest_binary,
                    "versioned_sha256": versioned_sha,
                    "latest_sha256": latest_sha,
                    "size_bytes": binary.stat().st_size,
                }
            )

    (out_dir / "promotion-summary.json").write_text(
        json.dumps(promotion_summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(promotion_summary, indent=2))
    print(f"\nPromotion summary written to: {out_dir / 'promotion-summary.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
