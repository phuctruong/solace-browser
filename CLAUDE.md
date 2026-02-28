# CLAUDE.md — Solace Browser Runtime

## Purpose
This repo owns two active runtime surfaces:
- the browser control webservice in `solace_browser_server.py`
- the browser-site static pages under `web/`

Everything else should support one of those two surfaces directly.

## Active Browser API
The only supported browser-control API lives in `solace_browser_server.py`.

Start it:
```bash
python3 solace_browser_server.py --port 9222 --head
```

Supported endpoints:
- `GET /api/health`
- `GET /api/status`
- `POST /api/navigate`
- `POST /api/click`
- `POST /api/fill`
- `POST /api/evaluate`
- `POST /api/screenshot`
- `POST /api/snapshot`
- `GET /api/aria-snapshot`
- `GET /api/dom-snapshot`
- `GET /api/page-snapshot`
- `GET /api/events`

Rules:
- `POST /api/evaluate` uses `expression`, not `script`
- do not introduce a second server surface under `browser/`
- if the API changes, update `docs/BROWSER_API.md`, `README.md`, and this file in the same change

## Browser Site Rules
The site under `web/` follows PHUC architecture:
- one shared stylesheet: `web/css/site.css`
- one shared runtime: `web/js/solace.js`
- slug-first routing via `web/server.py`
- no inline CSS
- no inline JS
- legacy `.html` routes redirect to slug URLs

Start local site:
```bash
./src/scripts/start-local-webserver.sh 8791
```

## Verification Gates
Browser API:
- `curl -fsS http://127.0.0.1:9222/api/health`
- `curl -fsS http://127.0.0.1:9222/api/page-snapshot`

Browser site:
- `./scripts/check_web_architecture.sh`
- `pytest -q tests/test_web_architecture.py`

For interaction/debugging:
- use the live browser webservice itself for navigation, snapshots, screenshots, and evaluation
- prefer saved HTML and screenshots over hand-waving when diagnosing page issues

## Documentation Contract
Canonical docs:
- `README.md` — operator quickstart
- `docs/BROWSER_API.md` — browser API reference
- `src/diagrams/README.md` — runtime diagram index

Historical papers can remain, but they must not override the active runtime contract.

## Anti-Patterns
Forbidden:
- adding a second HTTP server implementation for browser control
- documenting endpoints that the active server does not expose
- allowing API drift between code and docs
- page-local CSS/JS in `web/*.html`
- hidden fallback behavior that masks failed browser actions

## Current Runtime Status
- active browser API consolidated to `solace_browser_server.py`
- structured snapshot endpoints operational
- browser site and local slug server operational
- browser-driven QA artifacts supported through the live API
