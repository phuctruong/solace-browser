# CLAUDE.md — Solace Browser Runtime
# Belt: Yellow | Rung: 274177 | GLOW: L (Luminous)
# DNA: browser(capture, control, execute, evidence) x 18_apps x yinyang = agent_platform

## Purpose
This repo owns two active runtime surfaces:
- the browser control webservice in `solace_browser_server.py`
- the browser-site static pages under `web/`

Everything else should support one of those two surfaces directly.

## 10 Uplift Principles (Paper 17)

| # | Principle | This Project | Status |
|---|-----------|-------------|--------|
| P1 | Gamification | Belt Yellow, rung in papers, GLOW on artifacts | Partial |
| P2 | Magic Words | DNA equations, prime channels, /distill | Strong |
| P3 | Famous Personas | Norman (UX), Rams (design), Lie (CSS), Hickey (arch), Van Edwards (EQ) | On-demand |
| P4 | Skills | prime-safety + prime-coder + styleguide-first auto-load | Complete |
| P5 | Recipes | 81 recipes in data/default/recipes/ | Partial |
| P6 | Access Tools | Playwright + CDP 4-plane, OAuth3-scoped | Partial |
| P7 | Memory | 9 papers, 19 diagrams, evidence chains | Strong |
| P8 | Care | Yinyang delight engine, warm tokens, Anti-Clippy | Partial |
| P9 | Knowledge | Papers network, IF Theory foundation | Strong |
| P10 | God | 65537 target, evidence-first, humility, sealed store | Present |

Uplift = P1 x P2 x ... x P10. If any Pn = 0, Uplift = 0.

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
