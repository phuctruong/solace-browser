# Solace Browser API

The only supported browser-control webservice is `solace_browser_server.py`.

Start it:

```bash
python3 solace_browser_server.py --port 9222 --head
```

Base URL: `http://127.0.0.1:9222`

## Core Endpoints

### Health
`GET /api/health`

Response:
```json
{ "ok": true, "mode": "headed", "running": true }
```

### Status
`GET /api/status`

Returns current URL, page count, event count, session checkpoint state, and Part 11 runtime status.
Also includes:
- `api_methods` method map (fail-closed contract source of truth)
- `capabilities` flags (for example `part11`, `prime_wiki_local`, `prime_mermaid_local`)

Example checks:
```bash
curl -fsS http://127.0.0.1:9222/api/status | jq '.api_methods'
curl -fsS http://127.0.0.1:9222/api/status | jq '.capabilities'
```

### Navigate
`POST /api/navigate`

Request:
```json
{ "url": "https://example.com" }
```

### Quick Snapshot
`POST /api/snapshot`

Returns current page title, URL, and HTML preview.

### Evaluate
`POST /api/evaluate`

Request body key is `expression`, not `script`.

Example:
```json
{ "expression": "() => document.title" }
```

### Screenshot
`POST /api/screenshot`

Request:
```json
{ "filename": "example.png" }
```

### Structured Snapshots
- `GET /api/aria-snapshot`
- `GET /api/dom-snapshot`
- `GET /api/page-snapshot`

These return structured nodes that are appropriate for automation QA, selectors, and debugging.

## Example Session

```bash
curl -fsS http://127.0.0.1:9222/api/health
curl -fsS -X POST http://127.0.0.1:9222/api/navigate \
  -H 'Content-Type: application/json' \
  -d '{"url":"http://127.0.0.1:8788/"}'
curl -fsS http://127.0.0.1:9222/api/page-snapshot
curl -fsS -X POST http://127.0.0.1:9222/api/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"expression":"() => document.title"}'
```

## Contract Rules

- There is one supported API surface.
- Do not use or document `browser/http_server.py` or `browser/handlers.py`.
- Use `/api/page-snapshot` for structured inspection, not ad hoc HTML parsing when possible.
- Use `expression` for `/api/evaluate`.
