# ORACLE SWEEP

Task oracle checks:
- NORTHSTAR alignment: YES — browser-domain app discovery strengthens local-first messaging automation without service API keys.
- Safety gate: route is read-only and does not mutate session-rules or install state.
- Auth gate: `Bearer` header is required before any domain lookup response is returned.
- Domain logic: matching normalizes protocol, host casing, ports, and leading `www.`.
- Catalog scope: route is limited to messaging apps and excludes enterprise-only flows from this discovery lane.
- Regression sweep: adjacent server endpoint suites remain green after the helper and route changes.

Catalog verification:
- `data/default/app-store/official-store.json` already contains the ten required messaging app entries.
- No store mutation was necessary for this task because the current catalog already satisfies the requested coverage.
