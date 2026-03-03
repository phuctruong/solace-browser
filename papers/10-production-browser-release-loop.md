# Paper 10 — Production Browser Release Loop
**Date:** 2026-03-03  
**Auth:** 65537  
**Status:** CANONICAL

## Purpose
Define a repeatable pipeline for shipping a new Solace Browser build to real production (`solaceagi.com`) with measurable speed and deterministic validation.

## Platform Targets
Release loop is now platform-scoped and supports:
1. Linux: `solace-browser-linux-x86_64`
2. macOS: `solace-browser-macos-universal`
3. Windows: `solace-browser-windows-x86_64.exe`

## Native Build Reality (2026-03-03)
1. macOS binaries must be built on macOS runners/hosts.
2. Windows binaries must be built on Windows runners/hosts.
3. Linux host cannot produce valid native macOS/Windows artifacts for release channels.
4. Release script is fail-closed for non-native targets when `BUILD_ENABLED=1`.
5. Release script validates binary format before upload:
   - Linux target must be `ELF`
   - macOS target must be `Mach-O`
   - Windows target must be `PE`

Validation evidence:
- `scripts/build-mac.sh` on Linux returns: `ERROR: build-mac.sh must run on macOS`.
- `scripts/build-windows.sh` now fails on non-Windows hosts instead of emitting mislabeled artifacts.
- `src/scripts/release_browser_cycle.sh` rejects non-native binary headers (e.g., Linux ELF mislabeled as `.exe`).
- Native matrix path is GitHub Actions (`ubuntu-latest`, `macos-latest`, `windows-latest`).

## Committee (5 personas)
This release loop is reviewed by:
1. Rory Sutherland — perceived value, trust framing, adoption friction.
2. Russell Brunson — conversion path from `/download` to active usage.
3. Vanessa Van Edwards — emotional clarity, user confidence in install and first run.
4. Don Norman — interaction clarity and error-recovery ergonomics.
5. Kent Beck — testability, fast feedback, and regression containment.

## Release Invariant
Every release must satisfy:
1. Build reproducibly from source.
2. Publish to versioned + latest channels.
3. Download from production URL.
4. Boot with `--head` and pass API smoke.
5. Run production API matrix against `https://www.solaceagi.com`.
6. Write metrics to `scratch/` for each round.

## Deployment Loop
1. Select target platform (`TARGET_OS=linux|macos|windows`).
2. Compile binary (PyInstaller spec in this repo).
3. Generate SHA-256 checksum.
4. Upload to:
   - `gs://solace-downloads/solace-browser/v{VERSION}/solace-browser-linux-x86_64`
   - `gs://solace-downloads/solace-browser/latest/solace-browser-linux-x86_64`
   - `gs://solace-downloads/solace-browser/v{VERSION}/solace-browser-macos-universal`
   - `gs://solace-downloads/solace-browser/latest/solace-browser-macos-universal`
   - `gs://solace-downloads/solace-browser/v{VERSION}/solace-browser-windows-x86_64.exe`
   - `gs://solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe`
5. Download from `https://storage.googleapis.com/solace-downloads/solace-browser/latest/<platform-artifact>`
6. Run smoke:
   - start binary with `--head --port <port>`
   - verify `/api/status`
7. Run production API matrix from OpenAPI.
8. Persist run report + timings into `scratch/release-cycle/<timestamp>/`.

## Website Link Contract (solaceagi.com)
`solaceagi.com` and `www.solaceagi.com` download CTAs must point to GCS `latest` objects:
1. Linux:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-linux-x86_64`
2. macOS:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-macos-universal`
3. Windows:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe`

Checksum links (same page):
1. Linux checksum: `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-linux-x86_64.sha256`
2. macOS checksum: `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-macos-universal.sha256`
3. Windows checksum: `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe.sha256`

## Reusable Scripts
- `src/scripts/release_browser_cycle.sh`
  - platform-aware compile, upload, download, smoke, timing report.
- `src/scripts/test_solaceagi_api_matrix.py`
  - OpenAPI-driven matrix test for production APIs.
- `src/scripts/promote_native_builds_to_gcs.py`
  - downloads native GitHub Actions artifact bundles, verifies ELF/Mach-O/PE headers, uploads to GCS `v{VERSION}` + `latest`.

## CI Without GCP Secret
If GitHub Actions cannot authenticate to GCP:
1. Run native matrix build with `UPLOAD_ENABLED=0` and upload artifacts (`native-linux`, `native-macos`, `native-windows`).
2. Run promotion script locally:
   - `python3 src/scripts/promote_native_builds_to_gcs.py --tag <v-tag>`
3. Promotion script is fail-closed on binary-type mismatch.

### Canonical Commands
1. Linux release round:
   - `TARGET_OS=linux src/scripts/release_browser_cycle.sh`
2. macOS release round:
   - `TARGET_OS=macos src/scripts/release_browser_cycle.sh`
3. Windows release round:
   - `TARGET_OS=windows src/scripts/release_browser_cycle.sh`
4. CI compile/upload only (no smoke/download):
   - `TARGET_OS=<platform> DOWNLOAD_ENABLED=0 RUN_SMOKE=0 src/scripts/release_browser_cycle.sh`

## Default Bundle Policy
Ship by default:
1. Platform binary (`linux`, `macos`, `windows` target artifact).
2. SHA-256 checksum file.
3. Minimal runtime dependencies to boot `--head`.
4. OAuth3-aware API surface (`/api/status`, `/api/navigate`, `/api/snapshot`, `/api/screenshot`).

Do not bundle by default:
1. Experimental translators.
2. Deprecated handlers.
3. Large test fixtures.
4. Source-only research assets.

## Speed Metrics
Track every release:
1. build_ms (per platform)
2. upload_ms (per platform)
3. download_ms (per platform where enabled)
4. smoke_ms (per platform where enabled)
5. api_matrix_total_ms (linux production round)

Success threshold (initial):
- total release loop (build+upload+download+smoke) < 15 minutes on dev host.

## Real Account Testing Note
Authenticated endpoint coverage requires runtime credentials (`SOLACE_BEARER_TOKEN` and/or `SOLACE_API_KEY`) or live login token exchange.  
Without credentials, matrix still validates transport, routing, and auth gates (4xx expected, 5xx forbidden).
