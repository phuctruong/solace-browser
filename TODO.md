# TODO — Solace Browser Web Architecture Sprint

**Project:** solace-browser
**Current Sprint:** PHUC web architecture for static browser site
**Target:** one shared stylesheet, one shared runtime, slug-first local server, fail-closed UI behavior
**Completed:** 2026-02-28

## TASK-WEB-001
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Replace standalone page-local CSS with shared `web/css/site.css`
Evidence: `web/home.html`, `web/download.html`, `web/machine-dashboard.html`, `web/tunnel-connect.html` all reference `/css/site.css` and contain no embedded `<style>` blocks.

## TASK-WEB-002
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Replace page-local scripts with shared `web/js/solace.js`
Evidence: all four pages reference `/js/solace.js`; page behavior degrades to safe mock states when APIs are unavailable.

## TASK-WEB-003
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Add real local webserver startup path under `src/scripts`
Evidence: `src/scripts/start-local-webserver.sh` starts `web/server.py`; clean slug URLs serve content and legacy `.html` paths redirect.

## TASK-WEB-004
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Normalize site links onto slug URLs
Evidence: site nav/footer and internal links now target `/`, `/download`, `/machine-dashboard`, `/tunnel-connect`.

## TASK-WEB-005
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Add PHUC architecture enforcement and verification
Evidence: `scripts/check_web_architecture.sh` and `tests/test_web_architecture.py` pass.

## TASK-WEB-006
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Enforce PHUC web architecture in CI on pushes and pull requests
Evidence: `.github/workflows/web-architecture.yml` runs `./scripts/check_web_architecture.sh` and `pytest -q tests/test_web_architecture.py`.


## TASK-WEB-007
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Remove stale duplicate browser API surface and document one supported webservice
Evidence: `browser/http_server.py` and `browser/handlers.py` removed; `docs/BROWSER_API.md`, `README.md`, and `CLAUDE.md` now point only at `solace_browser_server.py`.
