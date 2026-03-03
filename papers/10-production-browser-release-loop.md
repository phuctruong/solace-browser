# Paper 10 — Production Browser Release Loop
**Date:** 2026-03-03  
**Auth:** 65537  
**Status:** CANONICAL

## Purpose
Define a repeatable pipeline for shipping a new Solace Browser build to real production (`solaceagi.com`) with measurable speed and deterministic validation.

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
1. Compile binary (`pyinstaller` spec in this repo).
2. Generate SHA-256 checksum.
3. Upload to:
   - `gs://solace-downloads/solace-browser/v{VERSION}/solace-browser-linux-x86_64`
   - `gs://solace-downloads/solace-browser/latest/solace-browser-linux-x86_64`
4. Download from `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-linux-x86_64`
5. Run smoke:
   - start binary with `--head --port <port>`
   - verify `/api/status`
6. Run production API matrix from OpenAPI.
7. Persist run report + timings into `scratch/release-cycle/<timestamp>/`.

## Reusable Scripts
- `src/scripts/release_browser_cycle.sh`
  - compile, upload, download, smoke, timing report.
- `src/scripts/test_solaceagi_api_matrix.py`
  - OpenAPI-driven matrix test for production APIs.

## Default Bundle Policy
Ship by default:
1. `solace-browser` Linux x86_64 binary.
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
1. build_ms
2. upload_ms
3. download_ms
4. smoke_ms
5. api_matrix_total_ms

Success threshold (initial):
- total release loop (build+upload+download+smoke) < 15 minutes on dev host.

## Real Account Testing Note
Authenticated endpoint coverage requires runtime credentials (`SOLACE_BEARER_TOKEN` and/or `SOLACE_API_KEY`) or live login token exchange.  
Without credentials, matrix still validates transport, routing, and auth gates (4xx expected, 5xx forbidden).
