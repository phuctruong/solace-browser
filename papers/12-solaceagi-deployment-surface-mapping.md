# Paper 12 — SolaceAGI Deployment Surface Mapping
**Date:** 2026-03-03  
**Auth:** 65537  
**Status:** CANONICAL

## Purpose
Prevent deployment confusion between Solace Browser repository surfaces and the public `www.solaceagi.com` website by documenting exact Cloud Run domain mappings and trigger sources.

## Verified Runtime Mapping (GCP)
Domain mappings in `us-central1`:
1. `www.solaceagi.com` -> Cloud Run service `solaceagi`
2. `solaceagi.com` -> Cloud Run service `solaceagi`
3. `qa.solaceagi.com` -> Cloud Run service `solaceagi-qa`

## Trigger Source of Truth
Cloud Build triggers for those services point to GitHub repo:
- `owner`: `phuctruong`
- `name`: `solaceagi`
- `qa` trigger branch regex: `^qa$`
- `prod` trigger branch regex: `^prod$`

Implication:
1. Pushing to `phuctruong/solace-browser` does NOT update `www.solaceagi.com` surfaces.
2. `www.solaceagi.com` updates require changes in `phuctruong/solaceagi` repo.

## Surface Separation
1. `solace-browser` repo:
   - Browser runtime, local web UI (`web/server.py`), browser release artifacts.
2. `solaceagi` repo:
   - Public website and production app-store surface at `www.solaceagi.com`.

## Download Surface Contract
Public website download links must resolve to GCS bucket `solace-downloads`:
1. Linux binary:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-linux-x86_64`
2. macOS binary:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-macos-universal`
3. Windows binary:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe`

Fail-closed condition:
- If any platform URL returns non-200 on release validation, block claim that production download surface is healthy.

## Release Gate Addendum
Before asserting production parity:
1. Confirm domain mapping target service.
2. Confirm build trigger repository and branch.
3. Confirm deployed commit SHA exists in the intended repository.
4. Run one production smoke test on the mapped surface.

## Operational Rule
Fail closed on deployment assumptions:
- If domain/service/trigger source do not match the edited repository, block release claim and redirect changes to the correct repository pipeline.
