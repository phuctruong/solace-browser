# Paper 11 — App Store Sync Governance
# DNA: `catalog = git-backed YAML; proposals = Firestore queue; promote = review → merge`
**Date:** 2026-03-03
**Auth:** 65537
**Status:** CANONICAL

## Purpose
Unify Solace website app store and Solace Browser app store around one official catalog source while preserving safe user-submitted app proposals.

## Committee Lens (5 Personas)
1. Rory Sutherland — trust and conversion framing for store credibility.
2. Russell Brunson — funnel clarity from app discovery to install.
3. Vanessa Van Edwards — confidence and emotional clarity in submission/review UX.
4. Don Norman — interaction clarity and recoverability.
5. Rich Hickey — simple data boundaries and explicit state transitions.

## Additional Guidance Anchors
- Phuc Forecast: prioritize predictable deploy/review loops over novelty.
- 65537 experts: evidence-first decisions and deterministic audit trails.
- Max Love: user-facing language should be warm, direct, and non-deceptive.
- God principle (humility): fail closed when a trust boundary is uncertain.

## Source-of-Truth Model
1. Official app catalog is git-backed JSON:
   - `data/default/app-store/official-store.json`
2. User proposals are backend-specific:
   - Production: Firestore collection (`app_store_proposals` by default)
   - Local dev: file backend (`data/default/app-store/proposed-apps-dev.jsonl`)
3. Browser API is the integration layer:
   - `GET /api/apps` and `GET /api/apps/{appId}` read official catalog + local install overlay
   - `GET /api/app-store/sync` exposes source metadata and counts
   - `GET|POST /api/app-store/proposals` handles proposal queue

## Sync Invariants
1. Official catalog is reviewable in git before release.
2. Installed local apps override status to `installed` but do not mutate official catalog.
3. Proposal submission never mutates official catalog directly.
4. Firestore/backend failures are fail-closed for proposal endpoints.
5. Local development can run without cloud dependencies.

## Local Development Workflow
1. Edit app manifests under `data/default/apps/<app-id>/manifest.yaml`.
2. Regenerate official catalog:
   - `python3 src/scripts/sync_app_store_catalog.py`
3. Commit catalog updates with manifest updates.
4. Submit proposal test entries through `/api/app-store/proposals` (file backend).
5. Review proposal JSONL in git PR before promoting apps to official catalog.

## Promotion Workflow (Proposal -> Official)
1. Proposal enters queue (`proposed`).
2. Human triage marks `triage` and validates diagrams/scopes/budget.
3. Accepted proposal becomes a real app manifest + diagrams + recipe.
4. Catalog re-sync script runs.
5. Git commit + deploy publishes to both website and browser surfaces.

## Forbidden Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Putting global app catalog in Firestore | Costs money per read, adds latency, breaks offline, and loses git versioning |
| Proposal submissions directly mutating the official catalog | Bypasses the review-then-merge promotion workflow and breaks trust |
| Running without a local development fallback for proposals | Cloud dependency for dev makes offline development impossible |

## Deployment Ownership Note
This governance model defines data contracts. Actual public `www.solaceagi.com` deployment ownership is validated separately in Paper 12 (domain mapping + trigger source). If the website surface is deployed from another repository, this paper's catalog/API changes must be ported there before claiming production parity.
