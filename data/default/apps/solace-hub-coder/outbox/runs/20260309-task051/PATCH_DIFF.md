# Task 051 Patch Diff

## Files changed
- `yinyang_server.py`
- `tests/test_domain_detection.py`
- `solace-hub/src/sidepanel.html`
- `solace-hub/src/sidepanel.js`

## Server changes
- Added `GET /api/v1/apps/by-domain` with auth and repo-scoped domain matching.
- Added `GET /api/v1/user/tier` reading `user.tier` with default `free`.
- Added `POST /api/v1/apps/custom/create` with slug validation, traversal blocking, manifest scaffolding, and session-rules scaffolding.
- Added `POST /api/v1/apps/sync` with free-tier denial plus upgrade URL, and paid-tier remote sync attempt.
- Reworked domain app discovery to read session rules from the active repo root instead of the global in-memory session cache.

## Sidebar changes
- Added `solace-hub/src/sidepanel.html` with the new domain apps panel.
- Added `solace-hub/src/sidepanel.js` with tier fetch, domain fetch, install gating, custom app creation, and sync submission wiring.

## Test changes
- Added `tests/test_domain_detection.py` covering domain discovery, auth, tier resolution, custom app creation, traversal rejection, free-tier sync denial, and sidebar panel presence.
