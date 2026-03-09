**Done**
- Added the version source and glow helper in `scripts/VERSION:1` and `scripts/version.sh:1`.
- Reworked the Debian packager in `scripts/build-deb.sh:1` to write `/tmp/solace-browser-pkg/DEBIAN/control`, copy the browser + Yinyang service assets, and build `dist/solace-browser_0.9.0_amd64.deb`.
- Added the Linux desktop entry in `scripts/solace-browser.desktop:1` and the distribution instructions in `README.md:20`.
- Wrote the required handoff artifacts in `outbox/runs/TASK-010-distribution/PATCH_DIFF.md:1`, `outbox/runs/TASK-010-distribution/GREEN_GATE.md:1`, and `outbox/runs/TASK-010-distribution/EVIDENCE.json:1`.

**Validated**
- Passed `bash -n scripts/build-deb.sh`, `bash -n scripts/version.sh`, `cat scripts/VERSION`, and `desktop-file-validate scripts/solace-browser.desktop`.
- Ran a real `bash scripts/build-deb.sh` build and produced `dist/solace-browser_0.9.0_amd64.deb`; the generated control file is at `/tmp/solace-browser-pkg/DEBIAN/control`.

- If you want, I can next add checksum/signing output or wire this packaging step into CI.