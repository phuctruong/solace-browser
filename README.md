# Solace Browser

Solace Browser is a local-first browser automation runtime with a single supported HTTP control API, OAuth3-aware execution surfaces, and a static site for product/distribution pages.

## Runtime Surfaces
- Browser control server: `solace_browser_server.py`
- Static site: `web/` served by `src/scripts/start-local-webserver.sh`
- Browser-site shared assets:
  - `web/css/site.css`
  - `web/js/solace.js`

## One Supported Browser API
The only supported browser-control webservice is `solace_browser_server.py`.

Start it:
```bash
python3 solace_browser_server.py --port 9222 --head
```

Base URL:
```text
http://127.0.0.1:9222
```

Core endpoints:
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

Important:
- `POST /api/evaluate` expects the JSON key `expression`
- `browser/http_server.py` and `browser/handlers.py` are not part of the supported runtime anymore

Full contract:
- [docs/BROWSER_API.md](/home/phuc/projects/solace-browser/docs/BROWSER_API.md)

## Local Web Site
Start the browser-site local server:
```bash
./src/scripts/start-local-webserver.sh 8791
```

Routes:
- `/`
- `/download`
- `/machine-dashboard`
- `/tunnel-connect`

Legacy `.html` URLs redirect to slug URLs.

## Install
```bash
git clone https://github.com/phuc-labs/solace-browser.git
cd solace-browser
python3 -m pip install -e .[dev]
playwright install
```

## Quick Use
Health check:
```bash
curl -fsS http://127.0.0.1:9222/api/health
```

Navigate:
```bash
curl -fsS -X POST http://127.0.0.1:9222/api/navigate \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

Get structured snapshot:
```bash
curl -fsS http://127.0.0.1:9222/api/page-snapshot
```

Evaluate page state:
```bash
curl -fsS -X POST http://127.0.0.1:9222/api/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"expression":"() => document.title"}'
```

Take screenshot:
```bash
curl -fsS -X POST http://127.0.0.1:9222/api/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"filename":"page.png"}'
```

## Static Site Architecture
The browser site follows the PHUC web architecture rules:
- one shared stylesheet
- one shared runtime JS file
- slug-first URLs
- no inline CSS
- no inline JS
- local-safe mock API responses for demo pages

Verification:
```bash
./scripts/check_web_architecture.sh
pytest -q tests/test_web_architecture.py
```

## Project Structure
```text
solace-browser/
├── solace_browser_server.py
├── browser/
│   ├── __init__.py
│   ├── core.py
│   ├── advanced.py
│   └── semantic.py
├── web/
│   ├── server.py
│   ├── home.html
│   ├── download.html
│   ├── machine-dashboard.html
│   ├── tunnel-connect.html
│   ├── css/site.css
│   ├── js/solace.js
│   └── images/splash/
├── src/scripts/start-local-webserver.sh
├── docs/BROWSER_API.md
├── scripts/check_web_architecture.sh
└── tests/test_web_architecture.py
```

## Current Status
- single supported browser API surface is active
- structured snapshot endpoints are working
- browser site uses shared CSS/JS and slug routes
- browser-driven QA artifacts can be generated through the live control API
