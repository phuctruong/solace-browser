# Notebook-First Deployment Decision

Date: 2026-03-05
Project: solace-browser

## Question
Would notebook-first deployment help Solace Browser for Windows + macOS + Linux uploads and GitHub updates?

## Short Answer
Yes, for this release workflow notebook-first helps.

## Why (mapped to Papers 46/47/48)
1. Paper 46 (notebook-first): deployment reasoning becomes executable proof before irreversible release actions.
2. Paper 47 (evidence ledger): each release step can be logged as a human-readable transaction with machine-verifiable artifacts.
3. Paper 48 (capsule rules): notebooks stay authoring/reporting surfaces, while runtime truth remains canonical scripts/workflows.

## Fit to Current Solace Browser Release Loop
Current canonical flow already exists in:
- `.github/workflows/build-binaries.yml` (native matrix build on linux/macos/windows)
- `src/scripts/release_browser_cycle.sh` (build and verify binary type)
- `src/scripts/promote_native_builds_to_gcs.py` (GitHub artifacts -> GCS versioned + latest)

Notebook-first should be added as orchestration + evidence, not as runtime replacement.

## Recommendation
Adopt notebook-first deployment for release operations with these boundaries:
1. Keep scripts/workflows as canonical execution path.
2. Use notebooks for preflight checks, controlled command execution, and before/after evidence reports.
3. Seal output reports and link them to release tags.

## Scope of this implementation
This directory includes practical notebooks to:
1. Trigger/observe GitHub native matrix builds.
2. Promote native artifacts to GCS.
3. Run a local Linux dry-run and capture before/after evidence.
