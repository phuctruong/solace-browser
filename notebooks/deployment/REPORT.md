# Deployment Notebook Report

Date: 2026-03-05
Project: solace-browser

## What was updated
1. Notebook 01 now treats Windows artifact as a full installer (`.exe`) and records installer size evidence.
2. Notebook 02 now assumes `gcloud` is already authenticated, fail-checks active account/project/bucket, and validates installer marker + checksum naming.
3. `src/scripts/release_browser_cycle.sh` now enforces installer marker when `TARGET_OS=windows` and `WINDOWS_PACKAGE_MODE=installer`.
4. `src/scripts/promote_native_builds_to_gcs.py` now enforces installer marker and is atomic (verifies all platform artifacts before any GCS upload).

## Validation executed
1. Notebook JSON validation:
   - `01-github-native-matrix-deploy.ipynb` OK
   - `02-promote-native-artifacts.ipynb` OK
2. Script validation:
   - `bash -n src/scripts/release_browser_cycle.sh` OK
   - `python3 -m py_compile src/scripts/promote_native_builds_to_gcs.py` OK
3. Local release-cycle dry run (Linux):
   - Command: `TARGET_OS=linux UPLOAD_ENABLED=0 DOWNLOAD_ENABLED=0 RUN_SMOKE=0 src/scripts/release_browser_cycle.sh`
   - Output dir: `scratch/release-cycle/20260305-133354`
   - Metrics: build `121722ms`, artifact `320822760` bytes, smoke skipped
4. Live GCS verification (Notebook 02 check cell):
   - Linux/macOS/Windows + sha URLs all returned `200`
   - Windows latest failed installer gate: `Inno Setup Setup Data` marker missing
5. Promotion behavior checks:
   - Initial run against existing run id `22675190613` failed on Windows installer gate.
   - After atomic fix, same run fails before any upload with:
     `... is not an Inno Setup installer (marker missing).`

## Current production state (important)
- `latest` Windows object exists at:
  - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe`
- Current size (HTTP `content-length`): `89005981` bytes (~84.88 MB)
- It is currently a plain PE executable, not an Inno Setup installer.

## Before vs After
Before:
- Notebook checks accepted Windows PE but did not require installer-level guarantee end-to-end.
- Promotion script could upload Linux/macOS before failing on Windows mismatch.

After:
- Notebook checks require installer marker and report installer size.
- Release and promotion scripts enforce installer marker.
- Promotion path is atomic fail-closed across all three platforms.

## What is still needed to fully switch production to installer-first
1. Push these changes to GitHub (workflow + scripts + notebook updates).
2. Trigger a new native matrix build on tag (`build-binaries`) so Windows artifact is installer-based.
3. Run Notebook 02 promotion with the new successful run id.
4. Re-run Notebook 02 verification cell; expected result is installer marker present and checksum matches for all platforms.
