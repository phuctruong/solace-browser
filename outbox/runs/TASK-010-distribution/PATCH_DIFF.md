# PATCH DIFF — TASK-010-distribution

- Added `scripts/VERSION` with package version `0.9.0`.
- Added `scripts/version.sh` to emit the release string from `scripts/VERSION` plus glow suffix `368`.
- Reworked `scripts/build-deb.sh` to read `scripts/VERSION`, assemble the package tree under `/tmp/solace-browser-pkg`, write `DEBIAN/control`, copy browser and Yinyang assets into package paths, and build the `.deb` with `dpkg-deb`.
- Added `scripts/solace-browser.desktop` with the requested desktop metadata for Linux distribution.
- Updated `README.md` with a `Distribution` section covering version lookup and `.deb` build steps.

## Files Changed

- `scripts/build-deb.sh`
- `scripts/version.sh`
- `scripts/VERSION`
- `scripts/solace-browser.desktop`
- `README.md`

## Key Behaviors

- `scripts/build-deb.sh` fails loudly when `dpkg-deb` is missing.
- The generated control file sets `Package: solace-browser`, `Version: 0.9.0`, `Architecture: amd64`, and the requested runtime dependencies.
- The package includes `usr/bin/solace-browser`, `usr/lib/solace-browser/launch-yinyang.sh`, `usr/lib/solace-browser/yinyang-server.py`, `usr/lib/systemd/user/yinyang.service`, and `usr/share/applications/solace-browser.desktop`.
- The packaged launcher injects `SOLACE_REPO_ROOT=/usr/lib/solace-browser`, and the packaged service points `ExecStart` at the installed launcher path.
