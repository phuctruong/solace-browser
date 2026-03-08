#!/usr/bin/env python3
"""
promote_native_builds_to_gcs.py — Promote verified GitHub artifacts to GCS.
Auth: 65537 | Port 9222: PERMANENTLY BANNED

Usage:
    python scripts/promote_native_builds_to_gcs.py \
        --tag v1.0.0 \
        --artifacts-dir scratch/github-artifacts \
        --bucket solace-downloads

    python scripts/promote_native_builds_to_gcs.py \
        --tag v1.0.0 \
        --run-id 12345678 \
        --bucket solace-downloads

Artifacts uploaded to GCS under:
    gs://{bucket}/solace-browser/v{VERSION}/
    gs://{bucket}/solace-browser/latest/
"""

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_sha_file(path: Path) -> tuple[str, str]:
    parts = path.read_text(encoding="utf-8").strip().split()
    if len(parts) < 2:
        raise ValueError(f"Invalid sha256 file: {path}")
    return parts[0], parts[-1]


def _verify_linux(path: Path) -> None:
    b = path.read_bytes()
    if not b.startswith(b"\x7fELF"):
        raise ValueError(f"Linux artifact is not ELF: {path}")


def _verify_macos(path: Path) -> None:
    b = path.read_bytes()
    macho_headers = {
        b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",
    }
    if b[:4] not in macho_headers:
        raise ValueError(f"macOS artifact is not Mach-O: {path}")


def _verify_windows(path: Path) -> None:
    b = path.read_bytes()
    ole2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    if not b.startswith(ole2):
        raise ValueError(f"Windows artifact is not MSI (OLE2 header missing): {path}")


# Artifact spec: (filename, verifier_fn)
ARTIFACTS: list[tuple[str, object]] = [
    ("solace-browser-linux-x86_64", _verify_linux),
    ("solace-browser-macos-universal", _verify_macos),
    ("solace-browser-windows-x86_64.msi", _verify_windows),
]


# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------

def _gcs_upload(local_path: Path, gcs_uri: str, gcloud: str) -> None:
    subprocess.run(
        [gcloud, "storage", "cp", str(local_path), gcs_uri],
        check=True,
    )
    print(f"  uploaded: {gcs_uri}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote native artifacts to GCS")
    parser.add_argument("--tag", required=True, help="Git tag, e.g. v1.0.0")
    parser.add_argument("--artifacts-dir", help="Directory of downloaded GitHub artifacts")
    parser.add_argument("--run-id", help="GitHub Actions run ID (alternative to --artifacts-dir)")
    parser.add_argument("--bucket", default="solace-downloads", help="GCS bucket name")
    args = parser.parse_args(argv)

    version = args.tag.lstrip("v")
    bucket = args.bucket
    timestamp = datetime.now(timezone.utc).isoformat()

    gcloud = shutil.which("gcloud")
    if not gcloud:
        raise RuntimeError("gcloud CLI not found on PATH")

    # Resolve artifacts directory
    if args.artifacts_dir:
        artifacts_base = Path(args.artifacts_dir)
    elif args.run_id:
        # Download from GitHub
        artifacts_base = Path(f"scratch/github-artifacts/{args.run_id}")
        artifacts_base.mkdir(parents=True, exist_ok=True)
        for artifact_name in ("native-linux", "native-macos", "native-windows"):
            dest = artifacts_base / artifact_name
            subprocess.run(
                ["gh", "run", "download", args.run_id, "-n", artifact_name, "-D", str(dest)],
                check=True,
            )
    else:
        raise ValueError("Must specify --artifacts-dir or --run-id")

    # Collect artifact files
    collected: dict[str, Path] = {}
    for filename, _ in ARTIFACTS:
        found = list(artifacts_base.rglob(filename))
        if not found:
            raise FileNotFoundError(f"Artifact not found in {artifacts_base}: {filename}")
        collected[filename] = found[0]

    # Verify all artifacts before ANY upload (fail-closed gate)
    print("=== Verifying artifacts (fail-closed gate) ===")
    for filename, verifier in ARTIFACTS:
        path = collected[filename]
        verifier(path)

        sha_file = path.parent / f"{filename}.sha256"
        if sha_file.is_file():
            expected_sha, _ = _parse_sha_file(sha_file)
            actual_sha = _sha256(path)
            if expected_sha != actual_sha:
                raise ValueError(
                    f"SHA256 mismatch for {filename}:\n"
                    f"  expected: {expected_sha}\n"
                    f"  actual:   {actual_sha}"
                )
            print(f"  PASS {filename} (sha256 verified)")
        else:
            print(f"  PASS {filename} (header verified, no sha256 file)")

    print("\n=== Uploading to GCS ===")
    versioned_prefix = f"gs://{bucket}/solace-browser/v{version}"
    latest_prefix = f"gs://{bucket}/solace-browser/latest"

    for filename, _ in ARTIFACTS:
        path = collected[filename]
        sha_file = path.parent / f"{filename}.sha256"

        # Upload binary to versioned + latest
        _gcs_upload(path, f"{versioned_prefix}/{filename}", gcloud)
        _gcs_upload(path, f"{latest_prefix}/{filename}", gcloud)

        # Upload sha256 if present
        if sha_file.is_file():
            _gcs_upload(sha_file, f"{versioned_prefix}/{filename}.sha256", gcloud)
            _gcs_upload(sha_file, f"{latest_prefix}/{filename}.sha256", gcloud)

    # Write promotion summary
    summary_dir = Path(f"scratch/native-promotion/{timestamp.replace(':', '-')}")
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "timestamp": timestamp,
        "tag": args.tag,
        "version": version,
        "bucket": bucket,
        "artifacts": [
            {
                "filename": filename,
                "sha256": _sha256(collected[filename]),
                "size_bytes": collected[filename].stat().st_size,
            }
            for filename, _ in ARTIFACTS
        ],
        "gcs_versioned_prefix": versioned_prefix,
        "gcs_latest_prefix": latest_prefix,
        "status": "promoted",
    }
    summary_path = summary_dir / "promotion-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== Promotion complete ===")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
