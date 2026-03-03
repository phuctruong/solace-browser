#!/usr/bin/env python3
"""
Bundle audit for release decisions.

Outputs a JSON and markdown report with size, runtime expectations, and
recommended default bundling policy.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    dist = repo / "dist"
    scratch = repo / "scratch" / "bundle-audit"
    scratch.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = scratch / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    binary = dist / "solace-browser"
    binary_alt = dist / "solace-browser-linux-x86_64"
    target = binary_alt if binary_alt.exists() else binary

    report = {
        "timestamp": stamp,
        "artifact_path": str(target),
        "artifact_exists": target.exists(),
        "artifact_size_bytes": target.stat().st_size if target.exists() else 0,
        "playwright_runtime_risk": "high",
        "recommendations": [
            "Bundle a pre-installed Chromium runtime or enforce first-run installer.",
            "Fail fast with explicit guidance if browser runtime is missing.",
            "Keep release artifact plus SHA-256 sidecar in versioned + latest channels.",
            "Track startup smoke success rate as a release gate.",
        ],
        "default_bundle_should_include": [
            "solace-browser binary",
            "sha256 checksum sidecar",
            "runtime browser install bootstrap",
            "minimal config template for --head and --headless",
        ],
        "default_bundle_should_exclude": [
            "translation generation scripts",
            "deprecated build-wish scripts",
            "non-runtime research/test fixtures",
        ],
    }

    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# Browser Bundle Audit",
        "",
        f"- Artifact: `{report['artifact_path']}`",
        f"- Exists: `{report['artifact_exists']}`",
        f"- Size bytes: `{report['artifact_size_bytes']}`",
        f"- Playwright runtime risk: `{report['playwright_runtime_risk']}`",
        "",
        "## Include by Default",
    ]
    md.extend([f"- {item}" for item in report["default_bundle_should_include"]])
    md.append("")
    md.append("## Exclude by Default")
    md.extend([f"- {item}" for item in report["default_bundle_should_exclude"]])
    md.append("")
    md.append("## Recommendations")
    md.extend([f"- {item}" for item in report["recommendations"]])
    (out_dir / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Audit output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
